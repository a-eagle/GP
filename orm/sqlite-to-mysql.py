import sys, peewee as pw, os, datetime, time

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

initMysqlDb()

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import base_orm, chrome_orm, cls_orm, d_orm, lhb_orm, my_orm, orm_urils, ths_orm

def motifyUpdateTime(info):
    ut = info.get('updateTime', None)
    if not ut:
        return
    st = datetime.datetime.fromisoformat(ut)
    mms = int(st.timestamp() * 1000 * 1000)
    info['updateTime'] = mms

def motifyTextLine(info):
    motifyUpdateTime(info)
    keyId = info.get('keyID', None)
    if not keyId:
        return
    mms = int(keyId * 1000 * 1000 * 10)
    info['keyID'] = mms

def move():
    import orm_urils
    # orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/delete.db'), base_orm.DeleteModel)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/Version.db'), base_orm.VersionModel)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/chrome.db'), chrome_orm.MyNote, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/cls_gntc_n.db'),  cls_orm.CLS_GNTC, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/cls_zs.db'), cls_orm.CLS_ZS, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZS_ZD.db'), cls_orm.CLS_ZS_ZD, srcTableName='CLS_ZS_ZD', modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZT.db'), cls_orm.CLS_ZT, descSrcColsMap = {'lbs': '连板数', 'ztReason':'涨停原因', 'detail':'详情'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_ZT.db'), cls_orm.CLS_UpDown, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_SCQX, descSrcColsMap={'zhqd': '综合强度'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_SCQX_Time, descSrcColsMap={'zhqd': '综合强度'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/CLS_HOT.db'), cls_orm.CLS_HotTc, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/PanKou.db'),  d_orm.ZT_PanKou, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/HotVol.db'),  d_orm.HotVol, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/ZhangSu.db'),  d_orm.LocalSpeedModel, srcTableName='LocalZS', modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/DiffBkGn.db'),  d_orm.DiffBkGnModel, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/LHB.db'),  lhb_orm.TdxLHB,
                                         descSrcColsMap={'day': '日期', 'title':'上榜类型', 'price':'收盘价', 'zd':'涨跌幅',
                                                         'cjje':'成交额_亿', 'mrje':'买入金额_亿', 'mcje':'卖出金额_亿', 'jme':'净买额_亿', 'detail':'详细'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/My.db'),  my_orm.TextLine, modifyFunc=motifyTextLine)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/My.db'),  my_orm.MySettings, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_GNTC.db'),  ths_orm.THS_GNTC, srcTableName='概念题材', modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_HotZH.db'),  ths_orm.THS_HotZH, srcTableName='个股热度综合排名', descSrcColsMap={'day':'日期', 'avgHotValue':'平均热度值_万', 'avgHotOrder': '平均热度排名', 'zhHotOrder':'综合热度排名'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZS.db'),  ths_orm.THS_ZS, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZS_ZD.db'),  ths_orm.THS_ZS_ZD, srcTableName='同花顺指数涨跌信息', modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_ZT.db'),  ths_orm.THS_ZT, descSrcColsMap={'ztTime':'涨停时间', 'status':'状态', 'ztReason':'涨停原因'}, modifyFunc=motifyUpdateTime)
    orm_urils.ModelManager.copyTableData(pw.SqliteDatabase('db/THS_Codes.db'),  ths_orm.THS_CodesInfo, modifyFunc=motifyUpdateTime)

    

if __name__ == '__main__':
    move()