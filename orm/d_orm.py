import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))
from orm import base_orm

db_pankou = pw.SqliteDatabase(f'{path}/db/PanKou.db')
db_zhangsu = pw.SqliteDatabase(f'{path}/db/ZhangSu.db')
db_diff_bkgn = pw.SqliteDatabase(f'{path}/db/DiffBkGn.db')

# 涨停盘口(收盘)
class ZT_PanKou(base_orm.BaseModel):
    keys = ('day', 'code')
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    info = pw.CharField()
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_pankou

db_hotvol = pw.SqliteDatabase(f'{path}/db/HotVol.db')
#热度股成交量前100信息
class HotVol(base_orm.BaseModel):
    keys = ('day', )
    day = pw.CharField() # YYYY-MM-DD
    p1 = pw.IntegerField() # 第一  亿元
    p10 = pw.IntegerField() # 第20
    p20 = pw.IntegerField() # 第20
    p50 = pw.IntegerField() # 第50
    p100 = pw.IntegerField() # 第100

    avg0_10 = pw.IntegerField() # 亿元 前10平均
    avg10_20 = pw.IntegerField() # 前11 ~ 20平均
    avg20_50 = pw.IntegerField() # 前21 ~ 50平均
    avg50_100 = pw.IntegerField() # 前51 ~ 100平均
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_hotvol


# Local涨速
class LocalSpeedModel(base_orm.BaseModel):
    keys = ('day', 'code')
    day = pw.IntegerField() # 日期
    code = pw.CharField() #股票代码
    fromMinute = pw.IntegerField()
    endMinute  = pw.IntegerField()
    minuts =  pw.IntegerField() # 时间
    zf = pw.FloatField() #涨幅
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_zhangsu
        table_name = 'LocalZS'

class DiffBkGnModel(base_orm.BaseModel):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # modify day
    op = pw.CharField() # add | remove
    zsCode = pw.CharField(null = True)
    zsName = pw.CharField(null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_diff_bkgn

def createDiffBkGn(code, name, diffrents):
    if not diffrents:
        return
    gns = diffrents.get('gn_code', None)
    if not gns:
        return
    def splits(n):
        a, b = n
        a = a.split(';')
        b = b.split(';')
        return a, b
    oldCodes, newCodes = splits(gns)
    oldNames, newNames = splits(diffrents['gn'])
    rs = []
    TODAY = datetime.date.today().strftime('%Y-%m-%d')
    for i, c in enumerate(oldCodes):
        if c not in newCodes:
            it = DiffBkGnModel(code = code, name = name, day = TODAY, op = 'remove', zsCode = c, zsName = oldNames[i])
            rs.append(it)
    for i, c in enumerate(newCodes):
        if c not in oldCodes:
            it = DiffBkGnModel(code = code, name = name, day = TODAY, op = 'add', zsCode = c, zsName = newNames[i])
            rs.append(it)
    return rs

# db_pankou.create_tables([ZT_PanKou])
db_hotvol.create_tables([HotVol])
db_zhangsu.create_tables([LocalSpeedModel])
db_diff_bkgn.create_tables([DiffBkGnModel])