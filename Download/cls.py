import ctypes, os, sys, requests, json, traceback, datetime

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import datafile
from Download import memcache

PX = os.path.join(os.path.dirname(__file__), 'cls-sign.dll')
mydll = ctypes.CDLL(PX)

def signByStr(s : str):
    return _c_digest(s)

def signByDict(params : dict):
    if not params:
        return signByStr('')
    ks = list(params.keys()).sort()
    sl = []
    for k in ks:
        sl.append(f'{k}={ks[k]}')
    s = '&'.join(sl)
    rs = _c_digest(s)
    return rs

def _c_digest(s : str):
    digest = mydll.digest # 
    digest.restype = ctypes.c_char_p
    digest.argtypes = [ctypes.c_char_p]

    bs = s.encode('utf-8')
    rs : bytes = digest(bs) # ctypes.c_char_p(bs)
    r = rs.decode('utf-8')
    #print('[_c_digest]', r)
    return r

class ClsUrl:
    def __init__(self) -> None:
        self.reqHeaders = {'Accept': 'text/plain, */*; q=0.01',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'zh-CN,zh;q=0.9'}

    def _getTagCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        if code[0] == '6':
            return 'sh' + code
        if code[0] == '0' or code[0] == '3':
            return 'sz' + code
        if code == '999999':
            return 'sh000001'
        return code
    
    def signParams(self, params):
        if isinstance(params, str):
            sign = signByStr(params)
            return params + '&sign=' + sign
        if isinstance(params, dict):
            ks = list(params.keys())
            ks.sort()
            sl = []
            for k in ks:
                sl.append(f'{k}={params[k]}')
            sparams = '&'.join(sl)
            sign = signByStr(sparams)
            return sparams + '&sign=' + sign
        return None # error params

    # 当日分时
    def loadFenShi(self, code):
        url = 'https://x-quote.cls.cn/quote/stock/tline?'
        scode = self._getTagCode(code)
        params = f'app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code={scode}&sv=7.7.5'
        url += self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        if data and 'line' in data:
            self._toStds(data['line'])
        data['dataArr'] = data.get('line', None)
        #print(js['data'])
        return data
    
    def getVal(self, data, name, _type, default):
        if name not in data:
            return default
        val = data[name]
        if val == None:
            return default
        return _type(val)

    # 基本信息
    def loadBasic(self, code):
        try:
            KIND = 'cls-basic'
            if not memcache.cache.needUpdate(code, KIND):
                return memcache.cache.getCache(code, KIND)
            params = {
                'secu_code': self._getTagCode(code),
                'fields': 'open_px,av_px,high_px,low_px,change,change_px,down_price,change_3,change_5,qrr,entrust_rate,tr,amp,TotalShares,mc,NetAssetPS,NonRestrictedShares,cmc,business_amount,business_balance,pe,ttm_pe,pb,secu_name,secu_code,trade_status,secu_type,preclose_px,up_price,last_px',
                'app': 'CailianpressWeb',
                'os': 'web',
                'sv': '7.7.5'
            }
            url = f'https://x-quote.cls.cn/quote/stock/basic?' + self.signParams(params)
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            data = js['data']
            rt = {}
            rt['pre'] = self.getVal(data, 'preclose_px', float, 0) # 昨日收盘价
            rt['code'] = data['secu_code'][2 : ]
            rt['name'] = data['secu_name']
            rt['vol'] = self.getVal(data, 'business_amount', int, 0) # int 股
            rt['amount'] = self.getVal(data, 'business_balance', int, 0) # int 元
            rt['open'] = self.getVal(data, 'open_px', float, 0)
            rt['high'] = self.getVal(data, 'high_px', float, 0)
            rt['close'] = self.getVal(data, 'last_px', float, 0)
            rt['low'] = self.getVal(data, 'low_px', float, 0)
            #pre = rt['pre'] or rt['open']
            #if pre != 0:
            #    rt['涨幅'] = (rt['close'] - pre) / pre * 100
            rt['涨幅'] = self.getVal(data, 'change', float, 0) * 100
            rt['委比'] = self.getVal(data, 'entrust_rate', float, 0) * 100 # 0 ~ 100%
            rt['总市值'] = self.getVal(data, 'mc', int, 0) # int 元
            rt['流通市值'] = self.getVal(data, 'cmc', int, 0) # int 元
            rt['每股净资产'] = self.getVal(data, 'NetAssetPS', float, 0)
            rt['流通股本'] = self.getVal(data, 'NonRestrictedShares', int, 0)
            rt['总股本'] = self.getVal(data, 'TotalShares', int, 0)
            rt['市净率'] = self.getVal(data, 'pb', float, 0)
            rt['市盈率_静'] = self.getVal(data, 'pe', float, 0)
            rt['市盈率_TTM'] = self.getVal(data, 'ttm_pe', float, 0)
            #print(rt)
            memcache.cache.saveCache(code, rt, KIND)
            return rt
        except Exception as e:
            traceback.print_exc()
    
    # 近5日分时
    def loadHistory5FenShi(self, code):
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5'
        }
        url = f'https://x-quote.cls.cn/quote/stock/tline_history?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        if data and 'line' in data:
            self._toStds(data['line'])
        #print(data)
        return data

    def _toStds(self, datas):
        if not datas:
            return
        for d in datas:
            self._toStd(d)
    
    def _toStd(self, data):
        data['day'] = data['date']
        if 'secu_code' in data:
            sc = data['secu_code']
            if ('cls' in sc) or ('sh0' in sc):
                data['code'] = sc
            else:
                data['code'] = sc[2 : ]
        if 'open_px' in data: data['open'] = self.getVal(data, 'open_px', float, 0)
        if 'close_px' in data: data['close'] = self.getVal(data, 'close_px', float, 0)
        if 'last_px' in data: data['close'] = self.getVal(data, 'last_px', float, 0)
        if 'low_px' in data: data['low'] = self.getVal(data, 'low_px', float, 0)
        if 'high_px' in data: data['high'] = self.getVal(data, 'high_px', float, 0)
        if 'preclose_px' in data: data['pre'] = self.getVal(data, 'preclose_px', float, 0)
        if 'change' in data: data['zf'] = self.getVal(data, 'change', float, 0) * 100 # %  zf = 涨幅
        if 'tr' in data: data['rate'] = self.getVal(data, 'tr', float, 0) * 100 # %
        if 'business_amount' in data: data['vol'] = self.getVal(data, 'business_amount', float, 0)
        if 'business_balance' in data: data['amount'] = self.getVal(data, 'business_balance', float, 0)
        if 'minute' in data:
            data['time'] = data['minute']
            data['price'] = data['close']
        if 'av_px' in data:
            data['avgPrice'] = self.getVal(data, 'av_px', float, 0)

    # K线数据
    # limit : K线数量
    def loadKline(self, code, limit = 1200):
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5',
            'offset': 0,
            'limit': limit,
            'type': 'fd1'
        }
        url = f'https://x-quote.cls.cn/quote/stock/kline?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        for d in data:
            self._toStd(d)
        #print(data)
        return data
    
    # 5档盘口
    # {b_amount_1...5 买1-5手    b_px_1...5: 买1-5价 preclose_px 昨日收盘价 s_amount_1...5 s_px_1...5}
    def loadPanKou5(self, code):
        try:
            KIND = 'cls-pankou-5'
            if not memcache.cache.needUpdate(code, KIND):
                return memcache.cache.getCache(code, KIND)
            params = {
                'secu_code': self._getTagCode(code),
                'app': 'CailianpressWeb',
                'field': 'five',
                'os': 'web',
                'sv': '7.7.5',
            }
            url = f'https://x-quote.cls.cn/quote/stock/volume?' + self.signParams(params)
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            data = js['data']
            #print(data)
            memcache.cache.saveCache(code, data, KIND)
            return data
        except Exception as e:
            traceback.print_exc()
        return None
    
    # 盘口成交量
    # {end: int, volume: [{change_vol=2, change_vol_color=0, last_px=23.31, minute=102800}, ...] }
    def loadPanKouVol(self, code):
        try:
            KIND = 'cls-pankou-vol'
            if not memcache.cache.needUpdate(code, KIND):
                return memcache.cache.getCache(code, KIND)
            params = {
                'secu_code': self._getTagCode(code),
                'app': 'CailianpressWeb',
                'field': 'vol',
                'os': 'web',
                'sv': '7.7.5',
            }
            url = f'https://x-quote.cls.cn/quote/stock/volume?' + self.signParams(params)
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            data = js['data']
            #print(data)
            memcache.cache.saveCache(code, data, KIND)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    # 热度题材
    def loadHotTC(self, day):
        try:
            today = datetime.date.today().strftime('%Y-%m-%d')
            KIND = 'cls-hot-tc'
            if isinstance(day, datetime.date):
                cday = day.strftime('%Y-%m-%d')
            elif isinstance(day, str):
                if len(day) == 8:
                    cday = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
            elif isinstance(day, int):
                cday = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
            if today > cday:
                cc = memcache.cache.getCache(cday, KIND)
                if cc:
                    return cc
            if not memcache.cache.needUpdate(cday, KIND):
                return memcache.cache.getCache(cday, KIND)
            params = {
                'app': 'CailianpressWeb',
                'cdate': cday,
                'os': 'web',
                'sv': '7.7.5',
            }
            url = 'https://www.cls.cn/v3/transaction/anchor?' + self.signParams(params)
            resp = requests.get(url, headers = self.reqHeaders)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            data = js['data']
            #print(data)
            memcache.cache.saveCache(cday, data, KIND)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    # 市场情绪 {day: YYYY-MM-DD, degree: int}
    def loadDegree(self):
        try:
            KIND = 'cls-scqx'
            if not memcache.cache.needUpdate(KIND, KIND):
                return memcache.cache.getCache(KIND, KIND)
            url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            day = js['data']['date']
            degree = js['data']['market_degree'] or 0
            degree = int(float(degree) * 100)
            data = {'day': day, 'degree': degree}
            memcache.cache.saveCache(KIND, data, KIND)
            return data
        except Exception as e:
            traceback.print_exc()
        return None
        
