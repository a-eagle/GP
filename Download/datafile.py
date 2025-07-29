import os, sys, requests, json, traceback, datetime, struct, time, copy, base64, platform

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

REMOTE_NODE = 'hcss-ecs-3865'

class PathManager:
    REMOTE_TDX_BASE_PATH = r'C:\new_tdx\vipdoc'
    TDX_BASE_PATH = r'D:\new_tdx\vipdoc'
    NET_BASE_PATH = f'\\NetData'
    NET_LDAY_PATH = '\\lday'
    NET_MINLINE_PATH = '\\minline'
    _ins = None

    def __init__(self) -> None:
        if platform.node() == REMOTE_NODE:
            PathManager.TDX_BASE_PATH = self.REMOTE_TDX_BASE_PATH
        if not os.path.exists(self.TDX_BASE_PATH):
            return
        PathManager.NET_BASE_PATH = PathManager.TDX_BASE_PATH + PathManager.NET_BASE_PATH
        PathManager.NET_LDAY_PATH = PathManager.TDX_BASE_PATH + PathManager.NET_LDAY_PATH
        PathManager.NET_MINLINE_PATH = PathManager.TDX_BASE_PATH + PathManager.NET_MINLINE_PATH
        for d in (self.NET_LDAY_PATH, self.NET_MINLINE_PATH):
            if not os.path.exists(d):
                os.makedirs(d)
        for s in ('sh', 'sz'):
            for f in ('lday', 'minline'):
                path = f'{self.TDX_BASE_PATH}\\{s}\\{f}'
                if not os.path.exists(path):
                    os.makedirs(path)

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
    def getLocalPath(self, dataType):
        code = self.code
        dataType = dataType.upper()
        if self.isNormalCode():
            tag = 'sh' if code[0] in ('6', '9') else 'sz'
            if dataType == 'DAY':
                bp = os.path.join(PathManager.TDX_BASE_PATH, f'{tag}\\lday\\{tag}{code}.day')
            else:
                bp = os.path.join(PathManager.TDX_BASE_PATH, f'{tag}\\minline\\{tag}{code}.lc1')
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
        path = dm.getLocalPath(_type)
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
        data = base64.decodebytes(bs)
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
                first = self.unpackTdxData(bs)
                pre = first.price
            rs['data'] = str(base64.encodebytes(bs))
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

    def accept(self):
        return platform.node() != REMOTE_NODE

    def loadLocalData_Day(self, destObj):
        if not self.accept():
            return False
        resp = requests.get(f'http://113.44.136.221:8090/remote?func=loadLocalData_Day&code={self.code}&params=')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return False
        data = js['data']
        bs = base64.decodestring(data)
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
        if not self.accept():
            return None
        resp = requests.get(f'http://113.44.136.221:8090/remote?func=getLocalLatestDay_Day&code={self.code}&params=')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return None
        day = js['data']
        return day

    def loadLocalData_Time(self, day, destObj):
        if not self.accept():
            return False
        resp = requests.get(f'http://113.44.136.221:8090/remote?func=loadLocalData_Time&code={self.code}&day={day}&params=day')
        cnt = resp.content.decode()
        js = json.loads(cnt)
        if js['status'] != 'OK':
            return False
        data = js['data']
        rbs = base64.decodestring(data)
        rs = []
        for i in range(len(bs) // 32):
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
        if not self.accept():
            return None
        resp = requests.get(f'http://113.44.136.221:8090/remote?func=getLocalLatestDay_Time&code={self.code}&params=')
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

    def loadLocalData(self): # tdx data
        self.data = None
        code = self.code
        if not code:
            return False
        path = self.getLocalPath('DAY')
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

    def getLocalLatestDay(self):
        path = self.getLocalPath('day')
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

    # day = str | int
    def _loadLocalData(self, day):
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        self.day = day
        TDX_MINUTES_IN_DAY = 240
        self.data = None
        path = self.getLocalPath('TIME')
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
        path = self.getLocalPath('TIME')
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
        if period == 'day':
            rs = hx.loadKLineData(self.code)
        elif period == 'week':
            url = hx.getKLineUrl_Week(self.code)
            rs = hx.loadUrlData(url)
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

class Writer:
    def writeToFile_K(self, code, datas):
        if not datas:
            return True
        path = K_DataModel(code).getLocalPath('DAY')
        filesize = 0
        RL = 32
        if os.path.exists(path):
            filesize = os.path.getsize(path)
            if filesize % RL != 0:
                print('[Writer.writeToFile_K] invalid file size ', code, path)
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

    def writeToFile_T(self, code, datas):
        RL = 32
        if not datas:
            return True
        if len(datas) % T_DataModel.MINUTES_IN_DAY != 0:
            print('[Writer.writeToFile_T] invalid data length', code)
            return False
        dm = T_DataModel(code)
        path = dm.getLocalPath('TIME')
        filesize = 0
        if os.path.exists(path):
            filesize = os.path.getsize(path)
            if filesize % (RL * T_DataModel.MINUTES_IN_DAY) != 0:
                print('[Writer.writeToFile_T] invalid file size ', code, path)
                return False
        f = open(path, 'a+b')
        # get last day
        lastDay = 0
        if filesize > 0:
            n = f.seek(-RL, 2)
            bs = f.read(RL)
            ri = dm.unpackTdxData(bs)
            lastDay = ri.day
        for idx, item in enumerate(datas):
            if item.day <= lastDay:
                continue
            if item.time == 930:
                continue
            self.merge930_931_data(datas[idx - 1], item)
            buf = dm.packTdxData(item)
            f.write(buf)
        f.close()
        return True

    def merge930_931_data(self, data930, data931):
        # TODO
        pass

    # tag = lday | minline
    def getLocalCodes(self, tag):
        codes = []
        path = PathManager.TDX_BASE_PATH + f'\\sh\\{tag}'
        dirs = os.listdir(path)
        c999999 = None
        for name in dirs:
            if name[0 : 2] == 'sh' and name[2] == '6':
                codes.append(name[2 : 8])
            if name[2 : 8] == '999999':
                c999999 = '999999'
        path = PathManager.TDX_BASE_PATH + f'\\sz\\{tag}'
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
        # for c in codes:
        #     self.writeToFile_T(c)

if __name__ == '__main__':
    proxy = RemoteProxy('601208')
    lday = proxy.getLocalLatestDay_Time()
    proxy.loadLocalData_Time(20250729)

    df = T_DataModel('601208') # 999999
    path = df.getLocalPath('TIME')
    f = open(path, 'rb')
    f.seek(-32 * 240, 2)
    for i in range(240):
        bs = f.read(32)
        item = df.unpackTdxData(bs)
        print(item)
