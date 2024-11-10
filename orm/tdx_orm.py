import peewee as pw
import sys

path = sys.argv[0]
path = path[0 : path.index('GP') ]
voldb = pw.SqliteDatabase(f'{path}GP/db/Tdx.db')

class TdxVolPMModel(pw.Model):
    code = pw.CharField() #股票代码
    name = pw.CharField() #股票名称
    day = pw.IntegerField() # 日期
    amount = pw.FloatField() #成交额 （亿元）
    pm = pw.IntegerField() #全市成交排名

    class Meta:
        database = voldb
        table_name = '成交额排名'

class TdxLSModel(pw.Model):
    day = pw.IntegerField(column_name='日期')
    amount = pw.FloatField(column_name='成交额', default=0) # （亿元）
    upNum = pw.IntegerField(column_name='上涨家数', default=0)
    downNum = pw.IntegerField(column_name = '下跌家数', default=0)
    zeroNum = pw.IntegerField(column_name = '平盘家数', default=0)

    ztNum = pw.IntegerField(column_name='涨停数', default=0)
    lbNum = pw.IntegerField(column_name='连板数', default=0) #二板以上家数
    zgb = pw.IntegerField(column_name='最高板', default=0)
    dtNum = pw.IntegerField(column_name='跌停数', default=0)

    z0_2 = pw.IntegerField(column_name='涨幅0_2', default=0) # (0, 2]
    z2_5 = pw.IntegerField(column_name='涨幅2_5', default=0) # (2, 5]
    z5_7 = pw.IntegerField(column_name='涨幅5_7', default=0) # (5, 7]
    z7 = pw.IntegerField(column_name='涨幅7以上', default=0) # > 7

    d0_2 = pw.IntegerField(column_name='跌幅0_2', default=0) # (0, -2]
    d2_5 = pw.IntegerField(column_name='跌幅2_5', default=0) # (-2, -5]
    d5_7 = pw.IntegerField(column_name='跌幅5_7', default=0) # (-5, -7]
    d7 = pw.IntegerField(column_name='跌幅7以上', default=0) # < -7

    class Meta:
        database = voldb
        table_name = '两市总体情况'

voldb.create_tables([TdxVolPMModel, TdxLSModel])
