import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]
db_tck = pw.SqliteDatabase(f'{path}GP/db/TCK.db') # 题材库

class KPL_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    ztNum = pw.IntegerField(null=True, column_name='涨停数量')
    remark = pw.CharField(null=True, column_name='备注')

    class Meta:
        database = db_tck
        table_name = '开盘啦涨停'

class KPL_SCQX(pw.Model):
    day = pw.CharField()
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_tck
        table_name = '开盘啦市场情绪'

class THS_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    #ztNum = pw.IntegerField(null=True, column_name='涨停数量')
    mark_1 = pw.CharField() # 简单的备注
    mark_2 = pw.CharField() # 详细备注
    mark_3 = pw.IntegerField(null = True) # 重点标记

    class Meta:
        database = db_tck
        table_name = '同花顺涨停'

class CLS_ZT(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField(null = True)
    lbs = pw.IntegerField(default = 0, column_name='连板数')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    detail = pw.CharField(null = True, column_name='详情')

    class Meta:
        database = db_tck
        table_name = '财联社涨停'

class CLS_SCQX(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_tck
        table_name = '财联社市场情绪'

db_tck.create_tables([THS_ZT, CLS_ZT, KPL_ZT, KPL_SCQX, CLS_SCQX])