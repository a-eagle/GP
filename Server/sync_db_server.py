import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging
import peewee as pw, flask

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import chrome_orm, cls_orm, d_orm, def_orm, lhb_orm, ths_orm

class Sync:
    def __init__(self, ormClass) -> None:
        self.ormClass = ormClass

    def getUpdatedDatas(self, dateTime : datetime.datetime):
        rs = []
        qr = self.ormClass.select().where(self.ormClass.updateTime > dateTime).dicts()
        for it in qr:
            rs.append(it)
        return rs

    def getMaxUpdateTime(self):
        maxTime = self.ormClass.select(pw.fn.max(self.ormClass.updateTime)).scalar()
        return maxTime

    # list of dict
    def insertDatas(self, datas : list):
        if not datas:
            return
        ds = []
        for d in datas:
            if 'id' in d:
                d.pop('id')
            ds.append(self.ormClass(**d))
        self.ormClass.bulk_create(ds, 50)

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)

    def check(self):
        pass

    def start(self):
        self.app.add_url_rule('/diff/ormFile/<ormClass>/<updateTime>', view_func = self.diff, methods = ['GET', 'POST'])
        self.app.run('localhost', 8090, use_reloader = False, debug = False)
    
    # updateTime float
    def diff(self, ormFile, ormClass, updateTime):
        files = {'chrome_orm': chrome_orm, 'cls_orm': cls_orm,
                'd_orm': d_orm, 'def_orm': def_orm, 'lhb_orm': lhb_orm,
                'ths_orm': ths_orm}
        if not updateTime:
            return {'status': 'Fail', 'msg': f'Request updateTime param'}
        if ormFile not in files:
            return {'status': 'Fail', 'msg': f'Not find orm file "{ormFile}"'}
        cl = getattr(files[ormFile], ormClass)
        if not cl or not issubclass(cl, pw.Model):
            return {'status': 'Fail', 'msg': f'Not find orm class"{ormClass}"'}

        dt = datetime.datetime.fromtimestamp(float(updateTime))
        qr = cl.select().where(cl.updateTime > dt).dicts()
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

class DbTableModifier:
    @staticmethod
    def _modifyTableColumn(cursor, tableName):
        cursor.execute(f'pragma table_info({tableName})')
        rs = cursor.fetchall()
        for r in rs:
            if r[1] == 'updateTime':
                return
        cursor.execute(f'alter table {tableName} add column updateTime datetime')

    @staticmethod
    def addUpdateTimeFiled():
        files = [chrome_orm, cls_orm, d_orm, def_orm, lhb_orm, ths_orm]
        for f in files:
            names = dir(f)
            for name in names:
                db = getattr(f, name)
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
                    DbTableModifier._modifyTableColumn(cc, t[0])


if __name__ == '__main__':
    #DbTableModifier.addUpdateTimeFiled()

    svr = Server()
    #svr.start()
    #d_orm.ZT_PanKou.update(updateTime = datetime.datetime.now()).where(
    #    d_orm.ZT_PanKou.id > 4300, d_orm.ZT_PanKou.id <= 4340).execute()
    #svr.diff('d_orm', 'ZT_PanKou', datetime.datetime(2025, 6, 10, 20, 48, 0).timestamp())
    print(Sync(d_orm.ZT_PanKou).getMaxUpdateTime())