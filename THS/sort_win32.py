import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
import sys
import orm
import peewee as pw

#-----------------------------------------------------------
class ThsSortQuery:
    lhbDB = None

    def __init__(self):
        path = sys.argv[0]
        path = path[0 : path.index('GP') ]
        if not ThsSortQuery.lhbDB:
            print('Load LHB db')
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

    def getCodeInfo_THS(self, code):
        code = int(code)
        code = "%06d" % code
        gdInfo = orm.THS_GD.get_or_none(orm.THS_GD.code == code)
        jgccInfo = orm.THS_JGCC.get_or_none(orm.THS_JGCC.code == code)
        hydbInfo = orm.THS_HYDB_2.select().where(orm.THS_HYDB_2.code == code).order_by(orm.THS_HYDB_2.hy).execute()

        name = ''
        zb = ''
        if not jgccInfo:
            zb = '--'
            jgNum = '--'
        else:
            jgNum = jgccInfo.orgNum1
            name = jgccInfo.name
            if not jgccInfo.totalRate1:
                zb = '--'
            elif jgccInfo.totalRate1 < 1:
                zb = '<1'
            else:
                zb = int(jgccInfo.totalRate1)
        jg = "机构 %s家, 持仓%s%%" % (jgNum, zb)

        if gdInfo:
            jg += f'   前十流通股东{int(gdInfo.ltgdTop10Rate)}%'
            name = gdInfo.name

        hy = ''
        hyName = ''
        for m in hydbInfo:
            hy += f'  {m.hydj} {m.zhpm} / {m.hysl} [{self.getPMTag(m.zhpm / m.hysl)}]\n'
            hyName = m.hy
            name = m.name
        
        line = code + ' ' + name
        txt = line + '\n' + hyName + '\n' + jg + '\n' + hy
        # 龙虎榜信息
        txt += self.getLhbInfo(code)
        
        return txt

#-----------------------------------------------------------
# 同行比较排名窗口信息
class SortInfoWindow:
    def __init__(self) -> None:
        self.wnd = None
        self.size = None  # 窗口大小 (w, h)
        self.maxMode = True #  是否是最大化的窗口
        self.curCode = None
        self.textInfo = ''
        self.query = ThsSortQuery()

    def createWindow(self, parentWnd):
        style = (0x00800000 | 0x10000000 | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION) & ~win32con.WS_SYSMENU
        w = win32api.GetSystemMetrics(0) # desktop width
        self.size = (280, 165)
        self.wnd = win32gui.CreateWindowEx(win32con.WS_EX_TOOLWINDOW, 'STATIC', '', style, int(w / 3), 300, *self.size, parentWnd, None, None, None)
        win32gui.SetWindowPos(self.wnd, win32con.HWND_TOP, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowLong(self.wnd, win32con.GWL_WNDPROC, sortInfoWinProc)
        win32gui.ShowWindow(self.wnd, win32con.SW_NORMAL)

    def changeCode(self, code):
        if (self.curCode == code) or (not code):
            return
        self.curCode = code
        self.textInfo = self.query.getCodeInfo_THS(self.curCode)
        if self.wnd and self.size:
            #win32gui.InvalidateRect(self.wnd, (0, 0, *self.size), True)
            #win32gui.UpdateWindow(self.wnd)
            win32gui.InvalidateRect(self.wnd, None, True)
            #win32gui.PostMessage(self.wnd, win32con.WM_PAINT)

    def onDraw(self):
        hwnd = self.wnd
        hdc, ps = win32gui.BeginPaint(hwnd)
        bk = win32gui.CreateSolidBrush(0x000000)
        win32gui.FillRect(hdc, win32gui.GetClientRect(hwnd), bk)
        pen = win32gui.CreatePen(win32con.PS_SOLID, 2, 0xff00ff)
        win32gui.SelectObject(hdc, pen)
        win32gui.SetBkMode(hdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(hdc, 0x0)

        a = win32gui.LOGFONT()
        a.lfHeight = 14
        a.lfFaceName = '新宋体'
        font = win32gui.CreateFontIndirect(a)
        win32gui.SelectObject(hdc, font)
        self.drawContent(hdc)
        win32gui.EndPaint(hwnd, ps)
        win32gui.DeleteObject(font)
        win32gui.DeleteObject(bk)
        win32gui.DeleteObject(pen)
    
    def drawContent(self, hdc):
        win32gui.SetTextColor(hdc, 0xdddddd)
        lines = self.textInfo.split('\n')
        for i, line in enumerate(lines):
            H = 18
            y = i * H + 2
            win32gui.DrawText(hdc, line, len(line), (2, y, self.size[0], y + H), 0)

    def hide(self):
        win32gui.ShowWindow(self.wnd, win32con.SW_HIDE)
    
    def show(self):
        if not win32gui.IsWindowVisible(self.wnd):
            win32gui.ShowWindow(self.wnd, win32con.SW_NORMAL)

def sortInfoWinProc(hwnd, msg, wParam, lParam):
    if msg == win32con.WM_PAINT:
        sortInfoWindow.onDraw()
    return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)

sortInfoWindow = SortInfoWindow()
#sortInfoWindow.createWindow(None)
#sortInfoWindow.changeCode('000977')
#win32gui.PumpMessages()
#------------------------------------------