class ClsDataFile(datafile.DataFile):
    def __init__(self, code, dataType):
        #super().__init__(code, dataType, flag)
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        self.dataType = dataType
        self.name = ''
        self.data = []

    def loadDataFile(self):
        if self.dataType == self.DT_DAY:
            self._loadDataFile_KLine()
        else:
            self._loadDataFile_FS()

    def _loadDataFile_KLine(self):
        datas = ClsUrl().loadKline(self.code, 1200)
        for ds in datas:
            it = datafile.ItemData()
            it.day = ds['date']
            it.open = ds['open_px']
            it.close = ds['close_px']
            it.low = ds['low_px']
            it.high = ds['high_px']
            it.amount = int(ds['business_balance'])
            it.vol = int(ds['business_amount'])
            it.rate = ds.get('tr', 0) * 100
            self.data.append(it)
        
    def _loadDataFile_FS(self):
        datas = ClsUrl().loadHistory5FenShi(self.code)
        for ds in datas:
            it = datafile.ItemData()
            it.day = ds['date']
            it.time = ds['minute']
            it.open = int(ds['open_px'] * 100 + 0.5)
            it.close = int(ds['close_px'] * 100 + 0.5)
            it.low = int(ds['low_px'] * 100 + 0.5)
            it.high = int(ds['high_px'] * 100 + 0.5)
            it.amount = int(ds['business_balance'])
            it.vol = int(ds['business_amount'])
            self.data.append(it)

if __name__ == '__main__':
    #signByStr('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012')
    #signByStr('app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz301488&sv=7.7.5')
    #ClsUrl().loadHistory5FenShi('cls80133') #cls80133
    #ClsUrl().loadDegree()
    pass
    u = ClsUrl()
    u.loadHotTC(20241104)