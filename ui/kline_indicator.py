import os, sys, functools, copy, datetime, json, time, traceback
import win32gui, win32con
import requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download.datafile import *
from ui.base_win import *
from utils import hot_utils, gn_utils
from download import cls, henxin
from orm import d_orm, ths_orm, lhb_orm, cls_orm

def getTypeByCode(code):
    if not code:
        return None
    if type(code) == int:
        code = f'{code :06d}'
    if type(code) != str:
        return None
    if code[0] in ('0', '3', '6'): # , '8'
        return 'ths'
    if code[0 : 2] in ('sh', 'sz'):
        return 'cls'
    if code[0 : 3] == 'cls':
        return 'cls'
    return 'ths'

def getNameByCode(code):
    if not code:
        return None
    if type(code) == int:
        code = f'{code :06d}'
    if code[0 : 2] in ('sz', 'sh'):
        code = code[2 : ]
    if code[0] in ('0', '3', '6'):
        obj = gn_utils.get_THS_GNTC(code)
        return obj['name'] if obj else ''
    elif code[0 : 3] == 'cls':
        obj = cls_orm.CLS_ZS.get_or_none(code = code)
        return obj.name if obj else ''
    elif code[0] == '8':
        obj = ths_orm.THS_ZS.get_or_none(code = code)
        return obj.name if obj else ''
    return ''

