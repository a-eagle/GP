import os, sys, functools, copy, datetime, json, time, traceback, copy
import win32gui, win32con, win32api, pyperclip

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from orm import chrome_orm, my_orm, d_orm
from ui import base_win, dialog
from utils import gn_utils
from ui.kline_indicator import *
from ui import bkgn_view
from download import henxin, console

class MarksManager:
    def __init__(self, win) -> None:
        self.win = win
        self.data = {} # int items

    def clearMarkDay(self):
        self.data.clear()

    # day = int | str | date | list | tuple
    def setMarkDay(self, day, tip = None):
        if not day:
            return
        if type(day) == str:
            day = int(day.replace('-', ''))
        elif isinstance(day, datetime.date):
            dd : datetime.date = day
            day = dd.year * 10000 + dd.month * 100 + dd.day
        elif type(day) == list or type(day) == tuple:
            for d in day:
                self.setMarkDay(d)
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
        kl : Indicator = self.win.klineIndicator
        vr = kl.visibleRange
        if not vr or not kl.model:
            return
        for day in self.data:
            idx = kl.model.getItemIdx(day)
            if idx >= vr[0] and idx < vr[1]:
                kl.drawIdxMark(hdc, drawer, idx)

class ContextMenuManager:
    def __init__(self, win) -> None:
        self.win = win

    def getMenuModel(self):
        data = self.win.klineIndicator.data
        if not data or self.win.selIdx < 0:
            return None
        selDay = data[self.win.selIdx].day
        code = self.win.klineIndicator.code
        mm = [
              {'title': '点击时选中K线', 'name': 'sel-idx-on-click', 'checked': self.win.selIdxOnClick},
              {'title': '显示叠加指数', 'name': 'show-ref-zs', 'checked': self.win.refIndicatorVisible},
              {'title': '显示K线', 'name': 'show-kline', 'checked': self.win.klineIndicatorVisible},
              {'title': 'LINE'},
              {'name': 'add-ref-zs', 'title': '叠加上证指数', 'code': '1A0001'}
        ]
        isZS = code[0 : 2] == '88' or code == '1A0001' or code[0 : 3] == 'cls'
        if not isZS:
            mm.extend([
              {'title': '叠加指数 THS', 'name': 'add-ref-zs', 'sub-menu': self.getThsZsList(selDay)},
              {'title': '叠加指数 CLS', 'name': 'add-ref-zs', 'sub-menu': self.getClsZsList(selDay)},
              {'title': '查看指数', 'name': 'open-cur-ref-zs', 'enable': self.win.refIndicator.isValid()},
              {'title': '查看板块', 'name': 'open-cur-ref-zs-bk', 'enable': selDay > 0 and self.win.refIndicator.isValid(), 'day': selDay,},
              #{'title': 'LINE'},
              #{'title': '查看板块个股 THS', 'name': 'open-ref-thszs', 'sub-menu': self.getThsZsList(selDay)},
              #{'title': '查看板块个股 CLS', 'name': 'open-ref-clszs', 'sub-menu': self.getClsZsList(selDay)},
              {'title': '查看当日行情', 'name': 'open-ref-global', 'enable': selDay > 0, 'day': selDay},
              {'title': '查看个股信息', 'name': 'open-info'},
            ])
        else:
            mm.extend([
                {'title': 'LINE'},
                {'title': '查看板块个股', 'name': 'open-cur-zs', 'day': selDay, 'enable': selDay > 0 and self.win.refIndicator.isValid()},
            ])
        mm.extend([
              {'title': 'LINE'},
              {'title': '标记日期 +', 'name': 'mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': '标记日期 -', 'name': 'cancel-mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': 'LINE'},
              {'title': '画线(直线)', 'name': 'draw-line'},
              {'title': '画线(文本)', 'name': 'draw-text'},
              {'title': '删除画线', 'name': 'del-draw-line', 'enable': self.win.lineMgr.isSelected()},
              {'title': '计算涨跌幅', 'name': 'calc-zdf'},
            #   {'title': 'LINE'},
            #   {'title': '标记', 'name': 'mark-color', 'sub-menu': self.getMarkColors},
            #   {'title': '简单指标', 'name': 'simple-indicator', 'checked': self.win.simpleIndicator},
        ])
        return mm
    
    def getMarkColors(self, it):
        def render(menu, hdc, rect, menuItem):
            W, H = rect[2] - rect[0], rect[3] - rect[1]
            BW, BH = 50, 15
            sx = rect[0] + 20
            sy = (H - BH) // 2 + rect[1]
            rc = (sx, sy, sx + BW, sy + BH)
            drawer = Drawer.instance()
            if menuItem['rcolor'] is None:
                drawer.drawRect(hdc, rc, 0x999999)
            else:
                drawer.fillRect(hdc, rc, menuItem['rcolor'])
                if menuItem['cur']:
                    drawer.drawText(hdc, '[*]', rect, color = 0, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)

        code = self.win.klineIndicator.model.code
        obj = chrome_orm.MyMarkColor.get_or_none(chrome_orm.MyMarkColor.code == code)
        scolor = None
        if obj:
            scolor = obj.color
        cs = [
            {'rcolor': None, 'render': render, 'scolor': None}, {'rcolor': 0x0000ff, 'render': render, 'scolor': '#f00'},
            {'rcolor': 0x00ff00, 'render': render, 'scolor': '#0f0'}, {'rcolor': 0xff0000, 'render': render, 'scolor': '#00f'},
            {'rcolor': 0x9314FF, 'render': render, 'scolor': '#FF1493'}, {'rcolor': 0xCD329A, 'render': render, 'scolor': '#9A32CD'}
        ]
        for c in cs:
            c['cur'] = c['scolor'] == scolor
        return cs

    def bkGnRender(self, menu, hdc, rect, menuItem):
        drawer = Drawer.instance()
        title = menuItem['title']
        if menuItem['hotsNum']:
            drawer.drawText(hdc, menuItem['hotsNum'], (0, rect[1], rect[0], rect[3]), 0x0000cc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        drawer.drawText(hdc, title, rect, menu.css['textColor'], win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_WORDBREAK)

    def getThsZsList(self, day):
        from orm import ths_orm
        hots = self.win.bkgnView.getHotBkGn()
        mhots = {h['gn'] : h['num'] for h in hots if h['num'] > 0}
        code = self.win.klineIndicator.code
        obj : ths_orm.THS_GNTC = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        model = []
        if not obj:
            return model
        if obj.hy_2_code: model.append({'title': obj.hy_2_name, 'code': obj.hy_2_code, 'day': day, 'hotsNum': mhots.get(obj.hy_2_name, 0), 'render': self.bkGnRender})
        if obj.hy_3_code: model.append({'title': obj.hy_3_name, 'code': obj.hy_3_code, 'day': day, 'hotsNum': mhots.get(obj.hy_3_name, 0), 'render': self.bkGnRender})
        model.append({'title': 'LINE'})
        if not obj.gn_code:
            return model
        gn_codes = obj.gn_code.split(';')
        gn_names = obj.gn.split(';')
        model2 = []
        for i in range(len(gn_codes)):
            if gn_codes[i].strip():
                model2.append({'title': gn_names[i], 'code': gn_codes[i].strip(), 'day': day, 'hotsNum': mhots.get(gn_names[i], 0), 'render': self.bkGnRender})
        model2.sort(key = lambda d: d['hotsNum'], reverse = True)
        return model + model2

    def getClsZsList(self, day):
        from orm import cls_orm
        hots = self.win.bkgnView.getHotBkGn()
        mhots = {h['gn'] : h['num'] for h in hots if h['num'] > 0}
        model = []
        code = self.win.klineIndicator.code
        obj : cls_orm.CLS_GNTC = cls_orm.CLS_GNTC.get_or_none(cls_orm.CLS_GNTC.code == code)
        if not obj:
            return model
        if obj.hy and obj.hy_code:
            hys = zip(obj.hy.split(';'), obj.hy_code.split(';'))
            for hy in hys:
                if hy[0].strip() and hy[1].strip():
                    model.append({'title': hy[0], 'code': hy[1].strip(), 'day': day, 'hotsNum': mhots.get(hy[0], 0), 'render': self.bkGnRender})
        model.append({'title': 'LINE'})
        model2 = []
        if obj.gn and obj.gn_code:
            gns = zip(obj.gn.split(';'), obj.gn_code.split(';'))
            for gn in gns:
                if gn[0].strip() and gn[1].strip():
                    model2.append({'title': gn[0], 'code': gn[1].strip(), 'day': day, 'hotsNum': mhots.get(gn[0], 0), 'render': self.bkGnRender})
        model2.sort(key = lambda d: d['hotsNum'], reverse = True)
        return model + model2

    def show(self, x, y):
        mm = self.getMenuModel()
        if not mm:
            return
        menu = base_win.PopupMenu.create(self.win.hwnd, mm)
        menu.VISIBLE_MAX_ITEM = 20
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
        elif name == 'show-kline':
            self.win.klineIndicatorVisible = evt.item['checked']
            self.win.invalidWindow()
        elif name == 'open-cur-ref-zs':
            code = self.win.refIndicator.code
            mk = self.win.marksMgr.data
            from ui import kline_utils
            data = {'code': code}
            zsWin = kline_utils.openInCurWindow(self.win.hwnd, data)
            for d in mk:
                zsWin.klineWin.marksMgr.setMarkDay(d, mk[d])
        elif name == 'open-cur-ref-zs-bk':
            code = self.win.refIndicator.code
            day = evt.item["day"]
            self.openRefZs(code, day)
        elif name == 'open-ref-thszs':
            code = evt.item['code']
            day = evt.item["day"]
            self._openRefThsZs(code, day)
        elif name == 'open-ref-clszs':
            code = evt.item['code']
            day = evt.item["day"]
            self._openRefClsZs(code, day)
        elif name == 'open-ref-global':
            day = evt.item["day"]
            self.openRefGlobal(day)
        elif name == 'open-info':
            code = self.win.klineIndicator.code
            scode = cls.ClsUrl()._getTagCode(code)
            url = f'https://www.cls.cn/stock?code={scode}'
            win32api.ShellExecute(None, 'open', url, '', '', True) # '--incognito'
        elif name == 'open-cur-zs':
            code = self.win.klineIndicator.code
            day = evt.item["day"]
            if code[0 : 2] == '88':
                self._openRefThsZs(code, day)
            else:
                self._openRefClsZs(code, day)
        elif name == 'add-ref-zs':
            code = evt.item['code']
            self.win.refIndicator.changeCode(code, self.win.klineIndicator.period)
            self.win.invalidWindow()
        elif name == 'draw-line':
            self.win.lineMgr.beginNew('line')
            pass
        elif name == 'draw-text':
            self.win.lineMgr.beginNew('text')
            pass
        elif name == 'del-draw-line':
            self.win.lineMgr.delSelectLine()
        elif name == 'mark-color':
            self.markColor(evt.item)
        elif name == 'simple-indicator':
            v = self.win.simpleIndicator = not self.win.simpleIndicator
            TS = (ThsZT_Indicator, ClsZT_Indicator)
            for it in self.win.indicators:
                it.visible = (not v) or (type(it) not in TS)
            self.win.calcIndicatorsRect()
        elif name == 'calc-zdf':
            self.win.calcZdfMgr.ready()

    def markColor(self, item):
        code = self.win.klineIndicator.model.code
        name = self.win.klineIndicator.model.name
        scode = ('sh' if code[0] == '6' else 'sz') + code
        obj = chrome_orm.MyMarkColor.get_or_none(chrome_orm.MyMarkColor.code == code)
        scolor = item['scolor']
        if scolor is None:
            if obj: obj.delete_instance()
            return
        if not obj:
            today = datetime.date.today().strftime('%Y-%m-%d')
            chrome_orm.MyMarkColor.create(code = code, secu_code = scode, name = name, color = scolor, day = today)
        else:
            obj.color = scolor
            obj.save()

    def openRefZs(self, code, day):
        if not code:
            return
        if code[0 : 2] == '88':
            obj = ths_orm.THS_ZS.get_or_none(ths_orm.THS_ZS.code == code)
        else:
            obj = cls_orm.CLS_ZS.get_or_none(cls_orm.CLS_ZS.code == code)
        name = obj.name if obj else ''
        url = f'http://localhost:8080/local/plate.html?code={code}&day={day}&name={name}'
        win32api.ShellExecute(None, 'open', url, '', '', True) # '--incognito'

    def openRefGlobal(self, day):
        url = f'http://localhost:8080/local/index.html?day={day}'
        pyperclip.copy(url)
        win32api.ShellExecute(None, 'open', url, '', '', True) # '--incognito'

class CalcZdfManager:
    def __init__(self, win) -> None:
        self.win = win
        self.captureMouse = False
        self.lockStartPos = False
        self.startPos = None
        self.endPos = None

    def ready(self):
        self.captureMouse = True
        self.startPos = None
        self.endPos = None
        self.lockStartPos = False

    def onLButtonUp(self, x, y):
        if not self.lockStartPos:
            self.lockStartPos = True
            self.startPos = (x, y)
            self.endPos = None
        else:
            self.captureMouse = False
            self.lockStartPos = False
            self.startPos = None
            self.endPos = None
        self.win.invalidWindow()

    def onMouseMove(self, x, y):
        if not self.captureMouse:
            return
        if not self.lockStartPos:
            self.startPos = (x, y)
        else:
            self.endPos = (x, y)
        self.win.invalidWindow()

    def onDraw(self, hdc):
        if not self.captureMouse or not self.startPos:
            return
        sx, sy = self.startPos
        sdc = win32gui.SaveDC(hdc)
        kl : KLineIndicator = self.win.klineIndicator
        drawer : base_win.Drawer = self.win.drawer

        LINE_COLOR = 0x008CFF
        drawer.use(hdc, drawer.getPen(LINE_COLOR, win32con.PS_SOLID))
        win32gui.MoveToEx(hdc, kl.x, sy)
        win32gui.LineTo(hdc, kl.x + kl.width, sy)
        price1 = kl.getValueAtY(sy - kl.y)
        if price1:
            tx = sx
            if self.endPos:
                tx = self.endPos[0]
            rc = (tx - 80, sy, tx, sy + 20)
            drawer.drawText(hdc, price1['fmtVal'], rc, color = LINE_COLOR, align = win32con.DT_LEFT)
        if self.endPos:
            ex, ey = self.endPos
            drawer.use(hdc, drawer.getPen(LINE_COLOR, win32con.PS_SOLID))
            win32gui.MoveToEx(hdc, kl.x, ey)
            win32gui.LineTo(hdc, kl.x + kl.width, ey)
            win32gui.MoveToEx(hdc, kl.x + ex, sy)
            win32gui.LineTo(hdc, kl.x + ex, ey)
            price2 = kl.getValueAtY(ey - kl.y)
            if price2:
                rc = (ex - 80, ey, ex, ey + 20)
                drawer.drawText(hdc, price2['fmtVal'], rc, color = LINE_COLOR, align = win32con.DT_LEFT)
            # calc zdf
            if price1 and price2:
                maxPrice = max(price1['value'], price2['value'])
                minPrice = min(price1['value'], price2['value'])
                zf = (maxPrice - minPrice) / minPrice * 100
                df = (minPrice - maxPrice) / maxPrice * 100
                cy = (ey - sy) // 2 + sy - 20
                rc = (ex + 15, cy, ex + 100, cy + 20)
                drawer.drawText(hdc, f'涨幅 {zf :.1f}%', rc, color = LINE_COLOR, align = win32con.DT_LEFT)
                cy += 20
                rc = (ex + 15, cy, ex + 100, cy + 20)
                drawer.drawText(hdc, f'跌幅 {df :.1f}%', rc, color = LINE_COLOR, align = win32con.DT_LEFT)

        win32gui.RestoreDC(hdc, sdc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg >= win32con.WM_MOUSEFIRST and msg <= win32con.WM_MOUSELAST:
            if not self.captureMouse:
                return False
            kl = self.win.klineIndicator
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            cx = x - kl.x
            cy = y - kl.y
            isInK = x >= 0 and x < kl.width and y >= 0 and y < kl.height
            if msg == win32con.WM_LBUTTONUP:
                self.onLButtonUp(x, y)
            if msg == win32con.WM_MOUSEMOVE:
                self.onMouseMove(x, y)
            return True
        return False

class IndicatorVisibleManager:
    def __init__(self, win) -> None:
        self.win = win
        self.model = []

    def getMenuModel(self):
        if self.model:
            return self.model
        for i in range(1, len(self.win.indicators)):
            it = self.win.indicators[i]
            self.model.append({'title': it.config['title'], 'checked': it.visible, 'index': i, 'indicator': it})
            if isinstance(it, AmountIndicator):
                self.model.append({'title': 'LINE'})
        return self.model

    def show(self, x, y):
        mm = self.getMenuModel()
        if not mm:
            return
        menu = base_win.PopupMenu.create(self.win.hwnd, mm)
        menu.VISIBLE_MAX_ITEM = 20
        x, y = win32gui.GetCursorPos()
        menu.addNamedListener('Select', self.onMemuItem)
        menu.show(x, y)

    def onMemuItem(self, evt, args):
        indicator = evt.item['indicator']
        indicator.visible = evt.item['checked']
        self.win.calcIndicatorsRect()
        self.win.invalidWindow()
        self.setIndicatorVisible(indicator, indicator.visible)
        
    def setIndicatorVisible(self, indicator, visible):
        platformKey = platform.node()
        obj = my_orm.MySettings.get_or_none(my_orm.MySettings.platform == platformKey,
                                      my_orm.MySettings.mainKey == 'IndicatorVisible',
                                      my_orm.MySettings.subKey == indicator.__class__.__name__)
        val = 'true' if visible else 'false'
        if obj:
            obj.val = val
            obj.save()
        else:
            my_orm.MySettings.create(platform = platformKey, mainKey = 'IndicatorVisible', 
                                     subKey = indicator.__class__.__name__, val = val)

    @staticmethod
    def getIndicatorVisible(indicatorClass, default = True):
        platformKey = platform.node()
        obj = my_orm.MySettings.get_or_none(my_orm.MySettings.platform == platformKey,
                                      my_orm.MySettings.mainKey == 'IndicatorVisible',
                                      my_orm.MySettings.subKey == indicatorClass.__name__)
        if obj:
            visible = True if obj.val == 'true' else False
            return visible
        return default

class Point:
    def __init__(self, day = 0, dx = 0, price = 0, pos = None) -> None:
        self.day = day
        self.dx = dx
        self.price = price
        if pos:
            self.load(pos)

    def toXY(self, kl : KLineIndicator):
        vr = kl.visibleRange
        if not vr or not self.isValid():
            return None
        idx = kl.model.getItemIdx(self.day)
        if idx < vr[0] or idx >= vr[1]:
            return None
        x = kl.getCenterX(idx) + self.dx
        if x < 0 or x > kl.width:
            return None
        y = kl.getYAtValue(self.price)
        if y < 0 or y >= kl.height:
            return None
        return (x, y)

    def update(self, point):
        if not point:
            return
        self.day = point.day
        self.dx = point.dx
        self.price = point.price

    @staticmethod
    def fromXY(x, y, kl : KLineIndicator):
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
        return Point(day, x - cx, price['value'])

    def setXY(self, x, y, kl : KLineIndicator):
        point = Point.fromXY(x, y, kl)
        if not point:
            return False
        self.update(point)
        return True

    def move(self, dx, dy, kl : KLineIndicator):
        xy = self.toXY(kl)
        if not xy:
            return False
        x, y = xy[0] + dx, xy[1] + dy
        return self.setXY(x, y, kl)

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

    def __eq__(self, m) -> bool:
        return self.day == m.day and self.dx == m.dx and self.price == m.price

class Polygon:
    def __init__(self) -> None:
        self.points = [] # Point array
    
    def isPointIn(self, x, y, kl : KLineIndicator):
        N = len(self.points)
        inside = False
        for i in range(N):
            pp1 = self.points[i]
            pp2 = self.points[(i + 1) % N]
            if not pp1 or not pp2:
                return False
            p1 = pp1.toXY(kl)
            p2 = pp2.toXY(kl)
            if not p1 or not p2:
                return False
            x1, y1 = p1[0], p1[1]
            x2, y2 = p2[0], p2[1]
            if ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1):
                inside = not inside
        return inside
    
    def move(self, dx, dy, kl : KLineIndicator):
        for p in self.points:
            p.move(dx, dy, kl)

    def setPoints(self, *points):
        self.points.clear()
        for p in points:
            self.points.append(p)

    def addPoint(self, point : Point):
        self.points.append(point)

    def addXYPoint(self, x, y, kl : KLineIndicator):
        pt = Point.fromXY(x, y, kl)
        self.points.append(pt)

    def toXYPoints(self, kl : KLineIndicator):
        pts = []
        for p in self.points:
            xy = p.getXY(kl)
            if not xy:
                return None
            pts.append(xy)
        return pts

    def isEmpty(self):
        return len(self.points) == 0

    def isValid(self):
        if self.isEmpty():
            return False
        for p in self.points:
            if not p or not p.isValid():
                return False
        return True

class Dragable:
    def __init__(self) -> None:
        super().__init__()
        self.shape = Polygon()
        self.pressXY = None
        self.moveXY = None
        self.draging = False

    def getOutShape(self) -> Polygon:
        return None

    def onLButtonDown(self, x, y, kl : KLineIndicator):
        self.draging = False
        self.pressXY = None
        self.moveXY = None
        if self.getOutShape().isPointIn(x, y, kl):
            self.pressXY = self.moveXY = (x, y)
            self.draging = True
            return True
        return False

    def onMouseMove(self, x, y, kl : KLineIndicator):
        if not self.draging:
            self.draging = False
            return False
        dx, dy = x - self.moveXY[0], y - self.moveXY[1]
        if dx == 0 and dy == 0:
            return True
        self.shape.move(dx, dy, kl)
        self.moveXY = (x, y)
        return True

    def onLButtonUp(self, x, y, kl : KLineIndicator):
        if not self.draging:
            return False
        self.onMouseMove(x, y, kl) # modify shape posints
        self.onDragEnd(x, y)
        self.pressXY = None
        self.moveXY = None
        self.draging = False
        return True
    
    def onDragEnd(self, x, y):
        pass

class DragManager:
    def __init__(self, win) -> None:
        self.capture = False
        self.target = None
        self.win = win

    def reset(self):
        self.capture = False
        self.target = None

    def isDraging(self):
        return self.capture and self.target and self.target.draging

    def onLButtonDown(self, x, y, target : Dragable):
        kl : KLineIndicator = self.win.klineIndicator
        self.reset()
        if not target:
            return False
        if target.onLButtonDown(x, y, kl):
            self.capture = True
            self.target = target
            return True
        return False

    def onMouseMove(self, x, y):
        kl : KLineIndicator = self.win.klineIndicator
        if not self.isDraging():
            return False
        flag = self.target.onMouseMove(x, y, kl)
        return True

    def onLButtonUp(self, x, y):
        kl : KLineIndicator = self.win.klineIndicator
        if not self.isDraging():
            return False
        flag = self.target.onLButtonUp(x, y, kl)
        self.reset()
        return True

class LineView(Dragable):
    def __init__(self, textLine, win) -> None:
        super().__init__()
        self.textLine = textLine
        self.win = win
        if textLine._startPos:
            self.startPos = Point(pos = textLine._startPos)
        else:
            self.startPos = Point()
        if textLine._endPos:
            self.endPos = Point(pos = textLine._endPos)
        else:
            self.endPos = Point()
    
    def isValid(self):
        if self.textLine.kind == 'line':
            return self.startPos and self.startPos.isValid() and \
                self.endPos and self.endPos.isValid()
        return self.startPos and self.startPos.isValid() and self.textLine.info

    def save(self):
        line = self.textLine
        if not line:
            return
        oldId = line.id
        if line.kind == 'line':
            if self.isValid() and self.startPos != self.endPos:
                line._startPos = self.startPos.dump()
                line._endPos = self.endPos.dump()
                line.save()
        elif line.kind == 'text':
            if self.isValid():
                line._startPos = self.startPos.dump()
                line.save()
    
    def getOutShape(self) -> Polygon:
        if not self.isValid():
            return None
        shape = None
        if self.textLine.kind == 'text':
            shape = self.calcTextOutShape()
        elif self.textLine.kind == 'line':
            shape = self.calcLineOutShape()
        if shape and shape.isValid():
            return shape
        return None

    def clearShape(self):
        self.shape.points.clear()

    def onDraw(self, hdc, hilight):
        if self.textLine.kind == 'text':
            self.onDrawText(hdc, hilight)
        elif self.textLine.kind == 'line':
            self.onDrawLine(hdc, hilight)

    def onDrawText(self, hdc, hilight):
        drawer = Drawer.instance()
        kl : KLineIndicator = self.win.klineIndicator
        vr = kl.visibleRange
        if not self.isValid() or not vr:
            return
        textLine = self.textLine
        size = drawer.calcTextSize(hdc, textLine.info)
        xy = self.startPos.toXY(kl)
        if not xy:
            return
        rc = (*xy, xy[0] + size[0], xy[1] + size[1])
        if self.shape.isEmpty():
            self.shape.addPoint(self.startPos)
        self.shape._textSize = size
        drawer.drawText(hdc, textLine.info, rc, color = 0x404040, align = win32con.DT_LEFT)
        if hilight:
            self.drawOutShape(hdc)

    def calcTextOutShape(self):
        kl : KLineIndicator = self.win.klineIndicator
        B = 4
        size = getattr(self.shape, '_textSize')
        if not size:
            return None
        sxy = self.startPos.toXY(kl)
        if not sxy:
            return None
        x, y = sxy
        w, h = size
        left, top, right, bottom = x - B, y - B, x + w + B, y + h + B
        outShape = Polygon()
        outShape.addXYPoint(left, top, kl)
        outShape.addXYPoint(right, top, kl)
        outShape.addXYPoint(right, bottom, kl)
        outShape.addXYPoint(left, bottom, kl)
        return outShape

    def calcLineOutShape(self):
        kl : KLineIndicator = self.win.klineIndicator
        B = 4
        sxy = self.startPos.toXY(kl)
        exy = self.endPos.toXY(kl)
        if not sxy or not exy:
            return None
        outShape = Polygon()
        if exy[1] > sxy[1]:
            sxy, exy = exy, sxy
        sx, sy = sxy
        ex, ey = exy
        if abs(ey - sy) <= abs(ex - sx):
            outShape.addXYPoint(sx, sy - B, kl)
            outShape.addXYPoint(sx, sy + B, kl)
            outShape.addXYPoint(ex, ey + B, kl)
            outShape.addXYPoint(ex, ey - B, kl)
        else:
            outShape.addXYPoint(sx - B, sy, kl)
            outShape.addXYPoint(sx + B, sy, kl)
            outShape.addXYPoint(ex + B, ey, kl)
            outShape.addXYPoint(ex - B, ey, kl)
        return outShape
            
    def onDrawLine(self,  hdc, hilight):
        kl : KLineIndicator = self.win.klineIndicator
        drawer = Drawer.instance()
        vr = kl.visibleRange
        if not self.isValid() or not vr:
            return
        sxy = self.startPos.toXY(kl)
        exy = self.endPos.toXY(kl)
        if not sxy or not exy:
            return
        if self.shape.isEmpty():
            self.shape.addPoint(self.startPos)
            self.shape.addPoint(self.endPos)
        drawer.drawLine(hdc, *sxy, *exy, 0x30f030, width = 1)
        self.drawLineArrow(hdc, *sxy, *exy)
        if hilight:
            self.drawOutShape(hdc)
    
    def drawOutShape(self, hdc):
        kl : KLineIndicator = self.win.klineIndicator
        drawer = Drawer.instance()
        out = self.getOutShape()
        if not out or not out.isValid():
            return
        pots = [p.toXY(kl) for p in out.points]
        pots.append(pots[0]) # close path
        drawer.use(hdc, drawer.getPen(0xA0A0A0, style = win32con.PS_DOT))
        win32gui.Polyline(hdc, pots)

    def drawLineArrow(self, hdc, sx, sy, ex, ey):
        drawer = Drawer.instance()
        if sx == ex and sy == ey:
            return
        rc = (ex - 2, ey - 2, ex + 3, ey + 3)
        drawer.fillRect(hdc, rc, 0x30f030)

    def onDragBegin(self, x, y):
        # print('[LineView.onDragBegin]', x, y)
        pass

    def onDrag(self, x, y):
        kl : KLineIndicator = self.win.klineIndicator
        dx = x - self.moveXY[0]
        dy = y - self.moveXY[1]
        self.shape.move(dx, dy, kl)

    def onDragEnd(self, x, y):
        self.onDrag(x, y)
        # save Line to db
        pts = self.shape.points
        if self.textLine.kind == 'text':
            if len(pts) == 1:
                self.startPos = pts[0]
                self.save()
        elif self.textLine.kind == 'line':
            if len(pts) == 2:
                self.startPos = pts[0]
                self.endPos = pts[1]
                self.save()

class DrawTextManager(base_win.Listener):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.curLine = None
        self.drawing = False

    def beginNew(self, code):
        self.drawing = True
        curLine = my_orm.TextLine(code = code, kind = 'text')
        self.curLine = LineView(curLine, self.win)

    def beginUpdate(self, lineView):
        self.cancel()
        if not lineView:
            return
        self.drawing = True
        self.curLine = lineView

    def end(self):
        if not self.drawing:
            return False
        self.curLine.save()
        cl = self.curLine
        self.cancel()
        self.notifyListener(self.Event('AppendLine', cl))
        return True

    def cancel(self):
        self.drawing = False
        self.curLine = None

    def openEditText(self):
        dlg = dialog.MultiInputDialog()
        dlg.createWindow(self.win.hwnd, (0, 0, 250, 200), style = win32con.WS_POPUP)
        dlg.setModal(True)
        dlg.addNamedListener('InputEnd', self.onInputEnd)
        dlg.setText(self.curLine.textLine.info)
        dlg.show(* win32gui.GetCursorPos())

    def onInputEnd(self, evt, args):
        if evt.ok and evt.text:
            self.curLine.textLine.info = evt.text
            self.end()
        else:
            self.cancel()

    def onLButtonDown(self, x, y):
        return self.drawing

    def onMouseMove(self, x, y):
        return self.drawing

    def onLButtonUp(self, x, y):
        if not self.drawing:
            return False
        pos = Point.fromXY(x, y, self.win.klineIndicator)
        if not pos:
            self.cancel()
            return True
        self.curLine.startPos.update(pos)
        self.openEditText()
        return True

class DrawLineManager(base_win.Listener):
    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.curLine : LineView = None
        self.drawing = False

    def beginNew(self, code):
        self.drawing = True
        curLine = my_orm.TextLine(code = code, kind = 'line')
        self.curLine = LineView(curLine, self.win)

    def end(self):
        if not self.drawing:
            return False
        self.curLine.save()
        cl = self.curLine
        self.cancel()
        cl.clearShape()
        self.notifyListener(self.Event('AppendLine', cl))
        self.win.invalidWindow()
        return True

    def cancel(self):
        self.drawing = False
        self.curLine = None

    def isDrawing(self):
        return self.drawing and self.curLine and self.curLine.startPos.isValid()

    def onLButtonDown(self, x, y):
        if not self.drawing:
            return False
        pos = Point.fromXY(x, y, self.win.klineIndicator)
        if not pos:
            self.cancel()
            return False
        # pos.dx = 0 # modify line dx to 0
        self.curLine.startPos.update(pos)
        return True

    def onMouseMove(self, x, y):
        if not self.drawing:
            return False
        pos = Point.fromXY(x, y, self.win.klineIndicator)
        self.curLine.endPos.update(pos)
        # self.curLine.endPos.dx = 0 # modify dx to 0
        self.win.invalidWindow()
        return True

    def onLButtonUp(self, x, y):
        if not self.isDrawing():
            self.cancel()
            return False
        pos = Point.fromXY(x, y, self.win.klineIndicator)
        self.curLine.endPos.update(pos)
        self.end()
        self.win.invalidWindow()
        return True

class TextLineManager:
    def __init__(self, win) -> None:
        self.win : KLineWindow = win
        self.drager = DragManager(win)
        self.drawTextMgr = DrawTextManager(win)
        self.drawLineMgr = DrawLineManager(win)
        self.drawTextMgr.addNamedListener('AppendLine', self.onAppendLine)
        self.drawLineMgr.addNamedListener('AppendLine', self.onAppendLine)
        self._reset()

    def _reset(self):
        self.code = None
        self.lines = []
        self.selLine = None

    def isSelected(self):
        return self.selLine != None

    def beginNew(self, kind):
        if kind == 'text':
            self.drawTextMgr.beginNew(self.code)
        elif kind == 'line':
            self.drawLineMgr.beginNew(self.code)

    def onAppendLine(self, event, args):
        self.lines.append(event.src)

    def changeCode(self, code):
        self._reset()
        self.code = code
        q = my_orm.TextLine.select().where(my_orm.TextLine.code == code)
        for row in q:
            self.lines.append(LineView(row, self.win))
    
    def reload(self):
        if self.code:
            self.changeCode(self.code)
    
    def delLine2(self, line):
        if not line:
            return
        for i in range(len(self.lines)):
            if self.lines[i] == line:
                line.textLine.delete_instance()
                self.lines.pop(i)
                break
        self.win.invalidWindow()

    def delSelectLine(self):
        self.delLine2(self.selLine)

    def onDraw(self, hdc):
        kl = self.win.klineIndicator
        for line in self.lines:
            line.onDraw(hdc, self.selLine == line)
        if self.drawLineMgr.isDrawing():
            self.drawLineMgr.curLine.onDraw(hdc, False)

    def getLineViewByXY(self, x, y):
        kl = self.win.klineIndicator
        for i in range(len(self.lines) - 1, -1, -1):
            shape = self.lines[i].getOutShape()
            if shape and shape.isPointIn(x, y, kl):
                return self.lines[i]
        return None

    def onLButtonDown(self, x, y):
        kl = self.win.klineIndicator
        flag = self.drawTextMgr.onLButtonDown(x, y)
        flag = flag or self.drawLineMgr.onLButtonDown(x, y)
        if flag:
            return True
        # check click on LineView
        old = self.selLine
        self.selLine = self.getLineViewByXY(x, y)
        if old != self.selLine:
            self.win.invalidWindow()
        flag = self.drager.onLButtonDown(x, y, self.selLine)
        if flag:
            return True
        return False
    
    def onLButtonUp(self, x, y):
        flag = self.drawTextMgr.onLButtonUp(x, y)
        flag = flag or self.drawLineMgr.onLButtonUp(x, y)
        if flag:
            return True
        # test drag
        flag = self.drager.onLButtonUp(x, y)
        if flag:
            return True
        return False

    def onMouseMove(self, x, y):
        flag = self.drawTextMgr.onMouseMove(x, y)
        flag = flag or self.drawLineMgr.onMouseMove(x, y)
        if flag:
            return True
        # test drag
        flag = self.drager.onMouseMove(x, y)
        if flag:
            self.win.invalidWindow()
            return True
        return False

    def onDblClick(self, x, y):
        self.selLine = self.getLineViewByXY(x, y)
        if not self.selLine or self.selLine.textLine.kind != 'text':
            return False
        self.drawTextMgr.beginUpdate(self.selLine)
        self.drawTextMgr.openEditText()
        return True

    def onKeyDown(self, key):
        if key == win32con.VK_DELETE or key == win32con.VK_BACK:
            self.delLine2(self.selLine)
            self.selLine = None
            return

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg >= win32con.WM_KEYFIRST and msg <= win32con.WM_KEYLAST and self.selLine:
            if msg == win32con.WM_KEYDOWN:
                self.onKeyDown(wParam)
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

class RangeSelectorManager:
    def __init__(self, win) -> None:
        self.win = win
        self.startPos = None
        self.endPos = None
        self.captureMouse = False

    def onLButtonDown(self, x, y):
        self.captureMouse = False
        self.startPos = self._adjustXY(x, y)
        return False
    
    def _adjustXY(self, x, y):
        kl = self.win.klineIndicator
        idx = kl.getIdxAtX(x)
        if idx >= 0:
            return (kl.getCenterX(idx), y)
        return None

    def onLButtonUp(self, x, y):
        endPos = self._adjustXY(x, y) or self.endPos
        if self.captureMouse and self.startPos and endPos:
            self.endPos = endPos
            kl = self.win.klineIndicator
            idx = kl.getIdxAtX(self.startPos[0])
            eidx = kl.getIdxAtX(self.endPos[0])
            if idx > eidx:
                idx, eidx = eidx, idx
            pre = kl.data[idx - 1].close if idx > 0 else kl.data[idx].open
            data = {'startIdx': idx, 'endIdx': eidx + 1, 'pre': pre, 'datas': kl.data[idx : eidx + 1]}
            self.win.notifyListener(self.win.Event('range-selector-changed', self.win, data = data))
        else:
            self.startPos = self.endPos = None
        return self.captureMouse
    
    def onMouseMove(self, x, y):
        isBtnDown = (win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0xff00) > 0
        if not isBtnDown and self.startPos and self.endPos:
            return True
        if not isBtnDown or not self.startPos:
            self.startPos = self.endPos = None
            self.captureMouse = False
            return False
        self.captureMouse = True
        self.endPos = self._adjustXY(x, y) or self.endPos
        self.win.invalidWindow()
        return True
    
    def onDraw(self, hdc):
        if not self.captureMouse or not self.startPos or not self.endPos:
            return
        sdc = win32gui.SaveDC(hdc)
        kl = self.win.klineIndicator
        rc = (self.startPos[0] + kl.x, self.startPos[1] + kl.y, self.endPos[0] + kl.x, self.endPos[1] + kl.y)
        drawer : base_win.Drawer = self.win.drawer
        drawer.use(hdc, drawer.getPen(0x77ff77, win32con.PS_DOT))
        win32gui.MoveToEx(hdc, rc[0], rc[1])
        win32gui.LineTo(hdc, rc[2], rc[1])
        win32gui.LineTo(hdc, rc[2], rc[3])
        win32gui.LineTo(hdc, rc[0], rc[3])
        win32gui.LineTo(hdc, rc[0], rc[1])
        win32gui.RestoreDC(hdc, sdc)
    
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg >= win32con.WM_MOUSEFIRST and msg <= win32con.WM_MOUSELAST:
            kl = self.win.klineIndicator
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            x -= kl.x
            y -= kl.y
            isInK = x >= 0 and x < kl.width and y >= 0 and y < kl.height
            if not kl.visibleRange:
                return False
            if not isInK and not self.captureMouse:
                return False
            if msg == win32con.WM_LBUTTONDOWN:
                return self.onLButtonDown(x, y)
            if msg == win32con.WM_LBUTTONUP:
                return self.onLButtonUp(x, y)
            if msg == win32con.WM_MOUSEMOVE:
                return self.onMouseMove(x, y)
            return self.captureMouse
        return False

# 日龙N标记
class DayLongManager:
    def __init__(self, win) -> None:
        self.win = win
        self.code = None
        self.refCode = None
        win.addNamedListener('Ref-Model-Changed', self.onRefModelChanged)
        win.addNamedListener('K-Model-Changed', self.onKModelChanged)

    def onRefModelChanged(self, evt, args):
        self.refCode = evt.code
        self.onChanged()

    def onKModelChanged(self, evt, args):
        self.code = evt.code
        self.refCode = None

    def onChanged(self):
        if not self.code or not self.refCode:
            return

# 异动计算器
class YiDongManager:
    def __init__(self) -> None:
        self.refCode = None
        self.refs = {}

    def changeCode(self, code):
        self.refCode = self.getRefCode(code)
        if not self.refCode:
            return
        base_win.ThreadPool.instance().addTask_N(self.onLoadRef, self.refCode)

    def getRefCode(self, code):
        if not code or code[0 : 2] == '88' or code[0 : 3] == 'cls' or code == '999999' or code == '1A0001':
            return None
        refCode = None
        if code[0 : 2] == 'sz':
            code = code[2 : ]
        if code[0 : 3] == '688':
            refCode = '1B0688'
        elif code[0] == '6':
            refCode = '999999'
        elif code[0] == '0':
            refCode = '399001'
        elif code[0] == '3' and code[0 : 3] != '399':
            refCode = '399006'
        return refCode

    def onLoadRef(self, refCode):
        dm = Ths_K_DataModel(refCode)
        dm.loadNetData('day')
        if dm.data:
            self.refs[refCode] = dm

    def getRefZF(self, selDay, daysNum):
        if not self.refCode or not self.refs.get(self.refCode, None):
            return 0
        model : K_DataModel = self.refs[self.refCode]
        idx = model.getItemIdx(selDay)
        if idx < 0 or idx < daysNum:
            return 0
        pre = model.data[idx - daysNum].close
        cur = model.data[idx].close
        zf = (cur - pre) / pre * 100
        return zf

    def getZF(self, model, daysNum, idx, day):
        pre = model.data[idx - daysNum].close
        cur = model.data[idx].close
        zf = (cur - pre) / pre * 100
        refZF = self.getRefZF(day, daysNum)
        result = zf - refZF
        return result, refZF
    
    def getMaxZF(self, model, day, daysNum):
        maxZF = None
        maxZFDay = 0
        refZF = 0
        idx = model.getItemIdx(day)
        if idx < 0 or idx < daysNum:
            return None
        for i in range(daysNum):
            d, refZF = self.getZF(model, i + 1, idx, day)
            if maxZF == None or maxZF <= d:
                maxZF = d
                maxZFDay = i + 1
        if maxZF == None:
            return None
        return maxZFDay, maxZF, refZF, idx

    # return dayNum, zf, less
    def calcInfo(self, model, day, daysNum):
        info = self.getMaxZF(model, day, daysNum)
        if not info:
            return None
        maxZFDay, maxZF, refZF, idx = info
        # calc less zf
        LIMIT_ZF = (100 if daysNum == 10 else 200) + refZF
        tt = model.data[idx - maxZFDay]
        pre = model.data[idx - maxZFDay].close
        cur = model.data[idx].close
        limitPrice = LIMIT_ZF * pre / 100 + pre
        zpre = model.data[idx - 1].close
        limitTodayZF = (limitPrice - zpre) / zpre * 100
        todayZF = (cur - zpre) / zpre * 100
        lessZF = limitTodayZF - todayZF
        return maxZFDay, maxZF, lessZF

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
        self.klineIndicatorVisible = True
        self.simpleIndicator = False
        self.refIndicator = RefIndicator(self)
        self.klineIndicator = KLineIndicator(self, {'height': -1, 'margins': (30, 20)})
        self.indicators.append(self.klineIndicator)
        self.bkgnView = bkgn_view.BkGnView()
        self.marksMgr = MarksManager(self)
        self.contextMenuMgr = ContextMenuManager(self)
        self.indicatorVisibleMgr = IndicatorVisibleManager(self)
        self.lineMgr = TextLineManager(self)
        self.rangeSelMgr = RangeSelectorManager(self)
        self.dayLongMgr = DayLongManager(self)
        self.calcZdfMgr = CalcZdfManager(self)

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
            if not cf.visible:
                continue
            fixHeight += cf.getMargins(0) + cf.getMargins(1)
            if cf.config['height'] >= 0:
                fixHeight += cf.config['height']
        exHeight = max(h - fixHeight, 0)
        y = 0
        for i in range(0, len(self.indicators)):
            cf = self.indicators[i]
            if not cf.visible:
                continue
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
        if not indicator.visible:
            return False
        return (x >= indicator.x and x < indicator.x + indicator.width and
                y >= indicator.y and y < indicator.y + indicator.height)

    def getIndicatorByPoint(self, x, y):
        for it in self.indicators:
            if not it.visible:
                continue
            if self.isPointInIndicator(x, y, it):
                return it
        return None

    def changeCode(self, code, period = 'day'):
        self.selIdx = -1
        if type(code) == int:
            code = f'{code :06d}'
        if len(code) == 8 and code[0] == 's':
            code = code[2 : ]
        for it in self.indicators:
            it.changeCode(code, period)
        #rs = gn_utils.get_THS_GNTC(code)
        #if rs and rs.get('hy_2_code', None):
        #    self.refIndicator.changeCode(rs['hy_2_code'], period)
        self.lineMgr.changeCode(code)
        self.makeVisible(-1)
        self.bkgnView.changeCode(code)
        self.invalidWindow()
        ThreadPool.instance().addTask_N(self.loadClsBkGn, code)
        self.notifyListener(self.Event('ChangeCode', self, code = code))

    def loadClsBkGn(self, code):
        if code[0] not in ('0', '3', '6'):
            return
        if code[0 : 3] == '399':
            return
        obj : cls_orm.CLS_GNTC = cls_orm.CLS_GNTC.get_or_none(code = code)
        if obj and obj.updateTime and datetime.date.today() == obj.updateTime.date():
            return
        info = cls.ClsUrl().loadBkGnOfCode(code)
        if not obj:
            info.save()
        else:
            diffrents = obj.diff(info, excludeAttrNames = ['updateTime'])
            if diffrents:
                obj.updateTime = datetime.datetime.now()
                obj.save()
                rs = d_orm.createDiffBkGn(obj.code, obj.name, diffrents)
                if rs:
                    d_orm.DiffBkGnModel.bulk_create(rs, 100)
        # self.bkgnView.changeCode(code, True)

    def onContextMenu(self, x, y):
        hygnRect = getattr(self.bkgnView, 'rect', None)
        if hygnRect:
            hygnRect = self.bkgnView.getRealMaxRect(hygnRect)
        if hygnRect and x >= hygnRect[0] and x < hygnRect[2] and y >= hygnRect[1] and y < hygnRect[3]:
            self.bkgnView.onShowSettings()
            return
        it = self.getIndicatorByPoint(x, y)
        if not it:
            return
        if it.onContextMenu(x - it.x, y - it.y):
            return
        if it == self.klineIndicator:
            self.contextMenuMgr.show(x, y)
        else:
            # show or hide Indicator
            self.indicatorVisibleMgr.show(x, y)

    def onDblClick(self, x, y):
        it = self.getIndicatorByPoint(x, y)
        if it and it.onDblClick(x - it.x, y - it.y):
            return
        # default deal
        if self.selIdx > 0:
            data = self.klineIndicator.data[self.selIdx]
            self.notifyListener(self.Event('DbClick', self, code = self.klineIndicator.code, idx = self.selIdx, data = data))

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.calcIndicatorsRect()
        self.bkgnView.DEF_COLOR = 0x22cc22
        self.bkgnView.hwnd = self.hwnd

    def onSize(self):
        self.makeVisible(self.selIdx)
        W, H = self.getClientSize()
        w = W - 200 # int(W * 0.7)
        self.bkgnView.rect = (0, 0, w, 80)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if self.lineMgr.winProc(hwnd, msg, wParam, lParam):
            return True
        if self.calcZdfMgr.winProc(hwnd, msg, wParam, lParam):
            return True
        if self.rangeSelMgr.winProc(hwnd, msg, wParam, lParam):
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
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onDblClick(x, y)
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
            if it.visible:
                it.onMouseLeave()
        self.invalidWindow()

    def onMouseClick(self, x, y):
        hygnRect = getattr(self.bkgnView, 'rect', None)
        if hygnRect and x >= hygnRect[0] and x < hygnRect[2] and y >= hygnRect[1] and y < hygnRect[3]:
            ok = self.bkgnView.onClick(x, y)
            if ok:
                return True
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
        self.bkgnView.changeLastDay(item.day)
        self.notifyListener(Listener.Event('selIdx-Changed', self, idx = idx, day = item.day, data = item, datas = self.klineIndicator.data))
        self.invalidWindow()

    def setSelDay(self, day):
        if not day:
            return
        idt = self.klineIndicator
        idx = idt.model.getItemIdx(day)
        self.makeVisible(idx)
        self.setSelIdx(idx)

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
            peroid = ks[idx]
            if self.klineIndicator.code:
                self.changeCode(self.klineIndicator.code, peroid)

    def makeVisible(self, idx):
        self.calcIndicatorsRect()
        ids = self.indicators[ : ]
        ids.append(self.refIndicator)
        for idt in ids:
            it : Indicator = idt
            it.calcVisibleRange(idx)
            vr = it.visibleRange
            if vr:
                it.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        if not self.klineIndicator.visibleRange:
            return
        w, h = self.getClientSize()
        # draw background
        for i, idt in enumerate(self.indicators):
            if not idt.visible:
                continue
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.drawBackground(hdc, self.drawer)
            y = idt.height + idt.getMargins(1)
            pw = 2 if i == 0 else 1
            self.drawer.drawLine(hdc, 0, y, w, y, 0x0000aa, width = pw)
            win32gui.RestoreDC(hdc, sdc)
        # draw Hilights
        for i, idt in enumerate(self.indicators):
            if not idt.visible:
                continue
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            if idt == self.klineIndicator:
                self.marksMgr.onDraw(hdc, self.drawer) # draw marks
            idt.drawIdxHilight(hdc, self.drawer, self.selIdx)
            win32gui.RestoreDC(hdc, sdc)
        self.bkgnView.onDrawRect(hdc, self.bkgnView.rect)
        # draw content
        if self.refIndicatorVisible:
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, self.refIndicator.x, self.refIndicator.y)
            self.refIndicator.draw(hdc, self.drawer)
            win32gui.RestoreDC(hdc, sdc)
        for i, idt in enumerate(self.indicators):
            if idt == self.klineIndicator and not self.klineIndicatorVisible:
                continue
            if not idt.visible:
                continue
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.draw(hdc, self.drawer)
            win32gui.RestoreDC(hdc, sdc)
        # draw lines
        sdc = win32gui.SaveDC(hdc)
        win32gui.SetViewportOrgEx(hdc, self.klineIndicator.x, self.klineIndicator.y)
        self.lineMgr.onDraw(hdc)
        win32gui.RestoreDC(hdc, sdc)
        # draw mouse
        if self.mouseXY and not self.lineMgr.isSelected():
            mx, my = self.mouseXY
            idt = self.getIndicatorByPoint(*self.mouseXY)
            if idt:
                sdc = win32gui.SaveDC(hdc)
                win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
                idt.drawMouse(hdc, self.drawer, mx - idt.x, my - idt.y)
                win32gui.RestoreDC(hdc, sdc)
        self.drawHeaderTip(hdc)
        self.drawer.drawLine(hdc, w - self.RIGHT_MARGIN + 10, 0, w - self.RIGHT_MARGIN + 10, h, 0x0000aa)
        # draw select range
        self.rangeSelMgr.onDraw(hdc)
        self.calcZdfMgr.onDraw(hdc)

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
        super().onDestory()

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
        def V(c, visible = True):
            return {'visible': IndicatorVisibleManager.getIndicatorVisible(c, visible)}
        win = KLineWindow()
        win.addIndicator(RateIndicator(win, {'height': 60, 'margins': (15, 2)}))
        win.addIndicator(AmountIndicator(win, {'height': 60, 'margins': (10, 2)}))
        win.addIndicator(DayIndicator(win))
        win.addIndicator(ScqxIndicator(win))
        win.addIndicator(LsAmountIndicator(win))
        win.addIndicator(HotIndicator(win))
        win.addIndicator(Amount2Indicator(win, V(Amount2Indicator, False)))
        win.addIndicator(ThsZT_Indicator(win))
        win.addIndicator(ClsZT_Indicator(win))
        win.addIndicator(ZhangSuIndicator(win, V(ZhangSuIndicator, False)))
        win.addIndicator(LhbIndicator(win, V(LhbIndicator)))
        win.addIndicator(GnLdIndicator(win, V(GnLdIndicator, False)))
        win.addIndicator(Code_ZT_NumIndicator(win, V(Code_ZT_NumIndicator, False)))
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
        self.rangeSelData = None
        self.klineWin = klineWin
        self.yiDongMgr = YiDongManager()
        klineWin.addNamedListener('selIdx-Changed', self.onSelIdxChanged)
        klineWin.addNamedListener('range-selector-changed', self.onRangeSelectorChanged)
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
            rz = int(self.basicData.get('市盈率_静', 0) or 0)
            self.drawer.drawText(hdc, str(rz or '--'), (RIGHT_X + 10, y, W, y + RH), (0xcccccc if rz >= 0 else 0x00ff00), self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '市盈率_TTM', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        if self.basicData:
            rz = int(self.basicData.get('市盈率_TTM', 0) or 0)
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
        # 异动
        y += RH
        rz = self.getYiDongInfo(klineModel, 10)
        if rz is not None:
            self.drawer.drawText(hdc, f'{rz[0]}日异动', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
            self.drawer.drawText(hdc, f'{rz[1] :.1f}% ({rz[2] :.1f}%)', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        rz = self.getYiDongInfo(klineModel, 30)
        if rz is not None:
            self.drawer.drawText(hdc, f'{rz[0]}日异动', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
            self.drawer.drawText(hdc, f'{rz[1] :.1f}% ({rz[2] :.1f}%)', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        # 区间统计
        if not self.rangeSelData:
            return
        y += RH
        self.drawer.drawLine(hdc, 5, y, W - 5, y, 0x606060)
        y += 3
        self.drawer.drawText(hdc, '区间统计', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER | win32con.DT_CENTER)
        y += RH
        sdatas = self.rangeSelData['datas']
        pre = self.rangeSelData['pre']
        self.drawer.drawText(hdc, '日期数', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        self.drawer.drawText(hdc, f'{len(sdatas)} 日', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '涨幅', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        zf = (sdatas[-1].close -  pre) / pre * 100
        # color = 0x0000E6 if zf >= 0 else 0x00E600
        self.drawer.drawText(hdc, f'{int(zf)} %', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '最大涨幅', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        maxVal, minVal = 0, 10000000
        totalRate = 0
        for it in sdatas:
            maxVal = max(maxVal, it.high)
            minVal = min(minVal, it.low)
            totalRate += it.rate
        if zf > 0:
            mzf = (maxVal -  pre) / pre * 100
        else:
            mzf = (minVal -  pre) / pre * 100
        # color = 0x0000E6 if zf >= 0 else 0x00E600
        self.drawer.drawText(hdc, f'{int(mzf)} %', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        self.drawer.drawText(hdc, '总换手率', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        self.drawer.drawText(hdc, f'{int(totalRate)} %', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        y += RH
        totalAmount = int(sum([d.amount for d in sdatas]) / 100000000)
        self.drawer.drawText(hdc, '总成交额', (LEFT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)
        self.drawer.drawText(hdc, f'{totalAmount} 亿', (RIGHT_X, y, W, y + RH), 0xcccccc, self.V_CENTER)

    def getModelAttr(self, model, attrName):
        if not self.selData or not model:
            return None
        day = self.selData.day
        idx = model.getItemIdx(day)
        if idx >= 0:
            return getattr(model.data[idx], attrName, None)
        return None

    def loadCodeBasic(self, code):
        if code[0 : 2] == '88':
            obj = ths_orm.THS_ZS.get_or_none(ths_orm.THS_ZS.code == code)
            if obj : self.basicData = obj.__data__
        else:
            #from download import cls
            url = cls.ClsUrl()
            self.basicData = url.loadBasic(code)
            # obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
            # if obj: self.basicData = obj.__data__
        self.invalidWindow()

    def changeCode(self, code):
        scode = f'{code :06d}' if type(code) == int else code
        if (self.curCode == scode) or (not scode):
            return
        self.curCode = scode
        self.basicData = None
        self.yiDongMgr.changeCode(scode)
        base_win.ThreadPool.instance().addTask_N(self.loadCodeBasic, scode)

    def onSelIdxChanged(self, evt, args):
        self.selData = evt.data
        self.rangeSelData = None
        self.invalidWindow()

    def onRangeSelectorChanged(self, evt, args):
        self.rangeSelData = evt.data
        self.invalidWindow()

    def getYiDongInfo(self, klineModel, daysNum):
        if not klineModel or not klineModel.data or not self.selData:
            return None
        day = self.selData.day
        info = self.yiDongMgr.calcInfo(klineModel, day, daysNum)
        return info

class KLineCodeWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x101010
        self.layout = None
        self.klineWin = KLineWindow.createDefault()
        self.codeWin = CodeWindow(self.klineWin)
        self.codeList = None
        self.code = None
        self.idxCodeList = -1
        self.idxCodeWin = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        DETAIL_WIDTH = 180
        self.layout = base_win.GridLayout(('100%', ), ('1fr', DETAIL_WIDTH), (5, 5))
        self.klineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.klineWin)

        rightLayout = base_win.FlowLayout()
        self.codeWin.createWindow(self.hwnd, (0, 0, DETAIL_WIDTH, 550))
        rightLayout.addContent(self.codeWin, {'margins': (0, 5, 0, 5)})
        btn = base_win.Button({'title': '<<', 'name': 'LEFT'})
        btn.createWindow(self.hwnd, (0, 0, 40, 30))
        btn.addNamedListener('Click', self.onLeftRight)
        rightLayout.addContent(btn, {'margins': (0, 10, 0, 0)})
        self.idxCodeWin = base_win.Label()
        self.idxCodeWin.createWindow(self.hwnd, (0, 0, 100, 30))
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

    def _getDay(self, d):
        if type(d) == dict and 'day' in d:
            return d['day']
        return None

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
        day = self._getDay(cur)
        if day:
            self.klineWin.marksMgr.clearMarkDay()
            self.klineWin.marksMgr.setMarkDay(day)
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
            self.notifyListener(self.Event('ChangeCode', self, code = code))
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
    #         [ {'code':xxx, 'day': xx}, ... ]  | [ {'secu_code':xxx, }, ... ]
    def setCodeList(self, codes, curIdx = -1):
        if not codes:
            return
        self.codeList = codes
        if curIdx < 0:
            curIdx = self._findIdx()
        self.idxCodeList = curIdx
        self.updateCodeIdxView()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_ACTIVATE and self.klineWin.hwnd:
            ac = wParam & 0xffff
            # if ac == win32con.WA_INACTIVE and self.klineWin.hwnd:
                # win32gui.SetFocus(self.klineWin.hwnd)
            # return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    import kline_utils
    CODE = '600172' #      1B0688 002202
    win = kline_utils.createKLineWindowByCode(CODE)
    win.changeCode(CODE)
    win.setCodeList([CODE, '002792', '002149', '002565', '301079', '300058', '688523'])
    win.mainWin = True
    win32gui.PumpMessages()