import os, json, sys, functools
import time, re
import win32gui, win32con, win32api
import peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Download.datafile import *
from Download import console
from Common import base_win
from Tck import kline_utils
from orm import speed_orm

class FenXiCode:
    def __init__(self, code) -> None:
        self.MINUTES_IN_DAY = 241
        self.SPEED_PEROID = 10 # 时速周期 5 / 10 /15
        self.MIN_ZHANG_SU = 5 # 最小涨速

        self.code = code
        self.mdf = DataFile(self.code, DataFile.DT_MINLINE)
        self.infoOfDay = {} # day : {'dayAvgAmount': xx, 'item': ItemData, }
        self.results = []

    def getResult(self):
        return self.results

    def loadFile(self):
        if self.mdf.data:
            return
        self.mdf.loadData(DataFile.FLAG_ALL)
    
    def loadFileOfDays(self, daysNum):
        if self.mdf.data:
            return
        self.mdf.loadDataOfDays(daysNum)

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
            #if i == fromIdx and i > 0:
            #    pre = self.mdf.data[i - 1].price
            #    cur = self.mdf.data[i].price
            #    pre = min(cur, pre)
            #else:
            pre = self.mdf.data[i].price
            zf = (maxPrice - pre) / pre * 100
            if zf < self.MIN_ZHANG_SU:
                continue
            if self.results:
                last = self.results[-1]
                if last['day'] == m.day and i >= last['fromIdx'] and i <= last['endIdx']:
                    if last['zf'] <= zf:
                        self.results.pop(-1) # remove last, replace it
                    else:
                        continue # skip
            maxAmount3 = self.getMax3MunitesAvgAmount(i, maxIdx + 1)
            di = self.infoOfDay[m.day]
            curJg = {'day': m.day, 'fromMinute': m.time, 'endMinute': me.time, 'minuts': maxIdx - i + 1,
                     'fromIdx' : i, 'endIdx': maxIdx, 'zf': zf,
                     'max3MinutesAvgAmount': maxAmount3, 'dayAvgAmount': di['dayAvgAmount']
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

class FenXiLoader:
    def __init__(self) -> None:
        pass

    def loadAllCodes_Local(self):
        cs = os.listdir(NET_MINLINE_PATH)
        rs = []
        FL = ('3', '0', '6')
        for name in cs:
            code = name[0 : 6]
            if code[0] in FL and code[0 : 3] != '399':
                rs.append(code)
        return rs

    def loadAllCodes(self):
        from orm import ths_orm
        qr = ths_orm.THS_GNTC.select()
        rs = []
        FL = ('3', '0', '6')
        for it in qr:
            code = it.code
            if code[0] in FL and code[0 : 3] != '399':
                rs.append(code)
        return rs

    def save(self, code, rs):
        if not rs:
            return
        lrs = {}
        q = speed_orm.LocalSpeedModel.select().where(speed_orm.LocalSpeedModel.code == code, speed_orm.LocalSpeedModel.day >= rs[0]['day'])
        for it in q:
            key = f"{it.day}-{it.fromMinute}"
            lrs[key] = it
        for r in rs:
            key = f"{r['day']}-{r['fromMinute']}"
            obj = lrs.get(key, None)
            if not obj:
                speed_orm.LocalSpeedModel.create(day = r['day'], code = code, fromMinute = r['fromMinute'], 
                        endMinute = r['endMinute'], minuts = r['minuts'], zf = r['zf'], 
                        max3MinutesAvgAmount = r['max3MinutesAvgAmount'])
            elif obj.endMinute != r['endMinute']:
                obj.endMinute = r['endMinute']
                obj.minuts = r['minuts']
                obj.zf = r['zf']
                obj.max3MinutesAvgAmount = r['max3MinutesAvgAmount']
                obj.save()

    def fxAll(self):
        print('---begin fenxi zhang su----')
        x, y = console.getCursorPos()
        cs = self.loadAllCodes()
        now = datetime.datetime.now()
        print('start', now.strftime('%Y-%m-%d %H:%M:%S'))
        startTime = time.time()
        for i, code in enumerate(cs):
            flag = self.fxOneOfDays(code)
            if not flag:
                x, y = console.getCursorPos()
            console.setCursorPos(x, y)
            diffTime = int(time.time() - startTime)
            h = diffTime // 3600
            m = diffTime % 3600 // 60
            s = diffTime % 60
            ut = f'{h}:{m :02d}:{s :02d}'
            print(f'Loading {i} / {len(cs)}, {ut}')
        now = datetime.datetime.now()
        print('end', now.strftime('%Y-%m-%d %H:%M:%S'))
        print('---end fenxi zhang su----')

    def fxOne(self, code):
        try:
            fx = FenXiCode(code)
            fx.loadFile()
            fx.calcLastestDays()
            self.save(code, fx.getResult())
            return True
        except Exception as e:
            traceback.print_exc()
            print('Exception at code: ', code)
        return False
    
    def fxOneOfDays(self, code, daysNum = 5):
        try:
            fx = FenXiCode(code)
            fx.loadFileOfDays(daysNum)
            fx.calcLastestDays()
            self.save(code, fx.getResult())
            return True
        except Exception as e:
            traceback.print_exc()
            print('Exception at code: ', code)
        return False

def test():
    CODE = '000066'
    fx = FenXiCode(CODE)
    fx.loadFileOfDays()
    fx.calcLastestDays()

if __name__ == '__main__':
    #test()
    ld = FenXiLoader()
    ld.fxAll()
    #os.system('pause')
    #ld.fxOne('300688')

    #df = DataFile('000859', DataFile.DT_MINLINE)
    #df.loadData(DataFile.FLAG_ALL)
    #df.calcDays()
    #print(df.days)
    #DataFileLoader().chunkMinlineFile(df.code, 20240301, 20241129)
    pass