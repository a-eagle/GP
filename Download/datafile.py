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
        PathManager.NET_LDAY_PATH = 'D:\\K-Data'
        pt = 'D:\\new_tdx'
        if not os.path.exists(pt):
            pt = 'C:\\new_tdx'
            PathManager.NET_LDAY_PATH = 'C:\\K-Data'
        PathManager.TDX_BASE_PATH = pt
        PathManager.TDX_VIP_PATH = os.path.join(self.TDX_BASE_PATH, 'vipdoc')
        
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
    
    def getNearItemIdx(self, day):
        if not day or not self.data:
            return -1
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        for i in range(len(self.data) - 1, -1, -1):
            if day < self.data[i].day:
                continue
            else:
                break
        return i

    # dataType = 'DAY' | 'TIME'
    def _getLocalPath(self, dataType):
        code = self.code
        dataType = dataType.upper()
        if self.isNormalCode():
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}')
            else:
                tag = 'sh' if code[0] in ('6', '9') else 'sz'
                bp = os.path.join(PathManager.TDX_VIP_PATH, f'{tag}\\minline\\{tag}{code}.lc1')
        else: # cls zs |  # ths zs
            if dataType == 'DAY':
                bp = os.path.join(PathManager.NET_LDAY_PATH, f'{code}')
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
            dd = struct.unpack_from('L7f', bs, i * 32)
            item = ItemData(day = dd[0], open = dd[1], close = dd[2], low = dd[3], high = dd[4], vol = dd[5], amount = dd[6], rate = dd[7])
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

    def loadLocalData(self): # local net data
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
            dd = struct.unpack('L7f', bs)
            item = ItemData(day = dd[0], open = dd[1], close = dd[2], low = dd[3], high = dd[4], vol = dd[5], amount = dd[6], rate = dd[7])
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
        if not self.isLocalFileValid():
            print('[KDataModel.getLocalLatestDay] invalid file size ', self.code, path)
            return None
        RL = 32
        f = open(path, 'rb')
        n = f.seek(-RL, 2)
        bs = f.read(RL)
        f.close()
        day, *_ = struct.unpack('L7f', bs)
        return day

