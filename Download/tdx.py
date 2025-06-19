import sys, os, pyautogui, win32gui, win32con, time, datetime, traceback
import io, psutil, subprocess, win32process, win32event, win32api, winerror
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import peewee as pw
from multiprocessing import shared_memory # python 3.8+

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from download.tdx_datafile import *
from orm import d_orm
from ui import fx

class TdxGuiDownloader:
    def __init__(self) -> None:
        pass

    def checkProcessStarted(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'tdxw.exe' in p.name().lower():
                self.pid = pid
                return True
        return False

    def startProcess(self):
        subprocess.Popen('D:\\new_tdx\\TdxW.exe', shell=True)
        time.sleep(15)

    def killProcess(self):
        os.system('taskkill /F /IM TdxW.exe')

    # x, y is relative position hwnd
    def click(self, hwnd, x, y):
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, 0, y * 65536 + x)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, y * 65536 + x)

    def inputs(self, hwnd, chars):
        for ch in chars:
            win32api.PostMessage(hwnd, win32con.WM_CHAR, ord(ch), 0x220001)
            time.sleep(0.1)

    def enter(self, hwnd):
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0x0001)
        time.sleep(0.1)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0x0001)

    def getScreenPos(self, hwnd, x, y, recurcive = True):
        while hwnd:
            #print(f'hwnd={hwnd:X}', win32gui.GetWindowText(hwnd))
            nx, ny , *_ = win32gui.GetWindowRect(hwnd)
            x += nx
            y += ny
            hwnd = win32gui.GetParent(hwnd)
            if not recurcive:
                break
        return (x, y)

    def login(self):
        hwnd = win32gui.FindWindow('#32770', '通达信金融终端V7.69')
        print(f'login hwnd=0x{hwnd :X}')
        if not hwnd:
            raise Exception('Not find Tdx login window')
        # win32gui.SetForegroundWindow(hwnd)
        time.sleep(3)
        loginBtn = win32gui.GetDlgItem(hwnd, 0x1)
        self.click(loginBtn, 0, 0)

        # pwdEditer = win32gui.GetDlgItem(hwnd, 0x422)
        # self.click(pwdEditer, 0, 0)
        # time.sleep(0.5)
        # self.enter(pwdEditer)

        # pwdPos = (250, 300)
        # pwdPos = self.getScreenPos(hwnd, *pwdPos)
        # pyautogui.click(*pwdPos, duration=0.5)
        # for i in range(20):
            # pyautogui.press('backspace')
        # pyautogui.typewrite('gaoyan2012')
        # loginBtnPos = (200, 370)
        # loginBtnPos = self.getScreenPos(hwnd, *loginBtnPos)
        # pyautogui.click(*loginBtnPos, duration=0.5)
        time.sleep(15)

    def getTdxMainWindow(self):
        mainWnd = win32gui.FindWindow('TdxW_MainFrame_Class', None)
        print(f'main tdx window={mainWnd:X}')
        if not mainWnd:
            raise Exception('Not find tdx main window')
        return mainWnd
    
    def getChildWindow(self, hwnd, className = None, title = None):
        child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
        while child:
            if className and title:
                if win32gui.GetClassName(child) == className and win32gui.GetWindowText(child) == title:
                    return child
            elif className:
                if win32gui.GetClassName(child) == className:
                    return child
            elif title:
                if win32gui.GetWindowText(child) == title:
                    return child
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
        return child

    def openDownloadDialog(self):
        mainWnd = self.getTdxMainWindow()
        child = self.getChildWindow(mainWnd, 'ToolbarWindow32')
        self.click(child, 430, 10)
        # win32gui.SetForegroundWindow(mainWnd)
        time.sleep(5)

    def getStartDayForDay(self):
        maxday = 20250612
        df = K_DataFile('999999')
        df.loadData()
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def getStartDayForTimemimute(self):
        maxday = 20250612
        df = T_DataFile('999999')
        df.loadData()
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def startDownloadForDay(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        selBtnPos = self.getScreenPos(hwnd, 80, 95, False)
        win32gui.SetForegroundWindow(hwnd)
        pyautogui.click(*selBtnPos, duration = 0.3)
        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) #
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForDay()
        fromDayCtrl.set_time(year = startDay.year, month = startDay.month, day = startDay.day)

        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 
        # wait for download end
        statusCtrl = win32gui.GetDlgItem(hwnd, 0x4C8) 
        time.sleep(3)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break
        pyautogui.click(*selBtnPos, duration = 0.3)
        time.sleep(3)

    def startDownloadForTimeMinute(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        # win32gui.SetForegroundWindow(hwnd)
        tabWin = win32gui.FindWindowEx(hwnd, None, 'SysTabControl32', 'Tab2')
        self.click(tabWin, 110, 10)
        time.sleep(2)
        oneFsBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '1分钟线数据')
        print(f'oneFsBtn = {oneFsBtn :x}')
        self.click(oneFsBtn, 10, 5)

        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5)
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForTimemimute()
        fromDayCtrl.set_time(year=startDay.year, month=startDay.month, day = startDay.day)
        print('start minutes day: ', startDay.strftime("%Y-%m-%d"))
        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        self.click(startBtn, 10, 5)

        # wait for download end
        time.sleep(3)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

    def checkNeedDownload(self, dataFileType):
        kdf = dataFileType('999999')
        kdf.loadData()
        today = datetime.date.today()
        if not kdf.days:
            return True
        fd = int(kdf.days[-1])
        fromDay = datetime.date(fd // 10000, fd // 100 % 100, fd % 100)
        days = 0
        while fromDay < today:
            fromDay += datetime.timedelta(days = 1)
            if fromDay.weekday() < 5: # week 1-5
                days += 1
        return days > 0

    def run(self):
        if self.checkProcessStarted():
            self.killProcess()
        pyautogui.hotkey('win', 'd')
        self.startProcess()
        try:
            self.login()
            self.openDownloadDialog()
            # if self.checkNeedDownload(K_DataFile):
            #     self.startDownloadForDay()
            if self.checkNeedDownload(T_DataFile):
                self.startDownloadForTimeMinute()
            ok = True
        except:
            traceback.print_exc()
            ok = False
        self.killProcess()
        return ok

class Main:
    def unlockScreen(self):
        try:
            shm = shared_memory.SharedMemory('PY_Screen_Locker', False)
            buf = shm.buf.cast('q')
            ts = win32api.GetTickCount() + 60 * 1000 * 60
            buf[0] = ts
            buf.release()
            shm.close()
            time.sleep(10)
        except Exception as e:
            import traceback
            traceback.print_exc()
            pass

    def resetLockScreen(self):
        try:
            shm = shared_memory.SharedMemory('PY_Screen_Locker', False)
            buf = shm.buf.cast('q')
            buf[0] = 0
            buf.release()
            shm.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            pass

    def runOnce(self):
        print('---work--start---')
        # self.unlockScreen()
        tm = datetime.datetime.now()
        ss = tm.strftime('%Y-%m-%d %H:%M')
        print('\033[32m' + ss + '\033[0m')
        tdx = TdxGuiDownloader()
        flag = tdx.run()
        # self.resetLockScreen()
        if flag:
            tm = datetime.datetime.now()
            ss = tm.strftime('%Y-%m-%d %H:%M')
            print('download end ', ss)
            print('merge mimute time line data')
            ld = Writer()
            ld.writeAll()
            ld = fx.FenXiLoader()
            ld.fxAll_2()
        print('-----------End----------\n\n')
        return flag

    def getDesktopGUILock(self):
        LOCK_NAME = 'D:/__Desktop_GUI_Lock__'
        mux = win32event.CreateMutex(None, False, LOCK_NAME)
        if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
            win32api.CloseHandle(mux)
            return None
        return mux

    def releaseDesktopGUILock(self, lock):
        if lock:
            win32api.CloseHandle(lock)

    # seconds
    def checkUserNoInputTime(self):
        a = win32api.GetLastInputInfo()
        cur = win32api.GetTickCount()
        diff = cur - a
        sec = diff / 1000
        return sec >= 5 * 60

    def runLoop(self):
        os.system('') # fix win10
        tryDays = {}
        while True:
            today = datetime.datetime.now()
            if today.weekday() >= 5:
                time.sleep(60 * 60)
                continue
            ts = f"{today.hour:02d}:{today.minute:02d}"
            if ts < '15:35':
                time.sleep(3 * 60)
                continue
            sday = today.strftime('%Y-%m-%d')
            if sday not in tryDays:
                tryDays[sday] = {'15': False, 'num' : 0, 'success': False}
            if today.hour == 15 and not tryDays[sday]['15']:
                tryDays[sday]['15'] = True
                if self.runOnce():
                    tryDays[sday]['success'] = True
                continue
            if ts < '19:00' or tryDays[sday]['success']:
                time.sleep(10 * 60)
                continue
            # lock = self.getDesktopGUILock()
            # if not lock:
            #     time.sleep(3 * 60)
            #     continue
            tryDays[sday]['num'] += 1
            if tryDays[sday]['num'] <= 2:
                if self.runOnce():
                    tryDays[sday]['success'] = True
            # self.releaseDesktopGUILock(lock)
            time.sleep(10 * 60)

    def start(self):
        if '--once' in sys.argv:
            print('Run only once time')
            self.runOnce()
        else:
            self.runLoop()

if __name__ == '__main__':
    mm = Main()
    mm.start()