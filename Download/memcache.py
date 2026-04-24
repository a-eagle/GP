import time, datetime

class CacheItem:
    def __init__(self, data, timeout) -> None:
        self.data = data
        self.lastTime = time.time()
        self.lastDay = datetime.date.today()
        self.timeout = timeout

class MemCache:
    def __init__(self) -> None:
        self.datas = {} # key = , value = CacheItem
        self.enableCache = True
    
    def getCache(self, key):
        self._cleanTimeout()
        if not key:
            return None
        rs = self.datas.get(key, None)
        if rs:
            if self._needUpdate(key):
                return None
            return rs.data
        return None
    
    def saveCache(self, key, data, timeout):
        self._cleanTimeout()
        if not self.enableCache:
            return
        it = CacheItem(data, timeout)
        self.datas[key] = it
    
    # @return True | False
    def _needUpdate(self, key):
        item = self.datas.get(key, None)
        if not item:
            return True
        if item.lastDay != datetime.date.today():
            return True
        u = self._checkTimeout(item, item.timeout)
        return u

    def _checkTimeout(self, item, diff):
        if time.time() - item.lastTime <= diff:
            return False
        cacheTime = datetime.datetime.fromtimestamp(item.lastTime)
        now = datetime.datetime.now()
        cacheTime = self._adjustDiffTime(cacheTime)
        now = self._adjustDiffTime(now)
        if now - cacheTime <= diff:
            return False
        return True
    
    def _adjustDiffTime(self, time : datetime.datetime):
        t = time.hour * 100 + time.minute
        if t >= 1500:
            return datetime.datetime(time.year, time.month, time.day, 15, 0, 0).timestamp()
        if t >= 1300:
            s = time.timestamp() - 1.5 * 60 * 60 # 1.5 hour
            return s
        if t >= 1130:
            zw = datetime.datetime(time.year, time.month, time.day, 11, 30, 0).timestamp()
            return zw
        if t >= 930:
            return time.timestamp()
        return datetime.datetime(time.year, time.month, time.day, 9, 25, 0).timestamp()
        
    
    def _cleanTimeout(self):
        for k in list(self.datas.keys()):
            item = self.datas[k]
            if self._checkTimeout(item, item.timeout):
                self.datas.pop(k)

# 根据当前时间，和是否在交易时间内计算超时时间
def calcDynamicTimeout(inTime, outTime):
    from download import ths_iwencai
    from utils import cutils
    if not ths_iwencai.isTradeDay():
        return outTime
    now = datetime.datetime.now()


cache = MemCache()