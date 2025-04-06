import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]
db_tck = pw.SqliteDatabase(f'{path}GP/db/TCK.db') # 题材库

# 同花顺涨停
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

# 财联社涨停
class CLS_ZT(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField(null = True)
    lbs = pw.IntegerField(default = 0, column_name='连板数')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    detail = pw.CharField(null = True, column_name='详情')

    class Meta:
        database = db_tck

# 财联社涨停、跌停、连板、炸板
class CLS_UpDown(pw.Model):
    secu_code = pw.CharField()
    secu_name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    time = pw.CharField() # HH:mm:SS
    change = pw.FloatField(null=True) # 涨跌幅
    last_px = pw.FloatField(null=True) # 收盘价
    up_reason = pw.CharField(null = True)
    limit_up_days = pw.IntegerField(default = 0) # 连板数
    is_down = pw.IntegerField(default = 0) # 是否是跌停

    class Meta:
        database = db_tck        

# 涨停盘口(收盘)
class ZT_PanKou(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    info = pw.CharField()

    class Meta:
        database = db_tck

# 综合强度
class CLS_SCQX(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    zhqd = pw.IntegerField(column_name='综合强度')
    fb = pw.CharField(null = True) # 涨跌分布

    class Meta:
        database = db_tck

# 综合强度(分时)
class CLS_SCQX_Time(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    time = pw.CharField() # HH:MM
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_tck        

# 财联社热度题材
class CLS_HotTc(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField(null = True, default = "")
    name = pw.CharField()
    up = pw.BooleanField() # 是否是上涨, 还是下跌
    ctime = pw.CharField()

    class Meta:
        database = db_tck
        
#db_tck.drop_tables([CLS_SCQX_Time])
db_tck.create_tables([THS_ZT, CLS_ZT, CLS_SCQX, CLS_HotTc, CLS_SCQX_Time, ZT_PanKou, CLS_UpDown])