import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json, functools
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import tck_def_orm
from Common import base_win

def formatDay(day):
    if not day:
        return day
    if type(day) == int:
        return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
    if type(day) == str:
        if len(day) == 8:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
    return day

def _buildKey(data, kind, enableDays):
    if kind == None:
        kind = ''
    k = 'code' if 'code' in data else 'secu_code'
    if enableDays:
        key = f'{data[k]}:{kind}:{data["day"]}'
    else:
        key = f'{data[k]}:{kind}'
    return key

def mergeMarks(datas : list, kind, enableDays : bool):
    qr = tck_def_orm.Mark.select().where(tck_def_orm.Mark.kind == kind).dicts()
    marks = {}
    for d in qr:
        k = _buildKey(d, kind, enableDays)
        marks[k] = d
    for d in datas:
        k = _buildKey(d, kind, enableDays)
        if k not in marks:
            continue
        # check is mark end
        mk = marks[k]
        if mk['endDay'] and d.get('day', None) and d['day'] >= mk['endDay']:
            continue
        d['markColor'] = mk['markColor']
        d['markText'] = mk['markText']

MARK_END_VAL = -9999

def _markMenuItemRender(win, hdc, rect, item):
    BX = 8
    W, H = rect[2] - rect[0], rect[3] - rect[1]
    box = (rect[0], rect[1] + (H - BX) // 2, rect[0] + BX, rect[1] + (H - BX) // 2 + BX)
    color = markColor2RgbColor(item['markColor'])
    if color != None:
        win.drawer.fillRect(hdc, box, color)
    rect[0] += BX + 6
    txtColor = win.css['textColor'] if item.get('enable', True) else win.css['disableTextColor']
    win.drawer.drawText(hdc, item['title'], rect, txtColor, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_WORDBREAK)

def getMarkModel(enable):
    model = [
        {'name': 'mark_1', 'title': '标记紫色', 'enable': enable, 'markColor': 1, 'render': _markMenuItemRender},
        {'name': 'mark_2', 'title': '标记蓝色', 'enable': enable, 'markColor': 2, 'render': _markMenuItemRender},
        {'name': 'mark_3', 'title': '标记绿色', 'enable': enable, 'markColor': 4, 'render': _markMenuItemRender},
        {'name': 'mark_5', 'title': '标记橙色', 'enable': enable, 'markColor': 6, 'render': _markMenuItemRender},
        {'name': 'mark_4', 'title': '标记红色', 'enable': enable, 'markColor': 7, 'render': _markMenuItemRender},
        {'name': 'mark_5', 'title': '标记黄色', 'enable': enable, 'markColor': 5, 'render': _markMenuItemRender},
        {'name': 'mark_3', 'title': '标记青色', 'enable': enable, 'markColor': 3, 'render': _markMenuItemRender},
        {'title': 'LINE'},
        {'name': 'mark_6', 'title': '取消记标', 'enable': enable, 'markColor': 0},
        {'name': 'mark_end', 'title': '终止标记', 'enable': enable, 'markColor': MARK_END_VAL}
    ]
    return model

def markColor2RgbColor(markColor):
    if not markColor:
        return None
    #CS = (0xCC3299, 0xCD0000, 0x008800, 0x3333FF, 0x1E69D2)
    CS = (0xFF007F, 0xff0000, 0xcccc00, 0x00cc00, 0x00CCCC, 0x0066CC, 0x0000ff)
    if markColor >= 1 and markColor <= len(CS):
        return CS[markColor - 1]
    return None

def markColorTextRender(win, hdc, row, col, colName, value, rowData, rect):
    color = win.css['textColor']
    mc = rowData.get('markColor', None)
    color = markColor2RgbColor(mc) or color
    align = win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE
    win.drawer.drawText(hdc, value, rect, color, align = align)

def sortMarkColor(colName, val, rowData, allDatas, asc):
    if val == None:
        return 9999999 if asc else 0
    return val

def markColorBoxRender(win, hdc, row, col, colName, value, rowData, rect):
    if value == None:
        return
    color = markColor2RgbColor(abs(value))
    if color == None:
        return
    x, y, w, h = rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1]
    SZ = 10
    x += (w - SZ) // 2
    y += (h - SZ) // 2
    if value > 0:
        win.drawer.fillRect(hdc, (x, y, x + SZ, y + SZ), color)
    else:
        win.drawer.drawRect(hdc, (x, y, x + SZ, y + SZ), color)

# keys = {'kind' : xx, 'code': xx, 'day': xx, ....}
# kwargs: endDay = ... (only used for mark end day)
def saveOneMarkColor( keyVals, markColor, **kwargs):
    if markColor < 0 and markColor != MARK_END_VAL:
        return
    cnd = None
    for k in keyVals:
        cndx = getattr(tck_def_orm.Mark, k) == keyVals[k]
        if not cnd: cnd = cndx
        else: cnd = cnd & cndx
    cnd = cnd & (tck_def_orm.Mark.markColor > 0)

    # save end mark day
    if markColor == MARK_END_VAL:
        cnd = cnd & (tck_def_orm.Mark.endDay.is_null(True) | tck_def_orm.Mark.endDay < kwargs['endDay'])
        obj = tck_def_orm.Mark.get_or_none(cnd)
        if obj:
            obj.endDay = kwargs['endDay']
            obj.save()
        return
    
    mps = {}
    mps.update(keyVals)
    mps['markColor'] = markColor
    if 'name' in kwargs:
        mps['name'] = kwargs['name']
    obj : tck_def_orm.Mark = tck_def_orm.Mark.get_or_none(cnd)
    if not obj:
        if markColor == 0:
            return None
        return tck_def_orm.Mark.create(**mps)
    else:
        if markColor == 0: # delete
            obj.delete_instance()
            return None
        else:
            for k in mps:
                setattr(obj, k, mps[k])
            obj.save()
            return obj