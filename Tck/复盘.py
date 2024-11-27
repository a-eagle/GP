import win32gui, win32con, sys, os, win32api

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win
import ddlr_detail, top_scqx, ddlr_struct, top_zs, top_zt_net
import top_vol_pm, top_cls_bk, top_hots, top_vol_lb, top_diary, top_dde, top_observe, top_hot_tc, top_lhb, top_bk, top_zt_lianban

class FuPanMgrWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('100%', ), (5, 0))
        self.childWin = []
        self.cardLayout = base_win.Cardayout()

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        gpInfos = [
            #{'name': 'KPL', 'title': '市场情绪', 'class': top_scqx.KPL_MgrWindow},
            #{'name': 'DDLR_STRUCT', 'title': '大单流入',  'class': ddlr_struct.DddlrStructWindow},
            #{'name': 'VOL_PM', 'title': '成交额排名',  'class': top_vol_pm.VolPMWindow},
            #{'name': 'VOL_LB', 'title': '量比',  'class': top_vol_lb.VolLBWindow},
            {'name': 'THS_ZS', 'title': '指数',  'class': top_zs.ZSWindow},
            #{'name': 'DDE', 'title': 'DDE',  'class': top_dde.DdeWindow},
            {'name': 'ZT', 'title': '涨停',  'class': top_zt_net.ZT_Window},
            {'name': 'HOTS', 'title': '热度',  'class': top_hots.Hots_Window},
            #{'name': 'HOTS', 'title': '板块',  'class': top_bk.Bk_Window},
            {'name': 'LHB', 'title': '龙虎榜',  'class': top_lhb.LHB_Window},
            {'name': 'LB-ZT', 'title': '连板',  'class': top_zt_lianban.ZT_Window},
            #{'name': 'TCGN', 'title': '题材梳理',  'class': tcgn2.TCGN_Window},
            #{'name': 'CLS_BK', 'title': '财联社板块',  'class': top_cls_bk.ClsBkWindow},
            #{'name': 'MY', 'title': '自选',  'class': top_observe.MyWindow},
            #{'name': 'HOTS_TC', 'title': '热度题材',  'class': top_hot_tc.HotTCWindow},
            #{'name': 'DIALY', 'title': '日记',  'class': top_diary.DailyWindow},
        ]
        gp = base_win.GroupButton(gpInfos)
        gp.setSelGroup(0)
        gp.createWindow(self.hwnd, (0, 0, 80 * len(gpInfos), 30))
        gp.addNamedListener('Select', self.changeGroup)
        gpLy = base_win.AbsLayout()
        gpLy.setContent(0, 0, gp)
        self.layout.setContent(0, 0, gpLy)

        for info in gpInfos:
            win = info['class']()
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            self.cardLayout.addContent(win)

        self.cardLayout.showCardByIdx(0)
        self.layout.setContent(1, 0, self.cardLayout)

    def changeGroup(self, evt, args):
        idx = evt.groupIdx
        self.cardLayout.showCardByIdx(idx)
        win = self.cardLayout.winsInfo[idx]['win']
        if hasattr(win, 'onShow'):
            win.onShow()

if __name__ == '__main__':
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    base_win.ThreadPool.instance().start()
    fp = FuPanMgrWindow()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    fp.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()
