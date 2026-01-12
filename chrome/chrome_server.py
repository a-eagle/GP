import threading, sys, traceback, datetime, json, logging, copy, os, base64
import flask, flask_cors, requests
import win32con, win32gui, peewee as pw
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ui import base_win, timeline, kline_utils, kline_win
from download import config, ths_iwencai, datafile, ths_iwencai, henxin, cls, memcache
from orm import d_orm, cls_orm, chrome_orm, lhb_orm, my_orm, ths_orm
from utils import hot_utils, gn_utils

class Server:
    BASE_CLS_PARAMS = {"os": "web", "sv":"8.4.6", "app": "CailianpressWeb"}

    def __init__(self) -> None:
        self.app = flask.Flask(__name__, static_folder = 'local', template_folder = '')
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        # log.disabled = True
        flask_cors.CORS(self.app)
        self.uiThread = None
        self.cache = {}
        self.docr = None

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
        self.app.add_url_rule('/query-by-sql/<dbName>', view_func = self.queryBySql, methods = ['POST'])
        self.app.add_url_rule('/get-trade-days', view_func = self.getTradeDays)
        self.app.add_url_rule('/iwencai', view_func = self.queryIWenCai)
        self.app.add_url_rule('/top100-vol', view_func = self.getTop100Vol)
        self.app.add_url_rule('/get-fenshi/<code>', view_func = self.getFenShi)
        self.app.add_url_rule('/query-codes-info', view_func = self.queryCodesInfo, methods = ['POST'])
        self.app.add_url_rule('/mark-color', view_func = self.markColor, methods = ['POST'])
        self.app.add_url_rule('/mynote', view_func = self.myNote, methods = [ 'POST'])
        self.app.add_url_rule('/plate/<code>', view_func = self.getPlate)
        self.app.add_url_rule('/industry/<code>', view_func = self.getIndustry)
        self.app.add_url_rule('/get-all-hot-tc', view_func = self.getAllHotTc)
        self.app.add_url_rule('/get-hot-tc-by-day', view_func = self.getHotTcByDay)
        self.app.add_url_rule('/get-hot-tc-by-code', view_func = self.getHotTcByCode)

        self.app.add_url_rule('/load-kline/<code>', view_func = self.loadKLine)
        self.app.add_url_rule('/cls-proxy/', view_func = self.clsProxy)
        self.app.add_url_rule('/subject/<title>', view_func = self.getSubject)
        self.app.add_url_rule('/plate-info/<code>', view_func = self.getPlateInfo)
        self.app.add_url_rule('/compare-amount/<day>', view_func = self.compareAmount)
        self.app.add_url_rule('/Yzcode', view_func = self.getYzcode)
        self.app.run('0.0.0.0', 8080, use_reloader = False, debug = False)

    def signParams(self, **kargs):
        params : dict = self.BASE_CLS_PARAMS.copy()
        params.update(kargs)
        return cls.ClsUrl().signParams(params)
    
    def compareAmount(self, day):
        tds : list = ths_iwencai.getTradeDays()
        if not day:
            day = tds[-1]
        day = day.replace('-', '')
        idx = tds.index(day)
        preDay = tds[idx - 1]
        rsPre, rsCur = [], []
        shPre = self._getFenShi('999999', preDay)
        szPre = self._getFenShi('399001', preDay)
        x930 = 0
        tm = []
        for it in zip(shPre['line'], szPre['line']):
            m = it[0]['amount'] + it[1]['amount']
            tm.append(it[0]['time'])
            if it[0]['time'] == 930:
                x930 = m
                continue
            if it[0]['time'] == 931:
                m += x930
            rsPre.append(m)
        shPre = self._getFenShi('999999', day)
        szPre = self._getFenShi('399001', day)
        for it in zip(shPre['line'], szPre['line']):
            m = it[0]['amount'] + it[1]['amount']
            if it[0]['time'] == 930:
                x930 = m
                continue
            if it[0]['time'] == 931:
                m += x930
            rsCur.append(m)
        return {'pre': rsPre, 'cur': rsCur, 'presum': sum(rsPre), 'cursum': sum(rsCur), 'time': tm}

    def getPlateInfo(self, code):
        url = f'https://x-quote.cls.cn/web_quote/plate/info?' + self.signParams(secu_code = code)
        rs = self._clsProxy(url, 120)
        return rs

    def getSubject(self, title):
        code = flask.request.args.get('code', '')
        if code[0 : 3] == '88':
            obj = cls_orm.CLS_ZS.get_or_none(name = title)
            if not obj:
                return {}
        url = f'https://www.cls.cn/api/subject/{title}/schema?' + self.signParams()
        resp = requests.get(url, headers = cls.ClsUrl.reqHeaders)
        js = json.loads(resp.content.decode())
        if js['errno'] != 0:
            return []
        schema = js['data'][0]['schema']
        keyId = schema[schema.index('=') + 1 : ]
        url = f'https://www.cls.cn/api/subject/detail/{keyId}?' + self.signParams()
        resp = requests.get(url, headers = cls.ClsUrl.reqHeaders)
        data = resp.content.decode()
        js = json.loads(data)
        js['subject_id'] = keyId
        return js

    def clsProxy(self):
        url = flask.request.args.get('url')
        cachetime= flask.request.args.get('cachetime', 300, type = int)
        rs = self._clsProxy(url, cachetime)
        return rs

    def _clsProxy(self, url, cachetime):
        item = memcache.cache.getCache(url)
        if item:
            return item
        try:
            purl = cls.getProxyUrl(url)
            resp = requests.get(purl, headers = cls.ClsUrl.reqHeaders)
            txt = resp.content.decode()
            js = json.loads(txt)
            if resp.status_code == 200:
                memcache.cache.saveCache(url, js, cachetime)
            return js
        except Exception as e:
            print('Error: url=', url)
            traceback.print_exc()
        return None

    def loadKLine(self, code):
        hx = henxin.HexinUrl()
        rs = hx.loadKLineData(code, 'day')
        datas = []
        if not rs:
            return datas
        KEYS = ('day', 'open', 'high', 'low', 'close', 'amount', 'vol')
        for d in rs['data']:
            obj = {}
            for k in KEYS:
                obj[k] = getattr(d, k, 0)
            datas.append(obj)
        return datas

    def getHotTcByDay_Local(self, day):
        day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day == day).dicts()
        rs = []
        for it in qr:
            rs.append(it)
        return rs
    
    def getHotTcByDay(self):
        day = flask.request.args.get('day', '')
        if not day:
            day = ths_iwencai.getTradeDays()[-1]
        if len(day) == 8:
            day = f"{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}"
        today = datetime.date.today().strftime('%Y-%m-%d')
        now = datetime.datetime.now().strftime('%H:%M')
        if now >= '15:10' or today != day:
            return self.getHotTcByDay_Local(day)
        # is trading now
        url = cls.ClsUrl().getHotTCUrl(day)
        rs = self._clsProxy(url, 60)
        if not rs or not rs['data']:
            self.cache[f'HotTC-Newest'] = None
            return self.getHotTcByDay_Local(day)
        newDatas = []
        for d in rs['data']:
            item = {}
            ts = d['c_time'].split(' ')
            item['day'] = ts[0]
            item['ctime'] = ts[1]
            item['code'] = d['symbol_code']
            item['name'] = d['symbol_name']
            item['up'] = d['float'] == 'up'
            newDatas.append(item)
        self.cache[f'HotTC-Newest'] = newDatas
        return newDatas
        
    def getAllHotTc(self):
        tds = ths_iwencai.getTradeDays()
        days = int(flask.request.args.get('days', None) or 10)
        curDay = flask.request.args.get('curDay', None) or tds[-1]
        curDay = curDay.replace('-', '')
        fromDay = None
        for i in range(len(tds) - 1, 0, -1):
            if curDay >= tds[i]:
                idx = max(i - days + 1, 0)
                fromDay = tds[idx]
                break
        if not fromDay:
            return []
        fromDay = f"{fromDay[0 : 4]}-{fromDay[4 : 6]}-{fromDay[6 : 8]}"
        curDay = f"{curDay[0 : 4]}-{curDay[4 : 6]}-{curDay[6 : 8]}"
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day >= fromDay, cls_orm.CLS_HotTc.day <= curDay).dicts()
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

    def getHotTcByCode(self):
        tds = ths_iwencai.getTradeDays()
        code = flask.request.args.get('code', None)
        daysNum = int(flask.request.args.get('days', None) or 20)
        curDay = flask.request.args.get('curDay', None) or tds[-1]
        curDay = curDay.replace('-', '')
        eidx = tds.index(curDay)
        fidx = eidx - daysNum + 1
        fromDay = gn_utils.formatDate(tds[fidx])
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day >= fromDay, cls_orm.CLS_HotTc.day <= curDay, cls_orm.CLS_HotTc.code == code).dicts()
        days = tds[fidx : eidx + 1]
        preDay = tds[fidx - 1] if fidx > 0 else None
        nextIdx = min(eidx + daysNum, len(tds) - 1)
        nextDay = tds[nextIdx] if eidx < len(tds) - 1 else None
        rs = {'code': code,
              'days': [gn_utils.formatDate(d) for d in days],
              'sdays': [gn_utils.formatDate(d)[5 : ] for d in days],
              'preDay': gn_utils.formatDate(preDay),
              'nextDay': gn_utils.formatDate(nextDay),
              'up': [], 'down': []}
        hotsTc = [q for q in qr]
        # merge today newest
        cacheData = self.cache.get('HotTC-Newest', None)
        fmtCurDay = gn_utils.formatDate(curDay)
        if cacheData and cacheData[0]['day'] == fmtCurDay:
            tmp = {d['ctime'] : d for d in cacheData if d['code'] == code}
            for i in range(len(hotsTc) - 1, -1, -1):
                if hotsTc[i]['day'] != fmtCurDay:
                    break
                if hotsTc[i]['ctime'] in tmp:
                    tmp.pop(hotsTc[i]['ctime'])
            hotsTc.extend(tmp.values())
        for day in rs['days']:
            upNum, downNum = 0, 0
            for tc in hotsTc:
                if tc['day'] <= day and tc['up']: upNum += 1
                if tc['day'] <= day and not tc['up']: downNum += 1
            rs['up'].append(upNum)
            rs['down'].append(downNum)
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
        if config.isServerMachine():
            return {'code': 0, 'msg': 'OK'}
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
            if q['time'] == '13:00':
                continue
            q['degree'] = q['zhqd']
            rs.append(q)
        return rs
    
    def _getDBs(self):
        dbs = {'hot': ths_orm.db_hot, 'hot_zh': ths_orm.db_hot_zh,
               'ths_zs': ths_orm.db_thszs, 'chrome': chrome_orm.db_chrome,
               'cls_hot': cls_orm.db_cls_hot, 'cls_zt': cls_orm.db_cls_zt, 'cls_zs_zd': cls_orm.db_cls_zs_zd}
        return dbs

    def queryBySql(self, dbName):
        dbs = self._getDBs()
        if dbName not in dbs:
            return {'code': 1, 'msg': f'Not find dbName: "{dbName}"'}
        # sql = flask.request.args.get('sql', None)
        params = flask.request.data
        js = json.loads(params.decode())
        if not js or not js.get('sql', None):
            return {'code': 1, 'msg': f'No sql'}
        db : pw.SqliteDatabase = dbs[dbName]
        c = db.cursor()
        c.execute(js['sql'])
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
        # if cfg.isServerMachine():
            # return {'code': code, 'pre': 0, 'line': None}
        day = flask.request.args.get('day', None)
        try:
            fs = self._getFenShi(code, day)
            return fs
        except Exception as e:
            traceback.print_exc()
        return None
    
    def _getFenShi(self, code, day):
        lastTradeDay = ths_iwencai.getTradeDays()[-1]
        if not day:
            day = lastTradeDay
        day = day.replace('-', '')
        rs = {'code': code, 'pre': 0, 'line': None}
        # load from local file first
        df = datafile.T_DataModel(code)
        df.loadLocalData(day)
        rs['pre'] = df.pre
        rs['line'] = df.data
        if not df.data and day == lastTradeDay: # load from server
            if (code[0 : 3] == 'cls') or code == '999999' or code == '1A0001' or code == '399001':
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
                data = hx.loadTimelineData(code)
                rs['pre'] = data['pre']
                rs['line'] = data['line']
        if not rs['line']:
            return rs
        rsd = []
        KS = ('day', 'time', 'price', 'avgPrice', 'amount', 'vol')
        for ln in rs['line']:
            item = {}
            for k in KS: 
                item[k] = getattr(ln, k, None)
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

    # {day: '' | 'YYYY-MM-DD', cols?:[xx_ztReason, hots], codes:[]}
    def queryCodesInfo(self):
        from utils import hot_utils
        params = json.loads(flask.request.data.decode())
        day = params.get('day', '')
        cols = set(params.get('cols', []))
        codes = params['codes']
        ncodes = []
        SS =  ('sz', 'sh')
        for c in codes:
            if len(c) == 6:
                ncodes.append(c)
            elif len(c) == 8 and c[0 : 2] in SS:
                ncodes.append(c[2 : ])
        dynHotZH = hot_utils.DynamicHotZH.instance()
        rs = {}
        zh = None
        for code in ncodes:
            it = {'code': code, 'secu_code': self._getSecuCode(code)}
            rs[it['secu_code']] = it
            cl = gn_utils.cls_gntc_s.get(code, None) or {}
            th = gn_utils.ths_gntc_s.get(code, None) or {}
            it['name'] = cl.get('name', '') or th.get('name', '')
            if 'cls_hy' in cols:
                it['cls_hy'] = cl.get('hy', '')
            if 'ths_hy' in cols:
                it['ths_hy'] = th.get('hy', '')
            if 'ltsz' in cols:
                it['ltsz'] = th.get('ltsz', 0) # 流通市值
            if 'hots' in cols:
                if not day or len(day) < 8:
                    day = None
                if zh is None:
                    zh = dynHotZH.getHotsZH(day) or {}
                hc = zh.get(int(code), None) if zh else None
                it['hots'] = 0 if not hc else hc['zhHotOrder']
            if 'ths_ztReason' in cols:
                zt = gn_utils.get_CLS_THS_ZT_Reason(code)
                it['ths_ztReason'] = zt['ths_ztReason'] if zt else ''
            if 'cls_ztReason' in cols:
                zt = gn_utils.get_CLS_THS_ZT_Reason(code)
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
            params = f'app=CailianpressWeb&os=web&rever=1&secu_code={code}&sv=8.4.6&way=last_px'
            url = 'https://x-quote.cls.cn/web_quote/plate/stocks?' + cls.ClsUrl().signParams(params)
            data = memcache.cache.getCache(url)
            if not data:
                resp = requests.get(cls.getProxyUrl(url), headers = cls.ClsUrl.reqHeaders)
                if resp.status_code != 200:
                    return []
                js = json.loads(resp.content.decode())
                data = js['data']['stocks']
                for i in range(len(data) - 1, -1, -1):
                    if data[i]['secu_code'][0] != 's':
                        data.pop(i)
                memcache.cache.saveCache(url, data, 60 * 60 * 8)
            data = copy.deepcopy(data)
            self._calcPlate(data, day, period, False)
            return data
        except Exception as e:
            traceback.print_exc()
        return []
    
    def getPlateThs(self, code):
        day = flask.request.args.get('day', None)
        period = flask.request.args.get('period', 30)
        KS = ('0', '3', '6')
        data = []
        for c in gn_utils.ths_gntc_s:
            info = gn_utils.ths_gntc_s[c]
            if (code not in info['gn_code']) and (code != info['hy_2_code']) and (code != info['hy_3_code']):
                continue
            if info['code'][0] not in KS:
                continue
            if 'st' in info['name'] or 'ST' in info['name']:
                continue
            info = copy.copy(info)
            info['cmc'] = (info.get('ltsz', 0) or 0) * 100000000
            info['secu_code'] = ('sh' if info['code'][0] == '6' else 'sz') + info['code']
            info['secu_name'] = info['name']
            data.append(info)
        self._calcPlate(data, day, period, False)
        return data
    
    def _calcPlate(self, stocks : list, day, period, subByHots):
        period = int(period)
        if not day or len(day) < 8:
            day = datetime.date.today()
        else:
            day = int(day.replace('-', ''))
            day = datetime.date(day // 10000, day // 100 % 100, day % 100)
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
        for s in stocks:
            s['code'] = s['secu_code'][2 : ]
        self._calcPlateMaxHots(stocks, endDayInt)
        self._calcMaxVol(stocks, endDayInt)

    def _calcMaxVol(self, stocks, endDayInt):
        # eidx = tradeDays.index(endDayInt)
        # fromDayInt = tradeDays[eidx - 3]
        for st in stocks:
            code = st['code']
            dm = datafile.K_DataModel(code)
            dm.loadLocalData()
            if not dm.data or len(dm.data) < 10:
                continue
            idx = -1
            cday = 0
            for i in range(len(dm.data)):
                if endDayInt >= dm.data[i].day:
                    cday = dm.data[i].day
                    idx = i
                else:
                    break
            if cday == 0:
                continue
            DD = (5, 10, 20)
            for d in DD:
                if idx < d:
                    continue
                maxDay = ''
                maxVol = 0
                for i in range(d):
                     if maxVol < dm.data[idx - i].amount:
                         maxVol = dm.data[idx - i].amount
                         maxDay = dm.data[idx - i].day
                st[f'max_{d}_vol'] = maxVol
                st[f'max_{d}_vol_day'] = maxDay


    def _calcPlateMaxHots(self, stocks : list, endDayInt):
        hots = {}
        istoks = [int(s['secu_code'][2 : ]) for s in stocks if len(s['secu_code']) == 8 and s['secu_code'][2] in ('0', '3', '6')]
        endDay = datetime.date(endDayInt // 10000, endDayInt // 100 % 100, endDayInt % 100)
        fromDay = endDay - datetime.timedelta(days = 30)
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

    def getYzcode(self):
        img = flask.request.args.get('img', None)
        if not img:
            return {'captcha': '', 'code': 1}
        if 'base64,' in img:
            idx = img.index(',')
            img = img[idx + 1 : ]
        img = base64.b64decode(img)
        if not self.docr:
            import ddddocr
            self.docr = ddddocr.DdddOcr()
        result = self.docr.classification(img)
        return {'captcha': result, 'code': 0}

if __name__ == '__main__':
    svr = Server()
    svr.start()