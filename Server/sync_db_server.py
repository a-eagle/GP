import json, os, sys, datetime, threading, time, inspect, platform
import traceback
import requests, json, logging
import peewee as pw, flask

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import chrome_orm, cls_orm, d_orm, def_orm, lhb_orm, ths_orm
from download import console, ths_iwencai

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)

    def check(self):
        pass

    def start(self):
        self.app.add_url_rule('/getUpdateData/<ormFile>/<ormClass>/<updateTime>', view_func = self.getUpdateData, methods = ['GET', 'POST'])
        self.app.add_url_rule('/getMaxUpdateTimeAll', view_func = self.getMaxUpdateTimeAll, methods = ['GET', 'POST'])
        self.app.run('0.0.0.0', 8090, use_reloader = False, debug = False)

    def getMaxUpdateTimeAll(self):
        mgr = DbTableManager()
        models = mgr.getAllModels()
        rs = []
        for m in models:
            maxTime = mgr.getMaxUpdateTime(m['ormClass'])
            if not maxTime:
                continue
            rs.append({'ormFile': m['ormFileName'], 'ormClass': m['ormClassName'], 'updateTime': maxTime.timestamp()})
        return rs
    
    # updateTime float
    def getUpdateData(self, ormFile, ormClass, updateTime):
        if not updateTime:
            return {'status': 'Fail', 'msg': f'Request updateTime param'}
        mgr = DbTableManager()
        model = mgr.getOrmClass(ormFile, ormClass)
        if not model:
            return {'status': 'Fail', 'msg': f'Not find orm class"{ormClass}" in "{ormFile}"'}
        dt = datetime.datetime.fromtimestamp(float(updateTime))
        qr = model.select().where(model.updateTime > dt).dicts()
        # print(qr)
        datas = []
        for it in qr:
            datas.append(it)
            it['updateTime'] = str(it['updateTime'])
        rs = {'status': 'OK', 'msg':'Success', 'data': datas}
        return rs

class Client:
    def __init__(self) -> None:
        pass

    def start(self):
        while True:
            if datetime.date.today().weekday() >= 5:
                time.sleep(60 * 60 * 2)
                continue
            hm = datetime.datetime.now().strftime('%H:%M')
            if hm < '09:00' or hm > '23:00':
                time.sleep(5 * 60)
                continue
            if not ths_iwencai.isTradeDay():
                time.sleep(60 * 60 * 2)
                continue
            self.checkOnce()
            time.sleep(5 * 60)

    def checkOnce(self):
        rs = self.getMaxUpdateTimeAll()
        if not rs:
            return
        for r in rs:
            self.loadUpdateData(r)

    def loadUpdateData(self, item):
        try:
            mgr = DbTableManager()
            ormFile, ormClass, updateTime = item['ormFile'], item['ormClass'], item['updateTime']
            model = mgr.getOrmClass(ormFile, ormClass)
            if not model:
                print(f"[Client.loadUpdateData] Not find model: {ormFile} {ormClass}")
                return
            maxTime = mgr.getMaxUpdateTime(model)
            if not maxTime:
                maxTime = datetime.datetime(2025, 6, 11, 8, 0, 0)
            if maxTime.timestamp() >= updateTime:
                return
            resp = requests.get(f"http://113.44.136.221:8090/getUpdateData/{ormFile}/{ormClass}/{maxTime.timestamp()}")
            txt = resp.content.decode()
            rs = json.loads(txt)
            if not rs:
                return
            if rs['status'] != 'OK':
                print('[loadUpdateData] ', rs)
                return
            datas = rs['data']
            self.diffDatas(model, datas)
            updateTimeStr = datetime.datetime.fromtimestamp(updateTime)
            console.writeln_1(console.GREEN, f'Update datas {ormFile}.{ormClass} --> num: {len(datas)} time: {updateTimeStr}')
        except Exception as e:
            traceback.print_exc()

    def diffDatas(self, model, datas : list):
        if not datas:
            return
        ds = []
        for d in datas:
            if 'id' in d:
                d.pop('id')
            ds.append(model(**d))
        if not getattr(model, 'keys', None):
            model.bulk_create(ds, 50)
            return
        for d in datas:
            self.diffOneData(model, d)

    def diffOneData(self, model, data):
        cnd = {}
        for k in model.keys:
            cnd[k] = data[k]
        obj = model.get_or_none(**cnd)
        if not obj: # insert
            model.create(**data)
            return
        # update
        for k in data:
            setattr(obj, k, data[k])
        obj.save()

    def getMaxUpdateTimeAll(self):
        try:
            resp = requests.get('http://113.44.136.221:8090/getMaxUpdateTimeAll')
            txt = resp.content.decode()
            rs = json.loads(txt)
            return rs
        except Exception as e:
            traceback.print_exc()
        return None

class DbTableManager:
    def __init__(self) -> None:
        self.modules = [chrome_orm, cls_orm, d_orm, def_orm, lhb_orm, ths_orm]

    def _addUpdateTimeColumn(self, cursor, tableName):
        cursor.execute(f'pragma table_info({tableName})')
        rs = cursor.fetchall()
        for r in rs:
            if r[1] == 'updateTime':
                return
        cursor.execute(f'alter table {tableName} add column updateTime datetime')

    def getAllDatabases(self):
        rs = []
        for m in self.modules:
            names = dir(m)
            for name in names:
                db = getattr(m, name)
                if isinstance(db, pw.SqliteDatabase):
                    rs.append(db)
        return rs
    
    def getAllModels(self):
        rs = []
        for m in self.modules:
            names = dir(m)
            for name in names:
                obj = getattr(m, name)
                if not isinstance(obj, type.__class__) or not issubclass(obj, pw.Model):
                    continue
                if hasattr(obj, 'updateTime'):
                    fn = m.__name__
                    if '.' in fn:
                        fn = fn[fn.index('.') + 1 : ]
                    rs.append({'ormFileName': fn, 'ormFile': m, 'ormClass': obj, 'ormClassName': obj.__name__})
        return rs
    
    def getMaxUpdateTime(self, model):
        maxTime = model.select(pw.fn.max(model.updateTime)).scalar()
        return maxTime

    def addUpdateTimeFiled(self):
        for m in self.modules:
            names = dir(m)
            for name in names:
                db = getattr(m, name)
                # check is database
                if not isinstance(db, pw.SqliteDatabase):
                    continue
                # check is pw.Model
                #if not isinstance(obj, type.__class__) or not issubclass(obj, pw.Model):
                #    continue
                #print(f.__name__, '==>', name, db)
                cc = db.cursor()
                cc.execute('SELECT name FROM sqlite_master WHERE type="table"')
                tables = cc.fetchall()
                for t in tables:
                    self._addUpdateTimeColumn(cc, t[0])

    def getOrmClass(self, ormFileName, ormClassName):
        for m in self.modules:
            simpleName = m.__name__
            if '.' in m.__name__:
                simpleName = simpleName[m.__name__.index('.') + 1 : ]
            if simpleName != ormFileName:
                continue
            obj = getattr(m, ormClassName, None)
            if inspect.isclass(obj) and issubclass(obj, pw.Model):
                return obj
            return None
        return None

if __name__ == '__main__':
    if platform.node() == 'DESKTOP-P6GAAMF':
        client = Client()
        client.start()
    else:
        svr = Server()
        svr.start()
        