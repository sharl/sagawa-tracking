# -*- coding: utf-8 -*-
import sys
import time
import io
import threading

import schedule
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageEnhance
import requests
from bs4 import BeautifulSoup
from win11toast import notify

INTERVAL = 60


class taskTray:
    def __init__(self, codes):
        # 追跡番号
        self.codes = codes
        # 通知済みフラグ
        self.notified = False
        # スレッド実行モード
        self.running = False

        # from favicon
        base = 'https://www.sagawa-exp.co.jp'
        soup = BeautifulSoup(requests.get(base).content, 'html.parser')
        href = soup.find('link', rel='apple-touch-icon').get('href')
        self.icon_image = Image.open(io.BytesIO(requests.get(base + href).content))
        self.dimm_image = ImageEnhance.Brightness(self.icon_image).enhance(0.5).convert('L')

        menu = Menu(
            MenuItem('Check', self.doCheck),
            MenuItem('Exit', self.stopApp),
        )
        self.app = Icon(name='PYTHON.win32.sagawa', title='sagawa checker', icon=self.dimm_image, menu=menu)
        self.doCheck()

    def doCheck(self):
        lines = []
        count = 0
        icon = self.dimm_image

        url = 'https://k2k.sagawa-exp.co.jp/p/sagawa/web/okurijoinput.jsp'
        for code in self.codes:
            with requests.get(url) as r:
                soup = BeautifulSoup(r.content, 'html.parser')
                form = soup.find_all('form')[0]
                inps = form.find_all('input')
                data = {}
                for inp in inps:
                    name = inp.get('name')
                    value = inp.get('value')
                    data[name] = value if value else ''
                data['main:no1'] = code
                del data['main:_id43']

                with requests.post(url, data=data) as r:
                    soup = BeautifulSoup(r.content, 'html.parser')
                    tables = soup.find_all('table', class_='table_basic table_okurijo_detail2')
                    if len(tables) >= 2:
                        stat = tables[1].find_all('tr')[-1].find_all('td')[0].text.strip()
                        title = f'{code} {stat}'
                        if stat == '配達済み':
                            if self.notified is False:
                                self.notified = True
                                notify(
                                    body=title,
                                    audio='ms-winsoundevent:Notification.Reminder',
                                )
                                count = count + 1
                        lines.append(title)

        if count:
            icon = self.icon_image

        self.app.title = '\n'.join(lines)
        self.app.icon = icon
        self.app.update_menu()

    def runSchedule(self):
        schedule.every(INTERVAL).seconds.do(self.doCheck)

        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def stopApp(self):
        self.running = False
        self.app.stop()

    def runApp(self):
        self.running = True

        task_thread = threading.Thread(target=self.runSchedule)
        task_thread.start()

        self.app.run_detached()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        codes = []
        for code in sys.argv[1:]:
            code = code.replace('-', '')
            if len(code) == 12 and str(int(code)) == code:
                codes.append(code)
        taskTray(codes).runApp()
    else:
        print(f'{sys.argv[0]} <tracking code ...>')
        exit(1)
