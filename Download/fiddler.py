import os, json, time, sys, pyautogui
import io, psutil, subprocess
import win32gui, win32con , win32api, win32ui, win32process # pip install pywin32

class Fiddler:
    def __init__(self) -> None:
        self.pid = None
        self.needClose = False
        self.hwnd = 0

    def open(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'fiddler.exe' in p.name().lower():
                self.pid = pid
                print('已检测到开启了fiddler')
                return
        print('未开启fiddler, 自动开启')
        pp = subprocess.Popen('C:\\Program Files (x86)\\Fiddler\\Fiddler.exe', shell=True)
        time.sleep(5)
        self.needClose = True

    def close(self):
        print('关闭Fiddler... ')
        # os.system('taskkill /F /IM Fiddler.exe')
        #if not self.needClose:
        #    return
        win32gui.EnumWindows(self.cb, self)
        print(f'Fiddler hwnd=0x{self.hwnd:X}')
        if not self.hwnd:
            return
        if win32gui.IsIconic(self.hwnd):
            win32gui.ShowWindow(self.hwnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(self.hwnd)
        time.sleep(1.5)
        win32gui.PostMessage(self.hwnd, win32con.WM_CLOSE, 0, 0)
        self.hwnd = None
        print('已自动关闭Fiddler')

    @staticmethod
    def cb(hwnd, self):
        title = win32gui.GetWindowText(hwnd)
        # print(title)
        if 'Telerik Fiddler' in title:
            #threadId, processId = win32process.GetWindowThreadProcessId(hwnd)
            #p = psutil.Process(processId)
            #if 'fiddler.exe' in p.name().lower():
            self.hwnd = hwnd
        return True


if __name__ == '__main__':
    fd = Fiddler()
    fd.open()
    time.sleep(20)
    fd.close()
