import peewee as pw
import sys, datetime, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import base_orm

# 笔记
class MyNote(base_orm.BaseModel):
    tag = pw.CharField() #
    cnt = pw.CharField(null = True, max_length = 1024 * 30) #
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

# 颜色标记
class MyMarkColor(base_orm.BaseModel):
    keys = ('code', 'day')
    code = pw.CharField() #
    secu_code = pw.CharField() #
    name = pw.CharField(null = True) #
    color = pw.CharField(null = True) # html/css color
    day  = pw.CharField(null = True) # YYYY-MM-DD
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

base_orm.db_mysql.create_tables([MyNote, MyMarkColor])

if __name__ == '__main__':
    pass
