import os, sys, functools, copy, datetime, json, time, traceback
from win32.lib.win32con import WS_CAPTION, WS_POPUP, WS_SYSMENU
import win32gui, win32con
import requests, peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import speed_orm, ths_orm, tdx_orm, tck_orm, tck_def_orm, lhb_orm, cls_orm
from Download import datafile
from Download import henxin, cls
from Common import base_win, ext_win, dialog
from THS import hot_utils

class KLineModel_Tdx(datafile.DataFile):
    def __init__(self, code):
        super().__init__(code, datafile.DataFile.DT_DAY)
        self.loadData(datafile.DataFile.FLAG_ALL)

class KLineModel_Ths(henxin.ThsDataFile):
    def __init__(self, code) -> None:
        super().__init__(code, datafile.DataFile.DT_DAY)

class KLineModel_Cls(cls.ClsDataFile):
    def __init__(self, code) -> None:
        super().__init__(code, datafile.DataFile.DT_DAY)

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

class KLineModel_DateType(datafile.DataFile):
    # typeName is 'ths' | 'cls'
    def __init__(self, code, typeName = None):
        #super().__init__(code, datafile.DataFile.DT_DAY, 0) # no call
        if type(code) == int:
            code = f'{code :06d}'
        if not typeName:
            typeName = getTypeByCode(code)
        self.code = code
        self.typeName = typeName
        self.dateType = 'day' # 'week' | 'month'
        self.dateTypeDatas = {}
        self.data = None
    
    def loadDataFile(self):
        if self.typeName.lower() == 'ths':
            model = KLineModel_Ths(self.code)
        else:
            model = KLineModel_Cls(self.code)
        model.loadDataFile()
        if not model.name:
            model.name = getNameByCode(self.code)
        self.__dict__.update(model.__dict__)
        self.dateTypeDatas['day'] = self.data

    def calcAttrs(self):
    #    base_win.ThreadPool.instance().addTask(f'Attrs-{self.code}', self.calcAttrs_)
    #   def calcAttrs(self):
        self.calcMA(5)
        self.calcMA(10)
        self.calcZDT()
        self.calcZhangFu()

    # 'day' | 'week' | 'month'
    def changeDateType(self, dateType):
        if self.dateType == dateType:
            return
        self.dateType = dateType
        if dateType not in self.dateTypeDatas:
            dayData = self.dateTypeDatas['day']
            if dateType == 'week':
                self.dateTypeDatas['week'] = self.initWeekModelData(dayData)
            elif dateType == 'month':
                self.dateTypeDatas['month'] = self.initMonthModelData(dayData)
            self.data = self.dateTypeDatas[dateType]
            self.calcMA(5)
            self.calcMA(10)
            self.calcZhangFu()
        else:
            self.data = self.dateTypeDatas[dateType]

    def _mergeItem(self, dest, item):
        if hasattr(item, 'day'):
            dest.day = item.day
        if hasattr(item, 'high'):
            dest.high = max(getattr(dest, 'high', 0), item.high)
        if hasattr(item, 'low'):
            dest.low = min(getattr(dest, 'low', 99999999), item.low)
        if hasattr(item, 'close'):
            dest.close = item.close
        if hasattr(item, 'amount'):
            dest.amount = getattr(dest, 'amount', 0) + item.amount
        if hasattr(item, 'vol'):
            dest.vol = getattr(dest, 'vol', 0) + item.vol
        if hasattr(item, 'rate'):
            dest.rate = getattr(dest, 'rate', 0) + item.rate
        dest.days += 1

    def _copyItem(self, item):
        it = copy.copy(item)
        EX = ('MA5', 'MA10', 'zhangFu', 'lbs', 'zdt', 'tdb')
        for k in EX:
            if hasattr(it, k):
                delattr(it, k)
        it.days = 1
        return it

    def initWeekModelData(self, ds):
        rs = []
        if not ds:
            return rs
        cur = None
        week = None
        for item in ds:
            dd = datetime.date(item.day // 10000, item.day // 100 % 100, item.day % 100)
            w = dd.isocalendar()[1]
            if cur == None or week != w:
                week = w
                cur = self._copyItem(item)
                rs.append(cur)
            else:
                self._mergeItem(cur, item)
        return rs

    def initMonthModelData(self, ds):
        rs = []
        cur = None
        for item in ds:
            if cur == None or item.day // 100 != cur.day // 100:
                cur = self._copyItem(item)
                rs.append(cur)
            else:
                self._mergeItem(cur, item)
        return rs

# 指标 Vol, Amount, Rate等
class Indicator:
    # config = { height: int 必填
    #            margins: (top, bottom)  可选
    #            name: ''
    #            title: 'xx'
    #        }
    def __init__(self, config = None) -> None:
        self.klineWin = None
        self.config = config or {}
        self.data = None
        self.valueRange = None
        self.visibleRange = None
        self.width = 0
        self.height = 0

    def getSimpleStrCode(self, code):
        if code == None:
            return None
        if type(code) == int:
            return f'{code :06d}'
        if len(code) == 8 and (code[0 : 2] == 'sh' or code[0 : 2] == 'sz'):
            return code[2 : ]
        return code

    def init(self, klineWin):
        self.klineWin = klineWin

    def setData(self, data):
        self.data = data
        self.valueRange = None
        self.visibleRange = None

    def changeDateType(self, dateType):
        pass

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
            return 'red'
        return 'light_green'

    def draw(self, hdc, pens, hbrs):
        pass

    def getItemWidth(self):
        return self.klineWin.klineWidth

    def getItemSpace(self):
        return self.klineWin.klineSpace

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
        return False

class RefZSKDrawer:
    def __init__(self) -> None:
        self.model = None # 关联指数
        self.code = None
        self.zsCode = None
        self.newData = None
        self.valueRange = None
        self.klineWin = None

    def updateData(self, code):
        if not code or self.code == code:
            return
        if code[0 : 2] in ('sh', 'sz'):
            code = code[2 : ]
        self.code = code
        self.model = None
        if code[0] not in ('3', '0', '6'):
            return
        gntc = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if not gntc or not gntc.hy:
            return
        hys = gntc.hy.split('-')
        zs = ths_orm.THS_ZS.get_or_none(ths_orm.THS_ZS.name == hys[1])
        if not zs:
            return
        #if zs.code == self.zsCode:
        #    return
        self.updateRefZsData(zs.code)

    def updateRefZsData(self, zsCode):
        self.zsCode = zsCode
        self.model = KLineModel_DateType(zsCode)
        self.model.loadDataFile()
        self.model.calcZhangFu()

    def changeDateType(self, dateType):
        if self.model:
            self.model.changeDateType(dateType)

    def drawKLineItem(self, hdc, pens, hbrs, idx, cx, itemWidth, getYAtValue):
        if not self.newData:
            return
        if idx < 0 or idx >= len(self.newData):
            return
        bx = cx - itemWidth // 2
        ex = bx + itemWidth
        data = self.newData[idx]
        rect = [bx, getYAtValue(data.open), ex, getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        if 'ref-zs-color' not in pens:
            pens['ref-zs-color'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xE19800)
        if 'ref-zs-color' not in hbrs:
            hbrs['ref-zs-color'] = win32gui.CreateSolidBrush(0xE19800)
        win32gui.SelectObject(hdc, pens['ref-zs-color'])
        win32gui.MoveToEx(hdc, cx, getYAtValue(data.low))
        win32gui.LineTo(hdc, cx, getYAtValue(min(data.open, data.close)))
        win32gui.MoveToEx(hdc, cx, getYAtValue(max(data.open, data.close)))
        win32gui.LineTo(hdc, cx, getYAtValue(data.high))
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, tuple(rect), hbrs['ref-zs-color'])

    def calcPercentPrice(self, data, fromIdx, endIdx, startDay):
        self.newData = []
        self.valueRange = None
        if not self.model or not self.model.data:
            return
        sidx = self.model.getItemIdx(startDay)
        if sidx < 0:
            nidx = self.klineWin.model.getItemIdx(self.model.data[0].day)
            if nidx < 0:
                return
            p = self.model.data[0].open / data[nidx].open
            skip = nidx - fromIdx
            sidx = -skip
        else:
            p = self.model.data[sidx].open / data[fromIdx].open
        maxVal, minVal = 0, 9999999
        last = None
        for i in range(fromIdx, endIdx):
            it = datafile.ItemData()
            di = i - fromIdx + sidx
            if di < 0:
                first = self.model.data[0]
                it.open = it.close = it.low = it.high = first.open / p
                self.newData.append(it)
                continue
            if di < len(self.model.data):
                cur = self.model.data[di]
                it.open = cur.open / p
                it.close = cur.close / p
                it.low = cur.low / p
                it.high = cur.high / p
                last = cur
            else:
                cur = last # only for fix bug
                it.open = it.close = it.low = it.high = cur.open / p
            self.newData.append(it)
            
            maxVal = max(maxVal, it.high)
            minVal = min(minVal, it.low)
        self.valueRange = (minVal, maxVal)

    def getZhangFu(self, day):
        if not self.model:
            return None
        item = self.model.getItemData(day)
        if not item:
            return None
        if hasattr(item, 'zhangFu'):
            return item.zhangFu
        return None

class KLineIndicator(Indicator):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.markDays = {} # int items
        self.refZSDrawer = RefZSKDrawer()
        self.visibleRefZS = True

    def init(self, klineWin):
        super().init(klineWin)
        self.refZSDrawer.klineWin = klineWin

    def setData(self, data):
        super().setData(data)
        if data:
            self.refZSDrawer.updateData(self.klineWin.model.code)

    def changeDateType(self, dateType):
        self.refZSDrawer.changeDateType(dateType)

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
        self.refZSDrawer.calcPercentPrice(self.data, fromIdx, endIdx, self.klineWin.model.data[fromIdx].day)
        # merge ref zs value range
        if self.refZSDrawer.valueRange:
            vr = self.refZSDrawer.valueRange
            if minVal > vr[0]: minVal = vr[0]
            if maxVal < vr[1]: maxVal = vr[1]
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
        if not self.klineWin.model:
            return 'light_green'
        code = self.klineWin.model.code
        if code[0 : 2] == '88' and idx > 0: # 指数
            zdfd = abs((self.data[idx].close - self.data[idx - 1].close) / self.data[idx - 1].close * 100)
            mdfd = abs((max(self.data[idx].high, self.data[idx - 1].close)- self.data[idx].low) / self.data[idx - 1].close * 100)
            if zdfd >= 3.5 or mdfd >= 3.5:
                return '0xff00ff'
        if getattr(data, 'tdb', False):
            return 'green'
        zdt = getattr(data, 'zdt', None)
        if zdt == 'ZT' or zdt == 'ZTZB':
            return 'blue'
        if zdt == 'DT' or zdt == 'DTZB':
            return 'yellow'
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        for mk in self.markDays:
            self.drawMarkDay(mk, hdc, pens, hbrs)
        self.drawHilight(hdc, pens, hbrs, self.klineWin.selIdx)
        if self.klineWin.mouseXY and self.klineWin.selIdxOnClick:
            si = self.getIdxAtX(self.klineWin.mouseXY[0])
            self.drawHilight(hdc, pens, hbrs, si)
        #sm = base_win.ThsShareMemory.instance()
        #if sm.readMarkDay() != 0:
        #    self.drawMarkDay(sm.readMarkDay(), hdc, pens, hbrs)
        self.drawKLines(hdc, pens, hbrs)
        self.drawMA(hdc, 5)
        self.drawMA(hdc, 10)

    def drawHilight(self, hdc, pens, hbrs, selIdx):
        if not self.klineWin.model or not self.visibleRange:
            return
        if selIdx < 0 or selIdx >= self.visibleRange[1] or selIdx < self.visibleRange[0]:
            return
        x = self.getCenterX(selIdx)
        sx = x - self.getItemWidth() // 2 #- self.getItemSpace()
        ex = x + self.getItemWidth() // 2 #+ self.getItemSpace()
        mr = self.config['margins'] or (0, 0)
        rc = (sx, 0, ex, self.height + mr[1])
        pen = win32gui.GetStockObject(win32con.NULL_PEN)
        win32gui.SelectObject(hdc, pen)
        win32gui.FillRect(hdc, rc, hbrs['hilight'])
    
    def drawMarkDay(self, markDay, hdc, pens, hbrs):
        if not markDay or not self.klineWin.model or not self.visibleRange:
            return
        idx = self.klineWin.model.getItemIdx(markDay)
        if idx < 0:
            return
        if idx < self.visibleRange[0] or idx >= self.visibleRange[1]:
            return
        x = self.getCenterX(idx)
        sx = x - self.getItemWidth() // 2# - self.getItemSpace()
        ex = x + self.getItemWidth() // 2# + self.getItemSpace()
        rc = (sx, 0, ex, self.height)
        pen = win32gui.GetStockObject(win32con.NULL_PEN)
        win32gui.SelectObject(hdc, pen)
        win32gui.FillRect(hdc, rc, hbrs['drak'])
        # draw tip
        if markDay not in self.markDays:
            return
        md = self.markDays[markDay]
        if not md['tip']:
            return
        rc = (sx - 30, self.height - 35, ex + 30, self.height)
        drawer : base_win.Drawer = self.klineWin.drawer
        drawer.drawText(hdc, md['tip'], rc, color = 0x404040, align = win32con.DT_CENTER | win32con.DT_WORDBREAK | win32con.DT_VCENTER)

    def drawKLineItem(self, idx, hdc, pens, hbrs, fillHbr):
        data = self.data[idx]
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(data.open), ex, self.getYAtValue(data.close)]
        if rect[1] == rect[3]:
            rect[1] -=1
        color = self.getColor(idx, data)

        win32gui.SelectObject(hdc, pens[color])
        win32gui.MoveToEx(hdc, cx, self.getYAtValue(data.low))
        win32gui.LineTo(hdc, cx, self.getYAtValue(min(data.open, data.close)))
        win32gui.MoveToEx(hdc, cx, self.getYAtValue(max(data.open, data.close)))
        win32gui.LineTo(hdc, cx, self.getYAtValue(data.high))
        if data.close >= data.open:
            nullHbr = win32gui.GetStockObject(win32con.NULL_BRUSH)
            win32gui.SelectObject(hdc, nullHbr)
            #win32gui.SelectObject(hdc, fillHbr)
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, tuple(rect), hbrs[color])
    
    def drawKLines(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        vr = self.visibleRange
        for idx in range(*vr):
            cx = self.getCenterX(idx)
            if self.visibleRefZS:
                self.refZSDrawer.drawKLineItem(hdc, pens, hbrs, idx - vr[0], cx, self.getItemWidth(), self.getYAtValue)
            self.drawKLineItem(idx, hdc, pens, hbrs, hbrs['black'])

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        SP = self.height // 4
        for i in range(0, 4):
            y = SP * i
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, self.width, y)
            price = self.getValueAtY(y)
            if not price:
                continue
            price = price['fmtVal']
            win32gui.SetTextColor(hdc, 0xab34de)
            x = self.width + 20
            rt = (x, y - 8, x + 60, y + 8)
            win32gui.DrawText(hdc, price, len(price), rt, win32con.DT_LEFT)

    def drawMA(self, hdc, n):
        vr = self.visibleRange
        if not vr:
            return
        if n == 5:
            pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, pen)
        elif n == 10:
            pen = win32gui.CreatePen(win32con.PS_SOLID, 2, 0xee00ee)
            win32gui.SelectObject(hdc, pen)
        bi = vr[0]

        ma = f'MA{n}'
        moveToFlag = False
        for i in range(bi, vr[1]):
            if not moveToFlag:
                mx = getattr(self.data[i], ma, 0)
                if mx > 0:
                    win32gui.MoveToEx(hdc, self.getCenterX(i), self.getYAtValue(mx))
                    moveToFlag = True
                continue
            win32gui.LineTo(hdc, self.getCenterX(i), self.getYAtValue(getattr(self.data[i], ma)))
        win32gui.DeleteObject(pen)
    
    def onMouseClick(self, x, y):
        if self.klineWin.selIdxOnClick:
            si = self.getIdxAtX(x)
            self.klineWin.setSelIdx(si)
        return True
    
