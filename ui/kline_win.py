import os, sys, functools, copy, datetime, json, time, traceback
import win32gui, win32con, win32api

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import def_orm
from ui import base_win, dialog
from utils import gn_utils
from ui.kline_indicator import *

class MarksMgr:
    def __init__(self, win) -> None:
        self.win = win
        self.data = {} # int items

    def clearMarkDay(self):
        self.data.clear()

    def setMarkDay(self, day, tip = None):
        if type(day) == str:
            day = int(day.replace('-', ''))
        elif isinstance(day, datetime.date):
            dd : datetime.date = day
            day = dd.year * 10000 + dd.month * 100 + dd.day
        if type(day) != int:
            return
        if day not in self.data:
            self.data[day] = {'day': day, 'tip': tip}
        else:
            self.data[day]['tip'] = tip

    def removeMarkDay(self, day):
        if type(day) == str:
            day = int(day.replace('-', ''))
        if type(day) == int and day in self.data:
            self.data.pop(day)

    def onDraw(self, hdc, drawer):
        kl = self.win.klineIndicator
        vr = kl.visibleRange
        if not vr or not kl.model:
            return
        for day in self.data:
            idx = kl.model.getItemIdx(day)
            if idx >= vr[0] and idx < vr[1]:
                kl.drawIdxHilight(hdc, drawer, idx)

class ContextMenuMgr:
    def __init__(self, win) -> None:
        self.win = win

    def getMenuModel(self):
        data = self.win.klineIndicator.data
        if not data or self.win.selIdx < 0:
            return None
        selDay = data[self.win.selIdx].day
        mm = [
              {'title': '点击时选中K线', 'name': 'sel-idx-on-click', 'checked': self.win.selIdxOnClick},
              {'title': '显示叠加指数', 'name': 'show-ref-zs', 'checked': self.win.refIndicatorVisible},
              {'title': '叠加指数 THS', 'name': 'add-ref-zs', 'sub-menu': self.getThsZsList},
            #   {'title': '打开指数 THS', 'name': 'open-ref-zs', 'sub-menu': self.getThsZsList},
              {'title': '叠加指数 CLS', 'name': 'add-ref-zs', 'sub-menu': self.getClsZsList},
              {'title': '打开板块 CLS', 'name': 'open-ref-clszs', 'sub-menu': self.getClsZsList},
              {'title': 'LINE'},
              {'title': '标记日期 +', 'name': 'mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': '标记日期 -', 'name': 'cancel-mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': 'LINE'},
              {'title': '画线(直线)', 'name': 'draw-line'},
              {'title': '画线(文本)', 'name': 'draw-text'},
              {'title': '删除直线', 'name': 'del-draw-line', 'day': selDay},
              ]
        return mm

    def getThsZsList(self, item):
        from orm import ths_orm
        code = self.win.klineIndicator.code
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
    
    def getClsZsList(self, item):
        from orm import cls_orm
        model = []
        code = self.win.klineIndicator.code
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

    def show(self, x, y):
        mm = self.getMenuModel()
        if not mm:
            return
        menu = base_win.PopupMenu.create(self.win.hwnd, mm)
        x, y = win32gui.GetCursorPos()
        menu.addNamedListener('Select', self.onMemuItem)
        menu.show(x, y)

    def onMemuItem(self, evt, args):
        name = evt.item['name']
        if name == 'sel-idx-on-click':
            self.win.selIdxOnClick = not self.win.selIdxOnClick
        elif name == 'mark-day':
            self.win.marksMgr.setMarkDay(evt.item['day'])
            self.win.invalidWindow()
        elif name == 'cancel-mark-day':
            self.win.marksMgr.removeMarkDay(evt.item['day'])
            self.win.invalidWindow()
        elif name == 'show-ref-zs':
            self.win.refIndicatorVisible = evt.item['checked']
            self.win.invalidWindow()
        elif name == 'open-ref-zs':
            from kline import kline_utils
            dt = {'code': evt.item['code'], 'day': None}
            kline_utils.openInCurWindow_ZS(self, dt)
        elif name == 'open-ref-clszs':
            code = evt.item['code']
            win32api.ShellExecute(None, 'open', f'https://www.cls.cn/plate?code={code}', '', '', True)
        elif name == 'add-ref-zs':
            code = evt.item['code']
            self.win.refIndicator.changeCode(code, self.win.refIndicator.period)
            self.win.invalidWindow()
        elif name == 'draw-line':
            self.win.lineMgr.beginNew('line')
            pass
        elif name == 'draw-text':
            self.win.lineMgr.beginNew('text')
            pass
        elif name == 'del-draw-line':
            self.win.lineMgr.delLine(evt.item['day'])
            pass