# 指标 Vol, Amount, Rate等
class Indicator:
    # config = { height: int 必填
    #            margins: (top, bottom)  可选
    #            name: ''
    #            title: 'xx'
    #        }
    def __init__(self, win, config = None) -> None:
        self.win = win
        self.config = config or {}
        self.data = None
        self.period = None
        self.valueRange = None
        self.visibleRange = None
        self.width = 0
        self.height = 0
    
    def getItemData(self, idx):
        if idx >= 0 and self.data and idx < len(self.data):
            return self.data[idx]
        return None

    def changeCode(self, code, period):
        self.code = code
        self.valueRange = None
        self.visibleRange = None
        self.period = period

    def calcValueRange(self, fromIdx, endIdx):
        pass

    def getYAtValue(self, value):
        if not self.valueRange:
            return 0
        if value < self.valueRange[0]:
            value = self.valueRange[0]
        elif value > self.valueRange[1]:
            value = self.valueRange[1]
        if self.valueRange[1] == self.valueRange[0]:
            return 0
        p = self.height * (value - self.valueRange[0]) / (self.valueRange[1] - self.valueRange[0])
        y = self.height - int(p)
        return y

    def getValueAtY(self, y):
        pass

    def getColor(self, idx, data):
        if getattr(data ,'close', 0) >= getattr(data ,'open', 0):
            return 0x0000ff
        return 0xfcfc54

    def draw(self, hdc, drawer):
        pass

    def drawBackground(self, hdc, drawer):
        pass

    def drawIdxHilight(self, hdc, drawer, idx):
        if not self.visibleRange:
            return
        if idx < 0 or idx >= self.visibleRange[1] or idx < self.visibleRange[0]:
            return
        x = self.getCenterX(idx)
        sx = x - self.getItemWidth() // 2 #- self.getItemSpace()
        ex = x + self.getItemWidth() // 2 #+ self.getItemSpace()
        if ex <= sx:
            ex = sx + 2
        rc = (sx, 1, ex, self.height + self.getMargins(1))
        drawer.fillRect(hdc, rc, 0x202020)

    def drawMouse(self, hdc, drawer, x, y):
        pass

    def getItemWidth(self):
        return self.win.klineWidth

    def getItemSpace(self):
        return self.win.klineSpace

    def getVisibleNum(self):
        return self.width // (self.getItemWidth() + self.getItemSpace())
    
    def getMargins(self, idx):
        cf = self.config.get('margins', None)
        if cf and idx >= 0 and idx < len(cf):
            return cf[idx]
        return 0

    def getCenterX(self, idx):
        if not self.visibleRange:
            return -1
        if idx < self.visibleRange[0] or idx > self.visibleRange[1]:
            return -1
        i = idx - self.visibleRange[0]
        x = i * (self.getItemWidth() + self.getItemSpace())
        x += self.getItemWidth() // 2
        return x
    
    def getIdxAtX(self, x):
        if not self.visibleRange:
            return -1
        if x <= 0 or x >= self.width:
            return -1
        idx = x // (self.getItemWidth() + self.getItemSpace())
        idx += self.visibleRange[0]
        if idx >= len(self.data) or idx >= self.visibleRange[1]:
            return -1
        return idx

    def calcVisibleRange(self, idx):
        self.visibleRange = self.calcVisibleRange_1(idx, self.data)

    def calcVisibleRange_1(self, idx, data):
        if not data:
            return None
        num = self.getVisibleNum()
        if idx < 0 or idx >= len(data):
            vr = (max(len(data) - num, 0), len(data))
            return vr
        HALF_NUM = num // 2
        if num >= len(data):
            return (0, len(data))
        leftNum = min(HALF_NUM, idx)
        fromIdx = idx - leftNum
        endIdx = min(fromIdx + num, len(data))
        while endIdx - fromIdx < num:
            endIdx = min(endIdx + 1, len(data))
            if endIdx - fromIdx >= num: break
            fromIdx = max(fromIdx - 1, 0)
        return (fromIdx, endIdx)
    
    def onMouseClick(self, x, y):
        si = self.getIdxAtX(x)
        if si >= 0 and self.win.selIdx != si:
            self.win.setSelIdx(si)
            return True
        return False
    
    def onDblClick(self, x, y):
        return False
    
    def onContextMenu(self, x, y):
        return True

    def onMouseMove(self, x, y):
        if x < 0 or y < 0 or x > self.width or y > self.height:
            self.mouseXY = None
        else:
            self.mouseXY = (x, y)
        return False
    
    def onMouseLeave(self):
        self.mouseXY = None

    def drawTipPrice(self, hdc, drawer, y):
        val = self.getValueAtY(y)
        if not val:
            return
        w = self.win.getClientSize()[0]
        H = 16
        rc = (w - self.win.RIGHT_MARGIN + 10 + 1, y - H // 2, w, y + H // 2)
        drawer.fillRect(hdc, rc, 0x800040)
        drawer.drawText(hdc, val['fmtVal'], rc, 0x0000ff, win32con.DT_CENTER)
        drawer.drawLine(hdc, 0, y, rc[0] - 2, y, 0xcccccc, win32con.PS_DOT)

class KLineIndicator(Indicator):
    def __init__(self, listener, config) -> None:
        super().__init__(listener, config)
        self.model = None

    def changeCode(self, code, period):
        tag = getTypeByCode(code)
        model = Cls_K_DataModel(code) if tag == 'cls' else Ths_K_DataModel(code)
        model.loadNetData(period)
        model.calcZhangFu()
        self.model = model
        super().changeCode(code, period)
        self.data = model.data if model else None
        code = model.code if model else None
        if model:
            model.calcMA(5)
            model.calcMA(10)
            model.calcZDT()
        self.win.notifyListener(Listener.Event('K-Model-Changed', self, data = self.data, model = model, code = code))

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = d.high
                minVal = d.low
            else:
                maxVal = max(maxVal, d.high)
                minVal = min(minVal, d.low)
            if getattr(d, 'MA5', None): 
                minVal = min(minVal, d.MA5)
                maxVal = max(maxVal, d.MA5)
            if getattr(d, 'MA10', None): 
                minVal = min(minVal, d.MA10)
                maxVal = max(maxVal, d.MA10)
        # merge ma5 ma10
        self.valueRange = (minVal, maxVal)

    def getValueAtY(self, y):
        if not self.valueRange or not self.height:
            return None
        m = y * (self.valueRange[1] - self.valueRange[0]) / self.height
        val = self.valueRange[1] - m
        if val >= 1000:
            fval = f'{val :0.1f}'
        elif val >= 100:
            fval = f'{val :0.1f}'
        else:
            fval = f'{val :.02f}'
        return {'value': val, 'fmtVal': fval, 'valType': 'Price'}

    def getColor(self, idx, data):
        if self.period.upper() != 'DAY':
            if data.close >= data.open:
                return 0x0000ff
            return 0xfcfc54
        if self.code[0 : 2] == '88' and idx > 0: # 指数
            zdfd = abs((self.data[idx].close - self.data[idx - 1].close) / self.data[idx - 1].close * 100)
            mdfd = abs((max(self.data[idx].high, self.data[idx - 1].close)- self.data[idx].low) / self.data[idx - 1].close * 100)
            if zdfd >= 3.5 or mdfd >= 3.5:
                return 0xff00ff
        if getattr(data, 'tdb', False):
            return 0x00ff00
        zdt = getattr(data, 'zdt', None)
        if zdt == 'ZT' or zdt == 'ZTZB':
            return 0xff0000
        if zdt == 'DT' or zdt == 'DTZB':
            return 0x00ffff
        if data.close >= data.open:
            return 0x0000ff
        return 0xfcfc54

    def draw(self, hdc, drawer):
        if not self.visibleRange or not self.valueRange:
            return
        self.drawKLines(hdc, drawer)
        self.drawMA(hdc, drawer, 'MA5', 0x00ffff, 1)
        self.drawMA(hdc, drawer, 'MA10', 0xee00ee, 2)
    
    def drawMouse(self, hdc, drawer, x, y):
        self.drawTipPrice(hdc, drawer, y)

    def drawMarkDay(self, markDay, hdc, drawer):
        if not markDay or not self.visibleRange:
            return
        idx = self.model.getItemIdx(markDay)
        if idx < 0:
            return
        if idx < self.visibleRange[0] or idx >= self.visibleRange[1]:
            return
        x = self.getCenterX(idx)
        sx = x - self.getItemWidth() // 2# - self.getItemSpace()
        ex = x + self.getItemWidth() // 2# + self.getItemSpace()
        rc = (sx, 0, ex, self.height)
        # pen = win32gui.GetStockObject(win32con.NULL_PEN)
        # win32gui.SelectObject(hdc, pen)
        # win32gui.FillRect(hdc, rc, hbrs['drak'])
        # draw tip
        if markDay not in self.markDays:
            return
        md = self.markDays[markDay]
        if not md['tip']:
            return
        rc = (sx - 30, self.height - 35, ex + 30, self.height)
        drawer.drawText(hdc, md['tip'], rc, color = 0x404040, align = win32con.DT_CENTER | win32con.DT_WORDBREAK | win32con.DT_VCENTER)

    def drawKLineItem(self, idx, hdc, drawer):
        data = self.data[idx]
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(data.open), ex, self.getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        color = self.getColor(idx, data)
        drawer.drawLine(hdc, cx, self.getYAtValue(data.low), cx, self.getYAtValue(min(data.open, data.close)), color)
        drawer.drawLine(hdc, cx, self.getYAtValue(max(data.open, data.close)), cx, self.getYAtValue(data.high), color)
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            #win32gui.SelectObject(hdc, fillHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            drawer.fillRect(hdc, rect, color)
    
    def drawKLines(self, hdc, drawer):
        if not self.visibleRange:
            return
        vr = self.visibleRange
        for idx in range(*vr):
            self.drawKLineItem(idx, hdc, drawer)

    def drawBackground(self, hdc, drawer):
        if not self.valueRange:
            return
        sdc = win32gui.SaveDC(hdc)
        SP = self.height // 4
        for i in range(0, 4):
            y = SP * i
            drawer.drawLine(hdc, 0, y, self.width, y, 0x000055, win32con.PS_DOT)
            price = self.getValueAtY(y)
            if not price:
                continue
            price = price['fmtVal']
            win32gui.SetTextColor(hdc, 0xab34de)
            x = self.width + 20
            rt = (x, y - 8, x + 60, y + 8)
            win32gui.DrawText(hdc, price, len(price), rt, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

        title = {'day': '日线', 'week': '周线', 'month': '月线'}
        title = '【' + title[self.period] + '】'
        drawer.use(hdc, drawer.getFont(fontSize = 18))
        rc = (5, self.height, 100, self.height + 20)
        # drawer.fillRect(hdc, rc, 0x0)
        drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_LEFT)

    def drawMA(self, hdc, drawer, ma, color, penWidth):
        vr = self.visibleRange
        moveToFlag = False
        drawer.use(hdc, drawer.getPen(color, width = penWidth))
        for i in range(vr[0], vr[1]):
            if not moveToFlag:
                mx = getattr(self.data[i], ma, 0)
                if mx > 0:
                    win32gui.MoveToEx(hdc, self.getCenterX(i), self.getYAtValue(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtValue(getattr(self.data[i], ma)))

    def onMouseMove(self, x, y):
        old = self.win.mouseXY
        si = self.getIdxAtX(x - self.x)
        if si < 0:
            return
        x = self.getCenterX(si)
        self.win.mouseXY = (x + self.x, y)
        if not self.win.selIdxOnClick:
            self.win.setSelIdx(si)
        if old != self.win.mouseXY:
            self.win.invalidWindow()
        return True

    def onContextMenu(self, x, y):
        return False

class RefIndicator(Indicator):
    def __init__(self, win, config = None) -> None:
        super().__init__(win, config)
        self.model = None
        self.mdata = None
        self.kindicator = None
        self.persent = 0
        self.win.addNamedListener('K-Model-Changed', self.onDataChanged)

    def onDataChanged(self, event, args):
        self.code = event.code
        self.data = event.data
        self.kindicator = event.src
        self.persent = 0

    def changeCode(self, code, period):
        self.model = None
        self.mdata = None
        self.persent = 0
        self.code = code
        self.valueRange = None
        self.visibleRange = None
        self.period = period
        ThreadPool.instance().addTask_N(self._changeCode)

    def _changeCode(self):
        self.persent = 0
        tag = getTypeByCode(self.code)
        model = Cls_K_DataModel(self.code) if tag == 'cls' else Ths_K_DataModel(self.code)
        model.loadNetData(self.period)
        model.calcZhangFu()
        self.model = model
        self.mdata = None
        if not self.model.data:
            return
        self.mdata = {}
        for d in self.model.data:
            self.mdata[d.day] = d
        self.win.notifyListener(Listener.Event('Ref-Model-Changed', self, data = self.data, model = model, code = self.code))

    def calcVisibleRange(self, idx):
        self.persent = 0

    def calcValueRange(self, fromIdx, endIdx):
        pass

    def calcPersent(self):
        self.persent = 0
        if not self.kindicator or not self.kindicator.visibleRange or not self.mdata:
            return
        for idx in range(*self.kindicator.visibleRange):
            day = self.data[idx].day
            if day not in self.mdata:
                continue
            self.persent = self.mdata[day].open / self.data[idx].open
            break

    def draw(self, hdc, drawer):
        if not self.kindicator or not self.kindicator.visibleRange or not self.mdata:
            return
        vr = self.kindicator.visibleRange
        if self.persent == 0:
            self.calcPersent()
        if self.persent == 0:
            return
        for idx in range(*vr):
            self.drawKLineItem(idx, hdc, drawer)

    def getCenterX(self, idx):
        if not self.kindicator:
            return -1
        return self.kindicator.getCenterX(idx)

    def getYAtValue(self, v):
        if not self.kindicator or not self.persent:
            return -1
        v /= self.persent
        y = self.kindicator.getYAtValue(v)
        if y < 0:
            return -1
        if y > self.height:
            return self.height
        return y

    def drawKLineItem(self, idx, hdc, drawer):
        day = self.data[idx].day
        if day not in self.mdata or not self.persent:
            return
        data = self.mdata[day]
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()

        rect = [bx, self.getYAtValue(data.open), ex, self.getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        color = 0xE19800
        drawer.drawLine(hdc, cx, self.getYAtValue(data.low), cx, self.getYAtValue(min(data.open, data.close)), color)
        drawer.drawLine(hdc, cx, self.getYAtValue(max(data.open, data.close)), cx, self.getYAtValue(data.high), color)
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            drawer.fillRect(hdc, rect, color)

class AttrIndicator(Indicator):
    def __init__(self, attrName, win, config) -> None:
        super().__init__(win, config)
        self.code = None
        self.attrName = attrName
        self.win.addNamedListener('K-Model-Changed', self.onDataChanged)

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        if fromIdx < 0 or endIdx < 0:
            return
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = getattr(d, self.attrName, 0)
                minVal = getattr(d, self.attrName, 0)
            else:
                maxVal = max(maxVal, getattr(d, self.attrName, 0))
                minVal = min(minVal, getattr(d, self.attrName, 0))
        self.valueRange = (0, maxVal)

    def onDataChanged(self, event, args):
        self.code = event.code
        self.data = event.data
        self.visibleRange = None
        self.valueRange = None

    def draw(self, hdc, drawer):
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        rc = (0, 2, 100, 20)
        drawer.fillRect(hdc, rc, 0x0)
        drawer.drawText(hdc, title, rc, 0xab34de, win32con.DT_LEFT)

    def onMouseMove(self, x, y):
        old = self.win.mouseXY
        if old and old[1] != y:
            self.win.mouseXY = (old[0], y)
            self.win.invalidWindow()
        elif not old:
            self.win.mouseXY = (x, y)
            self.win.invalidWindow()
        return True

class AmountIndicator(AttrIndicator):
    def __init__(self, win, config) -> None:
        super().__init__('amount', win, config)
        self.config['title'] = '[成交额]'

    def getValueAtY(self, y):
        rr = self.valueRange
        if not rr:
            return None
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val / 100000000 :.1f}亿', 'valType': self.attrName}
    
    def getColor(self, idx, data):
        if idx > 0:
            rv = getattr(data, self.attrName, 0)
            prv = getattr(self.data[idx - 1], self.attrName, 0)
            if prv > 0 and rv / prv >= 2: # 倍量
                return  0xff0000
        return super().getColor(idx, data)

    def drawItem(self, idx, hdc, drawer):
        data = self.data[idx]
        if not hasattr(data, self.attrName) or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.amount) + 1]
        if rect[3] - rect[1] == 0 and data.amount > 0:
            rect[1] -= 1
        rect = tuple(rect)
        color = self.getColor(idx, data)
        if data.close >= data.open:
            drawer.drawRect(hdc, rect, color)
        else:
            drawer.fillRect(hdc, rect, color)

    def draw(self, hdc, drawer):
        if not self.visibleRange:
            return
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, drawer)
        super().draw(hdc, drawer)
        self.drawAmountTipLine(hdc, drawer)

    def drawMouse(self, hdc, drawer, x, y):
        self.drawTipPrice(hdc, drawer, y)

    def drawAmountTipLine(self, hdc, drawer):
        if not self.code or self.code[0] == '8' or self.code[0 : 3] == '399':
            return
        if not self.valueRange or self.valueRange[0] == self.valueRange[1]:
            return
        亿 = 100000000
        if self.valueRange[1] >= 5 * 亿 and 5 * 亿  >= self.valueRange[0]:
            y = self.getYAtValue(5 * 亿)
            drawer.drawLine(hdc, 0, y, self.width, y, 0xff0000)
        if self.valueRange[1] >= 10 * 亿 and 10 * 亿  >= self.valueRange[0]:
            y = self.getYAtValue(10 * 亿)
            drawer.drawLine(hdc, 0, y, self.width, y, 0xff00ff)
        if self.valueRange[1] >= 20 * 亿 and 20 * 亿  >= self.valueRange[0]:
            y = self.getYAtValue(20 * 亿)
            drawer.drawLine(hdc, 0, y, self.width, y, 0x00ffff)

    def drawBackground(self, hdc, drawer):
        if not self.valueRange:
            return
        sdc = win32gui.SaveDC(hdc)
        y = self.getYAtValue(self.valueRange[1])
        drawer.drawLine(hdc, 0, y, self.width, y, 0x000055, win32con.PS_DOT)
        txt = f'{self.valueRange[1] / 100000000 :.1f}亿'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        drawer.drawText(hdc, txt, rt, 0xab34de, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

class RateIndicator(AttrIndicator):
    def __init__(self, win, config) -> None:
        super().__init__('rate', win, config)
        self.config['title'] = '[换手率]'

    def getValueAtY(self, y):
        rr = self.valueRange
        if not rr:
            return None
        m = (rr[1] - rr[0]) / self.height
        val = rr[1] - y * m
        return {'value': val, 'fmtVal': f'{val :.1f}%', 'valType': self.attrName}
    
    def getColor(self, idx, data):
        return super().getColor(idx, data)

    def drawItem(self, idx, hdc, drawer):
        data = self.data[idx]
        if not hasattr(data, self.attrName) or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.rate) + 1]
        if rect[3] - rect[1] == 0 and data.rate > 0:
            rect[1] -= 1
        rect = tuple(rect)
        color = self.getColor(idx, data)
        if data.close >= data.open:
            drawer.drawRect(hdc, rect, color)
        else:
            drawer.fillRect(hdc, rect, color)

    def draw(self, hdc, drawer):
        if not self.visibleRange:
            return
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, drawer)
        super().draw(hdc, drawer)
        self.drawAmountTipLine(hdc, drawer)

    def drawMouse(self, hdc, drawer, x, y):
        self.drawTipPrice(hdc, drawer, y)

    def drawAmountTipLine(self, hdc, drawer):
        if not self.code or self.code[0] == '8' or self.code[0 : 3] == '399':
            return
        if not self.valueRange or self.valueRange[0] == self.valueRange[1]:
            return
        if self.valueRange[1] >= 5:
            y = self.getYAtValue(5)
            drawer.drawLine(hdc, 0, y, self.width, y, 0xff0000)
        if self.valueRange[1] >= 10:
            y = self.getYAtValue(10)
            drawer.drawLine(hdc, 0, y, self.width, y, 0xff00ff)
        if self.valueRange[1] >= 20:
            y = self.getYAtValue(20)
            drawer.drawLine(hdc, 0, y, self.width, y, 0x00ffff)

    def drawBackground(self, hdc, drawer):
        if not self.valueRange:
            return
        sdc = win32gui.SaveDC(hdc)
        y = self.getYAtValue(self.valueRange[1])
        drawer.drawLine(hdc, 0, y, self.width, y, 0x000055, win32con.PS_DOT)
        txt = f'{self.valueRange[1] :.1f}%'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        drawer.drawText(hdc, txt, rt, 0xab34de, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

# config = {itemWidth: int}
class CustomIndicator(Indicator):
    def __init__(self, win, config = None) -> None:
        super().__init__(win, config)
        if 'itemWidth' not in self.config:
            self.config['itemWidth'] = 80
        self.cdata = None
        self.code = None
        self.win.addNamedListener('K-Model-Changed', self.onDataChanged)
        self.win.addNamedListener('selIdx-Changed', self.onSelIdxChanged)

    def onDataChanged(self, event, args):
        self.code = event.code
        self.data = event.data

    def changeCode(self, code, period):
        self.code = code
        self.valueRange = None
        self.visibleRange = None
        self.period = period
        ThreadPool.instance().addTask_N(self._changeCode)

    def _changeCode(self):
        self.calcVisibleRange(self.win.selIdx)

    def onSelIdxChanged(self, evt, args):
        idx = evt.idx
        self.calcVisibleRange(idx)
        if self.visibleRange:
            self.calcValueRange(*self.visibleRange)

    def onMouseMove(self, x, y):
        return True

    def getItemWidth(self):
        return self.config['itemWidth']

    def getItemSpace(self):
        return 1

    def onContextMenu(self, x, y):
        self.win.invalidWindow() # redraw
        return True

    def draw(self, hdc, drawer):
        if not self.visibleRange:
            return
        sdc = win32gui.SaveDC(hdc)
        for idx in range(*self.visibleRange):
            cx = self.getCenterX(idx)
            bx = cx - self.getItemWidth() // 2
            self.drawItem(hdc, drawer, idx, bx)
        win32gui.RestoreDC(hdc, sdc)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        wc, *_ = win32gui.GetTextExtentPoint32(hdc, title)
        rc = (0, 2, wc + 5, 20)
        drawer.fillRect(hdc, rc, 0x0)
        drawer.drawText(hdc, title, rc, 0xab34de, win32con.DT_LEFT)

    def drawItem(self, hdc, drawer, idx, x):
        x += self.config['itemWidth']
        drawer.drawLine(hdc, x, 0, x, self.height, 0x606060, win32con.PS_DASHDOT)

class DayIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 20
        super().__init__(win, config)
    
    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        day = str(self.data[idx].day)
        rc = (x + 1, 1, x + iw, self.height)
        hday = day[4 : 6] + '-' + day[6 : 8]
        today = datetime.date.today()
        if today.year != int(day[0 : 4]):
            day = day[2: 4] + '-' + hday
        else:
            day = hday
        drawer.drawText(hdc, day, rc, 0xcccccc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def drawBackground(self, hdc, drawer):
        drawer.fillRect(hdc, (0, 1, self.width - 1, self.height - 1), 0x151515)

class ScqxIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        if 'title' not in self.config:
            self.config['title'] = '[市场情绪]'

    def _changeCode(self):
        super()._changeCode()
        datas = cls_orm.CLS_SCQX.select().dicts()
        maps = {}
        for d in datas:
            day = d['day'].replace('-', '')
            maps[int(day)] = d['zhqd']
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        val = self.cdata[day]
        if not val:
            return
        rc = (x + 1, 1, x + iw, self.height)
        rc = (x + 3, 3, x + iw - 3, self.height)
        color = 0xcccccc
        if val >= 60: color = 0x0000FF
        elif val >= 40: color = 0x1D77FF
        else: color = 0x00ff00 #0x24E7C8
        drawer.drawText(hdc, str(val) + '°', rc, color, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class LsAmountIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[两市成交额]'

    def _changeCode(self):
        super()._changeCode()
        maps = {}
        url = henxin.HexinUrl()
        ds = url.loadKLineData('999999')
        for d in ds['data']:
            maps[d.day] = d.amount / 1000000000000 # 万亿
        ds = url.loadKLineData('399001')
        for d in ds['data']:
            maps[d.day] = maps.get(d.day, 0) + d.amount / 1000000000000 # 万亿
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        rc = (x + 1, 1, x + iw, self.height)
        drawer.drawText(hdc,f"{self.cdata[day] :.02f}", rc, 0xcccccc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def onMouseClick(self, x, y):
        if super().onMouseClick(x, y):
            return True
        si = self.getIdxAtX(x)
        if si < 0:
            return True
        # draw tip
        day = self.data[si].day
        fday = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        itemData = d_orm.HotVol.get_or_none(d_orm.HotVol.day == fday)
        if not itemData:
            return True
        self.drawHotVal(itemData, si)
        return True
        
    def drawHotVal(self, itemData, idx):
        hdc = win32gui.GetDC(self.win.hwnd)
        W, H = 250, 150
        ix = (idx - self.visibleRange[0]) * (self.getItemWidth() + self.getItemSpace())
        drawer : Drawer = self.win.drawer
        if ix + W <= self.width:
            sx = self.x + ix
        else:
            sx = self.width - W + self.x
        sy = self.y - H
        rc = [sx, sy, sx + W, sy + H]
        drawer.fillRect(hdc, rc, 0x101010)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        drawer.use(hdc, drawer.getFont())
        self.drawHotValInfo(hdc, rc, itemData, idx)
        drawer.drawRect(hdc, rc, 0xa0f0b0)
        win32gui.ReleaseDC(self.win.hwnd, hdc)

    def drawHotValInfo(self, hdc, rc, itemData, idx):
        drawer : Drawer = self.win.drawer
        VCENTER = win32con.DT_SINGLELINE | win32con.DT_VCENTER | win32con.DT_CENTER
        W, H = rc[2] - rc[0], rc[3] - rc[1]
        IW, IH = W / 4, H / 6
        drawer.fillRect(hdc, (rc[0], rc[1], rc[2], rc[1] + int(IH)), 0x202020)
        for i, title in enumerate(('', '成交额', '', '平均额')):
            drawer.drawText(hdc, title, (rc[0] + int(IW * i), rc[1], rc[0] + int(IW + IW * i), int(rc[1] + IH)), 0xcccccc, align = VCENTER)
        kdata = self.data[idx]
        amount = int(getattr(kdata, 'amount') / 100000000)
        lns = [('第 1', 'p1', '前1-10', 'avg0_10'), ('第10', 'p10', '前10-20', 'avg10_20'),
                ('第20', 'p20', '前20-50', 'avg20_50'), ('第50', 'p50', '前50-100', 'avg50_100'), ('第100', 'p100', '个股', 'A')]
        for idx, ln in enumerate(lns):
            for cidx, k in enumerate(ln):
                drawer.drawLine(hdc, rc[0], int(rc[1] + IH + IH * idx), rc[2], int(rc[1] + IH + IH * idx), 0xf0a0a0)
                irc = (rc[0] + int(IW * cidx), int(rc[1] + IH + IH * idx),
                        rc[0] + int(IW * cidx + IW), int(rc[1] + IH * 2 + IH * idx))
                if cidx % 2 == 0:
                    drawer.fillRect(hdc, irc, 0x202020)
                    drawer.drawText(hdc, k, irc, 0xcccccc, align = VCENTER)
                else:
                    val = getattr(itemData, k, 0) if k[0] == 'p' or k[0] == 'a' else amount
                    drawer.drawText(hdc, f'{val} 亿', irc, 0xcccccc, align = VCENTER)

class HotIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[热度排名]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        maps = {}
        hots = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.code == int(self.code)).dicts()
        maps = {}
        for d in hots:
            maps[d['day']] = d['zhHotOrder']
        lastDay = self.data[-1].day
        if lastDay not in maps:
            hot = hot_utils.DynamicHotZH.instance().getDynamicHotZH(lastDay, self.code)
            if hot: maps[lastDay] = hot['zhHotOrder']
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 1, 1, x + iw, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        drawer.use(hdc, drawer.getFont(fontSize = 15, weight = 500))
        drawer.drawText(hdc,f"{self.cdata[day]}", rc, 0x00dddd, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def drawBackground(self, hdc, drawer):
        drawer.fillRect(hdc, (0, 1, self.width - 1, self.height - 1), 0x151515)

class ThsZT_Indicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        super().__init__(win, config)
        self.config['title'] = '[同花顺涨停]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        maps = {}
        datas = ths_orm.THS_ZT.select().where(ths_orm.THS_ZT.code == self.code).dicts()
        for d in datas:
            day = int(d['day'].replace('-', ''))
            maps[day] = d
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 3, 1, x + iw - 3, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        txt = self.cdata[day]['ztReason']
        drawer.use(hdc, drawer.getFont(fontSize = 12))
        drawer.drawText(hdc,txt, rc, 0xcccccc, win32con.DT_WORDBREAK | win32con.DT_VCENTER)

class ClsZT_Indicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        super().__init__(win, config)
        self.config['title'] = '[财联社涨停]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        maps = {}
        datas = cls_orm.CLS_ZT.select().where(cls_orm.CLS_ZT.code == self.code).dicts()
        for d in datas:
            day = int(d['day'].replace('-', ''))
            maps[day] = d
        scode = ('sh' if self.code[0] == '6' else 'sz') + self.code
        qr = cls_orm.CLS_UpDown.select().where(cls_orm.CLS_UpDown.secu_code == scode).dicts()
        for d in qr:
            day = int(d['day'].replace('-', ''))
            d['ztReason'] = d['up_reason']
            d['detail'] = ''
            if day not in maps:
                maps[day] = d
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 3, 1, x + iw - 3, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        txt = self.cdata[day]['ztReason']
        drawer.use(hdc, drawer.getFont(fontSize = 12))
        drawer.drawText(hdc,txt, rc, 0xcccccc, win32con.DT_WORDBREAK | win32con.DT_VCENTER)

    def onMouseClick(self, x, y):
        if super().onMouseClick(x, y):
            return True
        si = self.getIdxAtX(x)
        if si < 0:
            return True
        # draw tip
        day = self.data[si].day
        if not self.cdata or day not in self.cdata:
            return True
        detail = self.cdata[day]['detail']
        self.drawDetail(detail)
        return True
    
    def drawDetail(self, detail):
        hdc = win32gui.GetDC(self.win.hwnd)
        drawer : Drawer = self.win.drawer
        W, H = int(0.5 * self.width), 60
        x = (self.width - W) // 2
        y = self.y - H
        rc = (x, y, x + W, y + H)
        drawer.fillRect(hdc, rc, 0x101010)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        drawer.use(hdc, drawer.getFont())
        drawer.drawText(hdc, detail, rc, 0xcccccc, win32con.DT_WORDBREAK | win32con.DT_VCENTER)
        drawer.drawRect(hdc, rc, 0xa0f0a0)
        win32gui.ReleaseDC(self.win.hwnd, hdc)

#概念联动
class GnLdIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[联动]'
        self.clsGntc = None
        self.curGntc = ''
        self.win.addNamedListener('Ref-Model-Changed', self.onRefChanged)

    def onRefChanged(self, evt, args):
        if not evt.code or evt.code[0 : 3] != 'cls' or not evt.model:
            return
        name = evt.model.name
        self.changeGntc(name)

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        # load gntc
        obj = cls_orm.CLS_GNTC.get_or_none(code = self.code)
        self.clsGntc = []
        isCurGntcExists = False
        if obj and obj.hy:
            for it in obj.hy.split(';'):
                it = it.strip()
                if it: self.clsGntc.append({'name': it, 'type': 'hy', 'title': f'【{it}】'})
                if self.curGntc and self.curGntc == it:
                    isCurGntcExists = True
        if obj and obj.gn:
            for it in obj.gn.split(';'):
                it = it.strip()
                if it: self.clsGntc.append({'name': it, 'type': 'gn', 'title': f'{it}'})
                if self.curGntc and self.curGntc == it:
                    isCurGntcExists = True
        
        curGntc = self.curGntc
        if not isCurGntcExists:
            curGntc = ''
        self.changeGntc(curGntc, True)
        # self.cdata = maps

    def changeGntc(self, gntc, force = False):
        if self.curGntc == gntc and not force:
            return
        self.curGntc = gntc or ''
        self.config['title'] = f'[联动-{self.curGntc}]'

        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.name == self.curGntc).dicts()
        maps = {}
        for d in qr:
            day = int(d['day'].replace('-', ''))
            if day not in maps:
                maps[day] = [d]
            else:
                maps[day].append(d)
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 1, 1, x + iw, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        items = self.cdata[day]
        IIW = 6
        w = IIW * len(items)
        sx = (iw - w) // 2 + x
        y = int(self.height * 0.3)
        for it in items:
            rc = (sx, y, sx + IIW - 1, self.height - 1)
            if it['up']:
                drawer.fillRect(hdc, rc, 0xee2b8c)
            else:
                drawer.fillRect(hdc, rc, 0x3CDC14)
            sx += IIW

    def _onContextMenu(self, x, y):
        if not self.clsGntc:
            return
        menu = PopupMenu.create(self.win.hwnd, self.clsGntc)
        menu.VISIBLE_MAX_ITEM = 8
        menu.addNamedListener('Select', self.onSelectItem)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)
        return True
    
    def onSelectItem(self, evt, args):
        item = evt.item
        self.changeGntc(item['name'])
        self.win.invalidWindow()

    def drawBackground(self, hdc, drawer):
        drawer.fillRect(hdc, (0, 1, self.width - 1, self.height - 1), 0x101010)

# 涨速，用于指明进攻意愿
class ZhangSuIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[涨速]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        qr = d_orm.LocalSpeedModel.select().where(d_orm.LocalSpeedModel.code == self.code).dicts()
        maps = {}
        for d in qr:
            day = d['day']
            if day not in maps:
                maps[day] = [d]
            else:
                maps[day].append(d)
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 1, 1, x + iw, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        items = self.cdata[day]
        MAX_ITEM_ZF = 5
        IW = 2
        zs = 0
        for it in items:
            zs += it['zf']
        import math
        aw = math.ceil(zs / MAX_ITEM_ZF)
        w = aw * IW
        sx = (iw - w) // 2 + x
        y = int(self.height * 0.3)
        rc = (sx, y, sx + w, self.height - 1)
        drawer.fillRect(hdc, rc, 0x3C14DC)

class LhbIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[龙虎榜]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 6:
            return
        maps = {}
        qr = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.code == self.code).dicts()
        for d in qr:
            day = int(d['day'].replace('-', ''))
            old = maps.get(day, None)
            if old:
                if '累计' in old['title']:
                    maps[day] = d
                    d['detail'] = json.loads(d['detail'])
            else:
                maps[day] = d
                d['detail'] = json.loads(d['detail'])
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        rc = (x + 1, 1, x + iw, self.height)
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        # detail = self.cdata[day]['detail']
        drawer.drawText(hdc, 'Y', rc, 0xcccccc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def getYzName(self, it):
        if it.get('yz', None):
            return ' (' + it['yz'] + ')'
        yyb = it.get('yyb', '')
        if '分公司' in yyb:
            yyb = yyb[0 : yyb.index('公司') + 2]
        if '公司' in yyb:
            i = yyb.index('公司')
            if i != len(yyb) - 2:
                yyb = yyb[i + 2 : ]
        yyb = yyb.replace('有限责任公司', '')
        yyb = yyb.replace('股份有限公司', '')
        yyb = yyb.replace('有限公司', '')
        yyb = yyb.replace('证券营业部', '')
        return yyb
    
    def onMouseClick(self, x, y):
        if super().onMouseClick(x, y):
            return True
        si = self.getIdxAtX(x)
        if si < 0:
            return True
        # draw tip
        day = self.data[si].day
        if not self.cdata or day not in self.cdata:
            return
        itemData = self.cdata[day]
        if not itemData or not itemData['detail']:
            return True
        hdc = win32gui.GetDC(self.win.hwnd)
        W, H = 400, 240
        ix = (si - self.visibleRange[0]) * (self.getItemWidth() + self.getItemSpace())
        drawer : Drawer = self.win.drawer
        if ix + W <= self.width:
            sx = self.x + ix
        else:
            sx = self.width - W + self.x
        sy = self.y - H
        rc = [sx, sy, sx + W, sy + H]
        drawer.fillRect(hdc, rc, 0x101010)
        drawer.drawRect(hdc, rc, 0xa0f0a0)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        drawer.use(hdc, drawer.getFont())
        rc[0] += 1
        rc[1] += 1
        rc[2] -= 1
        rc[3] -= 1
        self.drawItemDetail(drawer, hdc, rc, itemData)
        win32gui.ReleaseDC(self.win.hwnd, hdc)
        return True

    def drawItemDetail(self, drawer : Drawer, hdc, rect, itemData):
        detail = itemData['detail']
        if not detail:
            return
        newDetail = []
        detail.sort(key = lambda x : x['mrje'], reverse = True)
        mr = detail[0 : 5]
        newDetail.extend(mr)
        detail.sort(key = lambda x : x['mcje'], reverse = True)
        mc = detail[0 : 5]
        newDetail.extend(mc)

        ws = [0, 60, 60, 60, 60]
        ws[0] = rect[2] - rect[0] - sum(ws)
        IH = (rect[3] - rect[1]) / 11
        drawer.fillRect(hdc, (rect[0], rect[1], rect[2], rect[1] + int(IH)), 0x404040)
        titles = ['席位名称', '买入', '卖出', '净额', '']
        sx = rect[0]
        sy = rect[1]
        VCENTER = win32con.DT_SINGLELINE | win32con.DT_VCENTER
        for i in range(4):
            drawer.drawText(hdc, titles[i], (sx + 2, sy, sx + ws[i], int(sy + IH)), 0xcccccc, align = VCENTER)
            sx += ws[i]
        for r, d in enumerate(newDetail):
            sx = rect[0]
            sy += IH
            lw = 1
            lc = 0x202020
            if r == 5:
                lw = 1
                lc = 0xa0f0a0
            drawer.drawLine(hdc, rect[0] + 1, int(sy), rect[2] - 1, int(sy), lc, width = lw)
            cs = (self.getYzName(d), d.get('mrje', 0), d.get('mcje', 0), d.get('jme', 0))
            for i in range(len(cs)):
                drawer.drawText(hdc, cs[i], (sx + 2, int(sy), sx + ws[i], int(sy + IH)), color = 0xd0d0d0, align = VCENTER)
                sx += ws[i]
        # draw sum info
        sx = rect[2] - ws[-1]
        sy = rect[1] + IH
        sumInfo = ['总买', f'{itemData["mrje"] :.1f}亿', f'{itemData["mrje"] / itemData["cjje"] * 100 :.1f}%', '', '',
                   '总卖', f'{itemData["mcje"] :.1f}亿', f'{itemData["mcje"] / itemData["cjje"] * 100 :.1f}%']
        for i in range(len(sumInfo)):
            drawer.drawText(hdc, sumInfo[i], (sx + 2, int(sy), rect[2], int(sy + IH)), color = 0xd0d0d0, align = VCENTER)
            sy += IH

# 指数涨跌排名
class ZsZdPmIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        super().__init__(win, config)
        self.config['title'] = '[指数涨跌排名]'
    
    def _changeCode(self):
        super()._changeCode()
        maps = {}
        qr = None
        if len(self.code) == 6 and self.code[0 : 2] == '88':
            qr = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.code == self.code).dicts()
        elif len(self.code) == 8 and self.code[0 : 3] == 'cls':
            qr = cls_orm.CLS_ZS_ZD.select().where(cls_orm.CLS_ZS_ZD.code == self.code).dicts()
        if not qr:
            return
        for d in qr:
            day = int(d['day'].replace('-', ''))
            maps[day] = d
        self.cdata = maps

    def drawItem(self, hdc, drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata:
            return
        rc1 = (x + 1, 1, x + iw, self.height // 2)
        rc2 = (x + 1, self.height // 2, x + iw, self.height)
        CENTER = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE
        item = self.cdata[day]
        if 'zdf_topLevelPM' in item:
            drawer.drawText(hdc, item['zdf_topLevelPM'], rc1, 0xcccccc, CENTER)
            drawer.drawText(hdc, item['zdf_PM'], rc2, 0xcccccc, CENTER)
        elif 'pm' in item:
            drawer.drawText(hdc, f"{int(item['fund'])} 亿", rc1, 0xcccccc, CENTER)
            drawer.drawText(hdc, item['pm'], rc2, 0xcccccc, CENTER)

class CLS_HotTcIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(win, config)
        self.config['title'] = '[财联社热点]'

    def _changeCode(self):
        super()._changeCode()
        if len(self.code) != 8 or self.code[0 : 3] != 'cls':
            return
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.code == self.code).dicts()
        maps = {}
        for d in qr:
            day = int(d['day'].replace('-', ''))
            if day not in maps:
                maps[day] = [d]
            else:
                maps[day].append(d)
        self.cdata = maps

    def drawItem(self, hdc, drawer : Drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        iw = self.config['itemWidth']
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata or not self.cdata[day]:
            return
        items = self.cdata[day]
        ITEM_W = 8
        sx = (iw - len(items) * (ITEM_W + 1)) // 2 + x
        for i, item in enumerate(items):
            rc = (sx, 10, sx + ITEM_W, self.height)
            color = 0x0000ff if item['up'] else 0x00ff00
            drawer.fillRect(hdc, rc, color)
            sx += ITEM_W + 1

# 涨停数（用于指数）
class ZS_ZT_NumIndicator(CustomIndicator):
    def __init__(self, win, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 80
        super().__init__(win, config)
        self.config['title'] = '[涨跌停]'

    def _changeCode(self):
        super()._changeCode()
        self.changeZSCode(self.code)

    def changeZSCode(self, zsCode):
        if zsCode[0 : 3] != 'cls' and zsCode[0 : 2] != '88':
            return
        qr = cls_orm.CLS_UpDown.select(cls_orm.CLS_UpDown.secu_code, 
                cls_orm.CLS_UpDown.day, cls_orm.CLS_UpDown.limit_up_days, cls_orm.CLS_UpDown.is_down, 
                cls_orm.CLS_UpDown.time).dicts()
        self.cdata = self.calcGroups(zsCode, qr)
        ds = self.loadTodayData(zsCode)
        todayGroup = self.calcGroups(zsCode, ds)
        if not todayGroup or len(todayGroup) != 1:
            return
        today = todayGroup.keys()[0]
        self.cdata[today] = todayGroup[today]
        
    def calcGroups(self, zsCode, qr):
        if not qr:
            return None
        maps = {}
        isClsZs = zsCode[0 : 3] == 'cls'
        attrs = ('gn_code', 'hy_2_code', 'hy_3_code', 'hy_code')
        for it in qr:
            scode, day, lb, down = it['secu_code'], it['day'], it['limit_up_days'], it['is_down']
            code = scode[2 : ]
            day = int(day.replace('-', ''))
            if day not in maps:
                maps[day] = {'ZT': 0, 'DT': 0, 'ZB': 0, 'items': []}
            if isClsZs:
                obj = gn_utils.cls_gntc_s.get(code, None)
            else:
                obj = gn_utils.ths_gntc_s.get(code, None)
            if not obj:
                continue
            for a in attrs:
                if zsCode in (obj.get(a, '') or ''):
                    maps[day]['items'].append(it)
                    if lb: maps[day]['ZT'] += 1
                    elif lb == 0 and down == 0: maps[day]['ZB'] += 1
                    elif down: maps[day]['DT'] += 1
                    break
        return maps

    def loadTodayData(self, zsCode):
        from download import ths_iwencai, cls
        today = datetime.date.today().strftime("%Y%m%d")
        if int(today) in self.cdata:
            return None
        tds = ths_iwencai.getTradeDays()
        if not tds:
            return None
        lastDay = tds[-1]
        if lastDay != today:
            return None
        urls = ['https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=up_pool&way=last_px&sign=a6ab28604a6dbe891cdbd7764799eda1',
                'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=up_open_pool&way=last_px&sign=c178185f9b06e3d9e885ba54a47d68ec',
                'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=down_pool&way=last_px&sign=95d3a7c20bb0313a0bb3445d9faf2d27']
        rs = []
        for url in urls:
            try:
                resp = requests.get(url)
                js = json.loads(resp.text)
                if js['code'] != 200:
                    continue
                for d in js['data']:
                    if d['is_st']:
                        continue
                    d['day'] = d['time'][0 : 10]
                    d['time'] = d['time'][11 : ]
                    obj = cls_orm.CLS_UpDown(**d)
                    if 'type=down_pool' in url:
                        obj.is_down = 1
                    rs.append(obj.__data__)
            except Exception as e:
                print('[ZS_ZT_NumIndicator.loadTodayData] ', url)
        return rs

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        if fromIdx == endIdx or not self.cdata:
            return
        fday = self.data[fromIdx].day
        eday = self.data[endIdx - 1].day
        maxVal = 0
        for day in self.cdata:
            if day >= fday and day <= eday:
                item = self.cdata[day]
                maxVal = max(maxVal, item['ZT'], item['ZB'], item['DT'])
        self.valueRange = (0, maxVal)

    def drawItem(self, hdc, drawer : Drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        W = self.config['itemWidth']
        IW = 15
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata or not self.cdata[day] or not self.valueRange:
            return
        info = self.cdata[day]
        zt, zb, dt = info['ZT'], info['ZB'], info['DT']
        COLORS = (0xFF3333, 0x00ff00, 0x00ffff)
        maxVal = self.valueRange[1]
        if not maxVal:
            maxVal = 1
        maxHeight = self.height - 30
        SX = (W - IW * 3) // 2 + x
        for i, val in enumerate((zt, zb, dt)):
            y = maxHeight - int(val / maxVal * maxHeight) + 10
            sx = SX + IW * i
            isw = sx + (IW - 6) // 2
            rc = (isw, y, isw + 6, maxHeight + 10)
            drawer.fillRect(hdc, rc, COLORS[i])
            trc = (sx, maxHeight + 10, sx + IW, self.height)
            drawer.drawText(hdc, val, trc, COLORS[i], win32con.DT_SINGLELINE | win32con.DT_VCENTER | win32con.DT_CENTER)
    
    def onDblClick(self, x, y):
        from ui import kline_win
        if not self.code:
            return True
        #mgr = kline_win.ContextMenuManager(None)
        idx = self.getIdxAtX(x)
        if idx < 0:
            return True
        curData = self.getItemData(idx)
        #mgr.openRefZs(self.code, curData.day)
        self.showZT_List(curData, self.code)
        return True

    def showZT_List(self, item, zsCode):
        from ui import timeline, dialog
        if not zsCode:
            return
        kcode = self.win.klineIndicator.model.code
        tab = TableWindow()
        headers = [{'name': '#idx', 'width': 30, 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE},
                   {'name': 'mcode', 'width': 80, 'title': '代码', 'textAlign': win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'name': 'curKCode', 'width': 15, 'title': ''},{'name': 'lb', 'width': 50, 'title': '连板'},
                   {'name': 'fs', 'width': 80, 'stretch': 1},
                   {'name': 'up_reason', 'width': 100, 'textAlign': win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'paddings': (0, 0, 3, 0)}]
        tab.rowHeight = 50
        tab.css['selBgColor'] = 0xEAD6D6 # 0xEAD6D6 #0xf0a0a0
        tab.headers = headers
        timeline.Table_TimelineRender.registerFsRender(tab)
        day = f'{item.day // 10000}-{item.day // 100 % 100 :02d}-{item.day % 100 :02d}'
        qr = cls_orm.CLS_UpDown.select().where(cls_orm.CLS_UpDown.day == day).order_by(cls_orm.CLS_UpDown.time).dicts()
        model = []
        zt, zb, dt = [], [], []
        for it in qr:
            code = it['secu_code'][2 : ]
            fd = gn_utils.hasRefZs(code, zsCode)
            if not fd:
                continue
            lb = ''
            if it['limit_up_days'] > 0: 
                lb = str(it['limit_up_days']) + '板'
            reason = it['up_reason']
            if '|' in reason:
                reason = reason[0 : reason.index('|')]
            else:
                reason = reason[0 : 20]
            itemx = {'code': fd['code'], 'mcode': fd['code'] + '\n' + fd['name'], 'name': fd['name'], 'day': day, 'lb': lb, 'up_reason': reason}
            if itemx['code'] == kcode:
                itemx['curKCode'] = '*'
            if it['limit_up_days'] > 0:
                zt.append(itemx)
            elif it['is_down']:
                dt.append(itemx)
            else:
                zb.append(itemx)
        model = zt + zb + dt
        popup = dialog.Dialog()
        W, H = 650, 350
        style = win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_SIZEBOX
        popup.createWindow(self.win.hwnd, (0, 0, W, H), style, title = f'{day}')
        tab.createWindow(popup.hwnd, (0, 0, 1, 1))
        popup.layout = GridLayout(('1fr', ), ('1fr', ), (0, 0))
        popup.layout.setContent(0, 0, tab)
        popup.layout.resize(0, 0, *popup.getClientSize())
        tab.setData(model)
        tab.addNamedListener('RowEnter', self.onRowEnter, (model, item.day))
        tab.addNamedListener('DbClick', self.onRowEnter, (model, item.day))
        popup.showCenter()

    def onRowEnter(self, evt, args):
        model, curDay = args
        rowData = evt.data
        from ui import kline_utils
        mds = self.win.marksMgr.data
        days = [d for d in mds]
        if curDay not in days:
            days.append(curDay)
        winx = kline_utils.openInCurWindow(self.win, {'code': rowData['code'], 'day': days})
        winx.klineWin.refIndicator.changeCode(self.win.refIndicator.model.code, 'day')
        codes = [m['code'] for m in model]
        winx.setCodeList(codes)
        return
        pp = self.win.hwnd
        pcwin = self.win
        while True:
            pp = win32gui.GetParent(pp)
            if not BaseWindow.bindHwnds.get(pp, None):
                break
            px = BaseWindow.bindHwnds[pp]
            if hasattr(px, 'changeCode'):
                pcwin = px
        pcwin.changeCode(rowData['code'])

# 关联指数的涨停信息（用于个股）
class Code_ZT_NumIndicator(ZS_ZT_NumIndicator):
    def __init__(self, win, config = None) -> None:
        super().__init__(win, config)
        self.config['title'] = '[板块-]'
        self.refCode = None
        self.win.addNamedListener('Ref-Model-Changed', self.onRefChanged)

    def onRefChanged(self, evt, args):
        if not evt.code or not evt.model:
            return
        self.refCode = evt.code
        name = evt.model.name
        self.config['title'] = f'[板块-{name}]'
        #super().changeCode(self.refCode, self.period)
        ThreadPool.instance().addTask_N(self.changeZSCode, self.refCode)

    def changeZSCode(self, zsCode):
        super().changeZSCode(zsCode)
        self.calcZT_Order()

    def calcZT_Order(self):
        if not self.cdata:
            return
        for day in self.cdata:
            items : list = self.cdata[day]['items']
            ztItems = [d for d in items if d['limit_up_days'] > 0]
            ztItems.sort(key = lambda d : d['time'])
            for idx, cur in enumerate(ztItems):
                if cur['limit_up_days'] == 0:
                    break
                if idx == 0:
                    cur['order'] = 1
                elif cur['time'] == ztItems[idx - 1]['time']:
                    cur['order'] = ztItems[idx - 1]['order']
                else:
                    cur['order'] = idx + 1
                if cur['secu_code'][2 : ] == self.code:
                    self.cdata[day]['order'] = cur['order']
                    break
    
    def _changeCode(self):
        CustomIndicator._changeCode(self)

    def onDblClick(self, x, y):
        if not self.refCode:
            return True
        idx = self.getIdxAtX(x)
        if idx < 0:
            return True
        curData = self.getItemData(idx)
        self.showZT_List(curData, self.refCode)
        return True

    def drawItem(self, hdc, drawer : Drawer, idx, x):
        super().drawItem(hdc, drawer, idx, x)
        W = self.config['itemWidth']
        day = self.data[idx].day
        if not self.cdata or day not in self.cdata or not self.cdata[day] or not self.valueRange:
            return
        info = self.cdata[day]
        if not info.get('order', None):
            return
        order = str(info['order'])
        rc = (x, 5, x + W, 20)
        drawer.drawText(hdc, order, rc, 0x505050)

if __name__ == '__main__':
    #base_win.ThreadPool.instance().start()
    pass
    #win32gui.PumpMessages()