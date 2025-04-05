import peewee as pw
import sys

path = sys.argv[0]
path = path[0 : path.index('GP') ]
zsdb = pw.SqliteDatabase(f'{path}GP/db/ZhangSu.db')

# Local涨速
class LocalSpeedModel(pw.Model):
    day = pw.IntegerField() # 日期
    code = pw.CharField() #股票代码
    fromMinute = pw.IntegerField()
    endMinute  = pw.IntegerField()
    minuts =  pw.IntegerField() # 时间
    zf = pw.FloatField() #涨幅

    class Meta:
        database = zsdb
        table_name = 'LocalZS'

# 当日实时涨速
class RealSpeedModel(pw.Model):
    day = pw.IntegerField() # 日期
    minuts = pw.IntegerField() # 时间
    code = pw.CharField() #股票代码
    zf = pw.FloatField() #涨幅
    time = pw.BigIntegerField(column_name = 'time_') # 时间

    class Meta:
        database = zsdb
        table_name = 'RealZS'

#zsdb.drop_tables([LocalZSModel, RealZSModel])
zsdb.create_tables([LocalSpeedModel, RealSpeedModel])
