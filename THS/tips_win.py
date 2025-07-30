import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, threading, copy, traceback, json
import sys, pyautogui
import peewee as pw
import types

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download import datafile, henxin, cls, ths_iwencai
from utils import hot_utils
from ui import bkgn_view, dialog, base_win, kline_utils
from orm import d_orm, def_orm, ths_orm, cls_orm

# param days (int): [YYYYMMDD, ....]
# param selDay : int
# return [startIdx, endIdx)
def findDrawDaysIndex(days, selDay, maxNum):
    if not days:
        return (0, 0)
    if len(days) <= maxNum:
        return (0, len(days))
    if not selDay:
        return (len(days) - maxNum, len(days))
    if type(days[0]) != int:
        for i in range(len(days)):
            days[i] = int(days[i].replace('-', '.'))
    #最左
    if selDay <= days[0]:
        return (0, maxNum)
    #最右
    if selDay >= days[len(days) - 1]:
        return (len(days) - maxNum, len(days))
    
    idx = 0
    for i in range(len(days) - 1): # skip last day
        if (selDay >= days[i]) and (selDay < days[i + 1]):
            idx = i
            break
    # 居中优先显示
    fromIdx = lastIdx = idx
    while True:
        if lastIdx < len(days):
            lastIdx += 1
        if lastIdx - fromIdx >= maxNum:
            break
        if fromIdx > 0:
            fromIdx -= 1
        if lastIdx - fromIdx >= maxNum:
            break
    return (fromIdx, lastIdx)

def findDrawDaysIndexOfLastPage(days, maxNum):
    if not days:
        return (0, 0)
    if maxNum >= len(days):
        return (0, len(days))
    return (len(days) - maxNum, len(days))

class CardView(base_win.Drawer):
    def __init__(self, cardWindow):
        super().__init__()
        self.hwnd = cardWindow.hwnd
        self.cardWindow = cardWindow

    def onDraw(self, hdc):
        pass
    def winProc(self, hwnd, msg, wParam, lParam):
        return False
    def getWindowTitle(self):
        return None

class CardWindow(base_win.NoActivePopupWindow):
    # maxSize = (width, height)
    # minSize = (width, height)
    def __init__(self, maxSize, minSize) -> None:
        super().__init__()
        self.cardViews = []
        self.MAX_SIZE = maxSize
        self.MIN_SIZE = minSize
        self.maxMode = True
        self.curCardViewIdx = 0
        self.settings = None

    def getWindowState(self):
        rc = win32gui.GetWindowRect(self.hwnd)
        rs = {'maxMode': self.maxMode, 'pos': (rc[0], rc[1]), 'settings': self.settings}
        return rs
    
    def setWindowState(self, state):
        if not state:
            return
        x, y = state['pos']
        self.maxMode = state['maxMode']
        st = state.get('settings', None)
        if st:
            self.settings = st
        if state['maxMode']:
            self.move(x, y)
            self.resize(*self.MAX_SIZE)
            #win32gui.SetWindowPos(self.hwnd, 0, x, y, *self.MAX_SIZE, win32con.SWP_NOZORDER)
        else:
            self.move(x, y)
            self.resize(*self.MIN_SIZE)
            #win32gui.SetWindowPos(self.hwnd, 0, x, y, *self.MIN_SIZE, win32con.SWP_NOZORDER)

    def addCardView(self, cardView):
        self.cardViews.append(cardView)

    def getCurCardView(self):
        if self.cardViews:
            idx = self.curCardViewIdx % len(self.cardViews)
            return self.cardViews[idx]
        return None

    def onDraw(self, hdc):
        cardView = self.getCurCardView()
        if self.maxMode and cardView:
            cardView.onDraw(hdc)
    
    def changeCardView(self):
        idx = self.curCardViewIdx
        self.curCardViewIdx = (idx + 1) % len(self.cardViews)
        if self.curCardViewIdx != idx:
            cv = self.getCurCardView()
            title = cv.getWindowTitle()
            if title != None:
                win32gui.SetWindowText(self.hwnd, title)
            win32gui.InvalidateRect(self.hwnd, None, True)

    def showSettings(self):
        if not self.settings:
            return
        menu = base_win.PopupMenu.create(self.hwnd, self.settings)
        menu.addNamedListener('Select', self.onSettings)
        menu.show(*win32gui.GetCursorPos())

    def onSettings(self, evt, args):
        pass

    def getSetting(self, name):
        if not self.settings or not name:
            return None
        for s in self.settings:
            if s['name'] == name:
                return s
        return None

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            self.maxMode = not self.maxMode
            if self.maxMode:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MAX_SIZE, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER) # win32con.HWND_TOP
            else:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MIN_SIZE, win32con.SWP_NOMOVE| win32con.SWP_NOZORDER)
            return True
        if msg == win32con.WM_RBUTTONUP:
            self.changeCardView()
            return True
        if msg == win32con.WM_MBUTTONUP:
            self.showSettings()
            return True

        cardView = self.getCurCardView()
        if self.maxMode and cardView:
            r = cardView.winProc(hwnd, msg, wParam, lParam)
            if r != False:
                return r
        return super().winProc(hwnd, msg, wParam, lParam)

