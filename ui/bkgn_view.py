import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, threading, copy, traceback
import sys, pyautogui
import peewee as pw
import types

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import datafile, henxin, cls, ths_iwencai
from utils import hot_utils
from ui import dialog, base_win, kline_utils
from orm import d_orm, def_orm, ths_orm, cls_orm

class TextRender(base_win.RichTextRender):
    def __init__(self, win, lineHeight = 20) -> None:
        super().__init__(lineHeight)
        self.win = win

    def drawItem(self, drawer, hdc, rc, item):
        super().drawItem(drawer, hdc, rc, item)
        if not self.win.curClsHotGns:
            return
        args = self._getAttr(item, 'args')
        if not args:
            return
        num, gn = args['num'], args['gn']
        if gn not in self.win.curClsHotGns:
            return
        cur = self.win.curClsHotGns[gn]
        y = rc[1] + (rc[3] - rc[1] - self._getAttr(item, 'fontSize')) // 2 + self._getAttr(item, 'fontSize') + 2
        if cur['up'] > 0:
            drawer.drawLine(hdc, rc[0], y, rc[2], y, color = 0x0000ff, width = cur['up'])
            y += cur['up']
        if cur['down'] > 0:
            drawer.drawLine(hdc, rc[0], y, rc[2], y, color = 0xff0000, width = cur['down'])

