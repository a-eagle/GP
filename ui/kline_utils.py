import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, traceback

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from ui import timeline, kline_win, base_win
from THS import ths_win

def createKLineWindow(parent, rect = None, style = None):
    win = kline_win.KLineCodeWindow('default')
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    if not rect:
        BORDER = 7
        W, H = int(dw + BORDER * 2), int(dh * 0.92)
        x = -BORDER
        y = dh - H
        rect = (x, y, W, H)
    if not style:
        if parent:
            style = win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION
        else:
            style = win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW
    win.createWindow(parent, rect, style)
    win.klineWin.addNamedListener('DbClick', openKlineMinutes_Simple, win)
    return win

def openInCurWindow_Code(parent : base_win.BaseWindow, data):
    hwnd = parent.hwnd if parent else None
    win = createKLineWindow(hwnd)
    win.changeCode(data['code'])
    win.klineWin.marksMgr.setMarkDay(data.get('day', None))
    win.klineWin.makeVisible(-1)
    return win

def openInCurWindow_ZS(parent : base_win.BaseWindow, data):
    win = kline_win.KLineCodeWindow()
    win.addIndicator(kline_win.DayIndicator({}))
    win.addIndicator(kline_win.ThsZsPMIndicator({}))
    dw = win32api.GetSystemMetrics (win32con.SM_CXSCREEN)
    dh = win32api.GetSystemMetrics (win32con.SM_CYSCREEN) - 35
    W, H = int(dw * 1), int(dh * 0.8)
    x = (dw - W) // 2
    y = (dh - H) // 2
    win.createWindow(parent.hwnd, (0, y, W, H), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW | win32con.WS_CAPTION)
    win.changeCode(data['code'])
    win.klineWin.marksMgr.setMarkDay(data['day'])
    win.klineWin.addNamedListener('DbClick', openKlineMinutes_Simple, win)
    win.klineWin.makeVisible(-1)
    return win

def openInCurWindow(parent : base_win.BaseWindow, data):
    try:
        code = data['code']
        if code[0] == '8':
            return openInCurWindow_ZS(parent, data)
        else:
            return openInCurWindow_Code(parent, data)
    except Exception as e:
        traceback.print_exc()

def openKlineMinutes_Simple(evt, parent : base_win.BaseWindow):
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

if __name__ == '__main__':
    openInCurWindow_Code(None, {'code': '603011'})
    win32gui.PumpMessages()
    pass