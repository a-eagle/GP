import json, os, sys, datetime, threading, time, inspect, platform
import traceback, base64
import requests, json, logging
import peewee as pw, flask, flask_cors

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import config, console
from Server.sync_db import *

class LocalSyncModel(pw.Model):
    modelName = pw.CharField()
    localMaxTime = pw.IntegerField()

class LocalSyncDataModel(pw.Model):
    modelName = pw.CharField()
    value = pw.CharField()

# 无服务器同步数据
class LocalSyncManager:
    def getFilePath(self):
        PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sync.db')
        return PATH

    def openDatabase(self):
        PATH = self.getFilePath()
        db = pw.SqliteDatabase(PATH)
        LocalSyncModel._meta.database = db
        LocalSyncDataModel._meta.database = db
        return db

    def ready(self):
        PATH = self.getFilePath()
        if os.path.exists(PATH):
            os.remove(PATH)
        db = self.openDatabase()
        db.create_tables([LocalSyncModel, LocalSyncDataModel])
        dbMgr = DbTableManager()
        for m in dbMgr.getAllTableModels():
            ut = dbMgr.getMaxUpdateTime(m['ormClass'])
            LocalSyncModel.create(modelName = m['ormClassName'], localMaxTime = ut)
        db.close()

    def syncData(self):
        db = self.openDatabase()
        mgr = DbTableManager()
        datas = []
        for m in LocalSyncModel.select():
            if m.modelName == 'THS_Hot':
                continue
            mi = mgr.getTableModel(m.modelName)
            model = mi['ormClass']
            qr = model.select().where(model.updateTime > m.localMaxTime).dicts()
            for rr in qr:
                datas.append(LocalSyncDataModel(modelName = m.modelName, value = json.dumps(rr)))
        LocalSyncDataModel.bulk_create(datas, 50)
        db.close()

    def update(self):
        db = self.openDatabase()
        mgr = DbTableManager()
        mdatas = {}
        for m in LocalSyncDataModel.select():
            if m.modelName not in mdatas:
                mdatas[m.modelName] = []
            value = json.loads(m.value)
            mdatas[m.modelName].append(value)
        for name in mdatas:
            datas = mdatas[name]
            mi = mgr.getTableModel(name)
            model = mi['ormClass']
            client = Client()
            insertNum, updateNum = client.diffDatas(model, datas)
            console.write_1(console.GREEN, f'Update datas {model} --> ')
            console.writeln_1(console.GREEN, f' insert {insertNum} update {updateNum}')
            if model == base_orm.DeleteModel:
                mgr.execDeleteModels(datas)
        db.close()

    def main(self):
        print('1.ready sync database')
        print('2.sync data to database')
        print('3.update database')
        while True:
            opt = int(input('[select]: '))
            m = (self.ready, self.syncData, self.update)
            m[opt - 1]()

if __name__ == '__main__':
    LocalSyncManager().main()