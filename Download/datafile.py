import os, sys, requests, json, traceback, datetime, struct, time, copy, base64, platform

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import config

TDX_MINUTES_IN_DAY = 240

def isServerMachine():
    return config.isServerMachine()

class PathManager:
    TDX_BASE_PATH = ''
    TDX_VIP_PATH = ''
    NET_LDAY_PATH = ''
    NET_MINLINE_PATH = ''

    def __init__(self) -> None:
        pt = 'D:\\new_tdx'
        if not os.path.exists(pt):
            pt = 'C:\\new_tdx'
        PathManager.TDX_BASE_PATH = pt
        PathManager.TDX_VIP_PATH = os.path.join(self.TDX_BASE_PATH, 'vipdoc')
        PathManager.NET_LDAY_PATH = os.path.join(self.TDX_VIP_PATH, 'NetData\\lday')
        PathManager.NET_MINLINE_PATH = os.path.join(self.TDX_VIP_PATH, 'NetData\\minline')
        for d in (self.NET_LDAY_PATH, self.NET_MINLINE_PATH):
            if not os.path.exists(d):
                os.makedirs(d)
        for s in ('sh', 'sz'):
            for f in ('lday', 'minline'):
                path = f'{self.TDX_VIP_PATH}\\{s}\\{f}'
                if not os.path.exists(path):
                    os.makedirs(path)

PathManager()

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
        if code == '1A0001':
            code = '999999'
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
    def _getLocalPath(self, dataType):
        code = self.code
        dataType = dataType.upper()
        if self.isNormalCode():
            tag = 'sh' if code[0] in ('6', '9') else 'sz'
            if dataType == 'DAY':
                bp = os.path.join(PathManager.TDX_VIP_PATH, f'{tag}\\lday\\{tag}{code}.day')
            else:
                bp = os.path.join(PathManager.TDX_VIP_PATH, f'{tag}\\minline\\{tag}{code}.lc1')
        else: # cls zs |  # ths zs
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}.day')
            else:
                bp = os.path.join(PathManager.NET_MINLINE_PATH, f'{code}.lc1')
        return bp

    def isNormalCode(self):
        if not self.code:
            return False
        return self.code == '999999' or self.code == '1A0001' or (len(self.code) == 6 and self.code[0] in ('6', '3', '0'))

class RemoteStub:
    def __init__(self, code) -> None:
        self.code = code

    def getLocalPath(self, _type):
        dm = DataModel(self.code)
        path = dm._getLocalPath(_type)
        path = 'c' + path[1:]
        return path

    def loadLocalData_Day(self):
        path = self.getLocalPath(self.code, 'DAY')
        if not os.path.exists(path):
            return {'status': 'Fail', 'msg': 'No file', 'data': None}
        filesize = os.path.getsize(path)
        if filesize % 32 != 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        f = open(path, 'rb')
        bs = f.read(filesize)
        f.close()
        data = base64.decodebytes(bs).decode()
        return {'status': 'OK', 'msg': 'Success', 'data': str(data)}

    def getLocalLatestDay_Day(self):
        path = self.getLocalPath(self.code, 'DAY')
        if not os.path.exists(path):
            return {'status': 'Fail', 'msg': 'No file', 'data': None}
        filesize = os.path.getsize(path)
        if filesize % 32 != 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        f = open(path, 'rb')
        RL = 32
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        day, *_ = struct.unpack('5Lf2L', bs)
        return {'status': 'OK', 'msg': 'Success', 'data': day}
    
    def unpackTdxData(self, bs):
        ritem = struct.unpack('2H5f2l', bs)
        item = ItemData(day = ritem[0], time = ritem[1], open = ritem[2], high = ritem[3], low = ritem[4], close = ritem[5], amount = ritem[6], vol = ritem[7])
        # ritem[8] 是什么? 指数有内容，非指数为0
        year = item.day // 2048 + 2004
        month = item.day % 2048 // 100
        day = item.day % 2048 % 100
        item.day = year * 10000 + month * 100 + day
        hour = item.time // 60
        minute = item.time % 60
        item.time = hour * 100 + minute
        item.price = item.close
        return item
    
    def loadLocalData_Time(self, day):
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        TDX_MINUTES_IN_DAY = 240
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return {'status': 'Fail', 'msg': 'No file', 'data': None}
        filesize = os.path.getsize(path)
        if filesize == 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        RL = 32
        if filesize % (RL * 240) != 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        rs = {'status': 'OK', 'msg': 'Success', 'pre': 0, 'data': None}
        f = open(path, 'rb')
        maxDays = filesize // (RL * TDX_MINUTES_IN_DAY)
        PAGE = RL * TDX_MINUTES_IN_DAY
        for i in range(maxDays):
            pos = PAGE * (i + 1)
            n = f.seek(-pos, 2)
            bs = f.read(RL)
            item = self.unpackTdxData(bs)
            if day > item.day:
                break
            if day < item.day:
                continue
            pre = 0
            if i != maxDays - 1:
                n = f.seek(-pos - RL, 2)
                bs = f.read(RL)
                item = self.unpackTdxData(bs)
                pre = item.price
            n = f.seek(-pos, 2)
            bs = f.read(RL * TDX_MINUTES_IN_DAY)
            if pre == 0:
                first = self.unpackTdxData(bs[0 : RL])
                pre = first.price
            rs['data'] = base64.encodebytes(bs).decode()
            rs['pre'] = pre
            break
        f.close()
        return rs

    def getLocalLatestDay_Time(self):
        path = self.getLocalPath('TIME')
        if not os.path.exists(path):
            return {'status': 'Fail', 'msg': 'No file', 'data': None}
        filesize = os.path.getsize(path)
        if filesize == 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        RL = 32
        if filesize % (RL * 240) != 0:
            return {'status': 'Fail', 'msg': 'Invalid file size', 'data': None}
        f = open(path, 'rb')
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        item = self.unpackTdxData(bs)
        return {'status': 'OK', 'msg': 'Success', 'data': item.day}

