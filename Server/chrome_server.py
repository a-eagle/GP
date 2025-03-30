import threading, sys, traceback, datetime, json
import flask, flask_cors
import win32con, win32gui, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)
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
        self.app.add_url_rule('/get-fenshi/<code>', view_func = self.getFenShi)
        self.app.add_url_rule('/query-codes-info', view_func = self.queryCodesInfo, methods = ['POST'])
        self.app.run('localhost', 5665, use_reloader = False, debug = False)

    def openUI_Timeline(self, code, day):
        from Tck import timeline
        win = timeline.TimelinePanKouWindow()
        win.createWindow(None, (0, 0, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
        win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
        win.load(code, day)
        win32gui.PumpMessages()

    def openUI_Kline(self, code, params):
        from Tck import kline_utils
        win = kline_utils.createKLineWindow(None)
        win.changeCode(code)
        if params:
            js = json.loads(params.decode())
            win.klineWin.setMarkDay(js.get('day'), None)
            cs : list = js.get('codes', [])
            idx = cs.index(code) if code in cs else -1
            win.setCodeList(cs, idx)
        win.klineWin.makeVisible(-1)
        win32gui.PumpMessages()

    def openUI(self, type_, code):
        if type_ == 'timeline':
            day = flask.request.args.get('day', None)
            self.uiThread.addTask(code, self.openUI_Timeline, code, day)
        elif type_ == 'kline':
            self.uiThread.addTask(code, self.openUI_Kline, code, flask.request.data)
        else:
            return {'code': 2, 'msg': f'Type Error: {type_}'}
        return {'code': 0, 'msg': 'OK'}
    
    def getHots(self):
        day = flask.request.args.get('day', None)
        full = flask.request.args.get('full', False)
        if full == 'true':
            full = True
        from THS import hot_utils
        from Tck import utils
        hz = hot_utils.DynamicHotZH.instance()
        if day and len(day) >= 8:
            rs = hz.getHotsZH(day)
        else:
            rs = hz.getNewestHotZH()
        if not rs:
            return {}
        m = {}
        for k in rs:
            code = f'{k :06d}'
            it = m[code] = rs[k]
            it['code'] = code
            if not full:
                continue
            cl = utils.cls_gntc_s.get(code, None) or {}
            th = utils.ths_gntc_s.get(code, None) or {}
            it['name'] = cl.get('name', '') or th.get('name', '')
            it['cls_hy'] = cl.get('hy', '')
            it['ths_hy'] = th.get('hy', '')
            it['ltsz'] = th.get('ltsz', 0) # 流通市值
            zt = utils.get_CLS_THS_ZT_Reason(code)
            if zt: it.update(zt)
        return m
    
    # day = YYYY-MM-DD
    def getTimeDegree(self):
        from orm import tck_orm
        day = flask.request.args.get('day', None)
        if not day:
            qr = tck_orm.CLS_SCQX_Time.select(pw.fn.max(tck_orm.CLS_SCQX_Time.day)).tuples()
            for q in qr:
                day = q[0]
                break
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        qr = tck_orm.CLS_SCQX_Time.select().where(tck_orm.CLS_SCQX_Time.day == day).dicts()
        rs = []
        for q in qr:
            q['degree'] = q['zhqd']
            rs.append(q)
        return rs
    
    def queryBySql(self, dbName):
        from orm import cls_orm, lhb_orm, tck_def_orm, tck_orm, ths_orm, zs_orm
        dbs = {'cls_gntc': cls_orm.db_gntc, 
               'lhb': lhb_orm.db_lhb,
               'tck_def': tck_def_orm.db_tck_def, 
               'tck': tck_orm.db_tck,
               'ths_gntc': ths_orm.db_gntc, 'hot': ths_orm.db_hot, 'hot_zh': ths_orm.db_hot_zh, 'ths_zs': ths_orm.db_thszs,
               'zs': zs_orm.zsdb}
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
    
    def getTradeDays(self):
        from Download import ths_iwencai
        days = ths_iwencai.getTradeDays_Cache(180)
        rs = []
        for d in days:
            rs.append(f"{d[0 : 4]}-{d[4 : 6]}-{d[6 : 8]}")
        return rs

    def queryIWenCai(self):
        try:
            from Download import ths_iwencai
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
    
    def getFenShi(self, code):
        from Download import datafile, ths_iwencai, cls, henxin
        day = flask.request.args.get('day', None)
        lastTradeDay = ths_iwencai.getTradeDays_Cache()[-1]
        today = datetime.date.today().strftime('%Y%m%d')
        rs = {'code': code, 'pre': 0, 'line': None}
        if today == lastTradeDay and (not day or day.replace('-', '') == today): # load from server
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
            df = datafile.DataFile(code, datafile.DataFile.DT_MINLINE)
            df.loadDataByDay(day)
            rs['pre'] = getattr(df, 'pre', df.data[0].price)
            rs['line'] = df.data
        rsd = []
        for ln in rs['line']:
            item = {}
            for k in datafile.ItemData.MLS2: 
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
        from THS import hot_utils
        from Tck import utils
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
            cl = utils.cls_gntc_s.get(code, None) or {}
            th = utils.ths_gntc_s.get(code, None) or {}
            it['name'] = cl.get('name', '') or th.get('name', '')
            it['cls_hy'] = cl.get('hy', '')
            it['ths_hy'] = th.get('hy', '')
            it['ltsz'] = th.get('ltsz', 0) # 流通市值
            if 'hots' in mcols:
                day = mcols['hots']
                if not day or day == True or len(day) < 8:
                    day = None
                hh = hz.getHotsZH(day)
                hc = hh.get(int(code), None)
                it['hots'] = 0 if not hc else hc['zhHotOrder']
            if 'ztReason' in mcols:
                zt = utils.get_CLS_THS_ZT_Reason(code)
                it['ths_ztReason'] = zt['ths_ztReason'] if zt else ''
                it['cls_ztReason'] = zt['cls_ztReason'] if zt else ''
        return rs


if __name__ == '__main__':
    svr = Server()
    svr.start()
    #s.queryBySql('hot_zh', 'select *  from 个股热度综合排名 where 日期 >= 20250415')
    #s.getTimeDegree()
    