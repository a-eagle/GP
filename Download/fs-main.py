import re, sys, datetime, traceback
import time, os, platform, sys, struct

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import datafile, cls, henxin, console
from orm import ths_orm, cls_orm
from ui import fx

def acceptTime():
    now = datetime.datetime.now()
    ts = now.strftime('%H:%M')
    if ts > '15:00' and ts < '23:59':
        return True
    return False

class DataFile(datafile.DataModel):
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
        PAGE_SIZE = RL * DataFile.MINUTES_IN_DAY
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
        print(days)
        return days

    def isValidLocalFile(self):
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return True
        filesize = os.path.getsize(path)
        RL = 24
        PAGE_SIZE = RL * DataFile.MINUTES_IN_DAY
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

class DataFileLoader:
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

    def downloadAndMergeMililine(self, code):
        try:
            dst = DataFile(code)
            lastDay = dst.loadLocalLastDay()
            if self.newestDay and self.newestDay <= lastDay:
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
            traceback.print_exc()
            print('Exception: ', code)
            return False
        return True

    def _downloadAndMergeAllMililine(self, codes, internalTime, tag):
        try:
            self.newestDay = self.getNetNewestDay()
            if not self.newestDay:
                return
            print(f'-----begin download militime-----[{tag}]---')
            st = datetime.datetime.now()
            st = st.strftime('%Y-%m-%d %H:%M')
            startTime = time.time()
            print(st)
            x, y = console.getCursorPos()
            success, fail = 0, 0
            for c in codes:
                b = self.downloadAndMergeMililine(c)
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
                print(f'Loading: {success} / {len(codes)}, fail = {fail},  {ut}')
                time.sleep(internalTime)
        except Exception as e:
            traceback.print_exc()
        print('-----end download--------\n')

    def downloadAndMergeCodesMililine(self, internalTime):
        self._downloadAndMergeAllMililine(self.getCodes(), internalTime, 'Code')
    
    def downloadAndMergeAllZsMililine(self, internalTime):
        self._downloadAndMergeAllMililine(self.getClsCodes(), internalTime, 'Cls ZS')
        self._downloadAndMergeAllMililine(self.getThsCodes(), internalTime, 'Ths ZS')
        self._downloadAndMergeAllMililine(['399001', '399006', '999999'], internalTime, 'SH & SZ ZS')

    def mergeDayFile(self, code, klineDatas):
        ph = os.path.join(NET_LDAY_PATH, f'{code}.day')
        dst = DataFile(code, DataFile.DT_DAY)
        dst.loadData(DataFile.FLAG_NEWEST)
        f = open(ph, 'ab')
        lastDay = 0
        if dst.data:
            lastDay = dst.data[-1].day
        arr = bytearray(32)
        for d in klineDatas:
            if d.day > lastDay:
                struct.pack_into('l5f2l', arr, 0, d['day'], d['open'], d['high'], d['low'], d.close, d.amount, d.vol, 0)
                f.write(arr)
        f.close()
        return True
    
    def checkMinutes(self, md, fromIdx, endIdx):
        sum = 0
        for i in range(fromIdx, endIdx):
            sum += md[i].amount
        return sum > 0

    def mergeMinlineFile(self, code, minlineDatas):
        if not minlineDatas:
            return
        dst = DataFile(code)
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
            if i + DataFile.MINUTES_IN_DAY > len(minlineDatas):
                break
            td = minlineDatas[i + DataFile.MINUTES_IN_DAY - 1]
            if td.time != 1500:
                break
            if not self.checkMinutes(minlineDatas, i, i + DataFile.MINUTES_IN_DAY):
                break
            for j in range(DataFile.MINUTES_IN_DAY):
                d = minlineDatas[i + j]
                struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
                f.write(arr)
            i += DataFile.MINUTES_IN_DAY
        f.close()

    # only save data from [fromDay, endDay]
    def chunkDayFile(self, code, fromDay, endDay):
        df = DataFile(code, DataFile.DT_DAY)
        df.loadData(DataFile.FLAG_ALL)
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

    # only save data from [fromDay, endDay]
    def chunkMinlineFile(self, code, fromDay, endDay):
        df = DataFile(code)
        df.loadData(DataFile.FLAG_ALL)
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
            self.chunkDayFile(c, fromDay, endDay)
            self.chunkMinlineFile(c, fromDay, endDay)

    def writeToFile(self, df):
        f = open(df.getPath(), 'wb')
        arr = bytearray(24)
        for d in df.data:
            struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
            f.write(arr)
        f.close()

    def getNetNewestDay(self):
        url = cls.ClsUrl()
        fs = url.loadHistory5FenShi('999999')
        if not fs or ('line' not in fs):
            return None
        datas = fs['line']
        if not datas:
            return None
        for i in range(len(datas) - 1, -1, -1):
            if datas[i].time == 1500:
                return datas[i].day
        return None
    
    def getLocalNewestDay(self):
        df = DataFile('999999')
        return df.loadLocalLastDay()

    def checkDataFileValid():
        loader = DataFileLoader()
        cs = loader.getCodes()
        for code in cs:
            df = DataFile(code)
            if not df.isValidLocalFile():
                print('[checkDataFileValid] invalid file: ', code)

def main():
    # df = DataFile('000002')
    # df.getLocalDays()
    
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
        loader = DataFileLoader()
        lastDay = loader.getLocalNewestDay()
        newestDay = loader.getNetNewestDay()
        if not newestDay:
            time.sleep(60 * 5)
            continue
        if newestDay == lastDay:
            cache[today] = True
            time.sleep(60 * 5)
            continue
        loader.downloadAndMergeCodesMililine(0.1)
        ld = fx.FenXiLoader()
        ld.fxAll(loader.newestDay)
        loader.downloadAndMergeAllZsMililine(0.1)

if __name__ == '__main__':
    # ld = fx.FenXiLoader()
    # ld.fxAll(20250407)
    try:
        main()
    except Exception as e:
        traceback.print_exc()
    os.system('pause')