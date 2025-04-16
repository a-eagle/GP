import ctypes, os, sys, requests, json, traceback, datetime

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import memcache

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
    
    def loadFenShi(self, code):
        item = memcache.cache.getCache(f'cls-fs:{code}')
        if item:
            return item
        url = 'https://x-quote.cls.cn/quote/stock/tline?'
        scode = self._getTagCode(code)
        params = f'app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code={scode}&sv=7.7.5'
        url += self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        data['code'] = code
        if data and 'line' in data:
            data['line'] = self._toStds(data['line'], False)
        memcache.cache.saveCache(f'cls-fs:{code}', data, 60)
        return data
    
    # day = None : 当日分时 只能用于指数
    # day = int | YYYYMMDD | YYYY-MM-DD
    def loadIndexFenShi(self, code, day = None):
        url = 'https://x-quote.cls.cn/quote/index/tline?'
        if not day:
            sday = ''
        elif type(day) == int:
            sday = f"&date={day}"
        elif type(day) == str:
            sday = day.replace('-', '')
            day = int(sday)
            sday = f"&date={day}"
        params = f'app=CailianpressWeb{sday}&os=web&sv=8.4.6'
        url += self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        rs = {'code': code, 'date': []}
        rs['line'] = self._toStds(data, False)
        if rs['line']: 
            rs['date'].append(rs['line'][0].day)
        elif day:
            rs['date'].append(day)
        return rs
        
    def getVal(self, data, name, _type, default):
        if name not in data:
            return default
        val = data[name]
        if val == None:
            return default
        return _type(val)

    # 基本信息
    def loadBasic(self, code):
        KIND = 'cls-basic'
        item = memcache.cache.getCache(f'cls-basic-{code}')
        if item:
            return item
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
        rt['code'] = data['secu_code'][2 : ] if data['secu_code'][0] == 's' else data['secu_code']
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
        memcache.cache.saveCache(f'cls-basic-{code}', rt, 60)
        return rt

    # 近5日分时
    def loadHistory5FenShi(self, code):
        KIND = 'timeline'
        item = memcache.cache.getCache(f'cls-{code}-5')
        if item:
            return item
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
        data['code'] = code
        if data and ('line' in data):
            data['line'] = self._toStds(data['line'], False)
        item = memcache.cache.saveCache(f'cls-{code}-5', data, 60)
        return data

    def _toStds(self, datas, kline):
        if not datas:
            return datas
        rs = []
        for d in datas:
            if kline:
                rs.append(self._toStdKl(d))
            else:
                dx = self._toStdFs(d)
                if dx: rs.append(dx)
        return rs

    def _toStdFs(self, d):
        from download import datafile
        if not d:
            return None
        price = self.getVal(d, 'last_px', float, 0)
        if price == 0:
            return None
        ts = datafile.ItemData()
        ts.day = self.getVal(d, 'date', int, 0)
        ts.time = self.getVal(d, 'minute', int, 0)
        ts.price = price
        ts.vol = self.getVal(d, 'business_amount', int, 0)
        ts.amount = self.getVal(d, 'business_balance', int, 0)
        ts.avgPrice = self.getVal(d, 'av_px', float, 0)
        return ts
    
    def _toStdKl(self, d):
        from download import datafile
        if not d:
            return None
        ts = datafile.ItemData()
        if 'secu_code' in d:
            sc = d['secu_code']
            if ('cls' in sc) or ('sh0' in sc):
                ts.code = sc
            else:
                ts.code = sc[2 : ]
        ts.day = self.getVal(d, 'date', int, 0)
        ts.vol = self.getVal(d, 'business_amount', int, 0)
        ts.amount = self.getVal(d, 'business_balance', int, 0)
        ts.open = self.getVal(d, 'open_px', float, 0)
        ts.close = self.getVal(d, 'close_px', float, 0)
        ts.low = self.getVal(d, 'low_px', float, 0)
        ts.high = self.getVal(d, 'high_px', float, 0)
        ts.pre = self.getVal(d, 'preclose_px', float, 0)
        ts.zhangFu = self.getVal(d, 'change', float, 0) * 100 # %  zf = 涨幅
        ts.rate = self.getVal(d, 'tr', float, 0) * 100 # %
        return ts

    # K线数据
    # limit : K线数量
    # period: 周期 'day' | 'week' | 'month'
    def loadKline(self, code, limit = 1200, period = 'day'):
        item = memcache.cache.getCache(f'cls-{code}-{period}')
        if item:
            return item
        period = period.upper()
        if period == 'DAY': period = 'fd1'
        elif period == 'WEEK': period = 'fw'
        elif period == 'MONTH': period = 'fm'
        params = {
            'secu_code': self._getTagCode(code),
            'app': 'CailianpressWeb',
            'os': 'web',
            'sv': '7.7.5',
            'offset': 0,
            'limit': limit,
            'type': period
        }
        url = f'https://x-quote.cls.cn/quote/stock/kline?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        rs = self._toStds(data, True)
        memcache.cache.saveCache(f'cls-{code}-{period}', rs, 60)
        #print(data)
        return rs
    
    # 5档盘口
    # {b_amount_1...5 买1-5手    b_px_1...5: 买1-5价 preclose_px 昨日收盘价 s_amount_1...5 s_px_1...5}
    def loadPanKou5(self, code):
        try:
            KIND = 'cls-pankou-5'
            item = memcache.cache.getCache(f'pk5-{code}')
            if item: 
                return item
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
            memcache.cache.saveCache(f'pk5-{code}', data, 60)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    # 盘口成交量
    # {end: int, volume: [{change_vol=2, change_vol_color=0, last_px=23.31, minute=102800}, ...] }
    def loadPanKouVol(self, code):
        try:
            KIND = 'cls-pankou-vol'
            item = memcache.cache.getCache(f'pk-vol-{code}')
            if item:
                return item
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
            memcache.cache.saveCache(f'pk-vol-{code}', data, 60)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    # 热度题材
    def loadHotTC(self, day):
        today = datetime.date.today().strftime('%Y-%m-%d')
        if isinstance(day, datetime.date):
            cday = day.strftime('%Y-%m-%d')
        elif isinstance(day, str):
            if len(day) == 8:
                cday = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
            else:
                cday = day
        elif isinstance(day, int):
            cday = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
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
        return data

    # 市场情绪 {day: YYYY-MM-DD, degree: int}
    def loadDegree(self):
        item = memcache.cache.getCache(f'cls-scqx')
        if item:
            return item
        url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        day = js['data']['date']
        degree = js['data']['market_degree'] or 0
        degree = int(float(degree) * 100)
        data = {'day': day, 'degree': degree}
        memcache.cache.saveCache(f'cls-scqx', data, 60)
        return data
    
    # 所有的板块、概念
    # type_ = 'industry' | 'concept'
    # page = 1....
    def _loadZS_TN(self, type_):
        params = {
            'app' :'CailianpressWeb', 'os': 'web', 'page': '100','type': type_,
            'rever': '1', 'sv': '8.4.6', 'way': 'change'
        }
        url = f'https://x-quote.cls.cn/web_quote/plate/plate_list?' + self.signParams(params)
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        isAll = js['data']['is_all'] # 是否是全部数据
        data = js['data']['plate_data']
        rs = []
        stype = 'HY' if type_ == 'industry' else 'GN'
        for d in data:
            rs.append({'code': d['secu_code'], 'name': d['secu_name'], 'type_': stype})
        return rs
    
    # 所有的板块、概念
    def loadAllZS(self):
        rs = self._loadZS_TN('industry')
        rs2 = self._loadZS_TN('concept')
        rs.extend(rs2)
        return rs

    # zs set to {}
    def loadBkGnOfCode(self, code, zs = {}):
        from orm import cls_orm
        if type(code) == int:
            code = f'{code :06d}'
        if code[0 : 2] in ('sh', 'sz'):
            code = code[2 : ]
        if code[0] not in ('0', '3', '6'):
            return None
        if not zs:
            qr = cls_orm.CLS_ZS.select().dicts()
            for it in qr:
                zs[it['code']] = it
        params = f'app=CailianpressWeb&os=web&secu_code={self._getTagCode(code)}&sv=8.4.6'
        url = 'https://x-quote.cls.cn/web_quote/stock/assoc_plate?' + self.signParams(params)
        resp = requests.get(url)
        cnt = resp.content.decode('utf-8')
        js = json.loads(cnt)
        data = js['data']
        rs = cls_orm.CLS_GNTC()
        rs.code = code
        for d in data:
            c, n = d['secu_code'], d['secu_name']
            if c not in zs:
                continue
            type_ = zs[c]['type_']
            if type_ == 'HY': 
                rs.hy_code += c + ';'
                rs.hy += n + ';'
            else:
                rs.gn_code += c + ';'
                rs.gn += n + ';'
        if rs.gn_code:
            rs.gn_code = rs.gn_code[0 : -1]
            rs.gn = rs.gn[0 : -1]
        if rs.hy_code:
            rs.hy_code = rs.hy_code[0 : -1]
            rs.hy = rs.hy[0 : -1]
        return rs

    # 最新交易日的涨跌票的数量分布
    def getZDFenBu(self):
        #from Download import ths_iwencai
        #days = ths_iwencai.getTradeDays_Cache()
        #if not days:
        #    return None
        #lastDay = days[-1]
        #lastDay = f"{lastDay[0 : 4]}-{lastDay[4 : 6]}-{lastDay[6 : 8]}"
        resp = requests.get('https://x-quote.cls.cn/quote/index/home?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737')
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        v = js['data']['up_down_dis']
        if not v['status']:
            return None
        # modify real zt, dt num
        
        rs = {
            'zt': v['up_num'], 'dt': v['down_num'], 'up': v['rise_num'], 'down': v['fall_num'], 'zero': v['flat_num'],
            'up_2': v['up_2'], 'up_4': v['up_4'], 'up_6': v['up_6'], 'up_8': v['up_8'], 'up_10': v['up_10'],
            'down_2': v['down_2'], 'down_4': v['down_4'], 'down_6': v['down_6'], 'down_8': v['down_8'], 'down_10': v['down_10']
        }
        return rs

if __name__ == '__main__':
    #m = signByStr('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012')
    #print(m)
    #signByStr('app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz301488&sv=7.7.5')
    cu = ClsUrl()
    #ds = cu.loadBkGnOfCode('688041')
    #print(ds.__data__)
    #ClsUrl().loadDegree()
    pass
    #cu.loadHotTC(20241104)
    rs = cu.loadHotTC('20250408')
    print(rs)