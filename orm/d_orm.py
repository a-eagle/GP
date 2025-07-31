import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]
db_pankou = pw.SqliteDatabase(f'{path}GP/db/PanKou.db')

# 涨停盘口(收盘)
class ZT_PanKou(pw.Model):
    keys = ('day', 'code')
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    info = pw.CharField()
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_pankou

db_hotvol = pw.SqliteDatabase(f'{path}GP/db/HotVol.db')
#热度股成交量前100信息
class HotVol(pw.Model):
    keys = ('day', )
    day = pw.CharField() # YYYY-MM-DD
    p1 = pw.IntegerField() # 第一  亿元
    p10 = pw.IntegerField() # 第20
    p20 = pw.IntegerField() # 第20
    p50 = pw.IntegerField() # 第50
    p100 = pw.IntegerField() # 第100

    avg0_10 = pw.IntegerField() # 亿元 前10平均
    avg10_20 = pw.IntegerField() # 前11 ~ 20平均
    avg20_50 = pw.IntegerField() # 前21 ~ 50平均
    avg50_100 = pw.IntegerField() # 前51 ~ 100平均
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_hotvol

db_zhangsu = pw.SqliteDatabase(f'{path}GP/db/ZhangSu.db')
# Local涨速
class LocalSpeedModel(pw.Model):
    keys = ('day', 'code')
    day = pw.IntegerField() # 日期
    code = pw.CharField() #股票代码
    fromMinute = pw.IntegerField()
    endMinute  = pw.IntegerField()
    minuts =  pw.IntegerField() # 时间
    zf = pw.FloatField() #涨幅
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_zhangsu
        table_name = 'LocalZS'        

db_pankou.create_tables([ZT_PanKou])
db_hotvol.create_tables([HotVol])
db_zhangsu.create_tables([LocalSpeedModel])