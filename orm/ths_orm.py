import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)
from orm import base_orm, orm_urils

# 同花顺--概念题材
class THS_GNTC(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length = 12) #股票代码
    name = pw.CharField(max_length = 64) #股票名称
    gn = pw.CharField(null=True, max_length = 4096) # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(null=True, max_length = 4096) # 常规概念对应的代码;分隔
    hy = pw.CharField(null=True, max_length = 120) # 行业
    hy_2_name = pw.CharField(null=True, max_length = 120) # 二级行业名称
    hy_2_code = pw.CharField(null=True, max_length = 120) # 二级行业代码
    hy_3_name = pw.CharField(null=True, max_length = 120) # 三级行业名称
    hy_3_code = pw.CharField(null=True, max_length = 120) # 三级行业代码

# 同花顺--个股热度排名
class THS_Hot(base_orm.NeedSyncModel):
    # no keys
    day = pw.IntegerField() # 刷新日期
    code = pw.IntegerField() #股票代码
    time = pw.IntegerField() # 刷新时间  HHMM
    hotValue = pw.IntegerField() # 热度值_万
    hotOrder = pw.IntegerField() # 热度排名

# 同花顺--个股热度综合排名
class THS_HotZH(base_orm.NeedSyncModel):
    keys = ('day', 'code')
    day = pw.IntegerField() # 日期
    code = pw.IntegerField() #股票代码
    avgHotValue = pw.IntegerField() # 平均热度值_万
    avgHotOrder = pw.FloatField() # 平均热度排名
    zhHotOrder = pw.IntegerField() # 综合热度排名

class THS_ZS(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length=12) #指数代码
    name = pw.CharField(max_length=96) #指数名称
    parentCode = pw.CharField(null = True, max_length=12)

# 同花顺指数涨跌信息
class THS_ZS_ZD(base_orm.NeedSyncModel):
    keys = ('day', 'code')
    day = pw.CharField(max_length=12) # YYYY-MM-DD
    code = pw.CharField(max_length=12) #指数代码
    name = pw.CharField(null = True, max_length=96) #指数名称
    zdf_topLevelPM = pw.IntegerField(default = 0) # 一级概念、行业排名
    zdf_PM = pw.IntegerField(default = 0) # 二级排名
    # close = pw.FloatField(default = 0)
    # open = pw.FloatField(default = 0)
    # high = pw.FloatField(default = 0)
    # rate = pw.FloatField(default = 0)
    # money = pw.FloatField(default = 0)
    # vol = pw.FloatField(default = 0)
    zdf = pw.FloatField(default = 0)

def update_THS_ZS(onlyMaxDay = True):
    qr = None
    if onlyMaxDay:
        maxDay = THS_ZS_ZD.select(pw.fn.max(THS_ZS_ZD.day)).scalar()
        if maxDay:
            qr = THS_ZS_ZD.select(THS_ZS_ZD.code, THS_ZS_ZD.name).where(THS_ZS_ZD.day == maxDay).tuples()        
    if not qr:
        qr = THS_ZS_ZD.select(THS_ZS_ZD.code, THS_ZS_ZD.name).tuples()
    # print(qr)
    rs = {}
    for it in qr:
        code, name = it
        rs[code] = name
    inserts, updates = [], []
    curs = {}
    for it in THS_ZS.select():
        curs[it.code] = it
    # find inserts
    for code in rs:
        if code not in curs:
            inserts.append(THS_ZS(code = code, name = rs[code]))
    # find updates
    for code in curs:
        if code not in rs:
            continue
        if curs[code].name != rs[code]:
            curs[code].name = rs[code]
            updates.append(curs[code])
    THS_ZS.bulk_create(inserts, 100)
    THS_ZS.bulk_update(updates, ['name'], 100)

# 同花顺涨停
class THS_ZT(base_orm.NeedSyncModel):
    keys = ('code', 'day')
    code = pw.CharField(max_length=12)
    name = pw.CharField(null = True, max_length=24)
    day = pw.CharField(max_length=12) # YYYY-MM-DD
    ztTime = pw.CharField(null = True, max_length=24, column_name='') # 涨停时间
    status = pw.CharField(null = True, max_length=24, column_name='') # 状态
    ztReason = pw.CharField(null = True, max_length=120, column_name='') # 涨停原因

# 个股信息
class THS_CodesInfo(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length=12)
    name = pw.CharField(null = True, max_length=24)

    jrl = pw.CharField(null = True, max_length=512) # 近4年净利润
    jrl_2 = pw.CharField(null = True, max_length=512) # 近4季度净利润
    yysr = pw.CharField(null = True, max_length=512) # 近4年营业收入

class THS_CodesBasic(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length = 12) #股票代码
    name = pw.CharField(max_length = 64, null = True, default = '') #股票名称
    zgb = pw.BigIntegerField(null=True, default = None) # 总股本 股
    ltag = pw.BigIntegerField(null=True, default = None) # 流通a股 股
    pe = pw.FloatField(null=True, default = None) # 静态市盈率
    peTTM = pw.FloatField(null=True, default = None) # 市盈率(pe,ttm)

base_orm.db_mysql.create_tables([THS_Hot, THS_HotZH, THS_ZS, THS_ZS_ZD, 
    THS_GNTC, THS_ZT, THS_CodesInfo, THS_CodesBasic])

if __name__ == '__main__':
    pass