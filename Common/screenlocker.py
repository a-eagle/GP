import os, sys, re, time, json, io
import win32gui, win32con, win32api, win32event
import threading, time, datetime, sys, os
from multiprocessing import Process
from multiprocessing import shared_memory # python 3.8+
import ctypes
import system_hotkey

import base_win

class ScreenLocker(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0
        self.keys = ''

    def createWindow(self, parentWnd = None, rect = None, style = 0, className='STATIC', title=''):
        W = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        H = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        rect = (0, 0, W, H)
        style = win32con.WS_POPUP
        super().createWindow(parentWnd, rect, style, className, title)

    def onChar(self, keyCode):
        if keyCode == win32con.VK_RETURN:
            if 'gaoyan2012' in self.keys or 'gaoyan' in self.keys:
                self.unlock()
            self.keys = ''
            self.invalidWindow()
        else:
            self.keys += chr(keyCode)
            self.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SYSKEYDOWN or msg == win32con.WM_SYSKEYUP:
            return True
        if msg == win32con.WM_SHOWWINDOW:
            if wParam == True:
                win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_LBUTTONDOWN or msg == win32con.WM_LBUTTONUP:
            win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_CHAR:
            self.onChar(wParam)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
    def isLocked(self):
        locked = win32gui.IsWindow(self.hwnd) and win32gui.IsWindowVisible(self.hwnd)
        return locked
    
    def unlock(self):
        if win32gui.IsWindow(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def lock(self):
        if not win32gui.IsWindow(self.hwnd):
            self.createWindow()
        if win32gui.IsWindowVisible(self.hwnd):
            return
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOMOVE)
        W, H = self.getClientSize()
        win32api.SetCursorPos((W // 2, H // 2))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        self.invalidWindow()

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        # box
        CW = 30
        sx = 0
        sy = H - CW
        rc = (sx, sy, sx + CW, sy + CW)
        color = 0x202020
        self.drawer.fillRect(hdc, rc, color)

class Main:
    NO_LOCK_TIME_IDX = 0
    LOCK_IDX = 1

    LOCK_STATUS_LOCK = 100
    LOCK_STATUS_UNLOCK = 200
    MAX_IDLE_TIME = 3 * 60 * 1000
    
    def __init__(self, locker : ScreenLocker) -> None:
        self.locker = locker
        self.thread = base_win.Thread()
        self.shm = None
        self._name = 'PY_Screen_Locker'
        self.lastInputTime = 0
        self.lastOffMonitorTime = 0 # 黑屏时间

    def start(self):
        SZ = 128
        try:
            self.shm = shared_memory.SharedMemory(self._name, True, size = SZ)
        except:
            self.shm = shared_memory.SharedMemory(self._name, False, size = SZ)
        buf = self.shm.buf.cast('q')
        for i in range(SZ // 8):
            buf[i] = 0

        self.thread.addTask(1, self.loop)
        self.thread.start()

        hk = system_hotkey.SystemHotkey()
        hk.register(('alt', 'l'), callback = self.doHotKey, overwrite = True)

    def doHotKey(self, args):
        self.reset()
        if self.locker.isLocked():
            self.locker.unlock()
        else:
            self.locker.lock()
    
    def writeIntData(self, pos, data):
        if not self.shm:
            return
        buf = self.shm.buf.cast('q')
        buf[pos] = data

    def readIntData(self, pos):
        if not self.shm:
            return 0
        buf = self.shm.buf.cast('q')
        data = buf[pos]
        return data
    
    def reset(self):
        if not self.shm:
            return
        self.writeIntData(self.LOCK_IDX, 0)
        self.writeIntData(self.NO_LOCK_TIME_IDX, 0)
    
    # mili seconds
    def getIdleTime(self):
        lit = win32api.GetLastInputInfo()
        lit = max(lit, self.lastInputTime)
        idleTime = win32api.GetTickCount()  - lit
        return idleTime
    
    # mili seconds
    def getOffMonitorTime(self):
        diff = win32api.GetTickCount() - self.lastOffMonitorTime
        return diff
    
    def offMonitor(self):
        self.lastOffMonitorTime = win32api.GetTickCount()
        POWER_OFF = 2 # -1: 开机  1:省电  2:关闭
        win32gui.PostMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, win32con.SC_MONITORPOWER, POWER_OFF)

    def loop(self):
        while True:
            time.sleep(1)

            noLockTime = self.readIntData(self.NO_LOCK_TIME_IDX)
            if win32api.GetTickCount() < noLockTime:
                if self.locker.isLocked():
                    self.locker.unlock()
                continue

            #if (idleTime >= 5 * 60) and (self.getOffMonitorTime() >= 10 * 60):
            #    self.offMonitor()

            status = self.readIntData(self.LOCK_IDX)
            if status != 0:
                self.writeIntData(self.LOCK_IDX, 0)
                if status == self.LOCK_STATUS_LOCK:
                    self.locker.lock()
                elif status == self.LOCK_STATUS_UNLOCK:
                    self.locker.unlock()
                    self.lastInputTime = win32api.GetTickCount()
                continue
            
            idleTime = self.getIdleTime()
            if idleTime >= self.MAX_IDLE_TIME:
                self.locker.lock()

if __name__ == '__main__':
    locker = ScreenLocker()
    locker.createWindow()

    main = Main(locker)
    main.start()

    locker.lock()
    win32gui.PumpMessages()

    # 生成无cmd窗口的exe程序
    # cd Common; pyinstaller.exe -F -w screenlocker.py base_win.py   