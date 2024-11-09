import os, json, sys, functools
import time, re
import win32gui, win32con, win32api

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Download import fiddler
from Download.datafile import *
from Common import base_win
from Tck import kline_utils

class FenXiCode:
    def __init__(self, code) -> None:
        self.MINUTES_IN_DAY = 241
        self.SPEED_PEROID = 10 # 时速周期 5 / 10 /15
        self.MIN_ZHANG_FU = 5 # 进攻最小涨幅

        self.code = code
        self.mdf = DataFile(self.code, DataFile.DT_MINLINE)
        self.infoOfDay = {} # day : {'dayAvgAmount': xx, 'item': ItemData, }
        self.results = [] # 进攻

    def loadFile(self):
        if not self.mdf.data:
            self.mdf.loadData(DataFile.FLAG_ALL)

    def calcLastestDays(self, lastDayNum = 30):
        if not self.mdf.data:
            return
        dayNum = len(self.mdf.data) // self.MINUTES_IN_DAY
        dayNumNew = min(dayNum, lastDayNum)
        fromIdx = dayNum - dayNumNew
        for i in range(fromIdx, dayNum):
            d = self.mdf.data[i * self.MINUTES_IN_DAY]
            self.calcOneDay(d.day)

    def calcOneDay(self, day):
        if day is None:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        self._calcAvgAmountOfDay(day)
        self._calcMinutesOfDay(day)

    def _calcAvgAmountOfDay(self, day : int):
        idx = self.mdf.getItemIdx(day)
        if idx < 0:
            return False
        m = self.mdf.data[idx]
        if m.day in self.infoOfDay and 'dayAvgAmount' in self.infoOfDay[m.day]:
            return True
        if m.day not in self.infoOfDay:
            self.infoOfDay[m.day] = {'midx': idx}
        a = 0
        num = min(self.MINUTES_IN_DAY, len(self.mdf.data) - idx)
        for i in range(num):
            m = self.mdf.data[idx + i]
            a += m.amount
        self.infoOfDay[m.day]['dayAvgAmount'] = int(a / num ) # 日内分时平均成交额 
        return True
    
    def _calcMinutesOfDay(self, day : int):
        fromIdx = self.mdf.getItemIdx(day)
        if fromIdx < 0:
            return False
        endMaxIdx = min(fromIdx + self.MINUTES_IN_DAY, len(self.mdf.data))
        for i in range(fromIdx, endMaxIdx):
            m = self.mdf.data[i]
            maxIdx, maxPrice = self._calcMaxPrice(i, min(endMaxIdx, i + self.SPEED_PEROID))
            if maxIdx < 0:
                continue
            me = self.mdf.data[maxIdx]
            if i == fromIdx and i > 0:
                pre = self.mdf.data[i - 1].price
            else:
                pre = self.mdf.data[i].price
            zf = (maxPrice - pre) / pre * 100
            if zf < self.MIN_ZHANG_FU:
                continue
            if self.results:
                last = self.results[-1]
                if last['day'] == m.day and i >= last['fromIdx'] and i <= last['endIdx']:
                    if last['zf'] <= zf:
                        self.results.pop(-1) # remove last, replace it
                    else:
                        continue # skip
            maxAmount3 = self.getMax3MunitesAvgAmount(i, maxIdx + 1)
            万 = 10000
            di = self.infoOfDay[m.day]
            curJg = {'day': m.day, 'fromMinute': m.time, 'endMinute': me.time, 'minuts': maxIdx - i + 1,
                     'fromIdx' : i, 'endIdx': maxIdx, 'zf': zf,
                     'max3MinutesAvgAmount': int(maxAmount3 / 万), 'dayAvgAmount': int(di['dayAvgAmount'] / 万) # 万元
                    }
            self.results.append(curJg)
        return True

    def getMax3MunitesAvgAmount(self, fromIdx, endIdx):
        spec = self.mdf.data[fromIdx : endIdx]
        spec.sort(key = lambda x : x.amount, reverse = True)
        num = min(3, len(spec))
        s = 0
        for i in range(num):
            s += spec[i].amount
        return int(s / num)

    def _calcMaxPrice(self, fromIdx, endIdx):
        maxIdx = -1
        maxPrice = 0
        day = self.mdf.data[fromIdx].day
        for i in range(fromIdx, endIdx):
            m = self.mdf.data[i]
            if m.day != day:
                break
            if m.price > maxPrice:
                maxPrice = m.price
                maxIdx = i
        return maxIdx, maxPrice
    
def loadAllCodes():
    p = os.path.join(VIPDOC_BASE_PATH, '__minline')
    cs = os.listdir(p)
    rs = []
    for name in cs:
        if name[0 : 2] == 'sh' and name[2] == '6':
            rs.append(name[2 : 8])
        elif name[0 : 2] == 'sz' and name[2 : 4] in ('00', '30'):
            rs.append(name[2 : 8])
    return rs

def fxAll():
    cs = loadAllCodes()
    for code in cs:
        fx = FenXiCode(code)
        fx.calcLastestDays()

def test():
    CODE = '300925'
    fx = FenXiCode(CODE)
    fx.loadFile()
    fx.calcLastestDays()
    #fx.calcOneDay(20240829)
    win = kline_utils.openInCurWindow_Code(base_win.BaseWindow(), {'code': CODE, } )
    for d in fx.results:
        print(d)
        win.klineWin.setMarkDay(d['day'])
    win32gui.PumpMessages()


if __name__ == '__main__':
    test()
    pass
