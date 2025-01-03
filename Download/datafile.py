import os, sys, requests, json, traceback, datetime, struct, time

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

NET_BASE_PATH = r'D:\GP_Net_Data'
NET_LDAY_PATH = NET_BASE_PATH + '\\lday'
NET_MINLINE_PATH = NET_BASE_PATH + '\\minline'
NET_CLS_MINLINE_PATH = NET_BASE_PATH + '\\cls-minline'
NET_THS_MINLINE_PATH = NET_BASE_PATH + '\\ths-minline'

for d in (NET_LDAY_PATH, NET_MINLINE_PATH, NET_CLS_MINLINE_PATH, NET_THS_MINLINE_PATH):
    if not os.path.exists(d):
        os.makedirs(d)

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
    FLAG_NEWEST, FLAG_OLDEST, FLAG_ALL, FLAG_NEWEST_DAYS = -1, -2, -3, -4 # 最新、最早、全部、最近几日
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
            if self.isValidFileData() == False:
                raise Exception(f'Exception: invalide data file {self.code}')
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

    # day = str | int | date
    def loadDataByDay(self, day):
        if not day:
            return
        if isinstance(day, datetime.date):
            day = int(day.strftime('%Y%m%d'))
        elif isinstance(day, str):
            day = int(day.replace('-', ''))
        if not isinstance(day, int):
            return
        path = self.getPath()
        rs = []
        if not os.path.exists(path):
            return
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return
        if self.isValidFileData() == False:
            raise Exception(f'Exception: invalide data file {self.code}')
        if self.dataType == self.DT_DAY:
            RL = 32
            # TODO
            pass
        elif self.dataType == self.DT_MINLINE:
            RL = 24
            numDays = filesize // (RL * self.MINUTES_IN_DAY)
            PAGE_SIZE = self.MINUTES_IN_DAY * RL
            for i in range(numDays):
                f.seek(-RL - PAGE_SIZE * i , 2)
                bs = f.read(RL)
                cday, *_ = struct.unpack('2l4f', bs)
                if cday < day:
                    break
                if cday == day:
                    if i != numDays - 1:
                        i += 1
                        break
            rd = min(i + 1, numDays)
            pos = rd * PAGE_SIZE
            f.seek(- pos, 2)
            for j in range(min(rd, 2) * self.MINUTES_IN_DAY):
                bs = f.read(RL)
                items = struct.unpack('2l4f', bs)
                v = ItemData(*items)
                rs.append(v)
        f.close()
        self.data = rs
        self.calcDays()

    # flag is only FLAG_NEWEST_DAYS
    def loadDataOfDays(self, daysNum, flag = -4):
        path = self.getPath()
        if flag == self.FLAG_NEWEST_DAYS:
            self.data = self._loadNewstDataOfDays(path, daysNum)
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
        if code[0 : 3] == 'cls': # cls zs
            if self.dataType == DataFile.DT_DAY:
                bp = os.path.join(NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(NET_CLS_MINLINE_PATH, f'{code}.lc1')
        elif code[0] == '8': # ths zs
            if self.dataType == DataFile.DT_DAY:
                bp = os.path.join(NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(NET_THS_MINLINE_PATH, f'{code}.lc1')
        else: # GP
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
    
    def _loadNewstDataOfDays(self, path, daysNum = 1):
        rs = []
        if not os.path.exists(path):
            return rs
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return rs
        if self.dataType == self.DT_DAY:
            RL = 32
            maxDays = filesize // RL
            if daysNum > maxDays:
                daysNum = maxDays
            n = f.seek(-RL * daysNum, 2)
            for i in range(daysNum):
                bs = f.read(RL)
                item = struct.unpack('l5f2l', bs)
                item = ItemData(*item[0 : -1])
                rs.append(item)
        elif self.dataType == self.DT_MINLINE:
            RL = 24
            maxDays = filesize // (RL * self.MINUTES_IN_DAY)
            if daysNum > maxDays:
                daysNum = maxDays
            n = f.seek(-RL * daysNum * self.MINUTES_IN_DAY, 2)
            for i in range(daysNum * self.MINUTES_IN_DAY):
                bs = f.read(RL)
                item = struct.unpack('2l4f', bs)
                item = ItemData(*item)
                rs.append(item)
        f.close()
        return rs

    # True | False | None(no data file)
    def isValidFileData(self):
        path = self.getPath()
        if not os.path.exists(path):
            return None
        # check size valid
        if self.dataType == self.DT_DAY:
            RL = 32
        else:
            RL = 24 * self.MINUTES_IN_DAY
        filesize = os.path.getsize(path)
        return filesize % RL == 0

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
        if self.dataType == self.DT_DAY:
            for d in self.data:
                if not self.days:
                    self.days.append(d.day)
                elif self.days[-1] != d.day:
                    self.days.append(d.day)
        elif self.dataType == self.DT_MINLINE:
            for i in range(0, len(self.data), self.MINUTES_IN_DAY):
                curDay = self.data[i].day
                if not self.days:
                    self.days.append(curDay)
                elif self.days[-1] != curDay:
                    self.days.append(curDay)

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
            if sumVol > 0:
                d.avgPrice = sumamount / sumVol
            else:
                d.avgPrice = d.price
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
        self.newestDay = None

    def getCodes(self):
        if self.codes:
            return self.codes
        from orm import ths_orm
        q = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        rs.sort()
        rs.insert(0, '999999') # 上证指数
        rs.append('399001')
        rs.append('399006')
        self.codes = rs
        return self.codes
    
    def getClsCodes(self):
        from orm import cls_orm
        q = cls_orm.CLS_ZS.select(cls_orm.CLS_ZS.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        return rs
    
    def getThsCodes(self):
        from orm import ths_orm
        q = ths_orm.THS_ZS.select(ths_orm.THS_ZS.code).tuples()
        rs = []
        for t in q:
            rs.append(t[0])
        return rs

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

    def downloadAndMergeMililine(self, code):
        try:
            from Download import cls, henxin
            dst = DataFile(code, DataFile.DT_MINLINE)
            dst.loadData(DataFile.FLAG_NEWEST)
            if dst.data:
                lastDay = dst.data[-1].day
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
            print('DataFile exception: ', code)
            return False
        return True

    def _downloadAndMergeAllMililine(self, codes, internalTime, tag):
        try:
            from Download import console
            self.newestDay = self.getNetNewestDay()
            if not self.newestDay:
                return
            print(f'-----begin download militime-----{tag}---')
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

    def downloadAndMergeAllMililine(self, internalTime):
        self._downloadAndMergeAllMililine(self.getCodes(), internalTime, '')
        self._downloadAndMergeAllMililine(self.getClsCodes(), internalTime, 'Cls ZS')
        self._downloadAndMergeAllMililine(self.getThsCodes(), internalTime, 'Ths ZS')

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
        dst = DataFile(code, DataFile.DT_MINLINE)
        dst.loadData(DataFile.FLAG_NEWEST)
        f = open(dst.getPath(), 'ab')
        lastDay = 0
        if dst.data:
            lastDay = dst.data[-1].day
        arr = bytearray(24)
        for i, d in enumerate(minlineDatas):
            if d.day <= lastDay:
                continue
            if d.time == 930:
                if i + DataFile.MINUTES_IN_DAY > len(minlineDatas):
                    break
                td = minlineDatas[i + DataFile.MINUTES_IN_DAY - 1]
                if td.time != 1500:
                    break
                if not self.checkMinutes(minlineDatas, i, i + DataFile.MINUTES_IN_DAY):
                    break
            struct.pack_into('2l4f', arr, 0, d.day, d.time, d.price, d.avgPrice, d.amount, d.vol)
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
        from Download import cls
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
        df = DataFile('999999', DataFile.DT_MINLINE)
        df.loadData(DataFile.FLAG_NEWEST)
        lastDay = 0
        if df.data:
            lastDay = df.data[-1].day
        return lastDay

def merge_tdx(code):
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
        if d.avgPrice > d.close * 20:
            d.avgPrice /= 100
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

def merge_tdx_all():
    lodler = DataFileLoader()
    #lodler.mergeAllMililine(0.5)
    codes = lodler.getCodes()
    for c in codes:
        merge_tdx(c)

if __name__ == '__main__':
    df = DataFile('300843', DataFile.DT_MINLINE)
    df.loadDataByDay(20241221)
    print(df.days)

    ld = DataFileLoader()
    ld._downloadAndMergeAllMililine(ld.getThsCodes(), 0.5, 'Ths ZS')
    #ld.downloadAndMergeAllMililine(0.5)
    #ld.downloadAndMergeMililine('300420')
    #ld.chunkMinlineFile('300420', 20240301, 20241206)
    #df = DataFile('300420', DataFile.DT_MINLINE)
    #df.loadData(DataFile.FLAG_ALL)
    #print(df.days)