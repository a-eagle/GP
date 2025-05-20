import os, sys, requests, json, traceback, datetime, struct, time

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

class PathManager:
    NET_BASE_PATH = r'D:\GP_Net_Data'
    NET_LDAY_PATH = NET_BASE_PATH + '\\lday'
    NET_MINLINE_PATH = NET_BASE_PATH + '\\minline'
    NET_CLS_MINLINE_PATH = NET_BASE_PATH + '\\cls-minline'
    NET_THS_MINLINE_PATH = NET_BASE_PATH + '\\ths-minline'
    _ins = None

    def __init__(self) -> None:
        for d in (self.NET_LDAY_PATH, self.NET_MINLINE_PATH, self.NET_CLS_MINLINE_PATH, self.NET_THS_MINLINE_PATH):
            if not os.path.exists(d):
                os.makedirs(d)

if not PathManager._ins:
    PathManager._ins = PathManager()

class ItemData:
    # KLine ('day', 'open', 'high', 'low', 'close', 'amount', 'vol') MA5, MA10
    # TimeLine ('day', 'time', 'price', 'avgPrice', 'amount', 'vol')

    def __init__(self, **args):
        if not args:
            return
        for k in args:
            setattr(self, k, args[k])

    def __repr__(self) -> str:
        ds = self.__dict__
        s = 'ItemData('
        for k in ds:
            s += f"{k}={str(ds[k])}, "
        s = s[0 : -2]
        s += ')'
        return s

class DataModel:
    def __init__(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        if len(code) == 8 and code[0] == 's':
            code = code[2 : ]
        self.code : str = code
        self.name = self._getName()
        self.data = None

    def _getName(self):
        from orm import ths_orm, cls_orm
        if self.code[0] in ('0', '3', '6'):
            q = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.name.distinct()).where(ths_orm.THS_GNTC.code == self.code)
        elif self.code[0 : 2] == '88':
            q = ths_orm.THS_ZS.select(ths_orm.THS_ZS.name.distinct()).where(ths_orm.THS_ZS.code == self.code)
        elif self.code[0 : 3] == 'cls':
            q = cls_orm.CLS_ZS.select(cls_orm.CLS_ZS.name.distinct()).where(cls_orm.CLS_ZS.code == self.code)
        else:
            return
        for it in q.tuples():
            return it[0]
        return None

    def getItemIdx(self, day):
        if not self.data or not day:
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
        if idx >= 0 and idx < len(self.data) and self.data[idx].day == day:
            return idx
        return -1

    # dataType = 'DAY' | 'TIME'
    def getLocalPath(self, dataType):
        code = self.code
        dataType = dataType.upper()
        if code[0 : 3] == 'cls': # cls zs
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(PathManager.NET_CLS_MINLINE_PATH, f'{code}.lc1')
        elif code[0] == '8': # ths zs
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(PathManager.NET_THS_MINLINE_PATH, f'{code}.lc1')
        else: # GP
            if code[0 : 2] in ('sz', 'sh'):
                code = code[2 : ]
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(PathManager.NET_MINLINE_PATH, f'{code}.lc1')
        return bp

class K_DataModel(DataModel):
    def __init__(self, code):
        super().__init__(code)

    def calcMA(self, N):
        if not self.data:
            return
        name = 'MA' + str(N)
        for i in range(N - 1, len(self.data)):
            ap = 0
            for j in range(i + 1 - N, i + 1):
                ap += self.data[j].close
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
        if not self.data:
            return
        for i in range(1, len(self.data)):
            self._calcZDTInfo(self.data[i - 1].close, self.data[i])

    #计算涨幅
    def calcZhangFu(self):
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

    def loadLocalData(self):
        self.data = None
        path = self.getLocalPath('DAY')
        if not os.path.exists(path):
            return False
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return False
        RL = 32
        if filesize % RL != 0:
            print('[K_DataModel.loadLocalData] invalid file size ', self.code, path)
            return False
        maxDays = filesize // RL
        rs = []
        for i in range(maxDays):
            bs = f.read(RL)
            item = struct.unpack('l5f2l', bs)
            rs.append(ItemData(day = item[0], open = item[1], high = item[2], low = item[3], close = item[4], amount = item[5], vol = item[6]))
        self.data = rs
        f.close()
        return len(rs) > 0
    