class TextLineManager:
    class Pos:
        def __init__(self, day = 0, dx = 0, price = 0, pos = None) -> None:
            self.day = day
            self.dx = dx
            self.price = price
            if pos:
                self.load(pos)

        def dump(self):
            obj = {'day': self.day, 'dx': self.dx, 'price': self.price}
            return json.dumps(obj)

        def load(self, txt):
            if not txt:
                return
            obj = json.loads(txt)
            for k in obj:
                setattr(self, k, obj[k])

        def isValid(self):
            return self.day > 0 and self.price > 0

        def __repr__(self) -> str:
            return self.dump()

    def __init__(self, win) -> None:
        self.win : KLineWindow = win
        self._reset()

    def _reset(self):
        self.code = None
        self.lines = []
        self.isDrawing = False
        self.curLine = None
        self.selLine = None

    def changeCode(self, code):
        self._reset()
        self.code = code
        q = def_orm.TextLine.select().where(def_orm.TextLine.code == code)
        for row in q:
            row.startPos = self.Pos(pos = row._startPos)
            row.endPos = self.Pos(pos = row._endPos)
            self.lines.append(row)
    
    def reload(self):
        if self.code:
            self.changeCode(self.code)

    # kind = 'text' | 'line'
    def beginNew(self, kind):
        self.isDrawing = True
        self.curLine = def_orm.TextLine(code = self.code, kind = kind)
        self.curLine.startPos = self.Pos()
        self.curLine.endPos = self.Pos()
    
    def delLine(self, day):
        for i in range(len(self.lines) - 1, -1, -1):
            d = self.lines[i]
            if d.kind == 'line' and d.endPos and d.endPos.day == day:
                item = self.lines.pop(i)
                item.delete_instance()
        self.win.invalidWindow()

    def delLine2(self, line):
        for i in range(len(self.lines)):
            if self.lines[i] == line:
                line.delete_instance()
                self.lines.pop(i)
                break
        self.win.invalidWindow()

    def isValidLine(self, line):
        return line.startPos.isValid() and line.endPos.isValid()

    def isValidText(self, line):
        return line.startPos.isValid() and line.info

    def end(self):
        if not self.isDrawing or not self.curLine:
            self.isDrawing = False
            self.curLine = None
            return
        self.isDrawing = False
        if self.curLine.kind == 'line' and self.isValidLine(self.curLine):
            oldId = self.curLine.id
            self.curLine._startPos = self.curLine.startPos.dump()
            self.curLine._endPos = self.curLine.endPos.dump()
            self.curLine.save()
            if not oldId: self.lines.append(self.curLine)
        elif self.curLine.kind == 'text' and self.isValidText(self.curLine):
            oldId = self.curLine.id
            self.curLine._startPos = self.curLine.startPos.dump()
            self.curLine.save()
            if not oldId: self.lines.append(self.curLine)
        self.curLine = None
    
    def cancel(self):
        self.isDrawing = False
        self.curLine = None

    def getXYByPos(self, pos):
        kl = self.win.klineIndicator
        vr = kl.visibleRange
        if not vr or not pos or not pos.isValid(): 
            return None
        idx = kl.model.getItemIdx(pos.day)
        if idx < vr[0] or idx >= vr[1]:
            return None
        x = kl.getCenterX(idx) + pos.dx
        if x < 0 or x > self.win.klineIndicator.width:
            return None
        y = kl.getYAtValue(pos.price)
        if y < 0 or y >= self.win.klineIndicator.height:
            return None
        return (x, y)

    def getPosByXY(self, x, y):
        kl = self.win.klineIndicator
        if not kl.visibleRange:
            return None
        idx = kl.getIdxAtX(x)
        if idx < 0:
            return None
        day = kl.data[idx].day
        cx = kl.getCenterX(idx)
        price = kl.getValueAtY(y)
        if not price:
            return None
        return self.Pos(day, x - cx, price['value'])

    def onDrawText(self, hdc, drawer, line):
        kl = self.win.klineIndicator
        vr = kl.visibleRange
        if not self.isValidText(line) or not vr:
            return
        size = drawer.calcTextSize(hdc, line.info)
        xy = self.getXYByPos(line.startPos)
        if not xy:
            return
        rc = (*xy, xy[0] + size[0], xy[1] + size[1])
        line.rect = rc
        drawer.drawText(hdc, line.info, rc, color = 0x404040, align = win32con.DT_LEFT)
        if line == self.selLine:
            drawer.drawRect(hdc, rc, 0x00a0a0)

    def onDrawLine(self, hdc, drawer, line):
        # print('[onDrawLine]', line, line.startPos, line.endPos)
        # W, H = self.win.getClientSize()
        kl = self.win.klineIndicator
        vr = kl.visibleRange
        if not self.isValidLine(line) or not vr:
            return
        sxy = self.getXYByPos(line.startPos)
        exy = self.getXYByPos(line.endPos)
        if not sxy or not exy:
            return
        drawer.drawLine(hdc, *sxy, *exy, 0x30f030, width = 1)
        self.drawLineArrow(hdc, drawer, *sxy, *exy)

    def drawLineArrow(self, hdc, drawer, sx, sy, ex, ey):
        if sx == ex and sy == ey:
            return
        if sx != ex:
            rc = (ex - 2, ey - 2, ex + 3, ey + 3)
            drawer.fillRect(hdc, rc, 0x30f030)
            return
        W, H = self.win.getClientSize()
        # draw vertical line arrow
        d = 1 if ey < sy else -1
        for n in range(4):
            for dx in range(-n, n + 1):
                x = sx + dx
                y = ey + n * d
                if x > 0 and y > 0 and x < W and y < H:
                    win32gui.SetPixel(hdc, x, y, 0x30f030)
    
    def onDraw(self, hdc):
        drawer = self.win.drawer
        for line in self.lines:
            if line.kind == 'text':
                self.onDrawText(hdc, drawer, line)
            elif line.kind == 'line':
                self.onDrawLine(hdc, drawer, line)
        if self.isDrawing and self.isValidLine(self.curLine):
            self.onDrawLine(hdc, drawer, self.curLine)

    def getTextByXY(self, x, y):
        for i in range(len(self.lines) - 1, -1, -1):
            rc = getattr(self.lines[i], 'rect', None)
            if rc and x >= rc[0] and x < rc[2] and y >= rc[1] and y < rc[3]:
                return self.lines[i]
        return None

    def onLButtonDown(self, x, y):
        if not self.curLine or not self.isDrawing:
            return False
        # print('onLButtonDown ', self.isDrawing, self.curLine.__data__)
        kl = self.win.klineIndicator
        if self.curLine.kind == 'line':
            pos = self.getPosByXY(x, y)
            if not pos:
                self.cancel()
                return False
            self.curLine.startPos = pos
            return True
        return False
    
    def onInputEnd(self, evt, args):
        if evt.ok:
            self.curLine.info = evt.text
            self.end()
        else:
            self.cancel()

    def onLButtonUp(self, x, y):
        #print('onLButtonUp ', self.isDrawing, self.curLine.__data__)
        if (not self.curLine) or (not self.isDrawing):
            old = self.selLine
            self.selLine = self.getTextByXY(x, y)
            if old != self.selLine:
                self.win.invalidWindow()
            return self.selLine != None
        kl = self.win.klineIndicator
        if self.curLine.kind == 'line':
            if not self.isStartDrawLine():
                self.cancel()
                return True
            self.curLine.endPos = self.getPosByXY(x, y)
            self.curLine.endPos.dx = 0 # modify dx to 0
            self.end()
            self.win.invalidWindow()
        elif self.curLine.kind == 'text':
            self.curLine.startPos = self.getPosByXY(x, y)
            if not self.curLine.startPos:
                self.cancel()
                return True
            self.openEditText()
        return True

    def openEditText(self):
        dlg = dialog.MultiInputDialog()
        dlg.createWindow(self.win.hwnd, (0, 0, 250, 200), style = win32con.WS_POPUP)
        dlg.setModal(True)
        dlg.addNamedListener('InputEnd', self.onInputEnd)
        dlg.setText(self.curLine.info)
        dlg.show(* win32gui.GetCursorPos())

    def isStartDrawLine(self):
        return self.isDrawing and self.curLine and self.curLine.kind == 'line' and \
               self.curLine.startPos and self.curLine.startPos.day > 0

    def onMouseMove(self, x, y):
        if not self.isStartDrawLine():
            return False
        pos = self.getPosByXY(x, y)
        if pos:
            self.curLine.endPos = pos
            self.curLine.endPos.dx = 0 # modify dx to 0
        self.win.invalidWindow()
        return True

    def onDblClick(self, x, y):
        self.selLine = self.getTextByXY(x, y)
        if not self.selLine:
            return False
        self.isDrawing = True
        self.curLine = self.selLine
        self.openEditText()
        return True

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_KEYDOWN and self.selLine:
            if wParam == win32con.VK_DELETE or wParam == win32con.VK_BACK:
                self.delLine2(self.selLine)
                self.selLine = None
            return True
        if msg >= win32con.WM_MOUSEFIRST and msg <= win32con.WM_MOUSELAST:
            kl = self.win.klineIndicator
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            x -= kl.x
            y -= kl.y
            isInK = x >= 0 and x < kl.width and y >= 0 and y < kl.height
            if not isInK or not kl.visibleRange:
                return False
            if msg == win32con.WM_LBUTTONDOWN:
                return self.onLButtonDown(x, y)
            if msg == win32con.WM_LBUTTONUP:
                return self.onLButtonUp(x, y)
            if msg == win32con.WM_MOUSEMOVE:
                return self.onMouseMove(x, y)
            if msg == win32con.WM_LBUTTONDBLCLK:
                return self.onDblClick(x, y)
        return False

