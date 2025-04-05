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
    
    def getCache(self, key):
        if not key:
            return None
        rs = self.datas.get(key, None)
        if rs:
            if self._needUpdate(key):
                return None
            return rs.data
        return None
    
    def saveCache(self, key, data, timeout):
        it = CacheItem(data, timeout)
        self.datas[key] = it
    
    # @return True | False
    def _needUpdate(self, key):
        item = self.datas.get(key, None)
        if not item:
            return True
        if item.lastDay != datetime.date.today():
            return True
        u = self._checkTime(item, item.timeout)
        return u

    def _checkTime(self, item, diff):
        if time.time() - item.lastTime <= diff:
            return False
        lt = datetime.datetime.fromtimestamp(item.lastTime)
        mm = lt.hour * 100 + lt.minute
        now = datetime.datetime.now()
        nmm = now.hour * 100 + now.minute
        if mm > 1500 and nmm > 1500:
            return False
        if mm < 930 and nmm < 930:
            return False
        return True
        
cache = MemCache()