class ZSCardView(CardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.selectDay = 0

    def onDraw(self, hdc):
        if not self.zsData:
            return
        H = 18
        rect = win32gui.GetClientRect(self.hwnd)
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H - 2
        MIN_COL_WIDTH = 160
        COL_NUM = RW // MIN_COL_WIDTH
        COL_WIDTH = RW // COL_NUM
        days = [d['day'] for d in self.zsData]
        ks = self.cardWindow.getSetting('LOCK_TO_LAST_PAGE')
        if ks and ks['checked']:
            # lock last page
            fromIdx, endIdx = findDrawDaysIndexOfLastPage(days, MAX_ROWS * COL_NUM)
        else:
            fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS * COL_NUM)
        for i in range(fromIdx, endIdx):
            zs = self.zsData[i]
            if zs['day'] == self.selectDay:
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = str(zs['day'])[4 : ]
            day = day[0 : 2] + '.' + day[2 : 4]
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H + 2 + H
            x = (idx // MAX_ROWS) * COL_WIDTH
            rect = (x + 2, y, x + COL_WIDTH, y + H)
            line = f'{day}    {zs["zdf_PM"] :< 4d}     {zs["zdf_topLevelPM"] :< 6d}'
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
        # draw title
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.SetTextColor(hdc, 0xdddddd)
        for i in range(COL_NUM):
            trc = (i * COL_WIDTH, 0, i * COL_WIDTH + COL_WIDTH, H)
            title = f'       全市排名  一级排名'
            win32gui.DrawText(hdc, title, len(title), trc, win32con.DT_LEFT)
        win32gui.MoveToEx(hdc, 0, H)
        win32gui.LineTo(hdc, RW, H)
        if COL_NUM == 2:
            win32gui.MoveToEx(hdc, COL_WIDTH, 0)
            win32gui.LineTo(hdc, COL_WIDTH, RH)
        win32gui.DeleteObject(pen)
    
    def updateCode(self, code):
        self.zsData = self.getZSInfo(code)
        name = self.zsData[0]['name'] if self.zsData else ''
        win32gui.SetWindowText(self.hwnd, f'{code} {name}')

    def getZSInfo(self, zsCode):
        if type(zsCode) == int:
            zsCode = f'{zsCode :06d}'
        qr = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.code == zsCode).order_by(ths_orm.THS_ZS_ZD.day.asc())
        data = [d.__data__ for d in qr]
        for d in data:
            d['day'] = int(d['day'].replace('-', ''))
        return data
    
    def updateSelectDay(self, selDay):
        if type(selDay) == str:
            selDay = int(selDay.replace('-', ''))
        self.selectDay = selDay

