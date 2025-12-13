import re, sys, datetime, traceback
import time, os, platform, sys, struct

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import datafile, cls, henxin, console
from orm import ths_orm, cls_orm
from ui import fx

class TimelineDataFile(datafile.T_DataModel):
    MINUTES_IN_DAY = 241

    def __init__(self, code):
        super().__init__(code)

    def loadLocalLastDay(self):
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return 0
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return 0
        RL = 24
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        item = struct.unpack('2l4f', bs)
        return item[0]

    def getLocalDays(self):
        days = []
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return days
        filesize = os.path.getsize(path)
        RL = 24
        PAGE_SIZE = RL * TimelineDataFile.MINUTES_IN_DAY
        daysNum = filesize // PAGE_SIZE
        dx = filesize % PAGE_SIZE
        if dx != 0:
            print('File Size Error: ', self.code, filesize)
        f = open(path, 'rb')
        for i in range(daysNum):
            bs = f.read(RL)
            item = struct.unpack("2l4f", bs)
            days.append(item[0])
            f.seek(PAGE_SIZE - RL, 1)
        f.close()
        return days

    def isValidLocalFile(self):
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return True
        filesize = os.path.getsize(path)
        RL = 24
        PAGE_SIZE = RL * TimelineDataFile.MINUTES_IN_DAY
        daysNum = filesize // PAGE_SIZE
        if filesize % PAGE_SIZE != 0:
            return False
        f = open(path, 'rb')
        ok = True
        for i in range(daysNum):
            bs = f.read(RL)
            item = struct.unpack("2l4f", bs)
            if item[1] != 930:
                ok = False
                break
            f.seek(PAGE_SIZE - RL, 1)
        f.close()
        return ok

