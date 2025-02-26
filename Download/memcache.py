import time, datetime

class CacheItem:
    def __init__(self, data) -> None:
        self.data = data
        self.lastTime = time.time()
        self.lastDay = datetime.date.today()

class MemCache:
    TIMEOUT = {
        'default': 10 * 60,
        'cls-pankou-5': 60,
        'cls-pankou-vol': 60,
        'cls-basic': 10 * 60 * 60,
        'cls-scqx': 3 * 60,
        'cls-hot-tc': 30,
        '30-minuts': 30 * 60,
    }
    def __init__(self) -> None:
        self.datas = {} # key = code + kind, value = CacheItem
    
    def getCache(self, code, kind):
        if not code or not kind:
            return None
        key = code + kind
        rs = self.datas.get(key, None)
        if rs:
            return rs.data
        return None
    
    def saveCache(self, code, data, kind):
        it = CacheItem(data)
        self.datas[code + kind] = it
    
    # @return True | False
    def needUpdate(self, code, kind):
        if not code or not kind:
            return False
        key = f'{code}{kind}'
        item = self.datas.get(key, None)
        if not item:
            return True
        if item.lastDay != datetime.date.today():
            return True
        u = self._checkTime(item, self._getTimeout(kind))
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
    
    def _getTimeout(self, kind):
        if kind in MemCache.TIMEOUT:
            return MemCache.TIMEOUT[kind]
        return MemCache.TIMEOUT['default']
        
cache = MemCache()