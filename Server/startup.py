import time, os, threading, datetime, traceback
import json, os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Server import cls_server, ths_server, lhb_server

thsServer = ths_server.Server()
clsServer = cls_server.Server()
lhbServer = lhb_server.Server()

def runner():
    while True:
        clsServer.loadTimeDegree()
        thsServer.loadHotsOneTime()
        clsServer.loadHotTc()
        time.sleep(10)

def loop():
    lastDay = None
    while True:
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
        time.sleep(10)

if __name__ == '__main__':
    th = threading.Thread(target = runner, daemon = True)
    th.start()
    loop()