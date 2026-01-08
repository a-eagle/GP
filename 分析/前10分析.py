import requests, win32gui, sys, os, json
import peewee as pw

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(__file__))

from orm.ths_orm import THS_HotZH, db_hot_zh
from ui import kline_utils, kline_win

MAX_TOP_HOT = 10 # top 10 hots

def writeConfig(config):
    path = os.path.dirname(__file__)
    txt = json.dumps(config, ensure_ascii = False)
    f = open(os.path.join(path, 'config.json'), 'w', encoding = 'utf-8')
    f.write(txt)
    f.close()

def readConfig():
    path = os.path.dirname(__file__)
    path = os.path.join(path, 'config.json')
    if not os.path.exists(path):
        return None
    f = open(path, 'r', encoding = 'utf-8')
    txt = f.read()
    f.close()
    return json.loads(txt)

def getAllTopCodes():
    qr = THS_HotZH.select(THS_HotZH.code, pw.fn.count().alias('cc')).where(THS_HotZH.zhHotOrder <= MAX_TOP_HOT).group_by(THS_HotZH.code).tuples()
    # sql = f'select code, count(*) as cc from 个股热度综合排名 where 综合热度排名 <= {MAX_TOP_HOT} group by code order by cc desc '
    # cc = db_hot_zh.execute_sql(sql)
    # rs = cc.fetchall()
    codes = []
    for it in qr:
        code = f'{it[0] :06d}'
        num = it[1]
        if code[0] not in '036':
            continue
        codes.append((code, num))
    codes.sort(key = lambda x : x[1], reverse = True)
    cs = [c[0] for c in codes]
    return cs

def onChangeCode(evt, args):
    code = int(evt.code)
    setMarkDays(evt.src, code)
    # config = {'code': code}
    # writeConfig(config)

def setMarkDays(win : kline_win.KLineCodeWindow, code):
    qr = THS_HotZH.select(THS_HotZH.day).where(THS_HotZH.code == code, THS_HotZH.zhHotOrder <= MAX_TOP_HOT).tuples()
    # print(qr)
    days = []
    for d in qr:
        days.append(d[0])
    win.klineWin.marksMgr.clearMarkDay()
    win.klineWin.marksMgr.setMarkDay(days)

if __name__ == '__main__':
    codes = getAllTopCodes()
    cfg = readConfig()
    win = kline_utils.createKLineWindow()
    first = codes[51]
    win.changeCode(first)
    # setMarkDays(win, first)
    win.setCodeList(codes)
    win.mainWin = True
    win.addNamedListener('ChangeCode', onChangeCode)
    win32gui.PumpMessages()

