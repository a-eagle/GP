import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image  # pip install pillow

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, tdx_orm, lhb_orm, tck_orm
from common import base_win
from THS import hot_utils

class HotWindow(base_win.BaseWindow):
    #  HOT(热度)  LHB(龙虎榜) LS_INFO(两市信息) DDLR（大单流入） ZT_FUPAN(涨停复盘)
    DATA_TYPE = ('LHB', 'LS_INFO', 'DDLR')

    def __init__(self):
        super().__init__()
        self.css['fontSize'] = 12
        self.rect = None  # 窗口大小 (x, y, w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.hotData = None # 热点数据
        self.lhbData = None # 龙虎榜数据
        self.ddlrData = None # 大单流入数据
        self.lsInfoData = None # 两市信息
        self.ztFuPanData = None # 涨停复盘
        self.dataType = HotWindow.DATA_TYPE[0]
        self.selectDay = '' # YYYY-MM-DD
        self.tradeDays = None

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        rr = win32gui.GetClientRect(parentWnd)
        print('THS top window: ', rr)
        HEIGHT = 265 #285
        x = 0
        y = rr[3] - rr[1] - HEIGHT + 20
        #w = rr[2] - rr[0]
        w = win32api.GetSystemMetrics(0) # desktop width
        self.rect = (x, y, w, HEIGHT)
        style = (win32con.WS_VISIBLE | win32con.WS_POPUP)
        super().createWindow(parentWnd, self.rect, style, title='HOT-Window')
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        self.changeMode()

    def onDraw(self, hdc):
        if self.maxMode:
            self.drawDataType(hdc)
        else:
            self.drawMinMode(hdc)

    def drawDataType(self, hdc):
        ITEM_WIDTH = 100
        TITLE_HEIGHT = 20
        W, H = self.getClientSize()
        
        data = None
        drawOnDay = None
        if self.dataType == 'LHB':
            data = self.lhbData
            drawOnDay = self.drawOnDay_LHB
            title = '【龙虎榜】'
        elif self.dataType == 'LS_INFO':
            data = self.lsInfoData
            drawOnDay = self.drawOnDay_LS
            title = '【两市成交信息】'
        elif self.dataType == 'DDLR':
            ITEM_WIDTH = 80
            data = self.ddlrData
            drawOnDay = self.drawOnDay_DDLR
            title = '【大单流入】'
        TITLE_BG_COLOR = 0x1d201d
        self.drawer.fillRect(hdc, (0, 0, W, TITLE_HEIGHT), TITLE_BG_COLOR)
        # draw name
        rc = (0, 5, 120, TITLE_HEIGHT)
        self.drawer.drawText(hdc, title, rc, 0x00dddd, align = win32con.DT_LEFT)
        rg = self.findDrawDaysIndex(self.tradeDays, ITEM_WIDTH)
        if not data or not rg or rg[1] == rg[0]:
            return
        num = rg[1] - rg[0]
        sx = (W - num * ITEM_WIDTH) // 2
        sy = TITLE_HEIGHT
        for i in range(*rg):
            day = self.tradeDays[i]
            rc = (sx, sy, sx + ITEM_WIDTH - 1, H)
            if day == self.selectDay:
                self.drawer.fillRect(hdc, rc, 0x202020)
            self.drawer.drawLine(hdc, rc[2], 0, rc[2], H, 0x303030, win32con.PS_DASHDOTDOT)
            if i != rg[0]:
                self.drawer.drawText(hdc, day[5 : ], (sx, 0, sx + ITEM_WIDTH, TITLE_HEIGHT), 0xb0b0b0, win32con.DT_CENTER | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
            cur = data.get(day, None)
            if cur: drawOnDay(hdc, rc, cur, rg)
            sx += ITEM_WIDTH

    def drawOnDay_LHB(self, hdc, rc, data, rg):
        IH = 20
        sx = rc[0] + 10
        sy = rc[1] + 15
        fa = False
        for fs in data['famous']:
            if fs[0] == '-' and not fa:
                fa = True
                sy += 10
            self.drawer.drawText(hdc, fs, (sx, sy, rc[2], sy + IH), 0xc0c0c0, win32con.DT_LEFT)
            sy += IH

    def drawOnDay_LS(self, hdc, rc, data, rg):
        HEAD, TAIL = 40, 35

        zhqd = data.get('zhqd', None)
        if zhqd:
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 18))
            self.drawer.drawText(hdc, f'{zhqd}°', (rc[0], rc[1], rc[2], rc[1] + HEAD), color = 0xd0d0d0, align = win32con.DT_VCENTER | win32con.DT_CENTER | win32con.DT_SINGLELINE)

        upNumRg = self.getRangeOf(self.lsInfoData, 'upNum', *rg)
        downNumRg = self.getRangeOf(self.lsInfoData, 'downNum', *rg)
        upDownMax = max(*upNumRg, *downNumRg)
        sxUD = rc[0] + 30
        syUD = rc[1] + HEAD
        uh = int(data['upNum'] / upDownMax * (rc[3] - TAIL - syUD))
        y = (rc[3] - TAIL) - uh
        self.drawer.fillRect(hdc, (sxUD, y, sxUD + 5, rc[3] - TAIL), 0x2222dd) # upNum
        uh = int(data['downNum'] / upDownMax * (rc[3] - TAIL - syUD))
        y = (rc[3] - TAIL) - uh
        self.drawer.fillRect(hdc, (sxUD + 15, y, sxUD + 20, rc[3] - TAIL), 0x22dd22) # downNum
        
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
        self.drawer.drawText(hdc, f'{int(data["amount"])}亿', (rc[0], rc[3] - TAIL + 5, rc[2], rc[3]), color = 0xd0d0d0)

    def drawOnDay_DDLR(self, hdc, rc, data, rg):
        HEAD, TAIL = 45, 35
        buyRg = self.getRangeOf(self.ddlrData, 'buy', *rg)
        sellRg = self.getRangeOf(self.ddlrData, 'sell', *rg)
        bsMax = max(*buyRg, *sellRg)

        sxUD = rc[0] + 30
        syUD = rc[1] + HEAD
        uh = int(data['buy'] / bsMax * (rc[3] - TAIL - syUD))
        y = (rc[3] - TAIL) - uh
        self.drawer.drawText(hdc, f'{data["buy"] :.1f}', (sxUD - 20, y - 25, sxUD + 20, y), 0x2222dd)
        self.drawer.fillRect(hdc, (sxUD, y, sxUD + 5, rc[3] - TAIL), 0x2222dd)
        uh = int(data['sell'] / bsMax * (rc[3] - TAIL - syUD))
        y = (rc[3] - TAIL) - uh
        sxUD += 25
        self.drawer.drawText(hdc, f'{data["sell"] :.1f}', (sxUD - 20, y - 25, sxUD + 20, y), 0x22dd22)
        self.drawer.fillRect(hdc, (sxUD, y, sxUD + 5, rc[3] - TAIL), 0x22dd22)

        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14))
        self.drawer.drawText(hdc, f'{data["total"] :.1f}亿', (rc[0], rc[3] - TAIL + 10, rc[2], rc[3]), color = 0xd0d0d0)

    # format day (int, str(8), str(10)) to YYYY-MM-DD
    def formatDay(self, day):
        if not day:
            return None
        if type(day) == int:
            return f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        if type(day) == str and len(day) == 8:
            return day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        return day

    # param days : int, str(8), str(10)
    # return [startIdx, endIdx)
    def findDrawDaysIndex(self, days, itemWidth):
        if not days or len(days) == 0:
            return None
        days = [ self.formatDay(d) for d in days ]
        W, H = self.getClientSize()
        width = W
        num = width // itemWidth
        if num == 0:
            return None
        if len(days) <= num:
            return (0, len(days))
        if not self.selectDay:
            return (len(days) - num, len(days))
        #最左
        if self.selectDay <= days[0]:
            return (0, num)
        #最右
        if self.selectDay >= days[len(days) - 1]:
            return (len(days) - num, len(days))

        idx = 0
        for i in range(len(days) - 1): # skip last day
            if (self.selectDay >= days[i]) and (self.selectDay < days[i + 1]):
                idx = i
                break
        # 最右侧优先显示    
        #lastIdx = idx + num
        #if lastIdx > len(days):
        #    lastIdx = len(days)
        #if lastIdx - idx < num:
        #    idx -= num - (lastIdx - idx)
        #return (idx, lastIdx)

        # 居中优先显示
        fromIdx = lastIdx = idx
        while True:
            if lastIdx < len(days):
                lastIdx += 1
            if lastIdx - fromIdx >= num:
                break
            if fromIdx > 0:
                fromIdx -= 1
            if lastIdx - fromIdx >= num:
                break
        return (fromIdx, lastIdx)

    def getRangeOf(self, datas, name, startIdx, endIdx):
        maxVal, minVal = 0, 0
        for i in range(max(startIdx, 0), min(len(self.tradeDays), endIdx)):
            day = self.tradeDays[i]
            data = datas.get(day, None)
            if not data:
                continue
            v = data[name]
            if minVal == 0 and maxVal == 0:
                maxVal = minVal = v
            else:
                maxVal = max(maxVal, v)
                minVal = min(minVal, v)
        return minVal, maxVal

    def drawMinMode(self, hdc):
        title = '【我的热点】'
        rr = win32gui.GetClientRect(self.hwnd)
        win32gui.FillRect(hdc, win32gui.GetClientRect(self.hwnd), win32con.COLOR_WINDOWFRAME)  # background black
        win32gui.SetTextColor(hdc, 0x0000ff)
        win32gui.DrawText(hdc, title, len(title), rr, win32con.DT_CENTER | win32con.DT_VCENTER)

    def changeMode(self):
        if self.maxMode:
            WIDTH, HEIGHT = 150, 20
            y = self.rect[1] + self.rect[3] - HEIGHT - 20
            x = self.rect[2] // 2
            win32gui.SetWindowPos(self.hwnd, 0, x, y, WIDTH, HEIGHT, 0)
        else:
            win32gui.SetWindowPos(self.hwnd, 0, self.rect[0], self.rect[1], self.rect[2], self.rect[3], 0)
        self.maxMode = not self.maxMode
        win32gui.InvalidateRect(self.hwnd, None, True)

    def changeDataType(self):
        if not self.maxMode:
            return
        tp = self.DATA_TYPE
        idx = tp.index(self.dataType)
        idx = (idx + 1) % len(tp)
        self.dataType = tp[idx]
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateCode(self, code):
        self.loadTradeDays(None)
        self.updateLHBData(code)
        self.updateLSInfoData(code)
        self.updateDDLRData(code)
        self.invalidWindow()

    def updateLHBData(self, code):
        def gn(name : str):
            if not name: return name
            name = name.strip()
            i = name.find('(')
            if i < 0: return name
            return name[0 : i]

        ds = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.code == code)
        data = {}
        for d in ds:
            r = {'day': self.formatDay(d.day), 'famous': []}
            if '累计' in d.title:
                r['famous'].append('    3日')
            famous = str(d.famous).split('//')
            if len(famous) == 2:
                for f in famous[0].strip().split(';'):
                    if f: r['famous'].append('+ ' + gn(f))
                for f in famous[1].strip().split(';'):
                    if f: r['famous'].append('- ' + gn(f))
            else:
                r['famous'].append(' 无知名游资')
            data[r['day']] = r
        self.lhbData = data
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateDDLRData(self, code):
        ds = ths_orm.THS_DDLR.select().where(ths_orm.THS_DDLR.code == code).dicts()
        rs = {}
        for d in ds:
            rs[self.formatDay(d['day'])] = d
        for k in rs:
            d = rs[k]
            d['buy'] = d['activeIn'] + d['positiveIn']
            d['sell'] = d['activeOut'] + d['positiveOut']
        self.ddlrData = rs
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def updateLSInfoData(self, code):
        zsDatas = tdx_orm.TdxLSModel.select().dicts()
        qxDatas = tck_orm.CLS_SCQX.select()
        cs = {}
        for c in qxDatas:
            cs[c.day] = c.zhqd
        dd = {}
        for d in zsDatas:
            day = self.formatDay(d['day'])
            cc = cs.get(day, None)
            d['day'] = day
            d['zhqd'] = cc
            dd[day] = d
        self.lsInfoData = dd
        self.selectDay = None
        win32gui.InvalidateRect(self.hwnd, None, True)

    def loadTradeDays(self, day):
        if not self.tradeDays:
            ds = hot_utils.getTradeDaysByHot()
            self.tradeDays = [self.formatDay(d) for d in ds]
        if not day:
            return
        #for i in range(0, len(self.tradeDays)):
        #    if day < self.tradeDays[i]:
        #        continue
        #    if day > self.tradeDays[i]:
        #        self.tradeDays.insert(i, day)
        #    break
        if day > self.tradeDays[-1]:
            self.tradeDays.append(day)

    def updateSelectDay(self, newDay):
        newDay = self.formatDay(newDay)
        self.loadTradeDays(newDay)
        if not newDay or self.selectDay == newDay:
            return
        self.selectDay = newDay
        win32gui.InvalidateRect(self.hwnd, None, True)

    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return True
        elif msg == win32con.WM_LBUTTONDBLCLK:
            self.changeMode()
            self.notifyListener(self.Event('mode.change', self, maxMode = self.maxMode))
            return True
        elif msg == win32con.WM_RBUTTONUP:
            self.changeDataType()
            return True
        elif msg == win32con.WM_LBUTTONDOWN:
            win32gui.SendMessage(self.hwnd, win32con.WM_NCLBUTTONDOWN, 2, 0)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
