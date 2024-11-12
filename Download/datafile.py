import os, sys, requests, json, traceback, datetime, struct, time

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

NET_BASE_PATH = r'D:\GP_Net_Data'
NET_LDAY_PATH = NET_BASE_PATH + '\\lday'
NET_MINLINE_PATH = NET_BASE_PATH + '\\minline'

if not os.path.exists(NET_LDAY_PATH):
    os.makedirs(NET_LDAY_PATH)
if not os.path.exists(NET_MINLINE_PATH):
    os.makedirs(NET_MINLINE_PATH)

class ItemData:
    DS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol') # vol(股), lbs(连板数), zdt(涨跌停), tdb(天地板，地天板) zhangFu(涨幅)
    MLS = ('day', 'time', 'open', 'high', 'low', 'close', 'amount', 'vol') # avgPrice 分时均价
    MLS2 = ('day', 'time', 'price', 'avgPrice', 'amount', 'vol')
    # MA5

    def __init__(self, *args):
        if not args:
            return
        if len(args) == len(self.DS):
            for i, k in enumerate(self.DS):
                setattr(self, k, args[i])
        elif len(args) == len(self.MLS):
            for i, k in enumerate(self.MLS):
                setattr(self, k, args[i])
        elif len(args) == len(self.MLS2):
            for i, k in enumerate(self.MLS2):
                setattr(self, k, args[i])
            #self.close = self.price

    def __repr__(self) -> str:
        ds = self.__dict__
        s = 'ItemData('
        for k in ds:
            s += f"{k}={str(ds[k])}, "
        s = s[0 : -2]
        s += ')'
        return s

