import peewee as pw
import sys, datetime, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import base_orm

# 涨停盘口(收盘)
class ZT_PanKou(base_orm.NeedSyncModel):
    keys = ('day', 'code')
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    code = pw.CharField(max_length = 12)
    info = pw.CharField(max_length = 1024)

#热度股成交量前100信息
class HotVol(base_orm.NeedSyncModel):
    keys = ('day', )
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    p1 = pw.IntegerField() # 第一  亿元
    p10 = pw.IntegerField() # 第20
    p20 = pw.IntegerField() # 第20
    p50 = pw.IntegerField() # 第50
    p100 = pw.IntegerField() # 第100

    avg0_10 = pw.IntegerField() # 亿元 前10平均
    avg10_20 = pw.IntegerField() # 前11 ~ 20平均
    avg20_50 = pw.IntegerField() # 前21 ~ 50平均
    avg50_100 = pw.IntegerField() # 前51 ~ 100平均

# Local涨速
class LocalSpeedModel(base_orm.NeedSyncModel):
    keys = ('day', 'code')
    day = pw.IntegerField() # 日期
    code = pw.CharField() #股票代码
    fromMinute = pw.IntegerField()
    endMinute  = pw.IntegerField()
    minuts =  pw.IntegerField() # 时间
    zf = pw.FloatField() #涨幅


class DiffBkGnModel(base_orm.NeedSyncModel):
    code = pw.CharField(max_length = 12)
    name = pw.CharField(null = True, max_length = 48)
    day = pw.CharField(max_length = 12) # modify day
    op = pw.CharField(max_length = 12) # add | remove
    zsCode = pw.CharField(null = True, max_length = 12)
    zsName = pw.CharField(null = True, max_length = 24)

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

base_orm.db_mysql.create_tables([ZT_PanKou, HotVol, LocalSpeedModel, DiffBkGnModel])

if __name__ == '__main__':
    pass