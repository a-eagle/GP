import peewee as pw
import sys

path = __file__[0 : __file__.upper().index('GP')]
db_tck = pw.SqliteDatabase(f'{path}GP/db/TCK.db') # 题材库

class KPL_ZT(pw.Model):
    code = pw.CharField()
    name = pw.CharField(null = True)
    day = pw.CharField() # YYYY-MM-DD
    ztTime = pw.CharField(null = True, column_name='涨停时间')
    status = pw.CharField(null = True, column_name='状态')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    ztNum = pw.IntegerField(null=True, column_name='涨停数量')
    remark = pw.CharField(null=True, column_name='备注')

    class Meta:
        database = db_tck
        table_name = '开盘啦涨停'

class KPL_SCQX(pw.Model):
    day = pw.CharField()
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_tck
        table_name = '开盘啦市场情绪'

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
        table_name = '同花顺涨停'

class CLS_ZT(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    code = pw.CharField()
    name = pw.CharField(null = True)
    lbs = pw.IntegerField(default = 0, column_name='连板数')
    ztReason = pw.CharField(null = True, column_name='涨停原因')
    detail = pw.CharField(null = True, column_name='详情')

    class Meta:
        database = db_tck
        table_name = '财联社涨停'

class CLS_SCQX(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    zhqd = pw.IntegerField(column_name='综合强度')

    class Meta:
        database = db_tck
        table_name = '财联社市场情绪'

# 题材库-题材梳理
class TCK_TCGN(pw.Model):
    tcgn = pw.CharField() # 题材、概念 （大类）
    tcgn_sub = pw.CharField() # 题材、概念 （小类）
    code = pw.CharField()
    name = pw.CharField()
    info = pw.TextField(null=True) # 详细信息
    order_ = pw.IntegerField()
    mark = pw.IntegerField(null=True)

    class Meta:
        database = db_tck
        table_name = '题材梳理A'

# 题材库-词条
class TCK_CiTiao(pw.Model):
    name = pw.CharField() # 词条

    class Meta:
        database = db_tck
        table_name = '词条'

class DailyFuPan(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    info = pw.CharField(null = True) # 复盘信息
    
    class Meta:
        database = db_tck
        table_name = '复盘日记'

class Mark(pw.Model):
    kind = pw.CharField(null = True) # 
    day = pw.CharField(null = True) # YYYY-MM-DD
    code = pw.CharField(null = True)
    name = pw.CharField(null = True)
    markColor = pw.IntegerField(default = 0)
    markText = pw.CharField(null = True)
    endDay = pw.CharField(null = True) # YYYY-MM-DD

    class Meta:
        database = db_tck
        table_name = '标记'

class DrawLine(pw.Model):
    code = pw.CharField()
    dateType = pw.CharField()
    day = pw.CharField()
    kind = pw.CharField()
    info = pw.CharField(null = True)
    
    class Meta:
        database = db_tck
        table_name = '画线'

# 自选股
class MySelCode(pw.Model):
    code = pw.CharField()
    name = pw.CharField()
    class Meta:
        database = db_tck
        table_name = '自选股'

#db_tck.drop_tables([DrawLine])
db_tck.create_tables([THS_ZT, CLS_ZT, KPL_ZT, KPL_SCQX, CLS_SCQX, TCK_TCGN, 
                      TCK_CiTiao, DailyFuPan, Mark, DrawLine, MySelCode])