class AmountIndicator(Indicator):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.config['title'] = '[成交额]'

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        if fromIdx < 0 or endIdx < 0:
            return
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = getattr(d, 'amount', 0)
                minVal = getattr(d, 'amount', 0)
            else:
                maxVal = max(maxVal, getattr(d, 'amount', 0))
                minVal = min(minVal, getattr(d, 'amount', 0))
        self.valueRange = (0, maxVal)

    def getValueAtY(self, y):
        rr = self.valueRange
        if not rr:
            return None
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val / 100000000 :.1f}亿', 'valType': 'Amount'}
    
    def getColor(self, idx, data):
        if idx > 0:
            rv = getattr(data, 'amount', 0)
            prv = getattr(self.data[idx - 1], 'amount', 0)
            if prv > 0 and rv / prv >= 2: # 倍量
                return 'blue'
        return super().getColor(idx, data)

    def drawItem(self, idx, hdc, pens, hbrs):
        data = self.data[idx]
        if not hasattr(data, 'amount') or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = [bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.amount) + 1]
        if rect[3] - rect[1] == 0 and data.amount > 0:
            rect[1] -= 1
        if idx == self.klineWin.selIdx:
            mr = self.config['margins'] or (8, 0)
            hr = (rect[0], -mr[0] + 1, rect[2], rect[3])
            win32gui.FillRect(hdc, hr, hbrs['hilight'])
        rect = tuple(rect)
        color = self.getColor(idx, data)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, pens, hbrs)
        win32gui.SelectObject(hdc, pens['dark_red'])
        self.drawAmountTip(hdc, pens, hbrs)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        rc = (0, 2, 100, 20)
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

    def drawAmountTip(self, hdc, pens, hbrs):
        if not self.klineWin.model or self.klineWin.model.code[0] == '8' or self.klineWin.model.code[0 : 3] == '399':
            return
        亿 = 100000000
        w = self.width
        if self.valueRange[1] >= 5 * 亿 and 5 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['blue'])
            y = self.getYAtValue(5 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 10 * 亿 and 10 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['0xff00ff'])
            y = self.getYAtValue(10 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 20 * 亿 and 20 * 亿  >= self.valueRange[0]:
            win32gui.SelectObject(hdc, pens['yellow'])
            y = self.getYAtValue(20 * 亿)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        y = self.getYAtValue(self.valueRange[1])
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, self.width, y)
        win32gui.SetTextColor(hdc, 0xab34de)
        txt = f'{self.valueRange[1] / 100000000 :.1f}亿'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        win32gui.DrawText(hdc, txt, len(txt), rt, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

class RateIndicator(Indicator):
    def __init__(self, config = None) -> None:
        super().__init__(config)
        self.config['title'] = '[换手率]'

    def calcValueRange(self, fromIdx, endIdx):
        self.valueRange = None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.data[i]
            if maxVal == 0:
                maxVal = getattr(d, 'rate', 0)
                minVal = getattr(d, 'rate', 0)
            else:
                maxVal = max(maxVal, getattr(d, 'rate', 0))
                minVal = min(minVal, getattr(d, 'rate', 0))
        self.valueRange = (0, maxVal)

    def getValueAtY(self, y):
        if not self.valueRange:
            return None
        rr = self.valueRange
        m = (rr[1] - rr[0]) / self.height
        val = int(rr[1] - y * m)
        return {'value': val, 'fmtVal': f'{val :.1f}%', 'valType': 'Rate'}

    def getColor(self, idx, data):
        if data.close >= data.open:
            return 'red'
        return 'light_green'

    def drawItem(self, idx, hdc, pens, hbrs):
        data = self.data[idx]
        if not hasattr(data, 'rate') or not self.valueRange:
            return
        cx = self.getCenterX(idx)
        bx = cx - self.getItemWidth() // 2
        ex = bx + self.getItemWidth()
        rect = (bx, self.getYAtValue(self.valueRange[0]), ex, self.getYAtValue(data.rate) + 1)
        if idx == self.klineWin.selIdx:
            mr = self.config['margins'] or (8, 0)
            hr = (rect[0], -mr[0] + 1, rect[2], rect[3])
            win32gui.FillRect(hdc, hr, hbrs['hilight'])
        color = self.getColor(idx, data)
        win32gui.SelectObject(hdc, pens[color])
        if data.close >= data.open:
            win32gui.SelectObject(hdc, hbrs['black'])
            win32gui.Rectangle(hdc, *rect)
        else:
            win32gui.FillRect(hdc, rect, hbrs[color])

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        self.drawBackground(hdc, pens, hbrs)
        w = self.width
        for idx in range(*self.visibleRange):
            self.drawItem(idx, hdc, pens, hbrs)
        if self.valueRange[1] >= 5:
            win32gui.SelectObject(hdc, pens['blue'])
            y = self.getYAtValue(5)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 10:
            win32gui.SelectObject(hdc, pens['0xff00ff'])
            y = self.getYAtValue(10)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        if self.valueRange[1] >= 20:
            win32gui.SelectObject(hdc, pens['yellow'])
            y = self.getYAtValue(20)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        wc, *_ = win32gui.GetTextExtentPoint32(hdc, title)
        rc = (0, 2, wc + 5, 20)
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

    def drawBackground(self, hdc, pens, hbrs):
        sdc = win32gui.SaveDC(hdc)
        win32gui.SelectObject(hdc, pens['bk_dot_red'])
        y = self.getYAtValue(self.valueRange[1])
        win32gui.MoveToEx(hdc, 0, y)
        win32gui.LineTo(hdc, self.width, y)
        win32gui.SetTextColor(hdc, 0xab34de)
        txt = f'{self.valueRange[1] :.1f}%'
        rt = (self.width + 20, y - 8, self.width + 100, y + 8)
        win32gui.DrawText(hdc, txt, len(txt), rt, win32con.DT_LEFT)
        win32gui.RestoreDC(hdc, sdc)

# config = {itemWidth: int}
class CustomIndicator(Indicator):
    def __init__(self, config = None) -> None:
        super().__init__(config)
        if 'itemWidth' not in self.config:
            self.config['itemWidth'] = 80
        self.customData = None

    def init(self, klineWin):
        super().init(klineWin)
        self.klineWin.addListener(self.onSelIdxChanged, None)

    def onSelIdxChanged(self, evt, args):
        if evt.name != 'selIdx.changed':
            return
        idx = evt.selIdx
        self.calcVisibleRange(idx)
        if self.visibleRange:
            self.calcValueRange(*self.visibleRange)

    def getItemWidth(self):
        return self.config['itemWidth']

    def getItemSpace(self):
        return 1
    
    def setCustomData(self, datas):
        self.customData = datas
        if not self.customData:
            return
        for c in self.customData:
            day = c['day']
            if type(day) == str:
                day = day.replace('-', '')
                day = int(day)
            c['__day'] = day

    def translateIdx(self, idx):
        if not self.data or not self.customData:
            return -1
        day = int(self.data[idx].day)
        newIdx = -1
        for i, d in enumerate(self.customData):
            if d['__day'] == day:
                newIdx = i
                break
        return newIdx

    def calcVisibleRange(self, idx):
        if not self.data or not self.customData:
            self.visibleRange = None
            return
        idx = self.translateIdx(idx)
        self.visibleRange = self.calcVisibleRange_1(idx, self.customData)

    def _calcValueRange(self, fromIdx, endIdx, attrName):
        if not self.customData:
            return None
        maxVal = minVal = 0
        for i in range(fromIdx, endIdx):
            d = self.customData[i]
            if maxVal == 0:
                maxVal = d.get(attrName, 0)
                minVal = d.get(attrName, 0)
            else:
                maxVal = max(maxVal, d.get(attrName, 0))
                minVal = min(minVal, d.get(attrName, 0))
        return (0, maxVal)

    def getValueAtY(self, y):
        return

    def getColor(self, idx, data):
        return 'black'

    def drawItem(self, idx, hdc, pens, hbrs, x):
        data = self.customData[idx]
        pass

    def draw(self, hdc, pens, hbrs):
        if not self.visibleRange:
            return
        vr = self.visibleRange
        itemWidth = self.config['itemWidth']
        for idx in range(*vr):
            i = (idx - vr[0])
            self.drawItemBackground(idx, hdc, pens, hbrs, i * itemWidth)
            self.drawItem(idx, hdc, pens, hbrs, i * itemWidth)
        # draw title
        title = self.config.get('title', None)
        if not title:
            return
        wc, *_ = win32gui.GetTextExtentPoint32(hdc, title)
        rc = (0, 2, wc + 5, 20)
        win32gui.FillRect(hdc, rc, hbrs['black'])
        win32gui.SetTextColor(hdc, 0xab34de)
        win32gui.DrawText(hdc, title, -1, rc, win32con.DT_LEFT)

    def drawItemBackground(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        win32gui.SelectObject(hdc, pens['light_drak_dash_dot'])
        win32gui.MoveToEx(hdc, x + WW, 0)
        win32gui.LineTo(hdc, x + WW, self.height)

    def changeSelIdx(self, x, y):
        if not self.visibleRange or not self.data or not self.customData:
            return False
        vr = self.visibleRange
        itemWidth = self.config['itemWidth']
        idx = x // itemWidth + vr[0]
        if idx >= vr[1]:
            return False
        dx = x % itemWidth
        # click item idx
        itemData = self.customData[idx]
        if not itemData:
            return False
        day = itemData.get('__day', None)
        if not day:
            return False
        idx = self.klineWin.model.getItemIdx(day)
        if idx < 0:
            return False
        old = self.klineWin.selIdx
        self.klineWin.setSelIdx(idx)
        return self.klineWin.selIdx != old

    def onMouseClick(self, x, y):
        changed = self.changeSelIdx(x, y)
        return True

    def onContextMenu(self, x, y):
        self.klineWin.invalidWindow() # redraw
        return True

class DdlrIndicator(CustomIndicator):
    PADDING_TOP = 25
    def __init__(self, config = None, isDetail = True) -> None:
        super().__init__(config)
        if isDetail:
            self.config['title'] = '[大单流入]'
            if 'height' not in self.config:
                self.config['height'] = 100
        else:
            self.config['title'] = '[大单净流入]'
            if 'show-rate' not in self.config:
                self.config['show-rate'] = False
            if 'height' not in self.config:
                self.config['height'] = 30
        self.isDetail = isDetail

    def setData(self, data):
        super().setData(data)
        if not data:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        ddlr = ths_orm.THS_DDLR.select().where(ths_orm.THS_DDLR.code == code).order_by(ths_orm.THS_DDLR.day.asc()).dicts()
        maps = {}
        for d in ddlr:
            d['in'] = d['activeIn'] + d['positiveIn']
            d['out'] = d['activeOut'] + d['positiveOut']
            if d['amount'] > 0:
                d['ddRate'] = int(max(d['in'], d['out']) / d['amount'] * 100)
            else:
                d['ddRate'] = 0
            maps[int(d['day'])] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': str(d.day), 'isNone': True, 'in': 0, 'out': 0, 'ddRate' : 0, 'total': 0}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        if self.isDetail:
            self.drawItem_Detail(idx, hdc, pens, hbrs, x)
        else:
            self.drawItem_Sum(idx, hdc, pens, hbrs, x)
    
    def drawItem_Sum(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        if 'isNone' in data:
            return
        jlr = f"{data['total']: .1f} 亿"
        zb = f"({data['ddRate']}%)"
        if self.config['show-rate']:
            HH = self.height // 2
        else:
            HH = self.height
        if data['total'] > 0:
            win32gui.SetTextColor(hdc, 0x0000dd)
        elif data['total'] < 0:
            win32gui.SetTextColor(hdc, 0x00dd00)
        else:
            win32gui.SetTextColor(hdc, 0xcccccc)
        win32gui.DrawText(hdc, jlr, -1, (x, 0, x + WW, HH), win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        if self.config['show-rate']:
            win32gui.DrawText(hdc, zb, -1, (x, HH, x + WW, self.height), win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def drawItem_Detail(self, idx, hdc, pens, hbrs, x):
        if not self.valueRange:
            return
        WW = self.config['itemWidth']
        ITW = 5
        sx = x + 20
        data = self.customData[idx]
        sy = self.getYAtValue(data['in'])
        rc = (sx, sy, sx + ITW, self.getYAtValue(0))
        win32gui.FillRect(hdc, rc, hbrs['red'])
        rcx = (sx - 15, 3, sx + 15 + ITW, self.PADDING_TOP)
        if data['in'] > 0:
            win32gui.DrawText(hdc, f"{data['in'] :.1f}", -1, rcx, win32con.DT_CENTER)

        sx = rc[2] + 30
        sy = self.getYAtValue(data['out'])
        rc = (sx, sy, sx + ITW, self.getYAtValue(0))
        win32gui.FillRect(hdc, rc, hbrs['green'])
        rcx = (sx - 15, 3, sx + 15 + ITW, self.PADDING_TOP)
        if data['out'] > 0:
            win32gui.DrawText(hdc, f"{data['out'] :.1f}", -1, rcx, win32con.DT_CENTER)

    def getYAtValue(self, value):
        return self.getYAtValue2(value, self.height - self.PADDING_TOP - 3) + self.PADDING_TOP

    def calcValueRange(self, fromIdx, endIdx):
        vrIn = self._calcValueRange(fromIdx, endIdx, 'in')
        vrOut = self._calcValueRange(fromIdx, endIdx, 'out')
        if not vrIn or not vrOut:
            self.valueRange = None
        else:
            self.valueRange = (0, max(vrIn[1], vrOut[1]))

class DdlrPmIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        super().__init__(config)
        self.config['title'] = '[成交额排名]'
        if 'height' not in self.config:
            self.config['height'] = 30

    def setData(self, data):
        super().setData(data)
        if not data:
            self.setCustomData(None)
            return
        rs = []
        maps = {}
        code = self.getSimpleStrCode(self.klineWin.model.code)
        qr = tdx_orm.TdxVolPMModel.select().where(tdx_orm.TdxVolPMModel.code == code).order_by(tdx_orm.TdxVolPMModel.day.asc()).dicts()
        maps = {}
        for d in qr:
            maps[int(d['day'])] = d
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': str(d.day), 'isNone': True, 'pm': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.DrawText(hdc, str(data['pm']), -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class HotIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        self.config['title'] = '[热度排名]'

    def setData(self, data):
        super().setData(data)
        model = self.klineWin.model
        code = self.getSimpleStrCode(model.code)
        if not model or not model.code or (type(code) == str and len(code) != 6):
            self.setCustomData(None)
            return
        hots = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.code == int(code)).order_by(ths_orm.THS_HotZH.day.asc()).dicts()
        maps = {}
        for d in hots:
            maps[d['day']] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'zhHotOrder': ''}
            rs.append(fd)
        # calc last 
        if rs:
            last = rs[-1]
            hot = hot_utils.DynamicHotZH.ins.getDynamicHotZH(last['day'], code)
            if hot:
                rs[-1] = hot

        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        if data['zhHotOrder']:
            win32gui.DrawText(hdc, str(data['zhHotOrder']), -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class LsAmountIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        self.config['title'] = '[两市成交额]'

    def setData(self, data):
        super().setData(data)
        maps = {}
        url = cls.ClsUrl()
        ds = url.loadKline('sh000001')
        for d in ds:
            maps[d.day] = d.amount / 1000000000000 # 万亿
        ds = url.loadKline('sz399001')
        for d in ds:
            maps[d.day] += d.amount / 1000000000000 # 万亿
        rs = []
        for d in data:
            amount = maps.get(d.day, 0)
            fd = {'day': d.day, 'amount': amount}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        WW = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + WW, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        if data['amount']:
            win32gui.DrawText(hdc, f"{data['amount'] :.02f}", -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)


class DayIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 20
        super().__init__(config)
    
    def setData(self, data):
        super().setData(data)
        days = [{'day': str(d.day)} for d in data]
        self.setCustomData(days)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        day = self.customData[idx]['day']
        hday = day[4 : 6] + '-' + day[6 : 8]
        today = datetime.date.today()
        if today.year != int(day[0 : 4]):
            day = day[2: 4] + '-' + hday
        else:
            day = hday
        win32gui.SetTextColor(hdc, 0xcccccc)
        win32gui.DrawText(hdc, day, -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class ThsZsPMIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[指数排名]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        hots = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.code == code).order_by(ths_orm.THS_ZS_ZD.day.asc()).dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'zdf_topLevelPM': 0, 'zdf_PM': 0}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        data = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(data['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        cdata = self.customData[idx]
        win32gui.SetTextColor(hdc, 0xcccccc)

        if cdata['zdf_topLevelPM'] != 0:
            sy = 5
            rc = (x, sy, x + iw, sy + 16)
            win32gui.DrawText(hdc, f"{cdata['zdf_topLevelPM'] :<3d}", -1, rc, win32con.DT_CENTER) #  | win32con.DT_VCENTER | win32con.DT_SINGLELINE

        if cdata['zdf_PM'] != 0:
            sy = 25
            rc = (x, sy, x + iw, sy + 16)
            win32gui.DrawText(hdc, f"{cdata['zdf_PM'] :<3d}", -1, rc, win32con.DT_CENTER) 

class ThsZT_Indicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 50
        if 'itemWidth' not in config:
            config['itemWidth'] = 80
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[同花顺涨停]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        hots = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.code == code).order_by(tck_orm.THS_ZT.day.asc()).dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'ztReason': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.SetTextColor(hdc, 0xcccccc)
        rc = (x + 3, 3, x + iw - 3, self.height)
        drawer : base_win.Drawer = self.klineWin.drawer
        drawer.use(hdc, drawer.getFont(fontSize = 12))
        win32gui.DrawText(hdc, cdata['ztReason'], -1, rc, win32con.DT_WORDBREAK) #  | win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_CENTER | 

class ClsZT_Indicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        if 'itemWidth' not in config:
            config['itemWidth'] = 80
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[财联社涨停]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.getSimpleStrCode(self.klineWin.model.code)
        hots = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.code == code).order_by(tck_orm.CLS_ZT.day.asc()).dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'ztReason': ''}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.SetTextColor(hdc, 0xcccccc)
        rc = (x + 3, 3, x + iw - 3, self.height)
        drawer : base_win.Drawer = self.klineWin.drawer
        drawer.use(hdc, drawer.getFont(fontSize = 12))
        win32gui.DrawText(hdc, cdata['ztReason'], -1, rc, win32con.DT_WORDBREAK) #  | win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_CENTER | 

    def onMouseClick(self, x, y):
        if self.changeSelIdx(x, y):
            return True
        if not self.visibleRange:
            return True
        itemWidth = self.config['itemWidth']
        idx = x // itemWidth + self.visibleRange[0]
        if idx >= len(self.customData):
            return True
        # click item idx
        itemData = self.customData[idx]
        if not itemData:
            return True
        detail = itemData.get('detail', '')
        if not detail:
            return True
        # draw tip
        self.klineWin.invalidWindow()
        win32gui.UpdateWindow(self.klineWin.hwnd)
        hdc = win32gui.GetDC(self.klineWin.hwnd)
        W, H = int(self.width * 0.8), 70
        drawer : base_win.Drawer = self.klineWin.drawer
        sx = (self.width - W) // 2 + self.x
        sy = self.y - H
        rc = [sx, sy, sx + W, sy + H]
        drawer.fillRect(hdc, rc, 0x101010)
        drawer.drawRect(hdc, rc, 0xa0f0a0)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        drawer.use(hdc, drawer.getFont())
        rc[0] += 5
        rc[1] += 3
        rc[2] -= 5
        rc[3] -= 3
        drawer.drawText(hdc, detail, rc, color = 0xd0a0a0, align = win32con.DT_WORDBREAK)
        win32gui.ReleaseDC(self.klineWin.hwnd, hdc)
        return True

class ScqxIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[市场情绪]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        hots = tck_orm.CLS_SCQX.select().dicts()
        maps = {}
        for d in hots:
            day = d['day'].replace('-', '')
            maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'zhqd': ''}
            rs.append(fd)
        if rs and not rs[-1]['zhqd']:
            val = cls.ClsUrl().loadDegree()
            last = rs[-1]
            if val and last['day'] == int(val['day'].replace('-', '')):
                last['zhqd'] = val['degree']
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        rc = (x + 3, 3, x + iw - 3, self.height)
        if cdata['zhqd']:
            val = cdata['zhqd']
            color = 0xcccccc
            if val >= 60: color = 0x0000FF
            elif val >= 40: color = 0x1D77FF
            else: color = 0x00ff00 #0x24E7C8
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, str(val) + '°', -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class DdeIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[DDE-亿元]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        from Download import ths_iwencai
        rsx = ths_iwencai.download_one_dde(self.klineWin.model.code)
        maps = {}
        for d in rsx:
            if d.get('时间', None):
                day = d['时间'].replace('-', '')
                maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'dde大单净额': None}
            else:
                fd['day'] = d.day
            rs.append(fd)
        self.setCustomData(rs)

    def onMouseClick(self, x, y):
        if self.changeSelIdx(x, y):
            return True
        if not self.visibleRange:
            return True
        itemWidth = self.config['itemWidth']
        idx = x // itemWidth + self.visibleRange[0]
        # click item idx
        itemData = self.customData[idx]
        if not itemData:
            return True
        self.klineWin.invalidWindow()
        win32gui.UpdateWindow(self.klineWin.hwnd)
        code = self.klineWin.model.code
        day = itemData['day']
        sday = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        qr = ths_orm.THS_DDE.select().where(ths_orm.THS_DDE.code == code, ths_orm.THS_DDE.day == sday)
        detail = ''
        for q in qr:
            detail = f'排名：{q.dde_pm}'
            break
        if not detail:
            return True
        # draw tip
        hdc = win32gui.GetDC(self.klineWin.hwnd)
        W, H = 120, 50
        ix = x // itemWidth * itemWidth
        drawer : base_win.Drawer = self.klineWin.drawer
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
        rc[0] += 5
        rc[1] += 3
        rc[2] -= 5
        rc[3] -= 3
        drawer.drawText(hdc, detail, rc, color = 0xd0a0a0, align = win32con.DT_WORDBREAK)
        win32gui.ReleaseDC(self.klineWin.hwnd, hdc)
        return True

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        rc = (x + 3, 3, x + iw - 3, self.height)
        if cdata.get('dde大单净额', None):
            val = float(cdata['dde大单净额']) / 100000000 # 亿元
            color = 0xcccccc
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, f'{val :.1f}', -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

class LhbIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[龙虎榜]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.klineWin.model.code
        q = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.code == code).dicts()
        maps = {}
        for d in q:
            day = d['day'].replace('-', '')
            old = maps.get(int(day), None)
            if old:
                if '累计' in old['title']:
                    maps[int(day)] = d
            else:
                maps[int(day)] = d
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'title': None, 'detail': ''}
            else:
                fd['day'] = d.day
                fd['detail'] = json.loads(fd['detail'])
            rs.append(fd)
        self.setCustomData(rs)

    def onMouseClick(self, x, y):
        if self.changeSelIdx(x, y):
            return True
        if not self.visibleRange:
            return True
        itemWidth = self.config['itemWidth']
        idx = x // itemWidth + self.visibleRange[0]
        # click item idx
        self.klineWin.invalidWindow()
        win32gui.UpdateWindow(self.klineWin.hwnd)
        itemData = self.customData[idx]
        if not itemData or not itemData['detail']:
            return True
        code = self.klineWin.model.code
        day = itemData['day']
        sday = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        # draw tip
        hdc = win32gui.GetDC(self.klineWin.hwnd)
        W, H = 400, 240
        ix = x // itemWidth * itemWidth
        drawer : base_win.Drawer = self.klineWin.drawer
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
        #drawer.drawText(hdc, itemData['detail'], rc, color = 0xd0a0a0, align = win32con.DT_WORDBREAK)
        self.drawItemDetail(drawer, hdc, rc, itemData)
        win32gui.ReleaseDC(self.klineWin.hwnd, hdc)
        return True
    
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
    
    def drawItemDetail(self, drawer : base_win.Drawer, hdc, rect, itemData):
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

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        rc = (x + 3, 3, x + iw - 3, self.height)
        if cdata['detail']:
            color = 0xcccccc
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, f'Y', -1, rc, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