class KLineWindow(base_win.BaseWindow):
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70

    def __init__(self):
        super().__init__()
        self.klineWidth = 8 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.indicators = []
        self.mouseXY = None
        self.selIdx = -1
        self.selIdxOnClick = False
        self.refIndicatorVisible = True
        self.refIndicator = RefIndicator(self)
        self.klineIndicator = KLineIndicator(self, {'height': -1, 'margins': (30, 20)})
        self.indicators.append(self.klineIndicator)
        from THS import tips_win
        self.hygnWin = tips_win.BkGnWindow()
        self.marksMgr = MarksMgr(self)
        self.contextMenuMgr = ContextMenuMgr(self)
        self.lineMgr = TextLineManager(self)

    def addIndicator(self, indicator : Indicator):
        self.indicators.append(indicator)
        self.calcIndicatorsRect()

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
        self.refIndicator.x = self.klineIndicator.x
        self.refIndicator.y = self.klineIndicator.y
        self.refIndicator.width = self.klineIndicator.width
        self.refIndicator.height = self.klineIndicator.height
    
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
        rs = gn_utils.get_THS_GNTC(code)
        if rs and rs.get('hy_2_code', None):
            self.refIndicator.changeCode(rs['hy_2_code'], period)
        self.lineMgr.changeCode(code)
        self.makeVisible(-1)
        self.invalidWindow()

    def onContextMenu(self, x, y):
        it = self.getIndicatorByPoint(x, y)
        if it and it.onContextMenu(x - it.x, y - it.y):
            return
        # default deal
        self.contextMenuMgr.show(x, y)

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.calcIndicatorsRect()
        self.hygnWin.DEF_COLOR = 0x22cc22

    def onSize(self):
        self.makeVisible(self.selIdx)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if self.lineMgr.winProc(hwnd, msg, wParam, lParam):
            return True
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.onSize()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            self.onMouseMove(lParam & 0xffff, (lParam >> 16) & 0xffff)
            return True
        if msg == win32con.WM_KEYDOWN:
            keyCode = lParam >> 16 & 0xff
            self.onKeyDown(keyCode)
            return True
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onMouseClick(x, y)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            if self.selIdx > 0:
                data = self.klineIndicator.data[self.selIdx]
                self.notifyListener(self.Event('DbClick', self, code = self.klineIndicator.code, idx = self.selIdx, data = data))
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onContextMenu(x, y)
            return True
        if msg == win32con.WM_MOUSELEAVE:
            self.onMouseLeave()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

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
        if idx < 0:
            self.selIdx = -1
            return
        idt = self.klineIndicator
        if not idt.visibleRange or idx < idt.visibleRange[0] or idx >= idt.visibleRange[1]:
            return
        self.selIdx = idx
        item = idt.getItemData(idx)
        if not item:
            return
        self.notifyListener(Listener.Event('selIdx-Changed', self, idx = idx, day = item.day, data = item, datas = self.klineIndicator.data))
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
        ids = self.indicators[ : ]
        ids.append(self.refIndicator)
        for idt in ids:
            idt.calcVisibleRange(idx)
            vr = idt.visibleRange
            if vr:
                idt.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        if not self.klineIndicator.visibleRange:
            return
        w, h = self.getClientSize()
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
            if idt == self.klineIndicator:
                self.marksMgr.onDraw(hdc, self.drawer) # draw marks
            win32gui.RestoreDC(hdc, sdc)

        # draw content
        if self.refIndicatorVisible:
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, self.refIndicator.x, self.refIndicator.y)
            self.refIndicator.draw(hdc, self.drawer)
            win32gui.RestoreDC(hdc, sdc)
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.draw(hdc, self.drawer)
            win32gui.RestoreDC(hdc, sdc)

        sdc = win32gui.SaveDC(hdc)
        win32gui.SetViewportOrgEx(hdc, self.klineIndicator.x, self.klineIndicator.y)
        self.lineMgr.onDraw(hdc)
        win32gui.RestoreDC(hdc, sdc)

        # draw mouse
        if self.mouseXY:
            mx, my = self.mouseXY
            idt = self.getIndicatorByPoint(*self.mouseXY)
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.drawMouse(hdc, self.drawer, mx - idt.x, my - idt.y)
            win32gui.RestoreDC(hdc, sdc)
        self.drawHeaderTip(hdc)
        self.drawer.drawLine(hdc, w - self.RIGHT_MARGIN + 10, 0, w - self.RIGHT_MARGIN + 10, h, 0x0000aa)

    def drawHeaderTip(self, hdc):
        if self.selIdx < 0 or not self.klineIndicator.data:
            return
        data = self.klineIndicator.data
        cur = data[self.selIdx]
        pre = data[self.selIdx - 1]
        lb = cur.amount / pre.amount # 量比
        right = self.klineIndicator.x + self.klineIndicator.width
        PR = 70
        rc = (right - PR , 0, right, 20)
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
        title = f'同比({lb :.1f})'
        self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_RIGHT)

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

    @staticmethod
    def createDefault():
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
        return win

    @staticmethod
    def createSimple():
        win = KLineWindow()
        win.addIndicator(RateIndicator(win, {'height': 60, 'margins': (15, 2)}))
        win.addIndicator(AmountIndicator(win, {'height': 60, 'margins': (10, 2)}))
        return win

