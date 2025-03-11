import threading, sys
import flask, flask_cors
import win32con, win32gui, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)
        flask_cors.CORS(self.app)
        self.workThread = None

    def start(self):
        th = threading.Thread(target = self.runner, daemon = True)
        th.start()
        self.workThread = base_win.Thread()
        self.workThread.start()

    def runner(self):
        base_win.ThreadPool.instance().start()
        self.app.add_url_rule('/openui/<type_>/<code>', view_func = self.openUI)
        self.app.add_url_rule('/get-hots', view_func = self.getHots)
        self.app.add_url_rule('/get-time-degree', view_func = self.getTimeDegree)
        self.app.add_url_rule('/query-by-sql/<dbName>', view_func = self.queryBySql)
        self.app.add_url_rule('/get-trade-days', view_func = self.getTradeDays)
        self.app.run('localhost', 5665, use_reloader = False, debug = False)

    def openUI_Timeline(self, code, day):
        from Tck import timeline
        win = timeline.TimelinePanKouWindow()
        win.createWindow(None, (0, 0, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
        win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
        win.load(code, day)
        win32gui.PumpMessages()

    def openUI_Kline(self, code, day):
        from Tck import kline_utils
        win = kline_utils.createKLineWindow(None)
        win.changeCode(code)
        win.klineWin.setMarkDay(day)
        win.klineWin.makeVisible(-1)
        win32gui.PumpMessages()

    def openUI(self, type_, code):
        if type_ == 'timeline':
            day = flask.request.args.get('day', None)
            self.workThread.addTask(code, self.openUI_Timeline, code, day)
        elif type_ == 'kline':
            day = flask.request.args.get('day', None)
            self.workThread.addTask(code, self.openUI_Kline, code, day)
        else:
            return {'code': 2, 'msg': f'Type Error: {type_}'}
        return {'code': 0, 'msg': 'OK'}
    
    def getHots(self):
        day = flask.request.args.get('day', None)
        from THS import hot_utils
        hz = hot_utils.DynamicHotZH.instance()
        if day and len(day) >= 8:
            rs = hz.getHotsZH(day)
        else:
            rs = hz.getNewestHotZH()
        if not rs:
            return []
        m = {}
        for k in rs:
            fk = f'{k :06d}'
            m[fk] = rs[k]
        return m
    
    # day = YYYY-MM-DD
    def getTimeDegree(self):
        from orm import tck_orm
        day = flask.request.args.get('day', None)
        print(day)
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

if __name__ == '__main__':
    s = Server()
    #s.runner()
    #s.queryBySql('hot_zh', 'select *  from 个股热度综合排名 where 日期 >= 20250415')
    #s.getTimeDegree()
    s.getTradeDays()