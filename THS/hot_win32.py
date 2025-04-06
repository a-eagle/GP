import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, json, copy
from multiprocessing import Process
from multiprocessing.shared_memory import SharedMemory
import system_hotkey
#pip install system_hotkey

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import ths_win, ths_ocr, tips_win
from ui import base_win

curCode = None
thsWindow = ths_win.ThsWindow()
thsFPWindow = ths_win.ThsFuPingWindow()
simpleWindow = tips_win.SimpleWindow('HOT')
simpleWindow2 = tips_win.SimpleWindow('ZT_GN')
thsShareMem = base_win.ThsShareMemory()
simpleHotZHWindow = tips_win.SimpleHotZHWindow()
codeBasicWindow = tips_win.CodeBasicWindow()
thsSelDayWin = ths_win.ThsSelDayWindow()
bkGnWin = tips_win.BkGnWindow()
tipWins = [simpleWindow, simpleWindow2, simpleHotZHWindow, codeBasicWindow, bkGnWin]

def updateCode(nowCode):
    global curCode, thsShareMem
    try:
        icode = int(nowCode)
    except Exception as e:
        nowCode = '0'
    if curCode == nowCode:
        return
    curCode = nowCode
    #hotWindow.updateCode(nowCode)
    simpleWindow.changeCode(nowCode)
    simpleWindow2.changeCode(nowCode)
    codeBasicWindow.changeCode(nowCode)
    bkGnWin.changeCode(nowCode)
    thsShareMem.writeCode(nowCode)

def showTipWins(show : bool):
    for win in tipWins:
        if not win.hwnd or not win32gui.IsWindow(win.hwnd):
            continue
        win.setVisible(show)

def isTipWinsForeground():
    hwnd = win32gui.GetForegroundWindow()
    for h in tipWins:
        if hwnd == h.hwnd:
            return True
    return False

class WinStateMgr:
    def __init__(self, fileName) -> None:
        self.curPageName = None
        self.windowsInfo = {}
        path = os.path.dirname(__file__)
        path = os.path.join(path, fileName)
        self.fileName = path

    def read(self):
        if not os.path.exists(self.fileName):
            return
        file = open(self.fileName, 'r')
        txt = file.read().strip()
        file.close()
        if txt:
            self.windowsInfo = json.loads(txt)

    def save(self):
        file = open(self.fileName, 'w')
        txt = json.dumps(self.windowsInfo)
        file.write(txt)
        file.close()

def updateWindowInfo(thsWin, stateMgr : WinStateMgr):
    winsInfo = stateMgr.windowsInfo
    curPageName = thsWin.getPageName()
    if not curPageName:
        return
    if stateMgr.curPageName!= curPageName: # changed page
        stateMgr.curPageName = curPageName
        if curPageName not in winsInfo:
            winsInfo[curPageName] = {'s1': None, 's2': None, 's3': None, 's4': None, 's5': None}
        cp = winsInfo[curPageName]
        simpleWindow.setWindowState(cp.get('s1', None))
        simpleWindow2.setWindowState(cp.get('s3', None))
        simpleHotZHWindow.setWindowState(cp.get('s2', None))
        codeBasicWindow.setWindowState(cp.get('s4', None))
        bkGnWin.setWindowState(cp.get('s6', None))
        if curPageName == '技术分析':
            ths_win.ThsSmallF10Window.adjustPos()
    else:
        if curPageName not in winsInfo:
            winsInfo[curPageName] = {'s1': None, 's2': None, 's3': None}
        cp = winsInfo[curPageName]
        cp2 = {}
        cp2['s1'] = simpleWindow.getWindowState()
        cp2['s2'] = simpleHotZHWindow.getWindowState()
        cp2['s3'] = simpleWindow2.getWindowState()
        cp2['s4'] = codeBasicWindow.getWindowState()
        cp2['s6'] = bkGnWin.getWindowState()
        if cp != cp2:
            cp.update(cp2)
            stateMgr.save()

def _workThread(thsWin : ths_win.ThsWindow, fileName):
    global curCode
    stateMgr = WinStateMgr(fileName)
    stateMgr.read()
    wbOcr = ths_ocr.ThsWbOcrUtils()
    
    while True:
        time.sleep(0.5)
        #mywin.eyeWindow.show()
        if not win32gui.IsWindow(thsWin.topHwnd):
            #win32gui.PostQuitMessage(0)
            #sys.exit(0)  #仅退出当前线程
            os._exit(0) # 退出进程
            break
        #showHotWindow()
        if (win32gui.GetForegroundWindow() != thsWin.topHwnd) and (not isTipWinsForeground()):
            showTipWins(False)
            continue
        showTipWins(True)
        updateWindowInfo(thsWin, stateMgr)
        nowCode = thsWin.findCodeOfCurPage()
        if curCode != nowCode:
            updateCode(nowCode)
        selDay = thsWin.getSelectDay()
        if selDay:
            #hotWindow.updateSelectDay(selDay)
            simpleWindow.changeSelectDay(selDay)
            simpleWindow2.changeSelectDay(selDay)
            thsShareMem.writeSelDay(selDay)
        rs = wbOcr.runOcr_InHomePage(thsWin.mainHwnd)
        codeBasicWindow.updateWeiBi(rs)
        #thsSelDayWin.onTryMove(thsWin, nowCode)

def onListen(evt, args):
    if args == 'ListenHotWindow' and evt.name == 'mode.change':
        #showSortAndLiangDianWindow(not evtInfo['maxMode'], True)
        pass

