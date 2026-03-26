import peewee as pw
import sys, datetime, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import base_orm
from utils import cutils

# 财联社--个股概念题材
class CLS_GNTC(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length = 12) #股票代码
    name = pw.CharField(null = True, default='', max_length = 60) #股票名称
    hy = pw.CharField(null = True, default='', max_length = 240) # 行业
    hy_code = pw.CharField(null = True, default='', max_length = 240) # 行业
    gn = pw.CharField(null = True, default='', max_length = 2048) # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(null = True, default='', max_length = 2048) # 常规概念对应的代码;分隔

# 材联社--指数(板块、概念)
class CLS_ZS(base_orm.NeedSyncModel):
    keys = ('code', )
    code = pw.CharField(max_length = 12) #指数代码
    name = pw.CharField(max_length = 120) #指数名称
    type_ = pw.CharField(max_length = 8) #指数类型 HY | GN

# 财联社涨停
class CLS_ZT(base_orm.NeedSyncModel):
    keys = ('code', 'day')
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    code = pw.CharField(max_length = 12)
    name = pw.CharField(null = True, max_length = 60)
    lbs = pw.IntegerField(default = 0) # 连板数
    ztReason = pw.CharField(null = True, max_length = 480)  # 涨停原因
    detail = pw.CharField(null = True, max_length = 20000) # 详情

# 财联社涨停、跌停、连板、炸板
class CLS_UpDown(base_orm.NeedSyncModel):
    keys = ('secu_code', 'day')
    secu_code = pw.CharField(max_length = 12)
    secu_name = pw.CharField(null = True, max_length = 24)
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    time = pw.CharField(max_length = 12) # HH:mm:SS
    change = pw.FloatField(null=True) # 涨跌幅
    last_px = pw.FloatField(null=True) # 收盘价
    up_reason = pw.CharField(null = True, max_length = 480)
    limit_up_days = pw.IntegerField(default = 0) # 连板数
    is_down = pw.IntegerField(default = 0) # 是否是跌停

# 综合强度
class CLS_SCQX(base_orm.NeedSyncModel):
    keys = ('day', )
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    zhqd = pw.IntegerField(null = True) # 综合强度
    fb = pw.CharField(null = True) # 涨跌分布
    zdfb = pw.CharField(null = True) # 涨跌分布（东方财富数据）

# 综合强度(分时)
class CLS_SCQX_Time(base_orm.NeedSyncModel):
    keys = ('day', 'time')
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    time = pw.CharField(max_length = 12) # HH:MM
    zhqd = pw.IntegerField(null = True) # 综合强度

# 财联社热度题材
class CLS_HotTc(base_orm.NeedSyncModel):
    keys = ('code', 'day', 'ctime')
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    code = pw.CharField(null = True, default = "", max_length = 12)
    name = pw.CharField(max_length = 80)
    up = pw.BooleanField() # 是否是上涨, 还是下跌
    ctime = pw.CharField(max_length = 24)

# 材联社--指数涨跌(板块、概念)
class CLS_ZS_ZD(base_orm.NeedSyncModel):
    keys = ('code', 'day')
    code = pw.CharField(max_length = 24) #指数代码
    name = pw.CharField(default = '', max_length = 90) #指数名称
    type_ = pw.CharField(max_length = 8) #指数类型 HY | GN
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    zf = pw.FloatField(default = 0) # 涨幅
    fund = pw.FloatField(default = 0) #资金流向 (亿)
    pm = pw.IntegerField() # 涨跌排名

base_orm.db_mysql.create_tables([CLS_GNTC, CLS_ZS, CLS_ZS_ZD, CLS_ZT, CLS_UpDown, CLS_SCQX, CLS_SCQX_Time, CLS_HotTc])

if __name__ == '__main__':
    pass
    
