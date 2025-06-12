import threading, sys, traceback, datetime, json, requests
import flask, flask_cors
import win32con, win32gui, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from ui import base_win, timeline, kline_utils, kline_win
from download import ths_iwencai, datafile, ths_iwencai, henxin, cls, memcache
from orm import d_orm, def_orm, cls_orm, chrome_orm, lhb_orm, ths_orm
from utils import hot_utils, gn_utils

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__, static_folder = '', template_folder = '')
        flask_cors.CORS(self.app)
        self.uiThread = None

    def start(self):
        #th = threading.Thread(target = self.runner, daemon = True)
        #th.start()
        base_win.ThreadPool.instance().start()
        self.uiThread = base_win.Thread()
        self.uiThread.start()
        self.runner()

    def runner(self):
        self.app.add_url_rule('/openui/<type_>/<code>', view_func = self.openUI, methods = ['GET', 'POST'])
        self.app.add_url_rule('/get-hots', view_func = self.getHots)
        self.app.add_url_rule('/get-time-degree', view_func = self.getTimeDegree)
        self.app.add_url_rule('/query-by-sql/<dbName>', view_func = self.queryBySql)
        self.app.add_url_rule('/get-trade-days', view_func = self.getTradeDays)
        self.app.add_url_rule('/iwencai', view_func = self.queryIWenCai)
        self.app.add_url_rule('/top100-vol', view_func = self.getTop100Vol)
        self.app.add_url_rule('/get-fenshi/<code>', view_func = self.getFenShi)
        self.app.add_url_rule('/query-codes-info', view_func = self.queryCodesInfo, methods = ['POST'])
        self.app.add_url_rule('/mark-color', view_func = self.markColor, methods = ['POST'])
        self.app.add_url_rule('/mynote', view_func = self.myNote, methods = [ 'POST'])
        self.app.add_url_rule('/plate/<code>', view_func = self.getPlate)
        self.app.add_url_rule('/industry/<code>', view_func = self.getIndustry)
        self.app.add_url_rule('/get-anchors', view_func = self.getAnchors)
        self.app.add_url_rule('/load-one-anchor', view_func = self.getOneAnchor)
        self.app.add_url_rule('/load-kline/<code>', view_func = self.loadKLine)
        self.app.run('localhost', 8080, use_reloader = False, debug = False)

    def loadKLine(self, code):
        hx = henxin.HexinUrl()
        rs = hx.loadKLineData(code)
        datas = []
        KEYS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol')
        for d in rs['data']:
            obj = {}
            for k in KEYS:
                obj[k] = getattr(d, k, 0)
            datas.append(obj)
        return datas
    
    def getOneAnchor(self):
        day = flask.request.args.get('day', '')
        if len(day) == 8:
            day = f"{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}"
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day == day).dicts()
        rs = []
        for it in qr:
            rs.append(it)
        return rs

    def getAnchors(self):
        days = int(flask.request.args.get('days', '60'))
        tds = ths_iwencai.getTradeDays()
        fromDay = str(tds[-days])
        fromDay = f"{fromDay[0 : 4]}-{fromDay[4 : 6]}-{fromDay[6 : 8]}"
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day >= fromDay).dicts()
        rs = []
        one = None
        lastDay = None
        for it in qr:
            if it['day'] != lastDay:
                one = []
                rs.append(one)
                lastDay = it['day']
            one.append(it)
        rs.sort(key = lambda item : item[0]['day'], reverse = True)
        return rs

    def _openUI_Timeline(self, code, day):
        win = timeline.TimelinePanKouWindow()
        win.createWindow(None, (0, 0, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
        win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
        win.load(code, day)
        win32gui.PumpMessages()

    def _openUI_Kline(self, code, params):
        win = kline_utils.createKLineWindowByCode(code)
        win.changeCode(code)
        if params:
            js = json.loads(params.decode())
            win.klineWin.marksMgr.setMarkDay(js.get('day'), None)
            cs : list = js.get('codes', [])
            idx = cs.index(code) if code in cs else -1
            win.setCodeList(cs, idx)
        win.klineWin.makeVisible(-1)
        win32gui.SetWindowPos(win.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(win.hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.PumpMessages()

    def openUI(self, type_, code):
        def run(func, *args):
            func(*args)
        if type_ == 'timeline':
            day = flask.request.args.get('day', None)
            thread = threading.Thread(target = run, args = (self._openUI_Timeline, code, day), daemon = True)
            thread.start()
        elif type_ == 'kline':
            thread = threading.Thread(target = run, args = (self._openUI_Kline, code, flask.request.data), daemon = True)
            thread.start()
        else:
            return {'code': 2, 'msg': f'Type Error: {type_}'}
        return {'code': 0, 'msg': 'OK'}
    
    def getHots(self):
        day = flask.request.args.get('day', None)
        hz = hot_utils.DynamicHotZH.instance()
        if day and len(day) >= 8:
            rs = hz.getHotsZH(day)
        else:
            rs = hz.getNewestHotZH()
        if not rs:
            return {}
        m = {}
        for k in rs:
            obj = rs[k]
            code = f'{k :06d}'
            it = m[code] = {'code': code, 'hots': obj['zhHotOrder']}
            it['name'] = gn_utils.get_THS_GNTC_Attr(code, 'name')
        return m
    
    # day = YYYY-MM-DD
    def getTimeDegree(self):
        day = flask.request.args.get('day', None)
        if not day:
            qr = cls_orm.CLS_SCQX_Time.select(pw.fn.max(cls_orm.CLS_SCQX_Time.day)).tuples()
            for q in qr:
                day = q[0]
                break
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        qr = cls_orm.CLS_SCQX_Time.select().where(cls_orm.CLS_SCQX_Time.day == day).dicts()
        rs = []
        for q in qr:
            q['degree'] = q['zhqd']
            rs.append(q)
        return rs
    
    def _getDBs(self):
        dbs = {'cls_gntc': cls_orm.db_gntc,  'lhb': lhb_orm.db_lhb, 'def': def_orm.db_def,
               'ths_gntc': ths_orm.db_gntc, 'hot': ths_orm.db_hot, 'hot_zh': ths_orm.db_hot_zh,
               'ths_zs': ths_orm.db_thszs, 'chrome': chrome_orm.db_chrome, 'cls': cls_orm.db_cls}
        return dbs

    def queryBySql(self, dbName):
        dbs = self._getDBs()
        if dbName not in dbs:
            return {'code': 1, 'msg': f'Not find dbName: "{dbName}"'}
        sql = flask.request.args.get('sql', None)
        if not sql:
            return {'code': 1, 'msg': f'No sql'}
        db : pw.SqliteDatabase = dbs[dbName]
        c = db.cursor()
        c.execute(sql)
        ds = c.description
        rs = c.fetchall()
        ex = []
        for r in rs:
            item = {}
            for i, k in enumerate(r):
                item[ds[i][0]] = k
            ex.append(item)
        return ex
    
    # params = {op: 'save | get', data?: {code, secu_code?, name, color, day}  }
    def markColor(self):
        params = flask.request.data
        js = json.loads(params.decode())
        mrs = {}
        rs = []
        qr = chrome_orm.MyMarkColor.select()
        for it in qr:
            rs.append(it.__data__)
            mrs[it.code] = it
        if js['op'] == 'get':
            return rs
        data = js['data']
        if not data:
            return 'ok'
        code = data['code']
        if not data['color']:
            if code in mrs:
                mrs[code].delete_instance()
        else:
            if code in mrs:
                mrs[code].day = data['day']
                mrs[code].color = data['color']
                mrs[code].save()
            else:
                secu_code = data.get('secu_code', self._getSecuCode(code))
                chrome_orm.MyMarkColor.create(code = code, secu_code = secu_code, day = data.get('day', ''), name = data['name'], color = data['color'])
        return 'ok'
    
    # params = {op: 'save | get', name: xxx, cnt?: xxx}
    def myNote(self):
        params = flask.request.data
        js = json.loads(params.decode())
        obj = chrome_orm.MyNote.get_or_none(chrome_orm.MyNote.tag == js['name'])
        if js['op'] == 'get':
            return obj.cnt if obj else ''
        if not obj:
            chrome_orm.MyNote.create(tag = js['name'], cnt = js['cnt'] )
        else:
            obj.cnt = js['cnt']
            obj.save()
        return 'ok'

    def getTradeDays(self):
        days = ths_iwencai.getTradeDays(180)
        rs = []
        for d in days:
            rs.append(f"{d[0 : 4]}-{d[4 : 6]}-{d[6 : 8]}")
        return rs

    def queryIWenCai(self):
        try:
            q = flask.request.args.get('q', None)
            if not q:
                return None
            maxPage = flask.request.args.get('maxPage', 1, int)
            if maxPage < 0:
                maxPage = None
            data = ths_iwencai.iwencai_load_list(q, maxPage = maxPage)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    def getTop100Vol(self):
        try:
            day = flask.request.args.get('day', None)
            data = ths_iwencai.download_vol_top100(day)
            return data
        except Exception as e:
            traceback.print_exc()
        return None

    def getFenShi(self, code):
        day = flask.request.args.get('day', None)
        lastTradeDay = ths_iwencai.getTradeDays()[-1]
        today = datetime.date.today().strftime('%Y%m%d')
        if not day:
            day = lastTradeDay
        day = day.replace('-', '')
        rs = {'code': code, 'pre': 0, 'line': None}
        if today == lastTradeDay and day == today: # load from server
            if (code[0 : 3] == 'cls'):
                data = cls.ClsUrl().loadHistory5FenShi(code)
                lines = data['line']
                if lines[-1].time == 1500:
                    preLastIdx = -1 - 241
                else:
                    preLastIdx = -1 - len(data['line']) % 241
                rs['pre'] = lines[preLastIdx].price
                rs['line'] = lines[preLastIdx + 1 : ]
            else:
                hx = henxin.HexinUrl()
                data = hx.loadUrlData(hx.getFenShiUrl(code))
                rs['pre'] = data['pre']
                rs['line'] = data['line']
        else:
            df = datafile.T_DataModel(code)
            df.loadLocalData(day)
            rs['pre'] = df.pre
            rs['line'] = df.data
        if not rs['line']:
            return rs
        rsd = []
        KS = ('day', 'time', 'price', 'avgPrice', 'amount', 'vol')
        for ln in rs['line']:
            item = {}
            for k in KS: 
                item[k] = getattr(ln, k)
            rsd.append(item)
        rs['line'] = rsd
        return rs
    
    def _getSecuCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        code = code.strip()
        if len(code) != 6:
            return code
        if code[0] == '6':
            return f'sh{code}'
        return f'sz{code}'

    # {cols?:[ztReason, hots:[yyyy-mm-dd] ], codes:[]}
    def queryCodesInfo(self):
        from utils import hot_utils
        params = flask.request.data
        js = json.loads(params.decode())
        cols = js.get('cols', ['ztReason', 'hots'])
        mcols = {}
        for c in cols:
            if 'hots:' in c:
                mcols['hots'] =  c[c.index(':') + 1 : ].strip()
            else:
                mcols[c] = True
        codes = js['codes']
        ncodes = []
        SS =  ('sz', 'sh')
        for c in codes:
            if len(c) == 6:
                ncodes.append(c)
            elif len(c) == 8 and c[0 : 2] in SS:
                ncodes.append(c[2 : ])
        hz = hot_utils.DynamicHotZH.instance()
        rs = {}
        for code in ncodes:
            it = {'code': code, 'secu_code': self._getSecuCode(code)}
            rs[it['secu_code']] = it
            cl = gn_utils.cls_gntc_s.get(code, None) or {}
            th = gn_utils.ths_gntc_s.get(code, None) or {}
            it['name'] = cl.get('name', '') or th.get('name', '')
            it['cls_hy'] = cl.get('hy', '')
            it['ths_hy'] = th.get('hy', '')
            it['ltsz'] = th.get('ltsz', 0) # 流通市值
            if 'hots' in mcols:
                day = mcols['hots']
                if not day or day == True or len(day) < 8:
                    day = None
                hh = hz.getHotsZH(day)
                hc = hh.get(int(code), None) if hh else None
                it['hots'] = 0 if not hc else hc['zhHotOrder']
            if 'ztReason' in mcols:
                zt = gn_utils.get_CLS_THS_ZT_Reason(code)
                it['ths_ztReason'] = zt['ths_ztReason'] if zt else ''
                it['cls_ztReason'] = zt['cls_ztReason'] if zt else ''
        return rs

    def getPlate(self, code):
        try:
            if code[0 : 3] == 'cls':
                return self.getPlateCls(code)
            if code[0 : 2] == '88':
                return self.getPlateThs(code)
        except Exception as e:
            traceback.print_exc()
        return []
    
    def getIndustry(self, code):
        try:
            if code[0 : 3] == 'cls':
                return self.getIndustryCls(code)
        except Exception as e:
            traceback.print_exc()
        return []
    
    def getPlateCls(self, code):
        try:
            day = flask.request.args.get('day', None)
            period = flask.request.args.get('period', 30)
            subByHots = flask.request.args.get('subByMaxHots', '')
            params = f'app=CailianpressWeb&os=web&rever=1&secu_code={code}&sv=8.4.6&way=last_px'
            url = 'https://x-quote.cls.cn/web_quote/plate/stocks?' + cls.ClsUrl().signParams(params)
            data = memcache.cache.getCache(url)
            if not data:
                resp = requests.get(url, proxies = cls.PROXY)
                if resp.status_code != 200:
                    return []
                js = json.loads(resp.content.decode())
                data = js['data']['stocks']
                memcache.cache.saveCache(url, data, 60 * 60 * 8)
            self._calcPlate(data, day, period, subByHots)
            return data
        except Exception as e:
            traceback.print_exc()
        return []
    
    def getPlateThs(self, code):
        day = flask.request.args.get('day', None)
        period = flask.request.args.get('period', 30)
        subByHots = flask.request.args.get('subByMaxHots', '')
        data = []
        for c in gn_utils.ths_gntc_s:
            info = gn_utils.ths_gntc_s[c]
            if code in info['gn_code'] or code == info['hy_2_code'] or code == info['hy_3_code']:
                info['cmc'] = (info.get('ltsz', 0) or 0)* 100000000
                info['secu_code'] = ('sh'if info['code'][0] == '6' else 'sz') + info['code']
                info['secu_name'] = info['name']
                data.append(info)
        self._calcPlate(data, day, period, subByHots)
        return data
    
    def _calcPlate(self, stocks : list, day, period, subByHots):
        subByHots = subByHots == 'true'
        period = int(period)
        if not day or len(day) < 8:
            day = datetime.date.today()
        else:
            day = int(day.replace('-', ''))
            day = datetime.date(day // 10000, day // 100 % 100, day % 100)
        # check hots
        cs = {s['secu_code'][2 : ] : 0 for s in stocks if len(s['secu_code']) == 8 and s['secu_code'][2] in ('0', '3', '6')}
        # scode = ('sh' if code[0] == '6' else 'sz') + code
        endDayInt = int(day.strftime('%Y%m%d'))
        tradeDays = ths_iwencai.getTradeDays(500)
        if endDayInt > int(tradeDays[-1]):
            endDayInt = int(tradeDays[-1])
        for i in range(len(tradeDays) - 1, -1, -1):
            if endDayInt >= int(tradeDays[i]):
                endDayInt = int(tradeDays[i])
                break
        si = i - period + 1
        fromDayInt = int(tradeDays[si])

        self._calcPlateByHots(cs, fromDayInt, endDayInt)
        self._calcPlateByZS(cs, fromDayInt, endDayInt)
        self._calcPlateByZT(cs, fromDayInt, endDayInt)
        self._calcPlateByMaxHots(stocks, endDayInt)
        for i in range(len(stocks) - 1, -1, -1):
            st = stocks[i]
            code = st['secu_code'][2 : ]
            name = st.get('secu_name', '')
            snum = cs.get(code, 0)
            st['_snum_'] = snum
            if len(code) != 6 or 'st' in name or 'ST' in name: # snum < 1 or 
                stocks.pop(i)
                continue
            if subByHots and not st.get('maxHot', 0):
                stocks.pop(i)
        stocks.sort(key = lambda a: a['_snum_'], reverse = True)

    def _calcPlateByMaxHots(self, stocks : list, endDayInt):
        hots = {}
        istoks = [s['secu_code'][2 : ] for s in stocks if len(s['secu_code']) == 8 and s['secu_code'][2] in ('0', '3', '6')]
        endDay = datetime.date(endDayInt // 10000, endDayInt // 100 % 100, endDayInt % 100)
        fromDay = endDay - datetime.timedelta(days = 60)
        fromDay = int(fromDay.strftime('%Y%m%d'))
        qr = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.code, pw.fn.min(ths_orm.THS_HotZH.zhHotOrder)) \
            .where(ths_orm.THS_HotZH.code.in_(istoks), ths_orm.THS_HotZH.day >= fromDay)\
                .group_by(ths_orm.THS_HotZH.code).tuples()
        for it in qr:
            code = f'{it[0] :06d}'
            hots[code] = it[1]
        for st in stocks:
            code = st['secu_code'][2 : ]
            if code in hots:
                st['maxHot'] = hots[code]

    def _calcPlateByHots(self, stocks : dict, fromDayInt, endDayInt):
        qr = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.code, pw.fn.count()).where(ths_orm.THS_HotZH.day >= fromDayInt, ths_orm.THS_HotZH.day <= endDayInt).group_by(ths_orm.THS_HotZH.code).tuples()
        for it in qr:
            code = f'{it[0] :06d}'
            if code in stocks:
                stocks[code] += it[1]
        hotMaxZHDay = ths_orm.THS_HotZH.select(pw.fn.max(ths_orm.THS_HotZH.day)).scalar()
        lastTradeDay = hot_utils.getLastTradeDay()
        if lastTradeDay == hotMaxZHDay or fromDayInt > lastTradeDay or lastTradeDay > endDayInt:
            return
        hz = hot_utils.DynamicHotZH.instance().getNewestHotZH()
        for it in hz:
            code = f'{it :06d}'
            if code in stocks:
                stocks[code] += 1

    def _calcPlateByZS(self, stocks : dict, fromDayInt, endDayInt):
        qr = d_orm.LocalSpeedModel.select(d_orm.LocalSpeedModel.code, pw.fn.count()).where(d_orm.LocalSpeedModel.day >= fromDayInt, d_orm.LocalSpeedModel.day <= endDayInt).group_by(d_orm.LocalSpeedModel.code).tuples()
        for it in qr:
            code = it[0]
            if code in stocks:
                stocks[code] += it[1]

    def _calcPlateByZT(self, stocks : dict, fromDayInt, endDayInt):
        fromDayStr = f"{fromDayInt // 10000}-{fromDayInt // 100 % 100 :02d}-{fromDayInt % 100 :02d}"
        endDayStr = f"{endDayInt // 10000}-{endDayInt // 100 % 100 :02d}-{endDayInt % 100 :02d}"
        qr = cls_orm.CLS_UpDown.select(cls_orm.CLS_UpDown.secu_code, pw.fn.count()).where(cls_orm.CLS_UpDown.day >= fromDayStr, cls_orm.CLS_UpDown.day <= endDayStr).group_by(cls_orm.CLS_UpDown.secu_code).tuples()
        for it in qr:
            code = it[0][2 : ]
            if code in stocks:
                stocks[code] += it[1]
    
    def getIndustryCls(self, code):
        try:
            day = flask.request.args.get('day', None)
            period = flask.request.args.get('period', 30)
            subByHots = flask.request.args.get('subByMaxHots', '')
            params = f'app=CailianpressWeb&os=web&rever=1&secu_code={code}&sv=8.4.6&way=last_px'
            url = 'https://x-quote.cls.cn/web_quote/plate/industry?' + cls.ClsUrl().signParams(params)
            data = memcache.cache.getCache(url)
            if not data:
                resp = requests.get(url, proxies = cls.PROXY)
                if resp.status_code != 200:
                    return []
                js = json.loads(resp.content.decode())
                data = js['data']
                memcache.cache.saveCache(url, data, 60 * 60 * 8)
            if not data:
                return []
            for d in data:
                self._calcPlate(d['stocks'], day, period, subByHots)
            return data
        except Exception as e:
            traceback.print_exc()
        return []

if __name__ == '__main__':
    svr = Server()
    svr.start()
    # ds = svr.getIndustry('cls80147')
    # for it in ds:
    #     for idx, d in enumerate(it['stocks']):
    #         print(idx, d['secu_code'])
    # s.queryBySql('hot_zh', 'select *  from 个股热度综合排名 where 日期 >= 20250415')
    # s.getTimeDegree()
    