def subprocess_main():
    while True:
        if thsWindow.init():
            break
        time.sleep(1.5)
    thsShareMem.open()
    #hotWindow.createWindow(thsWindow.topHwnd)
    simpleWindow.createWindow(thsWindow.topHwnd)
    simpleWindow2.createWindow(thsWindow.topHwnd)
    simpleHotZHWindow.createWindow(thsWindow.topHwnd)
    codeBasicWindow.createWindow(thsWindow.topHwnd)
    bkGnWin.createWindow(thsWindow.topHwnd)
    #hotWindow.addListener(onListen, 'ListenHotWindow')
    threading.Thread(target = _workThread, args=(thsWindow, 'hot-win32.json')).start()
    
    mm = MarkMain()
    mm.createWindow(thsWindow.topHwnd, (0, 0, 1, 1), win32con.WS_POPUP)
    mm.reg()
    win32gui.PumpMessages()
    print('Quit Sub Process')

def subprocess_main_fp():
    while True:
        if thsFPWindow.init():
            break
        time.sleep(3)
    thsShareMem.open()
    #hotWindow.createWindow(thsFPWindow.topHwnd)
    simpleWindow.createWindow(thsFPWindow.topHwnd)
    simpleWindow2.createWindow(thsFPWindow.topHwnd)
    simpleHotZHWindow.createWindow(thsFPWindow.topHwnd)
    codeBasicWindow.createWindow(thsFPWindow.topHwnd)
    bkGnWin.createWindow(thsFPWindow.topHwnd)
    threading.Thread(target = _workThread, args=(thsFPWindow, 'hot-win32-fp.json')).start()
    win32gui.PumpMessages()
    print('Quit Sub Process(THS FU PING)')    


def listen_ThsFuPing_Process():
    print('open listen fu ping prcess')
    while True:
        p = Process(target = subprocess_main_fp, daemon = True)
        p.start()
        print('start a new sub process(FU PING), pid=', p.pid)
        p.join()

class MarkWin(base_win.BaseWindow):
    def __init__(self, isMain) -> None:
        super().__init__()
        self.css['bgColor'] = 0xc0c0c0
        self.isMain = isMain

    def createWindow(self, parentWnd, rect = None, style= win32con.WS_POPUP, className='STATIC', title=''):
        if not rect:
            rect = (0,0, 1, 1)
        super().createWindow(parentWnd, rect, style, className, title)
        ce = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, ce | win32con.WS_EX_LAYERED) #  | win32con.WS_EX_TRANSPARENT
        win32gui.SetLayeredWindowAttributes(self.hwnd, self.css['bgColor'], 80, win32con.LWA_ALPHA)

    def onDraw(self, hdc):
        if self.isMain:
            w, h = self.getClientSize()
            rc = (0, 0, w, 200)
            self.drawer.fillRect(hdc, rc, 0x1D66CD)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SendMessage(hwnd, win32con.WM_NCLBUTTONDOWN, win32con.HTCAPTION, 0)
            # no return
        if msg == win32con.WM_NCLBUTTONDBLCLK or msg == win32con.WM_LBUTTONDBLCLK:
            self.hide()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

    def show(self, x = None, y = None):
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        prc = win32gui.GetWindowRect(thsWindow.topHwnd)
        if x == None:
            x = win32gui.GetCursorPos()[0]
        if y == None:
            y = prc[1] + 30
        W = 10
        h = prc[3] - y - 30
        x -= W // 2
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOP, x, y, W, h, 0)
        #print(win32gui.GetWindowRect(self.hwnd))

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
        win32gui.DestroyWindow(self.hwnd)

class MarkMain(base_win.BaseWindow):
    MSG_M = win32con.WM_USER + 100
    MSG_N = win32con.WM_USER + 101

    def __init__(self) -> None:
        super().__init__()
        self.subWins = []
        self.mainWin = None

    def doMarkKey_1(self, msg):
        win32gui.PostMessage(self.hwnd, self.MSG_M, None, None)
        
    def doMarkKey_2(self, msg):
        win32gui.PostMessage(self.hwnd, self.MSG_N, None, None)

    def reg(self):
        hk = system_hotkey.SystemHotkey()
        hk.register(('control', 'alt', 'm'), callback = self.doMarkKey_1, overwrite = True)
        hk.register(('control', 'alt', 'n'), callback = self.doMarkKey_2, overwrite = True)

    def onMarkMain(self):
        d = thsShareMem.readSelDay()
        thsShareMem.writeMarkDay(d)
        if self.mainWin and win32gui.IsWindow(self.mainWin.hwnd):
            self.mainWin.show()
            return
        self.mainWin = MarkWin(True)
        self.mainWin.createWindow(thsWindow.topHwnd)
        self.mainWin.show()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == self.MSG_M:
            self.onMarkMain()
            return True
        if msg == self.MSG_N:
            win = MarkWin(False)
            win.createWindow(thsWindow.topHwnd)
            win.show()
            self.subWins.append(win)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    tsm = base_win.ThsShareMemory(True)
    tsm.open()
    #zsOcr = ths_ocr.ThsZhangShuOcrUtils()
    #zsOcr.start()
    # listen ths fu ping
    #p = Process(target = listen_ThsFuPing_Process, daemon = False)
    #p.start()
    time.sleep(1)
    while True:
        p = Process(target = subprocess_main, daemon = True)
        p.start()
        print('start a new sub process, pid=', p.pid)
        p.join()
