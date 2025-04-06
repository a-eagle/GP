import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, cls_orm

ths_gntc_s = {}
cls_gntc_s = {}
ths_cls_zt_reason_s = {'loadTime': 0}

def _init():
    q = ths_orm.THS_GNTC.select().dicts()
    for it in q:
        ths_gntc_s[it['code']] = it
    q = cls_orm.CLS_GNTC.select().dicts()
    for it in q:
        cls_gntc_s[it['code']] = it

_init()

def get_CLS_THS_ZT_Reason(code):
    if type(code) == int:
        code = f'{code :06d}'
    if time.time() - ths_cls_zt_reason_s['loadTime'] <= 30 * 60:
        return ths_cls_zt_reason_s.get(code, None)
    ths_cls_zt_reason_s['loadTime'] = time.time()
    qr = ths_orm.THS_ZT.select(ths_orm.THS_ZT.code, ths_orm.THS_ZT.ztReason).where(
                                                              ths_orm.THS_ZT.id.in_(
                                                                  ths_orm.THS_ZT.select(pw.fn.max(ths_orm.THS_ZT.id)).where(
                                                                      ths_orm.THS_ZT.ztReason != '').group_by(ths_orm.THS_ZT.code)
                                                              )
                                                              ).tuples()
    for it in qr:
        obj = ths_cls_zt_reason_s.get(it[0])
        if not obj:
            obj = {'code': it[0], 'ths_ztReason': '', 'cls_ztReason': ''}
            ths_cls_zt_reason_s[it[0]] = obj
        obj['ths_ztReason'] = it[1]
    qr = cls_orm.CLS_ZT.select(cls_orm.CLS_ZT.code, cls_orm.CLS_ZT.ztReason).where(
                                                              cls_orm.CLS_ZT.id.in_(
                                                                  cls_orm.CLS_ZT.select(pw.fn.max(cls_orm.CLS_ZT.id)).where(
                                                                      cls_orm.CLS_ZT.ztReason != '').group_by(cls_orm.CLS_ZT.code)
                                                              )
                                                              ).tuples()
    for it in qr:
        obj = ths_cls_zt_reason_s.get(it[0])
        if not obj:
            obj = {'code': it[0], 'ths_ztReason': '', 'cls_ztReason': ''}
            ths_cls_zt_reason_s[it[0]] = obj
        obj['cls_ztReason'] = it[1]
    return ths_cls_zt_reason_s.get(code, None)

# return ths_orm.THS_GNTC dict
def get_THS_GNTC(code):
    if type(code) == int:
        code = f'{code :06d}'
    return ths_gntc_s.get(code, None)

def get_THS_GNTC_Attr(code, attrName):
    obj = get_THS_GNTC(code)
    if not obj:
        return None
    return obj.get(attrName, None)

def getAllGNTC():
    return ths_gntc_s

def getClsZs(code):
    obj = cls_orm.CLS_ZS.select().where(cls_orm.CLS_ZS.code == code)
    if obj: return obj.__data__
    return None

def getClsZsAttr(code, attrName):
    if code[0 : 3] != 'cls':
        return None
    obj = cls_orm.CLS_ZS.get_or_none(cls_orm.CLS_ZS.code == code)
    if obj: 
        return obj.__data__.get(attrName, None)
    return None

# day = int | str | date | datetime | float [ time.time() ]
def formatDate(day, hasSplit = True):
    if not day:
        return day
    if isinstance(day, float):
        day = datetime.datetime.fromtimestamp(day)
    if isinstance(day, datetime.date):
        if hasSplit:
            return f'{day.year}-{day.month :02d}-{day.day :02d}'
        return str(day.year * 10000 + day.month * 100 + day.day)
    if type(day) == int:
        if hasSplit:
            return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        return str(int)
    if type(day) == str:
        if len(day) == 8 and hasSplit:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
    return day

# ts = float[ time.time() ] | datetime.datetime
def formatDateTime(ts):
    if isinstance(ts, float):
        ts = datetime.datetime.fromtimestamp(ts)
    ds = formatDate(ts)
    ms = f'{ts.hour :02d}:{ts.minute :02d}:{ts.second :02d}'
    return f'{ds} {ms}'


if __name__ == '__main__':
    c = time.time()
    for k in ths_gntc_s:
        rs = get_CLS_THS_ZT_Reason(k)
        print(rs)
    diff = time.time() - c
    print(diff)