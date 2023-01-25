import os, struct
import peewee as pw

db = pw.SqliteDatabase('hgt.db')

#沪股通十大成交金额
class HGT(pw.Model):
    day = pw.IntegerField()
    code = pw.CharField()
    jme = pw.IntegerField(default= 0, null=True) # column_name = '净买额'  万元
    mrje = pw.IntegerField(default= 0, null=True) #买入金额 万元
    mcje = pw.IntegerField(default= 0, null=True) #卖出金额 万元
    cjje = pw.IntegerField(default= 0, null=True) #成交金额 万元
    
    class Meta:
        database = db

#沪股通流入情况
class HGTAcc(pw.Model):
    day = pw.IntegerField()
    code = pw.CharField()
    zj = pw.IntegerField(default= 0, null=True) # 资金 万元
    cgsl = pw.IntegerField(default= 0, null=True) #持股数量
    per = pw.FloatField(default= 0, null=True) #持股占比 %
    zsz = pw.IntegerField(default= 0, null=True) #总市值 亿元
    
    class Meta:
        database = db



db.create_tables([HGT, HGTAcc])