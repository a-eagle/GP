import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, traceback
import os, sys, requests, json
import win32gui, win32con

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import datafile, cls, ths_iwencai
from orm import d_orm, ths_orm, cls_orm
from ui import fx, base_win

def getTypeByCode(code):
    if not code:
        return None
    if type(code) == int:
        code = f'{code :06d}'
    if type(code) != str:
        return None
    if code[0] in ('0', '3', '6'):
        return 'cls'
    if code[0 : 2] in ('sz', 'sh'):
        return 'cls'
    if code[0 : 3] == 'cls':
        return 'cls'
    return 'ths'

class TimelineModel:
    ONE_DAY_LINES = 241

    def __init__(self) -> None:
        self.priceRange = None
        self.volRange = None
        self.amountRange = None
        self.dataModel = None
        self.refDataModel = None
        self.clsHotTcList = None # only used for ZS ( CLS_HotTc )

    # day = int | str
    def load(self, code, day):
        if type(code) == int:
            code = f'{code :06d}'
        if code[0 : 2] in ('sz', 'sh'):
            code = code[2 : ]
        if getTypeByCode(code) == 'cls':
            self.dataModel = datafile.Cls_T_DataModel(code)
        else:
            self.dataModel = datafile.Ths_T_DataModel(code)
        self.dataModel.loadData(day)
        self.loadClsHotTc(day)

    def loadRef(self, code, day):
        if type(code) == int:
            code = f'{code :06d}'
        if getTypeByCode(code) == 'cls':
            self.refDataModel = datafile.Cls_T_DataModel(code)
        else:
            self.refDataModel = datafile.Ths_T_DataModel(code)
        self.refDataModel.loadData(day)

    def loadClsHotTc(self, day):
        if not self.refDataModel or not self.refDataModel.name:
            return
        day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        rs = []
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.name == self.refDataModel.name, cls_orm.CLS_HotTc.day == day)
        for q in qr:
            rs.append(q.__data__)
        self.clsHotTcList = rs

    # name = 'price' | 'vol' | 'amount'
    def calcAttrRange(self, dataModel, name):
        if not dataModel or not dataModel.data:
            return None
        minVal = maxVal = -1
        for dt in dataModel.data:
            v = getattr(dt, name)
            if not v: continue
            if minVal < 0 and maxVal < 0:
                maxVal = minVal = v
            else:
                minVal = min(minVal, v)
                maxVal = max(maxVal, v)
        if name != 'price':
            return (minVal, maxVal)
        maxVal = max(dataModel.pre, maxVal)
        minVal = min(dataModel.pre, minVal)
        ds = max(abs(maxVal - dataModel.pre), abs(minVal - dataModel.pre))
        maxVal = dataModel.pre + ds
        minVal = dataModel.pre - ds
        zf = (maxVal - dataModel.pre) / dataModel.pre
        return (minVal, maxVal, zf)

    def getPriceRange(self):
        if self.priceRange:
            return self.priceRange
        rg1 = self.calcAttrRange(self.dataModel, 'price')
        rg2 = self.calcAttrRange(self.refDataModel, 'price')
        if not rg1:
            return None
        if rg2 and rg2[2] > rg1[2]: # 指数涨幅较大
            ds = self.dataModel.pre * rg2[2]
            rg1 = (self.dataModel.pre + ds, self.dataModel.pre - ds)
        self.priceRange = (rg1[0], rg1[1], self.dataModel.pre)
        return self.priceRange

    def getVolRange(self):
        if self.volRange:
            return self.volRange
        self.volRange = self.calcAttrRange(self.dataModel, 'vol')
        return self.volRange
    
    def getAmountRange(self):
        if self.amountRange:
            return self.amountRange
        self.amountRange = self.calcAttrRange(self.dataModel, 'amount')
        return self.amountRange

