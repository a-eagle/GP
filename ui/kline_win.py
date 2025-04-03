import os, sys, functools, copy, datetime, json, time, traceback
import win32gui, win32con
import requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import speed_orm, ths_orm, tdx_orm, tck_orm, tck_def_orm, lhb_orm, cls_orm
from Download import datafile
from Download import henxin, cls
from Common import base_win, ext_win, dialog
from THS import hot_utils
from ui.kline_indicator import *

class KLineWindow(base_win.BaseWindow):
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70

    def __init__(self):
        super().__init__()
        self.klineWidth = 8 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.markDays = {} # int items
        self.indicators = []
        self.mouseXY = None
        self.selIdx = -1
        self.selIdxOnClick = False

        self.refIndicator = KLineIndicator(self, {'height': -1, 'margins': (30, 20)})
        self.klineIndicator = KLineIndicator(self, {'height': -1, 'margins': (30, 20)})
        self.indicators.append(self.klineIndicator)
        # self.lineMgr = DrawLineManager(self)
        from THS import tips_win
        self.hygnWin = tips_win.BkGnWindow()

    def addIndicator(self, indicator : Indicator):
        self.indicators.append(indicator)
        self.calcIndicatorsRect()

    # indicator = 'rate' | 'amount'
    # def addDefaultIndicator(self, name):
        # if 'rate' in name:
        #     idt = RateIndicator({'height': 60, 'margins': (15, 2)})
        #     self.indicators.append(idt)
        #     idt.init(self)
        # if 'amount' in name:
        #     idt = AmountIndicator({'height': 60, 'margins': (15, 2)})
        #     self.indicators.append(idt)
        #     idt.init(self)
        # self.calcIndicatorsRect()

    def clearMarkDay(self):
        self.markDays.clear()

    def setMarkDay(self, day, tip = None):
        if type(day) == str:
            day = int(day.replace('-', ''))
        elif isinstance(day, datetime.date):
            dd : datetime.date = day
            day = dd.year * 10000 + dd.month * 100 + dd.day
        if type(day) != int:
            return
        if day not in self.markDays:
            self.markDays[day] = {'day': day, 'tip': tip}
        else:
            self.markDays[day]['tip'] = tip

    def removeMarkDay(self, day):
        if type(day) == str:
            day = int(day.replace('-', ''))
        if type(day) == int and day in self.markDays:
            self.markDays.pop(day)

    def calcIndicatorsRect(self):
        if not self.hwnd:
            return
        w, h = self.getClientSize()
        fixHeight = 0
        for i in range(0, len(self.indicators)):
            cf : Indicator = self.indicators[i]
            fixHeight += cf.getMargins(0) + cf.getMargins(1)
            if cf.config['height'] >= 0:
                fixHeight += cf.config['height']
        exHeight = max(h - fixHeight, 0)
        y = 0
        for i in range(0, len(self.indicators)):
            cf = self.indicators[i]
            cf.x = self.LEFT_MARGIN
            y = y + cf.getMargins(0)
            cf.y = y
            cf.width = w - self.RIGHT_MARGIN - cf.x
            if cf.config['height'] < 0:
                cf.height = exHeight
            else:
                cf.height = cf.config['height']
            y += cf.height + cf.getMargins(1)

    # def getRectByIndicator(self, indicatorOrIdx):
    #     if type(indicatorOrIdx) == int:
    #         idx = indicatorOrIdx
    #     elif isinstance(indicatorOrIdx, Indicator):
    #         for i in range(0, len(self.indicators)):
    #             if self.indicators[i] == indicatorOrIdx:
    #                 idx = i
    #                 break
    #     if idx < 0 or idx >= len(self.indicators):
    #         return None
    #     idt = self.indicators[idx]
    #     return [idt.x, idt.y, idt.width, idt.height]
    
    def isPointInIndicator(self, x, y, indicator):
        return (x >= indicator.x and x < indicator.x + indicator.width and
                y >= indicator.y and y < indicator.y + indicator.height)

    def getIndicatorByPoint(self, x, y):
        for it in self.indicators:
            if self.isPointInIndicator(x, y, it):
                return it
        return None

    def changeCode(self, code, period):
        if type(code) == int:
            code = f'{code :06d}'
        if len(code) == 8 and code[0] == 's':
            code = code[2 : ]
        for it in self.indicators:
            it.changeCode(code, period)
        self.makeVisible(-1)
        self.invalidWindow()

    # def setModel(self, model):
    #     self.selIdx = -1
    #     self.dateType = 'day'
    #     self.model = model
    #     self.hygn = None
    #     if not model:
    #         for idt in self.indicators:
    #             idt.setData(None)
    #         return
    #     self.model.calcAttrs()
    #     gntcObj = ths_orm.THS_GNTC.get_or_none(code = str(self.model.code))
    #     self.model.hy = []
    #     self.model.gn = []
    #     if gntcObj and gntcObj.hy:
    #         self.model.hy = gntcObj.hy.split('-')
    #         if len(self.model.hy) == 3:
    #             del self.model.hy[0]
    #     if gntcObj and gntcObj.hy:
    #         self.model.gn = gntcObj.gn.replace('【', '').replace('】', '').split(';')
    #     for idt in self.indicators:
    #         idt.setData(self.model.data)
    #     self.lineMgr.load(model.code)
    #     self.hygnWin.changeCode(self.model.code)

    # dateType = 'day' 'week'  'month'
    # def changeDateType(self, dateType):
    #     if self.dateType == dateType:
    #         return
    #     self.dateType = dateType
    #     self.model.changeDateType(dateType)
    #     md = self.model
    #     for idt in self.indicators:
    #         idt.setData(md.data)
    #         idt.changeDateType(dateType)
    #     self.makeVisible(-1)
    #     self.selIdx = len(md.data) - 1
    #     x = self.klineIndicator.getCenterX(self.selIdx)
    #     if self.mouseXY:
    #         self.mouseXY = (x, self.mouseXY[1])
    #     self.invalidWindow()

    def onContextMenu(self, x, y):
        it = self.getIndicatorByPoint(x, y)
        if it and it.onContextMenu(x - it.x, y - it.y):
            return
        # default deal
        selDay = 0
        # if self.selIdx >= 0:
            # selDay = self.model.data[self.selIdx].day
            # if isinstance(selDay, str):
            #     selDay = selDay.replace('-', '')
            #     selDay = int(selDay)
        mm = [
              {'title': '点击时选中K线', 'name': 'sel-idx-on-click', 'checked': self.selIdxOnClick},
              {'title': '显示叠加指数', 'name': 'show-ref-zs', 'checked': getattr(self.refIndicator, 'visible', True)},
              {'title': '叠加指数 THS', 'name': 'add-ref-zs', 'sub-menu': self.getRefZsModel},
              {'title': '打开指数 THS', 'name': 'open-ref-zs', 'sub-menu': self.getRefZsModel},
              {'title': '叠加指数 CLS', 'name': 'add-ref-zs', 'sub-menu': self.getRefZsClsModel},
              {'title': '打开板块 CLS', 'name': 'add-ref-zs', 'sub-menu': self.getRefZsClsModel},
              {'title': 'LINE'},
              {'title': '标记日期', 'name': 'mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': '- 取消标记日期', 'name': 'cancel-mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': 'LINE'},
              {'title': '画线(直线)', 'name': 'draw-line'},
              {'title': '画线(文本)', 'name': 'draw-text'},
              {'title': '- 删除画线', 'name': 'del-draw-line'},
                #   {'title': '加自选', 'name':'JZX', 'sub-menu': zx},
                #   {'title': '- 删自选', 'name':'SZX', 'sub-menu': zx}
              ]
        menu = base_win.PopupMenu.create(self.hwnd, mm)
        x, y = win32gui.GetCursorPos()
        def onMM(evt, args):
            name = evt.item['name']
            if name == 'sel-idx-on-click':
                self.selIdxOnClick = not self.selIdxOnClick
            elif name in ('day', 'week', 'month'):
                self.changeDateType(name)
            elif name == 'mark-day':
                #base_win.ThsShareMemory.instance().writeMarkDay(selDay)
                self.setMarkDay(selDay)
                self.invalidWindow()
            elif name == 'cancel-mark-day':
                #base_win.ThsShareMemory.instance().writeMarkDay(0)
                self.removeMarkDay(selDay)
                self.invalidWindow()
            elif name == 'show-ref-zs':
                self.klineIndicator.visibleRefZS = evt.item['checked']
                self.invalidWindow()
            elif name == 'open-ref-zs':
                from Tck import kline_utils
                dt = {'code': evt.item['code'], 'day': None}
                kline_utils.openInCurWindow_ZS(self, dt)
            elif name == 'add-ref-zs':
                code = evt.item['code']
                refZSDrawer = self.klineIndicator.refZSDrawer
                refZSDrawer.updateRefZsData(code)
                refZSDrawer.changeDateType(self.dateType)
                self.makeVisible(-1)
                self.invalidWindow()
            elif name == 'draw-line':
                self.lineMgr.begin(self.dateType, 'line')
            elif name == 'draw-text':
                self.lineMgr.begin(self.dateType, 'text')
            elif name == 'del-draw-line':
                #qr = tck_orm.DrawLine.select().where(tck_orm.DrawLine.day == str(selDay))
                tck_def_orm.DrawLine.delete().where(tck_def_orm.DrawLine.day == str(selDay)).execute()
                self.lineMgr.reload()
                self.invalidWindow()
            elif name == 'JZX':
                if not self.model.name:
                    obj = ths_orm.THS_GNTC.get_or_none(code = self.model.code)
                    if obj:
                        self.model.name = obj.name
                tck_def_orm.MyObserve.get_or_create(code = self.model.code, name = self.model.name, kind = evt.item['kind'])
            elif name == 'SZX':
                tck_def_orm.MyObserve.delete().where((tck_def_orm.MyObserve.code == self.model.code) & (tck_def_orm.MyObserve.kind == evt.item['kind']))
            elif name == 'zt-reason':
                base_win.ThsShareMemory.instance().writeMarkDay(selDay)
                evt = self.Event('zt-reason', self, code = self.model.code, day = selDay)
                self.notifyListener(evt)
            elif name == 'zs-liandong':
                from Tck import top_real_zs, utils
                win = top_real_zs.ZS_Window()
                rc = win32gui.GetWindowRect(self.hwnd)
                W, H = rc[2] - rc[0], rc[3] - rc[1]
                win.createWindow(self.hwnd, (rc[0], rc[1], W, H), win32con.WS_POPUPWINDOW | win32con.WS_CAPTION | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX)
                win.datePicker.setSelDay(evt.item['day'])
                if not self.model.name:
                    obj = utils.get_THS_GNTC(self.model.code)
                    if obj: self.model.name = obj['name'] or ''
                win.editorWin.setText(self.model.code + ' | ' + self.model.name)
                w, h = win.getClientSize()
                win.layout.resize(0, 0, w, h)
                win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
                win.runTask()
        menu.addNamedListener('Select', onMM)
        menu.show(x, y)

    def getRefZsModel(self, item):
        code = self.model.code
        obj : ths_orm.THS_GNTC = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        model = []
        if not obj:
            return model
        model.append({'title': '上证指数', 'code': 'sh000001'})
        if obj.hy_2_code: model.append({'title': obj.hy_2_name, 'code': obj.hy_2_code})
        if obj.hy_3_code: model.append({'title': obj.hy_3_name, 'code': obj.hy_3_code})
        model.append({'title': 'LINE'})
        if not obj.gn_code:
            return model
        gn_codes = obj.gn_code.split(';')
        gn_names = obj.gn.split(';')
        for i in range(len(gn_codes)):
            if gn_codes[i].strip():
                model.append({'title': gn_names[i], 'code': gn_codes[i].strip()})
        return model
    
    def getRefZsClsModel(self, item):
        model = []
        code = self.model.code
        obj : cls_orm.CLS_GNTC = cls_orm.CLS_GNTC.get_or_none(cls_orm.CLS_GNTC.code == code)
        if not obj:
            return model
        if obj.hy and obj.hy_code:
            hys = zip(obj.hy.split(';'), obj.hy_code.split(';'))
            for hy in hys:
                if hy[0].strip() and hy[1].strip():
                    model.append({'title': hy[0], 'code': hy[1].strip()})
        model.append({'title': 'LINE'})
        if obj.gn and obj.gn_code:
            gns = zip(obj.gn.split(';'), obj.gn_code.split(';'))
            for gn in gns:
                if gn[0].strip() and gn[1].strip():
                    model.append({'title': gn[0], 'code': gn[1].strip()})
        return model

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.calcIndicatorsRect()
        self.hygnWin.DEF_COLOR = 0x22cc22

    def onSize(self):
        self.makeVisible(self.selIdx)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        # if self.lineMgr.winProc(hwnd, msg, wParam, lParam):
            # return True
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.onSize()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            self.onMouseMove(lParam & 0xffff, (lParam >> 16) & 0xffff)
            # self.notifyListener(self.Event('MouseMove', self, x = lParam & 0xffff, y = (lParam >> 16) & 0xffff))
            return True
        if msg == win32con.WM_KEYDOWN:
            keyCode = lParam >> 16 & 0xff
            self.onKeyDown(keyCode)
            # self.notifyListener(self.Event('KeyDown', self, keyCode = keyCode))
            return True
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onMouseClick(x, y)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            #x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            # si = self.selIdx
            # if si >= 0:
                # self.notifyListener(self.Event('DbClick', self, idx = si, data = self.model.data[si], code = self.model.code))
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onContextMenu(x, y)
            return True
        if msg == win32con.WM_MOUSELEAVE:
            self.onMouseLeave()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

    def updateAttr(self, attrName, attrVal):
        if not self.model:
            return
        if attrName == 'selIdx' and self.selIdx != attrVal:
            self.selIdx = attrVal
            data = self.model.data[attrVal] if attrVal >= 0 else None
            self.notifyListener(self.Event('selIdx.changed', self, selIdx = attrVal, data = data))
            self.hygnWin.changeLastDay(data.day)
            win32gui.InvalidateRect(self.hwnd, None, True)
    
    def acceptMouseMove(self, x, y, it : Indicator):
        isInRect = x >= it.x and y >= it.y and x < it.x + it.width and y < it.y + it.height
        if not isInRect:
            return False
        # if isinstance(it, KLineIndicator) or isinstance(it, RateIndicator) or isinstance(it, AmountIndicator):
            # return True
        return False

    def onMouseMove(self, x, y):
        it = self.getIndicatorByPoint(x, y)
        if not it:
            self.mouseXY = None
            self.invalidWindow()
            return
        it.onMouseMove(x, y)

    def onMouseLeave(self):
        for it in self.indicators:
            it.onMouseLeave()
        self.invalidWindow()

        # si = self.klineIndicator.getIdxAtX(x)
        # if si < 0:
        #     self.mouseXY = None
        #     if lmxy != self.mouseXY:
        #         self.invalidWindow()
        #     return
        # x = self.klineIndicator.getCenterX(si)
        # if x < 0:
        #     self.mouseXY = None
        #     if lmxy != self.mouseXY:
        #         self.invalidWindow()
        #     return
        # self.mouseXY = (x, y)
        # # if not self.selIdxOnClick:
        # #     if self.selIdx == si and lmxy and y == lmxy[1]:
        # #         return
        # #     self.updateAttr('selIdx', si)
        # if lmxy != self.mouseXY:
        #     self.invalidWindow()

    def onMouseClick(self, x, y):
        hygnRect = getattr(self.hygnWin, 'rect', None)
        if hygnRect and x >= hygnRect[0] and x < hygnRect[2] and y >= hygnRect[1] and y < hygnRect[3]:
            self.hygnWin.hwnd = self.hwnd
            self.hygnWin.onClick(x, y)
            return
        
        it = self.getIndicatorByPoint(x, y)
        if it:
            it.onMouseClick(x - it.x, y - it.y)

    def setSelIdx(self, idx):
        if self.selIdx == idx:
            return
        if (idx < 0):
            self.selIdx = -1
            return
        idt = self.klineIndicator
        if not idt.visibleRange or idx < idt.visibleRange[0] or idx >= idt.visibleRange[1]:
            return
        self.selIdx = idx
        item = idt.getItemData(idx)
        if not item:
            return
        self.notifyListener(Listener.Event('selIdx-Changed', self, idx = idx, day = item.day))
        self.invalidWindow()

    def onKeyDown(self, keyCode):
        if keyCode == 73: # page up
            pass
        elif keyCode == 81: # page down
            pass
        elif keyCode == 75: # left arrow key
            ni = self.selIdx - 1
            self.setSelIdx(ni)
        elif keyCode == 77: # right arrow key
            ni = self.selIdx + 1
            self.setSelIdx(ni)
        elif keyCode == 72: # up arrow key
            self.klineWidth += 2
            if self.klineWidth // 2 > self.klineSpace:
                self.klineSpace = min(self.klineSpace + 1, 2)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 80: # down arrow key
            self.klineWidth = max(self.klineWidth - 2, 1)
            if self.klineWidth // 2 < self.klineSpace:
                self.klineSpace = max(self.klineSpace - 1, 0)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 28:
            ks = ('day', 'week', 'month')
            idx = (ks.index(self.klineIndicator.period) + 1) % len(ks)
            self.changeCode(ks[idx])

    def makeVisible(self, idx):
        self.calcIndicatorsRect()
        idt : Indicator = None
        for idt in self.indicators:
            idt.calcVisibleRange(idx)
            vr = idt.visibleRange
            if vr:
                idt.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        # TODO: draw ref zs

        # draw background
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.drawBackground(hdc, self.drawer)
            y = idt.height + idt.getMargins(1)
            pw = 2 if i == 0 else 1
            self.drawer.drawLine(hdc, 0, y, w, y, 0x0000aa, width = pw)
            win32gui.RestoreDC(hdc, sdc)

        # draw Hilights
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.drawIdxHilight(hdc, self.drawer, self.selIdx)
            y = idt.height + idt.getMargins(1)
            win32gui.RestoreDC(hdc, sdc)

        # draw content
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.draw(hdc, self.drawer)
            y = idt.height + idt.getMargins(1)
            pw = 2 if i == 0 else 1
            win32gui.RestoreDC(hdc, sdc)

        # draw mouse
        if self.mouseXY:
            mx, my = self.mouseXY
            idt = self.getIndicatorByPoint(*self.mouseXY)
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.drawMouse(hdc, self.drawer, mx - idt.x, my - idt.y)
            win32gui.RestoreDC(hdc, sdc)

        self.drawer.drawLine(hdc, w - self.RIGHT_MARGIN + 10, 0, w - self.RIGHT_MARGIN + 10, h, 0x0000aa)

        # if self.selIdx > 0 and self.model and self.selIdx < len(self.model.data):
        #     cur = self.model.data[self.selIdx]
        #     pre = self.model.data[self.selIdx - 1]
        #     lb = cur.amount / pre.amount # 量比
        #     rc = (0, 0, cf.width, 20)
        #     self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
        #     zf = cf.refZSDrawer.getZhangFu(cur.day)
        #     if zf is None:
        #         zf = '--'
        #     else:
        #         zf = f'{zf :+.02f}%'
        #     title = f'指数({zf}) 同比({lb :.1f})'
        #     self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_RIGHT)

        # self.lineMgr.onDraw(hdc)

    def onDestory(self):
        pass

    def drawMouse(self, hdc):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        w, h = self.getClientSize()
        for it in self.indicators:
            # if isinstance(it, CustomIndicator):
                # h = it.y - 2
                break
        wp = win32gui.CreatePen(win32con.PS_DOT, 1, 0xffffff)
        win32gui.SelectObject(hdc, wp)
        win32gui.MoveToEx(hdc, self.LEFT_MARGIN, y)
        win32gui.LineTo(hdc, w, y)
        #win32gui.MoveToEx(hdc, x, self.klineIndicator.getMargins(1))
        #win32gui.LineTo(hdc, x, h)
        win32gui.DeleteObject(wp)


if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    win = KLineWindow()
    win.addIndicator(RateIndicator(win, {'height': 60, 'margins': (15, 2)}))
    win.addIndicator(AmountIndicator(win, {'height': 60, 'margins': (10, 2)}))
    win.addIndicator(DayIndicator(win))
    win.addIndicator(ScqxIndicator(win))
    win.addIndicator(LsAmountIndicator(win))
    win.addIndicator(HotIndicator(win))
    win.addIndicator(ThsZT_Indicator(win))
    win.addIndicator(ClsZT_Indicator(win))

    win.addIndicator(GnLdIndicator(win))
    win.addIndicator(ZhangSuIndicator(win))
    win.addIndicator(LhbIndicator(win))

    win.createWindow(None, (0, 0, 1500, 800), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)

    win.changeCode('002261', 'day') # 000737
    win32gui.PumpMessages()