class Tdx_K_DataModel(K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    def getLocalPath(self):
        tag = 'sh' if self.code[0] in ('6', '9') else 'sz'
        bp = os.path.join(PathManager.TDX_VIP_PATH, f'{tag}\\lday\\{tag}{self.code}.day')
        return bp

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

    def getLocalLatestDay(self):
        path = self.getLocalPath()
        RL = 32
        if not self.isLocalFileValid():
            print('[Tdx_K_DataModel.getLocalLatestDay] invalid file size ', self.code, path)
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

class Net_K_DataModel(K_DataModel):
    def __init__(self, code):
        super().__init__(code)
    
    # period = 'day' | 'week' | 'month'
    def loadNetData(self, period):
        from download import ths_iwencai
        if self.checkLocalData():
            self.loadDayData_UseLocal()
        else:
            self.loadDayData_UseNet()
            # write net data
            tday = ths_iwencai.getTradeDaysInt()[-1]
            today = int(datetime.date.today().strftime('%Y%m%d'))
            kd = KLineDownloader()
            if tday == today:
                maxDay = ths_iwencai.getTradeDaysInt()[-2]
            else:
                maxDay = tday
            kd.overWrite(self.code, self.data, toDay = maxDay)
        if period == 'week':
            self.buildWeekData()
        elif period == 'month':
            self.buildMonthData()

    def loadDayData_UseLocal(self):
        from download import ths_iwencai, henxin
        self.data = None
        self.loadLocalData()
        last = self.data[-1].day
        lday = ths_iwencai.getTradeDaysInt()[-1]
        if last == lday:
            return
        hx = henxin.HexinUrl()
        todayRs = hx.loadTodayKLineData(self.code)
        todayData = todayRs.get('data', None) if todayRs else None
        if not todayData:
            return
        if last != todayData.day:
            self.data.append(todayData)
            return
        self.data.pop(-1)
        self.data.append(todayData)

    def loadDayData_UseNet(self):
        pass

    def checkLocalData(self):
        from download import ths_iwencai
        tdays = ths_iwencai.getTradeDaysInt()
        lastDay = self.getLocalLatestDay()
        if not lastDay:
            return False
        if lastDay == tdays[-1] or lastDay == tdays[-2]:
            return True
        return False
    
    def buildWeekData(self):
        if not self.data:
            return
        datas = self.data
        wdatas = []
        startDay, endDay = None, None
        for d in datas:
            date = datetime.date(d.day // 10000, d.day // 100 % 100, d.day % 100)
            if startDay and date >= startDay and date <= endDay:
                # merge
                last = wdatas[-1]
                last.amount += d.amount
                last.vol += d.vol
                last.rate += d.rate
                last.close = d.close
                last.low = min(d.low, last.low)
                last.high = max(d.high, last.high)
                last.day = d.day
            else:
                startDay = date
                wdatas.append(copy.copy(d))
                endDay = date + datetime.timedelta(days = 4 - date.weekday())
        self.data = wdatas

    def buildMonthData(self):
        if not self.data:
            return
        datas = self.data
        wdatas = []
        startDay, endDay = None, None
        for d in datas:
            date = d.day
            if startDay and date >= startDay and date <= endDay:
                # merge
                last = wdatas[-1]
                last.amount += d.amount
                last.vol += d.vol
                last.rate += d.rate
                last.close = d.close
                last.low = min(d.low, last.low)
                last.high = max(d.high, last.high)
                last.day = d.day
            else:
                startDay = date
                endDay = date // 100 * 100 + 31
                wdatas.append(copy.copy(d))
        self.data = wdatas

class Ths_K_DataModel(Net_K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    def loadDayData_UseNet(self):
        from download import henxin
        hx = henxin.HexinUrl()
        rs = hx.loadKLineData(self.code, 'day')
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

class Cls_K_DataModel(Net_K_DataModel):
    def __init__(self, code):
        super().__init__(code)

    # period = 'day' | 'week' | 'month'
    def loadDayData_UseNet(self):
        from download import cls
        hx = cls.ClsUrl()
        rs = hx.loadKline(self.code, period = 'day')
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
        codes.sort(key = lambda c: c)
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
        if not df.isLocalFileValid():
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
        # print('[datafile.chunck_T]', exdays)
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

class KLineDownloader:
    K_PATH = PathManager.NET_LDAY_PATH

    def __init__(self) -> None:
        from download import memcache
        memcache.cache.enableCache = False

    def loadNet(self, code : str, useThs : bool, loadToday : bool):
        from download import henxin, cls
        if useThs:
            hx = henxin.HexinUrl()
            if loadToday:
                rs = hx.loadKLineData_Day(code)
            else:
                rs = hx._loadKLineDataPeroid(code, 'day')
            rs = rs['data']
        else:
            hx = cls.ClsUrl()
            rs = hx.loadKline(code, limit = 1800)
        return rs

    def overWrite(self, code : str, kdatas, fromDay = None, toDay = None):
        f = open(os.path.join(self.K_PATH, code), 'wb')
        for d in kdatas:
            if fromDay and d.day < fromDay:
                continue
            if toDay and d.day > toDay:
                break
            bs = struct.pack('L7f', d.day, float(d.open), float(d.close), float(d.low), float(d.high), float(d.vol), float(d.amount), float(d.rate))
            f.write(bs)
        f.close()

    def pack(self, kdata : ItemData):
        it = struct.pack('L7f', kdata.day, float(kdata.open), float(kdata.close), float(kdata.low),
                         float(kdata.high), float(kdata.vol), float(kdata.amount), float(kdata.rate))
        return it

    def unpack(self, bs) -> ItemData:
        dd = struct.unpack('L7f', bs)
        it = ItemData(day = dd[0], open = dd[1], close = dd[2], low = dd[3], high = dd[4], vol = dd[5], amount = dd[6], rate = dd[7])
        return it

    # kdata = ItemData | list[ItemData]
    def mergeWrite(self, code, kdata):
        if not kdata:
            return False
        if isinstance(kdata, ItemData):
            kdata = [kdata]
        kdata = [k for k in kdata if (k.day and k.open and k.close and k.vol)]
        kdata.sort(key = lambda k: k.day)
        if not kdata:
            return False
        
        path = os.path.join(self.K_PATH, code)
        ex = os.path.exists(path)
        fsize = os.path.getsize(path) if ex else 0

        # trunck file write
        if (not ex) or (fsize == 0) or (fsize % 32 != 0):
            f = open(path, 'wb')
            target = self.pack(kdata)
            f.write(target)
            f.close()
            return True
        self._mergeWrite(path, fsize, kdata)
        return True
    
    def _mergeKdata(self, rs, kdata):
        for i in range(len(rs) + 1):
            if i == len(rs):
                rs.append(kdata)
                break
            if rs[i].day < kdata.day:
                continue
            if rs[i].day == kdata.day:
                rs[i] = kdata
                break
            else:
                rs.insert(i, kdata)
                break
    
    def _mergeWrite(self, path, fsize, kdatas : list):
        from download import ths_iwencai
        tdays = ths_iwencai.getTradeDaysInt()
        idx = tdays.index(kdatas[0].day)
        num = len(tdays) - idx
        num = min(num, fsize // 32)
        f = open(path, 'r+b')
        f.seek(-num * 32, 2)
        bs = f.read(num * 32)
        rs = []
        for i in range(num):
            it = self.unpack(bs[i * 32 : i * 32 + 32])
            rs.append(it)
        for k in kdatas:
            self._mergeKdata(rs, k)
        f.seek(-num * 32, 2)
        for i in range(len(rs)):
            bs = self.pack(rs[i])
            f.write(bs)
        f.close()
        return True

    def isLocalFileValid(self, code):
        path = os.path.join(self.K_PATH, code)
        if not os.path.exists(path):
            return False
        filesize = os.path.getsize(path)
        if filesize == 0:
            return False
        RL = 32
        if filesize % RL != 0:
            return False
        return True
    
    def loadLocal(self, code):
        f = open(os.path.join(self.K_PATH, code), 'rb')
        datas = []
        bs = f.read()
        f.close()
        RL = 32
        if len(bs) % RL != 0:
            print('[KLineDownloader.loadLocal]', code, 'file size invalid')
            return None
        for i in range(0, len(bs) // RL):
            dd = struct.unpack('L7f', bs[i * RL : i * RL + RL])
            it = ItemData(day = dd[0], open = dd[1], close = dd[2], low = dd[3], high = dd[4], vol = dd[5], amount = dd[6], rate = dd[7])
            datas.append(it)
        return datas

    def downloadAll(self, fromIdx = 0, maxDay = None):
        from utils import gn_utils
        codes = []
        for code in gn_utils.ths_gntc_s:
            codes.append(code)
        codes.sort(key = lambda c : c)
        for i, code in enumerate(codes):
            if i < fromIdx: continue
            try:
                ds = self.loadNet(code, i % 2, False)
                self.overWrite(code, ds, toDay = maxDay)
                print('[KLineDownloader] ..', f'{i}/{len(codes)}', code)
            except Exception as e:
                print('[KLineDownloader] Fail load: ', code)
            if i % 2:
                time.sleep(3)

    # day = YYYYMMDD
    def downloadByDay(self, day = None, maxPage = None):
        self.downloadZsCodes()
        from download import ths_iwencai
        if not day:
            day = ths_iwencai.getTradeDaysInt()[-1]
        if type(day) == str:
            day = day.replace('-', '')
        q = f'{day}前复权开盘价,{day}前复权收盘价,{day}前复权最高价,{day}前复权最低价,{day}成交量,{day}成交额,{day}换手率'
        datas = ths_iwencai.iwencai_load_list(q, maxPage = maxPage)
        if not datas:
            return False
        for row in datas:
            columns = ths_iwencai.ThsColumns(row)
            code = columns.getColumnValue('code', str)
            if code[0] not in '036':
                continue
            it = ItemData(day = int(day),
                          open = columns.getColumnValue('开盘价:前复权', float, defaultVal='0'),
                          close = columns.getColumnValue('收盘价:前复权', float, defaultVal='0'),
                          low = columns.getColumnValue('最低价:前复权', float, defaultVal='0'),
                          high = columns.getColumnValue('最高价:前复权', float, defaultVal='0'),
                          vol = columns.getColumnValue('成交量', float, defaultVal='0'),
                          amount = columns.getColumnValue('成交额', float, defaultVal='0'),
                          rate = columns.getColumnValue('换手率', float, defaultVal='0'))
            if it.vol == 0 or it.amount == 0:
                continue
            ok = self.mergeWrite(code, it)
            if not ok:
                print('[KLineDownloader.downloadByDay] merge Fail:', code, it)
        return True
        
    def downloadZsCodes(self):
        codes = ['999999', '399001', '399006']
        self.downloadCodes(codes)

    def downloadCodes(self, codes):
        for code in codes:
            ds = self.loadNet(code, True, True)
            self.overWrite(code, ds)
            time.sleep(1.5)

    # 修复本地数据
    def fixAllNetData(self):
        fs = os.listdir(KLineDownloader.K_PATH)
        fs.sort(key = lambda k: k)
        for code in fs:
            changed, data = self.fixNetData(code)
            if changed:
                KLineDownloader().overWrite(code, data)

    def fixNetData(self, code):
        dm = K_DataModel(code)
        dm.loadLocalData()
        old = dm.data[ : ]
        dm.data.sort(key = lambda x: x.day)
        rmIdxs = []
        for i in range(len(dm.data) - 1, 1, -1):
            if dm.data[i].day == dm.data[i - 1].day:
                rmIdxs.append(i - 1)
        rmIdxs.reverse()
        for i in rmIdxs:
            dm.data.pop(i)
        changed = len(old) != len(dm.data)
        if not changed:
            for i in range(len(old)):
                if old[i].day != dm.data[i].day:
                    changed = True
                    break
        return changed, dm.data

    def getLocalLatestDay(self):
        def isCode(name):
            return name[0] in ('036') and name[0 : 3] != '399'
        fs = os.listdir(self.K_PATH)
        fs = [f for f in fs if isCode(f)]
        order = lambda f: os.path.getmtime(os.path.join(self.K_PATH, f))
        fs.sort(key = order)
        if len(fs) > 100:
            target = fs[100]
        else:
            target = fs[-1]
        dm = Net_K_DataModel(target)
        return dm.getLocalLatestDay()

    def getLocalCodes(self):
        def isCode(code):
            if len(code) != 6:
                return False
            if code in ('399001', '399006', '999999'):
                return True
            if code[0 : 3] == '399':
                return False
            return code[0] in '036'
        fs = os.listdir(KLineDownloader.K_PATH)
        fs = [f for f in fs if isCode(f)]
        fs.sort(key = lambda k: k)
        return fs

    # maxDay: trunck include maxDay
    def trunck(self, code, maxDay):
        dm = K_DataModel(code)
        dm.loadLocalData()
        self.overWrite(code, dm.data, fromDay=None, toDay = maxDay)

if __name__ == '__main__':
    kd = KLineDownloader()
    print('last day=', kd.getLocalLatestDay())
    print('code num=', len(kd.getLocalCodes()))

    #kd.fixAllNetData()
    #kd.fixNetData('601020')

    # kd.trunck('000001', 20260403)
    kdatas = [
        ItemData(day = 20260417, vol = 117, amount = 100, open = 1, close = 2, low = 3, high = 4, rate = 5),
        ItemData(day = 20260413, vol = 9113, amount = 100, open = 1, close = 2, low = 3, high = 4, rate = 5),
        ItemData(day = 20260416, vol = 116, amount = 100, open = 1, close = 2, low = 3, high = 4, rate = 5),
        ItemData(day = 20260401, vol = 101, amount = 100, open = 1, close = 2, low = 3, high = 4, rate = 5),
    ]
    # kd.mergeWrite('000001', kdatas)

    dm = K_DataModel('000001')
    dm.loadLocalData()
    # for i in range(5):
    #     print(dm.data[i])
    # print('--------')
    for i in range(8):
        print(dm.data[-i - 1])
    print('-----end----------')

    #kd.downloadByDay()
    # kd.downloadAll(fromIdx = 382)
    pass