class ContextMenuMgr:
    def __init__(self, win) -> None:
        self.win = win

    def onContextMenu(self):
        mm = [
            {'title': '叠加指数 THS', 'name': 'add-ref-ths-zs', 'sub-menu': self.getRefThsZsModel},
            {'title': '叠加指数 CLS', 'name': 'add-ref-cls-zs', 'sub-menu': self.getRefClsZsModel},
        ]
        menu = base_win.PopupMenu.create(self.win.hwnd, mm)
        x, y = win32gui.GetCursorPos()
        menu.addNamedListener('Select', self.onMenuItem)
        menu.show(x, y)

    def onMenuItem(self, evt, args):
        name = evt.item['name']
        if name == 'add-ref-ths-zs' or name == 'add-ref-cls-zs':
            code = evt.item['code']
            self.win.loadRef(code)
            self.win.invalidWindow()

    def getRefThsZsModel(self, item):
        model = []
        if not self.win.model.dataModel:
            return model
        code = self.win.model.dataModel.code
        if len(code) == 8:
            code = code[2 : ]
        obj : ths_orm.THS_GNTC = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if not obj:
            return model
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
    
    def getRefClsZsModel(self, item):
        model = []
        if not self.win.model.dataModel:
            return model
        code = self.win.model.dataModel.code
        if len(code) == 8:
            code = code[2 : ]
        obj : cls_orm.CLS_GNTC = cls_orm.CLS_GNTC.get_or_none(cls_orm.CLS_GNTC.code == code)
        if not obj:
            return model
        if obj.hy:
            hys = obj.hy.split(';')
            hycs = obj.hy_code.split(';')
            for i in range(len(hys)):
                if hycs[i].strip():
                    model.append({'title': hys[i], 'code': hycs[i]})
        model.append({'title': 'LINE'})
        if not obj.gn_code:
            return model
        gn_codes = obj.gn_code.split(';')
        gn_names = obj.gn.split(';')
        for i in range(len(gn_codes)):
            if gn_codes[i].strip():
                model.append({'title': gn_names[i], 'code': gn_codes[i].strip()})
        return model