# 涨速，用于指明进攻意愿
class ZhangSuIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[涨速]'

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.klineWin.model.code
        qr = speed_orm.LocalSpeedModel.select().where(speed_orm.LocalSpeedModel.code == code).dicts()
        maps = {}
        for d in qr:
            day = d['day']
            if day not in maps:
                maps[day] = [d]
            else:
                maps[day].append(d)
        rs = []
        for d in data:
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'val': None}
            else:
                fd = {'day': d.day, 'val': fd}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        if selDay == int(cdata['__day']):
            win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        if not cdata or not cdata.get('val', None):
            return
        
        MAX_ITEM_ZF = 5
        IW = 2
        zs = 0
        for it in cdata['val']:
            zs += it['zf']
        import math
        aw = math.ceil(zs / MAX_ITEM_ZF)
        w = aw * IW
        sx = (iw - w) // 2 + x
        y = int(self.height * 0.3)
        rc = (sx, y, sx + w, self.height - 1)
        drawer : base_win.Drawer = self.klineWin.drawer
        drawer.fillRect(hdc, rc, 0x3C14DC)

# 概念联动
class GnLdIndicator(CustomIndicator):
    def __init__(self, config = None) -> None:
        config = config or {}
        if 'height' not in config:
            config['height'] = 30
        super().__init__(config)
        if 'title' not in self.config:
            self.config['title'] = '[联动]'
        self.clsGntc = None
        self.curGntc = ''
        self.hotsData = None

    def setData(self, data):
        super().setData(data)
        if not self.klineWin.model:
            self.setCustomData(None)
            return
        code = self.klineWin.model.code
        # load gntc
        obj = cls_orm.CLS_GNTC.get_or_none(code = code)
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

    def changeGntc(self, gntc, force = False):
        if self.curGntc == gntc and not force:
            return
        self.curGntc = gntc or ''
        self.config['title'] = f'[联动-{self.curGntc}]'

        qr = tck_orm.CLS_HotTc.select().where(tck_orm.CLS_HotTc.name == self.curGntc).dicts()
        maps = {}
        for d in qr:
            day = int(d['day'].replace('-', ''))
            if day not in maps:
                maps[day] = [d]
            else:
                maps[day].append(d)
        rs = []
        for d in (self.data or []):
            fd = maps.get(d.day, None)
            if not fd:
                fd = {'day': d.day, 'items': None}
            else:
                fd = {'day': d.day, 'items': fd}
            rs.append(fd)
        self.setCustomData(rs)

    def drawItem(self, idx, hdc, pens, hbrs, x):
        iw = self.config['itemWidth']
        cdata = self.customData[idx]
        selIdx = self.klineWin.selIdx
        selData = self.data[selIdx] if selIdx >= 0 and selIdx < len(self.data) else None
        selDay = int(selData.day) if selData else 0
        rc = (x + 1, 1, x + iw, self.height)
        #if selDay == int(cdata['__day']):
        win32gui.FillRect(hdc, rc, hbrs['mask']) # light_dark
        if not cdata or not cdata.get('items', None):
            return
        
        items = cdata['items']
        IIW = 6
        w = IIW * len(items)
        sx = (iw - w) // 2 + x
        drawer : base_win.Drawer = self.klineWin.drawer
        y = int(self.height * 0.3)
        for it in items:
            rc = (sx, y, sx + IIW - 1, self.height - 1)
            if it['up']:
                drawer.fillRect(hdc, rc, 0xee2b8c)
            else:
                drawer.fillRect(hdc, rc, 0x3CDC14)
            sx += IIW

    def onContextMenu(self, x, y):
        menu = base_win.PopupMenu.create(self.klineWin.hwnd, self.clsGntc)
        menu.VISIBLE_MAX_ITEM = 8
        menu.addNamedListener('Select', self.onSelectItem)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)
        return True
    
    def onSelectItem(self, evt, args):
        item = evt.item
        self.changeGntc(item['name'])
        self.klineWin.invalidWindow()

    def onMouseClick(self, x, y):
        if self.changeSelIdx(x, y):
            return True
        if not self.visibleRange:
            return True
        itemWidth = self.config['itemWidth']
        idx = x // itemWidth + self.visibleRange[0]
        # click item idx
        if idx >= len(self.customData):
            return True
        itemData = self.customData[idx]
        if not itemData:
            return True
        items = itemData.get('items', None)
        if not items:
            return True
        # draw tip
        self.klineWin.invalidWindow()
        win32gui.UpdateWindow(self.klineWin.hwnd)
        hdc = win32gui.GetDC(self.klineWin.hwnd)
        W, H = 100, 70
        nidx =  x // itemWidth
        drawer : base_win.Drawer = self.klineWin.drawer
        if x >= self.width // 2:
            sx = nidx * itemWidth - W
        else:
            sx = nidx * itemWidth + itemWidth
        sx += self.x
        sy = self.y - H
        rc = [sx, sy, sx + W, sy + H]
        drawer.fillRect(hdc, rc, 0x101010)
        drawer.drawRect(hdc, rc, 0xa0f0a0)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        drawer.use(hdc, drawer.getFont())
        rc[0] += 5
        rc[1] += 3
        rc[2] -= 5
        rc[3] -= 3
        detail = '\n'.join((d['ctime'][0 : 5] + '  ' + ('+' if d['up'] else '-') for d in items))
        drawer.drawText(hdc, detail, rc, color = 0xd0a0a0, align = win32con.DT_WORDBREAK)
        win32gui.ReleaseDC(self.klineWin.hwnd, hdc)
        return True
    
class KLineSelTipWindow(base_win.BaseWindow):
    def __init__(self, klineWin) -> None:
        super().__init__()
        self.klineWin = klineWin
        klineWin.addNamedListener('selIdx.changed', self.onSelIdxChanged)

    def onSelIdxChanged(self, evt, args):
        self.invalidWindow()

    def onDraw(self, hdc):
        selIdx = self.klineWin.selIdx
        model = self.klineWin.model
        rc = (0, 0, *self.getClientSize())
        self.drawer.drawRect(hdc, rc, 0x0000dd)
        if selIdx < 0 or (not model) or (not model.data) or selIdx >= len(model.data):
            return
        d = model.data[selIdx]
        amx = d.amount / 100000000
        if amx >= 1000:
            am = f'{int(amx)}'
        elif amx > 100:
            am = f'{amx :.1f}'
        else:
            am =  f'{amx :.2f}'
        txt = f'涨幅\n{getattr(d, "zhangFu", 0):.2f}%\n\n成交额\n{am}亿' # 时间\n{d.day//10000}\n{d.day%10000:04d}\n\n
        if hasattr(d, 'rate'):
            txt += f'\n\n换手率\n{d.rate :.1f}%'
        self.drawer.drawText(hdc, txt, rc, 0xd0d0d0, win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_WORDBREAK)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCHITTEST:
            return win32con.HTCAPTION
        return super().winProc(hwnd, msg, wParam, lParam)

