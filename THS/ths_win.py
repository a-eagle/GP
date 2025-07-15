import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os
from multiprocessing import Process
from PIL import Image # pip install pillow
# import easyocr

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import number_ocr
from ui import base_win

class ThsWindow(base_win.BaseWindow):
    _ins = None

    def __init__(self) -> None:
        super().__init__()
        self.topHwnd = None
        self.mainHwnd = None
        self.level2CodeHwnd = None
        self.selDayHwnd = None
        self.numberOcr = number_ocr.NumberOCR('day', '0123456789')

    @classmethod
    def ins(clazz):
        if not clazz._ins:
            clazz._ins = ThsWindow()
        return clazz._ins

    def getPageName(self):
        if not self.topHwnd:
            return None
        if not win32gui.IsWindow(self.topHwnd):
            return None
        title = win32gui.GetWindowText(self.topHwnd)
        if not title:
            return None
        if not title.startswith('同花顺'):
            print('ThsWindow.getPageName not unknown widow type: ', title)
            return title
        if '技术分析' in title:
            return '技术分析'
        if '分时走势' in title:
            return '分时走势'
        if '龙虎榜' in title:
            return '龙虎榜'
        if '-' in title:
            title = title[title.index('-') + 1 : ].strip()
        return title

    def findLevel2CodeWnd(self, hwnd):
        child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
        while child:
            title = win32gui.GetWindowText(child)
            if win32gui.IsWindowVisible(child) and title and ('逐笔成交--' in title):
                self.level2CodeHwnd = child
                break
            self.findLevel2CodeWnd(child)
            if self.level2CodeHwnd:
                break
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)

    def findSelectDayWnd(self):
        if not self.mainHwnd:
            return None
        child = win32gui.GetWindow(self.mainHwnd, win32con.GW_CHILD)
        while child:
            if win32gui.GetClassName(child) == '#32770':
                left, top, right, bottom = win32gui.GetClientRect(child)
                w, h = right - left, bottom - top
                if h / 3 > w:
                    return child
            child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
        return None    

    # 当前显示的窗口是否是K线图
    def isInKlineWindow(self):
        if '技术分析' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 当前显示的窗口是否是分时图
    def isInFenShiWindow(self):
        if '分时走势' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 当前显示的窗口是否是龙虎榜
    def isInLHBWindow(self):
        if '龙虎榜' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 当前显示的窗口是否是“我的首页”
    def isInMyHomeWindow(self):
        if not self.topHwnd or not win32gui.IsWindow(self.topHwnd):
            return False
        if '我的首页' not in win32gui.GetWindowText(self.topHwnd):
            return False
        return win32gui.IsWindowVisible(self.topHwnd)

    # 查找股票代码
    def findCode_Level2(self):
        #if (not self.isInKlineWindow()) and (not self.isInMyHomeWindow()):
            #print('Not in KLine Window')
        #    return None
        # 逐笔成交明细 Level-2
        if not win32gui.IsWindowVisible(self.level2CodeHwnd):
            self.level2CodeHwnd = None
            self.findLevel2CodeWnd(self.mainHwnd)
        title = win32gui.GetWindowText(self.level2CodeHwnd) or ''
        code = ''
        if '逐笔成交--' in title:
            code = title[6 : 12]
        return code

    def hasCodeWindow(self):
        if not self.level2CodeHwnd:
            return False
        return win32gui.IsWindow(self.level2CodeHwnd) and win32gui.IsWindowVisible(self.level2CodeHwnd)

    def getSelectDay(self):
        if not self.selDayHwnd:
            self.selDayHwnd = self.findSelectDayWnd()
        if not win32gui.IsWindowVisible(self.selDayHwnd):
            return None
        rc = win32gui.GetWindowRect(self.selDayHwnd)
        w = rc[2] - rc[0]
        dc = win32gui.GetWindowDC(self.selDayHwnd)
        #mdc = win32gui.CreateCompatibleDC(dc)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, 50) # image size w x 50
        saveDC.SelectObject(saveBitMap)

        # copy year bmp
        RIGHT_CLOSE_BOX_WIDTH = 14
        srcPos = (RIGHT_CLOSE_BOX_WIDTH, 21)
        YEAR_MONTH_HEIGHT = 34
        srcSize = (w - RIGHT_CLOSE_BOX_WIDTH * 2, YEAR_MONTH_HEIGHT)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        #saveBitMap.SaveBitmapFile(saveDC, 'D:/SD.bmp')
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], YEAR_MONTH_HEIGHT), bmpstr, 'raw', 'BGRX', 0, 1) # bmpinfo['bmHeight']
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.selDayHwnd, dc)

        yearImg = im_PIL.crop((0, 0, im_PIL.width, YEAR_MONTH_HEIGHT // 2))
        monthImg = im_PIL.crop((0, YEAR_MONTH_HEIGHT // 2, im_PIL.width, YEAR_MONTH_HEIGHT))
        #yearImg.save('D:/y.bmp')
        #monthImg.save('D:/m.bmp')
        selYear = self.numberOcr.match(yearImg)
        selDay = self.numberOcr.match(monthImg)
        #print('selYear=', selYear, 'selDay=', selDay)

        sd = selYear + '-' + selDay[0 : 2] + '-' + selDay[2 : 4]
        #check is a day
        sd2 = sd.replace('-', '')
        if len(sd2) != 8:
            return '' # invalid day
        for s in sd2:
            if s < '0' or s > '9':
                return '' # invalid day
        #print(sd)
        return sd

    def init(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if ('同花顺(v' in title) and ('副屏' not in title):
                self.topHwnd = hwnd
            return True
        win32gui.EnumWindows(callback, None)
        self.mainHwnd =  win32gui.FindWindowEx(self.topHwnd, None, 'AfxFrameOrView140s', None)
        self.selDayHwnd = self.findSelectDayWnd()

        if (not self.mainHwnd) or (not self.topHwnd): # or (not self.selDayHwnd):
            return False
        #print('ThsWindow.topHwnd = %#X' % self.topHwnd)
        #print('ThsWindow.mainHwnd = %#X' % self.mainHwnd)
        #print('ThsWindow.selDayHwnd = %#X' % self.selDayHwnd)
        return True

    def showMax(self):
        if not win32gui.IsWindow(self.topHwnd):
            return
        #rc = win32gui.GetWindowRect(self.topHwnd)
        #if win32gui.IsIconic(self.topHwnd):
        win32gui.ShowWindow(self.topHwnd, win32con.SW_MAXIMIZE)

    def findCodeOfCurPage(self):
        #if self.isInKlineWindow() or self.isInFenShiWindow() or self.isInMyHomeWindow():
        #    return self.findCode_Level2()
        code = self.findCode_Level2()
        if code:
            return code
        if self.isInLHBWindow():
            return self.getCodeInLhbWindow()
        return ''

    def getCodeInLhbWindow(self):
        dwu = number_ocr.DumpWindowUtils()
        rc = win32gui.GetClientRect(self.mainHwnd)
        w = rc[2] - rc[0]
        img = dwu.dumpImg(self.mainHwnd, (int(w * 0.4), 52, int(w * 0.7), 85))
        # img.save('D:/lhb-code.bmp')
        code = number_ocr.readCodeFromImage(img)
        if not code:
            return ''
        return code

class ThsFuPingWindow(ThsWindow):
    def __init__(self) -> None:
        super().__init__()

    def init(self):
        def callback(hwnd, lparam):
            title = win32gui.GetWindowText(hwnd)
            if ('同花顺(v' in title) and ('副屏1' in title):
                self.topHwnd = hwnd
            return True
        win32gui.EnumWindows(callback, None)
        self.mainHwnd =  win32gui.FindWindowEx(self.topHwnd, None, 'AfxFrameOrView140s', None)
        self.selDayHwnd = self.findSelectDayWnd()

        if (not self.mainHwnd) or (not self.topHwnd) or (not self.selDayHwnd):
            return False
        print('ThsFuPingWindow.topHwnd = %#X' % self.topHwnd)
        print('ThsFuPingWindow.mainHwnd = %#X' % self.mainHwnd)
        print('ThsFuPingWindow.selDayHwnd = %#X' % self.selDayHwnd)
        return True  

class ThsSmallF10Window:
    hwnd = None

    @classmethod
    def findWindow(cls):
        if cls.hwnd and win32gui.IsWindow(cls.hwnd):
            return cls.hwnd
        cls.hwnd =  win32gui.FindWindow('smallF10_dlg', '小F10')
        return cls.hwnd

    @classmethod
    def adjustPos(cls, x = 25, y = 540):
        hwnd = cls.findWindow()
        if not hwnd:
            return
        win32gui.SetWindowPos(hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)

class ThsSelDayWindow:
    RIGHT = 448

    def __init__(self) -> None:
        self.reset()

    def reset(self):
        self.lastCode = None
        self.lastMoved = None

    def onTryMove(self, thsWin : ThsWindow, code):
        if not thsWin.isInMyHomeWindow():
            self.reset()
            return
        hwnd = thsWin.selDayHwnd
        if not win32gui.IsWindow(hwnd):
            self.reset()
            return
        if not win32gui.IsWindowVisible(hwnd):
            self.reset()
            return
        if self.lastCode == code:
            if self.lastMoved:
                return
            else:
                self.move(hwnd, code)
        else:
            self.move(hwnd, code)
            
    def move(self, hwnd, code):
        self.lastCode = code
        self.lastMoved = True
        parent = win32gui.GetParent(hwnd)
        if not parent:
            return
        prc = win32gui.GetWindowRect(parent)
        rc = win32gui.GetWindowRect(hwnd)
        PW, PH = prc[2] - prc[0], prc[3] - prc[1]
        W, H = rc[2] - rc[0], rc[3] - rc[1]
        x = PW - self.RIGHT
        y = PH - H
        win32gui.SetWindowPos(hwnd, 0, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)

if __name__ == '__main__':
    win = ThsWindow.ins()
    win.init()
    win.getCodeInLhbWindow()

