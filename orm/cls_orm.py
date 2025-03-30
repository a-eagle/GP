import peewee as pw
import sys

path = __file__[0 : __file__.upper().index('GP')]

db_gntc = pw.SqliteDatabase(f'{path}GP/db/CLS_GNTC.db')

# 材联社--个股概念题材
class CLS_GNTC(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField(default='') #股票名称
    hy = pw.CharField(default='') # 行业
    hy_code = pw.CharField(default='') # 行业
    gn = pw.CharField(default='') # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(default='') # 常规概念对应的代码;分隔

    class Meta:
        database = db_gntc

# 材联社--指数(板块、概念)
class CLS_ZS(pw.Model):
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称
    type_ = pw.CharField() #指数名称 HY | GN

    class Meta:
        database = db_gntc

db_gntc.create_tables([CLS_GNTC, CLS_ZS])
