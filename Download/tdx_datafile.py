import os, struct, platform, traceback, sys, copy

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

VIPDOC_BASE_PATH = r'D:\new_tdx\vipdoc'

class ItemData:
    DS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol') # vol(鑲¡), lbs(杩炴澘鏁°), zdt(娑ㄨ穼鍋), tdb(澶╁湴鏉匡紝鍦板ぉ鏉¿) zhangFu(娑ㄥ箙)
    MLS = ('day', 'time', 'open', 'high', 'low', 'close', 'amount', 'vol') # avgPrice 鍒嗘椂鍧囦环
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

    def __repr__(self) -> str:
        ds = self.__dict__
        s = 'ItemData('
        for k in ds:
            s += f"{k}={str(ds[k])}, "
        s = s[0 : -2]
        s += ')'
        return s

class DataFile:
    def __init__(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.data = []
        self.days = []

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

    def _getPath(self, type):
        code = self.code
        tag = '' 
        if code[0] == '6' or code[0] == '9': tag = 'sh'
        elif code[0] == '3' or code[0] == '0': tag = 'sz'
        if type == 'day':
            bp = os.path.join(VIPDOC_BASE_PATH, f'{tag}\\lday\\{tag}{code}.day')
        else:
            bp = os.path.join(VIPDOC_BASE_PATH, f'{tag}\\minline\\{tag}{code}.lc1')
        return bp

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

class K_DataFile(DataFile):
    def __init__(self, code):
        super().__init__(code)

    def getPath(self):
        return self._getPath('day')

    def loadData(self):
        self.data.clear()
        path = self.getPath()
        if not os.path.exists(path):
            return
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            ritem = struct.unpack('5Lf2L', bs)
            item = ItemData(*ritem[0 : -1])
            item.open /= 100
            item.close /= 100
            item.low /= 100
            item.high /= 100
            self.data.append(item)
        f.close()
        self.calcDays()        

class T_DataFile(DataFile):
    def __init__(self, code):
        super().__init__(code)

    def getPath(self):
        return self._getPath('minute')

    def loadData(self):
        self.data.clear()
        path = self.getPath()
        if not os.path.exists(path):
            return
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            ritem = struct.unpack('2H5f2l', bs)
            item = ItemData(*ritem[0 : -1])
            year = item.day //2048 + 2004
            month = item.day % 2048 //100
            day = item.day % 2048 % 100
            item.day = year * 10000 + month * 100 + day
            hour = item.time // 60
            minute = item.time % 60
            item.time = hour * 100 + minute
            item.price = item.close
            if item.time == 931:
                t930 = copy.copy(item)
                t930.time = 930
                t930.vol = t930.amount = 0
                self.data.append(t930)
            self.data.append(item)
        f.close()
        # check minute line number
        if len(self.data) % 241 != 0:
            print('Minute Line number error:', self.code, 'len = ', len(self.data))
            # raise Exception('Minute Line number error:', len(self.data))
            return
        self.calcDays()
        self.calcAvgPrice()

    # 分时均线
    def calcAvgPrice(self):
        if not self.data:
            return 0
        idx = 0
        sumamount, sumVol = 0, 0
        while idx < len(self.data):
            d = self.data[idx]
            if idx > 0 and self.data[idx - 1].day != d.day:
                sumamount, sumVol = 0, 0
            sumamount += d.amount
            sumVol += d.vol
            if sumVol > 0:
                d.avgPrice = sumamount / sumVol
            else:
                d.avgPrice = d.price
            idx += 1

class Writer:
    def writeToFile_K(self, code):
        srcDf = K_DataFile(code)
        srcDf.loadData()
        if not srcDf.data:
            return
        self._writeToNetFile_K(code, srcDf.data)

    def _writeToNetFile_K(self, code, datas):
        from download import datafile
        if not datas:
            return True
        path = datafile.K_DataModel(code).getLocalPath('DAY')
        filesize = 0
        RL = 32
        if os.path.exists(path):
            filesize = os.path.getsize(path)
            if filesize % RL != 0:
                print('[Writer._writeToNetFile_K] invalid file size ', code, path)
                return False
        f = open(path, 'a+b')
        # get last day
        lastDay = 0
        if filesize > 0:
            n = f.seek(-RL, 2)
            bs = f.read(RL)
            lastDay, *_ = struct.unpack('l5f2l', bs)
        for idx, item in enumerate(datas):
            if item.day <= lastDay:
                continue
            buf = struct.pack('l5f2l', item.day, item.open, item.high, item.low, item.close, item.amount, item.vol, 0)
            f.write(buf)
        f.close()
        return True

    def writeToFile_T(self, code):
        srcDf = T_DataFile(code)
        srcDf.loadData()
        if not srcDf.data:
            return
        self._writeToNetFile_T(code, srcDf.data)

    def _writeToNetFile_T(self, code, datas):
        from download import datafile
        RL = 24
        if not datas:
            return True
        if len(datas) % datafile.T_DataModel.MINUTES_IN_DAY != 0:
            print('[Writer._writeToNetFile_T] invalid data length', code)
            return False
        path = datafile.T_DataModel(code).getLocalPath('TIME')
        filesize = 0
        if os.path.exists(path):
            filesize = os.path.getsize(path)
            if filesize % (RL * datafile.T_DataModel.MINUTES_IN_DAY) != 0:
                print('[Writer._writeToNetFile_T] invalid file size ', code, path)
                return False
        f = open(path, 'a+b')
        # get last day
        lastDay = 0
        if filesize > 0:
            n = f.seek(-RL, 2)
            bs = f.read(RL)
            lastDay, *_ = struct.unpack('2l4f', bs)
        for idx, item in enumerate(datas):
            if item.day <= lastDay:
                continue
            buf = struct.pack('2l4f', item.day, item.time, item.price, item.avgPrice, item.amount, item.vol)
            f.write(buf)
        f.close()
        return True

    # tag = lday | minline
    def getLocalCodes(self, tag):
        codes = []
        path = VIPDOC_BASE_PATH + f'\\sh\\{tag}'
        dirs = os.listdir(path)
        c999999 = None
        for name in dirs:
            if name[0 : 2] == 'sh' and name[2] == '6':
                codes.append(name[2 : 8])
            if name[2 : 8] == '999999':
                c999999 = '999999'
        path = VIPDOC_BASE_PATH + f'\\sz\\{tag}'
        dirs = os.listdir(path)
        for name in dirs:
            if name[0 : 2] == 'sz' and name[2] in ('0', '3'):
                codes.append(name[2 : 8])
        if c999999:
            codes.append('999999')
        return codes

    def writeAll(self):
        codes = self.getLocalCodes('lday')
        # for c in codes:
            # self.writeToFile_K(c)

        codes = self.getLocalCodes('minline')
        for c in codes:
            self.writeToFile_T(c)

if __name__ == '__main__':
    df = T_DataFile('999999')
    df.loadData()
    print('Local Tdx:', df.days, len(df.days))

    import datafile
    dm = datafile.T_DataModel('999999')
    print('T_DataModel last day:', dm.getLocalLatestDay())

    w = Writer()
    w.writeAll()
   