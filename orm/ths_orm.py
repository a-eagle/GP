import peewee as pw
import sys

path = __file__[0 : __file__.upper().index('GP')]

db_gntc = pw.SqliteDatabase(f'{path}GP/db/THS_GNTC.db')
# 同花顺--概念题材
class THS_GNTC(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    gn = pw.CharField(null=True) # 常规概念，每概概念之间用;分隔
    gn_code = pw.CharField(null=True) # 常规概念对应的代码;分隔
    hy = pw.CharField(null=True) # 行业
    hy_2_name = pw.CharField(null=True) # 二级行业名称
    hy_2_code = pw.CharField(null=True) # 二级行业代码
    hy_3_name = pw.CharField(null=True) # 三级行业名称
    hy_3_code = pw.CharField(null=True) # 三级行业代码
    zsz = pw.IntegerField(null = True, default = 0) # 总市值, 亿元
    ltsz = pw.IntegerField(null = True, default = 0) # 流通市值, 亿元

    class Meta:
        database = db_gntc
        table_name = '概念题材'

db_hot = pw.SqliteDatabase(f'{path}GP/db/THS_Hot.db')
db_hot_zh = pw.SqliteDatabase(f'{path}GP/db/THS_HotZH.db')

# 同花顺--个股热度排名
class THS_Hot(pw.Model):
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    time = pw.IntegerField(column_name = '时间') # 刷新时间  HHMM
    hotValue = pw.IntegerField(column_name = '热度值_万' ) #
    hotOrder = pw.IntegerField(column_name = '热度排名' ) #

    class Meta:
        database = db_hot
        table_name = '个股热度排名'

# 同花顺--个股热度综合排名
class THS_HotZH(pw.Model):
    day = pw.IntegerField(column_name = '日期') # 刷新日期
    code = pw.IntegerField() #股票代码
    avgHotValue = pw.IntegerField(column_name = '平均热度值_万' )
    avgHotOrder = pw.FloatField(column_name = '平均热度排名' )
    zhHotOrder = pw.IntegerField(column_name = '综合热度排名' )

    class Meta:
        database = db_hot_zh
        table_name = '个股热度综合排名'

db_thszs = pw.SqliteDatabase(f'{path}GP/db/THS_ZS.db')
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

    class Meta:
        database = db_thszs
        table_name = '同花顺指数涨跌信息'

db_ths = pw.SqliteDatabase(f'{path}GP/db/THS.db')
# 同花顺涨停
class THS_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    #ztNum = pw.IntegerField(null=True, column_name='涨停数量')

    class Meta:
        database = db_ths

db_codes = pw.SqliteDatabase(f'{path}GP/db/codes.db')
# 个股信息(每日)
class CodesInfo(pw.Model):
    day = pw.CharField() # YYYYMMDD
    code = pw.CharField()
    name = pw.CharField(null = True)
    open = pw.FloatField()
    close = pw.FloatField()
    high = pw.FloatField()
    low = pw.FloatField()
    zf = pw.FloatField() # 涨跌幅 9.99%
    zd = pw.FloatField() # 涨跌价格（元）
    zhenfu = pw.FloatField() # 振幅
    vol = pw.FloatField() # 股
    amount = pw.FloatField() # 元
    rate = pw.FloatField() # 25%
    zgb = pw.FloatField() # 总股本 股
    ltag = pw.FloatField() # 流通a股 股
    zsz = pw.IntegerField() # 总市值  # 亿元
    pe = pw.FloatField() # 市盈率
    peTTM = pw.FloatField() # 市盈率(pe,ttm)
    ycPEs = pw.CharField() # 预测市盈率(三年)
    jrl = pw.FloatField() # 净利润

    class Meta:
        database = db_codes

db_hot.create_tables([THS_Hot])
db_hot_zh.create_tables([THS_HotZH])
db_thszs.create_tables([THS_ZS_ZD])
db_gntc.create_tables([THS_GNTC])
db_ths.create_tables([THS_ZT])
db_codes.create_tables([CodesInfo])


if __name__ == '__main__':
    pass