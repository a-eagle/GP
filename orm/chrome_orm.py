import peewee as pw
import sys, datetime

path = __file__[0 : __file__.upper().index('GP')]

db_chrome = pw.SqliteDatabase(f'{path}GP/db/Chrome.db')

# 笔记
class MyNote(pw.Model):
    tag = pw.CharField() #
    cnt = pw.CharField(null = True) #
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_chrome

# 颜色标记
class MyMarkColor(pw.Model):
    code = pw.CharField() #
    secu_code = pw.CharField() #
    name = pw.CharField(null = True) #
    color = pw.CharField(null = True) # html/css color
    day  = pw.CharField(null = True) # YYYY-MM-DD
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    class Meta:
        database = db_chrome

db_chrome.create_tables([MyNote, MyMarkColor])