class DrawTextDialog(dialog.Dialog):
    def __init__(self, update, insert) -> None:
        super().__init__()
        self.css['bgColor'] = 0x404040
        self.css['paddings'] = (5, 5, 5, 5)
        self.updateLine = update
        self.insertLine = insert
        self.layout = base_win.GridLayout((25, 25, 25, '1fr', 25), (40, '1fr'), (5, 5))
        self.radoisUpd = base_win.CheckBox({'name': 'op', 'value': 'UPDATE', 'title':'修改'})
        self.radoisNew = base_win.CheckBox({'name': 'op', 'value': 'NEW', 'title':'新建'})
        self.dayPicker = base_win.DatePicker()
        self.priceEditor = base_win.Editor()
        self.mEditor = base_win.MutiEditor()
    
    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP, className = 'STATIC', title = '画线'):
        super().createWindow(parentWnd, rect, style, className, title)
        if self.updateLine:
            self.radoisUpd.createWindow(self.hwnd, (0, 0, 60, 25))
            self.radoisUpd.addNamedListener('Checked', self.onChecked)
        self.radoisNew.createWindow(self.hwnd, (0, 0, 60, 25))
        self.radoisNew.addNamedListener('Checked', self.onChecked)
        self.radoisUpd.css['bgColor'] = 0x404040
        self.radoisNew.css['bgColor'] = 0x404040
        self.dayPicker.css['bgColor'] = 0xf0f0f0
        self.dayPicker.css['textColor'] = 0x202020
        self.dayPicker.createWindow(self.hwnd, (0, 0, 1, 1))
        self.priceEditor.createWindow(self.hwnd, (0, 0, 1, 1))
        self.mEditor.createWindow(self.hwnd, (0, 0, 1, 1))

        rl = base_win.FlowLayout(30)
        rl.addContent(self.radoisNew)
        if self.radoisUpd.hwnd:
            rl.addContent(self.radoisUpd)
        self.layout.setContent(0, 1, rl)
        t = base_win.Label('日期')
        t.css['bgColor'] = 0x404040
        t.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(1, 0, t)
        self.layout.setContent(1, 1, self.dayPicker)
        t = base_win.Label('价格')
        t.css['bgColor'] = 0x404040
        t.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(2, 0, t)
        self.layout.setContent(2, 1, self.priceEditor)
        t = base_win.Label('备注')
        t.css['bgColor'] = 0x404040
        t.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(3, 0, t)
        self.layout.setContent(3, 1, self.mEditor)

        okBtn = base_win.Button({'title': 'OK', 'name': 'ok'})
        okBtn.createWindow(self.hwnd, (0, 0, 50, 25))
        self.layout.setContent(4, 0, okBtn)
        cancelBtn = base_win.Button({'title': 'Cancel', 'name': 'cancel'})
        cancelBtn.createWindow(self.hwnd, (0, 0, 50, 25))
        okBtn.addNamedListener('Click', self.onOkCancel)
        cancelBtn.addNamedListener('Click', self.onOkCancel)
        rl = base_win.FlowLayout(30)
        rl.addContent(okBtn)
        rl.addContent(cancelBtn)
        self.layout.setContent(4, 1, rl)
        pds = self.css['paddings']
        w, h = self.getClientSize()
        self.layout.resize(pds[0], pds[1], w - pds[0] - pds[2], h - pds[1] - pds[3])
        if self.updateLine:
            self.radoisUpd.setChecked(True)
        else:
            self.radoisNew.setChecked(True)

    def onOkCancel(self, evt, args):
        self.close()
        ok = evt.info['name'] == 'ok'
        if not ok:
            self.notifyListener(self.Event('InputEnd', self, ok = False, data = None))
            return
        data = self.updateLine if self.radoisUpd.isChecked() else self.insertLine
        try:
            data.day = self.dayPicker.getSelDayInt()
            data.info['startX'] = data.day
            price = self.priceEditor.getText()
            data.info['startY'] = float(price)
            data.info['text'] = self.mEditor.getText()
            self.notifyListener(self.Event('InputEnd', self, ok = ok, data = data))
        except Exception as e:
            pass

    def updateData(self, line):
        self.dayPicker.setSelDay(line.day)
        info = line.info
        if not info:
            return
        price = float(info['startY']) + 0.005
        self.priceEditor.setText(f'{price :.2f}')
        self.priceEditor.invalidWindow()
        self.mEditor.setText(info.get('text', ''))
        self.mEditor.invalidWindow()
    
    def onChecked(self, evt, args):
        if evt.info['value'] == 'NEW' and evt.info['checked']:
            self.updateData(self.insertLine)
        elif evt.info['value'] == 'UPDATE' and evt.info['checked']:
            self.updateData(self.updateLine)

class DrawLineManager:
    def __init__(self, klineWin) -> None:
        self.klineWin : KLineWindow = klineWin
        self.reset()

    def reset(self):
        self.code = None
        self.lines = []
        self.isDrawing = False
        self.curLine = None

    def load(self, code):
        self.reset()
        self.code = code
        q = tck_def_orm.TextLine.select().where(tck_def_orm.TextLine.code == code)
        for row in q:
            row.info = json.loads(row.info)
            self.lines.append(row)
    
    def reload(self):
        if self.code:
            self.load(self.code)

    def begin(self, dateType, kind):
        self.isDrawing = True
        self.curLine = tck_def_orm.TextLine(code = self.code, dateType = dateType, kind = kind)

    def isValidLine(self, line):
        return line.info and ('startX' in line.info) and ('endX' in line.info)
    
    def isValideText(self, line):
        return line.info and ('text' in line.info)

    def end(self):
        if not self.isDrawing:
            return
        self.isDrawing = False
        if self.curLine.kind == 'line' and self.isValidLine(self.curLine):
            ln = self.curLine.info
            self.curLine.info = json.dumps(ln)
            self.curLine.save()
            self.curLine.info = ln
            self.lines.append(self.curLine)
        elif self.curLine.kind == 'text' and self.isValideText(self.curLine):
            ln = self.curLine.info
            self.curLine.info = json.dumps(ln)
            self.curLine.save()
            self.curLine.info = ln
            for i, it in enumerate(self.lines):
                if it.id == self.curLine.id:
                    self.lines.pop(i)
                    break
            self.lines.append(self.curLine)
        self.curLine = None
    
    def cancel(self):
        self.isDrawing = False
        self.curLine = None

    def onDrawText(self, hdc, line):
        if not self.isValideText(line) or (not self.klineWin.klineIndicator.visibleRange):
            return
        sidx = self.klineWin.model.getItemIdx(int(line.info['startX']))
        vr = self.klineWin.klineIndicator.visibleRange
        if sidx < 0 or sidx < vr[0] or sidx >= vr[1]:
            return
        sx = self.klineWin.klineIndicator.getCenterX(sidx) + self.klineWin.klineIndicator.x
        sy = self.klineWin.klineIndicator.getYAtValue(line.info['startY']) + self.klineWin.klineIndicator.y
        text = line.info.get('text', '')
        rc = (sx, sy, sx + 200, sy + 100)
        drawer = self.klineWin.drawer
        drawer.drawText(hdc, text, rc, color = 0x404040, align = win32con.DT_LEFT)

    def onDrawLine(self, hdc, line : tck_def_orm.TextLine):
        W, H = self.klineWin.getClientSize()
        if not self.isValidLine(line) or (not self.klineWin.klineIndicator.visibleRange):
            return
        sidx = self.klineWin.model.getItemIdx(int(line.info['startX']))
        eidx = self.klineWin.model.getItemIdx(int(line.info['endX']))
        vr = self.klineWin.klineIndicator.visibleRange
        if sidx < 0 or eidx < 0 or sidx < vr[0] or sidx >= vr[1] or eidx < vr[0] or eidx >= vr[1]:
            return
        sx = self.klineWin.klineIndicator.getCenterX(sidx) + self.klineWin.klineIndicator.x
        ex = self.klineWin.klineIndicator.getCenterX(eidx) + self.klineWin.klineIndicator.x
        sy = self.klineWin.klineIndicator.getYAtValue(line.info['startY']) + self.klineWin.klineIndicator.y
        ey = self.klineWin.klineIndicator.getYAtValue(line.info['endY']) + self.klineWin.klineIndicator.y
        drawer = self.klineWin.drawer
        drawer.drawLine(hdc, sx, sy, ex, ey, 0x30f030, width = 1)

        if sx == ex and sy == ey:
            return
        if sx != ex:
            rc = (ex - 2, ey - 2, ex + 3, ey + 3)
            drawer.fillRect(hdc, rc, 0x30f030)
            return
        # draw vertical line arrow
        d = 1 if ey < sy else -1
        for n in range(4):
            for dx in range(-n, n + 1):
                x = sx + dx
                y = ey + n * d
                if x > 0 and y > 0 and x < W and y < H:
                    win32gui.SetPixel(hdc, x, y, 0x30f030)
    
    def onDraw(self, hdc):
        if not self.klineWin.model or not self.klineWin.model.data:
            return
        dateType = self.klineWin.dateType
        for line in self.lines:
            if line.kind == 'text':
                if line.dateType == dateType:
                    self.onDrawText(hdc, line)
            elif line.kind == 'line':
                if line.dateType == dateType:
                    self.onDrawLine(hdc, line)
        if self.isDrawing and self.isValidLine(self.curLine):
            self.onDrawLine(hdc, self.curLine)

    def onLButtonDown(self, x, y):
        if not self.curLine or not self.isDrawing:
            return
        #print('onLButtonDown ', self.isDrawing, self.curLine.__data__)
        it = self.klineWin.klineIndicator
        if self.curLine.kind == 'line':
            idx = it.getIdxAtX(x)
            if idx < 0:
                self.cancel()
                return
            data = self.klineWin.model.data[idx]
            self.curLine.day = str(data.day)
            price = it.getValueAtY(y)
            self.curLine.info = {'startX': data.day, 'startY': price['value']}
    
    def onInputEnd(self, evt, args):
        if evt.ok:
            self.curLine = evt.data
            self.end()
        else:
            self.cancel()

    def onLButtonUp(self, x, y):
        #print('onLButtonUp ', self.isDrawing, self.curLine.__data__)
        if (not self.curLine) or (not self.isDrawing):
            return
        it = self.klineWin.klineIndicator
        if self.curLine.kind == 'line':
            if not self.isStartDrawLine():
                self.cancel()
                return
            idx = it.getIdxAtX(x)
            if idx >= 0:
                data = self.klineWin.model.data[idx]
                price = it.getValueAtY(y)
                self.curLine.day = str(data.day)
                self.curLine.info.update({'endX': data.day, 'endY': price['value']})
            self.end()
            self.klineWin.invalidWindow()
        elif self.curLine.kind == 'text':
            idx = it.getIdxAtX(x)
            if idx < 0:
                self.cancel()
                return
            data = self.klineWin.model.data[idx]
            self.curLine.day = str(data.day)
            price = it.getValueAtY(y)
            self.curLine.info = {'startX': data.day, 'startY': price['value']}

            qr = tck_def_orm.TextLine.select().where(tck_def_orm.TextLine.code == self.curLine.code, tck_def_orm.TextLine.day == self.curLine.day, tck_def_orm.TextLine.kind == 'text')
            u = None
            for it in qr:
                u = it
                if u.info:
                    u.info = json.loads(u.info)
                break
            dlg = DrawTextDialog(u, self.curLine)
            #dlg = dialog.MultiInputDialog()
            dlg.createWindow(self.klineWin.hwnd, (0, 0, 250, 200), style = win32con.WS_POPUP)
            dlg.setModal(True)
            dlg.addNamedListener('InputEnd', self.onInputEnd)
            dlg.show(* win32gui.GetCursorPos())
            #print('lbtnUP:', self.curLine.info)

    def isStartDrawLine(self):
        if not self.isDrawing:
            return False
        if (not self.curLine) or (not isinstance(self.curLine.info, dict)):
            return False
        return 'startX' in self.curLine.info

    def onMouseMove(self, x, y):
        if not self.isStartDrawLine():
            return
        #print('onMouseMove ', self.isDrawing, self.curLine.__data__)
        it = self.klineWin.klineIndicator
        if self.curLine.kind == 'line':
            if not self.isStartDrawLine():
                return
            idx = it.getIdxAtX(x)
            if idx >= 0:
                data = self.klineWin.model.data[idx]
                self.curLine.day = str(data.day)
                price = it.getValueAtY(y)
                self.curLine.info.update({'endX': data.day, 'endY': price['value']})
            self.klineWin.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if not self.isDrawing:
            return False
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            x -= self.klineWin.klineIndicator.x
            y -= self.klineWin.klineIndicator.y
            self.onLButtonDown(x, y)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            x -= self.klineWin.klineIndicator.x
            y -= self.klineWin.klineIndicator.y
            self.onLButtonUp(x, y)
            return True
        if msg == win32con.WM_MOUSEMOVE:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            x -= self.klineWin.klineIndicator.x
            y -= self.klineWin.klineIndicator.y
            self.onMouseMove(x, y)
            return True
        if msg >= win32con.WM_MOUSEFIRST and msg <= win32con.WM_MOUSELAST:
            return True
        if msg >= win32con.WM_KEYFIRST and msg <= win32con.WM_IME_KEYLAST:
            return True
        return False

