import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, json
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import henxin
from Common import base_win
from Download.datafile import DataFile

#base_win.ThreadPool.ins.start()

class CacheManager(base_win.Listener):
    def __init__(self) -> None:
        self.cache = {} # {code : data, ...}
        self.localCache = {} # {code-day: data, ...)
        self.wins = []

    def _needUpdate(self, data):
        now = datetime.datetime.now()
        cc : datetime.datetime = data['_load_time']
        delta : datetime.timedelta = now - cc
        if delta.seconds >= 15:
            return True
        ts = cc.hour * 100 + cc.minute
        cs = now.hour * 100 + now.minute
        if ts < 930 and cs >= 930:
            return True
        return False
    
    def _needUpdateLocal(self, data, day):
        if not data or data['day'] != day:
            return True
        now = datetime.datetime.now()
        cc : datetime.datetime = data['_load_time']
        delta : datetime.timedelta = now - cc
        if delta.seconds >= 60 * 60:
            return True
        return False

    def getData(self, code, win):
        if type(code) == int:
            code = f'{code :06d}'
        if code not in self.cache:
            self.download(code, win)
            return None
        data = self.cache[code]
        if self._needUpdate(data):
            self.cache.pop(code)
            self.download(code, win)
            return None
        return data
    
    def getLocalData(self, code, day, win):
        if type(code) == int:
            code = f'{code :06d}'
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        data = self.localCache.get(code, None)
        if self._needUpdateLocal(data, day):
            if data:
                self.localCache.pop(code)
            self.downloadLocal(code, day, win)
            return None
        return data
    
    def _getCode(self, data):
        if not data:
            return None
        if 'code' in data:
            c = data['code']
        elif 'secu_code' in data:
            c = data['secu_code']
        if isinstance(c, int):
            c = f'{c :06d}'
        return c
    
    def onVisibleRangeChanged(self, evt, args):
        win = evt.src
        vr = win.getVisibleRange()
        ds = win.getData()
        if not vr or not ds:
            return
        curDatas = ds[vr[0] : vr[1]]
        #codes = [self._getCode(d) for d in curDatas]
        base_win.ThreadPool.instance().clearTasks()

    def adjustDownloadList(self, win : base_win.TableWindow):
        wid = id(win)
        if wid not in self.wins:
            self.wins.append(wid)
            win.addNamedListener('VisibleRangeChanged', self.onVisibleRangeChanged)

    def download(self, code, win):
        base_win.ThreadPool.instance().addTask(code, self._download, code, win)

    def downloadLocal(self, code, day, win):
        base_win.ThreadPool.instance().addTask(code, self._downloadLocal, code, day, win)

    def _calcZF(self, data):
        if (not data.get('pre', 0)) or (not data.get('line', None)) :
            return None
        pre = data['pre']
        last = data['line'][-1]
        price = last.price
        if not price:
            return
        return (price - pre) / pre

    def _download(self, code, win):
        hx = henxin.HexinUrl()
        ds = hx.loadUrlData( hx.getFenShiUrl(code) )
        if not ds:
            return
        ds['code'] = code
        zf = self._calcZF(ds)
        render = TimelineRender()
        render.setData(ds)
        rs = {'_load_time': datetime.datetime.now(), 'render': render, 'zf': zf}
        self.cache[code] = rs
        if win:
            win.invalidWindow()

    def _downloadLocal(self, code, day, win):
        if type(day) == str:
            day = int(day.replace('-', ''))
        ds = {'code': code, 'day': day, 'pre': 0, 'line': []}
        render = TimelineRender()
        rs = {'_load_time': datetime.datetime.now(), 'render': render, 'zf': 0, 'day': day}
        self.localCache[code] = rs
        df = DataFile(code, DataFile.DT_MINLINE)
        #df.loadData(DataFile.FLAG_ALL)
        df.loadDataByDay(day)
        idx = df.getItemIdx(day)
        if idx < 0:
            return
        if idx == 0:
            ds['pre'] = df.data[idx].price
        else:
            ds['pre'] = df.data[idx -1].price
        while idx < len(df.data):
            if df.data[idx].day != day:
                break
            ds['line'].append(df.data[idx])
            idx += 1
        rs['zf'] = self._calcZF(ds)
        render.setData(ds)
        if win:
            win.invalidWindow()

_cache = CacheManager()