class RemoteProxy:
    def __init__(self, code) -> None:
        self.code = code

    def loadLocalData_Day(self, destObj):
        if isServerMachine():
            return False
        resp = requests.get(f'{config.SYNC_DB_SERVER_BASE_URL}/remote?func=loadLocalData_Day&code={self.code}&params=')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return False
        data = js['data']
        if not data:
            return False
        bs = base64.decodestring(data.encode())
        rs = []
        for i in range(len(bs) // 32):
            ritem = struct.unpack_from('5Lf2L', bs, i * 32)
            item = ItemData(day = ritem[0], open = ritem[1], high = ritem[2], low = ritem[3], close = ritem[4], amount = ritem[5], vol = ritem[6])
            item.open /= 100
            item.close /= 100
            item.low /= 100
            item.high /= 100
            rs.append(item)
        destObj.data = rs
        return True
        
    def getLocalLatestDay_Day(self):
        if isServerMachine():
            return None
        resp = requests.get(f'{config.SYNC_DB_SERVER_BASE_URL}/remote?func=getLocalLatestDay_Day&code={self.code}&params=')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return None
        day = js['data']
        return day

    def loadLocalData_Time(self, day, destObj):
        if isServerMachine():
            return False
        resp = requests.get(f'{config.SYNC_DB_SERVER_BASE_URL}/remote?func=loadLocalData_Time&code={self.code}&day={day}&params=day')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return False
        data : str = js['data']
        if not data:
            return False
        rbs = base64.decodebytes(data.encode())
        rs = []
        for i in range(len(rbs) // 32):
            bs = rbs[i * 32 : i * 32 + 32]
            item = destObj.unpackTdxData(bs)
            if item.time == 931:
                t930 = copy.copy(item)
                t930.time = 930
                t930.vol = t930.amount = 0
                rs.append(t930)
            rs.append(item)
        destObj.data = rs
        destObj.pre = js['pre']
        destObj.calcAvgPrice()
        return True

    def getLocalLatestDay_Time(self):
        if isServerMachine():
            return None
        resp = requests.get(f'{config.SYNC_DB_SERVER_BASE_URL}/remote?func=getLocalLatestDay_Time&code={self.code}&params=')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return None
        day = js['data']
        return day

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

    def getLocalPath(self):
        return self._getLocalPath('DAY')

    def loadLocalData(self): # tdx data
        self.data = None
        code = self.code
        if not code:
            return False
        path = self.getLocalPath()
        if not os.path.exists(path):
            return False
        rs = []
        f = open(path, 'rb')
        while f.readable():
            bs = f.read(32)
            if len(bs) != 32:
                break
            ritem = struct.unpack('5Lf2L', bs)
            item = ItemData(day = ritem[0], open = ritem[1], high = ritem[2], low = ritem[3], close = ritem[4], amount = ritem[5], vol = ritem[6])
            item.open /= 100
            item.close /= 100
            item.low /= 100
            item.high /= 100
            rs.append(item)
        self.data = rs
        f.close()
        return len(rs) > 0

    def isLocalFileValid(self):
        path = self.getLocalPath()
        if not os.path.exists(path):
            return False
        filesize = os.path.getsize(path)
        if filesize == 0:
            return False
        RL = 32
        if filesize % RL != 0:
            return False
        return True

    def getLocalLatestDay(self):
        path = self.getLocalPath()
        if not os.path.exists(path):
            return None
        filesize = os.path.getsize(path)
        if filesize == 0:
            return None
        RL = 32
        if filesize % RL != 0:
            print('[KDataModel.getLocalLatestDay] invalid file size ', self.code, path)
            return None
        f = open(path, 'rb')
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        day, *_ = struct.unpack('5Lf2L', bs)
        return day
    
class T_DataModel(DataModel):
    MINUTES_IN_DAY = 241

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

    def loadLocalData(self, day):
        ok = self._loadLocalData(day)
        if not ok:
            rp = RemoteProxy(self.code)
            ok = rp.loadLocalData_Time(day, self)
        return ok

    def getLocalPath(self):
        return self._getLocalPath('TIME')

    # day = str | int
    def _loadLocalData(self, day):
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        self.day = day
        self.data = None
        path = self.getLocalPath()
        if not os.path.exists(path):
            return False
        filesize = os.path.getsize(path)
        if filesize == 0:
            return False
        RL = 32
        if filesize % (RL * 240) != 0:
            print('[TDataModel.loadLocalData] invalid file size ', self.code, path)
            return False
        f = open(path, 'rb')
        maxDays = filesize // (RL * TDX_MINUTES_IN_DAY)
        PAGE = RL * TDX_MINUTES_IN_DAY
        rs = []
        for i in range(maxDays):
            pos = PAGE * (i + 1)
            n = f.seek(-pos, 2)
            bs = f.read(RL)
            item = self.unpackTdxData(bs)
            if day > item.day:
                break
            if day < item.day:
                continue
            pre = 0
            if i != maxDays - 1:
                n = f.seek(-pos - RL, 2)
                bs = f.read(RL)
                item = self.unpackTdxData(bs)
                pre = item.price
            n = f.seek(-pos, 2)
            for k in range(TDX_MINUTES_IN_DAY):
                bs = f.read(RL)
                item = self.unpackTdxData(bs)
                if item.time == 931:
                    t930 = copy.copy(item)
                    t930.time = 930
                    t930.vol = t930.amount = 0
                    rs.append(t930)
                rs.append(item)
            if pre == 0:
                self.pre = rs[0].price
            else:
                self.pre = pre
            self.data = rs
        f.close()
        self.calcAvgPrice()
        return len(rs) > 0

    def isLocalFileValid(self):
        path = self.getLocalPath()
        if not os.path.exists(path):
            return False
        filesize = os.path.getsize(path)
        if filesize == 0:
            return False
        RL = 32
        PAGE = RL * TDX_MINUTES_IN_DAY
        if filesize % PAGE != 0:
            return False
        return True

    # [day, ...]
    def loadDays(self):
        path = self.getLocalPath()
        if not os.path.exists(path):
            return None
        filesize = os.path.getsize(path)
        if filesize == 0:
            return None
        RL = 32
        PAGE = RL * TDX_MINUTES_IN_DAY
        if filesize % PAGE != 0:
            print('[T_DataModel.loadDays] invalid file size ', self.code, path)
            return None
        f = open(path, 'rb')
        rs = []
        maxDays = filesize // PAGE
        for i in range(maxDays):
            f.seek(i * PAGE, 0)
            bs = f.read(RL)
            item = self.unpackTdxData(bs)
            rs.append(item.day)
        f.close()
        return rs

    def unpackTdxData(self, bs):
        ritem = struct.unpack('2H5f2l', bs)
        item = ItemData(day = ritem[0], time = ritem[1], open = ritem[2], high = ritem[3], low = ritem[4], close = ritem[5], amount = ritem[6], vol = ritem[7])
        # ritem[8] 是什么? 指数有内容，非指数为0
        year = item.day // 2048 + 2004
        month = item.day % 2048 // 100
        day = item.day % 2048 % 100
        item.day = year * 10000 + month * 100 + day
        hour = item.time // 60
        minute = item.time % 60
        item.time = hour * 100 + minute
        item.price = item.close
        return item
    
    def packTdxData(self, item : ItemData):
        day = ((item.day // 10000 - 2004) * 2048) + (item.day // 100 % 100 * 100) + (item.day % 100)
        time = item.time // 100 * 60 + item.time % 100
        bs = struct.pack('2H5f2l', day, time, item.open, item.high, item.low, item.close, item.amount, item.vol, 0) # 最后一个L是什么？
        return bs

    def getLocalLatestDay(self):
        path = self.getLocalPath()
        if not os.path.exists(path):
            return None
        filesize = os.path.getsize(path)
        if filesize == 0:
            return None
        RL = 32
        if filesize % (RL * 240) != 0:
            print('[TDataModel.getLocalLatestDay] invalid file size ', self.code, path)
            return None
        f = open(path, 'rb')
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        item = self.unpackTdxData(bs)
        return item.day

class Ths_K_DataModel(K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    # period = 'day' | 'week' | 'month'
    def loadNetData(self, period):
        from download import henxin
        hx = henxin.HexinUrl()
        rs = hx.loadKLineData(self.code, period)
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
        rs = hx.loadTimelineData(self.code)
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

class TdxChuncker:
    # tag = lday | minline
    def getLocalCodes(self, tag):
        codes = []
        path = PathManager.TDX_VIP_PATH + f'\\sh\\{tag}'
        dirs = os.listdir(path)
        c999999 = None
        for name in dirs:
            if name[0 : 2] == 'sh' and name[2] == '6':
                codes.append(name[2 : 8])
            if name[2 : 8] == '999999':
                c999999 = '999999'
        path = PathManager.TDX_VIP_PATH + f'\\sz\\{tag}'
        dirs = os.listdir(path)
        for name in dirs:
            if name[0 : 2] == 'sz' and name[2] in ('0', '3'):
                codes.append(name[2 : 8])
        if c999999:
            codes.append('999999')
        return codes

    # tag = lday | minline
    # delete not GP code files
    def _removeNotCodes(self, tag):
        path = PathManager.TDX_VIP_PATH + f'\\sh\\{tag}'
        dirs = os.listdir(path)
        for name in dirs:
            isCode = name[0 : 2] == 'sh' and (name[2] == '6' or name[2:4] == '99')
            if not isCode:
                os.remove(os.path.join(path, name))
        path = PathManager.TDX_VIP_PATH + f'\\sz\\{tag}'
        dirs = os.listdir(path)
        for name in dirs:
            isCode = name[0 : 2] == 'sz' and (name[2] == '0' or name[2] == '3')
            if not isCode:
                os.remove(os.path.join(path, name))

    def removeNotCodes(self):
        self._removeNotCodes('lday')
        self._removeNotCodes('minline')

    def chunckAll_T(self, fromDay, endDay):
        codes = self.getLocalCodes('minline')
        for c in codes:
            self.chunck_T(c, (fromDay, endDay))

    def chunckAll_T_ByLastDay(self, lastDayNum):
        df = T_DataModel('999999') # 999999
        days = df.loadDays()
        if lastDayNum >= len(days):
            return
        self.chunckAll_T(days[-lastDayNum], days[-1])

    def _ajdustFromEndDay(self, days, fromDay, endDay):
        if type(fromDay) == str:
            fromDay = int(fromDay.replace('-', ''))
        if type(endDay) == str:
            endDay = int(endDay.replace('-', ''))
        if not days:
            return None
        # adjust from day
        for i in range(len(days)):
            if days[i] >= fromDay:
                fromDay = days[i]
                break
        # adjust end day
        ed = endDay
        for i in range(len(days)):
            if days[i] <= ed:
                endDay = days[i]
        if (fromDay > endDay) or (fromDay not in days) or (endDay not in days):
            return None
        return (fromDay, endDay)

    def removeInvalidCodes(self):
        codes = self.getLocalCodes('minline')
        for c in codes:
            m = T_DataModel(c)
            if os.path.exists(m.getLocalPath()) and not m.isLocalFileValid():
                os.remove(m.getLocalPath())
        pass

    # days = int | typle(fromDay: int, endDay: int)
    # 仅保留给定日期的数据
    def chunck_T(self, code, *days):
        df = T_DataModel(code)
        path = df.getLocalPath()
        if not os.path.exists(path):
            return
        if not days:
            os.remove(path)
            return
        ldays = df.loadDays()
        exdays = set()
        for d in days:
            if type(d) == str:
                d = int(d.replace('-', '').strip())
            fe = None
            if type(d) == int:
                fe = self._ajdustFromEndDay(ldays, d, d)
            elif type(d) == list or type(d) == tuple:
                fe = self._ajdustFromEndDay(ldays, d[0], d[1])
            if not fe:
                continue
            bidx = ldays.index(fe[0])
            eidx = ldays.index(fe[1])
            if bidx > 0:
                bidx -= 1 # add pre day
            for i in range(bidx, eidx + 1):
                exdays.add(ldays[i])
        exdays = list(exdays)
        exdays.sort()
        print(exdays)
        # read & write
        RL = 32
        PAGE = RL * TDX_MINUTES_IN_DAY
        # read
        datas = []
        f = open(path, 'rb')
        for day in exdays:
            bpos = ldays.index(day) * PAGE
            f.seek(bpos, 0)
            bs = f.read(PAGE)
            datas.append(bs)
        f.close()
        # write
        f = open(path, 'wb')
        for d in datas:
            f.write(d)
        f.close()

    # 保留热点及近几日的数据
    def chunckAll_T_ByHots(self, lastDaysNum = 100):
        from orm import ths_orm, cls_orm
        rs = {}
        for h in ths_orm.THS_HotZH.select():
            code = f'{h.code :06d}'
            if code not in rs:
                rs[code] = set()
            rs[code].add(h.day)
        for h in ths_orm.THS_ZT.select(ths_orm.THS_ZT.code, ths_orm.THS_ZT.day):
            if h.code not in rs:
                rs[h.code] = set()
            rs[h.code].add(int(h.day.replace('-', '')))
        for h in cls_orm.CLS_UpDown.select(cls_orm.CLS_UpDown.secu_code, cls_orm.CLS_UpDown.day):
            code = h.secu_code[2 : ]
            if code not in rs:
                rs[code] = set()
            rs[code].add(int(h.day.replace('-', '')))
        for h in cls_orm.CLS_ZT.select(cls_orm.CLS_ZT.code, cls_orm.CLS_ZT.day):
            if h.code not in rs:
                rs[h.code] = set()
            rs[h.code].add(int(h.day.replace('-', '')))
        df = T_DataModel('999999') # 999999
        days = df.loadDays()
        if len(days) <= lastDaysNum:
            return
        lastDays = (days[-lastDaysNum], days[-1])
        codes = self.getLocalCodes('minline')
        for c in codes:
            if c[0 : 3] in ('999', '399'): # 指数
                continue
            ex = rs.get(c, [])
            self.chunck_T(c, *ex, lastDays)

if __name__ == '__main__':
    w = TdxChuncker()
    # CODE = '600000'
    # dm = T_DataModel(CODE)
    # days = dm.loadDays()
    # print(len(days), days)
    # w.chunckAll_T_ByHots()
    # w.chunck_T('600000', 20251020, (20250925, 20251010), (20251223, 20251224))
    # w.removeNotCodes()
    # w.chunckAll_T_ByLastDay(22)
    # w.removeInvalidCodes()
    
    # f = open(r'C:\Users\GaoYan\Desktop\sz000030.lc1', 'rb')
    # bs = f.read(32)
    # tm = T_DataModel('000030')
    # ritem = tm.unpackTdxData(bs)
    # print(ritem)
    # f.close()
    stime = time.time()
    cs = w.getLocalCodes('lday')
    for c in cs[0 : 300]:
        dm = K_DataModel(c)
        dm.loadLocalData()
    etime = time.time()
    print('use time=', etime - stime)
    



