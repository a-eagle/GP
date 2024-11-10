import re, sys, datetime, traceback
import time, os, platform, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import datafile, cls

def acceptTime():
    now = datetime.datetime.now()
    ts = now.strftime('%H:%M')
    if ts > '15:30' and ts < '23:59':
        return True
    return False

def getLocalLastDay():
    loader = datafile.DataFileLoader()
    c = loader.getLastCode()
    df = datafile.DataFile(c, datafile.DataFile.DT_MINLINE)
    df.loadData(datafile.DataFile.FLAG_NEWEST)
    lastDay = 0
    if df.data:
        lastDay = df.data[-1].day
    return lastDay

def getNewestDay():
    loader = datafile.DataFileLoader()
    c = loader.getLastCode()
    url = cls.ClsUrl()
    fs = url.loadFenShi(c)
    if not fs:
        return None
    datas = fs['dataArr']
    if datas:
        return datas[-1]['day']
    return None

def main():
    cache = {} # day : True | False
    while True:
        if not acceptTime():
            time.sleep(60 * 5)
            continue
        today = datetime.date.today()
        today = today.strftime("%Y-%m-%d")
        if cache.get(today, False):
            time.sleep(60 * 5)
            continue
        lastDay = getLocalLastDay()
        newestDay = getNewestDay()
        if not newestDay:
            time.sleep(60 * 5)
            continue
        if newestDay == lastDay:
            cache[today] = True
            time.sleep(60 * 5)
            continue

        loader = datafile.DataFileLoader()
        loader.mergeAllMililine()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
    os.system('pause')