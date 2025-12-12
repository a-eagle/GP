import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, traceback

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui import timeline, kline_win, base_win, kline_indicator
from THS import ths_win

def createKLineWindow(parent = None, rect = None, style = None):
    win = kline_win.KLineCodeWindow()
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    if not rect:
        BORDER = 7
        W, H = int(dw + BORDER * 2), dh
        x = -BORDER
        y = dh - H
        rect = (x, y, W, H)
    if not style:
        if parent:
            style = win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION
        else:
            style = win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
    win.createWindow(parent, rect, style)
    win.klineWin.addNamedListener('DbClick', openTimeLineWindow, win)
    return win

def createKLineWindow_ZS(parent = None, rect = None, style = None):
    win = createKLineWindow(parent, rect, style)
    win.klineWin.indicators.clear()
    win.klineWin.addIndicator(win.klineWin.klineIndicator)
    win.klineWin.addIndicator(kline_indicator.AmountIndicator(win.klineWin, {'height': 60, 'margins': (10, 2)}))
    win.klineWin.addIndicator(kline_indicator.DayIndicator(win.klineWin))
    win.klineWin.addIndicator(kline_indicator.ScqxIndicator(win.klineWin))
    win.klineWin.addIndicator(kline_indicator.LsAmountIndicator(win.klineWin))
    win.klineWin.addIndicator(kline_indicator.ZsZdPmIndicator(win.klineWin))
    win.klineWin.addIndicator(kline_indicator.CLS_HotTcIndicator(win.klineWin))
    win.klineWin.addIndicator(kline_indicator.ZS_ZT_NumIndicator(win.klineWin))
    win.klineWin.calcIndicatorsRect()
    return win

def createKLineWindowByCode(code, parent = None, rect = None, style = None):
    if type(code) == int:
        code = f'{code :06d}'
    code = code.strip()
    if len(code) == 8 and code[0] == 's':
        code = code[2 : ]
    if code[0] in ('0', '3', '6'):
        return createKLineWindow(parent, rect, style)
    if code[0] == '8' or code[0 : 3] == 'cls':
        return createKLineWindow_ZS(parent, rect, style)
    return None

def openTimeLineWindow(evt, parent : base_win.BaseWindow):
    win = timeline.TimelinePanKouWindow()
    #rc = win32gui.GetWindowRect(parent.hwnd)
    #rc2 = (rc[0], rc[1], rc[2] - rc[0], rc[3] - rc[1])
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    w, h = max(800, int(SW * 0.6)), 600
    x, y = (SW - w) // 2, (SH - h) // 2
    rc2 = (x, y, w, h)
    hw = None
    if isinstance(parent, base_win.BaseWindow):
        hw = parent.hwnd
    else:
        hw = parent
    win.createWindow(hw, rc2, win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    day = evt.data.day
    win.load(evt.code, day)
    if isinstance(parent, kline_win.KLineCodeWindow):
        p : kline_win.KLineCodeWindow = parent
        zs = p.klineWin.refIndicator.model
        if zs:
            win.loadRef(zs.code)
    if evt.code[0 : 3] == 'cls':
        win.loadRef(evt.code)
    return win

def openInThsWindow(data):
    thsWin = ths_win.ThsWindow.ins()
    if not thsWin.topHwnd or not win32gui.IsWindow(thsWin.topHwnd):
        thsWin.topHwnd = None
        thsWin.init()
    if not thsWin.topHwnd:
        return
    win32gui.SetForegroundWindow(thsWin.topHwnd)
    time.sleep(0.5)
    pyautogui.typewrite(data['code'], 0.1)
    time.sleep(0.2)
    pyautogui.press('enter')

def openInCurWindow(parent, data):
    parent = parent.hwnd if isinstance(parent, base_win.BaseWindow) else parent
    win = createKLineWindowByCode(data['code'], parent)
    win.changeCode(data['code'])
    days = data.get('day', None)
    if isinstance(days, list):
        for d in days:
            win.klineWin.marksMgr.setMarkDay(d)
    else:
        win.klineWin.marksMgr.setMarkDay(days)
    win.klineWin.makeVisible(-1)
    return win

if __name__ == '__main__':
    openInCurWindow(None, {'code': 'cls80222'}) # 601086 cls80353
    win32gui.PumpMessages()
    pass