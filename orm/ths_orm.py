import peewee as pw
import sys

path = __file__[0 : __file__.upper().index('GP')]
db_f10 = pw.SqliteDatabase(f'{path}GP/db/THS_F10.db')

# 同花顺--最新动态
class THS_Newest(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    zsz = pw.IntegerField(null=True, column_name='总市值') # （亿元）
    gsld = pw.CharField(null=True, column_name='公司亮点')
    kbgs = pw.CharField(null=True, column_name='可比公司')
    cwfx = pw.CharField(null=True, column_name='财务分析')

    class Meta:
        database = db_f10
        table_name = '最新动态'

# 同花顺--前十大流通股东
class THS_Top10_LTGD(pw.Model):
    code = pw.CharField() #股票代码
    day = pw.CharField(null = True) # 日期 YYYY-MM-DD
    rate = pw.FloatField(null = True) # 前十大流通股东占比 %
    change = pw.FloatField(null=True, column_name='较上期变化') # 万股
    class Meta:
        database = db_f10
        table_name = '前十大流通股东'

# 同花顺-- 机构持股 (主力持仓)
class THS_JGCG(pw.Model):
    code = pw.CharField() #股票代码
    day = pw.CharField(null=True) # 日期(年报、季报、中报等)   中报改为二季报， 年报改为四季报
    jjsl = pw.IntegerField(null=True, column_name='机构数量')
    rate = pw.FloatField(null=True, column_name='持仓比例')
    change = pw.FloatField(null=True, column_name='较上期变化') # (万股)
    day_sort = pw.CharField(null=True) # 日期，用于排序

    class Meta:
        database = db_f10
        table_name = '机构持股'

# 同花顺--行业对比（排名）
class THS_HYDB(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    day = pw.CharField() # 报告日期
    hy = pw.CharField(null=True, column_name='行业')
    hydj = pw.IntegerField(null = True, column_name='行业等级') #
    hysl = pw.IntegerField(null=True, column_name='同行数量') # 行业中股票总数量

    mgsy = pw.FloatField(null=True, column_name='每股收益') #
    mgjzc = pw.FloatField(null=True, column_name='每股净资产') #
    mgxjl = pw.FloatField(null=True, column_name='每股现金流') #
    jlr = pw.FloatField(null=True, column_name='净利润') #
    yyzsl = pw.FloatField(null=True, column_name='营业总收入') #
    zgb = pw.FloatField(null=True, column_name='总股本') #

    zhpm = pw.IntegerField(null = True, column_name='综合排名')

    class Meta:
        database = db_f10
        table_name = '行业对比'

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

#查询指字的股票代码的详细信息 
# return a dict of : {THS_Newest:最新动态、THS_GNTC:概念题材、THS_GD:股东、THS_JGCC:机构持仓、THS_HYDB_2:行业对比(二级)、THS_HYDB_3:行业对比(三级)}
def queryFullInfo(code):
    code = code.strip()
    rs = {'code' : code}
    rs['THS_Newest'] = THS_Newest.get_or_none(THS_Newest.code == code)
    rs['THS_GNTC'] = THS_GNTC.get_or_none(THS_GNTC.code == code)
    rs['THS_GD'] = THS_Top10_LTGD.get_or_none(THS_Top10_LTGD.code == code)
    rs['THS_JGCC'] = THS_JGCG.get_or_none(THS_JGCG.code == code)
    rs['THS_HYDB_2'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '二级'))
    rs['THS_HYDB_3'] = THS_HYDB.get_or_none((THS_HYDB.code == code) & (THS_HYDB.hyDJ == '三级'))
    #print(rs)
    return rs

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


#db3 = pw.SqliteDatabase(f'{path}GP/db/TaoGuBa.db')

# 淘股吧 remark表 收藏表
#class TaoGuBa_Remark(pw.Model):
#    info = pw.TextField() # 收藏信息
#    class Meta:
#        database = db3

# 大单流入流出情况
db_ddlr = pw.SqliteDatabase(f'{path}/GP/db/THS_DDLR.db')
class THS_DDLR(pw.Model):
    day = pw.CharField(max_length = 8) # YYYYMMDD
    code = pw.CharField(max_length = 6)
    name = pw.CharField(max_length= 24)
    activeIn = pw.DecimalField(column_name = '主动买入_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    activeOut = pw.DecimalField(column_name = '主动卖出_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    positiveIn = pw.DecimalField(column_name = '被动买入_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    positiveOut = pw.DecimalField(column_name = '被动卖出_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    total = pw.DecimalField(column_name = '净流入_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    amount = pw.DecimalField(column_name='成交额_亿', null=True, decimal_places = 1, max_digits = 10)
    class Meta:
        database = db_ddlr
        table_name = '个股大单买卖'

db_thszs = pw.SqliteDatabase(f'{path}GP/db/THS_ZS.db')
class THS_ZS(pw.Model):
    code = pw.CharField() #指数代码
    name = pw.CharField() #指数名称

    class Meta:
        database = db_thszs
        table_name = '同花顺指数_view'
        primary_key = False
        # create view 同花顺指数_view (code, name) as select code, name from 同花顺指数涨跌信息 where day = (select max(day) from 同花顺指数涨跌信息)

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
    zdf_50PM = pw.IntegerField(default = 0) # 50亿以上排名
    zdf_PM = pw.IntegerField(default = 0) # 全部排名
    markColor = pw.IntegerField(null = True, column_name = 'mark_1') # 标记 1

    class Meta:
        database = db_thszs
        table_name = '同花顺指数涨跌信息'

db_thsdde = pw.SqliteDatabase(f'{path}GP/db/THS_DDE.db')
class THS_DDE(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField() #指数代码
    name = pw.CharField(null = True) #指数代码
    dde_buy = pw.FloatField(default = 0) #  dde大单买入金额  (亿元)
    dde_sell = pw.FloatField(default = 0) # dde大单卖出金额  (亿元)
    dde = pw.FloatField(default = 0) # dde大单净额 (亿元)
    dde_pm = pw.IntegerField(default = 0) # dde大单净额排名

    class Meta:
        database = db_thsdde
        table_name = 'ths_dde'

#db_zt = pw.SqliteDatabase(f'{path}GP/db/THS_ZT.db')
class THS_ZT(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField() #指数代码
    name = pw.CharField(null = True) #指数代码

    tag = pw.CharField(null = True) # 涨停 | 炸板
    lbs = pw.CharField(null = True) # 几天几板
    lastZtTime = pw.CharField(null = True) # 最终涨停时间
    firstZtTime = pw.CharField(null = True) # 首次涨停时间
    ztMoney = pw.FloatField(default = 0) # 涨停封单额 (亿元)

    class Meta:
        #database = db_zt
        table_name = 'ths_zt'       

db_f10.create_tables([THS_JGCG, THS_HYDB, THS_Top10_LTGD, THS_Newest])
db_hot.create_tables([THS_Hot])
db_hot_zh.create_tables([THS_HotZH])
db_ddlr.create_tables([THS_DDLR])
db_thszs.create_tables([THS_ZS_ZD])
db_gntc.create_tables([THS_GNTC])
db_thsdde.create_tables([THS_DDE])
#db_zt.create_tables([THS_ZT])


if __name__ == '__main__':
    pass