class DataFile:
    MINUTES_IN_DAY = 241
    DT_DAY, DT_MINLINE = 1, 2
    FLAG_NEWEST, FLAG_OLDEST, FLAG_ALL = -1, -2, -3 # 最新、最早、全部
    cache = {}

    # @param dataType = DT_DAY  |  DT_MINLINE
    def __init__(self, code, dataType):
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.name = ''
        self.dataType = dataType
        self.data = []
        self.days = []

    # @param flag = FLAG_NEWEST | FLAG_OLDEST | FLAG_ALL
    def loadData(self, flag):
        key = f"{self.dataType}:{flag}"
        needLoad = None
        if (key in self.cache) and (self.code != self.cache[key].code):
            needLoad = True
        if key not in self.cache:
            needLoad = True
        if needLoad:
            path = self.getPath()
            if flag == DataFile.FLAG_NEWEST:
                self.data = self._loadDataFile_Newest(path)
            elif flag == DataFile.FLAG_OLDEST:
                self.data = self._loadDataFile_Oldest(path)
            elif flag == DataFile.FLAG_ALL:
                self.data = self._loadDataFile_All(path)
            self.calcDays()
            self.cache[key] = self
        else:
            obj = self.cache[key]
            self.data = obj.data[ : ]
            self.calcDays()

    @staticmethod
    def loadFromFile(filePath):
        name = os.path.basename(filePath)
        code = name[0 : 6]
        dataType = DataFile.DT_DAY if name[-4 : ] == '.day' else DataFile.DT_MINLINE
        df = DataFile(code, dataType)
        df.data = df._loadDataFile_All(filePath)
        df.calcDays()
        return df

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
        if self.dataType == DataFile.DT_DAY:
            bp = os.path.join(NET_LDAY_PATH, f'{code}.day')
        else:
            bp = os.path.join(NET_MINLINE_PATH, f'{code}.lc1')
        return bp

    def _loadDataFile_All(self, path):
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        RL = 32 if self.dataType == self.DT_DAY else 24
        while f.readable():
            bs = f.read(RL)
            if len(bs) != RL:
                break
            if self.dataType == self.DT_DAY:
                item = struct.unpack('l5f2l', bs)
                item = ItemData(*item[0 : -1])
            else:
                item = struct.unpack('2l4f', bs)
                item = ItemData(*item)
            rs.append(item)
        f.close()
        # check minute line number
        if self.dataType == self.DT_MINLINE and (len(rs) % self.MINUTES_IN_DAY) != 0:
            raise Exception('Minute Line number error:', len(rs))
        return rs
    
    def _loadDataFile_Newest(self, path):
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return rs
        RL = 32 if self.dataType == self.DT_DAY else 24
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        if self.dataType == self.DT_DAY:
            item = struct.unpack('l5f2l', bs)
            item = ItemData(*item[0 : -1])
        else:
            item = struct.unpack('2l4f', bs)
            item = ItemData(*item)
        rs.append(item)
        f.close()
        return rs
    
    def _loadDataFile_Oldest(self, path):
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return rs
        RL = 32 if self.dataType == self.DT_DAY else 24
        bs = f.read(RL)
        if self.dataType == self.DT_DAY:
            item = struct.unpack('l5f2l', bs)
            item = ItemData(*item[0 : -1])
        else:
            item = struct.unpack('2l4f', bs)
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
            d.avgPrice = sumamount / sumVol * 100
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
            for i in range(1, len(self.data) // self.MINUTES_IN_DAY):
                pre = self.data[i * self.MINUTES_IN_DAY - 1].price
                lc = 0
                for j in range(0, self.MINUTES_IN_DAY):
                    cur = self.data[i * self.MINUTES_IN_DAY + j]
                    if lc != cur.price:
                        self._calcZDTInfo(pre, cur)
                    lc = cur.price

    #计算涨幅
    def calcZhangFu(self):
        if self.dataType != self.DT_DAY:
            return
        if not self.data:
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

class DataFileLoader:
    def __init__(self) -> None:
        self.codes = None

    def _getCodes(self):
        if self.codes:
            return self.codes
        from orm import ths_orm
        q = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        rs.sort()
        rs.append('999999') # 上证指数
        rs.append('399001')
        rs.append('399006')
        self.codes = rs
        return self.codes

    def getLastCode(self):
        return '399006'

    def _adjustMinutesData(self, rs : list):
        MINUTES_IN_DAY = DataFile.MINUTES_IN_DAY
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

    def mergeMililine(self, code):
        try:
            from Download import cls
            url = cls.ClsUrl()
            datas = url.loadHistory5FenShi(code)
            self.mergeMinlineFile(code, datas['line'])
        except Exception as e:
            traceback.print_exc()
            return False
        return True

    def mergeAllMililine(self, internalTime = 2):
        try:
            from Download import console
            print(f'-----begin download militime--------')
            st = datetime.datetime.now()
            st = st.strftime('%Y-%m-%d %H:%M')
            print(st)
            x, y = console.getCursorPos()
            success, fail = 0, 0
            for c in self._getCodes():
                b = self.mergeMililine(c)
                if b: success += 1
                else: fail += 1
                console.setCursorPos(x, y)
                print(f'Loading: {success} / {len(self._getCodes())}, fail = {fail}')
                time.sleep(internalTime)
        except Exception as e:
            traceback.print_exc()
        print('-----end download--------\n')

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

    def mergeMinlineFile(self, code, minlineDatas):
        if len(minlineDatas) % DataFile.MINUTES_IN_DAY != 0:
            return False
        ph = os.path.join(NET_MINLINE_PATH,f'{code}.lc1')
        dst = DataFile(code, DataFile.DT_MINLINE)
        dst.loadData(DataFile.FLAG_NEWEST)
        f = open(ph, 'ab')
        lastDay = 0
        if dst.data:
            lastDay = dst.data[-1].day
        arr = bytearray(24)
        for d in minlineDatas:
            if d['day'] > lastDay:
                struct.pack_into('2l4f', arr, 0, d['day'], d['time'], d['price'], d['avgPrice'], d['amount'], d['vol'])
                f.write(arr)
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
        df = DataFile(code, DataFile.DT_MINLINE)
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
        codes = self._getCodes()
        for c in codes:
            self.chunkDayFile(c, fromDay, endDay)
            self.chunkMinlineFile(c, fromDay, endDay)

def merge_old(code):
    import tdx_datafile
    print('Load', code, end = '')
    newDf = DataFile(code, DataFile.DT_MINLINE)
    newDf.loadData(DataFile.FLAG_ALL)
    oldDf = tdx_datafile.DataFile(code, DataFile.DT_MINLINE)
    oldDf.loadData(tdx_datafile.DataFile.FLAG_ALL)
    if not oldDf.data:
        print(' --> No old data')
        return True
    for d in oldDf.days:
        oldDf.calcAvgPriceOfDay(d)
    if len(oldDf.data) % 240 != 0:
        print(' --> Error data')
        return False
    ph = os.path.join(NET_MINLINE_PATH, f'{code}.lc1')
    
    firstDay = 0
    if newDf.data:
        firstDay = newDf.data[0].day
    if firstDay <= oldDf.data[0].day:
        print(' --> No Need')
        return True
    f = open(ph, 'wb')
    arr = bytearray(24)
    for d in oldDf.data:
        if d.day >= firstDay:
            break
        if d.time == 931:
            struct.pack_into('2l4f', arr, 0, d.day, 930, d.close, d.avgPrice, 0, 0)
            f.write(arr)
        struct.pack_into('2l4f', arr, 0, d.day, d.time, d.close, d.avgPrice, d.amount, d.vol)
        f.write(arr)
    for d in newDf.data:
        struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
        f.write(arr)
    f.close()
    print(' --> Success')
    return True

def merge_old_all():
    lodler = DataFileLoader()
    #lodler.mergeAllMililine(0.5)
    codes = lodler._getCodes()
    for c in codes:
        merge_old(c)

if __name__ == '__main__':
    #lodler = DataFileLoader()
    #lodler.mergeAllMililine(0.5)
    #merge_old_all()
    pass