class KLineWindow(base_win.BaseWindow):
    LEFT_MARGIN, RIGHT_MARGIN = 0, 70

    def __init__(self):
        super().__init__()
        self.pens = {}
        self.hbrs = {}
        self.model = None
        self.dateType = 'day'
        self.models = {} # {'day': , 'week': xx, 'month': xx}
        self.showSelTip = True # 是否显示选中K线时的竖向提示框
        self.showCodeName = True # 显示代码，名称的提示
        self.klineWidth = 8 # K线宽度
        self.klineSpace = 2 # K线之间的间距离
        self.selIdx = -1
        self.mouseXY = None
        self.selIdxOnClick = False

        self.indicators = []
        idt = KLineIndicator({'height': -1, 'margins': (30, 20)})
        idt.init(self)
        self.indicators.append(idt)
        self.klineIndicator = idt
        self.lineMgr = DrawLineManager(self)
        from THS import tips_win
        self.hygnWin = tips_win.BkGnWindow()

    def addIndicator(self, indicator : Indicator):
        indicator.init(self)
        self.indicators.append(indicator)
        self.calcIndicatorsRect()

    # indicator = 'rate' | 'amount'
    def addDefaultIndicator(self, name):
        if 'rate' in name:
            idt = RateIndicator({'height': 60, 'margins': (15, 2)})
            self.indicators.append(idt)
            idt.init(self)
        if 'amount' in name:
            idt = AmountIndicator({'height': 60, 'margins': (15, 2)})
            self.indicators.append(idt)
            idt.init(self)
        self.calcIndicatorsRect()

    def setMarkDay(self, day, tip = None):
        self.klineIndicator.setMarkDay(day, tip)

    def removeMarkDay(self, day):
        self.klineIndicator.removeMarkDay(day)

    def clearMarkDay(self):
        self.klineIndicator.clearMarkDay()

    def calcIndicatorsRect(self):
        if not self.hwnd:
            return
        w, h = self.getClientSize()
        fixHeight = 0
        for i in range(0, len(self.indicators)):
            cf = self.indicators[i]
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

    def getRectByIndicator(self, indicatorOrIdx):
        if type(indicatorOrIdx) == int:
            idx = indicatorOrIdx
        elif isinstance(indicatorOrIdx, Indicator):
            for i in range(0, len(self.indicators)):
                if self.indicators[i] == indicatorOrIdx:
                    idx = i
                    break
        if idx < 0 or idx >= len(self.indicators):
            return None
        idt = self.indicators[idx]
        return [idt.x, idt.y, idt.width, idt.height]

    def setModel(self, model : KLineModel_DateType):
        self.selIdx = -1
        self.dateType = 'day'
        self.model = model
        self.hygn = None
        if not model:
            for idt in self.indicators:
                idt.setData(None)
            return
        self.model.calcAttrs()
        gntcObj = ths_orm.THS_GNTC.get_or_none(code = str(self.model.code))
        self.model.hy = []
        self.model.gn = []
        if gntcObj and gntcObj.hy:
            self.model.hy = gntcObj.hy.split('-')
            if len(self.model.hy) == 3:
                del self.model.hy[0]
        if gntcObj and gntcObj.hy:
            self.model.gn = gntcObj.gn.replace('【', '').replace('】', '').split(';')
        for idt in self.indicators:
            idt.setData(self.model.data)
        self.lineMgr.load(model.code)
        self.hygnWin.changeCode(self.model.code)

    # dateType = 'day' 'week'  'month'
    def changeDateType(self, dateType):
        if self.dateType == dateType:
            return
        self.dateType = dateType
        self.model.changeDateType(dateType)
        md = self.model
        for idt in self.indicators:
            idt.setData(md.data)
            idt.changeDateType(dateType)
        self.makeVisible(-1)
        self.selIdx = len(md.data) - 1
        x = self.klineIndicator.getCenterX(self.selIdx)
        if self.mouseXY:
            self.mouseXY = (x, self.mouseXY[1])
        self.invalidWindow()

    def onContextMenu(self, x, y):
        for it in self.indicators:
            isInRect = x >= it.x and y >= it.y and x < it.x + it.width and y < it.y + it.height
            if isInRect:
                if it.onContextMenu(x - it.x, y - it.y):
                    return
                break
        # default deal
        selDay = 0
        if self.selIdx >= 0:
            selDay = self.model.data[self.selIdx].day
            if isinstance(selDay, str):
                selDay = selDay.replace('-', '')
                selDay = int(selDay)
        ck = self.klineIndicator.visibleRefZS
        zx = [
            {'title': '默认', 'kind': 'def'},
            {'title': '涨停观察', 'kind': 'zt'},
        ]
        mm = [#{'title': '日线', 'name': 'day', 'enable': 'day' != self.dateType}, 
              #{'title': '周线', 'name': 'week', 'enable': 'week' != self.dateType}, 
              #{'title': '月线', 'name': 'month', 'enable': 'month' != self.dateType},
              #{'title': 'LINE'},
              {'title': '点击时选中K线', 'name': 'sel-idx-on-click', 'checked': self.selIdxOnClick},
              {'title': '显示叠加指数', 'name': 'show-ref-zs', 'checked': ck},
              {'title': '叠加指数 THS', 'name': 'add-ref-zs', 'sub-menu': self.getRefZsModel},
              {'title': '打开指数 THS', 'name': 'open-ref-zs', 'sub-menu': self.getRefZsModel},
              {'title': '叠加指数 CLS', 'name': 'add-ref-zs', 'sub-menu': self.getRefZsClsModel},
              {'title': 'LINE'},
              {'title': '标记日期', 'name': 'mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': '- 取消标记日期', 'name': 'cancel-mark-day', 'enable': selDay > 0, 'day': selDay},
              {'title': 'LINE'},
              {'title': '画线(直线)', 'name': 'draw-line'},
              {'title': '画线(文本)', 'name': 'draw-text'},
              {'title': '- 删除画线', 'name': 'del-draw-line'},
              {'title': 'LINE'},
              {'title': '涨停原因', 'name':'zt-reason', 'enable': selDay > 0},
              {'title': '涨速联动', 'name':'zs-liandong', 'enable': selDay > 0, 'day': selDay},
              {'title': '加自选', 'name':'JZX', 'sub-menu': zx},
              {'title': '- 删自选', 'name':'SZX', 'sub-menu': zx}
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
                tck_def_orm.TextLine.delete().where(tck_def_orm.TextLine.day == str(selDay)).execute()
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
        if self.showSelTip:
            self.createTipWindow(self.hwnd)
        self.hygnWin.DEF_COLOR = 0x22cc22

    def createTipWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_VISIBLE):
        selTipWin = KLineSelTipWindow(self)
        if rect == None:
            prc = win32gui.GetWindowRect(self.hwnd)
            rect = (prc[0] + 10, prc[1] + 80, 80, 140)
        selTipWin.createWindow(self.hwnd, rect, style) # win32con.WS_CAPTION |
    
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
            self.notifyListener(self.Event('MouseMove', self, x = lParam & 0xffff, y = (lParam >> 16) & 0xffff))
            return True
        if msg == win32con.WM_KEYDOWN:
            keyCode = lParam >> 16 & 0xff
            self.onKeyDown(keyCode)
            self.notifyListener(self.Event('KeyDown', self, keyCode = keyCode))
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
            si = self.selIdx
            if si >= 0:
                self.notifyListener(self.Event('DbClick', self, idx = si, data = self.model.data[si], code = self.model.code))
            return True
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onContextMenu(x, y)
            return True
        if msg == win32con.WM_MOUSELEAVE:
            self.mouseXY = None
            self.invalidWindow()
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
        if isinstance(it, KLineIndicator) or isinstance(it, RateIndicator) or isinstance(it, AmountIndicator):
            return True
        return False

    def onMouseMove(self, x, y):
        acc = False
        lmxy = self.mouseXY
        for it in self.indicators:
            acc = acc or self.acceptMouseMove(x, y, it)
        if not acc:
            self.mouseXY = None
            if lmxy != self.mouseXY:
                self.invalidWindow()
            return
        si = self.klineIndicator.getIdxAtX(x)
        if si < 0:
            self.mouseXY = None
            if lmxy != self.mouseXY:
                self.invalidWindow()
            return
        x = self.klineIndicator.getCenterX(si)
        if x < 0:
            self.mouseXY = None
            if lmxy != self.mouseXY:
                self.invalidWindow()
            return
        self.mouseXY = (x, y)
        if not self.selIdxOnClick:
            if self.selIdx == si and lmxy and y == lmxy[1]:
                return
            self.updateAttr('selIdx', si)
        if lmxy != self.mouseXY:
            self.invalidWindow()

    def onMouseClick(self, x, y):
        hygnRect = getattr(self.hygnWin, 'rect', None)
        if hygnRect and x >= hygnRect[0] and x < hygnRect[2] and y >= hygnRect[1] and y < hygnRect[3]:
            self.hygnWin.hwnd = self.hwnd
            self.hygnWin.onClick(x, y)
            return
        
        for it in self.indicators:
            isInRect = x >= it.x and y >= it.y and x < it.x + it.width and y < it.y + it.height
            if isInRect:
                it.onMouseClick(x - it.x, y - it.y)
                break

    def setSelIdx(self, idx):
        if not self.indicators:
            return
        idt = self.klineIndicator
        if not idt.visibleRange or idx < 0 or idx >= idt.visibleRange[1]:
            return
        data = self.model.data[idx]
        #x = idt.getCenterX(idx)
        #y = idt.getYAtValue(data.close) + idt.y
        #self.mouseXY = (x, y)
        self.updateAttr('selIdx', idx)

    def onKeyDown(self, keyCode):
        if keyCode == 73: # page up
            pass
        elif keyCode == 81: # page down
            pass
        elif keyCode == 75: # left arrow key
            if self.selIdx > 0:
                ni = self.selIdx - 1
                self.setSelIdx(ni)
        elif keyCode == 77: # right arrow key
            if self.klineIndicator.visibleRange and self.selIdx < self.klineIndicator.visibleRange[1] - 1:
                ni = self.selIdx + 1
                self.setSelIdx(ni)
        elif keyCode == 72: # up arrow key
            self.klineWidth += 2
            if self.klineWidth // 2 > self.klineSpace:
                self.klineSpace = min(self.klineSpace + 1, 2)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
                if self.mouseXY:
                    self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 80: # down arrow key
            self.klineWidth = max(self.klineWidth - 2, 1)
            if self.klineWidth // 2 < self.klineSpace:
                self.klineSpace = max(self.klineSpace - 1, 0)
            if self.selIdx >= 0:
                self.makeVisible(self.selIdx)
                x = self.klineIndicator.getCenterX(self.selIdx)
                self.mouseXY = (x, self.mouseXY[1])
            win32gui.InvalidateRect(self.hwnd, None, True)
        elif keyCode == 28:
            ks = ('day', 'week', 'month')
            idx = (ks.index(self.dateType) + 1) % len(ks)
            self.changeDateType(ks[idx])

    def makeVisible(self, idx):
        self.calcIndicatorsRect()
        idt : Indicator = None
        for idt in self.indicators:
            idt.calcVisibleRange(idx)
            vr = idt.visibleRange
            if vr:
                idt.calcValueRange(*vr)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def drawSelDayTip(self, hdc, pens, hbrs):
        if self.selIdx < 0 or (not self.model) or (not self.model.data) or self.selIdx >= len(self.model.data):
            return
        if not self.indicators:
            return
        it : Indicator = self.klineIndicator
        if not hasattr(it, 'y'):
            return
        cx = it.getCenterX(self.selIdx)
        SEL_DAY_WIDTH_HALF = 30
        sy = it.y + it.height + it.getMargins(1) + 1
        rc = (cx - SEL_DAY_WIDTH_HALF , sy, cx + SEL_DAY_WIDTH_HALF, sy + 14)
        d = self.model.data[self.selIdx]
        day = f'{d.day}'
        day = day[4 : 6] + '-' + day[6 : ] # day[0 : 4] + '-' + 
        win32gui.FillRect(hdc, rc, hbrs['light_dark'])
        win32gui.SetTextColor(hdc, 0xdddddd)
        win32gui.DrawText(hdc, day, len(day), rc, win32con.DT_CENTER)

    def drawCodeInfo(self, hdc, pens, hbrs):
        if not self.model:
            return
        code = self.model.code
        name = self.model.name
        #gnhy = '【' + ' - '.join(getattr(self.model, "hy", [])) + '】' + '│'.join(getattr(self.model, "gn", []))
        rc = (0, 0, int(self.getClientSize()[0] * 0.7), 70)
        self.hygnWin.rect = rc
        self.hygnWin.hwnd = self.hwnd
        self.hygnWin.onDrawRect(hdc, rc)
        #font = self.drawer.getFont('宋体', 12)
        #self.drawer.use(hdc, font)
        #self.drawer.drawText(hdc, gnhy, rc, 0x00cc00, win32con.DT_LEFT | win32con.DT_EDITCONTROL | win32con.DT_WORDBREAK)
        if self.showCodeName:
            sdc = win32gui.SaveDC(hdc)
            font = self.drawer.getFont('黑体', 16, 900)
            tip = f'{code}  {name}'
            w = self.getClientSize()[0]
            sx = int(w* 0.65)
            rc = (sx, 0, sx + 250, 30)
            self.drawer.use(hdc, font)
            self.drawer.drawText(hdc, tip, rc, 0x0000ff)
            win32gui.RestoreDC(hdc, sdc)

    def onDraw(self, hdc):
        pens = self.pens
        hbrs = self.hbrs
        if not pens:
            pens['white'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xffffff)
            pens['red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000ff)
            pens['green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ff00)
            pens['light_green'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xfcfc54)
            pens['blue'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff0000)
            pens['yellow'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            pens['yellow2'] = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x00ffff)
            pens['0xff00ff'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xff00ff)
            pens['dark_red'] = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x0000aa) # 暗红色
            pens['dark_red2'] = win32gui.CreatePen(win32con.PS_SOLID, 2, 0x0000aa) # 暗红色
            pens['bk_dot_red'] = win32gui.CreatePen(win32con.PS_DOT, 1, 0x000055) # 背景虚线
            pens['blue_dash_dot'] = win32gui.CreatePen(win32con.PS_DASHDOT, 1, 0xdd5555)
            pens['light_drak_dash_dot'] = win32gui.CreatePen(win32con.PS_DASHDOT, 1, 0x606060)
        if not hbrs:
            hbrs['white'] = win32gui.CreateSolidBrush(0xffffff)
            hbrs['drak'] = win32gui.CreateSolidBrush(0x202020)
            hbrs['red'] = win32gui.CreateSolidBrush(0x0000ff)
            hbrs['green'] = win32gui.CreateSolidBrush(0x00ff00)
            hbrs['light_green'] = win32gui.CreateSolidBrush(0xfcfc54)
            hbrs['blue'] = win32gui.CreateSolidBrush(0xff0000)
            hbrs['yellow'] = win32gui.CreateSolidBrush(0x00ffff)
            hbrs['black'] = win32gui.CreateSolidBrush(0x000000)
            hbrs['0xff00ff'] = win32gui.CreateSolidBrush(0xff00ff)
            hbrs['light_dark'] = win32gui.CreateSolidBrush(0x202020)
            hbrs['hilight'] = win32gui.CreateSolidBrush(0x202030)
            hbrs['mask'] = win32gui.CreateSolidBrush(0x101010)
        
        w, h = self.getClientSize()
        for i, idt in enumerate(self.indicators):
            sdc = win32gui.SaveDC(hdc)
            win32gui.SetViewportOrgEx(hdc, idt.x, idt.y)
            idt.draw(hdc, pens, hbrs)
            if i == 0:
                win32gui.SelectObject(hdc, pens['dark_red2'])
            else:
                win32gui.SelectObject(hdc, pens['dark_red'])
            y = idt.height + idt.getMargins(1)
            win32gui.MoveToEx(hdc, 0, y)
            win32gui.LineTo(hdc, w, y)
            win32gui.RestoreDC(hdc, sdc)
        
        win32gui.SelectObject(hdc, pens['dark_red'])
        win32gui.MoveToEx(hdc, w - self.RIGHT_MARGIN + 10, 0)
        win32gui.LineTo(hdc, w - self.RIGHT_MARGIN + 10, h)
        win32gui.SelectObject(hdc, pens['yellow'])
        win32gui.MoveToEx(hdc, 0, h - 2)
        win32gui.LineTo(hdc, w, h - 2)
        self.drawMouse(hdc, pens)
        #self.drawSelTip(hdc, pens, hbrs)
        self.drawCodeInfo(hdc, pens, hbrs)
        #self.drawSelDayTip(hdc, pens, hbrs)

        if self.mouseXY:
            self.drawTipPrice(hdc, self.mouseXY[1], pens, hbrs)
        
        # draw day | week | month
        cf = self.klineIndicator
        y = cf.getMargins(1) + cf.height
        title = {'day': '日线', 'week': '周线', 'month': '月线'}
        title = '【' + title[self.dateType] + '】'
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 18))
        rc = (5, y, 100, y + 30)
        self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_LEFT)

        if self.selIdx > 0 and self.model and self.selIdx < len(self.model.data):
            cur = self.model.data[self.selIdx]
            pre = self.model.data[self.selIdx - 1]
            lb = cur.amount / pre.amount # 量比
            rc = (0, 0, cf.width, 20)
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
            zf = cf.refZSDrawer.getZhangFu(cur.day)
            if zf is None:
                zf = '--'
            else:
                zf = f'{zf :+.02f}%'
            title = f'指数({zf}) 同比({lb :.1f})'
            self.drawer.drawText(hdc, title, rc, color = 0x00dddd, align = win32con.DT_RIGHT)

        self.lineMgr.onDraw(hdc)

    def onDestory(self):
        pens = self.pens
        hbrs = self.hbrs
        for k in pens:
            win32gui.DeleteObject(pens[k])
        for k in hbrs:
            win32gui.DeleteObject(hbrs[k])
        pens.clear()
        hbrs.clear()

    def drawMouse(self, hdc, pens):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        w, h = self.getClientSize()
        for it in self.indicators:
            if isinstance(it, CustomIndicator):
                h = it.y - 2
                break
        wp = win32gui.CreatePen(win32con.PS_DOT, 1, 0xffffff)
        win32gui.SelectObject(hdc, wp)
        win32gui.MoveToEx(hdc, self.LEFT_MARGIN, y)
        win32gui.LineTo(hdc, w, y)
        #win32gui.MoveToEx(hdc, x, self.klineIndicator.getMargins(1))
        #win32gui.LineTo(hdc, x, h)
        win32gui.DeleteObject(wp)

    def getValueAtY(self, y):
        for i in range(0, len(self.indicators)):
            rect = self.getRectByIndicator(i)
            if y >= rect[1] and y < rect[3] + rect[1]:
                return self.indicators[i].getValueAtY(y - rect[1])
        return None

    def drawTipPrice(self, hdc, y, pens, hbrs):
        val = self.getValueAtY(y)
        if not val:
            return
        win32gui.SetTextColor(hdc, 0x0000ff)
        w = self.getClientSize()[0]
        H = 16
        rc = (w - self.RIGHT_MARGIN + 10 + 1, y - H // 2, w, y + H // 2)
        hb = win32gui.CreateSolidBrush(0x800040)
        win32gui.FillRect(hdc, rc, hb)
        win32gui.DrawText(hdc, val['fmtVal'], len(val['fmtVal']), rc, win32con.DT_CENTER)
        win32gui.DeleteObject(hb)

class CodeWindow(ext_win.CellRenderWindow):
    def __init__(self, line : KLineWindow) -> None:
        super().__init__((70, '1fr'), 5)
        self.curCode = None
        self.data = None
        self.selData = None
        self.cacheData = {}
        self.klineWin : KLineWindow = line
        line.addNamedListener('selIdx.changed', self.onSelIdxChanged)
        self.V_CENTER = win32con.DT_SINGLELINE | win32con.DT_VCENTER
        self.init()
    
    def getBasicCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0xcccccc, 'textAlign': self.V_CENTER, 'fontSize': 15}
        if not self.data:
            return cell
        name = rowInfo['name']
        val = self.data.get(name, None)
        if val == None:
            #cell['text'] = '--'
            return cell
        if name == '委比': cell['text'] = f'{int(val)} %'
        elif '市值' in name: cell['text'] = f'{val // 100000000}' + ' 亿'
        elif '市盈率' in name:
            if val < 0: cell['text'] = '亏损'
            else: cell['text'] = f'{int(val)}'
        elif '涨幅' == name: cell['text'] = f'{val :.2f} %'
        else: 
            cell['text'] = str(val)
        if name == '涨幅' or name == '委比':
            cell['color'] = 0x0000ff if int(val) >= 0 else 0x00ff00
        if '市盈率' in name and val < 0:
            cell['color'] =  0x00ff00
        return cell

    def getBkCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0x808080, 'textAlign': self.V_CENTER, 'fontSize': 15}
        if not self.klineWin or not self.klineWin.klineIndicator.refZSDrawer.model:
            return cell
        refModel = self.klineWin.klineIndicator.refZSDrawer.model
        val = ''
        name = rowInfo['name']
        if name == 'refZSName':
           val = refModel.name
        elif name == 'refZSCode':
            val = refModel.code
        cell['text'] = val
        if name == 'refZSName':
            cell['span'] = 2
            cell['textAlign'] |= win32con.DT_CENTER
        return cell

    def getCodeCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0x5050ff, 'textAlign': win32con.DT_CENTER | self.V_CENTER, 'fontSize': 15, 'fontWeight': 1000, 'span': 2}
        if not self.data:
            return cell
        if rowInfo['name'] == 'code':
            code = self.data.get('code', None)
            cell['text'] = code
        elif rowInfo['name'] == 'name':
            name = self.data.get('name', None)
            cell['text'] = name
        return cell

    def init(self):
        RH = 25
        self.addRow({'height': 25, 'margin': 0, 'name': 'code'}, self.getCodeCell)
        self.addRow({'height': 25, 'margin': 0, 'name': 'name'}, self.getCodeCell)
        KEYS = ('Line', '流通市值', '总市值', 'Line', '市盈率_静', '市盈率_TTM', 'Line') # '涨幅', '委比', 
        for k in KEYS:
            if k == 'Line':
                self.addRow({'height': 1, 'margin': 0, 'name': 'split-line'}, {'color': 0xa0a0a0, 'bgColor': 0x606060, 'span': 2})
            else:
                self.addRow({'height': RH, 'margin': 0, 'name': k}, {'text': k, 'color': 0xcccccc, 'textAlign': self.V_CENTER}, self.getBasicCell)
        self.addRow({'height': RH, 'margin': 0, 'name': 'refZSName'}, self.getBkCell)
        self.addRow({'height': RH, 'margin': 0, 'name': 'refZSCode'}, {'text': '板块指数', 'color': 0x808080, 'textAlign': self.V_CENTER}, self.getBkCell)
        self.addRow({'height': RH, 'margin': 0, 'name': 'refZSZhangFu'}, {'text': '指数涨幅', 'color': 0x808080, 'textAlign': self.V_CENTER}, self.getCell)
        self.addRow({'height': 1, 'margin': 0, 'name': 'split-line'}, {'color': 0xa0a0a0, 'bgColor': 0x606060, 'span': 2})
        self.addRow({'height': RH, 'margin': 0, 'name': 'zhangFu'}, {'text': '涨幅', 'color': 0xcccccc, 'textAlign': self.V_CENTER}, self.getCell)
        self.addRow({'height': RH, 'margin': 0, 'name': 'vol'},{'text': '成交额', 'color': 0xcccccc, 'textAlign': self.V_CENTER},  self.getCell)
        self.addRow({'height': RH, 'margin': 0, 'name': 'rate'}, {'text': '换手率', 'color': 0xcccccc, 'textAlign': self.V_CENTER}, self.getCell)

    def loadZS(self, code):
        name = ths_orm.THS_ZS.select(ths_orm.THS_ZS.name).where(ths_orm.THS_ZS.code == code).scalar()
        self.data = {'code': self.curCode, 'name': name}
        self.invalidWindow()

    def loadCodeBasic(self, code):
        if code[0] == '8':
            self.loadZS(code)
            return
        url = cls.ClsUrl()
        data = url.loadBasic(code)
        data['code'] = code
        self.cacheData[code] = data
        if code[0] in ('0', '3', '6'):
            bk = ths_orm.THS_GNTC.get_or_none(code = code)
            if bk:
                data['refZSName'] = bk.hy_2_name
                data['refZSCode'] = bk.hy_2_code
        self._useCacheData(code)

    def _useCacheData(self, code):
        if code != self.curCode or code not in self.cacheData:
            return
        self.data = self.cacheData[code]
        self.invalidWindow()
        
    def changeCode(self, code):
        scode = f'{code :06d}' if type(code) == int else code
        if (self.curCode == scode) or (not scode):
            return
        self.curCode = scode
        self.data = None
        #if len(scode) != 6 or (scode[0] not in ('0', '3', '6')):
        #    self.invalidWindow()
        #    return
        if scode in self.cacheData:
            self._useCacheData(scode)
        else:
            base_win.ThreadPool.instance().addTask(scode, self.loadCodeBasic, scode)

    def onSelIdxChanged(self, evt, args):
        self.selData = evt.data
        self.klineWin = evt.src
        self.invalidWindow()

    def getCell(self, rowInfo, idx):
        cell = {'text': '', 'color': 0xcccccc, 'textAlign': self.V_CENTER, 'fontSize': 15}
        if self.selData is None:
            return
        if rowInfo['name'] == 'zhangFu':
            zf = getattr(self.selData, 'zhangFu', None)
            if zf is not None:
                cell['text'] = f'{zf :.02f}%'
                cell['color'] = 0x0000ff if zf >= 0 else 0x00ff00
        elif rowInfo['name'] == 'vol':
            money = getattr(self.selData, 'amount', None)
            if money:
                cell['text'] = f'{money / 100000000 :.01f} 亿'
        elif rowInfo['name'] == 'rate':
            rate = getattr(self.selData, 'rate', None)
            if rate:
                cell['text'] = f'{int(rate)} %'
        elif rowInfo['name'] == 'refZSZhangFu' and self.klineWin:
            day = self.selData.day
            zf = self.klineWin.klineIndicator.refZSDrawer.getZhangFu(day)
            if zf is not None:
                cell['text'] = f'{zf :.02f}%'
                cell['color'] = 0x808080
        elif rowInfo['name'] == 'refZSCode' and self.klineWin:
            code = self.klineWin.klineIndicator.refZSDrawer.zsCode
            cell['text'] = f'{code}'
            cell['color'] = 0x808080
        elif rowInfo['name'] == 'refZSName' and self.klineWin:
            cell['span'] = 2
            cell['textAlign'] = win32con.DT_CENTER
            refzs = self.klineWin.klineIndicator.refZSDrawer
            if refzs and refzs.model and refzs.model.name:
                cell['text'] = refzs.model.name
                cell['color'] = 0x808080
        return cell

class KLineCodeWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x101010
        self.layout = None
        self.klineWin = KLineWindow()
        self.klineWin.showSelTip = True
        self.klineWin.showCodeName = False
        self.codeWin = CodeWindow(self.klineWin)
        self.codeList = None
        self.code = None
        self.idxCodeList = -1
        self.idxCodeWin = None
        self.refZtReasonDetailWin = None
        self.refZtReasonWin = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, className, title)
        DETAIL_WIDTH = 150
        REF_GN_WIDTH = 120
        self.layout = base_win.GridLayout(('100%', ), ('1fr', DETAIL_WIDTH, REF_GN_WIDTH), (5, 5))
        self.klineWin.showSelTip = False
        self.klineWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.klineWin.addNamedListener('zt-reason', self.onZtReason)
        self.layout.setContent(0, 0, self.klineWin)

        rightLayout = base_win.FlowLayout()
        self.codeWin.createWindow(self.hwnd, (0, 0, DETAIL_WIDTH, self.codeWin.getContentHeight()))
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

        self.refZtReasonWin = base_win.TableWindow()
        self.refZtReasonWin.css['bgColor'] = 0x000000
        self.refZtReasonWin.css['textColor'] = 0xc0c0c0
        self.refZtReasonWin.css['selBgColor'] = 0x303030
        self.refZtReasonWin.css['cellBorder'] = 0x101010
        #self.refZtReasonWin.css['headerBgColor'] = 0x303030
        #self.refZtReasonWin.css['headerBorderColor'] = None
        #self.refZtReasonWin.css['cellBorder'] = 0x101010  # A
        #self.refZtReasonWin.css['selBgColor'] = 0xA0A0A0  # A
        self.refZtReasonWin.createWindow(self.hwnd, (0, 0, DETAIL_WIDTH, 300))
        self.refZtReasonWin.headers = [
            {'name': 'gn', 'title': '涨停原因', 'width': 0, 'stretch': 1, 'paddings': (15, 0, 0, 0)}
        ]
        rightLayout.addContent(self.refZtReasonWin, {'margins': (0, 15, 0, 0)})
        self.refZtReasonWin.addListener(self.onSelectZtResason)
        self.layout.setContent(0, 1, rightLayout)

        self.refZtReasonDetailWin = base_win.TableWindow()
        self.refZtReasonDetailWin.css['bgColor'] = 0x000000
        self.refZtReasonDetailWin.css['textColor'] = 0xc0c0c0
        self.refZtReasonDetailWin.css['selBgColor'] = 0x303030
        self.refZtReasonDetailWin.css['cellBorder'] = 0x101010
        #self.refZtReasonDetailWin.css['cellBorder'] = 0x101010  # A
        #self.refZtReasonDetailWin.css['selBgColor'] = 0xA0A0A0  # A
        def renderReasonDetail(win, hdc, row, col, colName, value, rowData, rect):
            if self.code == rowData['code']:
                color = 0x00dd00
            else:
                color = win.css['textColor']
            self.drawer.drawText(hdc, value, rect, color = color, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        
        def hotFormater(colName, val, rowData):
            if not val:
                return ''
            return str(val)

        self.refZtReasonDetailWin.headers = [
            {'name': '#idx',  'width': 20, 'textAlign': win32con.DT_VCENTER | win32con.DT_SINGLELINE},
            {'name': 'name', 'title': '关联股票', 'width': 0, 'stretch': 1, 'render': renderReasonDetail, 'textAlign': win32con.DT_VCENTER | win32con.DT_SINGLELINE},
            {'name': 'hotZH', 'title': 'Hot', 'width': 25, 'formater': hotFormater, 'textAlign': win32con.DT_VCENTER | win32con.DT_SINGLELINE}
        ]
        self.refZtReasonDetailWin.addListener(self.onSelectZtResasonDetail)
        self.refZtReasonDetailWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 2, self.refZtReasonDetailWin)
        self.layout.resize(0, 0, *self.getClientSize())

    def onSelectZtResason(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        rowData = evt.data
        if rowData['is_bk']:
            info = self.findInBk(rowData)
        else:
            info = self.findInZtReason(rowData)
        day = int(rowData['day'].replace('-', ''))
        hots = hot_utils.DynamicHotZH.instance().getHotsZH(day)
        for d in info:
            cc = int(d['code'])
            if cc in hots:
                d['hotZH'] = hots[cc]['zhHotOrder']
        info.sort(key = lambda k : k.get('hotZH', 1000), reverse = False)
        self.refZtReasonDetailWin.setData(info)
        self.refZtReasonDetailWin.invalidWindow()

    def onSelectZtResasonDetail(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        rowData = evt.data
        self.changeCode(rowData['code'])
    
    def findInBk(self, rowData):
        bkCodes = []
        key = rowData['name']
        day = rowData['day']
        q = ths_orm.THS_GNTC.select().where(ths_orm.THS_GNTC.hy_2_name == key)
        KV = ('0', '3', '6')
        for it in q:
            if it.code[0] not in KV:
                continue
            bkCodes.append(it.code)
        i = 0
        rs = []
        while i < len(bkCodes):
            ei = min(i + 50, len(bkCodes))
            bc = bkCodes[i : ei]
            i = ei
            q = tck_orm.THS_ZT.select(tck_orm.THS_ZT.code, tck_orm.THS_ZT.name).distinct().where(tck_orm.THS_ZT.day == day, tck_orm.THS_ZT.code.in_(bc)).dicts()
            for it in q:
                rs.append({'code': it['code'], 'name': it['name'],  'day': day})
        #arr.sort(key = lambda it: it['num'], reverse = True)
        return rs

    def findInZtReason(self, rowData):
        day = rowData['day']
        key = rowData['name']
        q1 = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day == day, tck_orm.THS_ZT.ztReason.contains(key))
        q2 = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day == day, tck_orm.CLS_ZT.ztReason.contains(key))
        rs = {}
        for q in (q1, q2):
            for it in q:
                if not it.ztReason:
                    continue
                rzs = it.ztReason.split('+')
                if key not in rzs:
                    continue
                if it.code not in rs:
                    rs[it.code] = {'code': it.code, 'name': it.name, 'day': day}
        arr = [rs[k] for k in rs]
        #arr.sort(key = lambda it: it['num'], reverse = True)
        return arr

    def _getCode(self, d):
        if type(d) == dict:
            return d.get('code', None) or d.get('secu_code', None)
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
        self.refZtReasonWin.setData(None)
        self.refZtReasonDetailWin.setData(None)
        self.refZtReasonWin.invalidWindow()
        self.refZtReasonDetailWin.invalidWindow()

    # nameOrObj : str = 'rate amount'
    # nameOrObj : Indicator
    def addIndicator(self, nameOrObj):
        if isinstance(nameOrObj, str):
            self.klineWin.addDefaultIndicator(nameOrObj)
        if isinstance(nameOrObj, Indicator):
            self.klineWin.addIndicator(nameOrObj)

    def changeCode(self, code):
        base_win.ThreadPool.instance().addTask(f'K-{code}', self.changeCode_R, code)

    def changeCode_R(self, code):
        try:
            self.code = code
            self.codeWin.changeCode(code)
            model = KLineModel_DateType(code)
            model.loadDataFile()
            self.klineWin.setModel(model)
            self.klineWin.makeVisible(-1)
            self.klineWin.invalidWindow()
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

    def onZtReason(self, evt, args):
        hd = self.refZtReasonWin.headers[0]
        fmt = f'{evt.day // 100 % 100 :02d}-{evt.day % 100 :02d}'
        hd['title'] = '涨停原因 ' + fmt
        self.updateGnTable(evt.code, evt.day)
        self.klineWin.setMarkDay(evt.day, 'ZT')

    def updateGnTable(self, code, day):
        rs = []
        gns = []
        if type(day) == int:
            day = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        if len(day) == 8:
            day = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
        gntc = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        ds = self.klineWin.model.data
        if gntc and gntc.hy:
            hys = gntc.hy.split('-')
            rs.append({'gn': '【' + hys[1] + '】', 'is_bk': True, 'day': day, 'name': hys[1], 'fromDay': day})
        ths = tck_orm.THS_ZT.get_or_none(tck_orm.THS_ZT.code == code, tck_orm.THS_ZT.day == day)
        if ths and ths.ztReason:
            its = ths.ztReason.split('+')
            for it in its: 
                it = it.strip()
                gns.append(it)
                rs.append({'gn': it, 'is_bk': False, 'day': day, 'type': 'ths', 'name': it, 'fromDay': day})
        cls = tck_orm.CLS_ZT.get_or_none(tck_orm.CLS_ZT.code == code, tck_orm.CLS_ZT.day == day)
        if cls and cls.ztReason:
            its = cls.ztReason.split('+')
            for it in its: 
                it = it.strip()
                if it not in gns:
                    rs.append({'gn': it, 'is_bk': False, 'day': day, 'type': 'cls', 'name': it, 'fromDay': day})
        self.refZtReasonWin.setData(rs)
        self.refZtReasonWin.invalidWindow()

if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    sm = base_win.ThsShareMemory.instance()
    sm.open()
    import kline_utils
    win = kline_utils.openInCurWindow_Code(None, {'code': '600476'})
    win32gui.PumpMessages()