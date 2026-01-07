import time, os, threading, datetime, traceback
import json, os, sys, platform

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
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
        if LOAD_CLS:
            clsServer.loadTimeDegree()
            clsServer.loadHotTc()
        if LOAD_THS:
            thsServer.loadHotsOneTime()
        time.sleep(20)

def loop():
    lastDay = None
    skipDay = '2026-01-07'
    while True:
        if not acceptDay():
            time.sleep(60 * 60)
            continue
        td = datetime.date.today().strftime('%Y-%m-%d')
        if td == skipDay:
            print('----skip-----', skipDay, '-----------')
            time.sleep(60 * 60)
            continue
        if lastDay != td:
            lastDay = td
            print('---------------->', lastDay, '<----------------')
        try:
            if LOAD_CLS:
                clsServer.loadOneTime()
            if LOAD_THS:
                thsServer.loadOneTime()
            lhbServer.loadOneTime()
        except Exception as e:
            traceback.print_exc()
        time.sleep(60)


LOAD_CLS = True
LOAD_THS = True

if __name__ == '__main__':
    th = threading.Thread(target = runner, daemon = True)
    th.start()
    loop()