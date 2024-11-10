import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from Download import datafile
from Download import henxin, ths_ddlr
from THS import ths_win
from Common import base_win
from Tck import timeline

class TableWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.data = None
        self.totalData = None
        self.SCROLL_BAR_WIDTH = 10
        self.HEAD_HEIGHT = 35
        self.TAIL_HEIGHT = 100
        self.ROW_HEIGHT = 30
        self.startIdx = 0
        self.selIdx = -1
        self.filterName = None

    def drawHeadColumn(self, hdc):
        sz = self.getClientSize()[0] - self.SCROLL_BAR_WIDTH
        cw = sz // 3
        self.drawer.fillRect(hdc, (0, 0, sz, self.HEAD_HEIGHT), 0x191919)
        titles = ('开始时间', '成交量', '金额')
        for i, t in enumerate(titles):
            rc = (i * cw, 10, (i + 1) * cw, self.HEAD_HEIGHT)
            self.drawer.drawText(hdc, t, rc, 0xffffff)

    def drawTailColumn(self, hdc):
        def fmtMoney(m):
            if abs(m) < 10000:
                return f'{m}万'
            return f'{m / 10000 :.02f}亿'

        if not self.totalData:
            return
        sz = self.getClientSize()
        ch = self.TAIL_HEIGHT // (len(self.totalData) + 1)
        cw = sz[0] // 3
        sy = sz[1] - self.TAIL_HEIGHT
        self.drawer.fillRect(hdc, (0, sy, sz[0], sy + ch), 0x1A1A1A)
        self.drawer.drawRect(hdc, (0, sy, sz[0], sy + ch), 0xcacaca)
        titles = (str(self.filterName), '个数', '总金额') # , '主动', '被动'
        for i, t in enumerate(titles):
            rc = (i * cw, sy + 5, (i + 1) * cw, sy + ch)
            self.drawer.drawText(hdc, t, rc, 0xffffff)
        sy += ch
        for i, d in enumerate(self.totalData):
            if d['name'] == '买单':
                color = 0x2222ff
            elif d['name'] == '卖单':
                color = 0x22ff22
            else:
                color = 0x2222ff if d['money'] >= 0 else 0x22ff22
            vals = (d['name'], d['num'], fmtMoney(d['money']))
            for j in range(len(vals)):
                rc = (j * cw, sy + 5, (j + 1) * cw, sy + ch)
                self.drawer.drawText(hdc, str(vals[j]), rc, color)
            sy += ch

    def getVisibleRange(self):
        rowNum = self.getMaxRowNum() - 1
        return (self.startIdx, min(self.startIdx + rowNum, len(self.data)))
    
    def drawRowItem(self, hdc, sy, data, cw):
        _btime = data['beginTime']
        bs = data['bs']
        money = data['money']
        vol = data['vol']
        sy += (self.ROW_HEIGHT - 14) // 2
        rc = [0, sy, cw, sy + self.ROW_HEIGHT]
        self.drawer.drawText(hdc, f'{_btime // 100 :02d}:{_btime % 100 :02d}', rc, color=0xffffff)
        
        colors = (0x2E2FFF, 0x0F1CBA, 0x00D600, 0x279F3D)
        color = colors[bs - 1]
        rc[0], rc[2]= cw, cw * 2 - 20
        self.drawer.drawText(hdc, f'{vol}手', rc, color=color, align=win32con.DT_RIGHT)
        rc[0], rc[2]= cw * 2, cw * 3 - 20
        self.drawer.drawText(hdc, f'{money}万', rc, color=color, align=win32con.DT_RIGHT)

    def drawRows(self, hdc):
        w = self.getClientSize()[0] - self.SCROLL_BAR_WIDTH
        cw = w // 3
        vr = self.getVisibleRange()
        y = self.HEAD_HEIGHT
        for i in range(*vr):
            if i == self.selIdx:
                self.drawer.fillRect(hdc, (0, y, w, y + self.ROW_HEIGHT), 0x393533)
            self.drawRowItem(hdc, y, self.data[i], cw)
            y += self.ROW_HEIGHT
    
    def findNearestTime(self, _time):
        if not self.data:
            return -1
        for i, d in enumerate(self.data):
            if d['beginTime'] >= _time:
                return i
        return -1

    def onListen(self, evt, args):
        if evt.name== 'click.ddlr.time':
            _time = evt.time
            idx = self.findNearestTime(_time)
            self.startIdx = idx
            self.selIdx = idx
            win32gui.InvalidateRect(self.hwnd, None, True)
    
    def onDraw(self, hdc):
        self.drawer.fillRect(hdc, (0, 0, *self.getClientSize()), 0x151313)
        self.drawHeadColumn(hdc)
        if not self.data:
            return
        self.drawRows(hdc)
        self.drawTailColumn(hdc)

    def setData(self, data, filterName):
        self.filterName = filterName
        self.startIdx = 0
        self.selIdx = -1
        self.totalData = None
        if not data:
            self.data = None
            return
        self.data = []
        for ds in data:
            for d in ds:
                self.data.append(d)
        buy = {'name': '买单', 'num' : 0, 'money': 0, 'zdMoney': 0, 'bdMoney': 0}
        sell = {'name': '卖单','num' : 0, 'money': 0, 'zdMoney': 0, 'bdMoney': 0}
        for d in self.data:
            bs, money = d['bs'], d['money']
            rr = buy if bs <= 2 else sell
            rr['num'] += 1
            rr['money'] += money
            if bs % 2 == 1:
                rr['zdMoney'] += money
            else:
                rr['bdMoney'] += money
        total = {'name':'差值', 'num': buy['num'] - sell['num'], 'money': buy['money'] - sell['money']}
        self.totalData = (buy, sell, total)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onClick(self, x, y):
        #win32gui.SetFocus(self.hwnd)
        if y > self.HEAD_HEIGHT and y < self.getClientSize()[1] - self.TAIL_HEIGHT:
            y -= self.HEAD_HEIGHT
            self.selIdx = y // self.ROW_HEIGHT + self.startIdx
            win32gui.InvalidateRect(self.hwnd, None, True)

    def getMaxRowNum(self):
        h = self.getClientSize()[1]
        h -= self.HEAD_HEIGHT + self.TAIL_HEIGHT
        num = (h + self.ROW_HEIGHT - 1) // self.ROW_HEIGHT
        return num

    def onMouseWheel(self, delta):
        if not self.data:
            return
        if delta & 0x8000:
            delta = delta - 0xffff - 1
        delta = -delta // 120
        addIdx = delta * 5
        self.startIdx = max(addIdx + self.startIdx, 0)
        self.startIdx = min(self.startIdx, len(self.data) - self.getMaxRowNum())
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            self.onMouseWheel((wParam >> 16) & 0xffff)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class DDMoneyWindow(base_win.BaseWindow):
    def __init__(self):
        super().__init__()
        self.MARGINS = (51, 50, 60, 30)
        self.data = None #连续数据
        self.jjData = None #竟价数据 9:25 - 9:30
        self.buyMax = 0
        self.sellMax = 0
        self.jjBuyMax = 0
        self.jjSellMax = 0
        self.mouseXY = None
        self.title = None

    def setTitle(self, title):
        self.title = title

    def setData(self, data):
        if not data:
            self.data = None
            return
        self.data = []
        self.jjData = []
        for i in range(0, 250):
            self.data.append({'buy': 0, 'sell': 0, 'time': 0})
        for i in range(0, 10):
            self.jjData.append({'buy': 0, 'sell': 0, 'time': 0})
        for ds in data:
            _time = ds[0]['beginTime']
            if _time <= 930:
                rs = self.jjData[_time - 925]
            else:
                idx = self.timeToIdx(_time)
                rs = self.data[idx]
            rs['time'] = _time
            for d in ds:
                bs, money = d['bs'], d['money']
                if bs <= 2:
                    rs['buy'] += money
                else:
                    rs['sell'] += money
        buyMax, sellMax = 0, 0
        for d in self.data:
            buyMax = max(d['buy'], buyMax)
            sellMax = max(d['sell'], sellMax)
        self.buyMax = buyMax
        self.sellMax = sellMax

        buyMax, sellMax = 0, 0
        for d in self.jjData:
            buyMax = max(d['buy'], buyMax)
            sellMax = max(d['sell'], sellMax)
        self.jjBuyMax = buyMax
        self.jjSellMax = sellMax
        win32gui.InvalidateRect(self.hwnd, None, True)

    def getMainRect(self):
        sz = self.getClientSize()
        return (self.MARGINS[0], self.MARGINS[1], sz[0] - self.MARGINS[2], sz[1] - self.MARGINS[3])

    def timeToIdx(self, _time):
        if _time <= 930:
            return 0
        hour = _time // 100
        minute = _time % 100
        ds = 0
        if hour <= 11:
            ds = 60 * (hour - 9) + minute - 30
            return ds
        ds = 120
        ds += minute + (hour - 13) * 60
        return ds

    def getMinuteX(self, idx):
        mr = self.getMainRect()
        w = mr[2] - mr[0]
        sw = w / 240
        return int(sw * idx) + mr[0]

    def getMinuteIdx(self, x):
        if not self.data:
            return -1
        mr = self.getMainRect()
        if x < mr[0]:
            return -1
        x -= mr[0]
        w = mr[2] - mr[0]
        sw = w / 240
        idx = int(x / sw)
        if idx >= 240:
            return -1
        return idx

    def getMinuteData(self, idx):
        fds = self.model.fsData
        if idx < 0 or not fds:
            return None
        return fds[idx]

    def formatMoney(self, money):
        if money < 10000:
            return f'{money}万'
        return f'{money / 10000 :.02f}亿'

    def drawBackground(self, hdc):
        mc = self.getMainRect()
        self.drawer.drawRect(hdc, mc, 0x36332E)
        ms = (1000, 1030, 1100, 1300, 1330, 1400, 1430)
        for m in ms:
            idx = self.timeToIdx(m)
            x = self.getMinuteX(idx)
            self.drawer.drawLine(hdc, x, mc[1], x, mc[3], 0x36332E, style=win32con.PS_DOT)
        bm = self.formatMoney(self.buyMax)
        sm = self.formatMoney(self.sellMax)
        bmRc = (mc[2] + 3, mc[0] - 10, mc[2] + 50, mc[0] + 10)
        smRc = (mc[2] + 3, mc[3] - 10, mc[2] + 50, mc[3] + 10)
        self.drawer.drawText(hdc, bm, bmRc, 0x3333ff, align=win32con.DT_LEFT)
        self.drawer.drawText(hdc, sm, smRc, 0x33ff33, align=win32con.DT_LEFT)
        # draw title
        sdc = win32gui.SaveDC(hdc)
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 16, weight = 1200))
        self.drawer.drawText(hdc, self.title, (0, 3, self.getClientSize()[0], 30), 0x333399)
        win32gui.RestoreDC(hdc, sdc)

    def getZeroY(self, jj):
        mc = self.getMainRect()
        w, h = mc[2] - mc[0], mc[3] - mc[1]
        if jj:
            if self.jjBuyMax + self.jjSellMax == 0:
                return mc[1]
            return mc[1] + int(self.jjBuyMax / (self.jjBuyMax + self.jjSellMax) * h)
        if self.buyMax + self.sellMax == 0:
            return mc[1]
        return mc[1] + int(self.buyMax / (self.buyMax + self.sellMax) * h)

    def drawJJ(self, hdc):
        if not self.jjData:
            return
        mc = self.getMainRect()
        jjZeroY = self.getZeroY(True)
        sz = self.getClientSize()
        jjH = sz[1]
        for jj in self.jjData:
            if jj['time'] == 0:
                continue
            jjX = 5 # 925
            if jj['time'] == 930:
                jjX = 35
            h925 = int(jj['buy'] / (self.jjBuyMax + self.jjSellMax) * jjH)
            rc = (jjX, jjZeroY - h925, jjX + 5, jjZeroY)
            self.drawer.fillRect(hdc, rc, 0x3333ff)
            y = max(rc[1] - 20, 2)
            rc2 = (jjX, y, jjX + 50, y + 20)
            self.drawer.drawText(hdc, self.formatMoney(jj['buy']), rc2, 0xdddddd)

            h925 = int(jj['sell'] / (self.jjBuyMax + self.jjSellMax) * jjH)
            rc = (jjX, jjZeroY, jjX + 5, jjZeroY + h925)
            self.drawer.fillRect(hdc, rc, 0x33ff33)
            y = min(rc[3] + 20, sz[1])
            rc2 = (jjX, y - 20, jjX + 50, y)
            self.drawer.drawText(hdc, self.formatMoney(jj['sell']), rc2, 0xdddddd)

    def drawMain(self, hdc):
        if not self.data:
            return
        mc = self.getMainRect()
        w, h = mc[2] - mc[0], mc[3] - mc[1]
        zeroY = self.getZeroY(False)
        self.drawer.drawLine(hdc, mc[0], zeroY, mc[2], zeroY, 0x36332E)

        for i, d in enumerate(self.data):
            if not (d['buy'] > 0 or d['sell'] > 0):
                continue
            x = self.getMinuteX(i)
            if d['buy'] > 0:
                hx = int(d['buy'] / (self.buyMax + self.sellMax) * h)
                rc = (x, zeroY - hx, x + 2, zeroY)
                self.drawer.fillRect(hdc, rc, 0x3333ff)
            if d['sell'] > 0:
                hx = int(d['sell'] / (self.buyMax + self.sellMax) * h)
                rc = (x, zeroY, x + 2, zeroY + hx)
                self.drawer.fillRect(hdc, rc, 0x33ff33)

    def test(self, hdc):
        for i in range(10):
            rc = [100 + i * 30, 5, 120 + i * 30, 25]
            self.drawer.fillCycle(hdc, rc,  0x2524A1) # 0x2524A1  0x2E2FFF
            vs = win32gui.SetROP2(hdc, win32con.R2_MERGEPEN)
            rc = [100 + i + i * 30, 5 + i, 120 + i * 30 - i, 25 - i]
            self.drawer.fillCycle(hdc, rc, 0x0F570E) # 0x0F570E 0x00D600
            win32gui.SetROP2(hdc, vs)

    def onDraw(self, hdc):
        self.drawer.drawRect(hdc, (0, 0, *self.getClientSize()), 0x36332E)
        rect = self.getMainRect()
        if not self.data:
            return
        self.drawBackground(hdc)
        self.drawJJ(hdc)
        self.drawMain(hdc)
        self.drawMouse(hdc)

    def getMoneyOfMainY(self, y):
        rc = self.getMainRect()
        zeroY = self.getZeroY(False)
        if y >= zeroY: # sell
            dy = y - zeroY
            return int(dy / (rc[3] - zeroY) * self.sellMax)
        dy = zeroY - y
        return int(dy / (zeroY - rc[1]) * self.buyMax)

    def drawMouse(self, hdc):
        if not self.mouseXY:
            return
        x, y = self.mouseXY
        rect = self.getMainRect()
        isInMainRect = x >= rect[0] and x <= rect[2] and y >= rect[1] and y <= rect[3]
        if isInMainRect:
            money = self.getMoneyOfMainY(y)
            money = self.formatMoney(money)
            self.drawer.drawLine(hdc, rect[0], y, rect[2], y, 0xaaaaaa, style=win32con.PS_DOT)
            rc = (x, y - 22, x + 60, y - 3)
            self.drawer.drawText(hdc, money, rc, 0xdddddd)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.mouseXY = (x, y)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class DDLR_MinuteMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.fsWin = None
        self.tableWin = None
        self.shareMem = ths_win.ThsShareMemory.instance()
        trs = (40, 340, 'auto')
        tcs = (250, 'auto')
        self.gridLayout = base_win.GridLayout(trs, tcs, (10, 5))

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''):
        super().createWindow(parentWnd, rect, style, title = '大单复盘')

        size = self.getClientSize()
        self.tableWin = TableWindow()
        rc = (0, 50, 250, size[1] - 50)
        self.tableWin.createWindow(self.hwnd, rc)

        rc2 = (rc[2] + 5, 0, size[0] - rc[2] - 10, 400)
        self.fsWin = timeline.TimelineWindow()
        self.fsWin.createWindow(self.hwnd, rc2)
        self.fsWin.addListener(self.tableWin.onListen, None)
        
        grs = (  {'title': '50万', 'val': 50, 'desc': '50万以上'},
                 {'title': '100万', 'val': 100, 'desc': '100万以上'},
                 {'title': '300万', 'val': 300, 'desc': '300万以上'},
                 {'title': '500万', 'val': 500, 'desc': '500万以上'} )
        self.moneyBtns = base_win.GroupButton(grs)
        rc3 = (63, 10, 190, 30)
        self.moneyBtns.createWindow(self.hwnd, rc3)
        self.moneyBtns.addListener(self.onListenMoney, None)

        refreshBtn = base_win.Button({'title': '同步', 'val': 'Refresh'})
        rc4 = (5, 10, 50, 30)
        refreshBtn.createWindow(self.hwnd, rc4)
        refreshBtn.addListener(self.onListenRefresh, None)

        self.moneyWin = DDMoneyWindow()
        rc5 = (rc[2] + 5, rc2[3] + 10, size[0] - rc[2] - 10, size[1] - rc2[3]- 15)
        self.moneyWin.createWindow(self.hwnd, rc5)

        absLayout = base_win.AbsLayout()
        absLayout.setContent(rc4[0], rc4[1], refreshBtn)
        absLayout.setContent(rc3[0], rc3[1], self.moneyBtns)
        self.gridLayout.setContent(0, 0, absLayout, {'autoFit' : False})
        self.gridLayout.setContent(1, 0, self.tableWin, {'verExpand': True})
        self.gridLayout.setContent(0, 1, self.fsWin, {'verExpand' : 1})
        self.gridLayout.setContent(2, 1, self.moneyWin)
        self.gridLayout.resize(0, 0, size[0], size[1])

        # TODO: remove 
        #self.updateCodeDay('601096', 20240119)

    def onListenMoney(self, evt, args):
        if evt.name != 'ClickSelect':
            return
        group = evt.group
        ds = self.fsWin.model.filterDDLR(group['val'])
        self.tableWin.setData(ds, group['desc'])
        self.moneyWin.setData(ds)
        win32gui.InvalidateRect(self.fsWin.hwnd, None, True)

    def onListenRefresh(self, evt, args):
        if evt.name != 'ClickSelect':
            return
        self.shareMem.open()
        code = self.shareMem.readCode()
        day = self.shareMem.readSelDay()
        if not code or not day:
            return
        code = f'{code :06d}'
        self.updateCodeDay(code, day)

    def updateCodeDay(self, code, day):
        if type(code) == int:
            code = f'{code :06d}'
        if type(day) == str:
            day = int(day.replace('-', ''))
        xx = ths_orm.THS_Newest.get_or_none(ths_orm.THS_Newest.code == code)
        name = xx.name if xx else ''
        title = f'{code} {name} {day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        win32gui.SetWindowText(self.hwnd, f'大单复盘 -- {title}')
        self.fsWin.update(code, day)
        ds = self.fsWin.model.filterDDLR(50)
        gp0 = self.moneyBtns.groups[0]
        self.moneyBtns.setSelGroup(0)
        self.tableWin.setData(ds, gp0['desc'])
        self.moneyWin.setTitle(title)
        self.moneyWin.setData(ds)
        win32gui.InvalidateRect(self.fsWin.hwnd, None, True)

    def onSize(self):
        size = self.getClientSize()
        self.gridLayout.resize(0, 0, size[0], size[1])
        self.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEWHEEL:
            win32gui.SendMessage(self.tableWin.hwnd, msg, wParam, lParam)
            return True
        if msg == win32con.WM_SIZE:
            self.onSize()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    mgr = DDLR_MinuteMgrWindow()
    mgr.createWindow(None,(0, 0, 1000, 400), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE )
    win32gui.ShowWindow(mgr.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()