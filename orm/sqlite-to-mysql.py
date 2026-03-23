import sys, peewee as pw, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import base_orm, chrome_orm, cls_orm, d_orm, lhb_orm, my_orm, orm_urils, ths_orm

def initMysqlDb():
    import pymysql
    conn = pymysql.connect(host='localhost', user='root', password='root@2025')
    cs = conn.cursor()
    cs.execute('show databases')
    rs = cs.fetchall()
    dbs = [r[0].upper() for r in rs]
    if 'GP' in dbs:
        return
    cs.execute('create database GP')
    conn.close()

def move():
    import orm_urils
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/delete.db'), base_orm.DeleteModel)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/Version.db'), base_orm.VersionModel)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/chrome.db'), chrome_orm.MyNote)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/cls_gntc_n.db'),  cls_orm.CLS_GNTC)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/cls_zs.db'), cls_orm.CLS_ZS)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZS_ZD.db'), 'CLS_ZS_ZD', cls_orm.CLS_ZS_ZD)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZT.db'), cls_orm.CLS_ZT, descSrcColsMap = {'lbs': '连板数', 'ztReason':'涨停原因', 'detail':'详情'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZT.db'), cls_orm.CLS_UpDown)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_SCQX, descSrcColsMap={'zhqd': '综合强度'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_SCQX_Time, descSrcColsMap={'zhqd': '综合强度'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_HotTc)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/PanKou.db'),  d_orm.ZT_PanKou)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/HotVol.db'),  d_orm.HotVol)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/ZhangSu.db'),  d_orm.LocalSpeedModel, srcTableName='LocalZS')
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/DiffBkGn.db'),  d_orm.DiffBkGnModel)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/LHB.db'),  lhb_orm.TdxLHB,
                                         descSrcColsMap={'day': '日期', 'title':'上榜类型', 'price':'收盘价', 'zd':'涨跌幅',
                                                         'cjje':'成交额_亿', 'mrje':'买入金额_亿', 'mcje':'卖出金额_亿', 'jme':'净买额_亿', 'detail':'详细'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/My.db'),  my_orm.TextLine)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/My.db'),  my_orm.MySettings)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_GNTC.db'),  ths_orm.THS_GNTC, srcTableName='概念题材')
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_HotZH.db'),  ths_orm.THS_HotZH, srcTableName='个股热度综合排名', descSrcColsMap={'day':'日期', 'avgHotValue':'平均热度值_万', 'avgHotOrder': '平均热度排名', 'zhHotOrder':'综合热度排名'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZS.db'),  ths_orm.THS_ZS)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZS_ZD.db'),  ths_orm.THS_ZS_ZD, srcTableName='同花顺指数涨跌信息')
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZT.db'),  ths_orm.THS_ZT, descSrcColsMap={'ztTime':'涨停时间', 'status':'状态', 'ztReason':'涨停原因'})
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_Codes.db'),  ths_orm.THS_CodesInfo)

if __name__ == '__main__':
    initMysqlDb()
    move()