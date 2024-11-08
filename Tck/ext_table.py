import os, json, sys, functools
import time, re
import win32gui, win32con, win32api

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Common import base_win, ext_win

class TimelineTableWindow(ext_win.EditTableWindow):
    def __init__(self) -> None:
        super().__init__()
        self.timelineHeaderXRange = None
        self.mouseX = None

    def getTimelineXRange(self):
        if self.timelineHeaderXRange:
            return self.timelineHeaderXRange
        if not self.headers:
            return None
        idx = -1
        for i, hd in enumerate(self.headers):
            if hd['title'] == '分时图':
                idx = i
                break
        if idx < 0:
            return None
        sx = self.getColumnX(idx)
        cw = self.getColumnWidth(idx, None)
        self.timelineHeaderXRange = (sx, sx + cw)
        return self.timelineHeaderXRange
    
    def onMouseMove(self, x, y):
        self.mouseX = x
        xr = self.getTimelineXRange()
        if not xr:
            return
        if x >= self.timelineHeaderXRange[0] and x <= self.timelineHeaderXRange[1]:
            self.invalidWindow()

    def onDraw(self, hdc):
        super().onDraw(hdc)
        if not self.mouseX or not self.timelineHeaderXRange:
            return
        if self.mouseX < self.timelineHeaderXRange[0] or self.mouseX > self.timelineHeaderXRange[1]:
            return
        w, h = self.getClientSize()
        self.drawer.drawLine(hdc, self.mouseX, self.headHeight, self.mouseX, h, color = 0x202020, style = win32con.PS_DASHDOT)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onMouseMove(x, y)
            # no return
        elif msg == win32con.WM_SIZE:
            self.timelineHeaderXRange = None
            # no return
        return super().winProc(hwnd, msg, wParam, lParam)
    