class T_DataModel(DataModel):
    def __init__(self, code):
        super().__init__(code)
        self.pre = 0
        self.day : int = None # int

    def getPre(self):
        if self.pre:
            return self.pre
        if self.data:
            return self.data[0].price
        return 0

    def getItemIdx(self, day):
        if not self.data:
            return -1
        idx = super().getItemIdx(day)
        if idx < 0:
            return -1
        day = self.data[idx].day
        while idx > 0:
            if self.data[idx - 1].day == day:
                idx -= 1
            else:
                break
        return idx

    # 分时均线
    def calcAvgPrice(self):
        if not self.data:
            return 0
        idx = 0
        sumamount, sumVol = 0, 0
        while idx < len(self.data):
            d = self.data[idx]
            sumamount += d.amount
            sumVol += d.vol
            if sumVol > 0:
                d.avgPrice = sumamount / sumVol
            else:
                d.avgPrice = d.price
            idx += 1

    #计算涨幅
    def calcZhangFu(self):
        if not self.data:
            return
        if self.pre <= 0:
            self.zhangFu = 0
            return
        cc = self.data[-1].price
        self.zhangFu = (cc - self.pre) / self.pre * 100

    # day: int
    def loadLocalData(self, day):
        MINUTES_IN_DAY = 241
        self.data = None
        if not day:
            return False
        if type(day) == str:
            day = int(day.replace('-', ''))
        self.day = day
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return False
        f = open(path, 'rb')
        filesize = os.path.getsize(path)
        if filesize == 0:
            f.close()
            return False
        RL = 24
        if filesize % (RL * MINUTES_IN_DAY) != 0:
            print('[TDataFile.loadData] invalid file size ', self.code, path)
            return False
        maxDays = filesize // (RL * MINUTES_IN_DAY)
        PAGE = RL * MINUTES_IN_DAY
        rs = []
        for i in range(maxDays):
            pos = PAGE * (i + 1)
            n = f.seek(-pos, 2)
            bs = f.read(RL)
            item = struct.unpack('2l4f', bs)
            if day > item[0]:
                break
            if day < item[0]:
                continue
            pre = 0
            if i != maxDays - 1:
                n = f.seek(-pos - RL, 2)
                bs = f.read(RL)
                item = struct.unpack('2l4f', bs)
                pre = item[2]
            n = f.seek(-pos, 2)
            for k in range(MINUTES_IN_DAY):
                bs = f.read(RL)
                item = struct.unpack('2l4f', bs)
                rs.append(ItemData(day = item[0], time = item[1], price = item[2], avgPrice = item[3], amount  = item[4], vol = item[5]))
            if pre == 0:
                self.pre = rs[0].price
            else:
                self.pre = pre
            self.data = rs
        f.close()
        return len(rs) > 0

class Ths_K_DataModel(K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    # period = 'day' | 'week' | 'month'
    def loadNetData(self, period):
        from download import henxin
        hx = henxin.HexinUrl()
        if period == 'day':
            url = hx.getKLineUrl(self.code)
        elif period == 'week':
            url = hx.getKLineUrl_Week(self.code)
        elif period == 'month':
            url = hx.getKLineUrl_Month(self.code)
        rs = hx.loadUrlData(url)
        if rs:
            self.data = rs['data']
            self.name = rs['name']
        else:
            self.data = None

class Ths_T_DataModel(T_DataModel):
    def __init__(self, code):
        super().__init__(code)

    def _loadNetLastData(self):
        from download import henxin
        hx = henxin.HexinUrl()
        url = hx.getFenShiUrl(self.code)
        rs = hx.loadUrlData(url)
        return rs
    
    def loadData(self, day):
        if not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        ok = self.loadLocalData(day)
        if ok:
            self.day = day
            return
        rs = self._loadNetLastData()
        if not rs or rs.get('date', -1) != day:
            return
        self.data = rs['line']
        self.name = rs['name']
        self.pre = rs['pre']
        self.day = day

class Cls_K_DataModel(K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    # period = 'day' | 'week' | 'month'
    def loadNetData(self, period):
        from download import cls
        hx = cls.ClsUrl()
        rs = hx.loadKline(self.code, period = period)
        self.data = rs

class Cls_T_DataModel(T_DataModel):
    def __init__(self, code):
        super().__init__(code)

    def _loadNetLastData(self):
        from download import cls
        hx = cls.ClsUrl()
        rs = hx.loadHistory5FenShi(self.code)
        return rs
    
    def loadData(self, day):
        if not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        ok = self.loadLocalData(day)
        if ok:
            self.day = day
            return
        rs = self._loadNetLastData()
        if not rs:
            return
        days = rs['date']
        if day not in days:
            return
        self.day = day
        idx = days.index(day)
        pos = idx * 241
        line = rs['line']
        self.data = line[pos : pos + min(241, len(line) - pos)]
        if idx > 0:
            self.pre = line[pos - 1].price
        else:
            self.pre = line[pos].price


if __name__ == '__main__':
    df = Cls_T_DataModel('300260')
    df.loadData(20250403)
    print(df)