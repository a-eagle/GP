import re, sys, datetime, traceback
import time, os, platform, sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import datafile, cls
from utils import fx

def acceptTime():
    now = datetime.datetime.now()
    ts = now.strftime('%H:%M')
    if ts > '15:00' and ts < '23:59':
        return True
    return False

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
        loader = datafile.DataFileLoader()
        lastDay = loader.getLocalNewestDay()
        newestDay = loader.getNetNewestDay()
        if not newestDay:
            time.sleep(60 * 5)
            continue
        if newestDay == lastDay:
            cache[today] = True
            time.sleep(60 * 5)
            continue
        loader.downloadAndMergeAllMililine(0.1)
        
        ld = fx.FenXiLoader()
        ld.fxAll()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        traceback.print_exc()
    os.system('pause')