class HotTcView(base_win.NoActivePopupWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['fontSize'] = 12
        self.css['bgColor'] = 0xfcfcfc
        self.datas = None
    
    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP, className='STATIC', title=''):
        IW = 30
        LL = 10
        if self.datas:
            LL = len(self.datas)
        W = max(LL * IW, 200)
        rect = (0, 0, W, 200)
        super().createWindow(parentWnd, rect, style, className, title)

    def loadData_2(self, endDay, daysNum, tcName):
        tradeDays = []
        qr = cls_orm.CLS_HotTc.select(cls_orm.CLS_HotTc.day.distinct()).where(cls_orm.CLS_HotTc.day <= endDay).order_by(cls_orm.CLS_HotTc.day.desc()).tuples()
        for it in qr:
            tradeDays.append(it[0])
            if len(tradeDays) >= daysNum:
                break
        fromDay = tradeDays[-1]
        self.loadData(fromDay, endDay, tcName)

    def loadData(self, fromDay, endDay, tcName):
        tradeDays = []
        qr = cls_orm.CLS_HotTc.select(cls_orm.CLS_HotTc.day.distinct()).where(cls_orm.CLS_HotTc.day >= fromDay, cls_orm.CLS_HotTc.day <= endDay).order_by(cls_orm.CLS_HotTc.day.asc()).tuples()
        for it in qr:
            tradeDays.append(it[0])
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.name == tcName, cls_orm.CLS_HotTc.day >= fromDay, cls_orm.CLS_HotTc.day <= endDay)
        model = []
        for it in qr:
            model.append(it)
        datas = []
        for i, d in enumerate(tradeDays):
            td = {'day': d, 'up': [], 'down': [], 'sumUpNum': 0, 'sumDownNum': 0}
            datas.append(td)
            for m in model:
                if m.day == d:
                    if m.up: td['up'].append(m)
                    else: td['down'].append(m)
            td['sumUpNum'] = len(td['up'])
            td['sumDownNum'] = len(td['down'])
            if i > 0:
                td['sumUpNum'] += datas[i - 1]['sumUpNum']
                td['sumDownNum'] += datas[i - 1]['sumDownNum']
        self.datas = datas
    
    def onDraw(self, hdc):
        if not self.datas or len(self.datas) == 1:
            return
        MAX_NUM = max(self.datas[-1]['sumUpNum'], self.datas[-1]['sumDownNum'])
        STEP_VAL = 2 if MAX_NUM > 8 else 1
        STEP_NUM = max((MAX_NUM + STEP_VAL - 1) // STEP_VAL, 4)
        LEFT_X, RIGHT_X = 30, 20
        TOP_Y, BOTTOM_Y = 20, 30
        W, H = self.getClientSize()
        STEP_Y = (H - TOP_Y - BOTTOM_Y) / STEP_NUM
        STEP_X = (W - LEFT_X - RIGHT_X) / (len(self.datas) - 1)

        LINE_COLOR, TXT_COLOR, TXT_COLOR_HILIGHT  = 0xE2E2E2, 0x777777, 0xFF007F
        # vertical line
        for i in range(len(self.datas)):
            sx = int(LEFT_X + i * STEP_X)
            ey = H - BOTTOM_Y + 5
            lc = LINE_COLOR
            if i != 0 and i % 5 == 0:
                lc = 0xff0000
            self.drawer.drawLine(hdc, sx, TOP_Y, sx, ey, lc)
            if i % 5 == 0:
                day = self.datas[i]['day'][5 : ]
                c = TXT_COLOR_HILIGHT
            else:
                day = self.datas[i]['day'][-2 : ]
                c = TXT_COLOR
            self.drawer.drawText(hdc, day.replace('-', '/'), (sx - 30, ey + 5, sx + 30, ey + 20), c)
        # horizontal line
        for i in range(STEP_NUM + 1):
            sy = int(H - BOTTOM_Y - STEP_Y * i)
            self.drawer.drawLine(hdc, LEFT_X - 5, sy, W - RIGHT_X, sy, LINE_COLOR)
            val = str(i * STEP_VAL)
            rc = (0, sy - 10, LEFT_X - 10, sy + 10)
            if STEP_NUM < 10 or i % 2 == 0:
                self.drawer.drawText(hdc, val, rc, TXT_COLOR, win32con.DT_RIGHT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        
        RED, GREEN, GRAY = 0x3333ff, 0x33ff33, 0xCACACA
        # draw up datas
        for i, dt in enumerate(self.datas):
            sx = int(LEFT_X + i * STEP_X)
            sy = int(H - BOTTOM_Y - dt['sumUpNum'] / STEP_VAL * STEP_Y)
            self.drawer.fillRect(hdc, (sx - 3, sy - 3, sx + 3, sy + 3), RED)
            if i != len(self.datas) - 1: # not last
                nsx = int(LEFT_X + (i + 1) * STEP_X)
                nsy = int(H - BOTTOM_Y - self.datas[i + 1]['sumUpNum'] / STEP_VAL * STEP_Y)
                if dt['sumUpNum'] != self.datas[i + 1]['sumUpNum']:
                    self.drawer.drawLine(hdc, sx, sy, nsx, nsy, RED, style = win32con.PS_SOLID, width = 2)
                else:
                    self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GRAY, style = win32con.PS_DOT, width = 1)

            sy = int(H - BOTTOM_Y - dt['sumDownNum'] / STEP_VAL * STEP_Y)
            self.drawer.fillRect(hdc, (sx - 3, sy - 3, sx + 3, sy + 3), GREEN)
            if i != len(self.datas) - 1: # not last
                nsx = int(LEFT_X + (i + 1) * STEP_X)
                nsy = int(H - BOTTOM_Y - self.datas[i + 1]['sumDownNum'] / STEP_VAL * STEP_Y)
                if dt['sumDownNum'] != self.datas[i + 1]['sumDownNum']:
                    self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GREEN, style = win32con.PS_SOLID, width = 2)
                else:
                    self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GRAY, style = win32con.PS_DOT, width = 1)

    # x, y is screen pos
    def show(self, x, y):
        rc = win32gui.GetWindowRect(self.hwnd)
        W, H = rc[2] - rc[0], rc[3] - rc[1]
        SW, SH = win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN) - 40
        if x + W > SW: x = SW - W
        if y + H > SH: y = SH - H
        super().show(x, y)

