import peewee as pw
import sys, datetime, os, json

path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)
from orm import base_orm

class TdxLHB(base_orm.NeedSyncModel):
    keys = ('code', 'day', 'title')
    day = pw.CharField(max_length = 12) # YYYY-MM-DD
    code = pw.CharField(max_length = 12)
    name = pw.CharField(max_length = 24)
    title = pw.CharField( null=True, max_length = 240) # 上榜类型
    price = pw.FloatField( null=True) # 收盘价
    zd = pw.FloatField(null=True) # 涨跌幅
    cjje = pw.DecimalField(null=True, decimal_places = 1, max_digits = 10) #  成交额_亿(亿元)
    mrje = pw.DecimalField(null=True, decimal_places = 1, max_digits = 10) #  买入金额_亿(亿元)
    mcje = pw.DecimalField(null=True, decimal_places = 1, max_digits = 10) #  卖出金额_亿(亿元)
    jme = pw.DecimalField(null=True, decimal_places = 1, max_digits = 10) #  净买额_亿(亿元)
    detail = pw.CharField(null = True, max_length = 8092) #详细

base_orm.db_mysql.create_tables([TdxLHB])


if __name__ == '__main__':
    pass