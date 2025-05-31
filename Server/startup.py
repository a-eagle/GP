import time, os, threading, datetime, traceback
import json, os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Server import cls_server, ths_server, lhb_server

thsServer = ths_server.Server()
clsServer = cls_server.Server()
lhbServer = lhb_server.Server()

IGNORE_DAY = ('2025-06-02', )

def acceptDay():
    td = datetime.date.today().strftime('%Y-%m-%d')
    return td not in IGNORE_DAY

def runner():
    while True:
        if not acceptDay():
            time.sleep(60 * 60)
            continue
        clsServer.loadTimeDegree()
        thsServer.loadHotsOneTime()
        clsServer.loadHotTc()
        time.sleep(20)

def loop():
    lastDay = None
    while True:
        if not acceptDay():
            time.sleep(60 * 60)
            continue
        td = datetime.date.today().strftime('%Y-%m-%d')
        if lastDay != td:
            lastDay = td
            print('---------------->', lastDay, '<----------------')
        try:
            thsServer.loadOneTime()
            clsServer.loadOneTime()
            lhbServer.loadOneTime()
        except Exception as e:
            traceback.print_exc()
        time.sleep(60)

if __name__ == '__main__':
    th = threading.Thread(target = runner, daemon = True)
    th.start()
    loop()