class HotCardView(CardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.hotData = None
        self.ROW_HEIGHT = 18
        self.hotsInfo = [None] * 25  # {data: , rect: (), }
        self.tipInfo = {} # {rect:(), hotInfo: xx, detail:[], }
        self.resetTipInfo()
        self.showStartIdx = 0
        self.selectDay = 0

    def resetTipInfo(self):
        self.tipInfo['rect'] = None
        self.tipInfo['hotRect'] = None
        self.tipInfo['detail'] = None

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def onDraw(self, hdc):
        drawer : base_win.Drawer = base_win.Drawer.instance()
        rr = win32gui.GetClientRect(self.hwnd)
        if not self.hotData:
            drawer.drawText(hdc, '无Hot信息', rr, 0xdddddd)
            return
        win32gui.SetTextColor(hdc, 0xdddddd)

        RH = rr[3] - rr[1]
        RW = rr[2] - rr[0]
        MAX_ROWS = RH // self.ROW_HEIGHT - 1
        MIN_COL_WIDTH = 80
        MAX_COLS = max(RW // MIN_COL_WIDTH, 1)
        COL_WIDTH = RW // MAX_COLS
        days = [d['day'] for d in self.hotData]
        ks = self.cardWindow.getSetting('LOCK_TO_LAST_PAGE')
        if ks and ks['checked']:
            # lock last page
            fromIdx, endIdx = findDrawDaysIndexOfLastPage(days, MAX_ROWS * MAX_COLS)
        else:
            fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS * MAX_COLS)
        for i in range(len(self.hotsInfo)):
            self.hotsInfo[i] = None
        for i in range(fromIdx, endIdx):
            hot = self.hotData[i]
            if hot['day'] == self.selectDay:
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            day = str(hot['day'])[4 : ]
            day = day[0 : 2] + '.' + day[2 : 4]
            zhHotOrder = '' if hot['zhHotOrder'] == 0 else f"{hot['zhHotOrder'] :>3d}"
            line = f"{day}   {zhHotOrder}"
            idx = i - fromIdx
            col = idx // MAX_ROWS
            row = idx % MAX_ROWS
            y = row * self.ROW_HEIGHT + self.ROW_HEIGHT
            x = col * COL_WIDTH
            rect = (x + 4, y, x + COL_WIDTH, y + self.ROW_HEIGHT)
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
            self.hotsInfo[i - fromIdx] = {'data': hot, 'rect': rect}
        drawer.fillRect(hdc, (0, 0, rr[2], self.ROW_HEIGHT), 0x202020)
        drawer.drawLine(hdc, RW // 2, self.ROW_HEIGHT, RW // 2, rr[3], 0xaaccaa)
        # top
        topHots = 99999
        for d in self.hotData:
            topHots = min(topHots, d['zhHotOrder'])
        drawer.drawText(hdc, f'  最高  {topHots}', (0, 0, rr[2], self.ROW_HEIGHT), 0x44cc44, win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def updateCode(self, code):
        self.showStartIdx = 0
        self.resetTipInfo()
        for i in range(len(self.hotsInfo)):
            self.hotsInfo[i] = None
        if type(code) != int:
            code = int(code)
        self.code = code
        # load hot data
        qq2 = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.day, ths_orm.THS_HotZH.zhHotOrder).where(ths_orm.THS_HotZH.code == code).dicts()
        self.hotData = [d for d in qq2]
        newest = hot_utils.DynamicHotZH.instance().getNewestHotZH()
        if code in newest:
            data = newest[code]
            if not self.hotData or self.hotData[-1]['day'] != data['day']:
                self.hotData.append(data)
        win32gui.SetWindowText(self.hwnd, self.getWindowTitle())

    def getWindowTitle(self):
        obj = ths_orm.THS_GNTC.get_or_none(code = f"{self.code :06d}")
        if obj:
            title = f"{self.code :06d}  {obj.name}"
        else:
            title = f"{self.code :06d}"
        return title

    def isInRect(self, x, y, rect):
        if not rect:
            return False
        f1 = x >= rect[0] and x < rect[2]
        f2 = y >= rect[1] and y < rect[3]
        return f1 and f2

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            return False
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                self.showStartIdx += 5
            else:
                self.showStartIdx -= 5
            win32gui.InvalidateRect(hwnd, None, True)
            return True
        return False
    
    def setTip(self, hot):
        code = self.code
        rr = win32gui.GetClientRect(self.hwnd)
        w, h = rr[2], rr[3]
        if (hot['rect'][0] + hot['rect'][2]) >= w:
            tipRect = (0, 0, w // 2, h)
        else:
            tipRect = (w // 2, 0, w, h)
        self.tipInfo['rect'] = tipRect
        self.tipInfo['hotRect'] = hot['rect']
        if 'detail' not in hot:
            day = hot['data']['day']
            info = ths_orm.THS_Hot.select().where(ths_orm.THS_Hot.code == code, ths_orm.THS_Hot.day == day)
            hot['detail'] = [d.__data__ for d in info]
        self.tipInfo['detail'] = hot['detail']

class ZTCardView(CardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.kplZTData = None
        self.ROW_HEIGHT = 18
        self.selectDay = 0
        self.ormClazz = None
        self.emptyLine = '\n\n无涨停信息'
        self.fontSize = 12
        self.code = None
        self.visibleRange = None

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def updateCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        self.code = code
        qq = self.ormClazz.select().where(self.ormClazz.code == code).order_by(self.ormClazz.day.asc())
        def fmtDay(d): 
            d['day'] = d['day'].replace('-', '')
            return d
        self.kplZTData = [fmtDay(d) for d in qq.dicts()]
        win32gui.SetWindowText(self.hwnd, self.getWindowTitle())

    def drawLine(self, hdc, kpl, rect):
        day = kpl['day']
        day = day[2 : 4] + '-' + day[4 : 6] + '-' + day[6 : ]
        line = f"{day} {kpl['ztReason']}({kpl['ztNum']})"
        win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT)

    def getCodeName(self):
        obj = ths_orm.THS_GNTC.get_or_none(code = self.code)
        if obj:
            return obj.name
        return ''

    def getWindowTitle(self):
        name = self.getCodeName()
        title = f"{self.code}  {name}"
        return title

    def onDraw(self, hdc):
        self.visibleRange = None
        win32gui.SetTextColor(hdc, 0xdddddd)
        rect = win32gui.GetClientRect(self.hwnd)
        if not self.kplZTData:
            win32gui.DrawText(hdc, self.emptyLine, len(self.emptyLine), rect, win32con.DT_CENTER)
            return
        self.use(hdc, self.getFont(fontSize = self.fontSize))
        H = self.ROW_HEIGHT
        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // H
        COL_WIDTH = RW
        days = [d['day'] for d in self.kplZTData]
        ks = self.cardWindow.getSetting('LOCK_TO_LAST_PAGE')
        if ks and ks['checked']:
            # lock last page
            fromIdx, endIdx = findDrawDaysIndexOfLastPage(days, MAX_ROWS)
        else:
            fromIdx, endIdx = findDrawDaysIndex(days, self.selectDay, MAX_ROWS)
        self.visibleRange = (fromIdx, endIdx)

        for i in range(fromIdx, endIdx):
            kpl = self.kplZTData[i]
            if kpl['day'] == str(self.selectDay):
                win32gui.SetTextColor(hdc, 0x0000ff)
            else:
                win32gui.SetTextColor(hdc, 0xdddddd)
            idx = i - fromIdx
            y = (idx % MAX_ROWS) * H
            x = (idx // MAX_ROWS) * COL_WIDTH
            self.drawLine(hdc, kpl, (x, y, x + COL_WIDTH, y + H))

class THS_ZTCardView(ZTCardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.ormClazz = ths_orm.THS_ZT
        self.emptyLine = '\n\n无同花顺涨停信息'
        self.fontSize = 12
        self.ROW_HEIGHT = 16

    def getWindowTitle(self):
        title = f'{self.code} {self.getCodeName()} THS'
        return title

    def drawLine(self, hdc, kpl, rect):
        day = kpl['day']
        day = day[4 : 6] + '.' + day[6 : ]
        line = kpl['ztReason']
        rc2 = (rect[0] + 35, rect[1], rect[2], rect[3])
        win32gui.DrawText(hdc, line, len(line), rc2, win32con.DT_LEFT) #  | win32con.DT_WORDBREAK
        win32gui.DrawText(hdc, day, len(day), rect, win32con.DT_LEFT)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            if not self.visibleRange:
                return False
            idx = y // self.ROW_HEIGHT
            if idx + self.visibleRange[0] >= self.visibleRange[1]:
                return False
            win32gui.InvalidateRect(hwnd, None, True)
            win32gui.UpdateWindow(hwnd)

            kpl = self.kplZTData[idx + self.visibleRange[0]]
            hdc = win32gui.GetDC(hwnd)
            self.use(hdc, self.getFont(fontSize = self.fontSize))
            win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
            win32gui.SetTextColor(hdc, 0xffff00)
            CR = win32gui.GetClientRect(hwnd)
            W = CR[2] - CR[0]
            H = CR[3] - CR[1]
            rc = (35, 0, W, self.ROW_HEIGHT)
            line = kpl['ztReason']
            _, rc2 = win32gui.DrawText(hdc, line, -1, rc, win32con.DT_CALCRECT | win32con.DT_WORDBREAK)

            if rc2[3] > rc[3]:
                isLast = idx == H // self.ROW_HEIGHT - 1
                if isLast:
                    sy = H - (rc2[3] - rc2[1])
                else:
                    sy = idx * self.ROW_HEIGHT
                drc = (rc[0], sy, rc[2], sy + rc2[3] - rc2[1])
                win32gui.FillRect(hdc, drc, self.getBrush(0x202020))
                win32gui.DrawText(hdc, line, -1, drc, win32con.DT_LEFT | win32con.DT_WORDBREAK)
            win32gui.ReleaseDC(hwnd, hdc)
            return True
        return False
    
class Cls_ZTCardView(ZTCardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.ormClazz = cls_orm.CLS_ZT
        self.emptyLine = '\n\n无财联社涨停信息'
        self.fontSize = 12
        self.ROW_HEIGHT = 18

    def getWindowTitle(self):
        title = f'{self.code} {self.getCodeName()} CLS'
        return title

    def drawLine(self, hdc, kpl, rect):
        day = kpl['day']
        day = day[4 : 6] + '.' + day[6 : ]
        line = kpl['ztReason']
        rc2 = (rect[0] + 35, rect[1], rect[2], rect[3])
        win32gui.DrawText(hdc, line, len(line), rc2, win32con.DT_LEFT | win32con.DT_WORDBREAK)
        win32gui.DrawText(hdc, day, len(day), rect, win32con.DT_LEFT)

class SimpleWindow(CardWindow):
    # type_ is 'HOT' | 'ZT_GN'
    def __init__(self, type_) -> None:
        if type_ == 'HOT':
            super().__init__((200, 238), (150, 30))
        else:
            super().__init__((200, 250), (150, 30))
        self.curCode = None
        self.selectDay = 0
        self.zsCardView = None
        self.type_ = type_
        self.settings = [
            {'name': 'LOCK_TO_LAST_PAGE', 'title': '锁定到最后一页', 'checked': False},
        ]

    def createWindow(self, parentWnd):
        style = win32con.WS_POPUP | win32con.WS_CAPTION
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (int(w / 3), 300, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect, style, title='SimpleWindow')
        #win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        #self.addCardView(SortCardView(self))
        if self.type_ == 'HOT':
            self.addCardView(HotCardView(self))
            self.zsCardView = ZSCardView(self)
        elif self.type_ == 'ZT_GN':
            self.addCardView(THS_ZTCardView(self))
            self.addCardView(Cls_ZTCardView(self))

    def changeCardView(self):
        scode = f'{self.curCode :06d}' if type(self.curCode) == int else self.curCode
        if scode and scode[0 : 2] == '88':
            return
        super().changeCardView()

    def getCurCardView(self):
        scode = f'{self.curCode :06d}' if type(self.curCode) == int else self.curCode
        if scode and scode[0 : 2] == '88' and self.zsCardView:
            return self.zsCardView
        return super().getCurCardView()

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.curCode = code
        scode = f'{code :06d}' if type(code) == int else code
        if scode[0 : 2] == '88' and self.zsCardView:
            self.zsCardView.updateCode(code)
        else:
            for cv in self.cardViews:
                cc =  getattr(cv, 'updateCode')
                if cc: cc(code)
        cv = self.getCurCardView()
        title = cv.getWindowTitle()
        if title != None:
            win32gui.SetWindowText(self.hwnd, title)
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

    # param selDay yyyy-mm-dd or int 
    def changeSelectDay(self, selDay):
        if not selDay:
            selDay = 0
        if type(selDay) == str:
            selDay = selDay.replace('-', '')
            selDay = int(selDay)
        if self.selectDay == selDay:
            return
        self.selectDay = selDay
        for cv in self.cardViews:
            cc =  getattr(cv, 'updateSelectDay', None)
            if cc: cc(selDay)
        if self.zsCardView:
            self.zsCardView.updateSelectDay(selDay)
        if self.hwnd:
            win32gui.InvalidateRect(self.hwnd, None, True)

#----------------------------------------
class ListView(CardView):
    thread = None
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.ROW_HEIGHT = 18
        self.selIdx = -1
        self.pageIdx = 0
        self.data = None
        if not ListView.thread:
            ListView.thread = base_win.Thread()
            ListView.thread.start()

    def getColumnNum(self):
        return 1
    
    def getColumnWidth(self):
        n = self.getColumnNum()
        w = win32gui.GetClientRect(self.hwnd)[2]
        return w // n

    def getRowNum(self):
        rect = win32gui.GetClientRect(self.hwnd)
        h = rect[3] - rect[1]
        return h // self.ROW_HEIGHT
    
    def getPageSize(self):
        return self.getRowNum() * self.getColumnNum()

    def getMaxPageNum(self):
        if not self.data:
            return 0
        return (len(self.data) + self.getPageSize() - 1) // self.getPageSize()

    def getItemRect(self, idx):
        pz = self.getPageSize()
        idx -= self.pageIdx * pz
        if idx < 0 or idx >= pz:
            return None
        c = idx // self.getRowNum()
        cw = self.getColumnWidth()
        sx, ex = c * cw, (c + 1) * cw
        sy = (idx % self.getRowNum()) * self.ROW_HEIGHT
        ey = sy + self.ROW_HEIGHT
        return (sx, sy + 2, ex, ey + 2)

    def getItemIdx(self, x, y):
        c = x // self.getColumnWidth()
        r = y // self.ROW_HEIGHT
        idx = c * self.getRowNum() + r
        idx += self.getPageSize() * self.pageIdx
        return idx

    def getVisibleRange(self):
        pz = self.getPageSize()
        start = pz * self.pageIdx
        end = (self.pageIdx + 1) * pz
        start = min(start, len(self.data) - 1)
        end = min(end, len(self.data) - 1)
        return start, end

    def openTHSCode(self, code):
        topWnd = win32gui.GetParent(self.hwnd)
        win32gui.SetForegroundWindow(topWnd)
        if type(code) == int:
            code = f'{code :06d}'
        pyautogui.typewrite(code, interval=0.05)
        pyautogui.press('enter')
        #win32gui.SetActiveWindow(self.hwnd)
        self.thread.addTask('AW', self.activeWindow)
    
    def activeWindow(self):
        time.sleep(1)
        win32gui.SetForegroundWindow(self.hwnd)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEWHEEL:
            wParam = (wParam >> 16) & 0xffff
            if wParam & 0x8000:
                wParam = wParam - 0xffff + 1
            if wParam > 0: # up
                self.pageIdx = max(self.pageIdx - 1, 0)
            else:
                self.pageIdx = min(self.pageIdx + 1, self.getMaxPageNum() - 1)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.selIdx = self.getItemIdx(x, y)
            win32gui.InvalidateRect(self.hwnd, None, True)
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            selIdx = self.getItemIdx(x, y)
            if not self.data or selIdx < 0 or selIdx >= len(self.data):
                return False
            code = self.data[selIdx]['code']
            self.openTHSCode(code)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_DOWN:
                if self.data and self.selIdx < len(self.data):
                    self.selIdx += 1
                    if self.selIdx > 0 and self.selIdx % self.getPageSize() == 0:
                        self.pageIdx += 1
                    win32gui.InvalidateRect(hwnd, None, True)
            elif wParam == win32con.VK_UP:
                if self.data and self.selIdx > 0:
                    self.selIdx -= 1
                    if self.selIdx > 0 and (self.selIdx + 1) % self.getPageSize() == 0:
                        self.pageIdx -= 1
                    win32gui.InvalidateRect(hwnd, None, True)
            elif wParam == win32con.VK_RETURN:
                if self.data and self.selIdx >= 0:
                    code = self.data[self.selIdx]['code']
                    self.openTHSCode(code)
            return True
        return False

#-------------小窗口（全热度）----------------------------------------------
class HotZHCardView(ListView):
    def __init__(self, hwnd) -> None:
        super().__init__(hwnd)
        self.codeInfos = {}
        qr = ths_orm.THS_GNTC.select()
        for q in qr:
            self.codeInfos[q.code] = {'name': q.name}
        self.thread = base_win.Thread()
        self.thread.start()
        self.timerThread = base_win.TimerThread()
        self.henxinUrl = henxin.HexinUrl()
        self.updateDataTime = 0

        self.curSelDay : int = 0
        self.maxHotDay : int = 0
        self.windowTitle = 'HotZH'
        self.timerThread.addIntervalTask('LoadInterval', 4 * 60, self.updateData)

    def updateData(self, foreUpdate = False):
        lt = time.time()
        if not foreUpdate and lt - self.updateDataTime < 60:
            return
        self.updateDataTime = lt
        today = ths_iwencai.getTradeDaysInt()[-1] #ths_orm.THS_Hot.select(pw.fn.max(ths_orm.THS_Hot.day)).scalar()
        self.maxHotDay = today
        if self.curSelDay == 0:
            self.curSelDay = today
        self.setWindowTitle(self.curSelDay)
        datas = hot_utils.DynamicHotZH.instance().getHotsZH(self.curSelDay)
        self.data = [datas[k] for k in datas]

    def loadCodeInfoNet(self, code):
        try:
            if type(code) == int:
                code = f'{code :06d}'
            data = self.codeInfos.get(code, None)
            if not data:
                self.codeInfos[code] = data = {}
            url = self.henxinUrl.getFenShiUrl(code)
            obj = self.henxinUrl.loadUrlData(url)
            data['name'] = obj['name']
            dts = obj['line']
            if len(dts) != 0:
                curPrice = float(dts[-1].price)
                data['HX_curPrice'] = curPrice
                data['HX_prePrice'] = float(obj['pre'])
                pre = data['HX_prePrice']
                data['HX_zhangFu'] = (curPrice - pre) / pre * 100
                data['HX_updateTime'] = time.time()
            win32gui.InvalidateRect(self.hwnd, None, True)
        except Exception as e:
            print('[HotZHView.loadCodeInfoNet]', data, e)
            traceback.print_exc()

    def loadCodeInfoNative(self, code, setNull):
        if type(code) == int:
            code = f'{code :06d}'
        data = self.codeInfos.get(code, None)
        if not data:
            self.codeInfos[code] = data = {}
            data['name'] = ''
        if setNull:
            if 'HX_curPrice_Native' in data:
                del data['HX_curPrice_Native']
            if 'HX_prePrice_Native' in data:
                del data['HX_prePrice_Native']
            if 'HX_zhangFu_Native' in data:
                del data['HX_zhangFu_Native']
            return
        dt = datafile.T_DataModel(code)
        dt.loadLocalData(self.curSelDay)
        if not dt.data:
            return
        pre = dt.pre
        cur = dt.data[-1].price
        data['HX_curPrice_Native'] = cur / 100
        data['HX_prePrice_Native'] = pre / 100
        data['HX_zhangFu_Native'] = (cur - pre) / pre * 100
        win32gui.InvalidateRect(self.hwnd, None, True)

    def getCodeInfo(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        data = self.codeInfos.get(code, None)
        if not data:
            data = self.codeInfos[code] = {}
        if ('HX_updateTime' not in data) or (time.time() - data['HX_updateTime'] > 120): # 120 seconds
            data['HX_updateTime'] = time.time()
            if self.curSelDay == 0 or self.curSelDay == self.maxHotDay:
                self.thread.addTask(code + '-Native', self.loadCodeInfoNative, code, True)
                self.thread.addTask(code + '-Net', self.loadCodeInfoNet, code)
            else:
                self.thread.addTask(code + '-Native', self.loadCodeInfoNative, code, False)
                self.thread.addTask(code + '-Net', self.loadCodeInfoNet, code)
            return data
        return data

    def drawItem(self, hdc, data, idx):
        rect = self.getItemRect(idx)
        if not rect:
            return
        if self.selIdx == idx:
            base_win.Drawer.instance().fillRect(hdc, rect, 0x202020)
        code = f"{data['code'] :06d}"
        info = self.getCodeInfo(code)
        name = ''
        zf, nativeZF = '', ''
        if info:
            name = info.get('name', '')
            zf = info.get('HX_zhangFu', None)
            if zf != None:
                zf = f'{zf :.2f}% '
            nativeZF = info.get('HX_zhangFu_Native', None)
            if nativeZF != None:
                nativeZF = f'{nativeZF :.2f}% '
                zf = nativeZF
        txt = f"{data['zhHotOrder']:>3d} {name}"
        win32gui.SetTextColor(hdc, 0xdddddd)
        win32gui.DrawText(hdc, txt, len(txt), rect, win32con.DT_LEFT)
        #if nativeZF:
        #    color = 0x00ff00 if  '-' in nativeZF else 0x0000ff
        #    win32gui.SetTextColor(hdc, color)
        #    rc2 = list(rect)
        #    rc2[2] = 145
        #    win32gui.DrawText(hdc, nativeZF, len(nativeZF), tuple(rc2), win32con.DT_RIGHT)
        if zf:
            color = 0x00ff00 if  '-' in zf else 0x0000ff
            win32gui.SetTextColor(hdc, color)
            win32gui.DrawText(hdc, zf, len(zf), rect, win32con.DT_RIGHT)
        

    def onDraw(self, hdc):
        self.updateData()
        if not self.data:
            return
        rect = win32gui.GetClientRect(self.hwnd)
        vr = self.getVisibleRange()
        for i in range(*vr):
            self.drawItem(hdc, self.data[i], i)

        for i in range(1, self.getColumnNum()):
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            x = i * self.getColumnWidth()
            win32gui.MoveToEx(hdc, x, 0)
            win32gui.LineTo(hdc, x, rect[3])
            win32gui.DeleteObject(ps)

    def getWindowTitle(self):
        return self.windowTitle

    def onDayChanged(self, target, evt):
        if evt.name != 'Select':
            return
        selDay = evt.day
        if selDay > self.maxHotDay:
            return
        if self.curSelDay == selDay:
            return
        qr = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.name)
        self.codeInfos.clear()
        for q in qr:
            self.codeInfos[q.code] = {'name': q.name}
        self.curSelDay = selDay
        self.selIdx = -1
        self.pageIdx = 0
        self.setWindowTitle(selDay)
        self.updateData(True)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def setWindowTitle(self, day : int):
        tradeDays = ths_iwencai.getTradeDaysInt()
        bef = 0
        for i in range(len(tradeDays) - 1, 0, -1):
            if day < tradeDays[i]:
                bef += 1
            else:
                break
        if bef == 0:
            self.windowTitle = f'HotZH {day // 100 % 100 :02d}-{day % 100: 02d} 今日'
        else:
            self.windowTitle = f'HotZH {day // 100 % 100 :02d}-{day % 100: 02d} {bef}天前'
        win32gui.SetWindowText(self.hwnd, self.windowTitle)

class SimpleHotZHWindow(CardWindow):
    def __init__(self) -> None:
        super().__init__((170, 310), (80, 30))
        self.maxMode = True #  是否是最大化的窗口

    def createWindow(self, parentWnd):
        style = win32con.WS_POPUP | win32con.WS_CAPTION
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (w - self.MAX_SIZE[0], 300, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect, style, title='HotZH')
        #win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        self.addCardView(HotZHCardView(self))
        #self.addCardView(KPL_AllCardView(self))

    def onDraw(self, hdc):
        super().onDraw(hdc)
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        bk = win32gui.GetStockObject(win32con.NULL_BRUSH)
        size = self.getClientSize()
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, 0, 0, size[0] - 1, size[1] - 1)
        win32gui.DeleteObject(ps)
        #win32gui.DeleteObject(bk)

    def onDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
        cv = self.getCurCardView()
        dc = getattr(cv, 'onDayChanged', None)
        if not dc:
            return
        dc(args, evt)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_CONTEXTMENU:
            if not getattr(self, 'DP', None):
                self.DP = base_win.DatePopupWindow()
                self.DP.destroyOnHide = False
                self.DP.createWindow(hwnd)
                self.DP.addListener(self.onDayChanged, 'DatePicker')
            if win32gui.IsWindowVisible(self.DP.hwnd):
                self.DP.setVisible(False)
            else:
                rc = win32gui.GetWindowRect(hwnd)
                self.DP.show(x = rc[0] + 8, y = rc[1] + 30)
            return False
        return super().winProc(hwnd, msg, wParam, lParam)
    
class CodeBasicWindow(base_win.NoActivePopupWindow):
    def __init__(self) -> None:
        super().__init__()
        self.curCode = None
        self.data = None
        self.cacheData = {}
        self.css['bgColor'] = 0x050505
        self.css['borderColor'] = 0x22dddd
        self.css['enableBorder'] = True
        self.wbData = None
        self.MAX_SIZE = (350, 65)
        self.MIN_SIZE = (60, 30)
        self.maxMode = True
        self.inputs = ''
        self.detailWin = None
        base_win.ThreadPool.instance().start()

    def show(self, x, y):
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE) #  | win32con.SWP_NOACTIVATE
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW) # SW_SHOWNOACTIVATE

    def createWindow(self, parentWnd):
        w = win32api.GetSystemMetrics(0) # desktop width
        rect = (w - self.MAX_SIZE[0] - 100, 200, *self.MAX_SIZE)
        super().createWindow(parentWnd, rect)

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        LW, LH = W - 110, H
        PD = 10
        LR = 3
        rc = (LR, 2, W - LR, 18)
        if self.data:
            cs = f'{self.data["name"]}  {self.data["code"]}'
        else:
            cs = self.curCode
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14, weight=1000))
        self.drawer.fillRect(hdc, rc, 0x101010)
        self.drawer.drawText(hdc, cs, rc, 0x00D7FF)
        
        if not self.data or not self.curCode or self.curCode[0] == '8':
            return
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14, weight=1000))
        y1, y2 = 22, 45
        rc = (LR, y1, LW // 2 - PD, y1 + 20)
        v = int(self.data.get('ltsz', 0) / 100000000) #亿 # 流通市值
        cs1 =  f'{v :d} 亿'
        self.drawer.drawText(hdc, '流通值', rc, 0xcccccc, align=win32con.DT_LEFT)
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)
        rc = (LR, y2, LW // 2 - PD, y2 + 20)
        v = int(self.data.get('zsz', 0) / 100000000) #亿 总市值
        cs1 =  f'{v :d} 亿'
        self.drawer.drawText(hdc, '总市值', rc, 0xcccccc, align=win32con.DT_LEFT)
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)

        rc = (LW // 2 + PD, y1, LW - LR, y1 + 20)
        self.drawer.drawText(hdc, '市盈_静', rc, 0xcccccc, align=win32con.DT_LEFT)
        v = self.data['pe']
        if v == None:
            cs1 = '--'
        else:
            cs1 = f'{int(v)}'
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)
        rc = (LW // 2 + PD, y2, LW - LR, y2 + 20)
        self.drawer.drawText(hdc, '市盈_TTM', rc, 0xcccccc, align=win32con.DT_LEFT)
        v = self.data["peTTM"]
        if v == None:
            cs1 = '--'
        else:
            cs1 = f'{int(v)}'
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)

        x = LW + 20
        y = 22
        self.drawer.drawText(hdc, '委买', (x, y + 22, x + 30, y + 22 + 20), 0xcccccc, align = win32con.DT_LEFT)
        self.drawer.drawText(hdc, '委卖', (x, y, x + 30, y + 20), 0xcccccc, align = win32con.DT_LEFT)
        # draw 委比
        wb = self.wbData
        if not wb:
            return
        if 'sell' in self.wbData:
            bi = self.wbData['sell']
            if bi >= 10000:
                b = f'{bi / 10000 :.1f}亿'
            else:
                b = f'{bi}万'
            self.drawer.drawText(hdc, b, (x, y, W - 5, y + 20), 0x00aa00, align = win32con.DT_RIGHT)
        if 'buy' in self.wbData:
            bi = self.wbData['buy']
            if bi >= 10000:
                b = f'{bi / 10000 :.1f}亿'
            else:
                b = f'{bi}万'
            self.drawer.drawText(hdc, b, (x, y + 22, W - 5, y + 22 + 20), 0x2222aa, align = win32con.DT_RIGHT)

    def onDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
    
    def loadCodeBasic(self, code):
        #url = cls.ClsUrl()
        #data = url.loadBasic(code)
        #self.cacheData[code] = data
        #self._useCacheData(code)
        if code[0 : 2] == '88':
            obj = ths_orm.THS_ZS.get_or_none(ths_orm.THS_ZS.code == code)
            if obj: self.data = obj.__data__
        else:
            obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
            if obj: self.data = obj.__data__
        self.invalidWindow()

    def _useCacheData(self, code):
        if code != self.curCode or code not in self.cacheData:
            return
        self.data = self.cacheData[code]
        self.invalidWindow()
        
    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        scode = f'{code :06d}' if type(code) == int else code
        self.curCode = scode
        self.data = None
        self.wbData = None
        if len(scode) != 6 or (code[0] not in ('0', '3', '6', '8')):
            self.invalidWindow()
            return
        #if scode in self.cacheData:
        #    self._useCacheData(scode)
        #else:
        #    base_win.ThreadPool.instance().addTask(scode, self.loadCodeBasic, scode)
        self.loadCodeBasic(scode)

    def getWindowState(self):
        rc = win32gui.GetWindowRect(self.hwnd)
        return {'pos': (rc[0], rc[1])}
    
    def setWindowState(self, state):
        if not state:
            return
        x, y = state['pos']
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)

    def updateWeiBi(self, newWb):
        oldWb = self.wbData
        # check changed
        if not oldWb and not newWb:
            return
        if not newWb:
            return
        if not newWb.get('code', None):
            return
        # code changed ?
        changed = newWb['code'] != self.curCode
        if changed:
            self.changeCode(newWb['code'])
        self.wbData = newWb
        self.invalidWindow()

    def onOpenKLine(self):
        if self.curCode and self.curCode[0 : 2] == '88':
            data = {'code': self.curCode, 'day': None}
            kline_utils.openInCurWindow(None, data)
            return
        if self.data and 'code' in self.data and self.data['code']:
            data = {'code': self.data['code'], 'day': None}
            kline_utils.openInCurWindow(None, data)

    class DetailWindow(base_win.NoActivePopupWindow):
        def __init__(self) -> None:
            super().__init__()
            self.css['bgColor'] = 0x0
            self.css['borderColor'] = 0xFFCC99
            self.destroyOnHide = False
            self.code = None
            self.data = None

        def formatMoney(self, val):
            if type(val) != float and type(val) != int:
                return '-'
            if abs(val) >= 100000000:
                return f'{int(val / 100000000)}亿'
            if abs(val) >= 10000:
                return f'{int(val / 10000)}万'
            return int(val)
        
        def formatYearMonth(self, val, year):
            val = str(val)
            if year:
                return val[0 : 4] + '年'
            return val[0 : 4] + '-' + val[4 : 6]

        def onDraw(self, hdc):
            if not self.data:
                return
            ITEM_H = 25
            COL_NUM = 4
            W, H = self.getClientSize()
            titleColor = 0xFFCC99
            self.drawer.fillRect(hdc, (1, 1, W-1, ITEM_H), 0x202020)
            V_CENTER = win32con.DT_VCENTER | win32con.DT_SINGLELINE
            VH_CENTER = V_CENTER | win32con.DT_CENTER
            self.drawer.drawText(hdc, '营业收入', (15, 0, W, ITEM_H), color = titleColor, align = VH_CENTER)
            y = ITEM_H
            self.drawer.fillRect(hdc, (1, ITEM_H, W-1, y + ITEM_H - 1), 0x202020)
            WC = W / COL_NUM

            for idx, it in enumerate(self.data['yysr']):
                sx = int(idx * WC)
                ex = int(sx + WC)
                self.drawer.drawText(hdc, self.formatYearMonth(it[0], True), (sx, y, ex, y + ITEM_H), color = titleColor, align = VH_CENTER)
                self.drawer.drawText(hdc, self.formatMoney(it[1]), (sx, y + ITEM_H, ex, y + ITEM_H * 2), color = 0xaaaaaa, align = VH_CENTER)

            y += ITEM_H * 2
            self.drawer.fillRect(hdc, (1, y, W-1, y + ITEM_H), 0x202020)
            self.drawer.drawText(hdc, '净利润', (15, y, W, y + ITEM_H), color = titleColor, align = VH_CENTER)
            y += ITEM_H
            self.drawer.fillRect(hdc, (1, y, W-1, y + ITEM_H - 1), 0x202020)
            for idx, it in enumerate(self.data['jrl']):
                sx = int(idx * WC)
                ex = int(sx + WC)
                self.drawer.drawText(hdc, self.formatYearMonth(it[0], True), (sx, y, ex, y + ITEM_H), color = titleColor, align = VH_CENTER)
                self.drawer.drawText(hdc, self.formatMoney(it[1]), (sx, y + ITEM_H, ex, y + ITEM_H * 2), color = 0xaaaaaa, align = VH_CENTER)

            y += ITEM_H * 2
            self.drawer.fillRect(hdc, (1, y, W-1, y + ITEM_H), 0x202020)
            self.drawer.drawText(hdc, '净利润', (15, y, W, y + ITEM_H), color = titleColor, align = VH_CENTER)
            y += ITEM_H
            self.drawer.fillRect(hdc, (1, y, W-1, y + ITEM_H - 1), 0x202020)
            for idx, it in enumerate(self.data['jrl_2']):
                sx = int(idx * WC)
                ex = int(sx + WC)
                self.drawer.drawText(hdc, self.formatYearMonth(it[0], False), (sx, y, ex, y + ITEM_H), color = titleColor, align = VH_CENTER)
                self.drawer.drawText(hdc, self.formatMoney(it[1]), (sx, y + ITEM_H, ex, y + ITEM_H * 2), color = 0xaaaaaa, align = VH_CENTER)

        def loadData(self, code):
            if self.code == code:
                return
            obj = ths_orm.THS_CodesInfo.get_or_none(code = code)
            if not obj:
                self.data = None
            else:
                self.data = obj.__data__
                self.data['jrl'] = json.loads(self.data['jrl']) if self.data['jrl'] else []
                self.data['jrl_2'] = json.loads(self.data['jrl_2']) if self.data['jrl_2'] else []
                self.data['yysr'] = json.loads(self.data['yysr']) if self.data['yysr'] else []
            self.invalidWindow()

    def onOpenDetail(self):
        if not self.curCode or self.curCode[0] not in ('0', '3', '6'):
            return
        if self.curCode[0 : 3] == '399':
            return
        if not self.detailWin:
            self.detailWin = self.DetailWindow()
            self.detailWin.createWindow(self.hwnd, (0, 0, 300, 235))
        self.detailWin.loadData(self.curCode)
        self.detailWin.show(*win32gui.GetCursorPos())
        self.detailWin.msgLoop()

    def onChar(self, char):
        if char >= ord('0') and char <= ord('9'):
            self.inputs += chr(char)
        elif char == 13: # enter
            self.changeCode(self.inputs)
            self.inputs = ''
        else:
            self.inputs = ''

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCHITTEST:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            cx, cy = win32gui.ScreenToClient(self.hwnd, (x, y))
            if cy <= 20:
                return win32con.HTCAPTION
            return win32con.HTCLIENT
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            self.onOpenKLine()
            return True
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_RBUTTONDOWN:
            self.onOpenDetail()
            return True
        if msg == win32con.WM_CHAR:
            self.onChar(wParam)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class BkGnWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x050505
        self.css['borderColor'] = 0x22dddd
        self.css['enableBorder'] = True
        self.MAX_SIZE = (950, 70)
        self.MIN_SIZE = (60, 30)
        self.TITLE_HEIGHT = 15
        self.maxMode = True
        self.view = bkgn_view.BkGnView()

    def changeCode(self, code):
        self.view.changeCode(code)

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP, className='STATIC', title=''):
        if not rect:
            sz =  self.MAX_SIZE if self.maxMode else self.MIN_SIZE
            rect = (0, 0, *sz)
        super().createWindow(parentWnd, rect, style, className, title)
        self.view.hwnd = self.hwnd

    def getWindowState(self):
        rc = win32gui.GetWindowRect(self.hwnd)
        rs = {'maxMode': self.maxMode, 'pos': (rc[0], rc[1])}
        return rs
    
    def setWindowState(self, state):
        if not state:
            return
        x, y = state['pos']
        self.maxMode = state['maxMode']
        if state['maxMode']:
            win32gui.SetWindowPos(self.hwnd, 0, x, y, *self.MAX_SIZE, win32con.SWP_NOZORDER)
        else:
            win32gui.SetWindowPos(self.hwnd, 0, x, y, *self.MIN_SIZE, win32con.SWP_NOZORDER)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCHITTEST:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            cx, cy = win32gui.ScreenToClient(self.hwnd, (x, y))
            if cy <= self.TITLE_HEIGHT and cx <= 15:
                return win32con.HTCAPTION
            return win32con.HTCLIENT
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            self.maxMode = not self.maxMode
            if win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE) & win32con.WS_CHILD:
                return True
            if self.maxMode:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MAX_SIZE, win32con.SWP_NOMOVE | win32con.SWP_NOZORDER) # win32con.HWND_TOP
            else:
                win32gui.SetWindowPos(self.hwnd, 0, 0, 0, *self.MIN_SIZE, win32con.SWP_NOMOVE| win32con.SWP_NOZORDER)
            return True
        elif msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.view.onClick(x, y)
            return True
        elif msg == win32con.WM_MBUTTONUP:
            self.view.onShowSettings()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
    def onDraw(self, hdc):
        W, H = self.getClientSize()
        self.drawer.fillRect(hdc, (2, 2, 10, self.TITLE_HEIGHT), 0x0A550A)
        self.view.onDrawRect(hdc, (0, 0, W, H))

    def setVisible(self, visible : bool):
        if not win32gui.IsWindow(self.hwnd):
            return
        if visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            
if __name__ == '__main__':
    #win = BkGnWindow()
    #win.createWindow(None)
    #win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    #win.changeCode('688800')
    #win.changeLastDay(20250102)
    #win32gui.PumpMessages()

    # win = CodeBasicWindow()
    # win.createWindow(None)
    # win.changeCode('001298')
    # win.show(300, 500)
    # win32gui.PumpMessages()

    import ths_win
    thsWin = ths_win.ThsWindow()
    thsWin.init()
    win = SimpleWindow('HOT')
    win.createWindow(thsWin.mainHwnd)
    win.changeCode('603716')
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()