class KlineDataFile(datafile.K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    def loadLocalLastDay(self):
        path = self.getLocalPath('DAY')
        if not os.path.exists(path):
            return 0
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return 0
        RL = 32
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        item = struct.unpack('l5f2l', bs)
        return item[0]

class TimelineDataFileLoader:
    def __init__(self) -> None:
        self.codes = None
        self.newestDay = None

    def getCodes(self):
        if self.codes:
            return self.codes
        q = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        rs.sort()
        self.codes = rs
        return self.codes
    
    def getClsCodes(self):
        q = cls_orm.CLS_ZS.select(cls_orm.CLS_ZS.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        return rs
    
    def getThsCodes(self):
        q = ths_orm.THS_ZS.select(ths_orm.THS_ZS.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        return rs

    def _adjustMinutesData(self, rs : list):
        MINUTES_IN_DAY = 241
        idx = 0
        while idx < len(rs):
            first = rs[idx]
            if idx + MINUTES_IN_DAY >= len(rs):
                break
            last = rs[idx + MINUTES_IN_DAY - 1]
            if first.day != last.day:
                break
            idx += MINUTES_IN_DAY
        num = len(rs) - idx
        for i in range(num):
            rs.pop(-1)

    def download(self, code):
        try:
            dst = TimelineDataFile(code)
            lastDay = dst.loadLocalLastDay()
            if self.getNetNewestDay() and self.getNetNewestDay() <= lastDay:
                return True
            if len(code) == 6 and code[0] == '8': # ths zs
                hx = henxin.HexinUrl()
                datas = hx.loadUrlData( hx.getFenShiUrl(code))
            else:
                url = cls.ClsUrl()
                datas = url.loadHistory5FenShi(code)
            if datas and ('line' in datas):
                self.mergeMinlineFile(code, datas['line'])
        except Exception as e:
            # traceback.print_exc()
            print('Exception: download ', code, 'timeline')
            return False
        return True
    
    def _downloadList(self, codes, internalTime, tag):
        try:
            if not self.getNetNewestDay():
                return
            print(f'-----begin download militime-----[{tag}]---')
            st = datetime.datetime.now()
            st = st.strftime('%Y-%m-%d %H:%M')
            startTime = time.time()
            print('\t', st)
            x, y = console.getCursorPos()
            success, fail = 0, 0
            for c in codes:
                b = self.download(c)
                if b: success += 1
                else: fail += 1
                if not b:
                    x, y = console.getCursorPos()
                console.setCursorPos(x, y)
                diffTime = int(time.time() - startTime)
                h = diffTime // 3600
                m = diffTime % 3600 // 60
                s = diffTime % 60
                ut = f'{h}:{m :02d}:{s :02d}'
                print(f'\tLoading: {success} / {len(codes)}, fail = {fail},  {ut}')
                time.sleep(internalTime)
        except Exception as e:
            traceback.print_exc()
        print('-----end download--------\n')

    def downloadCodes(self, internalTime):
        self._downloadList(self.getCodes(), internalTime, 'Code')
    
    def downloadAllZs(self, internalTime):
        self._downloadList(self.getClsCodes(), internalTime, 'Cls ZS')
        self._downloadList(self.getThsCodes(), internalTime, 'Ths ZS')
        self._downloadList(['399001', '399006', '999999'], internalTime, 'SH & SZ ZS')
    
    def checkMinutes(self, md, fromIdx, endIdx):
        sum = 0
        for i in range(fromIdx, endIdx):
            sum += md[i].amount
        return sum > 0

    def mergeMinlineFile(self, code, minlineDatas):
        if not minlineDatas:
            return
        dst = TimelineDataFile(code)
        lastDay = dst.loadLocalLastDay()
        mode = 'ab' if lastDay > 0 else 'wb'
        f = open(dst.getLocalPath('TIME'), mode)
        arr = bytearray(24)
        i = 0
        while i < len(minlineDatas):
            d = minlineDatas[i]
            if d.day <= lastDay or d.time != 930:
                i += 1
                continue
            if i + TimelineDataFile.MINUTES_IN_DAY > len(minlineDatas):
                break
            td = minlineDatas[i + TimelineDataFile.MINUTES_IN_DAY - 1]
            if td.time != 1500:
                break
            if not self.checkMinutes(minlineDatas, i, i + TimelineDataFile.MINUTES_IN_DAY):
                break
            for j in range(TimelineDataFile.MINUTES_IN_DAY):
                d = minlineDatas[i + j]
                struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
                f.write(arr)
            i += TimelineDataFile.MINUTES_IN_DAY
        f.close()

    # only save data from [fromDay, endDay]
    def chunkMinlineFile(self, code, fromDay, endDay):
        df = TimelineDataFile(code)
        df.loadData(TimelineDataFile.FLAG_ALL)
        if not df.data:
            return
        minDay = df.data[0].day
        maxDay = df.data[-1].day
        if minDay >= fromDay and maxDay <= endDay:
            return
        f = open(df.getPath(), 'wb')
        arr = bytearray(24)
        for d in df.data:
            if d.day >= fromDay and d.day <= endDay:
                struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
                f.write(arr)
        f.close()

    def chunkAll(self, fromDay, endDay):
        codes = self.getCodes()
        for c in codes:
            self.chunkMinlineFile(c, fromDay, endDay)

    def writeToFile(self, df):
        f = open(df.getPath(), 'wb')
        arr = bytearray(24)
        for d in df.data:
            struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
            f.write(arr)
        f.close()

    def getNetNewestDay(self):
        if self.newestDay:
            return self.newestDay
        url = cls.ClsUrl()
        fs = url.loadHistory5FenShi('999999')
        if not fs or ('line' not in fs):
            return None
        datas = fs['line']
        if not datas:
            return None
        for i in range(len(datas) - 1, -1, -1):
            if datas[i].time == 1500:
                self.newestDay = datas[i].day
                return self.newestDay
        return None
    
    def getLocalNewestDay(self):
        df = TimelineDataFile('999999')
        return df.loadLocalLastDay()

    def checkDataFileValid(self):
        for code in self.codes:
            df = TimelineDataFile(code)
            if not df.isValidLocalFile():
                print('[checkDataFileValid] invalid file: ', code)

class KlineDataFileLoader:
    def __init__(self) -> None:
        self.codes = None
        self.newestDay = None

    def getCodes(self):
        if self.codes:
            return self.codes
        q = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        rs.sort()
        self.codes = rs
        return self.codes

    def download(self, code):
        try:
            dst = KlineDataFile(code)
            lastDay = dst.loadLocalLastDay()
            if self.getNetNewestDay() and self.getNetNewestDay() <= lastDay:
                return True
            if len(code) != 8: #
                hx = henxin.HexinUrl()
                datas = hx.loadUrlData( hx.getKLineUrl(code))
            else:
                url = cls.ClsUrl()
                datas = url.loadKline(code, 100)
            self.writeToFile(code, datas)
        except Exception as e:
            # traceback.print_exc()
            print('Exception: download ', code, 'kline')
            return False
        return True
    
    def writeToFile(self, code, klineDatas):
        dst = datafile.K_DataModel(code)
        f = open(dst.getLocalPath('DAY'), 'wb')
        arr = bytearray(32)
        for d in klineDatas:
            struct.pack_into('l5f2l', arr, 0, d.day, d.open, d.high, d.low, d.close, d.amount, int(d.vol / 10000), 0)
            f.write(arr)
        f.close()

    # only save data from [fromDay, endDay]
    def chunkDayFile(self, code, fromDay, endDay):
        df = KlineDataFile(code)
        df.loadLocalData()
        if not df.data:
            return
        minDay = df.data[0].day
        maxDay = df.data[-1].day
        if minDay >= fromDay and maxDay <= endDay:
            return
        f = open(df.getPath(), 'wb')
        arr = bytearray(32)
        for d in df.data:
            if d.day >= fromDay and d.day <= endDay:
                struct.pack_into('l5f2l', arr, 0, d.day, d.open, d.high, d.low, d.close, d.amount, d.vol, 0)
                f.write(arr)
        f.close()

    def getNetNewestDay(self):
        if self.newestDay:
            return self.newestDay
        url = cls.ClsUrl()
        fs = url.loadHistory5FenShi('999999')
        if not fs or ('line' not in fs):
            return None
        datas = fs['line']
        if not datas:
            return None
        for i in range(len(datas) - 1, -1, -1):
            if datas[i].time == 1500:
                self.newestDay = datas[i].day
                return self.newestDay
        return None
    
    def getLocalNewestDay(self):
        df = KlineDataFile('999999')
        return df.loadLocalLastDay()

    def downloadCodes(self, internalTime):
        self._downloadList(self.getCodes(), internalTime, 'Code')
        self._downloadList(['399001', '399006', '999999'], internalTime, 'SH & SZ Codes')

    def _downloadList(self, codes, internalTime, tag):
        try:
            if not self.getNetNewestDay():
                return
            print(f'-----begin download kline-----[{tag}]---')
            st = datetime.datetime.now()
            st = st.strftime('%Y-%m-%d %H:%M')
            startTime = time.time()
            print('\t', st)
            x, y = console.getCursorPos()
            success, fail = 0, 0
            for c in codes:
                b = self.download(c)
                if b: success += 1
                else: fail += 1
                if not b:
                    x, y = console.getCursorPos()
                console.setCursorPos(x, y)
                diffTime = int(time.time() - startTime)
                h = diffTime // 3600
                m = diffTime % 3600 // 60
                s = diffTime % 60
                ut = f'{h}:{m :02d}:{s :02d}'
                print(f'\tLoading: {success} / {len(codes)}, fail = {fail},  {ut}')
                time.sleep(internalTime)
        except Exception as e:
            traceback.print_exc()
        print('-----end download--------\n')

class Main:
    def __init__(self) -> None:
        self.cache = {} # day : True | False

    def acceptTime(self):
        now = datetime.datetime.now()
        ts = now.strftime('%H:%M')
        if ts > '15:00' and ts < '23:59':
            return True
        return False

    def downloadTLine(self):
        today = datetime.date.today()
        today = today.strftime("%Y-%m-%d")
        if self.cache.get(f'{today}-T', False):
            return True
        loader = TimelineDataFileLoader()
        lastDay = loader.getLocalNewestDay()
        newestDay = loader.getNetNewestDay()
        if not newestDay:
            return False
        if newestDay == lastDay:
            self.cache[f'{today}-T'] = True
            return True
        loader.downloadCodes(1)
        ld = fx.FenXiLoader()
        ld.fxAll(loader.newestDay)
        loader.downloadAllZs(1)
        return True

    def downloadKLine(self):
        today = datetime.date.today()
        today = today.strftime("%Y-%m-%d")
        if self.cache.get(f'{today}-K', False):
            return True
        loader = KlineDataFileLoader()
        lastDay = loader.getLocalNewestDay()
        newestDay = loader.getNetNewestDay()
        if not newestDay:
            return False
        if newestDay == lastDay:
            self.cache[f'{today}-K'] = True
            return True
        loader.downloadCodes(1)
        return True

    def run(self):
        while True:
            if not self.acceptTime():
                time.sleep(60 * 5)
                continue
            self.downloadKLine()
            self.downloadTLine()
            time.sleep(60 * 60 * 2)

if __name__ == '__main__':
    try:
        ld = KlineDataFileLoader()
        #ld._downloadList(['399001', '399006', '999999'], 0.1, 'AA')
        #ld._downloadList(['002131', '600050', '600157', '603005'], 0.1, 'BB')

        m = Main()
        m.run()
    except Exception as e:
        traceback.print_exc()
    os.system('pause')