import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))

db_gntc = pw.SqliteDatabase(f'{path}/db/THS_GNTC.db')
# 同花顺--概念题材
class THS_GNTC(pw.Model):
    keys = ('code', )
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    gn = pw.CharField(null=True) # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(null=True) # 常规概念对应的代码;分隔
    hy = pw.CharField(null=True) # 行业
    hy_2_name = pw.CharField(null=True) # 二级行业名称
    hy_2_code = pw.CharField(null=True) # 二级行业代码
    hy_3_name = pw.CharField(null=True) # 三级行业名称
    hy_3_code = pw.CharField(null=True) # 三级行业代码
    zgb = pw.FloatField(null=True) # 总股本 股
    ltag = pw.FloatField(null=True) # 流通a股 股
    xsg = pw.FloatField(null=True) # 限售股 股
    ltsz = pw.FloatField(null=True) # 流通市值
    zsz = pw.FloatField(null=True) #  总市值
    pe = pw.FloatField(null=True) # 静态市盈率
    peTTM = pw.FloatField(null=True) # 市盈率(pe,ttm)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_gntc
        table_name = '概念题材'

db_hot = pw.SqliteDatabase(f'{path}/db/THS_Hot.db')
db_hot_zh = pw.SqliteDatabase(f'{path}/db/THS_HotZH.db')

# 同花顺--个股热度排名
class THS_Hot(pw.Model):
    # no keys
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    time = pw.IntegerField(column_name = '时间') # 刷新时间  HHMM
    hotValue = pw.IntegerField(column_name = '热度值_万' ) #
    hotOrder = pw.IntegerField(column_name = '热度排名' ) #
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_hot
        table_name = '个股热度排名'

# 同花顺--个股热度综合排名
class THS_HotZH(pw.Model):
    keys = ('day', 'code')
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    avgHotValue = pw.IntegerField(column_name = '平均热度值_万' )
    avgHotOrder = pw.FloatField(column_name = '平均热度排名' )
    zhHotOrder = pw.IntegerField(column_name = '综合热度排名' )
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_hot_zh
        table_name = '个股热度综合排名'

db_thszs = pw.SqliteDatabase(f'{path}/db/THS_ZS.db')
class THS_ZS(pw.Model):
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称

    class Meta:
        database = db_thszs
        table_name = '同花顺指数_view'
        primary_key = False
        # create view 同花顺指数_view (code, name) as select code, name from 同花顺指数涨跌信息 where day = (select max(day) from 同花顺指数涨跌信息)

# 同花顺指数涨跌信息
class THS_ZS_ZD(pw.Model):
    keys = ('day', 'code')
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField() #指数代码
    name = pw.CharField(null = True) #指数名称
    close = pw.FloatField(default = 0)
    open = pw.FloatField(default = 0)
    high = pw.FloatField(default = 0)
    rate = pw.FloatField(default = 0)
    money = pw.FloatField(default = 0) #亿(元)
    vol = pw.FloatField(default = 0) # 亿(股)
    zdf = pw.FloatField(default = 0) #涨跌幅
    zdf_topLevelPM = pw.IntegerField(default = 0) # 一级概念、行业排名
    zdf_PM = pw.IntegerField(default = 0) # 全部排名
    markColor = pw.IntegerField(null = True, column_name = 'mark_1') # 标记 1
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_thszs
        table_name = '同花顺指数涨跌信息'

db_ths = pw.SqliteDatabase(f'{path}/db/THS.db')
# 同花顺涨停
class THS_ZT(pw.Model):
    keys = ('code', 'day')
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    #ztNum = pw.IntegerField(null=True, column_name='涨停数量')
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_ths

db_ths_codes = pw.SqliteDatabase(f'{path}/db/THS_Codes.db')
# 个股信息
class THS_CodesInfo(pw.Model):
    keys = ('code', )
    code = pw.CharField()
    name = pw.CharField(null = True)

    jrl = pw.CharField(null = True) # 近4年净利润
    jrl_2 = pw.CharField(null = True) # 近4季度净利润
    yysr = pw.CharField(null = True) # 近4年营业收入
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_ths_codes

db_hot.create_tables([THS_Hot])
db_hot_zh.create_tables([THS_HotZH])
db_thszs.create_tables([THS_ZS_ZD])
db_gntc.create_tables([THS_GNTC])
db_ths.create_tables([THS_ZT])
db_ths_codes.create_tables([THS_CodesInfo])

if __name__ == '__main__':
    pass