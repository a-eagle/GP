import os, json, sys, functools
import time, re
import win32gui, win32con, win32api
import peewee as pw

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from download.datafile import *
from download import console
from orm import d_orm

class FenXiCode:
    def __init__(self, code) -> None:
        self.MINUTES_IN_DAY = 241
        self.SPEED_PEROID = 10 # 时速周期 5 / 10 /15
        self.MIN_ZHANG_SU = 5 # 最小涨速

        self.code = code
        self.mdf = T_DataModel(self.code)
        self.infoOfDay = {} # day : {'dayAvgAmount': xx, 'item': ItemData, }
        self.results = []

    def getResult(self):
        return self.results

    def calcOneDay(self, day, loadData = True):
        if day is None:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        if loadData:
            self.mdf.loadLocalData(day)
        self.results.clear()
        self._calcMinutesOfDay(day)

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
            curJg = {'day': m.day, 'fromMinute': m.time, 'endMinute': me.time, 'minuts': maxIdx - i + 1,
                     'fromIdx' : i, 'endIdx': maxIdx, 'zf': zf}
            self.results.append(curJg)
        return True

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

    def loadAllCodes(self):
        rs = []
        KS = {'sz': ['0', '3'], 'sh': ['6']}
        for s in KS:
            path = f'{PathManager.TDX_VIP_PATH}\\{s}\\minline'
            accept = KS[s]
            cs = os.listdir(path)
            for name in cs:
                code = name[2 : 8]
                if code[0] in accept and code[0 : 3] != '399':
                    rs.append(code)
        return rs

    def save(self, code, rs):
        if not rs:
            return
        lrs = {}
        q = d_orm.LocalSpeedModel.select().where(d_orm.LocalSpeedModel.code == code, d_orm.LocalSpeedModel.day >= rs[0]['day'])
        for it in q:
            key = f"{it.day}-{it.fromMinute}"
            lrs[key] = it
        for r in rs:
            key = f"{r['day']}-{r['fromMinute']}"
            obj = lrs.get(key, None)
            if not obj:
                d_orm.LocalSpeedModel.create(day = r['day'], code = code, fromMinute = r['fromMinute'], 
                        endMinute = r['endMinute'], minuts = r['minuts'], zf = r['zf'])
            elif obj.endMinute != r['endMinute']:
                obj.endMinute = r['endMinute']
                obj.minuts = r['minuts']
                obj.zf = r['zf']
                obj.save()

    def fxAll_2(self):
        lastDay = d_orm.LocalSpeedModel.select(pw.fn.max(d_orm.LocalSpeedModel.day)).scalar()
        lastDay = datetime.date(lastDay // 10000, lastDay // 100 % 100, lastDay % 100)
        fromDay = lastDay + datetime.timedelta(days = 1)
        while fromDay <= datetime.date.today():
            curDay = fromDay.strftime('%Y%m%d')
            self.fxAll(curDay)
            fromDay += datetime.timedelta(days = 1)

    def fxAll(self, day):
        cs = self.loadAllCodes()
        for i, code in enumerate(cs):
            self.fxOneOfDay(code, day)
        print(f'Fenxi zhang su for [{day}] end')

    def fxOneOfDay(self, code, day):
        try:
            fx = FenXiCode(code)
            fx.calcOneDay(day)
            self.save(code, fx.getResult())
            return True
        except Exception as e:
            traceback.print_exc()
            print('Exception at code: ', code)
        return False

if __name__ == '__main__':
    #test()
    ld = FenXiLoader()
    ld.fxAll_2()
    #os.system('pause')
    #ld.fxOne('300688')

    #df = DataFile('000859', DataFile.DT_MINLINE)
    #df.loadData(DataFile.FLAG_ALL)
    #df.calcDays()
    #print(df.days)
    #DataFileLoader().chunkMinlineFile(df.code, 20240301, 20241129)
    pass