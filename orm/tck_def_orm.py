import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]
db_tck_def = pw.SqliteDatabase(f'{path}GP/db/TCK_def.db') # 题材库 

# 画线
class TextLine(pw.Model):
    code = pw.CharField()
    kind = pw.CharField()
    _startPos = pw.CharField(default = None)
    _endPos = pw.CharField(default = None, null = True)
    info = pw.CharField(default = None, null = True)
    
    class Meta:
        database = db_tck_def

class MyHotGn(pw.Model):
    info = pw.CharField(null = True)
    class Meta:
        database = db_tck_def

class MySettings(pw.Model):
    mainKey =  pw.CharField()
    subKey =  pw.CharField(null = True)
    val = pw.CharField(null = True)
    class Meta:
        database = db_tck_def

db_tck_def.create_tables([TextLine, MyHotGn, MySettings])