class BkGnView:
    def __init__(self) -> None:
        super().__init__()
        self.DEF_COLOR = 0xa0a0a0
        self.HOT_DEF_COLOR = 0xff3399
        self.HOT_CLS_COLOR = 0x14698B
        self.hwnd = None
        self.curCode = None
        self.hotGnObj = None
        self.thsGntc = None
        self.clsGntc = None
        self.defHotGns = []
        self.clsHotGns = []
        self.curClsHotGns = None
        self.limitDaysNum = self._getLimitDaysNum()
        self.lastDay = None
        self.hotDaysRange = None
        self.richRender = TextRender(self, 17)

    def onClick(self, x, y):
        sp = None
        for it in self.richRender.specs:
            rc = it.get('rect', None)
            if not rc: break
            if x >= rc[0] and x < rc[2] and y >= rc[1] and y < rc[3]:
                sp = it
                break
        if not sp or not sp['args']:
            return
        gnNum, gn = sp['args']['num'], sp['args']['gn']
        if gnNum <= 0:
            return
        if not self.hotDaysRange:
            return
        tcView = HotTcView()
        #tcView.loadData(*self.hotDaysRange, gn)
        TRADE_DAYS_NUM = 20
        tcView.loadData_2(self.hotDaysRange[1], TRADE_DAYS_NUM, gn)
        tcView.createWindow(self.hwnd)
        tcView.show(*win32gui.GetCursorPos())
        tcView.msgLoop()
    
    def _getLimitDaysNum(self):
        obj, _ = def_orm.MySettings.get_or_create(mainKey = 'HotTc_N_Days')
        if not obj.val:
            obj.val = '5'
            obj.save()
        return int(obj.val)

    def onShowSettings(self):
        model = [{'title': '设置热点概念', 'name': 'hot'},
                 {'title': '设置热点概念-5日', 'name': 'HotTc_5', 'checked': self.limitDaysNum == 5},
                 {'title': '设置热点概念-10日', 'name': 'HotTc_10', 'checked': self.limitDaysNum == 10}
                ]
        menu = base_win.PopupMenu.create(self.hwnd, model)
        menu.addNamedListener('Select', self.onSettings, self.hwnd)
        menu.show(*win32gui.GetCursorPos())

    def onSettings(self, evt, args):
        if evt.item['name'] == 'hot':
            dlg = dialog.MultiInputDialog()
            dlg.setText(self.hotGnObj.info or '')
            prc = win32gui.GetWindowRect(self.hwnd)
            def onInputEnd(evt, args):
                if not evt.ok:
                    return
                self.saveDefHotGn(evt.text)
                self._buildBkgn()
                win32gui.InvalidateRect(self.hwnd, None, False)
            dlg.addNamedListener('InputEnd', onInputEnd)
            dlg.createWindow(self.hwnd, (prc[0], prc[1], 450, 200), title = '设置热点概念') # GetParent(self.hwnd)
            dlg.showCenter()
        elif 'HotTc_' in evt.item['name']:
            ndays = int(evt.item['name'][len('HotTc_') : ])
            if self.limitDaysNum == ndays:
                return
            self.limitDaysNum = ndays
            obj, _ = def_orm.MySettings.get_or_create(mainKey = 'HotTc_N_Days')
            obj.val = str(self.limitDaysNum)
            obj.save()
            self.changeLimitDaysNum()

    def onDrawRect(self, hdc, rc):
        drawer = base_win.Drawer.instance()
        self.richRender.draw(hdc, drawer, (rc[0] + 3, rc[1] + 2, rc[2] - 3, rc[3]))

    def setLimitDaysNum(self, daysNum):
        self.limitDaysNum = daysNum

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.lastDay = None
        scode = f'{code :06d}' if type(code) == int else code
        if scode[0 : 2] in ('sz', 'sh'):
            scode = scode[2 : ]
        self.curCode = scode
        # load code info
        self._loadDefHotGn()
        self._loadThsClsTcgn()
        self._loadClsHotGn(None)
        self._buildBkgn()
        win32gui.InvalidateRect(self.hwnd, None, False)

    def changeLastDay(self, lastDay):
        if type(lastDay) == int:
            lastDay = str(lastDay)
        if type(lastDay) == str and len(lastDay) == 8:
            lastDay = lastDay[0 : 4] + '-' + lastDay[4 : 6] + '-' + lastDay[6 : 8]
        if self.lastDay == lastDay:
            return
        self.lastDay = lastDay
        self._loadClsHotGn(self.lastDay)
        self._buildBkgn()
        win32gui.InvalidateRect(self.hwnd, None, False)

    def changeLimitDaysNum(self):
        self._loadClsHotGn(self.lastDay)
        self._buildBkgn()
        win32gui.InvalidateRect(self.hwnd, None, False)

    def saveDefHotGn(self, txt):
        self.hotGnObj.info = txt or ''
        self.hotGnObj.save()

    def _loadDefHotGn(self):
        from orm import def_orm
        qr = def_orm.MyHotGn.select()
        self.hotGnObj = None
        self.defHotGns = []
        for obj in qr:
            self.hotGnObj = obj
            if obj.info:
                sx = obj.info.replace('\n', ' ').split(' ')
                for s in sx:
                    if s.strip(): self.defHotGns.append(s.strip())
            break
        if not self.hotGnObj:
            self.hotGnObj = def_orm.MyHotGn.create(info = '')

    # lastDay = None(newest day) | int | str
    # return [(cls-name, num), ...]
    def _loadClsHotGn(self, lastDay):
        self.hotDaysRange = None
        qr = cls_orm.CLS_HotTc.select(cls_orm.CLS_HotTc.day.distinct()).order_by(cls_orm.CLS_HotTc.day.desc()).tuples()
        # tdays = ths_iwencai.getTradeDays()
        days = []
        for it in qr:
            if (lastDay is None) or (it[0] <= lastDay):
                days.append(it[0])
            if len(days) >= self.limitDaysNum: # 仅显示近N天的热点概念
                break
        if not days:
            self.hotDaysRange = None
            self.clsHotGns = []
            return
        fromDay = days[-1]
        endDay = days[0]
        self.hotDaysRange = (fromDay, endDay)
        rs = []
        qr = cls_orm.CLS_HotTc.select(cls_orm.CLS_HotTc.name, pw.fn.count()).where(cls_orm.CLS_HotTc.day >= fromDay, cls_orm.CLS_HotTc.day <= endDay, cls_orm.CLS_HotTc.up == True).group_by(cls_orm.CLS_HotTc.name).tuples()
        for it in qr:
            clsName, num = it
            rs.append((clsName.strip(), num))
        self.clsHotGns = rs
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day == endDay).dicts()
        cr = {}
        for it in qr:
            k = it['name']
            if k not in cr:
                cr[k] = {'up': 0, 'down': 0, 'name': k}
            if it['up']: cr[k]['up'] += 1
            else:  cr[k]['down'] += 1
        self.curClsHotGns = cr

    def _loadThsClsTcgn(self):
        self.thsGntc = ths_orm.THS_GNTC.get_or_none(code = self.curCode) or ths_orm.THS_GNTC()
        self.clsGntc = cls_orm.CLS_GNTC.get_or_none(code = self.curCode) or cls_orm.CLS_GNTC()

    def _buildBkgn(self):
        self.richRender.specs.clear()
        defHotGns = self.defHotGns[ : ]
        clsHotGns = self.clsHotGns[ : ]
        hy1 = ''
        if self.thsGntc.hy_2_name: hy1 = self.thsGntc.hy_2_name + ';'
        if self.thsGntc.hy_3_name: hy1 += self.thsGntc.hy_3_name
        hys = self._buildBkInfos(hy1, self.clsGntc.hy, defHotGns, clsHotGns)
        self.richRender.addText(' 【', self.DEF_COLOR)
        for idx, h in enumerate(hys):
            if idx != 0:
                self.richRender.addText(' | ', self.DEF_COLOR)
            self.richRender.addText(h[1], h[2], args = {'num': h[3], 'gn': h[4]})
        self.richRender.addText('】 ', self.DEF_COLOR)
        
        lastGns = self._buildBkInfos(self.thsGntc.gn, self.clsGntc.gn, defHotGns, clsHotGns)
        lastGns.sort(key = lambda d: d[0])
        for i, h in enumerate(lastGns):
            self.richRender.addText(h[1], h[2], args = {'num': h[3], 'gn': h[4]})
            if i != len(lastGns) - 1:
                self.richRender.addText(' | ', self.DEF_COLOR)
        #for h in self.defHotGns:
        #    self.richRender.addText(h + ' ', 0x404040)

    # return (no, gn-name, color, num, org-gn-name)
    def _buildBkInfos(self, thsGn, clsGn, defHotGns, clsHotGns):
        thsGn = thsGn or ''
        clsGn = clsGn or '' 
        gns = [] # item of {gn: xx, type: xx, same:xx}
        gnsMap = {} # gn: obj
        for g in thsGn.split(';'):
            g = g.strip()
            if not g:
                continue
            item = {'gn': g, 'type': 'THS'}
            gns.append(item)
            gnsMap[g] = item
        for g in clsGn.split(';'):
            g = g.strip()
            if not g: 
                continue
            if g in gnsMap:
                item = gnsMap[g]
                item['type'] = 'THS+CLS'
            else:
                item = {'gn': g, 'type': 'CLS'}
                gns.append(item)
        lastGns = []
        for item in gns:
            if item['type'] == 'THS':
                info = self._getTypeNameAndColor_THS(item['gn'], True, defHotGns)
            elif item['type'] == 'CLS':
                info = self._getTypeNameAndColor_CLS(item['gn'], True, clsHotGns)
                info = info[0], '#' + info[1], info[2], info[3]
            else: # THS+CLS
                info1 = self._getTypeNameAndColor_THS(item['gn'], True, defHotGns)
                info2 = self._getTypeNameAndColor_CLS(item['gn'], True, clsHotGns)
                no = min(info1[0], info2[0])
                color = info1[2] if no == info1[0] else info2[2]
                info = (no, '*' + info2[1], color, info2[3])
            info = *info, item['gn']
            lastGns.append(info)
        return lastGns

    def _getTypeNameAndColor_THS(self, bk, remove, defHotGns):
        idx = self._getDefHotIndex(bk, defHotGns)
        if idx >= 0:
            if remove: defHotGns.pop(idx)
            return 20, bk, self.HOT_DEF_COLOR, 0
        return 1000, bk, self.DEF_COLOR, 0
    
    def _getTypeNameAndColor_CLS(self, bk, remove, clsHotGns):
        idx = self._getClsHotIndex(bk, clsHotGns)
        if idx >= 0:
            clsName, num = clsHotGns[idx]
            if remove:
                clsHotGns.pop(idx)
            name = f'{bk}（{num}）'
            return 100 - num, name, self.HOT_CLS_COLOR, num
        return 2000, bk, self.DEF_COLOR, 0

    def _getDefHotIndex(self, bk, defHotGns):
        for i, h in enumerate(defHotGns):
            if h == bk: # h in bk or bk in h
                return i
        return -1

    def _getClsHotIndex(self, bk, clsHotGns):
        for i, it in enumerate(clsHotGns):
            clsName, num = it
            if bk == clsName:
                return i
        return -1
    
    def removeDefHotGn(self, hotGns : list, gn):
        for i, h in enumerate(hotGns):
            if h in gn:
                hotGns.pop(i)

    def getHotBkGn(self):
        rs = []
        for it in self.richRender.specs:
            if it['args']:
                rs.append(it['args'])
        return rs