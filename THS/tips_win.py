from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, threading, copy
import sys, pyautogui
import peewee as pw
import types
sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import datafile
from THS import hot_utils
from Download import henxin, cls
from Common import base_win, ext_win, dialog, richeditor
from orm import tck_orm, ths_orm, tck_def_orm, cls_orm

#-----------------------------------------------------------
class ThsSortQuery:
    lhbDB = None

    def __init__(self):
        path = sys.argv[0]
        path = path[0 : path.index('GP') ]
        if not ThsSortQuery.lhbDB:
            ThsSortQuery.lhbDB = pw.SqliteDatabase(f'{path}GP/db/LHB.db')
        
    def getPMTag(self, v):
        if (v < 0.2): return '优秀'
        if (v < 0.4): return '良好'
        if (v < 0.6): return '一般'
        if (v < 0.8): return '较差'
        return '垃圾'

    def getLhbInfo(self, code):
        cc = self.lhbDB.cursor()
        cc.execute('select count(*) from tdxlhb where code = "' + code + '" ')
        data = cc.fetchone()
        count = data[0]
        cc.close()
        txt = f'龙虎榜 {count}次'
        return txt
    
    def getMaxHotInfo(self, code):
        code = int(code)
        maxHotZH = ths_orm.THS_HotZH.select(pw.fn.min(ths_orm.THS_HotZH.zhHotOrder), ths_orm.THS_HotZH.day).where(ths_orm.THS_HotZH.code == code).tuples()
        maxHot = ths_orm.THS_Hot.select(pw.fn.min(ths_orm.THS_Hot.hotOrder), ths_orm.THS_Hot.day).where(ths_orm.THS_Hot.code == code).tuples()
        info = ''
        for d in maxHotZH:
            if d[0]:
                info = f'最高热度综合排名: {d[0] :> 3d}  {d[1] // 10000}.{d[1] // 100 % 100:02d}.{d[1]%100:02d}'
            break
        for d in maxHot:
            if d[0]:
                info += f'\n    最高热度排名: {d[0] :> 3d}  {d[1] // 10000}.{d[1] // 100 % 100:02d}.{d[1]%100:02d}'
            break
        return info

    def getCodeInfo_THS(self, code):
        code = int(code)
        code = "%06d" % code
        gdInfo = ths_orm.THS_Top10_LTGD.select().where(ths_orm.THS_Top10_LTGD.code == code).order_by(ths_orm.THS_Top10_LTGD.day.desc())
        jgcgInfo = ths_orm.THS_JGCG.select().where(ths_orm.THS_JGCG.code == code).order_by(ths_orm.THS_JGCG.day_sort.desc())
        hydbInfo = ths_orm.THS_HYDB.select().where(ths_orm.THS_HYDB.code == code).order_by(ths_orm.THS_HYDB.day.desc())

        name = ''
        rate = '--'
        jgNum = '--'
        for jgcg in jgcgInfo:
            jgNum = jgcg.jjsl
            rate = int(jgcg.rate) if jgcg.rate else 0
            break
        jg = f"机构 {jgNum}家, 持仓{rate}%"

        for gd in gdInfo:
            rate = int(gd.rate) if gd.rate else 0
            jg += f'   前十流通股东{rate}%'
            break

        hy2, hy3 = '', ''
        hyName = ''
        gntc = ths_orm.THS_GNTC.get_or_none(code = code)
        if gntc:
            hyName = gntc.hy
            name = gntc.name
        for m in hydbInfo:
            if m.hydj == '三级' and not hy3:
                hy3 = f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
            elif m.hydj == '二级' and not hy2:
                hy2 = f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
        txt = hyName + '\n' + jg + '\n' + hy2 + hy3
        # 龙虎榜信息
        txt += self.getLhbInfo(code)
        txt += '\n' + self.getMaxHotInfo(code)
        return {'info': txt, 'code': code, 'name': name}

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

