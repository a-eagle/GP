import peewee as pw
import sys, datetime, os, time

path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)
from orm import base_orm, orm_urils

db_def = pw.SqliteDatabase(f'{path}/db/My.db') # 题材库

# 画线
class TextLine(base_orm.BaseModel):
    keys = ('keyID', )
    code = pw.CharField()
    kind = pw.CharField()
    period = pw.CharField(null = True)
    _startPos = pw.CharField(default = None)
    _endPos = pw.CharField(default = None, null = True)
    info = pw.CharField(default = None, null = True)
    keyID = pw.FloatField(default = time.time)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)
    
    class Meta:
        database = db_def

class MySettings(base_orm.BaseModel):
    keys = ('platform', 'mainKey', 'subKey')
    platform = pw.CharField(default = '')
    mainKey =  pw.CharField(default = '')
    subKey =  pw.CharField(default = '')
    val = pw.CharField(null = True)
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_def

db_def.create_tables([TextLine, MySettings])

if base_orm.VersionManager.getVersion('TextLine') == 0:
    base_orm.VersionManager.saveVersion('TextLine', 1)
    db_def.drop_tables([TextLine])
    db_def.create_tables([TextLine])

if base_orm.VersionManager.getVersion('TextLine') == 1:
    base_orm.VersionManager.saveVersion('TextLine', 2)
    orm_urils.ModelManager.addField(TextLine, TextLine.period)
    TextLine.update(period = 'day').execute()

