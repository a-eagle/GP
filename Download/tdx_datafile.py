import os, struct, platform, traceback, sys

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

    def loadData(self):
        pass

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
        pass
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