class TimelineRender:
    def __init__(self) -> None:
        self.data = None
        self.paddings = (0, 5, 35, 5)
        self.priceRange = None
        self.maxPrice = None
        self.minPrice = None
        self.speeds = None

    def calcPriceRange(self):
        minVal = 100000
        maxVal = -10000
        for d in self.data['line']:
            minVal = min(d.price, minVal)
            maxVal = max(d.price, maxVal)
        self.maxPrice = maxVal
        self.minPrice = minVal
        minVal = min(self.data['pre'], minVal)
        maxVal = max(self.data['pre'], maxVal)
        self.priceRange = (minVal, maxVal)

    def setData(self, data):
        self.priceRange = None
        self.data = data
        if not data:
            return
        self.calcPriceRange()
        self.speeds = self.calcMinutesSpeed(data.get('line', None))

    def _calcMaxPrice(self, datas, fromIdx, endIdx):
        maxIdx = -1
        maxPrice = 0
        day = datas[fromIdx].day
        for i in range(fromIdx, endIdx):
            m = datas[i]
            if m.day != day:
                break
            if m.price > maxPrice:
                maxPrice = m.price
                maxIdx = i
        return maxIdx, maxPrice
    
    def calcMinutesSpeed(self, datas):
        if not datas:
            return
        ONE_DAY_LINES = 241
        SPEED_PEROID = 10 # 时速周期 5 / 10 / 15
        MIN_ZHANG_SU = 5 # 最小涨速
        speedResults = []
        fromIdx = 0
        endMaxIdx = min(fromIdx + ONE_DAY_LINES, len(datas))
        for i in range(fromIdx, endMaxIdx):
            m = datas[i]
            maxIdx, maxPrice = self._calcMaxPrice(datas, i, min(endMaxIdx, i + SPEED_PEROID))
            if maxIdx < 0:
                continue
            me = datas[maxIdx]
            pre = datas[i].price
            zf = (maxPrice - pre) / pre * 100
            if zf < MIN_ZHANG_SU:
                continue
            if speedResults:
                last = speedResults[-1]
                if last['day'] == m.day and i >= last['fromIdx'] and i <= last['endIdx']:
                    if last['zf'] <= zf:
                        speedResults.pop(-1) # remove last, replace it
                    else:
                        continue # skip
            curJg = {'day': m.day, 'fromMinute': m.time, 'endMinute': me.time, 'minuts': maxIdx - i + 1,
                     'fromIdx' : i, 'endIdx': maxIdx, 'zf': zf}
            speedResults.append(curJg)
        return speedResults
    
    def getYAtPrice(self, price, height):
        ph = self.priceRange[1] - self.priceRange[0]
        if ph == 0:
            return 0
        height -= self.paddings[1] + self.paddings[3]
        y = (self.priceRange[1] - price) / ph * height + self.paddings[1]
        return int(y)
    
    def getLineColor(self):
        if self.isZTPrice(self.maxPrice):
            return self.getPriceColor(self.maxPrice)
        if self.isDTPrice(self.minPrice):
            return self.getPriceColor(self.minPrice)
        if 'line' in self.data:
            last = self.data['line'][-1]
            color = self.getPriceColor(last.price)
            return color
        return 0x000000
    
    def isZTPrice(self, price):
        # check is zt
        code = self.data['code']
        zf = 0.1
        if code[0] == '3' or code[0 : 3] == '688':
            zf = 0.20
        pre = self.data['pre']
        ztPrice = int(int(pre * 100 + 0.5) * (1 + zf) + 0.5)
        if int(price * 100 + 0.5) >= ztPrice:
            return True
        return False
    
    def isDTPrice(self, price):
        code = self.data['code']
        zf = 0.1
        if code[0] == '3' or code[0 : 3] == '688':
            zf = 0.20
        pre = self.data['pre']
        dtPrice = int(int(pre * 100 + 0.5) * (1 - zf) + 0.5)
        if int(price * 100 + 0.5) <= dtPrice:
            return True
        return False

    def getPriceColor(self, price):
        color = 0x0
        GREEN = 0xA3C252
        RED = 0x2204de

        # check is zt
        code = self.data['code']
        zf = 0.1
        if code[0] == '3' or code[0 : 3] == '688':
            zf = 0.20
        pre = self.data['pre']
        ztPrice = int(int(pre * 100 + 0.5) * (1 + zf) + 0.5)
        if int(price * 100 + 0.5) >= ztPrice:
            return 0xdd0000
        dtPrice = int(int(pre * 100 + 0.5) * (1 - zf) + 0.5)
        if int(price * 100 + 0.5) <= dtPrice:
            return 0x009999
        if price > self.data['pre']:
            color = RED
        elif price < self.data['pre']:
            color = GREEN
        return color

    def onDrawSpeed(self, hdc, drawer : base_win.Drawer, rect):
        if not self.speeds:
            return
        cwidth = rect[2] - rect[0] - self.paddings[0] - self.paddings[2]
        dx = cwidth / 241
        PADDINGS = 5
        for sp in self.speeds:
            sx = int(sp['fromIdx'] * dx + self.paddings[0]) + rect[0]
            ex = int(sp['endIdx'] * dx + self.paddings[0]) + 1 + rect[0]
            drawer.fillRect(hdc, (sx, rect[1] + PADDINGS, ex, rect[3] - PADDINGS), 0xB0B0B0)

    def onDraw(self, hdc, drawer : base_win.Drawer, rect):
        if not self.priceRange or self.priceRange[1] - self.priceRange[0] <= 0:
            return
        cwidth = rect[2] - rect[0] - self.paddings[0] - self.paddings[2]
        height = rect[3] - rect[1]
        da = self.data['line']
        if not da:
            return
        self.onDrawSpeed(hdc, drawer, rect)
        dx = cwidth / 241
        drawer.use(hdc, drawer.getPen(self.getLineColor()))
        for i, d in enumerate(da):
            x = int(i * dx + self.paddings[0])
            y = self.getYAtPrice(d.price, height)
            if i == 0:
                win32gui.MoveToEx(hdc, x + rect[0], y + rect[1])
            else:
                win32gui.LineTo(hdc, x + rect[0], y + rect[1])
        # draw zero line
        GREEY = 0x909090
        drawer.use(hdc, drawer.getPen(GREEY, win32con.PS_DOT))
        py = self.getYAtPrice(self.data['pre'], height)
        win32gui.MoveToEx(hdc, rect[0] + self.paddings[0], py + rect[1])
        win32gui.LineTo(hdc, rect[2] - self.paddings[2], py + rect[1])
        # draw max price
        mzf = (self.maxPrice - self.data['pre']) / self.data['pre'] * 100
        szf = (self.minPrice - self.data['pre']) / self.data['pre'] * 100
        ZFW = 50
        rc = [rect[2] - ZFW, rect[1], rect[2], rect[1] + 20]
        drawer.use(hdc, drawer.getFont(fontSize = 10))
        drawer.drawText(hdc, f'{mzf :.2f}%', rc, self.getPriceColor(self.maxPrice), win32con.DT_RIGHT | win32con.DT_TOP)
        rc = [rect[2] - ZFW, rect[3] - 12, rect[2], rect[3]]
        drawer.drawText(hdc, f'{szf :.2f}%', rc, self.getPriceColor(self.minPrice), win32con.DT_RIGHT | win32con.DT_BOTTOM)
        # zf
        zf = (da[-1].price - self.data['pre']) / self.data['pre'] * 100
        rc = [rect[2] - ZFW, rect[1] + (rect[3] - rect[1]) // 2 - 5 , rect[2], rect[3]]
        drawer.drawText(hdc, f'{zf :.2f}%', rc, 0xFF3399, win32con.DT_RIGHT | win32con.DT_TOP)

# 分时图
def renderTimeline(win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
    global _cache
    if 'secu_code' in rowData:
        code = rowData['secu_code'][2 : ]
    elif 'code' in rowData:
        code = rowData['code']
    else:
        return
    _cache.adjustDownloadList(win)
    hd = win.headers[col]
    day = hd.get('LOCAL-FS-DAY', None)
    if callable(day):
        argCount = day.__code__.co_argcount
        if argCount == 0:
            day = day()
        elif argCount == 1:
            day = day(rowData)
    if day:
        if type(day) == str:
            day = int(day.replace('-', ''))
        data = _cache.getLocalData(code, day, win)
    else:
        data = _cache.getData(code, win)
    if not data:
        return
    rowData['calc-zf'] = data['zf']
    data['render'].onDraw(hdc, win.drawer, rect)

def sorterTimeline(colName, val, rowData, allDatas, asc):
    if 'calc-zf' in rowData:
        return rowData['calc-zf']
    if 'zf' in rowData:
        return rowData['zf']
    return rowData.get('change', 0)

# 涨幅
def renderZFColor(win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
    GREEN = 0xA3C252
    RED = 0x2204de
    global _cache
    if value == None:
        return
    if 'secu_code' in rowData:
        code = rowData['secu_code'][2 : ]
    elif 'code' in rowData:
        code = rowData['code']
    else:
        return
    data = _cache.getData(code, win)
    if data and 'zf' in data:
        value = data['zf']
    color = 0x00
    if value > 0: color = RED
    elif value < 0: color = GREEN
    value *= 100
    win.drawer.drawText(hdc, f'{value :.2f} %', rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)    

# 涨幅
def renderZF(win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
    global _cache
    if value == None:
        return
    if 'secu_code' in rowData:
        code = rowData['secu_code'][2 : ]
    elif 'code' in rowData:
        code = rowData['code']
    else:
        return
    data = _cache.getData(code, win)
    if data and 'zf' in data:
        value = data['zf']
    color = 0x00
    value *= 100
    win.drawer.drawText(hdc, f'{value :.2f} %', rect, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)     