class TimelineWindow(base_win.BaseWindow):
    ONE_DAY_LINES = 241

    def __init__(self) -> None:
        super().__init__()
        self.model = None
        self.mouseXY = None
        self.topTipRect = None
        self.priceRect = None
        self.timeTipRect = None
        self.volRect = None
        self.bottomTipRect = None
        self.hilights = []
        self.cttMenuMgr = ContextMenuMgr(self)

    def load(self, code, day = None):
        self.model = TimelineModel()
        self._day = day
        base_win.ThreadPool.instance().addTask_N(self._load, code)

    def _load(self, code):
        self.model.load(code, self._day)
        self.model.priceRange = None # re-calc
        self.initHilights()
        title = f'{self.model.dataModel.code}   {self.model.dataModel.name}'
        win32gui.SetWindowText(self.hwnd, title)
        self.invalidWindow()

    def loadRef(self, code):
        base_win.ThreadPool.instance().addTask_N(self._loadRef, code)

    def _loadRef(self, code):
        self.model.loadRef(code, self._day)
        self.model.priceRange = None # re-calc
        self.invalidWindow()

    def initHilights(self):
        self.hilights.clear()
        fxc = fx.FenXiCode(self.model.dataModel.code)
        fxc.mdf = self.model.dataModel
        fxc.calcOneDay(self.model.dataModel.day, False)
        for x in fxc.results:
            self.addHilight(x['fromMinute'], x['endMinute'], x)
        self.invalidWindow()

    def getYAtPrice(self, price):
        priceRange = self.model.getPriceRange()
        if not priceRange:
            return 0
        h = self.priceRect[3] - self.priceRect[1]
        p = (price - priceRange[0]) / (priceRange[1] - priceRange[0])
        y = h - int(p * h) + self.priceRect[1]
        return y
    
    def getYAtVol(self, vol):
        volRange = self.model.getVolRange()
        h = self.volRect[3] - self.volRect[1]
        if not volRange or volRange[0] == volRange[1]:
            return self.volRect[3] - 1
        p = (vol - volRange[0]) / (volRange[1] - volRange[0])
        y = h - int(p * h) + self.volRect[1]
        return y

    def getXAtMinuteIdx(self, minuteIdx):
        w = self.priceRect[2] - self.priceRect[0]
        p = w / self.ONE_DAY_LINES
        if minuteIdx == self.ONE_DAY_LINES:
            return self.priceRect[2]
        return int(minuteIdx * p) + self.priceRect[0]

    def getPriceAtY(self, y):
        if y <= self.priceRect[1] or y >= self.priceRect[3]:
            return None
        y -= self.priceRect[1]
        pr = self.model.getPriceRange()
        if not pr or pr[0] == pr[1]:
            return None
        h = self.priceRect[3] - self.priceRect[1]
        p = pr[1] - (y / h) * (pr[1] - pr[0])
        return p

    def getMinuteIdxAtX(self, x):
        if x < self.priceRect[0]:
            x = self.priceRect[0]
        elif x > self.priceRect[2]:
            x = self.priceRect[2]
        x -= self.priceRect[0]
        cw = self.priceRect[2] - self.priceRect[0]
        p = cw / self.ONE_DAY_LINES
        x += p / 2
        idx = int(x / p)
        if idx >= len(self.model.dataModel.data):
            idx = len(self.model.dataModel.data) - 1
        return idx
    
    def formatAmount(self, amount):
        if amount >= 100000000:
            amount /= 100000000
            return f'{amount :.2f}亿'
        amount = int(amount / 10000)
        return f'{amount}万'

    def drawBackground(self, hdc):
        if not self.model:
            return
        # draw vertical line
        for i in range(1, 8):
            idx = i * 30
            x = self.getXAtMinuteIdx(idx)
            style = win32con.PS_SOLID if i % 4 == 0 else win32con.PS_DOT
            self.drawer.drawLine(hdc, x, self.priceRect[1], x, self.priceRect[3], 0x36332E, style)
            self.drawer.drawLine(hdc, x, self.volRect[1], x, self.volRect[3], 0x36332E, style)
        # draw horizontal line
        pr = self.model.getPriceRange()
        if not pr:
            return
        W, H = self.getClientSize()
        ph = (pr[1] - pr[0]) / 4
        ps = (pr[1], pr[1] - ph, pr[2], pr[2] - ph, pr[0])
        for i, price in enumerate(ps):
            y = self.getYAtPrice(price)
            style = win32con.PS_SOLID if i % 2 == 0 else win32con.PS_DOT
            psWidth = 2 if i == 2 else 1
            lc = 0x36332E
            if i >= 1 and i <= 3:
                self.drawer.drawLine(hdc, self.priceRect[0], y, self.priceRect[2], y, lc, style = style, width = psWidth)
            color = 0x0000ff if price >= pr[2] else 0x00ff00
            zf = (price - pr[2]) / pr[2] * 100
            p2 = f'{zf :.02f}%'
            rc = (self.priceRect[2] + 5, y - 8, W, y + 8)
            self.drawer.drawText(hdc, p2, rc, color, align = win32con.DT_LEFT)
        self.drawer.drawRect(hdc, self.priceRect, 0x36332E)

        # draw vol lines
        am = self.model.getAmountRange()
        rc = (self.volRect[2] + 5, self.volRect[1] - 8, W, self.volRect[1] + 8)
        self.drawer.drawText(hdc, self.formatAmount(am[1]), rc, 0x993322, align = win32con.DT_LEFT)
        y = self.volRect[1] + (self.volRect[3] - self.volRect[1]) // 2
        self.drawer.drawLine(hdc, self.volRect[0], y, self.volRect[2], y, 0x36332E, style = win32con.PS_DOT)
        self.drawer.drawRect(hdc, self.volRect, 0x36332E)

    def minuteToIdx(self, minute):
        if minute <= 930:
            return 0
        hour = minute // 100
        minute = minute % 100
        ds = 0
        if hour <= 11:
            ds = 60 * (hour - 9) + minute - 30
            return ds
        ds = 120
        ds += minute + (hour - 13) * 60
        return ds

    def drawHilight(self, hdc):
        if not self.model:
            return
        sdc = win32gui.SaveDC(hdc)
        for fe in self.hilights:
            f, e, info = fe
            sx = self.getXAtMinuteIdx(self.minuteToIdx(f))
            ex = self.getXAtMinuteIdx(self.minuteToIdx(e))
            H_COLOR = 0x101010
            self.drawer.fillRect(hdc, (sx, self.priceRect[1] + 1, ex + 1, self.priceRect[3] - 1), H_COLOR)
            txtRc = (sx, self.priceRect[3] - 20, sx + 60, self.priceRect[3])
            text = f'{info["zf"] :.1f}%'
            self.drawer.drawText(hdc, text, txtRc, color = 0xe0abce, align = win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)
            
    def addHilight(self, fromMinute, endMinute, info):
        fe = (fromMinute, endMinute, info)
        self.hilights.append(fe)

    def drawMouse(self, hdc):
        if not self.mouseXY or not self.model:
            return
        W, H = self.getClientSize()
        x, y = self.mouseXY
        idx = self.getMinuteIdxAtX(x)
        if idx < 0:
            return
        # vertical line
        x = self.getXAtMinuteIdx(idx)
        self.drawer.drawLine(hdc, x, self.priceRect[1] + 1, x, self.priceRect[3] - 1, 0x905090, style = win32con.PS_DOT)
        self.drawer.drawLine(hdc, x, self.volRect[1] + 1, x, self.volRect[3] - 1, 0x905090, style = win32con.PS_DOT)
        md = self.model.dataModel.data[idx]
        tips = f'{self.formatAmount(md.amount)}元'
        rc = (x - 50, self.bottomTipRect[1] + 5, x + 50, self.bottomTipRect[3])
        self.drawer.drawText(hdc, tips, rc, 0xf06050)
        # draw time
        ts = f'{md.time // 100}:{md.time % 100 :02d}'
        rc = (x - 30, self.timeTipRect[1] + 5, x + 30, self.timeTipRect[3])
        self.drawer.fillRect(hdc, rc, self.css['bgColor'])
        self.drawer.drawText(hdc, ts, rc, color = 0xf06050, align = win32con.DT_CENTER)
        # horizontal line
        price = self.getPriceAtY(y)
        if not price:
            return
        zf = (price - self.model.dataModel.pre) / self.model.dataModel.pre * 100
        self.drawer.drawLine(hdc, self.priceRect[0], y, self.priceRect[2], y, 0x905090, style = win32con.PS_DOT)
        rc = (self.priceRect[2] + 5, y - 10, W, y + 10)
        self.drawer.fillRect(hdc, rc, 0)
        self.drawer.drawText(hdc, f'{zf :.2f}%', rc, 0xf06050, win32con.DT_LEFT)

    def drawMinites(self, hdc):
        if not self.model or not self.model.dataModel or not self.model.dataModel.data:
            return
        datas = self.model.dataModel.data
        self.drawer.use(hdc, self.drawer.getPen(0xffffff))
        for i, md in enumerate(datas):
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx)
            y = self.getYAtPrice(md.price)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)
        first = datas[0]
        if not hasattr(first, 'avgPrice'):
            return
        self.drawer.use(hdc, self.drawer.getPen(0x00ffff))
        for i, md in enumerate(datas):
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx)
            y = self.getYAtPrice(md.avgPrice)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)

    def drawRefMinites(self, hdc):
        if not self.model.refDataModel or not self.model.refDataModel.data:
            return
        self.drawer.use(hdc, self.drawer.getPen(0xff2222))
        yz = self.model.refDataModel.pre / self.model.dataModel.pre
        for i, md in enumerate(self.model.refDataModel.data):
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx)
            y = self.getYAtPrice(md.price / yz)
            if i == 0:
                win32gui.MoveToEx(hdc, x, y)
            else:
                win32gui.LineTo(hdc, x, y)
        info = f'{self.model.refDataModel.name}  {self.model.refDataModel.code}'
        self.drawer.drawText(hdc, info, (self.topTipRect[0], 10, 250, self.topTipRect[3]), align = win32con.DT_LEFT )
    
    def drawRefClsHotTc(self, hdc):
        if not self.model.refDataModel or not self.model.refDataModel.data:
            return
        if not self.model.clsHotTcList:
            return
        for it in self.model.clsHotTcList:
            itime = int(it['ctime'].replace(':', '')[0 : 4])
            idx = self.minuteToIdx(itime)
            x = self.getXAtMinuteIdx(idx)
            color = 0x2233ff if it['up'] else 0x23ff33
            self.drawer.use(hdc, self.drawer.getBrush(color))
            self.drawer.use(hdc, self.drawer.getPen(color))
            X_HLF, Y_HLF = 4, 6
            SY = self.priceRect[3] + 4
            pts = [(x - X_HLF, SY + Y_HLF), (x + X_HLF, SY + Y_HLF), (x, SY)]
            win32gui.Polygon(hdc, pts)

    def _getVolLineColor(self, idx):
        now = self.model.dataModel.data[idx].price
        if idx == 0:
            pre = self.model.dataModel.pre
        else:
            pre = self.model.dataModel.data[idx - 1].price
        if now > pre:
            return 0x0000dd
        if now == pre:
            return 0xdddddd
        return 0x00dd00

    def drawVol(self, hdc):
        for i, md in enumerate(self.model.dataModel.data):
            idx = self.minuteToIdx(md.time)
            x = self.getXAtMinuteIdx(idx)
            y = self.getYAtVol(md.vol)
            self.drawer.use(hdc, self.drawer.getPen(self._getVolLineColor(i)))
            win32gui.MoveToEx(hdc, x, self.volRect[3] - 1)
            win32gui.LineTo(hdc, x, y)

    def onDraw(self, hdc):
        if not self.model or not self.model.dataModel or not self.model.dataModel.data:
            return
        self.drawHilight(hdc)
        self.drawBackground(hdc)
        self.drawMouse(hdc)
        self.drawRefMinites(hdc)
        self.drawMinites(hdc)
        self.drawVol(hdc)
        self.drawRefClsHotTc(hdc)

    def onContextMenu(self, x, y):
        self.cttMenuMgr.onContextMenu()

    def onSize(self):
        W, H = self.getClientSize()
        PL, PR = 45, W - 60
        self.topTipRect = (PL, 0, PR, 40)
        self.bottomTipRect = (PL, H - 35, PR, H)
        self.volRect = (PL, self.bottomTipRect[1] - 160, PR, self.bottomTipRect[1])
        self.timeTipRect = (PL, self.volRect[1] - 30, PR, self.volRect[1])
        self.priceRect = (PL, self.topTipRect[3], PR, self.timeTipRect[1])

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            y, x = (lParam >> 16) & 0xffff,(lParam & 0xffff)
            self.mouseXY = (x, y)
            if self.model:
                win32gui.InvalidateRect(hwnd, None, True)
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onContextMenu(x, y)
            return True
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.onSize()
        return super().winProc(hwnd, msg, wParam, lParam)

class PanKouWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.data = None

    # day = str | int
    def load(self, code, day):
        base_win.ThreadPool.instance().addTask_N(self._load, code, day)
    
    def _load(self, code, day):
        if type(day) == int:
            day = str(day)
        if len(day) == 8:
            day = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
        tdays = ths_iwencai.getTradeDays()
        if tdays[-1] == day.replace('-', ''):
            url = cls.ClsUrl()
            self.data = url.loadPanKou5(code)
        else:
            obj = d_orm.ZT_PanKou.get_or_none(day = day, code = code)
            if obj and obj.info:
                self.data = json.loads(obj.info)
        self.invalidWindow()

    def onDraw(self, hdc):
        if not self.data:
            return
        W, H = self.getClientSize()
        VCENTER = win32con.DT_VCENTER | win32con.DT_SINGLELINE
        CENTER = VCENTER | win32con.DT_CENTER
        RH = 25
        pre = self.data.get('preclose_px', 0)
        for i in range(10):
            if i < 5:
                idx = str(5 - i)
                px = self.data.get(f's_px_{idx}', 0)
                amount = self.data.get(f's_amount_{idx}', 0)
            else:
                idx = str(i - 4)
                px = self.data.get(f'b_px_{idx}', 0)
                amount = self.data.get(f'b_amount_{idx}', 0)
            amount *= px * 100
            if amount >= 100000000:
                famount = f'{amount / 100000000 :.2f}亿'
            else:
                famount = f'{amount / 10000 :.1f}万'
            ipx = int(px * 100 + 0.5)
            fpx = f'{ipx // 100}.{ipx % 100}'
            idxColor = 0x0000ff if px >= pre else 0x00ff00
            valColor = 0xF4E202
            self.drawer.drawText(hdc, str(idx), (5, RH * i, 20, RH * i + RH), idxColor, VCENTER)
            if ipx > 0:
                self.drawer.drawText(hdc, fpx, (40, RH * i, 90, RH * i + RH), idxColor, VCENTER)
            if amount > 0:
                self.drawer.drawText(hdc, famount, (60, RH * i, W - 10, RH * i + RH), valColor, VCENTER | win32con.DT_RIGHT)
            if i == 4:
                self.drawer.drawLine(hdc, 0, RH * i + RH, W, RH * i + RH, 0x909090)

class TimelinePanKouWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.timelineWin = None
        self.pankouWin = None
        self.css['bgColor'] = 0x202020
    
    def createWindow(self, parentWnd, rect, style= win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.layout = base_win.GridLayout(('1fr', ), ('1fr', 200), (5, 5))
        self.timelineWin = TimelineWindow()
        self.timelineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.pankouWin = PanKouWindow()
        self.pankouWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.timelineWin)
        self.layout.setContent(0, 1, self.pankouWin)
        win32gui.PostMessage(self.hwnd, win32con.WM_SIZE, 0, 0)

    # day = str | int
    def load(self, code, day):
        self.timelineWin.load(code, day)
        self.pankouWin.load(code, day)

    def loadRef(self, code):
        self.timelineWin.loadRef(code)

if __name__ == '__main__':
    win = TimelinePanKouWindow()
    win.createWindow(None, (0, 0, 1000, 600), win32con.WS_OVERLAPPEDWINDOW| win32con.WS_VISIBLE)
    win.load('301016', 20250403) # cls82437 sh000001 ; 300390  600611
    win.loadRef('cls82437') 
    win32gui.PumpMessages()