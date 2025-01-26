import peewee as pw
import sys

path = sys.argv[0]
path = path[0 : path.index('GP') ]

db_lhb = pw.SqliteDatabase(f'{path}/GP/db/LHB.db')
#db_ths = pw.SqliteDatabase(f'{path}GP/db/THS_F10.db')

class TdxLHB(pw.Model):
    day = pw.CharField(column_name = '日期' ) # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField()
    title = pw.CharField(column_name = '上榜类型', null=True)
    price = pw.FloatField(column_name = '收盘价', null=True)
    zd = pw.FloatField(column_name = '涨跌幅' , null=True)
    #vol = pw.IntegerField(column_name = '成交量_万' , null=True) # 万股
    cjje = pw.DecimalField(column_name = '成交额_亿' , null=True, decimal_places = 1, max_digits = 10) # 亿元
    
    mrje = pw.DecimalField(column_name = '买入金额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    #mrjeRate = pw.IntegerField(column_name = '买入金额_占比' , null=True) #  (占总成交比例%)
    mcje = pw.DecimalField(column_name = '卖出金额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    #mcjeRate = pw.IntegerField(column_name = '卖出金额_占比' , null=True) #  (占总成交比例%)
    jme = pw.DecimalField(column_name = '净买额_亿' , null=True, decimal_places = 1, max_digits = 10) #  (亿元)
    famous = pw.CharField(column_name = '知名游资' , null=True)
    detail = pw.CharField(column_name = '详细', null = True)

    class Meta:
        database = db_lhb


db_lhb.create_tables([TdxLHB])


if __name__ == '__main__':
    pass
    

