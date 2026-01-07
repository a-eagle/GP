import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))
ROOT_DB_PATH = f'{path}/db2'

db_cls_gntc = pw.SqliteDatabase(f'{ROOT_DB_PATH}/CLS_GNTC.db')
db_cls_zs = pw.SqliteDatabase(f'{ROOT_DB_PATH}/CLS_ZS.db')
db_cls_zs_zd = pw.SqliteDatabase(f'{ROOT_DB_PATH}/CLS_ZS_ZD.db')
db_cls_zt = pw.SqliteDatabase(f'{ROOT_DB_PATH}/CLS_ZT.db')
db_cls_hot = pw.SqliteDatabase(f'{ROOT_DB_PATH}/CLS_HOT.db')

# 财联社--个股概念题材
class CLS_GNTC(pw.Model):
    keys = ('code', )
    code = pw.CharField() #股票代码
    name = pw.CharField(default='') #股票名称
    hy = pw.CharField(default='') # 行业
    hy_code = pw.CharField(default='') # 行业
    gn = pw.CharField(default='') # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(default='') # 常规概念对应的代码;分隔
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_gntc

    # return changed  False: no changed, Yes: changed
    def diff(self, newObj):
        if not newObj:
            return False
        changed = False
        changed = self.diffStrAttr(newObj, 'name') or changed
        changed = self.diffStrAttr(newObj, 'hy') or changed
        changed = self.diffStrAttr(newObj, 'hy_code') or changed
        changed = self.diffStrAttr(newObj, 'gn') or changed
        changed = self.diffStrAttr(newObj, 'gn_code') or changed
        return changed
    
    def diffStrAttr(self, newObj, attrName):
        if getattr(self, attrName, '') != getattr(newObj, attrName, ''):
            setattr(self, attrName, getattr(newObj, attrName, ''))
            return True
        return False

# 材联社--指数(板块、概念)
class CLS_ZS(pw.Model):
    keys = ('code', )
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称
    type_ = pw.CharField() #指数类型 HY | GN
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_zs

# 财联社涨停
class CLS_ZT(pw.Model):
    keys = ('code', 'day')
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField(null = True)
    lbs = pw.IntegerField(default = 0, column_name='连板数')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    detail = pw.CharField(null = True, column_name='详情')
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_zt

# 财联社涨停、跌停、连板、炸板
class CLS_UpDown(pw.Model):
    keys = ('secu_code', 'day')
    secu_code = pw.CharField()
    secu_name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    time = pw.CharField() # HH:mm:SS
    change = pw.FloatField(null=True) # 涨跌幅
    last_px = pw.FloatField(null=True) # 收盘价
    up_reason = pw.CharField(null = True)
    limit_up_days = pw.IntegerField(default = 0) # 连板数
    is_down = pw.IntegerField(default = 0) # 是否是跌停
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_zt

# 综合强度
class CLS_SCQX(pw.Model):
    keys = ('day', )
    day = pw.CharField() # YYYY-MM-DD
    zhqd = pw.IntegerField(column_name='综合强度', null = True)
    fb = pw.CharField(null = True) # 涨跌分布
    zdfb = pw.CharField(null = True) # 涨跌分布（东方财富数据）
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_hot

# 综合强度(分时)
class CLS_SCQX_Time(pw.Model):
    keys = ('day', 'time')
    day = pw.CharField() # YYYY-MM-DD
    time = pw.CharField() # HH:MM
    zhqd = pw.IntegerField(column_name='综合强度')
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_hot

# 财联社热度题材
class CLS_HotTc(pw.Model):
    keys = ('code', 'day', 'ctime')
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField(null = True, default = "")
    name = pw.CharField()
    up = pw.BooleanField() # 是否是上涨, 还是下跌
    ctime = pw.CharField()
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_hot

# 材联社--指数涨跌(板块、概念)
class CLS_ZS_ZD(pw.Model):
    keys = ('code', 'day')
    code = pw.CharField() #指数代码
    name = pw.CharField(default = '') #指数名称
    type_ = pw.CharField() #指数类型 HY | GN
    day = pw.CharField() # YYYY-MM-DD
    zf = pw.FloatField(default = 0) # 涨幅
    fund = pw.FloatField(default = 0) #资金流向 (亿)
    pm = pw.IntegerField() # 涨跌排名
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_cls_zs_zd

db_cls_gntc.create_tables([CLS_GNTC])
db_cls_zs.create_tables([CLS_ZS])
db_cls_zs_zd.create_tables([CLS_ZS_ZD])
db_cls_zt.create_tables([CLS_ZT, CLS_UpDown])
db_cls_hot.create_tables([CLS_SCQX, CLS_SCQX_Time, CLS_HotTc])

if __name__ == '__main__':
    import orm_urils
    clsGntcDB = pw.SqliteDatabase(f'{path}/db/CLS_GNTC.db')
    clsDB = pw.SqliteDatabase(f'{path}/db/CLS.db')
    
    orm_urils.move_table_data(clsGntcDB, CLS_GNTC)
    orm_urils.move_table_data(clsGntcDB, CLS_ZS)
    orm_urils.move_table_data(clsDB, CLS_ZT)
    orm_urils.move_table_data(clsDB, CLS_ZS_ZD)
    orm_urils.move_table_data(clsDB, CLS_HotTc)
    orm_urils.move_table_data(clsDB, CLS_SCQX_Time)
    orm_urils.move_table_data(clsDB, CLS_SCQX)
    orm_urils.move_table_data(clsDB, CLS_UpDown)