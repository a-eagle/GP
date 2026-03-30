import peewee as pw
import sys, datetime, os, time

path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)
from orm import base_orm, orm_urils
from utils import cutils

# 画线
class TextLine(base_orm.NeedSyncModel):
    keys = ('keyID', )
    code = pw.CharField(max_length = 12)
    kind = pw.CharField(max_length = 24)
    period = pw.CharField(null = True, max_length = 24)
    _startPos = pw.CharField(default = None, max_length = 120)
    _endPos = pw.CharField(default = None, null = True, max_length = 120)
    info = pw.CharField(default = None, null = True, max_length = 1024)
    keyID = pw.BigIntegerField(null = True, default = cutils.nowTimeInt)
    
class MySettings(base_orm.NeedSyncModel):
    keys = ('platform', 'mainKey', 'subKey')
    platform = pw.CharField(default = '')
    mainKey =  pw.CharField(default = '')
    subKey =  pw.CharField(default = '')
    val = pw.CharField(null = True, max_length = 1024)

class MySelect(base_orm.NeedSyncModel):
    keys = ('code')
    code = pw.CharField()
    name =  pw.CharField(null = True)
    day =  pw.CharField()

base_orm.db_mysql.create_tables([TextLine, MySettings, MySelect])

if __name__ == '__main__':
    pass