#-------------小窗口----------------------------------------------
class SortCardView(CardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.query = ThsSortQuery()
        self.sortData = None
        self.selectDay = 0

    def updateSelectDay(self, selDay):
        self.selectDay = selDay

    def updateCode(self, code):
        if type(code) == int:
            code = f'{code :06d}'
        # load sort data
        self.zsData = None
        self.sortData = self.query.getCodeInfo_THS(code)
        win32gui.SetWindowText(self.hwnd, f'{self.sortData["code"]} {self.sortData["name"]}')

    def onDraw(self, hdc):
        if not self.sortData:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        lines = self.sortData['info'].split('\n')
        rect = win32gui.GetClientRect(self.hwnd)
        for i, line in enumerate(lines):
            H = 18
            y = i * H + 2
            win32gui.DrawText(hdc, line, len(line), (2, y, rect[2], y + H), win32con.DT_LEFT)

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
        rect = win32gui.GetClientRect(self.hwnd)
        if not self.hotData:
            win32gui.SetTextColor(hdc, 0xdddddd)
            win32gui.DrawText(hdc, '无Hot信息', -1, rect, win32con.DT_CENTER)
            return
        rr = win32gui.GetClientRect(self.hwnd)
        win32gui.SetTextColor(hdc, 0xdddddd)

        RH = rect[3] - rect[1]
        RW = rect[2] - rect[0]
        MAX_ROWS = RH // self.ROW_HEIGHT
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
            avgHotOrder = f"{hot['avgHotOrder'] :.1f}"
            avgHotOrder = avgHotOrder[0 : 3]
            avgHotVal = int(hot['avgHotValue'])
            #line = f"{day} {hot['minOrder'] :>3d}->{hot['maxOrder'] :<3d} {avgHotVal :>3d}万 {zhHotOrder}"
            line = f"{day}   {zhHotOrder}"
            idx = i - fromIdx
            col = idx // MAX_ROWS
            row = idx % MAX_ROWS
            y = row * self.ROW_HEIGHT
            x = col * COL_WIDTH
            rect = (x + 4, y, x + COL_WIDTH, y + self.ROW_HEIGHT)
            win32gui.DrawText(hdc, line, len(line), rect, win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
            self.hotsInfo[i - fromIdx] = {'data': hot, 'rect': rect}
        pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xaaccaa)
        win32gui.SelectObject(hdc, pen)
        win32gui.MoveToEx(hdc, RW // 2, 0)
        win32gui.LineTo(hdc, RW // 2, rr[3])
        self.drawTip(hdc)
        win32gui.DeleteObject(pen)

    def drawTip(self, hdc):
        tipRect = self.tipInfo['rect']
        if not tipRect:
            return
        hotDetail = self.tipInfo['detail']
        if not hotDetail:
            return
        bk = win32gui.CreateSolidBrush(0)
        ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
        win32gui.SelectObject(hdc, ps)
        win32gui.SelectObject(hdc, bk)
        win32gui.Rectangle(hdc, *tipRect)
        si1 = max(self.showStartIdx, 0)
        si2 = max(0, len(hotDetail) - 5)
        si = min(si1, si2)
        self.showStartIdx = si
        win32gui.SetTextColor(hdc, 0x3333CD)
        for i in range(si, len(hotDetail)):
            hot = hotDetail[i]
            txt = f" {hot['time'] // 100 :02d}:{hot['time'] % 100 :02d}  {hot['hotValue'] :>3d}万  {hot['hotOrder'] :>3d}"
            y = (i - si) * self.ROW_HEIGHT + 5
            rc = (tipRect[0], y, tipRect[2], y + self.ROW_HEIGHT)
            win32gui.DrawText(hdc, txt, len(txt), rc, win32con.DT_CENTER)
        rc = self.tipInfo['hotRect']
        win32gui.MoveToEx(hdc, rc[0], rc[3] - 2)
        win32gui.LineTo(hdc, rc[2], rc[3] - 2)
        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(ps)

    def updateCode(self, code):
        self.showStartIdx = 0
        self.resetTipInfo()
        for i in range(len(self.hotsInfo)):
            self.hotsInfo[i] = None
        if type(code) != int:
            code = int(code)
        self.code = code
        # load hot data
        qq = ths_orm.THS_Hot.select(ths_orm.THS_Hot.day, pw.fn.min(ths_orm.THS_Hot.hotOrder).alias('minOrder'), pw.fn.max(ths_orm.THS_Hot.hotOrder).alias('maxOrder')).where(ths_orm.THS_Hot.code == code).group_by(ths_orm.THS_Hot.day) #.order_by(orm.THS_Hot.day.desc())
        #print(qq.sql())
        self.hotData = [d for d in qq.dicts()]
        qq2 = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.day, ths_orm.THS_HotZH.zhHotOrder, ths_orm.THS_HotZH.avgHotOrder, ths_orm.THS_HotZH.avgHotValue).where(ths_orm.THS_HotZH.code == code)
        qdata = {}
        for d in qq2.tuples():
            qdata[d[0]] = d[1 : ]
        for d in self.hotData:
            day = d['day']
            if day in qdata:
                d['zhHotOrder'] = qdata[day][0]
                d['avgHotOrder'] = qdata[day][1]
                d['avgHotValue'] = qdata[day][2]
            else:
                d['zhHotOrder'] = 0
                d['avgHotOrder'] = 0
                d['avgHotValue'] = 0

        if self.hotData and len(self.hotData) > 0:
            last = self.hotData[-1]
            if last['zhHotOrder'] == 0:
                rd = hot_utils.calcHotZHOnDayCode(last['day'], code)
                if rd:
                    last['zhHotOrder'] = rd['zhHotOrder']
                    last['avgHotOrder'] = rd['avgHotOrder']
                    last['avgHotValue'] = rd['avgHotValue']
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
            self.showStartIdx = 0
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            if self.isInRect(x, y, self.tipInfo['rect']):
                self.resetTipInfo()
                win32gui.InvalidateRect(hwnd, None, True)
                return True
            for hot in self.hotsInfo:
                if hot and self.isInRect(x, y, hot['rect']):
                    if self.tipInfo['hotRect'] == hot['rect']:
                        self.resetTipInfo()
                    else:
                        self.setTip(hot)
                    win32gui.InvalidateRect(hwnd, None, True)
                    return True
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

class KPLCardView(CardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.kplZTData = None
        self.ROW_HEIGHT = 18
        self.selectDay = 0
        self.ormClazz = tck_orm.KPL_ZT
        self.emptyLine = '\n\n无开盘啦涨停信息'
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

class THS_ZTCardView(KPLCardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.ormClazz = tck_orm.THS_ZT
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
    
class Cls_ZTCardView(KPLCardView):
    def __init__(self, cardWindow):
        super().__init__(cardWindow)
        self.ormClazz = tck_orm.CLS_ZT
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
        maxHotDay = ths_orm.THS_Hot.select(pw.fn.max(ths_orm.THS_Hot.day)).scalar()
        maxHotZhDay = ths_orm.THS_HotZH.select(pw.fn.max(ths_orm.THS_HotZH.day)).scalar()
        self.maxHotDay = maxHotDay
        if self.curSelDay == 0 or self.curSelDay == maxHotDay or self.curSelDay == maxHotZhDay:
            if maxHotDay == maxHotZhDay:
                qr = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == maxHotZhDay).order_by(ths_orm.THS_HotZH.zhHotOrder.asc())
                self.data = [d.__data__ for d in qr]
            else:
                self.data = hot_utils.calcHotZHOnDay(maxHotDay)
        else:
            # is history 
            qr = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == self.curSelDay).order_by(ths_orm.THS_HotZH.zhHotOrder.asc())
            self.data = [d.__data__ for d in qr]

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
        dt = datafile.DataFile(code, datafile.DataFile.DT_DAY)
        dt.loadData(datafile.DataFile.FLAG_ALL)
        idx = dt.getItemIdx(self.curSelDay)
        if idx <= 0:
            return
        pre = dt.data[idx - 1].close
        cur = dt.data[idx].close
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
        if self.selIdx == idx:
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            win32gui.MoveToEx(hdc, rect[0], rect[3] - 2)
            win32gui.LineTo(hdc, rect[2], rect[3] - 2)
            win32gui.DeleteObject(ps)

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
        if selDay == self.maxHotDay:
            self.windowTitle = f'HotZH'
            win32gui.SetWindowText(self.hwnd, self.windowTitle)
        else:
            tradeDays = hot_utils.getTradeDaysByHot()
            bef = 0
            for i in range(len(tradeDays) - 1, 0, -1):
                if selDay < tradeDays[i]:
                    bef += 1
                else:
                    break
            self.windowTitle = f'HotZH   {selDay}   {bef}天前'
            win32gui.SetWindowText(self.hwnd, self.windowTitle)
        self.updateData(True)
        win32gui.InvalidateRect(self.hwnd, None, True)

class KPL_AllCardView(ListView):
    def __init__(self, hwnd):
        super().__init__(hwnd)
        self.windowTitle = 'KPL-ZT'
        self.curSelDay = 0
        day = tck_orm.KPL_ZT.select(pw.fn.max(tck_orm.KPL_ZT.day)).scalar()
        self.updateData(day)

    def getFont(self):
        fnt = getattr(self, '_font', None)
        if not fnt:
            a = win32gui.LOGFONT()
            a.lfHeight = 12
            a.lfFaceName = '宋体'
            self._font = fnt = win32gui.CreateFontIndirect(a)
        return fnt

    def getWindowTitle(self):
        if not self.curSelDay:
            return 'KPL-ZT'
        tradeDays = hot_utils.getTradeDaysByHot()
        bef = 0
        for i in range(len(tradeDays) - 1, 0, -1):
            if self.curSelDay < tradeDays[i]:
                bef += 1
            else:
                break
        self.windowTitle = f'KPL-ZT   {self.curSelDay}   {bef}天前'
        return self.windowTitle
    
    def updateData(self, day):
        if day == self.curSelDay:
            return
        if not day:
            day = tck_orm.KPL_ZT.select(pw.fn.max(tck_orm.KPL_ZT.day)).scalar()
        if not day:
            day = '0000-00-00'
        if type(day) == int:
            day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        self.curSelDay = int(day.replace('-', ''))
        qr = tck_orm.KPL_ZT.select().where(tck_orm.KPL_ZT.day == day)
        self.data = [d.__data__ for d in qr]
        self.pageIdx = 0
        self.selIdx = -1
   
    def drawItem(self, hdc, data, idx):
        rect = self.getItemRect(idx)
        if not rect:
            return
        win32gui.SetTextColor(hdc, 0xdddddd)
        name = data['name']
        nl = 0
        for n in name:
            nl += 1 if ord(n) < 256 else 2
        if nl < 8:
            name += ' ' * (8 - nl)
        nl = 0
        status = data["status"]
        if '连' in status:
            status = status.replace('连', '') + ' '
        elif len(status) >= 4: # x天y板
            status = status[0 : -1]
        txt = f'{name} {data["ztTime"]} {status} {data["ztReason"]}({data["ztNum"]})'
        win32gui.SelectObject(hdc, self.getFont())
        win32gui.DrawText(hdc, txt, len(txt), rect, win32con.DT_LEFT)
        if self.selIdx == idx:
            ps = win32gui.CreatePen(win32con.PS_SOLID, 1, 0x00ffff)
            win32gui.SelectObject(hdc, ps)
            win32gui.MoveToEx(hdc, rect[0], rect[3] - 2)
            win32gui.LineTo(hdc, rect[2], rect[3] - 2)
            win32gui.DeleteObject(ps)

    def onDraw(self, hdc):
        vr = self.getVisibleRange()
        if not vr:
            return
        for i in range(*vr):
            self.drawItem(hdc, self.data[i], i)

    def onDayChanged(self, target, evt):
        selDay = evt.day
        if selDay == self.curSelDay:
            return
        self.updateData(selDay)
        win32gui.SetWindowText(self.hwnd, self.getWindowTitle())
        win32gui.InvalidateRect(self.hwnd, None, True)

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
        base_win.ThreadPool.instance().start()

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
        
        if not self.data:
            return
        self.drawer.use(hdc, self.drawer.getFont(fontSize = 14, weight=1000))
        y1 = 22
        rc = (LR, y1, LW // 2 - PD, y1 + 20)
        v = self.data["流通市值"] // 100000000 #亿
        cs1 =  f'{v :d} 亿'
        self.drawer.drawText(hdc, '流通值', rc, 0xcccccc, align=win32con.DT_LEFT)
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)
        rc = (LW // 2 + PD, y1, LW - LR, y1 + 20)
        v = self.data["总市值"] // 100000000 #亿
        cs1 =  f'{v :d} 亿'
        self.drawer.drawText(hdc, '总市值', rc, 0xcccccc, align=win32con.DT_LEFT)
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)

        y2 = 45
        rc = (LR, y2, LW // 2 - PD, y2 + 20)
        self.drawer.drawText(hdc, '市盈_静', rc, 0xcccccc, align=win32con.DT_LEFT)
        v = self.data['市盈率_静']
        if v == None:
            cs1 = '--'
        else:
            cs1 = '亏损' if v < 0 else f'{int(v)}'
        self.drawer.drawText(hdc, cs1, rc, 0xF4E202, align=win32con.DT_RIGHT)
        rc = (LW // 2 + PD, y2, LW - LR, y2 + 20)
        self.drawer.drawText(hdc, '市盈_TTM', rc, 0xcccccc, align=win32con.DT_LEFT)
        v = self.data["市盈率_TTM"]
        if v == None:
            cs1 = '--'
        else:
            cs1 = '亏损' if v < 0 else f'{int(v)}'
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
        url = cls.ClsUrl()
        data = url.loadBasic(code)
        self.cacheData[code] = data
        self._useCacheData(code)

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
        if len(scode) != 6 or (code[0] not in ('0', '3', '6')):
            self.invalidWindow()
            return
        if scode in self.cacheData:
            self._useCacheData(scode)
        else:
            base_win.ThreadPool.instance().addTask(scode, self.loadCodeBasic, scode)

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
            from Tck import kline_utils
            if self.data and 'code' in self.data and self.data['code']:
                data = {'code': self.data['code'], 'day': None}
                kline_utils.openInCurWindow(self, data)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class RecordWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x606060
        self.DEF_SIZE = (1280, 500)
        self.layout = base_win.GridLayout((160, '1fr'), ('1fr', ), (3, 0))
        self.editorWin = base_win.MutiEditor()
        self.editorWin.css['bgColor'] = 0xfafafa
        from Tck import swdt
        self.swdtWin = swdt.SwdtWindow()
        self.recObj = None
        self.swdtObj = None
        self.editForTag = 'Tips-Record' # 'Tips-GP-SWDT'

    def show(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)

    def createWindow(self, parentWnd, rect, style = None, className = 'STATIC', title='记'):
        SW, SH = win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        W, H = self.DEF_SIZE
        #rect = ((SW - W) // 2, (SH - H) // 2, *self.DEF_SIZE)
        super().createWindow(parentWnd, rect, style, className, title)
        self.swdtWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.swdtWin)
        self.layout.setContent(1, 0, self.editorWin)
        W, H = self.getClientSize()
        self.layout.resize(0, 0, W, H)
        self.initContent()
        self.rebindWinProc()

    def initContent(self):
        self.swdtObj, *_ = tck_def_orm.MyNote.get_or_create(tag = 'Tips-GP-SWDT')
        self.recObj, *_ = tck_def_orm.MyNote.get_or_create(tag = 'Tips-Record')
        self.editorWin.setText(self.recObj.info)
        self.swdtWin.loads(self.swdtObj.info)

    def onSave(self):
        if self.editForTag == 'Tips-Record':
            txt = self.editorWin.getText()
            self.recObj.info = txt
            self.recObj.save()
        elif self.editForTag == 'Tips-GP-SWDT':
            txt = self.editorWin.getText()
            self.swdtObj.info = txt
            self.swdtObj.save()
            self.swdtWin.loads(txt)
    
    def getKeyState(self, vk):
        return (win32api.GetKeyState(vk) & 0x80000000) != 0

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCLBUTTONDBLCLK:
            return True
        elif msg == win32con.WM_KEYDOWN:
            if wParam == ord('S') and self.getKeyState(win32con.VK_CONTROL):
                self.onSave()
        elif msg == win32con.WM_CLOSE:
            pp = win32gui.GetParent(self.hwnd)
            pp2 = win32gui.GetParent(pp)
            win32gui.SetForegroundWindow(pp2 or pp)
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            return 0
        return super().winProc(hwnd, msg, wParam, lParam)

    @staticmethod
    def swdt_winProc(swdtWin, hwnd, msg, wParam, lParam):
        self = swdtWin.pwin
        if msg == win32con.WM_KEYDOWN:
            if wParam == ord('S') and self.getKeyState(win32con.VK_CONTROL):
                self.onSave()
                return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            if self.editForTag == 'Tips-Record':
                self.editorWin.setText(self.swdtObj.info)
                self.editForTag = 'Tips-GP-SWDT'
            elif self.editForTag == 'Tips-GP-SWDT':
                self.editorWin.setText(self.recObj.info)
                self.editForTag = 'Tips-Record'
            self.editorWin.invalidWindow()
            return True
        old = swdtWin.old_win_proc
        return old(hwnd, msg, wParam, lParam)

    @staticmethod
    def edit_winProc(swdtWin, hwnd, msg, wParam, lParam):
        self = swdtWin.pwin
        if msg == win32con.WM_KEYDOWN:
            if wParam == ord('S') and self.getKeyState(win32con.VK_CONTROL):
                self.onSave()
                return True
        old = swdtWin.old_win_proc
        return old(hwnd, msg, wParam, lParam)
    
    def rebindWinProc(self):
        self.swdtWin.pwin = self
        self.swdtWin.old_win_proc = self.swdtWin.winProc
        self.swdtWin.winProc = types.MethodType(RecordWindow.swdt_winProc, self.swdtWin)
        self.editorWin.pwin = self
        self.editorWin.old_win_proc = self.editorWin.winProc
        self.editorWin.winProc = types.MethodType(RecordWindow.edit_winProc, self.editorWin)

class BkGnWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.TITLE_HEIGHT = 15
        self.DEF_COLOR = 0xa0a0a0
        self.HOT_DEF_COLOR = 0xff3399
        self.HOT_CLS_COLOR = 0x14698B
        self.css['bgColor'] = 0x050505
        self.css['borderColor'] = 0x22dddd
        self.css['enableBorder'] = True
        self.MAX_SIZE = (950, 70)
        self.MIN_SIZE = (60, 30)
        self.maxMode = True

        self.curCode = None
        self.hotGnObj = None
        self.thsGntc = None
        self.clsGntc = None
        self.defHotGns = []
        self.richRender = ext_win.RichTextRender(17)
        self.clsHotGns = []
        self.limitDaysNum = self._getLimitDaysNum()
        self.lastDay = None
        self.hotDaysRange = None

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP, className='STATIC', title=''):
        if not rect:
            sz =  self.MAX_SIZE if self.maxMode else self.MIN_SIZE
            rect = (0, 0, *sz)
        super().createWindow(parentWnd, rect, style, className, title)

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

    def onClick(self, x, y):
        sp = None
        for it in self.richRender.specs:
            rc = it.get('rect', None)
            if not rc: break
            if x >= rc[0] and x < rc[2] and y >= rc[1] and y < rc[3]:
                sp = it
                break
        if not sp or not sp['args']:
            return
        gnNum, gn = sp['args']
        if gnNum <= 0:
            return
        if not self.hotDaysRange:
            return
        tcView = self.HotTcView()
        #tcView.loadData(*self.hotDaysRange, gn)
        TRADE_DAYS_NUM = 20
        tcView.loadData_2(self.hotDaysRange[1], TRADE_DAYS_NUM, gn)
        tcView.createWindow(self.hwnd)
        tcView.show(*win32gui.GetCursorPos())
        tcView.msgLoop()

    class HotTcView(base_win.NoActivePopupWindow):
        def __init__(self) -> None:
            super().__init__()
            self.css['fontSize'] = 12
            self.css['bgColor'] = 0xfcfcfc
            self.datas = None
        
        def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP, className='STATIC', title=''):
            IW = 30
            LL = 10
            if self.datas:
                LL = len(self.datas)
            W = max(LL * IW, 200)
            rect = (0, 0, W, 200)
            super().createWindow(parentWnd, rect, style, className, title)

        def loadData_2(self, endDay, daysNum, tcName):
            tradeDays = []
            qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.day.distinct()).where(tck_orm.CLS_HotTc.day <= endDay).order_by(tck_orm.CLS_HotTc.day.desc()).tuples()
            for it in qr:
                tradeDays.append(it[0])
                if len(tradeDays) >= daysNum:
                    break
            fromDay = tradeDays[-1]
            self.loadData(fromDay, endDay, tcName)

        def loadData(self, fromDay, endDay, tcName):
            tradeDays = []
            qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.day.distinct()).where(tck_orm.CLS_HotTc.day >= fromDay, tck_orm.CLS_HotTc.day <= endDay).order_by(tck_orm.CLS_HotTc.day.asc()).tuples()
            for it in qr:
                tradeDays.append(it[0])
            qr = tck_orm.CLS_HotTc.select().where(tck_orm.CLS_HotTc.name == tcName, tck_orm.CLS_HotTc.day >= fromDay, tck_orm.CLS_HotTc.day <= endDay)
            model = []
            for it in qr:
                model.append(it)
            datas = []
            for i, d in enumerate(tradeDays):
                td = {'day': d, 'up': [], 'down': [], 'sumUpNum': 0, 'sumDownNum': 0}
                datas.append(td)
                for m in model:
                    if m.day == d:
                        if m.up: td['up'].append(m)
                        else: td['down'].append(m)
                td['sumUpNum'] = len(td['up'])
                td['sumDownNum'] = len(td['down'])
                if i > 0:
                    td['sumUpNum'] += datas[i - 1]['sumUpNum']
                    td['sumDownNum'] += datas[i - 1]['sumDownNum']
            self.datas = datas
        
        def onDraw(self, hdc):
            if not self.datas or len(self.datas) == 1:
                return
            MAX_NUM = max(self.datas[-1]['sumUpNum'], self.datas[-1]['sumDownNum'])
            STEP_VAL = 2 if MAX_NUM > 8 else 1
            STEP_NUM = max((MAX_NUM + STEP_VAL - 1) // STEP_VAL, 4)
            LEFT_X, RIGHT_X = 30, 20
            TOP_Y, BOTTOM_Y = 20, 30
            W, H = self.getClientSize()
            STEP_Y = (H - TOP_Y - BOTTOM_Y) / STEP_NUM
            STEP_X = (W - LEFT_X - RIGHT_X) / (len(self.datas) - 1)

            LINE_COLOR, TXT_COLOR, TXT_COLOR_HILIGHT  = 0xE2E2E2, 0x777777, 0xFF007F
            # vertical line
            preMonth = None
            for i in range(len(self.datas)):
                sx = int(LEFT_X + i * STEP_X)
                ey = H - BOTTOM_Y + 5
                self.drawer.drawLine(hdc, sx, TOP_Y, sx, ey, LINE_COLOR)
                day = self.datas[i]['day'][5 : ]
                month = day[0 : 2]
                c = TXT_COLOR_HILIGHT
                if preMonth == month:
                    day = day[3 : 5]
                    c = TXT_COLOR
                preMonth = month
                self.drawer.drawText(hdc, day.replace('-', '/'), (sx - 30, ey + 5, sx + 30, ey + 20), c)
            # horizontal line
            for i in range(STEP_NUM + 1):
                sy = int(H - BOTTOM_Y - STEP_Y * i)
                self.drawer.drawLine(hdc, LEFT_X - 5, sy, W - RIGHT_X, sy, LINE_COLOR)
                val = str(i * STEP_VAL)
                rc = (0, sy - 10, LEFT_X - 10, sy + 10)
                if STEP_NUM < 10 or i % 2 == 0:
                    self.drawer.drawText(hdc, val, rc, TXT_COLOR, win32con.DT_RIGHT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            
            RED, GREEN, GRAY = 0x3333ff, 0x33ff33, 0xCACACA
            # draw up datas
            for i, dt in enumerate(self.datas):
                sx = int(LEFT_X + i * STEP_X)
                sy = int(H - BOTTOM_Y - dt['sumUpNum'] / STEP_VAL * STEP_Y)
                self.drawer.fillRect(hdc, (sx - 3, sy - 3, sx + 3, sy + 3), RED)
                if i != len(self.datas) - 1: # not last
                    nsx = int(LEFT_X + (i + 1) * STEP_X)
                    nsy = int(H - BOTTOM_Y - self.datas[i + 1]['sumUpNum'] / STEP_VAL * STEP_Y)
                    if dt['sumUpNum'] != self.datas[i + 1]['sumUpNum']:
                        self.drawer.drawLine(hdc, sx, sy, nsx, nsy, RED, style = win32con.PS_SOLID, width = 2)
                    else:
                        self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GRAY, style = win32con.PS_DOT, width = 1)

                sy = int(H - BOTTOM_Y - dt['sumDownNum'] / STEP_VAL * STEP_Y)
                self.drawer.fillRect(hdc, (sx - 3, sy - 3, sx + 3, sy + 3), GREEN)
                if i != len(self.datas) - 1: # not last
                    nsx = int(LEFT_X + (i + 1) * STEP_X)
                    nsy = int(H - BOTTOM_Y - self.datas[i + 1]['sumDownNum'] / STEP_VAL * STEP_Y)
                    if dt['sumDownNum'] != self.datas[i + 1]['sumDownNum']:
                        self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GREEN, style = win32con.PS_SOLID, width = 2)
                    else:
                        self.drawer.drawLine(hdc, sx, sy, nsx, nsy, GRAY, style = win32con.PS_DOT, width = 1)

        # x, y is screen pos
        def show(self, x, y):
            rc = win32gui.GetWindowRect(self.hwnd)
            W, H = rc[2] - rc[0], rc[3] - rc[1]
            SW, SH = win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN) - 40
            if x + W > SW: x = SW - W
            if y + H > SH: y = SH - H
            super().show(x, y)

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
            self.onClick(x, y)
            return True
        elif msg == win32con.WM_MBUTTONUP:
            self.onShowSettings()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
    def _getLimitDaysNum(self):
        obj, _ = tck_def_orm.MySettings.get_or_create(mainKey = 'HotTc_N_Days')
        if not obj.val:
            obj.val = '5'
            obj.save()
        return int(obj.val)

    def onShowSettings(self):
        model = [{'title': '设置热点概念', 'name': 'hot'},
                 {'title': '设置热点概念-5日', 'name': 'HotTc_5', 'checked': self.limitDaysNum == 5},
                 {'title': '设置热点概念-10日', 'name': 'HotTc_10', 'checked': self.limitDaysNum == 10}
                ]
        menu = base_win.PopupMenu.create(self.hwnd, model)
        menu.addNamedListener('Select', self.onSettings)
        menu.show(*win32gui.GetCursorPos())

    def onSettings(self, evt, args):
        if evt.item['name'] == 'hot':
            dlg = dialog.MultiInputDialog()
            dlg.setText(self.hotGnObj.info or '')
            prc = win32gui.GetWindowRect(self.hwnd)
            def onInputEnd(evt, args):
                if not evt.ok:
                    return
                self.saveDefHotGn(evt.text)
                self._buildBkgn()
                self.invalidWindow()
            dlg.addNamedListener('InputEnd', onInputEnd)
            dlg.createWindow(win32gui.GetParent(self.hwnd), (prc[0], prc[1], 450, 200), title = '设置热点概念')
            dlg.showCenter()
        elif 'HotTc_' in evt.item['name']:
            ndays = int(evt.item['name'][len('HotTc_') : ])
            if self.limitDaysNum == ndays:
                return
            self.limitDaysNum = ndays
            obj, _ = tck_def_orm.MySettings.get_or_create(mainKey = 'HotTc_N_Days')
            obj.val = str(self.limitDaysNum)
            obj.save()
            self.changeLimitDaysNum()
    
    def onDraw(self, hdc):
        W, H = self.getClientSize()
        self.onDrawRect(hdc, (0, 0, W, H))
    
    def onDrawRect(self, hdc, rc):
        self.drawer.fillRect(hdc, (rc[0] + 2, rc[1] + 2, rc[0] + 10, rc[1] + self.TITLE_HEIGHT), 0x0A550A)
        self.richRender.draw(hdc, self.drawer, (rc[0] + 3, rc[1] + 2, rc[2] - 3, rc[3]))
    
    def setLimitDaysNum(self, daysNum):
        self.limitDaysNum = daysNum

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.lastDay = None
        scode = f'{code :06d}' if type(code) == int else code
        if scode[0 : 2] in ('sz', 'sh'):
            scode = scode[2 : ]
        self.curCode = scode
        # load code info
        self._loadDefHotGn()
        self._loadThsClsTcgn()
        self._loadClsHotGn(None)
        self._buildBkgn()
        self.invalidWindow()

    def changeLastDay(self, lastDay):
        if type(lastDay) == int:
            lastDay = str(lastDay)
        if type(lastDay) == str and len(lastDay) == 8:
            lastDay = lastDay[0 : 4] + '-' + lastDay[4 : 6] + '-' + lastDay[6 : 8]
        if self.lastDay == lastDay:
            return
        self.lastDay = lastDay
        self._loadClsHotGn(self.lastDay)
        self._buildBkgn()
        self.invalidWindow()

    def changeLimitDaysNum(self):
        self._loadClsHotGn(self.lastDay)
        self._buildBkgn()
        self.invalidWindow()

    def saveDefHotGn(self, txt):
        self.hotGnObj.info = txt or ''
        self.hotGnObj.save()

    def _loadDefHotGn(self):
        from orm import tck_def_orm
        qr = tck_def_orm.MyHotGn.select()
        self.hotGnObj = None
        self.defHotGns = []
        for obj in qr:
            self.hotGnObj = obj
            if obj.info:
                sx = obj.info.replace('\n', ' ').split(' ')
                for s in sx:
                    if s.strip(): self.defHotGns.append(s.strip())
            break
        if not self.hotGnObj:
            self.hotGnObj = tck_def_orm.MyHotGn.create(info = '')

    # lastDay = None(newest day) | int | str
    # return [(cls-name, num), ...]
    def _loadClsHotGn(self, lastDay):
        self.hotDaysRange = None
        qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.day.distinct()).order_by(tck_orm.CLS_HotTc.day.desc()).tuples()
        days = []
        for it in qr:
            if (lastDay is None) or (it[0] <= lastDay):
                days.append(it[0])
            if len(days) >= self.limitDaysNum: # 仅显示近N天的热点概念
                break
        if not days:
            self.hotDaysRange = None
            self.clsHotGns = []
            return
        fromDay = days[-1]
        endDay = days[0]
        self.hotDaysRange = (fromDay, endDay)
        rs = []
        qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.name, pw.fn.count()).where(tck_orm.CLS_HotTc.day >= fromDay, tck_orm.CLS_HotTc.day <= endDay, tck_orm.CLS_HotTc.up == True).group_by(tck_orm.CLS_HotTc.name).tuples()
        for it in qr:
            clsName, num = it
            rs.append((clsName.strip(), num))
        self.clsHotGns = rs

    def _loadThsClsTcgn(self):
        self.thsGntc = ths_orm.THS_GNTC.get_or_none(code = self.curCode) or ths_orm.THS_GNTC()
        self.clsGntc = cls_orm.CLS_GNTC.get_or_none(code = self.curCode) or cls_orm.CLS_GNTC()

    def _buildBkgn(self):
        self.richRender.specs.clear()
        defHotGns = self.defHotGns[ : ]
        clsHotGns = self.clsHotGns[ : ]
        hy1 = ''
        if self.thsGntc.hy_2_name: hy1 = self.thsGntc.hy_2_name + ';'
        if self.thsGntc.hy_3_name: hy1 += self.thsGntc.hy_3_name
        hys = self._buildBkInfos(hy1, self.clsGntc.hy, defHotGns, clsHotGns)
        self.richRender.addText(' 【', self.DEF_COLOR)
        for idx, h in enumerate(hys):
            if idx != 0:
                self.richRender.addText(' | ', self.DEF_COLOR)
            self.richRender.addText(h[1], h[2], args = (h[3], h[4]))
        self.richRender.addText('】 ', self.DEF_COLOR)
        
        lastGns = self._buildBkInfos(self.thsGntc.gn, self.clsGntc.gn, defHotGns, clsHotGns)
        lastGns.sort(key = lambda d: d[0])
        for i, h in enumerate(lastGns):
            self.richRender.addText(h[1], h[2], args = (h[3], h[4]))
            if i != len(lastGns) - 1:
                self.richRender.addText(' | ', self.DEF_COLOR)
        #for h in self.defHotGns:
        #    self.richRender.addText(h + ' ', 0x404040)

    # return (no, gn-name, color, type, num, org-gn-name)
    def _buildBkInfos(self, thsGn, clsGn, defHotGns, clsHotGns):
        thsGn = thsGn or ''
        clsGn = clsGn or '' 
        gns = [] # item of {gn: xx, type: xx, same:xx}
        gnsMap = {} # gn: obj
        for g in thsGn.split(';'):
            g = g.strip()
            if not g: 
                continue
            item = {'gn': g, 'type': 'THS'}
            gns.append(item)
            gnsMap[g] = item
        for g in clsGn.split(';'):
            g = g.strip()
            if not g: 
                continue
            if g in gnsMap:
                item = gnsMap[g]
                item['type'] = 'THS+CLS'
            else:
                item = {'gn': g, 'type': 'CLS'}
                gns.append(item)
        lastGns = []
        for item in gns:
            if item['type'] == 'THS':
                info = self._getTypeNameAndColor_THS(item['gn'], True, defHotGns)
            elif item['type'] == 'CLS':
                info = self._getTypeNameAndColor_CLS(item['gn'], True, clsHotGns)
                info = info[0], '#' + info[1], info[2], info[3]
            else: # THS+CLS
                info1 = self._getTypeNameAndColor_THS(item['gn'], True, defHotGns)
                info2 = self._getTypeNameAndColor_CLS(item['gn'], True, clsHotGns)
                no = min(info1[0], info2[0])
                color = info1[2] if no == info1[0] else info2[2]
                info = (no, '*' + info2[1], color, info2[3])
            info = *info, item['gn']
            lastGns.append(info)
        return lastGns

    def _getTypeNameAndColor_THS(self, bk, remove, defHotGns):
        idx = self._getDefHotIndex(bk, defHotGns)
        if idx >= 0:
            if remove: defHotGns.pop(idx)
            return 20, bk, self.HOT_DEF_COLOR, 0
        return 1000, bk, self.DEF_COLOR, 0
    
    def _getTypeNameAndColor_CLS(self, bk, remove, clsHotGns):
        idx = self._getClsHotIndex(bk, clsHotGns)
        if idx >= 0:
            clsName, num = clsHotGns[idx]
            if remove:
                clsHotGns.pop(idx)
            name = f'{bk}（{num}）'
            return 100 - num, name, self.HOT_CLS_COLOR, num
        return 2000, bk, self.DEF_COLOR, 0

    def _getDefHotIndex(self, bk, defHotGns):
        for i, h in enumerate(defHotGns):
            if h == bk: # h in bk or bk in h
                return i
        return -1

    def _getClsHotIndex(self, bk, clsHotGns):
        for i, it in enumerate(clsHotGns):
            clsName, num = it
            if bk == clsName:
                return i
        return -1
    
    def removeDefHotGn(self, hotGns : list, gn):
        for i, h in enumerate(hotGns):
            if h in gn:
                hotGns.pop(i)

        #return ('半导体', '鸿蒙概念', '低空经济', '消费电子')
    
    def setVisible(self, visible : bool):
        if not win32gui.IsWindow(self.hwnd):
            return
        if visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

class ToolBarWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['borderColor'] = 0x00ffff
        self.DEF_SIZE = (280, 25)
        self.MOVE_BOX_WIDTH = 20
        self.ITEM_WIDTH = 40
        from Tck import top_zt_net, top_bk, top_lhb, top_zt_lianban, top_real_zs, top_hots, top_xgc
        self.model = [
            {'title': '记', 'name': 'Record', 'class': RecordWindow, 'win': None, 'win-title': '笔记'},
            #{'title': '板块', 'name': 'BK', 'class': top_bk.Bk_Window, 'win': None, 'win-title': '板块概念'},
            #{'title': '涨停', 'name': 'ZT', 'class': top_zt_net.ZT_Window, 'win': None, 'win-title': '涨停'},
            #{'title': '天梯', 'name': 'BK', 'class': top_zt_lianban.ZT_Window, 'win': None, 'win-title': '连板天梯'},
            #{'title': '龙','name': 'LHB', 'class': top_lhb.LHB_Window, 'win': None, 'win-title': '龙虎榜'},
            #{'title': '速', 'name': 'SU', 'class': top_real_zs.ZS_Window, 'win': None, 'win-title': '涨速联动'},
            {'title': '热', 'name': 'SU', 'class': top_hots.Hots_Window, 'win': None, 'win-title': '热度'},
            {'title': '选', 'name': 'XG', 'class': top_xgc.XGC_Window, 'win': None, 'win-title': '选股'},
        ]

    def setVisible(self, visible : bool):
        if not win32gui.IsWindow(self.hwnd):
            return
        if visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def getWindowState(self):
        rc = win32gui.GetWindowRect(self.hwnd)
        return {'pos': (rc[0], rc[1])}

    def setWindowState(self, state):
        if not state:
            return
        x, y = state['pos']
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)

    @staticmethod
    def _wp(winObj, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_CLOSE:
            win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
            return True
        old = winObj.old_win_proc
        return old(hwnd, msg, wParam, lParam)
    
    def rebindWinProc(self, win):
        win.old_win_proc = win.winProc
        win.winProc = types.MethodType(ToolBarWindow._wp, win)

    def newWindow(self, item):
        if item['win']:
            return item['win']
        item['win'] = win = item['class']()
        win.css['paddings'] = (4, 4, 4, 4)
        sw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        sh = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        W, H = sw, 600
        rc = (0, sh - H - 35, W, H)
        win.createWindow(self.hwnd, rc, style = win32con.WS_POPUPWINDOW | win32con.WS_CAPTION | win32con.WS_MAXIMIZEBOX | win32con.WS_MINIMIZEBOX | win32con.WS_THICKFRAME, title = item['win-title'])
        self.rebindWinProc(win)
        win32gui.PostMessage(win.hwnd, win32con.WM_SIZE, 0, 0)
        return win

    def onClick(self, x, y):
        idx = x // self.ITEM_WIDTH
        if idx >= 0 and idx < len(self.model):
            item = self.model[idx]
            win = self.newWindow(item)
            if hasattr(win, 'show'):
                win.show()
            else:
                win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_NCHITTEST:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            cx, cy = win32gui.ScreenToClient(self.hwnd, (x, y))
            W, H = self.getClientSize()
            if cx >= W - self.MOVE_BOX_WIDTH:
                return win32con.HTCAPTION
            return win32con.HTCLIENT
        elif msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

    def createWindow(self, parentWnd, rect = None, style = None, className = 'STATIC', title = ''):
        style = win32con.WS_POPUP
        rect = (0, 0, *self.DEF_SIZE)
        super().createWindow(parentWnd, rect, style, className, title)

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        self.drawer.fillRect(hdc, (W - self.MOVE_BOX_WIDTH, 1, W - 1, H - 1), 0x202020)
        sx = 1
        for i in range(len(self.model)):
            item = self.model[i]
            color = 0x333333
            isx = sx + i * self.ITEM_WIDTH
            rc = [isx, 1, isx + self.ITEM_WIDTH, H - 1]
            self.drawer.fillRect(hdc, rc, color)
            self.drawer.drawRect(hdc, rc, 0x202020)
            self.drawer.drawText(hdc, item['title'], rc, 0xAAAA2f, win32con.DT_SINGLELINE | win32con.DT_VCENTER | win32con.DT_CENTER)

def test():
    pass

if __name__ == '__main__':
    #win = BkGnWindow()
    #win.createWindow(None)
    #win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    #win.changeCode('688800')
    #win.changeLastDay(20250102)
    #win32gui.PumpMessages()

    import ths_win
    thsWin = ths_win.ThsWindow()
    thsWin.init()
    rwin = ToolBarWindow()
    rwin.createWindow(thsWin.topHwnd)
    win32gui.ShowWindow(rwin.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()