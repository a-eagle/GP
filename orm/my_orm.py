import peewee as pw
import sys, datetime, os

path = os.path.dirname(os.path.dirname(__file__))
from orm import base_orm

db_def = pw.SqliteDatabase(f'{path}/db/My.db') # 题材库

# 画线
class TextLine(base_orm.BaseModel):
    # keys = ('code', 'kind', '_startPos', '_endPos', 'info')
    code = pw.CharField()
    kind = pw.CharField()
    _startPos = pw.CharField(default = None)
    _endPos = pw.CharField(default = None, null = True)
    info = pw.CharField(default = None, null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)
    
    class Meta:
        database = db_def

class MySettings(base_orm.BaseModel):
    platform = pw.CharField(default = '')
    mainKey =  pw.CharField(default = '')
    subKey =  pw.CharField(default = '')
    val = pw.CharField(null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)
    
    class Meta:
        database = db_def

db_def.create_tables([TextLine, MySettings])

