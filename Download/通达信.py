import sys, os, pyautogui, win32gui, win32con, time, datetime, traceback
import io, psutil, subprocess, win32process, win32event, win32api, winerror
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import peewee as pw
from multiprocessing import shared_memory # python 3.8+

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import datafile

class TdxDownloader:
    def __init__(self) -> None:
        pass

    def checkProcessStarted(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'tdxw.exe' in p.name().lower():
                self.pid = pid
                #print('已检测到开启了通达信')
                return True
        return False

    def startProcess(self):
        subprocess.Popen('D:\\Program Files\\new_tdx2\\TdxW.exe', shell=True)
        time.sleep(10)

    def killProcess(self):
        os.system('taskkill /F /IM TdxW.exe')

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
        hwnd = win32gui.FindWindow('#32770', '通达信金融终端V7.642')
        print(f'login hwnd=0x{hwnd :X}')
        if not hwnd:
            raise Exception('Not find Tdx login window')
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(3)
        pwdPos = (250, 300)
        pwdPos = self.getScreenPos(hwnd, *pwdPos)
        pyautogui.click(*pwdPos, duration=0.5)
        for i in range(20):
            pyautogui.press('backspace')
        pyautogui.typewrite('gaoyan2012')

        loginBtnPos = (200, 370)
        loginBtnPos = self.getScreenPos(hwnd, *loginBtnPos)
        pyautogui.click(*loginBtnPos, duration=0.5)
        time.sleep(15)

    def getTdxMainWindow(self):
        mainWnd = win32gui.FindWindow('TdxW_MainFrame_Class', None)
        print(f'main tdx window={mainWnd:X}')
        if not mainWnd:
            raise Exception('Not find tdx main window')
        return mainWnd
    
    def openDownloadDialog(self):
        mainWnd = self.getTdxMainWindow()
        win32gui.SetForegroundWindow(mainWnd)
        btnPos = (433, 35)
        time.sleep(3)
        btnPos = self.getScreenPos(mainWnd, *btnPos)
        pyautogui.click(*btnPos, duration=0.5)
        time.sleep(10)

    def getStartDayForDay(self):
        maxday = 20240101
        df = datafile.DataFile('999999', datafile.DataFile.DT_DAY)
        df.loadData(datafile.DataFile.FLAG_ALL)
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        #dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def getStartDayForTimemimute(self):
        maxday = 20240101
        df = datafile.DataFile('999999', datafile.DataFile.DT_MINLINE)
        df.loadData(datafile.DataFile.FLAG_ALL)
        if df.data:
            maxday = df.data[-1].day
        dt = datetime.datetime.strptime(str(maxday), '%Y%m%d')
        #dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def startDownloadForDay(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        selBtnPos = self.getScreenPos(hwnd, 80, 95, False) # 日线和实时行情Button pos
        win32gui.SetForegroundWindow(hwnd)
        pyautogui.click(*selBtnPos, duration = 0.3)
        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForDay()
        fromDayCtrl.set_time(year = startDay.year, month = startDay.month, day = startDay.day)

        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        statusCtrl = win32gui.GetDlgItem(hwnd, 0x4C8) 
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break
        pyautogui.click(*selBtnPos, duration = 0.3)

    def startDownloadForTimeMinute(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        win32gui.SetForegroundWindow(hwnd)
        selTabPos = self.getScreenPos(hwnd, 130, 35, False) # 一分钟线 tab pos
        pyautogui.click(*selTabPos, duration = 0.3)
        time.sleep(1.5)
        selBtnPos = self.getScreenPos(hwnd, 70, 70, False) # 一分钟线 pos
        pyautogui.click(*selBtnPos, duration = 0.3)

        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForTimemimute()
        fromDayCtrl.set_time(year=startDay.year, month=startDay.month, day = startDay.day)
        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(5)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

    def run(self):
        if self.checkProcessStarted():
            self.killProcess()
        pyautogui.hotkey('win', 'd')
        self.startProcess()
        try:
            self.login()
            self.openDownloadDialog()
            self.startDownloadForDay()
            self.startDownloadForTimeMinute()
        except:
            traceback.print_exc()
            return False
        self.killProcess()
        return True

def unlockScreen():
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

def resetLockScreen():
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

def tryWork():
    try:
        return work()
    except Exception as e:
        traceback.print_exc()
    return False

def work():
    time.sleep(5)
    print('---work--start---')
    unlockScreen()
    time.sleep(10)
    tm = datetime.datetime.now()
    ss = tm.strftime('%Y-%m-%d %H:%M')
    print('\033[32m' + ss + '\033[0m')
    # 下载
    tdx = TdxDownloader()
    flag = tdx.run()
    resetLockScreen()
    if flag:
        tm = datetime.datetime.now()
        ss = tm.strftime('%Y-%m-%d %H:%M')
        print('download end ', ss)
        print('merge mimute time line data')
        ld = datafile.DataFileLoader()
        ld.mergeAll()
    print('-----------End----------\n\n')
    return flag

def getDesktopGUILock():
    LOCK_NAME = 'D:/__Desktop_GUI_Lock__'
    mux = win32event.CreateMutex(None, False, LOCK_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        win32api.CloseHandle(mux)
        return None
    return mux

def releaseDesktopGUILock(lock):
    if lock:
        win32api.CloseHandle(lock)

# seconds
def checkUserNoInputTime():
    a = win32api.GetLastInputInfo()
    cur = win32api.GetTickCount()
    diff = cur - a
    sec = diff / 1000
    return sec >= 5 * 60

def getMaxDay(paths):
    md = None
    for p in paths:
        bn = os.path.basename(p)
        if '-' not in bn:
            continue
        sp = bn.split('-')
        if not md:
            md = sp[-1]
        elif md < sp[-1]:
            md = sp[-1]
    return md


def autoMain():
    os.system('') # fix win10 下console 颜色不生效
    lastDay = 0
    tryDays = {}
    while True:
        today = datetime.datetime.now()
        if today.weekday() >= 5: #周六周日
            time.sleep(60 * 60)
            continue
        if lastDay == today.day:
            time.sleep(60 * 60)
            continue
        ts = f"{today.hour:02d}:{today.minute:02d}"
        if ts < '18:30' or ts > '19:30':
            time.sleep(3 * 60)
            continue
        lock = getDesktopGUILock()
        if not lock:
            time.sleep(3 * 60)
            continue
        sday = today.strftime('%Y-%m-%d')
        if sday in tryDays:
            tryDays[sday] += 1
        else:
            tryDays[sday] = 1
        if tryDays[sday] <= 3 and work(): #checkUserNoInputTime() and
            lastDay = today.day
        releaseDesktopGUILock(lock)
        time.sleep(10 * 60)
        

def mergeTimeline():
    pass

if __name__ == '__main__':
    #t = TdxLSTools()
    #t.calcInfo()
    print('Tdx start')
    if 'debug' in sys.argv:
        work() # run one time
    else:
        autoMain()