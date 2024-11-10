import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]
db_tck_def = pw.SqliteDatabase(f'{path}GP/db/TCK_def.db') # 题材库 


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
        database = db_tck_def
        table_name = '题材梳理A'

# 题材库-词条
class TCK_CiTiao(pw.Model):
    name = pw.CharField() # 词条

    class Meta:
        database = db_tck_def
        table_name = '词条'

class DailyFuPan(pw.Model):
    day = pw.CharField() # YYYY-MM-DD
    info = pw.CharField(null = True) # 复盘信息
    
    class Meta:
        database = db_tck_def
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
        database = db_tck_def
        table_name = '标记'

class DrawLine(pw.Model):
    code = pw.CharField()
    dateType = pw.CharField()
    day = pw.CharField() # YYYYMMDD
    kind = pw.CharField()
    info = pw.CharField(null = True)
    
    class Meta:
        database = db_tck_def
        table_name = '画线'

# 自选股
class MyObserve(pw.Model):
    code = pw.CharField()
    name = pw.CharField()
    kind = pw.CharField(null = True, default = 'def')
    day = pw.DateField(null = True, default = datetime.date.today)
    order = pw.IntegerField(null = True, default = 10000, column_name = '_order')
    class Meta:
        database = db_tck_def
        table_name = '自选股'

class MyNote(pw.Model):
    info = pw.CharField(null = True)
    class Meta:
        database = db_tck_def
        table_name = '笔记'

class MyHotGn(pw.Model):
    info = pw.CharField(null = True)
    class Meta:
        database = db_tck_def
        table_name = '热点概念'

db_tck_def.create_tables([TCK_CiTiao, DailyFuPan, Mark, DrawLine, MyObserve, MyNote, MyHotGn])

