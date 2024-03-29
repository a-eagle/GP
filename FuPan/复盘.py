import win32gui, win32con, sys, os, win32api

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win
import ddlr_detail, kpl_2, multi_kline, ddlr_struct, zs, tck, vol_pm, tcgn2

class FuPanMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('100%', ), (5, 0))
        self.childWin = []
        self.cardLayout = base_win.Cardayout()

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        gpInfos = [{'name': 'KPL', 'title': '市场情绪'},
            {'name': 'DDLR_STRUCT', 'title': '大单流入'},
            {'name': 'THS_ZS', 'title': '指数'}, 
            {'name': 'VOL_PM', 'title': '成交额排名'},
            {'name': 'TCK', 'title': '题材库'}, 
            {'name': 'TCGN', 'title': '题材梳理'}, 
            ]
        gp = base_win.GroupButton(gpInfos)
        gp.setSelGroup(0)
        gp.createWindow(self.hwnd, (0, 0, 80 * len(gpInfos), 30))
        gp.addListener(self.changeGroup, 'GroupButton')
        gpLy = base_win.AbsLayout()
        gpLy.setContent(0, 0, gp)
        self.layout.setContent(0, 0, gpLy)

        kplWin = kpl_2.KPL_MgrWindow()
        kplWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(kplWin)

        ddlrWin = ddlr_struct.DddlrStructWindow()
        ddlrWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(ddlrWin)

        zsWin = zs.ZSWindow()
        zsWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(zsWin)

        volPmWin = vol_pm.VolPMWindow()
        volPmWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(volPmWin)

        tckWin = tck.TCK_Window()
        tckWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(tckWin)

        tcgnWin = tcgn2.TCGN_Window()
        tcgnWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.cardLayout.addContent(tcgnWin)

        self.cardLayout.showCardByIdx(0)
        self.layout.setContent(1, 0, self.cardLayout)

    def changeGroup(self, evt, args):
        if evt.name != 'ClickSelect':
            return
        idx = evt.groupIdx
        self.cardLayout.showCardByIdx(idx)

if __name__ == '__main__':
    base_win.ThreadPool.start()
    fp = FuPanMgrWindow()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    fp.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()
