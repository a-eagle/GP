import requests, win32gui, sys, os, json
import peewee as pw

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(__file__))

from orm.ths_orm import THS_HotZH
from ui import kline_utils

def writeFile(datas):
    f = open('a.txt', 'w')
    for k in datas:
        txt = json.dumps(datas[k], ensure_ascii = False)
        f.write(txt)
        f.write('\n')
    f.close()

def getAllTopCodes(fromDay : int):
    qr = THS_HotZH.select(THS_HotZH.code, THS_HotZH.day).where(THS_HotZH.zhHotOrder <= 10, THS_HotZH.day >= fromDay).tuples()
    # print(qr)
    codes = {}
    for it in qr:
        code = f'{it[0] :06d}'
        if code[0] not in '036':
            continue
        if code not in codes:
            codes[code] = {'code': code, 'day': []}
        codes[code]['day'].append(it[1])
    # cc = [c for c in codes]
    # print(len(cc), cc)
    # writeFile(codes)
    cs = [codes[c] for c in codes]
    return cs

if __name__ == '__main__':
    FROM_DAY = 20250501
    codes = getAllTopCodes(FROM_DAY)
    win = kline_utils.createKLineWindow()
    first = codes[0]
    win.changeCode(first['code'])
    win.klineWin.marksMgr.setMarkDay(first['day'])
    win.setCodeList(codes)
    win.mainWin = True
    win32gui.PumpMessages()

