import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, traceback, functools, types
import os, sys, requests, json
import win32gui, win32con

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from ui import base_win

class ToolbarWindow(base_win.NoActivePopupWindow):
    MOVE_BOX_WIDTH = 15
    def __init__(self, sender, linkWindow) -> None:
        super().__init__()
        self.sender = sender
        self.css['paddings'] = (30, 0, 30, 0)
        self.css['bgColor'] = 0xdddddd
        self.linkWindow = linkWindow
        self.boxs = [
            # {'text': 'A', 'icon': None, 'name': 'sel-idx-on-click', 'width': 30, 'desc': '点击时选中K线'},
            {'text': '', 'icon': self.drawLineIcon, 'name': 'draw-line', 'width': 30, 'desc': ''},
            {'text': 'A', 'icon': self.drawTextIcon, 'name': 'draw-text', 'width': 30, 'desc': ''},
            {'text': '', 'icon': self.drawZFIcon, 'name': 'calc-zdf', 'width': 30, 'desc': ''},
        ]
        self.hoverIdx = -1

        # self.linkWindowProc = self.linkWindow.winProc
        # self.linkWindow.winProc = types.MethodType(self._linkWindowProcNew, self.linkWindow)

    def _linkWindowProcNew(self, win, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOVE:
            pass
        return self.linkWindowProc(hwnd, msg, wParam, lParam)

    def onDraw(self, hdc):
        self.calcBoxsRect()
        W, H = self.getClientSize()
        self.drawer.fillRect(hdc, (0, 0, self.MOVE_BOX_WIDTH, H), rgb=0xbbbbbb)
        for i in range(len(self.boxs)):
            box = self.boxs[i]
            if self.hoverIdx == i:
                self.drawer.fillRect(hdc, box['rect'], rgb = 0x9999FF)
            if box['icon']: box['icon'](hdc, i)

    def drawLineIcon(self, hdc, idx):
        box = self.boxs[idx]
        sx, sy, ex, ey = box['rect']
        cy = (ey + sy) // 2
        SP = 4
        px, py = ex - SP - SP // 2, cy
        self.drawer.drawLine(hdc, sx + SP, cy, px, py, color = 0x0, width = 2)
        M = 3
        self.drawer.fillRect(hdc, (px - M, py - M, px + M, py + M), 0x0)

    def drawTextIcon(self, hdc, idx):
        rc = self.boxs[idx]['rect']
        self.drawer.use(hdc, self.drawer.getFont(fontSize=18, weight=1000))
        self.drawer.drawText(hdc, 'A', rc, color = 0x0, align = base_win.Drawer.ALIGN_SINGLELINE_CENTER)

    def drawZFIcon(self, hdc, idx):
        box = self.boxs[idx]
        sx, sy, ex, ey = box['rect']
        SP = 4
        H = 13
        bsy = ((ey - sy) - H) // 2 + sy
        bey = bsy + H
        self.drawer.drawLine(hdc, sx + SP, bsy, ex - SP, bsy, color = 0x0, width = 2)
        self.drawer.drawLine(hdc, sx + SP, bey, ex - SP, bey, color = 0x0, width = 2)
        bcx = (ex - sx) // 2 + sx
        self.drawer.drawLine(hdc, bcx, bsy, bcx, bey, color = 0x0, width = 1)

    def calcBoxsRect(self):
        w, h = self.getClientSize()
        x = w - self.css['paddings'][2]
        ey = h - self.css['paddings'][3]
        y = self.css['paddings'][1]
        BOX_SPACE = 5
        for i in range(len(self.boxs) - 1, -1, -1):
            box = self.boxs[i]
            box['rect'] = (x, y, x + box['width'], ey)
            x -= box['width'] + BOX_SPACE

    def pointAt(self, x, y):
        for idx, box in enumerate(self.boxs):
            if 'rect' not in box:
                continue
            sx, sy, ex, ey = box['rect']
            if x >= sx and y >= sy and x < ex and y < ey:
                return idx
        return -1
    
    def onClick(self, x, y):
        idx = self.pointAt(x, y)
        if idx < 0:
            return
        box = self.boxs[idx]
        if self.sender:
            self.sender.onMemuItem(self.Event('Select', self, item = {'name': box['name']}), None)
    
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
        elif msg == win32con.WM_MOUSEMOVE:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            idx = self.pointAt(x, y)
            if self.hoverIdx != idx:
                self.hoverIdx = idx
                self.invalidWindow()
        elif msg == win32con.WM_NCHITTEST:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            cx, cy = win32gui.ScreenToClient(self.hwnd, (x, y))
            if cx <= self.MOVE_BOX_WIDTH:
                return win32con.HTCAPTION
            return win32con.HTCLIENT
        elif msg == win32con.WM_MOUSELEAVE: # no use
            if self.hoverIdx != -1:
                self.hoverIdx = -1
                self.invalidWindow()
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    win = ToolbarWindow(None, None)
    win.createWindow(None, (0, 0, 500, 80), win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    win.mainWin = True
    win32gui.PumpMessages()