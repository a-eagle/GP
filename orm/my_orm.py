import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))
db_def = pw.SqliteDatabase(f'{path}/db/My.db') # 题材库

# 画线
class TextLine(pw.Model):
    code = pw.CharField()
    kind = pw.CharField()
    _startPos = pw.CharField(default = None)
    _endPos = pw.CharField(default = None, null = True)
    info = pw.CharField(default = None, null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)
    
    class Meta:
        database = db_def

class MySettings(pw.Model):
    mainKey =  pw.CharField()
    subKey =  pw.CharField(null = True)
    val = pw.CharField(null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)
    
    class Meta:
        database = db_def

db_def.create_tables([TextLine])

