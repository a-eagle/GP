import os, struct, platform
from collections import namedtuple

VIPDOC_BASE_PATH = r'D:\Program Files\new_tdx2\vipdoc'

class ItemData:
    DS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol') # vol(股), lbs(连板数), zdt(涨跌停), tdb(天地板，地天板) zhangFu(涨幅)
    MLS = ('day', 'time', 'open', 'high', 'low', 'close', 'amount', 'vol') # avgPrice 分时均价
    # MA5

    def __init__(self, *args):
        if not args:
            return
        a = self.DS if len(args) == len(self.DS) else self.MLS
        for i, k in enumerate(a):
            setattr(self, k, args[i])

    def __repr__(self) -> str:
        ds = self.__dict__
        s = 'ItemData('
        for k in ds:
            s += f"{k}={str(ds[k])}, "
        s = s[0 : -2]
        s += ')'
        return s

class DataFile:
    DT_DAY, DT_MINLINE = 1, 2
    FLAG_NEWEST, FLAG_OLDEST, FLAG_ALL = -1, -2, -3 # 最新、最早、全部

    # @param dataType = DT_DAY  |  DT_MINLINE
    # @param flag = FLAG_NEWEST | FLAG_OLDEST | FLAG_ALL
    def __init__(self, code, dataType, flag = -3):
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.dataType = dataType
        path = self.getPath()
        if flag == DataFile.FLAG_NEWEST:
            self.data = self._loadDataFile_Newest(path)
        elif flag == DataFile.FLAG_OLDEST:
            self.data = self._loadDataFile_Oldest(path)
        else:
            self.data = self._loadDataFile_All(path)
        self.days = []
        self.calcDays()
        self.name = ''

    @staticmethod
    def loadFromFile(filePath):
        name = os.path.basename(filePath)
        if name[0 : 2] in ('sh', 'sz'):
            code = name[2 : 8]
        elif name[0 : 3] == 'ths':
            code = name[3 : 9]
        dataType = DataFile.DT_DAY if name[-4 : ] == '.day' else DataFile.DT_MINLINE
        datafile = DataFile('000000', dataType, DataFile.FLAG_ALL)
        datafile.code = code
        datafile.data = datafile._loadDataFile_All(filePath)
        return datafile

    def getItemIdx(self, day):
        if not self.data:
            return -1
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        left, right = 0, len(self.data) - 1
        idx = -1
        while left <= right:
            mid = (left + right) // 2
            d = self.data[mid]
            if d.day == day:
                idx = mid
                break
            elif day > d.day:
                left = mid + 1
            else:
                right = mid - 1
        if idx == -1:
            return -1
        if self.dataType == self.DT_DAY:
            return idx
        t = self.data[idx].day
        while idx > 0:
            if self.data[idx - 1].day == t:
                idx -= 1
            else:
                break
        return idx

    def getItemData(self, day):
        idx = self.getItemIdx(day)
        if idx < 0:
            return None
        return self.data[idx]

    def getPath(self):
        code = self.code
        tag = '' 
        if code[0] == '6' or code[0] == '9': tag = 'sh'
        elif code[0] == '3' or code[0] == '0': tag = 'sz'
        elif code[0] == '8': tag = 'ths'
        if self.dataType == DataFile.DT_DAY:
            dm = '__lday' if tag in ('sh', 'sz') else '__ths_lday'
            bp = os.path.join(VIPDOC_BASE_PATH, dm, f'{tag}{code}.day')
        else:
            dm = '__minline' if tag in ('sh', 'sz') else '__ths_minline'
            bp = os.path.join(VIPDOC_BASE_PATH, dm, f'{tag}{code}.lc1')
        #if os.path.exists(bp):
        return bp

    def _loadDataFile_All(self, path):
        def T(fv): return  fv # int(fv * 100 + 0.5)
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            if self.dataType == self.DT_DAY:
                item = struct.unpack('l5f2l', bs)
                item = ItemData(*item[0 : -1])
            else:
                item = struct.unpack('2l5fl', bs)
                item = ItemData(*item)
            rs.append(item)
        f.close()
        # check minute line number
        if self.dataType == self.DT_MINLINE and (len(rs) % 240) != 0:
            raise Exception('Minute Line number error:', len(rs))
        return rs
    
    def _loadDataFile_Newest(self, path):
        def T(fv): return  fv # int(fv * 100 + 0.5)
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return rs
        n = f.seek(-32, 2)
        bs = f.read(32)
        if self.dataType == self.DT_DAY:
            item = struct.unpack('l5f2l', bs)
            item = ItemData(*item[0 : -1])
        else:
            item = struct.unpack('2l5fl', bs)
            item = ItemData(*item)
        rs.append(item)
        f.close()
        return rs
    
    def _loadDataFile_Oldest(self, path):
        def T(fv): return  fv # int(fv * 100 + 0.5)
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return rs
        bs = f.read(32)
        if self.dataType == self.DT_DAY:
            item = struct.unpack('l5f2l', bs)
            item = ItemData(*item[0 : -1])
        else:
            item = struct.unpack('2l5fl', bs)
            item = ItemData(*item)
        rs.append(item)
        f.close()
        return rs

    def calcDays(self):
        self.days.clear()
        if not self.data:
            return
        for d in self.data:
            if not self.days:
                self.days.append(d.day)
            elif self.days[-1] != d.day:
                self.days.append(d.day)

    # 分时均线
    def calcAvgPriceOfDay(self, day):
        if not self.data or len(self.data) == 0:
            return 0
        if self.dataType != self.DT_MINLINE:
            return 0
        fromIdx = self.getItemIdx(day)
        if fromIdx < 0:
            return 0
        idx = fromIdx
        sumamount, sumVol = 0, 0
        while idx < len(self.data) and self.data[idx].day == day:
            d = self.data[idx]
            sumamount += d.amount
            sumVol += d.vol
            d.avgPrice = int(sumamount / sumVol * 100 + 0.5)
            idx += 1

    def calcMA(self, N):
        name = 'MA' + str(N)
        for i in range(N - 1, len(self.data)):
            ap = 0
            for j in range(i + 1 - N, i + 1):
                ap += self.data[j].close
            setattr(self.data[i], name, ap / N)
    
    def calcMA_Amount(self, N):
        name = 'MA_Amount' + str(N)
        for i in range(N - 1, len(self.data)):
            ap = 0
            for j in range(i + 1 - N, i + 1):
                ap += self.data[j].amount
            setattr(self.data[i], name, ap / N)

    def calcMA_Vol(self, N):
        name = 'MA_Vol' + str(N)
        for i in range(N - 1, len(self.data)):
            ap = 0
            for j in range(i + 1 - N, i + 1):
                ap += self.data[j].vol
            setattr(self.data[i], name, ap / N)
    
    def _calcZDTInfo(self, pre, c):
        is20p = (self.code[0:3] == '688') or (self.code[0:2] == '30')
        is20p = is20p and c.day >= 20200824
        ZT = 20 if is20p else 10
        iszt = int(pre * (100 + ZT) + 0.5) <= int(c.close * 100 + 0.5)
        isztzb = int(pre * (100 + ZT) + 0.5) <= int(c.high * 100 + 0.5) and (c.high != c.close)
        isdt = int(pre * (100 - ZT) + 0.5) >= int(c.close * 100 + 0.5)
        isdtzb = int(pre * (100 - ZT) + 0.5) >= int(c.low * 100 + 0.5) and (c.low != c.close)
        if isztzb: c.zdt = 'ZTZB'
        if isdtzb: c.zdt = 'DTZB'
        if iszt: c.zdt = 'ZT'
        if isdt: c.zdt = 'DT'
        if (isztzb or iszt) and (isdt or isdtzb):
            c.tdb = True

    # 计算涨跌停信息
    def calcZDT(self):
        if self.dataType == self.DT_DAY:
            for i in range(1, len(self.data)):
                self._calcZDTInfo(self.data[i - 1].close, self.data[i])
                if getattr(self.data[i], 'zdt', '') == 'ZT':
                    nowLbs = getattr(self.data[i - 1], 'lbs', 0)
                    self.data[i].lbs = nowLbs + 1
        else:
            ONE_DAY_NUM = 240
            for i in range(1, len(self.data) // ONE_DAY_NUM):
                pre = self.data[i * ONE_DAY_NUM - 1].close
                lc = 0
                for j in range(0, ONE_DAY_NUM):
                    cur = self.data[i * ONE_DAY_NUM + j]
                    if lc != cur.close:
                        self._calcZDTInfo(pre, cur)
                    lc = cur.close

    #计算涨幅
    def calcZhangFu(self):
        if self.dataType != self.DT_DAY:
            return
        for i in range(1, len(self.data)):
            pc = self.data[i - 1].close
            cc = self.data[i].close
            if pc == 0:
                zhangFu = 0
            else:
                zhangFu = (cc - pc) / pc * 100
            setattr(self.data[i], 'zhangFu', zhangFu)

    # 获得涨停板
    # param includeZTZB  是否含涨停炸板
    def getItemsByZT(self, includeZTZB : bool):
        rs = []
        for d in self.data:
            if getattr(d, 'zdt', None) == 'ZT':
                rs.append(d)
            if includeZTZB and getattr(d, 'zdt', None) == 'ZTZB':
                rs.append(d)
        return rs

class DataFileUtils:

    # 所有股标代码（上证、深证股），不含指数、北证股票
    # @return list[code, ...]
    @staticmethod
    def listAllCodes():
        allDirs = []
        for tag in ('sh', 'sz'):
            sh = os.path.join(VIPDOC_BASE_PATH, tag)
            for ld in os.listdir(sh):
                if 'lday' in ld:
                    allDirs.append(os.path.join(sh, ld))
        rs = set()
        for d in allDirs:
            codes = os.listdir(d)
            rt = [c[2:8] for c in codes if (c[2] == '6' or c[2] == '0' or c[2] == '3') and (c[2:5] != '399')]
            rs = rs.union(rt)
        rs = sorted(rs, reverse=True)
        return rs
    
    # 计算fromDay开始的所有交易日期
    # @return list[day, ...]
    @staticmethod
    def calcDays(fromDay, inclueFromDay = False):
        df = DataFile('999999', DataFile.DT_DAY, DataFile.FLAG_ALL)
        days = []
        for i in range(len(df.data)):
            if inclueFromDay and df.data[i].day == fromDay:
                days.append(df.data[i].day)
            if df.data[i].day > fromDay:
                days.append(df.data[i].day)
        return days

class DataFileLoader:
    def __init__(self) -> None:
        pass

    def _loadTdxDataFile(self, path):
        def T(fv): return fv # int(fv * 100 + 0.5)
        rs = []
        if not os.path.exists(path):
            return rs
        dataType = DataFile.DT_DAY if 'lday' in path else DataFile.DT_MINLINE
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            if dataType == DataFile.DT_DAY:
                item = struct.unpack('5lf2l', bs)
                item = ItemData(*item[0 : -1])
            else:
                item = struct.unpack('2H5f2l', bs)
                d0 = item[0]
                y = (int(d0 / 2048) + 2004)
                m = int((d0 % 2048 ) / 100)
                r = (d0 % 2048) % 100
                d0 = y * 10000 + m * 100 + r
                d1 = (item[1] // 60) * 100 + (item[1] % 60)
                item = ItemData(d0, d1, T(item[2]), T(item[3]), T(item[4]), T(item[5]), item[6], item[7])
                #item._time = item[1]
            rs.append(item)
        f.close()
        # check minute line number
        if dataType == DataFile.DT_MINLINE and (len(rs) % 240) != 0:
            raise Exception('Minute Line number error:', len(rs))
        return rs

    def mergeAll(self):
        codes = DataFileUtils.listAllCodes()
        codes.append('999999')
        codes.append('399001')
        codes.append('399006')
        for c in codes:
            self.mergeDayFile(c)
            self.mergeMinlineFile(c)

    def mergeDayFile(self, code):
        tag = 'sh' if code[0] == '6' or code[0] == '8' or code[0] == '9' else 'sz'
        ph = os.path.join(VIPDOC_BASE_PATH, tag, 'lday', f'{tag}{code}.day')
        src = self._loadTdxDataFile(ph)
        if not src:
            return
        pph = os.path.join(VIPDOC_BASE_PATH, '__lday')
        if not os.path.exists(pph):
            os.mkdir(pph)
        dst = DataFile(code, DataFile.DT_DAY, DataFile.FLAG_ALL)
        ph = os.path.join(pph, f'{tag}{code}.day')
        f = open(ph, 'ab')
        lastDay = 0
        if dst.data:
            lastDay = dst.data[-1].day
        arr = bytearray(32)
        for d in src:
            if d.day > lastDay:
                struct.pack_into('l5f2l', arr, 0, d.day, d.open / 100, d.high / 100, d.low / 100, d.close / 100, d.amount, d.vol, 0)
                f.write(arr)
        f.close()

    def mergeMinlineFile(self, code):
        tag = 'sh' if code[0] == '6' or code[0] == '8' or code[0] == '9' else 'sz'
        ph = os.path.join(VIPDOC_BASE_PATH, tag, 'minline', f'{tag}{code}.lc1')
        src = self._loadTdxDataFile(ph)
        if not src:
            return
        pph = os.path.join(VIPDOC_BASE_PATH, '__minline')
        if not os.path.exists(pph):
            os.mkdir(pph)
        dst = DataFile(code, DataFile.DT_MINLINE, DataFile.FLAG_ALL)
        ph = os.path.join(pph, f'{tag}{code}.lc1')
        f = open(ph, 'ab')
        lastDay = 0
        if dst.data:
            lastDay = dst.data[-1].day
        arr = bytearray(32)
        for d in src:
            if d.day > lastDay:
                struct.pack_into('2l5fl', arr, 0, d.day, d.time, d.open, d.high, d.low, d.close, d.amount, d.vol)
                f.write(arr)
        f.close()

    # only save data from [fromDay, endDay]
    def chunkDayFile(self, code, fromDay, endDay):
        df = DataFile(code, DataFile.DT_DAY, DataFile.FLAG_ALL)
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
        df = DataFile(code, DataFile.DT_MINLINE, DataFile.FLAG_ALL)
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
                struct.pack_into('2l5fl', arr, 0, d.day, d.time, d.open, d.high, d.low, d.close, d.amount, d.vol)
                f.write(arr)
        f.close()

    def chunkAll(self, fromDay, endDay):
        codes = DataFileUtils.listAllCodes()
        codes.append('999999')
        codes.append('399001')
        codes.append('399006')
        for c in codes:
            self.chunkDayFile(c, fromDay, endDay)
            self.chunkMinlineFile(c, fromDay, endDay)

if __name__ == '__main__':
    ld = DataFileLoader()
    #ld.mergeDayFile('999999')
    df = DataFile('999999', DataFile.DT_DAY)
    df.calcDays()
    #ld.mergeAll()
    #df = DataFile('999999', DataFile.DT_MINLINE, DataFile.FLAG_ALL)
    #ld.chunkAll(20240301, 20240430)
    rs = ld._loadTdxDataFile(r'D:\Program Files\new_tdx2\vipdoc\sz\minline\sz000001.lc1')
    df = DataFile('000000', DataFile.DT_MINLINE)
    df.data = rs
    df.calcDays()
    pass
    