import time, os, threading, datetime, traceback
import json, os, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Server import cls_server, ths_server, lhb_server
from download import ths_iwencai

thsServer = ths_server.Server()
clsServer = cls_server.Server()
lhbServer = lhb_server.Server()

def acceptDay():
    days = ths_iwencai.getTradeDays()
    if not days:
        return False
    td = datetime.date.today().strftime('%Y%m%d')
    return td == days[-1]

def runner():
    while True:
        if not acceptDay():
            time.sleep(60 * 60)
            continue
        #clsServer.loadTimeDegree()
        thsServer.loadHotsOneTime()
        #clsServer.loadHotTc()
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
            #clsServer.loadOneTime()
            lhbServer.loadOneTime()
        except Exception as e:
            traceback.print_exc()
        time.sleep(60)

if __name__ == '__main__':
    th = threading.Thread(target = runner, daemon = True)
    th.start()
    loop()