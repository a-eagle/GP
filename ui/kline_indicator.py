import os, sys, functools, copy, datetime, json, time, traceback
import win32gui, win32con
import requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import speed_orm, ths_orm, tdx_orm, tck_orm, tck_def_orm, lhb_orm, cls_orm
from Download.datafile_2 import *
from Download import henxin, cls
from Common.base_win import *
from THS import hot_utils

def getTypeByCode(code):
    if not code:
        return None
    if type(code) == int:
        code = f'{code :06d}'
    if type(code) != str:
        return None
    if code[0] in ('0', '3', '6'): # , '8'
        return 'cls'
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
        from Tck import utils
        obj = utils.get_THS_GNTC(code)
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
        self.valueRange = None
        self.visibleRange = None
        self.period = period

    def calcValueRange(self, fromIdx, endIdx):
        pass

    def getYAtValue(self, value):
        return self.getYAtValue2(value, self.height)

    def getYAtValue2(self, value, height):
        if not self.valueRange:
            return 0
        if value < self.valueRange[0] or value > self.valueRange[1]:
            return 0
        if self.valueRange[1] == self.valueRange[0]:
            return 0
        p = height * (value - self.valueRange[0]) / (self.valueRange[1] - self.valueRange[0])
        y = height - int(p)
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
        rc = (sx, 0, ex, self.height + self.getMargins(1))
        drawer.fillRect(hdc, rc, 0x202030)

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
        self.model = model
        super().changeCode(code, period)
        self.data = model.data if model else None
        code = model.code if model else None
        if model:
            model.calcMA(5)
            model.calcMA(10)
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
        # if not self.code:
            # return 0xfcfc54
        # if self.code[0 : 2] == '88' and idx > 0: # 指数
        #     zdfd = abs((self.data[idx].close - self.data[idx - 1].close) / self.data[idx - 1].close * 100)
        #     mdfd = abs((max(self.data[idx].high, self.data[idx - 1].close)- self.data[idx].low) / self.data[idx - 1].close * 100)
        #     if zdfd >= 3.5 or mdfd >= 3.5:
        #         return 0xff00ff
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
    
    def onMouseClick(self, x, y):
        si = self.getIdxAtX(x)
        self.win.setSelIdx(si)
        return True

    def onMouseMove(self, x, y):
        old = self.win.mouseXY
        si = self.getIdxAtX(x - self.x)
        while True:
            if si < 0:
                self.mouseXY = None
                break
            x = self.getCenterX(si)
            if x < 0:
                self.mouseXY = None
                break
            self.win.mouseXY = (x + self.x, y)
            break
        if not self.win.selIdxOnClick:
            self.win.setSelIdx(si)
        if old != self.win.mouseXY:
            self.win.invalidWindow()
        return True

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

    def onMouseClick(self, x, y):
        si = self.getIdxAtX(x)
        self.win.setSelIdx(si)
        return True

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



if __name__ == '__main__':
    #base_win.ThreadPool.instance().start()
    pass
    #win32gui.PumpMessages()