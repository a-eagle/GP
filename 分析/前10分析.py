import requests, win32gui, sys, os, json
import peewee as pw

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(os.path.dirname(__file__))

from orm.ths_orm import THS_HotZH
from ui import kline_utils

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

def onChangeCode(evt, args):
    md = evt.src.klineWin.marksMgr.data
    days = []
    for d in md:
        days.append(d)
    config = {'code': evt.code, 'day': days}
    writeConfig(config)

if __name__ == '__main__':
    FROM_DAY = 20250501
    codes = getAllTopCodes(FROM_DAY)
    win = kline_utils.createKLineWindow()
    first = codes[0]
    config = readConfig()
    if config:
        first = config
    win.changeCode(first['code'])
    win.klineWin.marksMgr.setMarkDay(first['day'])
    win.setCodeList(codes)
    win.mainWin = True
    win.addNamedListener('ChangeCode', onChangeCode)
    win32gui.PumpMessages()