class CodeWindow(BaseWindow):
    def __init__(self, klineWin) -> None:
        super().__init__()
        self.curCode = None
        self.basicData = None
        self.selData = None
        self.klineWin = klineWin
        klineWin.addNamedListener('selIdx-Changed', self.onSelIdxChanged)
        self.V_CENTER = win32con.DT_SINGLELINE | win32con.DT_VCENTER

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        LEFT_X, RIGHT_X = 3, 70
        RH = 25
        y = 10
        if self.basicData:
            cs = self.basicData.get('code', '') + '\n' + self.basicData.get('name', '')
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 15, weight = 1000))
            self.drawer.drawText(hdc, cs, (0, y, W, 40), 0x5050ff, win32con.DT_CENTER | win32con.DT_WORDBREAK)
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
        y += 40
        self.drawer.drawLine(hdc, 5, y, W - 5, y, 0x606060)
        y += 3
        self.drawer.drawText(hdc, '流通市值', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        if self.basicData:
            val = (str(int(self.basicData.get('流通市值', 0) / 100000000)) or '--') + ' 亿'
            self.drawer.drawText(hdc, val, (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '总市值', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        if self.basicData:
            val = (str(int(self.basicData.get('总市值', 0) / 100000000)) or '--') + ' 亿'
            self.drawer.drawText(hdc, val, (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawLine(hdc, 5, y, W - 5, y, 0x606060)
        y += 3
        self.drawer.drawText(hdc, '市盈率_静', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        if self.basicData:
            rz = int(self.basicData.get('市盈率_静', 0))
            self.drawer.drawText(hdc, str(rz or '--'), (RIGHT_X + 10, y, W, y + RH), (0xcccccc if rz >= 0 else 0x00ff00), self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '市盈率_TTM', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        if self.basicData:
            rz = int(self.basicData.get('市盈率_TTM', 0))
            self.drawer.drawText(hdc, str(rz or '--'), (RIGHT_X + 10, y, W, y + RH), (0xcccccc if rz >= 0 else 0x00ff00), self.V_CENTER)
        y += RH
        self.drawer.drawLine(hdc, 5, y, W - 5, y, 0x606060)
        y += 3
        # bk gn
        refModel = self.klineWin.refIndicator.model
        klineModel = self.klineWin.klineIndicator.model
        if refModel:
            self.drawer.drawText(hdc, refModel.name, (0, y, W, y + RH), 0x808080, self.V_CENTER | win32con.DT_CENTER)
        y += RH
        self.drawer.drawText(hdc, '板块指数', (LEFT_X, y, W, y + RH), 0x808080, self.V_CENTER)
        if refModel:
            self.drawer.drawText(hdc, refModel.code, (RIGHT_X, y, W, y + RH), 0x808080, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '指数涨幅', (LEFT_X, y, W, y + RH), 0x808080, self.V_CENTER)
        rz = self.getModelAttr(refModel, 'zhangFu')
        if rz is not None:
            self.drawer.drawText(hdc, f'{rz :.2f}%', (RIGHT_X, y, W, y + RH), 0x808080, self.V_CENTER)
        y += RH
        self.drawer.drawLine(hdc, 5, y, W - 5, y, 0x606060)
        y += 3
        self.drawer.drawText(hdc, '涨幅', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        rz = self.getModelAttr(klineModel, 'zhangFu')
        if rz is not None:
            color = 0x0000ff if rz >= 0 else 0x00ff00
            self.drawer.drawText(hdc, f'{rz :.2f}%', (RIGHT_X, y, W, y + RH), color, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '成交额', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        rz = self.getModelAttr(klineModel, 'amount')
        if rz is not None:
            self.drawer.drawText(hdc, f'{rz / 100000000 :.1f} 亿', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '换手率', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        rz = self.getModelAttr(klineModel, 'rate')
        if rz is not None:
            self.drawer.drawText(hdc, f'{int(rz)} %', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)

    def getModelAttr(self, model, attrName):
        if not self.selData or not model:
            return None
        day = self.selData.day
        idx = model.getItemIdx(day)
        if idx >= 0: 
            return getattr(model.data[idx], attrName, None)
        return None

    def loadCodeBasic(self, code):
        from download import cls
        url = cls.ClsUrl()
        self.basicData = url.loadBasic(code)
        self.invalidWindow()

    def changeCode(self, code):
        scode = f'{code :06d}' if type(code) == int else code
        if (self.curCode == scode) or (not scode):
            return
        self.curCode = scode
        self.basicData = None
        base_win.ThreadPool.instance().addTask_N(self.loadCodeBasic, scode)

    def onSelIdxChanged(self, evt, args):
        self.selData = evt.data
        self.invalidWindow()

class KLineCodeWindow(base_win.BaseWindow):
    def __init__(self, tag = 'default') -> None:
        super().__init__()
        self.css['bgColor'] = 0x101010
        self.layout = None
        if tag == 'simple':
            self.klineWin = KLineWindow.createSimple()
        else:
            self.klineWin = KLineWindow.createDefault()
        self.codeWin = CodeWindow(self.klineWin)
        self.codeList = None
        self.code = None
        self.idxCodeList = -1
        self.idxCodeWin = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        DETAIL_WIDTH = 150
        self.layout = base_win.GridLayout(('100%', ), ('1fr', DETAIL_WIDTH), (5, 5))
        self.klineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.klineWin)

        rightLayout = base_win.FlowLayout()
        self.codeWin.createWindow(self.hwnd, (0, 0, DETAIL_WIDTH, 310))
        rightLayout.addContent(self.codeWin, {'margins': (0, 5, 0, 5)})
        btn = base_win.Button({'title': '<<', 'name': 'LEFT'})
        btn.createWindow(self.hwnd, (0, 0, 40, 30))
        btn.addNamedListener('Click', self.onLeftRight)
        rightLayout.addContent(btn, {'margins': (0, 10, 0, 0)})
        self.idxCodeWin = base_win.Label()
        self.idxCodeWin.createWindow(self.hwnd, (0, 0, 70, 30))
        self.idxCodeWin.css['textAlign'] |= win32con.DT_CENTER
        rightLayout.addContent(self.idxCodeWin, {'margins': (0, 10, 0, 0)})
        btn = base_win.Button({'title': '>>', 'name': 'RIGHT'})
        btn.createWindow(self.hwnd, (0, 0, 40, 30))
        btn.addNamedListener('Click', self.onLeftRight)
        rightLayout.addContent(btn, {'margins': (0, 10, 0, 0)})
        self.layout.setContent(0, 1, rightLayout)
        self.layout.resize(0, 0, *self.getClientSize())

    def _getCode(self, d):
        if type(d) == dict:
            code = d.get('code', None) or d.get('secu_code', None) or ''
            if len(code) == 8 and code[0] == 's':
                code = code[2 : ]
            return code
        if type(d) == str:
            return d
        if type(d) == int:
            return f'{d :06d}'
        return d

    def _findIdx(self):
        for idx, d in enumerate(self.codeList):
            if self._getCode(d) == self.code:
                return idx
        return -1

    def onLeftRight(self, evt, args):
        if not self.codeList or not self.code:
            return
        idx = self.idxCodeList
        if evt.info['name'] == 'LEFT':
            if idx == 0:
                idx = len(self.codeList)
            idx -= 1
        else:
            if idx == len(self.codeList) - 1:
                idx = -1
            idx += 1
        self.idxCodeList = idx
        cur = self.codeList[idx]
        self.changeCode(self._getCode(cur))
        self.updateCodeIdxView()

    def changeCode(self, code, peroid = 'day'):
        try:
            if type(code) == int:
                code = f'{code :06d}'
            if len(code) == 8 and code[0] == 's':
                code = code[2 : ]
            self.code = code
            self.codeWin.changeCode(code)
            self.klineWin.changeCode(code, peroid)
        except Exception as e:
            traceback.print_exc()
    
    def updateCodeIdxView(self):
        if not self.codeList:
            self.idxCodeWin.setText('')
            return
        idx = self.idxCodeList
        if idx >= 0:
            self.idxCodeWin.setText(f'{idx + 1} / {len(self.codeList)}')

    # codes = [ str, str, ... ]  |  [ int, int, ... ]
    #         [ {'code':xxx, }, ... ]  | [ {'secu_code':xxx, }, ... ]
    def setCodeList(self, codes, curIdx = -1):
        if not codes:
            return
        self.codeList = codes
        if curIdx < 0:
            curIdx = self._findIdx()
        self.idxCodeList = curIdx
        self.updateCodeIdxView()


if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    win = KLineCodeWindow()
    win.createWindow(None, (0, 0, 1300, 700), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)

    win.changeCode('000737', 'day') # 000737  002261
    win32gui.PumpMessages()