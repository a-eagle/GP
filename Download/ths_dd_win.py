import os, json, time, sys, pyautogui
import io, psutil, subprocess
import win32gui, win32con , win32api, win32ui, win32process # pip install pywin32

class THS_Window:
    def __init__(self) -> None:
        self.hwnd = None
        self.needClose = False

    def open(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'hexin.exe' in p.name().lower():
                print('已检测到开启了同花顺, pid=', pid)
                return
        print('未开启同花顺, 自动开启')
        self.needClose = True
        subprocess.Popen('C:\\Program Files (x86)\\THS\\hexin.exe', shell=True)
        time.sleep(8)

    def close(self):
        if self.needClose:
            os.system('taskkill /F /IM hexin.exe')

    @staticmethod
    def cb(hwnd, self):
        title = win32gui.GetWindowText(hwnd)
        if '同花顺(v' in title:
            self.hwnd = hwnd
        return True
    
    def findWindow(self):
        win32gui.EnumWindows(THS_Window.cb, self)
        return self.hwnd

    def minisize(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_MINIMIZE)

# 同花顺大单的窗口
class THS_DDWindow:
    def __init__(self) -> None:
        self.ddDlgWnd = None
        self.ddBtnWnd = None
        self.topWnd = None

    def _enumChild(self, hwnd, ext):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        if '逐笔成交--600000(' in title:
            self.ddBtnWnd = hwnd
        return True

    # 打开 大单棱镜
    def _openDDLJ(self):
        if not self.topWnd:
            return
        if win32gui.IsIconic(self.topWnd):
            win32gui.ShowWindow(self.topWnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(self.topWnd)
        self.ddDlgWnd = win32gui.FindWindow(None, '大单棱镜')
        if self.ddDlgWnd:
            return
        time.sleep(2)
        pyautogui.press('F6', interval=0.5) # 进入我的自选股
        time.sleep(2)
        pyautogui.typewrite('600000', 0.1)
        pyautogui.press('enter')
        time.sleep(3)
        self.ddBtnWnd = None
        win32gui.EnumChildWindows(self.topWnd, self._enumChild, None)
        if not self.ddBtnWnd:
            return
        print(f'THS_DDWindow ddBtn hwnd= {self.ddBtnWnd: X}')
        *_, w, h = win32gui.GetClientRect(self.ddBtnWnd)
        x = w - 50
        win32gui.PostMessage(self.ddBtnWnd, win32con.WM_LBUTTONDOWN, 0, 0x000a0000 | x)
        time.sleep(0.01)
        win32gui.PostMessage(self.ddBtnWnd, win32con.WM_LBUTTONUP, 0, 0x000a0000 | x)
        time.sleep(3)
        self.ddDlgWnd = win32gui.FindWindow(None, '大单棱镜')
    
    def openDDLJ(self):
        for i in range(0, 3):
            if not self.ddDlgWnd:
                self._showTopWindow()
                self._openDDLJ()
                time.sleep(3)
        return self.ddDlgWnd

    def closeDDLJ(self):
        if self.ddDlgWnd:
            win32gui.PostMessage(self.ddDlgWnd, win32con.WM_CLOSE, 0, 0)
        self.ddDlgWnd = None

    def initWindows(self):
        def callback(hwnd, selfx):
            title = win32gui.GetWindowText(hwnd)
            if '同花顺(v' in title:
                selfx.topWnd = hwnd
            return True
        win32gui.EnumWindows(callback, self)
        print(f'[THS_DDWindow] 同花顺 top hwnd={self.topWnd :X}')

    def _showTopWindow(self):
        if not self.topWnd:
            return
        if win32gui.IsIconic(self.topWnd):
            win32gui.ShowWindow(self.topWnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(self.topWnd)

    def grubFocusInSearchBox(self):
        if not self.ddDlgWnd:
            return
        rect = win32gui.GetWindowRect(self.ddDlgWnd)
        x, y = rect[0] + 100, rect[1] + 60 # search input box center
        pyautogui.click(x, y)

    def releaseFocus(self):
        if not self.ddDlgWnd:
            return
        rect = win32gui.GetWindowRect(self.ddDlgWnd)
        x, y = rect[0] + 200, rect[1] + 60 # out search input box 
        pyautogui.click(x, y)

if __name__ == '__main__':
    dd = THS_DDWindow()
    dd.initWindows()
    dd.openDDLJ()
    dd.grubFocusInSearchBox()
    time.sleep(3)
    dd.closeDDLJ()
    time.sleep(3)
    dd.openDDLJ()