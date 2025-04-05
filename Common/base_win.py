import win32gui, win32con , win32api, win32ui, win32gui_struct, win32clipboard # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools, ctypes
import pyperclip # pip install pyperclip
from multiprocessing import shared_memory # python 3.8+
import ctypes, traceback

class Listener:
    class Event:
        def __init__(self, name, src, **kargs) -> None:
            self.name = name
            self.src = src
            for k in kargs:
                setattr(self, k, kargs[k])

    def __init__(self) -> None:
        self.listeners = []

    # func = function(event : Event, args)
    def addListener(self, func, args = None):
        self.listeners.append((func, args, '*'))

    def addNamedListener(self, evtName, func, args = None):
        if evtName == None or evtName == '':
            evtName = '*'
        self.listeners.append((func, args, evtName))

    def notifyListener(self, event : Event):
        for ls in self.listeners:
            func, args, name = ls
            if name == '*' or name == event.name:
                func(event, args)

# listeners : ContextMenu = {src, x, y} , default is disable
#             DbClick = {src, x, y} , default is disable
#             R_DbClick = {src, x, y} , default is disable
class BaseWindow(Listener):
    bindHwnds = {}
    def __init__(self) -> None:
        super().__init__()
        self.hwnd = None
        self.oldProc = None
        self.drawer = Drawer.instance()
        self._bitmap = None
        self._bitmapSize = None
        self.cacheBitmap = False
        self.css = {'fontSize' : 14, 'fontName' : '新宋体', 'fontWeight' : 0,
                    'bgColor': 0x000000, 'textColor': 0xffffff,
                    'borderColor': None, # None(no border) | int
                    'paddings': (0, 0, 0, 0) # (left, top, right, bottom)
                    } # config css style
    
    # @param rect = (x, y, width, height)
    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className = 'STATIC', title = ''): #  0x00800000 |
        self.hwnd = win32gui.CreateWindow(className, title, style, *rect, parentWnd, None, None, None)
        BaseWindow.bindHwnds[self.hwnd] = self
        self.oldProc = win32gui.SetWindowLong(self.hwnd, win32con.GWL_WNDPROC, BaseWindow._WinProc)
        #print(f'[BaseWindow.createWindow] self.oldProc=0x{self.oldProc :x}, title=', title)

    def getClientSize(self):
        if not self.hwnd:
            return None
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        return (r, b)
    
    def getDefFont(self):
        return self.drawer.getFont(name = self.css['fontName'], fontSize = self.css['fontSize'], weight=self.css['fontWeight'])
    
    # @return True: 已处理事件,  False:未处理事件
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_PAINT:
            hdc, ps = win32gui.BeginPaint(self.hwnd)
            self._draw(hdc)
            win32gui.EndPaint(self.hwnd, ps)
            return True
        if msg == win32con.WM_DESTROY:
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if (not (style & win32con.WS_POPUP)) and (not (style & win32con.WS_CHILD)):
                owner = win32gui.GetWindow(self.hwnd, win32con.GW_OWNER)
                if not owner:
                    win32gui.PostQuitMessage(0)
                return True
            self.onDestory()
            del BaseWindow.bindHwnds[hwnd]
        if msg == win32con.WM_RBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.notifyListener(self.Event('ContextMenu', self, x = x, y = y))
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.notifyListener(self.Event('DbClick', self, x = x, y = y))
            return True
        if msg == win32con.WM_RBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.notifyListener(self.Event('R_DbClick', self, x = x,  y = y))
            return True
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            #style = win32gui.GetWindowLong(self.hwnd, win32con.GWL_STYLE)
            #if (style & win32con.WS_OVERLAPPED) and
            if getattr(self, 'layout', None):
                pds = self.css['paddings']
                w, h = self.getClientSize()
                w -= pds[0] + pds[2]
                h -= pds[1] + pds[3]
                self.layout.resize(pds[0], pds[1], w, h)
            self.invalidWindow()
            #return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = delta - 0xffff - 1
            delta = delta // 120
            self.onMouseWheel(delta)
            return True
        return False

    def _draw(self, hdc):
        l, t, r, b = win32gui.GetClientRect(self.hwnd)
        w, h = r - l, b - t
        mdc = win32gui.CreateCompatibleDC(hdc)
        if (not self._bitmap) or (w != self._bitmapSize[0]) or (h != self._bitmapSize[1]):
            if self._bitmap: win32gui.DeleteObject(self._bitmap)
            self._bitmap = bmp = win32gui.CreateCompatibleBitmap(hdc, w, h)
            self._bitmapSize = (w, h)
        else:
            bmp = self._bitmap
        win32gui.SelectObject(mdc, bmp)
        self.drawer.fillRect(mdc, win32gui.GetClientRect(self.hwnd), self.css['bgColor'])
        if isinstance(self.css['borderColor'], int):
            self.drawer.drawRect(mdc, win32gui.GetClientRect(self.hwnd), self.css['borderColor'])
        win32gui.SetBkMode(mdc, win32con.TRANSPARENT)
        win32gui.SetTextColor(mdc, self.css['textColor'])
        self.drawer.use(mdc, self.getDefFont())
        self.onDraw(mdc)
        win32gui.BitBlt(hdc, 0, 0, w, h, mdc, 0, 0, win32con.SRCCOPY)
        win32gui.DeleteObject(mdc)
        if not self.cacheBitmap:
            win32gui.DeleteObject(self._bitmap)
            self._bitmap = None
            self._bitmapSize = None
        return True
        
    def onDraw(self, hdc):
        pass
    
    def onDestory(self):
        pass
    def onMouseWheel(self, delta):
        pass
    @staticmethod
    def _WinProc(hwnd, msg, wParam, lParam):
        self = BaseWindow.bindHwnds.get(hwnd, None)
        if not self:
            return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        rs = self.winProc(hwnd, msg, wParam, lParam)
        if not isinstance(rs, bool):
            return rs
        if rs == True:
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wParam, lParam)
        #if self.oldProc:
        #    return win32gui.CallWindowProc(self.oldProc, hwnd, msg, wParam, lParam)
    
    def invalidWindow(self):
        if win32gui.IsWindow(self.hwnd):
            win32gui.InvalidateRect(self.hwnd, None, True)

class Thread:
    _num = 0
    def __init__(self, threadName = None) -> None:
        Thread._num += 1
        self.tasks = []
        self.stoped = False
        self.started = False
        self.event = threading.Event()
        if not threadName:
            threadName = f'Thread-{Thread._num}'
        self.name = threadName
        self.thread = threading.Thread(target = Thread._run, args=(self,), name=threadName, daemon = True)
        self.lock = threading.Lock()

    def addTask(self, taskId, fun, *args):
        self.lock.acquire()
        for tk in self.tasks:
            if (taskId is not None) and (tk['task_id'] == taskId):
                self.lock.release()
                return
        task = {'func': fun, 'args': args, 'task_id': taskId}
        self.tasks.append(task)
        self.event.set()
        self.lock.release()

    def start(self):
        if not self.started:
            self.started = True
            self.thread.start()

    def stop(self):
        self.stoped = True
    
    def removeTask(self, taskId):
        self.lock.acquire()
        e = False
        for i in range(len(self.tasks)):
            tk = self.tasks[i]
            if tk['task_id'] == taskId:
                self.tasks.pop(i)
                e = True
                break
        self.lock.release()
        return e

    def clearTasks(self):
        self.lock.acquire()
        self.tasks.clear()
        self.lock.release()

    @staticmethod
    def _run(self):
        while not self.stoped:
            if len(self.tasks) == 0:
                self.event.wait()
                self.event.clear()
            else:
                self.lock.acquire()
                task = self.tasks[0]
                self.tasks.pop(0)
                self.lock.release()
                try:
                    func = task['func']
                    func( *task['args'] )
                except Exception as e:
                    traceback.print_exc()

class TimerThread:
    _num = 0
    def __init__(self, threadName = None) -> None:
        TimerThread._num += 1
        self.tasks = []
        self.stoped = False
        self.started = False
        if not threadName:
            threadName = f"TimerThread-{TimerThread._num}"
        self.name = threadName
        self.thread = threading.Thread(target = TimerThread._run, name = threadName, args=(self,), daemon = True)
        self.lock = threading.Lock()

    # param delay : float seconds
    def addTimerTask(self, taskId, delay, func, *args):
        self.lock.acquire()
        for tk in self.tasks:
            if (taskId is not None) and (tk['task_id'] == taskId):
                self.lock.release()
                return
        tsk = {'func': func, 'args': args, 'delay': time.time() + delay, 'task_id': taskId}
        self.tasks.append(tsk)
        self.lock.release()

    # param intervalTime : float seconds
    def addIntervalTask(self, taskId, intervalTime, func, *args):
        self.lock.acquire()
        for tk in self.tasks:
            if tk['task_id'] == taskId:
                self.lock.release()
                return
        tsk = {'func': func, 'args': args, 'interval': intervalTime, 'delay': time.time() + intervalTime, 'task_id': taskId}
        self.tasks.append(tsk)
        self.lock.release()

    def removeTask(self, taskId):
        self.lock.acquire()
        idx = -1
        for i, tk in enumerate(self.tasks):
            if tk['task_id'] == taskId:
                idx = i
                break
        if idx >= 0:
            self.tasks.pop(idx)
        self.lock.release()
        return idx >= 0

    def start(self):
        if not self.started:
            self.started = True
            self.thread.start()

    def stop(self):
        self.stoped = True
    
    def runOnce(self):
        idx = 0
        while idx < len(self.tasks):
            task = self.tasks[idx]
            if time.time() < task['delay']:
                idx += 1
                continue
            func = task['func']
            func( *task['args'] )
            if 'interval' in task:
                task['delay'] = time.time() + task['interval']
                idx += 1
            else:
                self.tasks.pop(idx)

    @staticmethod
    def _run(self):
        while not self.stoped:
            time.sleep(0.1)
            self.runOnce()

class ThreadPool:
    _ins = None

    def __init__(self) -> None:
        self.threads = [Thread(), Thread(), Thread()]
        self.started = False
        self._taskId = 0

    @staticmethod
    def instance():
        if not ThreadPool._ins:
            ThreadPool._ins = ThreadPool()
        return ThreadPool._ins

    def start(self):
        if self.started == True:
            return
        self.started = True
        for th in self.threads:
            th.start()

    def nextTaskId(self):
        self._taskId += 1
        return self._taskId

    def addTask(self, taskId, func, *args):
        th = None
        for t in self.threads:
            if th is None or len(t.tasks) < len(th.tasks):
                th = t
        th.addTask(taskId, func, *args)

    def addTask_N(self, func, *args):
        self.addTask(self.nextTaskId(), func, *args)

    def addTaskOnThread(self, threadIdx, taskId, func, *args):
        if threadIdx >= 0 and threadIdx < len(self.threads):
            self.threads[threadIdx].addTask(taskId, func, *args)

    def addTaskOnThread_N(self, threadIdx, func, *args):
        self.addTaskOnThread(threadIdx, self.nextTaskId(), func, *args)

    def removeTask(self, taskId):
        for t in self.threads:
            t.removeTask(taskId)

    def clearTasks(self):
        for t in self.threads:
            t.clearTasks()

class Drawer:
    _instance = None

    @staticmethod
    def instance():
        if not Drawer._instance:
            Drawer._instance = Drawer()
        return Drawer._instance

    def __init__(self) -> None:
        self.pens = {}
        self.hbrs = {}
        self.fonts = {}

    def getPen(self, color, style = win32con.PS_SOLID, width = 1):
        if type(color) == int:
            name = f'{style}-{color :06d}-{width}'
            ps = self.pens.get(name, None)
            if not ps:
                ps = self.pens[name] = win32gui.CreatePen(style, width, color)
            return ps
        return None

    def getBrush(self, color):
        if type(color) == int:
            name = f'solid-{color :06d}'
            ps = self.hbrs.get(name, None)
            if not ps:
                ps = self.hbrs[name] = win32gui.CreateSolidBrush(color)
            return ps
        return None

    # weight = 400 is normal, 700 is bold
    def getFont(self, name = '新宋体', fontSize = 14, weight = 0, italic = False, underline = False):
        key = f'{name}:{fontSize}:{weight}:{italic}:{underline}'
        font = self.fonts.get(key, None)
        if not font:
            a = win32gui.LOGFONT()
            a.lfHeight = fontSize
            a.lfFaceName = name
            if weight > 0:
                a.lfWeight = weight
            a.lfItalic = 1 if italic else 0
            a.lfUnderline = 1 if underline else 0
            self.fonts[key] = font = win32gui.CreateFontIndirect(a)
        return font

    def use(self, hdc, obj):
        if obj:
            win32gui.SelectObject(hdc, obj)

    # rgb = int 0xrrggbb  -> 0xbbggrr
    def rgbToColor(self, rgb):
        r = (rgb >> 16) & 0xff
        g = (rgb >> 8) & 0xff
        b = rgb & 0xff
        return (b << 16) | (g << 8) | r

    # return 0xbbggrr
    # h : 0 - 359
    # s, v:  0 - 1.1
    def hsv2rgb(self, h, s, v):
        C = v * s
        hh = h / 60
        ys = int(hh) % 2 + (hh - int(hh))
        X = C * (1.0 - abs(ys - 1.0))
        r, g, b = 0, 0, 0
        if hh >= 0 and hh < 1:
            r, g = C, X
        elif hh >= 1 and hh < 2:
            r, g = X, C
        elif hh >= 2 and hh < 3:
            g, b = C, X
        elif hh >= 3 and hh < 4:
            g, b = X, C
        elif hh >= 4 and hh < 5:
            r, b = X, C
        else:
            r, b = C, X
        m = v - C
        r += m
        g += m
        b += m
        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)
        return r | (g << 8) | (b << 16)

    # rgb = 0xbbggrr
    # return h (0 - 359), s(0 - 1.0), v (0 - 1.0)
    def rgb2hsv(self, rgb):
        def ys(v, k):
            return int(v) % k + (v - int(v))
        r, g, b = rgb & 0xff, (rgb >> 8) & 0xff, (rgb >> 16) & 0xff
        r /= 255
        g /= 255
        b /= 255
        M = max(r, g, b)
        m = min(r, g, b)
        C = M - m
        if C == 0:  h = 0
        elif M == r: h = ys((g - b) / C, 6)
        elif M == g: h= (b - r) / C + 2
        else: h = (r - g) / C + 4
        h *= 60
        if h < 0: h += 360
        v = M
        if v == 0: s = 0
        else: s = C / v
        return round(h), s, v

    def lightness(self, color, d = 0.2):
        h, s, v = self.rgb2hsv(color)
        v = min(v + d, 1)
        color = Drawer.hsv2rgb(h, s, v)
        return color
    
    def darkness(self, color, d = 0.2):
        h, s, v = self.rgb2hsv(color)
        v = max(v - d, 0)
        color = self.hsv2rgb(h, s, v)
        return color

    # color = int(0xbbggrr color)
    def drawLine(self, hdc, sx, sy, ex, ey, color, style = win32con.PS_SOLID, width = 1):
        ps = self.getPen(color, style, width)
        self.use(hdc, ps)
        win32gui.MoveToEx(hdc, sx, sy)
        win32gui.LineTo(hdc, ex, ey)

    # only draw borders
    # rect = list or tuple (left, top, right, bottom)
    def drawRect(self, hdc, rect, borderColor, borderWidth = 1):
        if not rect:
            return
        hbr = self.getBrush(borderColor)
        rc = (rect[0], rect[1], rect[2], rect[1] + borderWidth)
        win32gui.FillRect(hdc, rc, hbr)
        rc = (rect[0], rect[3] - borderWidth, rect[2], rect[3])
        win32gui.FillRect(hdc, rc, hbr)
        rc = (rect[0], rect[1], rect[0] + borderWidth, rect[3])
        win32gui.FillRect(hdc, rc, hbr)
        rc = (rect[2] - borderWidth, rect[1], rect[2], rect[3])
        win32gui.FillRect(hdc, rc, hbr)

    # rect = list or tuple (left, top, right, botton)
    # color = int (0xbbggrr color)
    def fillRect(self, hdc, rect, color):
        if not rect:
            return
        if type(rect) == list:
            rect = tuple(rect)
        hbr = self.getBrush(color)
        win32gui.FillRect(hdc, rect, hbr)
    
    # color1Aplha : 0 ~ 1
    def blendColor(self, color1, color2, color1Aplha : float):
        if color1 is None and color2 is None:
            return None
        if color1 is None:
            return color2
        if color2 is None:
            return color1
        r = int((color1 & 0xff) * color1Aplha + (color2 & 0xff) * (1 - color1Aplha)) & 0xff
        g = (int(((color1 >> 8) & 0xff) * color1Aplha + ((color2 >> 8) & 0xff) * (1 - color1Aplha)) & 0xff) << 8
        b = (int(((color1 >> 16) & 0xff) * color1Aplha + ((color2 >> 16) & 0xff) * (1 - color1Aplha)) & 0xff) << 16
        return r | g | b
    
    # rect = list or tuple (left, top, right, botton)
    # color = int(0xbbggrr color) | None(not set color)
    def drawText(self, hdc, text, rect, color = None, align = win32con.DT_CENTER):
        if text is None or not rect:
            return
        if not isinstance(text, str):
            text = str(text)
        if not isinstance(text, str):
            text = str(text)
        if type(color) == int:
            win32gui.SetTextColor(hdc, color)
        if type(rect) == list:
            rect = tuple(rect)
        if (align & win32con.DT_VCENTER) and (align & win32con.DT_WORDBREAK):
            rect2 = self.calcTextRect(hdc, text, rect, align)
            win32gui.DrawText(hdc, text, len(text), rect2, win32con.DT_WORDBREAK | win32con.DT_LEFT)
        else:
            win32gui.DrawText(hdc, text, len(text), rect, align)

    # return rect, is tuple object, or None
    def calcTextRect(self, hdc, text, srcRect, align):
        if text == None or not srcRect:
            return None
        m, rect = win32gui.DrawText(hdc, text, len(text), srcRect, win32con.DT_CALCRECT | align)
        if m == 0:
            return srcRect
        left = rect[0]
        top = max(rect[1], srcRect[1])
        right = min(rect[2], srcRect[2])
        bottom = min(rect[3], srcRect[3])
        if (align & win32con.DT_VCENTER) and (align & win32con.DT_WORDBREAK):
            topn = ((srcRect[3] - srcRect[1]) - (bottom - top)) // 2
            top = topn + top
            bottom = topn + bottom
        resRect = [left, top, right, bottom]
        if align & win32con.DT_CENTER:
            mx = ((srcRect[2] - srcRect[0]) - (resRect[2] - resRect[0])) // 2
            resRect[0] += mx
            resRect[2] += mx
        elif align & win32con.DT_RIGHT:
            mx = ((srcRect[2] - srcRect[0]) - (resRect[2] - resRect[0]))
            resRect[0] += mx
            resRect[2] += mx
        return tuple(resRect)

    def calcTextSize(self, hdc, text):
        if not text:
            return None
        w, h = 0, 0
        for ln in text.split('\n'):
            tw, th = win32gui.GetTextExtentPoint32(hdc, ln)
            w = max(w, tw)
            h += th
        return (w, h)
            
    # rect = list or tuple (left, top, right, bottom)
    def fillCycle(self, hdc, rect, color):
        if not rect:
            return
        win32gui.SelectObject(hdc, win32gui.GetStockObject(win32con.NULL_PEN))
        self.use(hdc, self.getBrush(color))
        win32gui.Ellipse(hdc, *rect)

    def drawCycle(self, hdc, rect, penColor, penWidth):
        if not rect:
            return
        pen = self.getPen(penColor, win32con.PS_SOLID, penWidth)
        self.use(hdc, pen)
        self.use(hdc, win32gui.GetStockObject(win32con.NULL_BRUSH))
        win32gui.Ellipse(hdc, *rect)

class Layout:
    def __init__(self) -> None:
        self.rect = None # (x, y, width, height)

    def resize(self, x, y, width, height):
        self.rect = (x, y, width, height)

    def setVisible(self, visible):
        pass

    def setWinVisible(self, win, visible):
        if isinstance(win, BaseWindow):
            if visible:
                win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
            else:
                win32gui.ShowWindow(win.hwnd, win32con.SW_HIDE)
        elif type(win) == int:
            # is HWND object
            if visible:
                win32gui.ShowWindow(win, win32con.SW_SHOW)
            else:
                win32gui.ShowWindow(win, win32con.SW_HIDE)
        elif isinstance(win, Layout):
            win.setVisible(visible)
        else:
            print('[Layout.setVisible] unsport win type: ', win)

class GridLayout(Layout):
    # templateRows = 分行, 设置高度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, 'auto', '15%')  fr与auto不能同时出现, auto最多只能有一个
    # templateColumns = 分列, 设置宽度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, '1fr', '2fr' '15%')
    # gaps = (行间隙, 列间隙)  Eg:  (5, 10)
    def __init__(self, templateRows, templateColumns, gaps):
        super().__init__()
        self.templateRows = templateRows
        self.templateColumns = templateColumns
        if not gaps: gaps = (0, 0)
        self.gaps = gaps
        self.winsInfo = {}
        self.layouts = {}

    def setTemplates(self, templateRows, templateColumns):
        self.templateRows = templateRows
        self.templateColumns = templateColumns
    
    # @param style = {  autoFit: True(is default), 
    #            horExpand : int; 0 ( is default) | -1 : right expand all columns |  int(expand num)
    #            verExpand: int;  0 (is default)  | -1 : down expand all rows     |  int(expand num)
    #            priority: 100 (default) 越小越优先计算
    #    }
    # align : left|top|right|bottom
    # @param winType  'HWND', 'Layout', None
    def setContent(self, row, col, win, style = None):
        defaultStyle = {'autoFit' : True, 'horExpand' : 0, 'verExpand' : 0, 'priority': 100}
        if style:
            defaultStyle.update(style)
        self.winsInfo[(row, col)] = {'win' : win, 'style' : defaultStyle, 'content': True, 'position': (row, col)}

    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        self.calcLayout(width, height)
        for k in self.layouts:
            winInfo = self.layouts[k]
            if winInfo['content']:
                self.adjustContentRect(x, y, winInfo)

    def parseTemplate(self, template, wh, gap):
        num = len(template)
        vals = [0] * num
        allTp = 0
        for i, tp in enumerate(template):
            if type(tp) == int:
                vals[i] = tp
                continue
            if type(tp) != str:
                raise Exception('Error: unknow template of ', tp)
            tp = tp.strip()
            if '%' == tp[-1]:
                tp = float(tp[0 : -1]) / 100
                vals[i] = int(wh * tp)
                continue
            if tp[-2 : ] == 'fr':
                tp = int(tp[0 : -2])
                allTp += tp
        used = gap * (num - 1)
        for t in vals: used += t
        less = wh - used
        if less <= 0:
            return vals
        for i, tp in enumerate(template):
            if type(tp) != str:
                continue
            tp = tp.strip()
            if tp[-2 : ] == 'fr':
                tp = int(tp[0 : -2])
                vals[i] = int(tp * less / allTp)
        for i, tp in enumerate(template):
            if type(tp) == str:
                tp = tp.strip()
            if tp == 'auto':
                vals[i] = int(max(less, 0))
                break
        return vals

    def calcLayout(self, width, height):
        self.rows = self.parseTemplate(self.templateRows, height, self.gaps[0])
        self.cols = self.parseTemplate(self.templateColumns, width, self.gaps[1])
        self.layouts.clear()
        self.layouts.update(copy.copy(self.winsInfo))
        ls = []
        for r in range(len(self.rows)):
            for c in range(len(self.cols)):
                k = (r, c)
                ws = self.layouts.get(k)
                if ws: ls.append(ws)
        ls.sort(key = lambda d : d['style']['priority'])
        for item in ls:
            pos = item['position']
            item['rect'] = self.calcContentRect(*pos, item)

    def getHorVerExpandEnd(self, row, col, horExpand, verExpand, fill):
        maxCol = len(self.cols) if horExpand < 0 else min(len(self.cols), col + horExpand + 1)
        maxRow = len(self.rows) if verExpand < 0 else min(len(self.rows), row + verExpand + 1)
        if horExpand > 0 or (horExpand < 0 and verExpand < 0 and horExpand < verExpand): # hor first search
            _, endCol = self.getHorExpandEnd(row, col, horExpand, False)
            endRow = row
            for r in range(row + 1, maxRow, 1):
                _, _c = self.getHorExpandEnd(r, col, horExpand, False)
                if _c != endCol:
                    break
                endRow = r
        else: # ver first search
            endRow, _ = self.getVerExpandEnd(row, col, verExpand, False)
            endCol = col
            for c in range(col + 1, maxCol, 1):
                _r, _ = self.getVerExpandEnd(row, c, verExpand, False)
                if _r != endRow:
                    break
                endCol = c
        if not fill:
            return (endRow, endCol)
        for r in range(row, endRow + 1):
            for c in range(col, endCol + 1):
                if r == row and c == col:
                    continue
                self.layouts[(r, c)] = {'win' : None, 'name': f'expand-hor-ver-item({row, col})', 'content': False}
        return (endRow, endCol)

    def getHorExpandEnd(self, row, col, horExpand, fill):
        maxCol = len(self.cols) if horExpand < 0 else min(len(self.cols), col + horExpand + 1)
        rc = col
        for c in range(col + 1, maxCol, 1):
            k = (row, c)
            if (k in self.layouts):
                return (row, rc)
            if fill:
                self.layouts[k] = {'win' : None, 'name': f'expand-hor-item({row, col})', 'content': False}
            rc = c
        return (row, rc)

    def getVerExpandEnd(self, row, col, verExpand, fill):
        maxRow = len(self.rows) if verExpand < 0 else min(len(self.rows), row + verExpand + 1)
        rr = row
        for r in range(row + 1, maxRow, 1):
            k = (r, col)
            if (k in self.layouts):
                return (rr, col)
            if fill:
                self.layouts[k] = {'win' : None, 'name': f'expand-ver-item({row, col})', 'content': False}
            rr = r
        return (rr, col)

    def calcContentRect(self, row, col, winInfo):
        style = winInfo['style']
        horExpand = style['horExpand']
        verExpand = style['verExpand']
        if horExpand != 0 and verExpand != 0:
            endRow, endCol = self.getHorVerExpandEnd(row, col, horExpand, verExpand, True)
        elif horExpand != 0 and verExpand == 0:
            endRow, endCol = self.getHorExpandEnd(row, col, horExpand, True)
        elif horExpand == 0 and verExpand != 0:
            endRow, endCol = self.getVerExpandEnd(row, col, verExpand, True)
        else:
            endRow, endCol = row, col
        rect = self.calcRect(row, col, endRow, endCol)
        return rect

    def getLeftTop(self, row, col):
        y = int(row * self.gaps[0])
        x = int(col * self.gaps[1])
        for r in range(0, row):
            y += self.rows[r]
        for c in range(0, col):
            x += self.cols[c]
        return (x, y)

    # return (l, t, r, b)
    def calcRect(self, row, col, endRow, endCol):
        left, top = self.getLeftTop(row, col)
        right, bottom = self.getLeftTop(endRow, endCol)
        right += self.cols[endCol]
        bottom += self.rows[endRow]
        return (left, top, right, bottom)

    def adjustContentRect(self, x, y, winInfo):
        style = winInfo['style']
        win = winInfo['win']
        rect = winInfo.get('rect')
        if not win or not rect:
            return
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        x += rect[0]
        y += rect[1]
        
        if isinstance(win, BaseWindow):
            if style['autoFit']:
                win32gui.SetWindowPos(win.hwnd, None, x, y, w, h, win32con.SWP_NOZORDER)
            else:
                win32gui.SetWindowPos(win.hwnd, None, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
            win.invalidWindow()
        elif type(win) == int:
            # is HWND object
            if style['autoFit']:
                win32gui.SetWindowPos(win, None, x, y, w, h, win32con.SWP_NOZORDER)
            else:
                win32gui.SetWindowPos(win, None, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
            win32gui.InvalidateRect(win, None, True)
        elif isinstance(win, Layout):
            if style['autoFit']:
                win.resize(x, y, w, h)
            else:
                if win.rect:
                    *_, w, h = win.rect
                    win.resize(x, y, w, h)
        else:
            print('[GridLayout.adjustContentRect] unsport win type: ', winInfo)

    def setVisible(self, visible):
        for k in self.winsInfo:
            winInfo = self.winsInfo[k]
            win = winInfo['win']
            self.setWinVisible(win, visible)

class AbsLayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.winsInfo = []

    # win = BaseWindow, HWND
    def setContent(self, x, y, win):
        if win:
            self.winsInfo.append({'win': win, 'x' : x, 'y': y})

    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        for it in self.winsInfo:
            self.adjustContentRect(x, y, it)

    def adjustContentRect(self, x, y, winInfo):
        win = winInfo['win']
        x += winInfo['x']
        y += winInfo['y']
        if isinstance(win, BaseWindow):
            win32gui.SetWindowPos(win.hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif type(win) == int:
            win32gui.SetWindowPos(win, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif isinstance(win, Layout):
            win.resize(x, y, win.rect[2], win.rect[3])
        else:
            print('[AbsLayout.adjustContentRect] unsupport win type :', winInfo)

    def setVisible(self, visible):
        for winInfo in self.winsInfo:
            win = winInfo['win']
            self.setWinVisible(win, visible)

class Cardayout(Layout):
    def __init__(self) -> None:
        super().__init__()
        self.winsInfo = []
        self.curVisibleIdx = -1

    def addContent(self, win):
        ws = {'win': win}
        self.winsInfo.append(ws)
        self.setWinVisible(win, False)
    
    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        for it in self.winsInfo:
            self.adjustContentRect(it, x, y, width, height)

    def adjustContentRect(self, winInfo, x, y, width, height):
        win = winInfo['win']
        if isinstance(win, BaseWindow):
            win32gui.SetWindowPos(win.hwnd, None, x, y, width, height, win32con.SWP_NOZORDER)
        elif type(win) == int:
            win32gui.SetWindowPos(win, None, x, y, width, height, win32con.SWP_NOZORDER)
        elif isinstance(win, Layout):
            win.resize(x, y, width, height)
        else:
            print('[Cardayout.adjustContentRect] unsupport win type :', winInfo)

    def setVisible(self, visible):
        if not visible:
            for winInfo in self.winsInfo:
                win = winInfo['win']
                self.setWinVisible(win, False)
        else:
            self.showCardByIdx(self.curVisibleIdx)
    
    def showCardByIdx(self, idx):
        if not self.winsInfo:
            return
        if self.curVisibleIdx != idx and self.curVisibleIdx >= 0 and self.curVisibleIdx < len(self.winsInfo):
            win = self.winsInfo[self.curVisibleIdx]['win']
            self.setWinVisible(win, False)
        self.curVisibleIdx = idx
        win = self.winsInfo[idx]['win']
        self.setWinVisible(win, True)

    def showCard(self, win):
        for i, winInfo in enumerate(self.winsInfo):
            if win == winInfo['win']:
                self.showCardByIdx(i)
                break

class FlowLayout(Layout):
    def __init__(self, horItemSpace = 0) -> None:
        super().__init__()
        self.horItemSpace = horItemSpace
        self.winsInfo = []

    # win = BaseWindow, HWND, Layout(must set Layout.rect's width & height )
    # style = { valign: 'top' | 'center' | 'bottom' (default is 'center')
    #           margins: None | (l, t, r, b)
    #         }
    def addContent(self, win, style = None):
        defStyle = {'valign': 'center', 'margins': None}
        if style:
            defStyle.update(style)
        if win:
            self.winsInfo.append({'win': win, 'style': defStyle})
        if not defStyle['margins']:
            defStyle['margins'] = (0, 0, 0, 0)

    def _calcY(self, winInfo, sy, lineHeight):
        dy = 0
        style = winInfo['style']
        margins = style['margins']
        lineHeight -= margins[1] + margins[3]
        if style['valign'].strip() == 'center':
            dy = (lineHeight - winInfo['h']) // 2
        elif style['valign'].strip() == 'top':
            dy = 0
        elif style['valign'].strip() == 'bottom':
            dy = lineHeight - winInfo['h']
        dy += margins[1]
        winInfo['y'] = sy + dy

    def resize(self, x, y, width, height):
        super().resize(x, y, width, height)
        sx = sy = 0
        # calc lineNo and sx
        lineNo = 0
        for it in self.winsInfo:
            style = it['style']
            margins = style['margins']
            w, h = self._getWinSize(it)
            it['w'] = w
            it['h'] = h
            if sx + w + margins[0] > width:
                #sy +=  self.lineHeight
                lineNo += 1
                sx = 0
            it['lineNo'] = lineNo
            it['x'] = sx + margins[0]
            sx += w + self.horItemSpace + margins[0] + margins[2]
        # calc line height, & y
        rows = []
        for i in range(len(self.winsInfo) + 1):
            it = self.winsInfo[i] if i < len(self.winsInfo) else None
            if rows and (it is None or rows[0]['lineNo'] != it['lineNo']):
                lv = map(lambda x : x['h'] + x['style']['margins'][1] + x['style']['margins'][3], rows)
                lineHeight  = max(lv)
                for r in rows:
                    self._calcY(r, sy, lineHeight)
                rows.clear()
                sy += lineHeight
            rows.append(it)
        # adjust x, y
        for it in self.winsInfo:
            self.adjustContentPositon(x + it['x'], y + it['y'], it)

    def _getWinSize(self, winInfo):
        win = winInfo['win']
        if isinstance(win, Layout):
            return win.rect[2], win.rect[3]
        if isinstance(win, BaseWindow):
            hwnd = win.hwnd
        elif type(win) == int:
            hwnd = win
        if not hwnd:
            return (0, 0)
        rc = win32gui.GetWindowRect(hwnd)
        return rc[2] - rc[0], rc[3] - rc[1]

    def adjustContentPositon(self, x, y, winInfo):
        win = winInfo['win']
        if isinstance(win, BaseWindow):
            win32gui.SetWindowPos(win.hwnd, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif type(win) == int:
            win32gui.SetWindowPos(win, None, x, y, 0, 0, win32con.SWP_NOSIZE | win32con.SWP_NOZORDER)
        elif isinstance(win, Layout):
            win.resize(x, y, win.rect[2], win.rect[3])
        else:
            print('[FlowLayout.adjustContentRect] unsupport win type :', winInfo)

    def setVisible(self, visible):
        for winInfo in self.winsInfo:
            win = winInfo['win']
            self.setWinVisible(win, visible)


# listeners : DbClick = {src, x, y, row, data(row data), model(all data)}
#             RowEnter = {src, row, data, model}
#             SelectRow = {src, row(-1: 没有选中行), oldRow, data, model}
#             DragEnd = {src, fromRow, toRow, rowData, data}
class TableWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x333333
        self.css['headerBgColor'] = 0xc3c3c3
        self.css['headerBorderColor'] = 0x888888
        self.css['headerTextColor'] = 0x333333
        self.css['cellBorder'] = 0xc0c0c0
        self.css['selBgColor'] = 0xf0a0a0 # 0xEAD6D6 #0xf0a0a0
        self.paddings = (2, 0, 2, 0) # cell default paddings

        self.enableDrag = False
        self.draging = False
        self.lButtonDown = False
        self.dragRow = -1
        self.dragToRow = -1

        self.enableCellSelect = False
        self.rowHeight = 24
        self.headHeight = 24
        self.tailHeight = 0
        self.startRow = 0
        self.selRow = -1
        self.selCol = -1
        self.sortHeader = {'header': None, 'state': None} # state: 'ASC' | 'DSC' |  None
        self.sortData = None

        self.data = None # a data array, [{colName1: xx, colName2: xxx}, ...]

        # headers : need set a list , items of
        #    { name:xxx,   '#idx' is index row column 
        #      title:xx,
        #      sortable:True | False (default is False),
        #      default: None | any | function('ASC' | 'DSC')
        #      width : int, fix width
        #      stretch: int, how stretch less width, is part of all stretchs
        #      formater: function(colName, val, rowData) -> return format str data
        #      sorter: function(colName, val, rowData, allDatas, asc:True|False)  -> return sorted value
        #      textAlign: int, win32con.DT_LEFT(is default) | .....
        #      fontSize: 14 (default)
        #      render: function(win, hdc, row, col, colName, value, rowData, rect)  cell-render
        #      paddings : (left, top, right, bottom), cell paddings
        self.headers = None # must be set TODO

    def getData(self):
        if self.sortData != None:
            return self.sortData
        return self.data

    def getHeaders(self):
        return self.headers

    def getHeaderByName(self, headerName):
        if not self.headers:
            return None
        for h in self.headers:
            if h['name'] == headerName:
                return h
        return None

    def getValueOf(self, rowData, colName, row):
        if colName == '#idx':
            return row + 1
        if not rowData:
            return None
        if isinstance(rowData, dict):
            return rowData.get(colName, None)
        return getattr(rowData, colName, None)

    def getColumnWidth(self, colIdx, colName):
        BASE_WIDTH = 40
        w, h = self.getClientSize()
        hd = self.headers[colIdx]
        stretch = int(hd.get('stretch', 0))
        cw = int(hd.get('width', BASE_WIDTH))
        if stretch <= 0:
            return cw

        fixWidth = 0
        frs = 0
        for hd in self.headers:
            st = int(hd.get('stretch', 0))
            if st <= 0:
                rw = int(hd.get('width', BASE_WIDTH))
            else:
                rw = int(hd.get('width', 0))
            fixWidth += rw
            frs += st
        lessWidth = w - fixWidth
        if lessWidth <= 0 or frs <= 0:
            return cw
        stretchWidth = int(lessWidth * stretch / frs)
        return cw + stretchWidth
    
    def getColumnCount(self):
        if not self.headers:
            return 1
        return len(self.headers)

    def getPageSize(self):
        h = self.getClientSize()[1]
        h -= self.headHeight + self.tailHeight
        #maxRowCount = (h + self.rowHeight - 1) // self.rowHeight
        maxRowCount = h // self.rowHeight
        return maxRowCount
    
    # [startIdx, end)
    def getVisibleRange(self):
        datas = self.getData()
        if not datas:
            return (0, 0)
        num = len(datas)
        maxRowCount = self.getPageSize()
        end = self.startRow + maxRowCount
        end = min(end, num)
        return (self.startRow, end)
    
    def getColumnX(self, col):
        if col <= 0 or not self.headers or col >= len(self.headers):
            return 0
        hds = self.headers
        x = 0
        for i in range(col):
            colName = hds[i]['name']
            x += self.getColumnWidth(i, colName)
        return x
    
    def getYOfRow(self, row):
        vr = self.getVisibleRange()
        if not vr:
            return -1
        if row >= vr[0] and row < vr[1]: # is visible
            return self.headHeight + (row - vr[0]) * self.rowHeight
        return -1 # not visible
    
    def _notifyVisibleRangeChanged(self, old = None):
        self.notifyListener(self.Event('VisibleRangeChanged', self, visibleRange = self.getVisibleRange(), old = old))

    def setData(self, data):
        if self.data == data:
            return
        self.data = data
        self.sortData = None
        for k in self.sortHeader:
            self.sortHeader[k] = None
        self.startRow = 0
        self.selRow = -1
        self.selCol = -1
        self._notifyVisibleRangeChanged()

    def setFilterData(self, data):
        if self.sortData == data:
            return
        #self.data = data # no need set
        self.sortData = data
        for k in self.sortHeader:
            self.sortHeader[k] = None
        self.startRow = 0
        self.selRow = -1
        self.selCol = -1
        self._notifyVisibleRangeChanged()

    # delta > 0 : up scroll
    # delta < 0 : down scroll
    def scroll(self, delta):
        sr = self.startRow
        if delta >= 0:
            self.startRow = max(self.startRow - delta, 0)
            self.invalidWindow()
            if self.startRow != sr:
                self._notifyVisibleRangeChanged()
            return
        delta = -delta
        vr = self.getVisibleRange()
        psz = self.getPageSize()
        nn = vr[1] - vr[0]
        if nn <= psz // 2:
            return
        mx = nn - psz // 2
        delta = min(delta, mx)
        self.startRow += delta
        self.invalidWindow()
        if sr != self.startRow:
            self._notifyVisibleRangeChanged()
    
    def showRow(self, row):
        rg = self.getVisibleRange()
        if not rg or row < 0:
            return
        num = rg[1] - rg[0]
        if num == 0:
            return
        if row >= rg[0] and row < rg[1]:
            return # is visible
        if row < rg[0]:
            self.startRow -= rg[0] - row
        elif row >= rg[1]:
            self.startRow += row - rg[1] + 1
        self.invalidWindow()

    def onDraw(self, hdc):
        if not self.headers:
            return
        self.drawHeaders(hdc)
        if not self.data:
            return
        vr = self.getVisibleRange()
        if not vr:
            return
        w = self.getClientSize()[0]
        sy = self.headHeight
        for i in range(vr[1] - vr[0]):
            rc = (0, sy + i * self.rowHeight, w, sy + (i + 1) * self.rowHeight)
            self.drawRow(hdc, i, i + vr[0], rc)
        # draw draging
        if not self.draging or self.dragToRow < 0:
            return
        CW, CH = self.getClientSize()
        if self.dragToRow < len(self.data):
            cy = self.getYOfRow(self.dragToRow)
        else:
            cy = self.getYOfRow(self.dragToRow - 1) + self.rowHeight
        self.drawer.drawLine(hdc, 2, cy, CW - 2, cy, color = 0x00ff00, width = 2)

    def drawSort(self, hdc, rc):
        if not self.sortHeader:
            return
        hd = self.sortHeader['header']
        state = self.sortHeader['state']
        if not hd or not state:
            return
        WH = 6
        sx = rc[2] - 10
        sy = (rc[3] - rc[1] - WH) // 2
        if state == 'ASC':
            pts = [(sx + WH // 2, sy), (sx, sy + WH), (sx + WH, sy + WH)]
        else:
            pts = [(sx, sy), (sx + WH, sy), (sx + WH // 2, sy + WH)]
        hbr = win32gui.CreateSolidBrush(0xff007f)
        win32gui.SelectObject(hdc, hbr)
        win32gui.Polygon(hdc, pts)
        win32gui.DeleteObject(hbr)

    def drawHeaders(self, hdc):
        hds = self.getHeaders()
        if self.headHeight <= 0 or not hds:
            return
        w = self.getClientSize()[0]
        self.drawer.fillRect(hdc, (0, 0, w, self.headHeight), self.css['headerBgColor'])
        rc = [0, 0, 0, self.headHeight]
        for i, hd in enumerate(hds):
            rc[2] += self.getColumnWidth(i, hd['name'])
            if isinstance(self.css['headerBorderColor'], int):
                self.drawer.drawRect(hdc, rc, self.css['headerBorderColor'])
            if self.sortHeader and self.sortHeader['header'] == hd:
                self.drawSort(hdc, rc)
            rc2 = rc.copy()
            rc2[1] = (self.headHeight - 14) // 2
            if 'title' in hd:
                self.drawer.drawText(hdc, hd['title'], rc2, color = self.css['headerTextColor'])
            rc[0] = rc[2]
        
    def drawCell(self, hdc, row, col, colName, value, rowData, rect):
        hd = self.headers[col]
        fs = hd.get('fontSize', self.css['fontSize'])
        self.drawer.use(hdc, self.drawer.getFont(fontSize = fs))
        formater = hd.get('formater', None)
        if formater:
            value = formater(colName, value, rowData)
        cellRender = hd.get('render', None)
        paddings = hd.get('paddings', self.paddings)
        if paddings:
            rect = list(rect)
            for i, p in enumerate(paddings):
                if i < 2: rect[i] += paddings[i]
                else: rect[i] -= paddings[i]
        if cellRender:
            cellRender(self, hdc, row, col, colName, value, rowData, rect)
        else:
            align = hd.get('textAlign', win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            self.drawer.drawText(hdc, value, rect, self.css['textColor'], align = align)

    def drawRow(self, hdc, showIdx, row, rect):
        rc = [0, rect[1], 0, rect[3]]
        self.drawer.drawLine(hdc, rect[0], rect[3], rect[2], rect[3], self.css['cellBorder'])
        hds = self.headers
        if row == self.selRow:
            self.drawer.fillRect(hdc, rect, self.css['selBgColor'])
        datas = self.getData()
        for i in range(len(hds)):
            colName = hds[i]['name']
            rc[2] += self.getColumnWidth(i, colName)
            rowData = datas[row]
            val = self.getValueOf(rowData, colName, row)
            if self.enableCellSelect and row == self.selRow and self.selCol == i:
                # draw cell border
                h, s, v = Drawer.rgb2hsv(self.css['selBgColor'])
                if v <= 0.8: v += 0.2
                else: v -= 0.2
                color = Drawer.hsv2rgb(h, s, v)
                self.drawer.drawRect(hdc, rc, color, 2)
            self.drawCell(hdc, row, i, colName, val, rowData, rc)
            rc[0] = rc[2]

    def drawTail(self, hdc, rect):
        if self.tailHeight <= 0:
            return

    def getHeaderAtX(self, x):
        idx = self.getColAtX(x)
        if idx < 0:
            return None
        return self.headers[idx]

    def getColAtX(self, x):
        if not self.headers or x < 0:
            return -1
        for i, hd in enumerate(self.headers):
            iw = self.getColumnWidth(i, hd['name'])
            if x <= iw:
                return i
            x -= iw
        return -1

    # state = 'ASC | 'DSC' | None | 'Suggest'
    def setSortHeader(self, header, state):
        self.startRow = 0
        self.selRow = self.selCol = -1
        hd = self.sortHeader['header']
        st = self.sortHeader['state']
        if state == 'Suggest':
            if hd == header:
                a = ('ASC', 'DSC', None)
                idx = (a.index(st) + 1) % len(a)
                state = a[idx]
            else:
                state = 'ASC'
        if not header or not state:
            self.sortHeader['header'] = None
            self.sortHeader['state'] = None
            self.sortData = None
            return
        self.sortHeader['header'] = header
        self.sortHeader['state'] = state
        reverse = state == 'DSC'
        if self.data:
            if 'sorter' in header:
                def keyn(rowData):
                    hdn = header['name']
                    return header['sorter'](hdn, rowData.get(hdn, None), rowData, self.data, state == 'ASC')
                self.sortData = sorted(self.data, key = keyn, reverse = reverse)
            else:
                df = header.get('default', None)
                if callable(df):
                    df = df(state)
                def getKey(d):
                    if isinstance(d, dict):
                        val = d.get(header['name'], None) 
                    else:
                        val = getattr(d, header['name'], None)
                    if val is None:
                        val = df
                    return val
                self.sortData = sorted(self.data, key = getKey, reverse = reverse)
        else:
            self.sortData = None
        self._notifyVisibleRangeChanged()

    # get row idx, -2: in header, -3: in tail, -1: in empty rows
    def getRowAtY(self, y):
        datas = self.getData()
        if not datas:
            return -1
        if y <= self.headHeight:
            return -2
        if y >= self.getClientSize()[1] - self.tailHeight:
            return -3
        y -= self.headHeight
        row = y // self.rowHeight + self.startRow
        if row >= 0 and row < len(datas):
            return row
        return -1

    def setSelRow(self, row):
        oldRow = self.selRow
        datas = self.getData()
        if not datas or row < 0 or row >= len(datas):
            if self.selRow != row:
                self.selRow = -1
                self.notifyListener(self.Event('SelectRow',self, row = -1, oldRow = oldRow, data = None, mode = datas))
            return
        if self.selRow != row:
            self.selRow = row
            self.notifyListener(self.Event('SelectRow', self, row = row, oldRow = oldRow, data = datas[row], model = datas))

    def onClick(self, x, y):
        win32gui.SetFocus(self.hwnd)
        row = self.getRowAtY(y)
        if row == -2: # click headers
            hd = self.getHeaderAtX(x)
            if hd and hd.get('sortable', False) == True:
               self.setSortHeader(hd, 'Suggest')
               self.invalidWindow()
        elif row >= 0:
            self.setSelRow(row)
            self.selCol = self.getColAtX(x)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onMouseWheel(self, delta):
        if not self.getData():
            return
        if delta & 0x8000:
            delta = delta - 0xffff - 1
        delta = delta // 120
        self.scroll(delta * 5)
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onKeyDown(self, key):
        datas = self.getData()
        if not datas:
            return False
        if key == win32con.VK_DOWN:
            if self.selRow < len(datas) - 1:
                self.setSelRow(self.selRow + 1)
                self.showRow(self.selRow)
                self.invalidWindow()
            return True
        elif key == win32con.VK_UP:
            if self.selRow > 0:
                self.setSelRow(self.selRow - 1)
                self.showRow(self.selRow)
                self.invalidWindow()
            return True
        elif key == win32con.VK_RETURN:
            if self.selRow >= 0 and datas:
                self.notifyListener(self.Event('RowEnter', self, row = self.selRow, data = datas[self.selRow], model = datas))
            return True
        return False

    def _calcDragToRow(self, y):
        if not self.data:
            return -1
        row = self.getRowAtY(y)
        if row == -1:
            return len(self.data)
        if row < 0:
            return -1
        sy = self.getYOfRow(row)
        if y - sy <= self.rowHeight // 2:
            return row
        return row + 1

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            #win32gui.SetCapture()
            self.lButtonDown = True
            self.draging = False
            self.dragRow = -1
            self.dragToRow = -1
            if self.enableDrag:
                row = self.getRowAtY(y)
                if row >= 0:
                    self.dragRow = row
            return True
        if msg == win32con.WM_MOUSEMOVE:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            if self.lButtonDown and self.enableDrag:
                row = self._calcDragToRow(y)
                if row != self.dragRow and row >= 0:
                    self.draging = True
                    self.dragToRow = row
                    self.invalidWindow()
                    win32gui.UpdateWindow(self.hwnd)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.lButtonDown = False
            row = self._calcDragToRow(y)
            if not self.draging:
                self.onClick(x, y)
            elif self.draging and self.dragRow != row and self.dragRow >= 0 and row >= 0:
                #drag end
                ds = self.getData()
                obj = ds.pop(self.dragRow)
                if self.dragRow < row:
                    ds.insert(row - 1, obj)
                else:
                    ds.insert(row, obj)
                self.invalidWindow()
                self.notifyListener(self.Event('DragEnd', self, fromRow = self.dragRow, toRow = row, rowData = obj, data = ds))
            self.draging = False
            self.dragRow = -1
            self.dragToRow = -1
            self.invalidWindow()
            win32gui.UpdateWindow(self.hwnd)
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            self.onMouseWheel((wParam >> 16) & 0xffff)
            return True
        if msg == win32con.WM_KEYDOWN:
            tg = self.onKeyDown(wParam)
            return tg
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            if row >= 0:
                dx = self.getData()
                self.notifyListener(self.Event('DbClick', self, x = x, y = y, row = row, data = dx[row], model = dx))
            return True
        if msg == win32con.WM_SIZE:
            self._notifyVisibleRangeChanged()
            # go through, no return
        return super().winProc(hwnd, msg, wParam, lParam)


        if not self.data:
            return
        rowNum = self.getRowNum()
        colNum = self.columnCount
        begin, end = self.getVisibleRange()
        for i in range(begin, end):
            idx = i - begin
            colIdx = idx // rowNum
            rowIdx = idx % rowNum
            if colIdx >= colNum:
                continue
            itemData = self.data[i]
            self.drawItemData(hdc, colIdx, rowIdx, i, itemData)
        for i in range(0, colNum):
            self.drawColumnHead(hdc, i)

# listeners : Select = {src, group, groupIdx}
class GroupButton(BaseWindow):
    def __init__(self, groups) -> None:
        super().__init__()
        self.groups = groups
        self.selGroupIdx = -1
    
    # group = int, is group idx or group object
    def setSelGroup(self, group):
        if type(group) == int:
            self.selGroupIdx = group
        win32gui.InvalidateRect(self.hwnd, None, True)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        for i in range(len(self.groups)):
            item = self.groups[i]
            color = 0x00008C if i == self.selGroupIdx else 0x333333
            rc = [int(cw * i), 0,  int((i + 1) * cw), h]
            self.drawer.fillRect(hdc, rc, color)
            self.drawer.drawRect(hdc, rc, 0x202020)
            rc[1] = (h - 16) // 2
            self.drawer.drawText(hdc, item['title'], rc, 0x2fffff)

    def onClick(self, x, y):
        w, h = self.getClientSize()
        cw = w / len(self.groups)
        idx = int(x / cw)
        if self.selGroupIdx == idx:
            return
        self.selGroupIdx = idx
        self.notifyListener(self.Event('Select', self, group = self.groups[idx], groupIdx = idx))
        win32gui.InvalidateRect(self.hwnd, None, True)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)        

# listeners : Click = {src, info}
class Button(BaseWindow):
    # btnInfo = {name: xxx, title: xxx}
    def __init__(self, btnInfo) -> None:
        super().__init__()
        self.css['bgColor'] = 0x333333
        self.css['borderColor'] = 0x202020
        self.css['textColor'] = 0x2fffff
        self.info = btnInfo
    
    def onDraw(self, hdc):
        w, h = self.getClientSize()
        TH = 14
        rc = (0, 0,  w, h)
        rc = (0, (h - TH) // 2,  w, h - (h - TH) // 2)
        self.drawer.drawText(hdc, self.info['title'], rc, self.css['textColor'])
        #w, *_ = win32gui.GetTextExtentPoint32(hdc, ' ')
        #print('Button.onDraw ', w)

    def onClick(self, x, y):
        self.notifyListener(self.Event('Click', self, info = self.info))

    def lightness(self, color):
        h, s, v = self.drawer.rgb2hsv(color)
        if v <= 0.8: v += 0.2
        else: v -= 0.2
        color = self.drawer.hsv2rgb(h, s, v)
        return color

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            hdc = win32gui.GetDC(hwnd)
            bgColor = self.css['bgColor']
            color = self.lightness(bgColor)
            self.css['bgColor'] = color
            self._draw(hdc)
            self.css['bgColor'] = bgColor
            win32gui.ReleaseDC(hwnd, hdc)
            time.sleep(0.05)
            self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class Label(BaseWindow):
    def __init__(self, text = None) -> None:
        super().__init__()
        self.text = text
        self.css['textAlign'] = win32con.DT_SINGLELINE | win32con.DT_VCENTER # win32con.DT_LEFT (0)
    
    def setText(self, text):
        if text == None:
            self.text = ''
        elif isinstance(text, str):
            self.text = text
        else:
            self.text = str(text)
        self.invalidWindow()
    
    def onDraw(self, hdc):
        w, h = self.getClientSize()
        TH = 14
        rc = (0, 0,  w, h)
        rc = (0, (h - TH) // 2,  w, h - (h - TH) // 2)
        self.drawer.drawText(hdc, self.text, rc, self.css['textColor'], self.css['textAlign'])

# listeners : Checked = {src, info, checked}
class CheckBox(BaseWindow):
    _groups = {}

    # info = {name: xx, value:xx, title:'', checked: True|False }
    def __init__(self, info : dict) -> None:
        super().__init__()
        self.info = info
        name = info.get('name', None)
        if not name:
            return
        ls = CheckBox._groups.get(name, None)
        if not ls:
            ls = CheckBox._groups[name] = []
        ls.append(self)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        BRD = 2
        WH = self.css['fontSize'] // 2 * 2
        sy = (h - WH) // 2
        rc = (0, sy, WH, sy + WH)
        self.drawer.drawRect(hdc, rc, 0x606060, borderWidth = BRD)
        
        if self.isChecked():
            SP = 4
            iwh = WH - SP * 2
            sy = rc[1] + SP
            sx = rc[0] + SP
            rc2 = (sx, sy, sx + iwh, sy + iwh)
            self.drawer.fillRect(hdc, rc2, 0x338833)

        if 'title' in self.info:
            rc3 = (rc[2] + 3, (h - WH) // 2, w, h)
            self.drawer.drawText(hdc, self.info['title'], rc3, self.css['textColor'], win32con.DT_LEFT)

    def isChecked(self):
        return self.info and self.info.get('checked', False)

    def setChecked(self, checked : bool):
        if self.isChecked() == checked:
            return
        if checked:
            name = self.info.get('name', None)
            self.uncheckedGroup(name)
        self.info['checked'] = checked
        self.invalidWindow()
        self.notifyListener(self.Event('Checked', self, info = self.info, checked = checked))

    def uncheckedGroup(self, name):
        if not name:
            return
        ls = CheckBox._groups[name]
        for c in ls:
            if c != self:
                c.setChecked(False)

    def _destroy(self):
        if not self.info:
            return
        name = self.info.get('name', None)
        if not name:
            return
        ls = CheckBox._groups.get(name, None)
        if not ls:
            return
        ls.remove(self)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            self.setChecked(not self.isChecked())
            return True
        if msg == win32con.WM_DESTROY:
            self._destroy() # no return any
        return super().winProc(hwnd, msg, wParam, lParam)

class PopupWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ownerHwnd = None
        self.css['borderColor'] = 0xaaaaaa
        self.destroyOnHide = True
        self.hideOnInactive = True

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP, className = 'STATIC', title = ''):
        #style = win32con.WS_POPUP | win32con.WS_CHILD
        self.ownerHwnd = parentWnd
        super().createWindow(parentWnd, rect, style, className, title)
        win32gui.SetWindowPos(self.hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    def updateOwner(self, ownerHwnd):
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_HWNDPARENT, ownerHwnd)

    # x, y is screen pos
    def show(self, x = None, y = None):
        if self.ownerHwnd:
            ownerRect = win32gui.GetWindowRect(self.ownerHwnd)
        else:
            ownerRect = (0, 0, 0, 0)
        if x == None:
            x = ownerRect[0]
        if y == None:
            y = ownerRect[3]
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetActiveWindow(self.hwnd)

    def move(self, x, y):
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)

    def resize(self, w, h):
        win32gui.SetWindowPos(self.hwnd, 0, 0, 0, w, h, win32con.SWP_NOZORDER | win32con.SWP_NOMOVE)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
        if self.destroyOnHide and self.hwnd:
            hwnd = self.hwnd
            self.hwnd = None
            win32gui.DestroyWindow(hwnd)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_ACTIVATE:
            ac = wParam & 0xffff
            if ac == win32con.WA_INACTIVE and self.hideOnInactive:
                self.hide()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class NoActivePopupWindow(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.ownerHwnd = None
        self.css['borderColor'] = 0xaaaaaa
        self.destroyOnHide = True
        self.hook = None
        self.user32 = ctypes.windll.user32

    # x, y is screen pos
    def show(self, x, y):
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)

    def setVisible(self, visible : bool):
        if not win32gui.IsWindow(self.hwnd):
            return
        if visible:
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNOACTIVATE)
        else:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def move(self, x, y):
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def resize(self, w, h):
        win32gui.SetWindowPos(self.hwnd, 0, 0, 0, w, h, win32con.SWP_NOZORDER | win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE)

    def msgLoop(self):
        msg = ctypes.wintypes.MSG()
        ref = ctypes.byref(msg)
        hasPressed = False
        while self.hwnd and win32gui.IsWindowVisible(self.hwnd):
            br = self.user32.GetMessageA(ref, 0, 0, 0)
            if not br:
                break
            if msg.message >= win32con.WM_MOUSEFIRST and msg.message <= win32con.WM_MOUSELAST:
                if msg.message == win32con.WM_LBUTTONDOWN:
                    hasPressed = True
                xy = win32gui.GetCursorPos()
                rc = win32gui.GetWindowRect(self.hwnd)
                isIn = win32gui.PtInRect(rc, xy)
                if not isIn:
                    if not hasPressed and msg.message == win32con.WM_LBUTTONUP:
                        continue
                    if msg.message != win32con.WM_MOUSEMOVE:
                        self.hide()
                        break
                    else:
                        continue
            self.user32.TranslateMessage(ref)
            self.user32.DispatchMessageA(ref)

    def hide(self):
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
        if self.destroyOnHide and self.hwnd:
            hwnd = self.hwnd
            self.hwnd = None
            win32gui.DestroyWindow(hwnd)

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.ownerHwnd = parentWnd
        st = win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE, st | win32con.WS_EX_NOACTIVATE)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEACTIVATE:
            return win32con.MA_NOACTIVATE
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners : Select = {src, item, model}
class PopupMenu(NoActivePopupWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['selBgColor'] = 0xdfd0d0
        self.css['textColor'] = 0x222222
        self.css['disableTextColor'] = 0x909090
        self.destroyOnHide = True
        self.css['paddings'] = (20, 0, 20, 0)
        self.SEPRATOR_HEIGHT = 2
        self.ARROW_HEIGHT = 10
        self.VISIBLE_MAX_ITEM = 15 # 最大显示的个数
        self.model = None  # [{title:xx, name:xx }, ...]   title = LINE 表示分隔线
        self.rowHeight = 24
        self.minItemWidth = 150 # 最小宽度
        self.selIdx = -1
        self.startIdx = 0 # 开始显示的idx

    # x, y is screen position
    # model = [ {
    #       title: xx | LINE,
    #       enable: True(is default) | False,
    #       checked: None(not checkable) | True | False
    #       render: function(menu, hdc, rect, menu-item)
    #       sub-menu: function(menu-item) | a model(list object)
    #   }, ...
    # ]
    # listener = function(evtName, evtInfo, args)
    # return PopupMenu object
    @staticmethod
    def create(parentHwnd, model):
        menu = PopupMenu()
        menu.createWindow(parentHwnd, (0, 0, 1, 1), title = 'I-PopupMenu')
        menu.setModel(model)
        return menu

    def setModel(self, model):
        self.model = model

    def show(self, x = None, y = None):
        if not self.hwnd:
            return
        self.selIdx = -1
        w, h = self.calcSize()
        if self.ownerHwnd:
            ownerRect = win32gui.GetWindowRect(self.ownerHwnd)
        else:
            ownerRect = (0, 0, 0, 0)
        if x == None:
            x = ownerRect[0]
        if y == None:
            y = ownerRect[3]
        SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        if x + w > SW:
            if x >= w:
                x = x - w
            else:
                x = SW - w
        if y + h > SH - 40:
            y = SH - h - 40
        self.resize(w, h)
        super().show(x, y)
        self.msgLoop()
    
    def calcSize(self):
        w, h = 0, 0
        if not self.model:
            return (self.minItemWidth, self.rowHeight)
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        # calc max height
        si = max(self.startIdx, 0)
        for i in range(si, min(si + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            h += self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
        # calc max width
        for i in range(0, len(self.model)):
            m = self.model[i]
            title = m.get('title', '')
            sz = win32gui.GetTextExtentPoint32(hdc, title)
            w = max(w, sz[0])
        w += self.css['paddings'][0] + self.css['paddings'][2]
        win32gui.ReleaseDC(self.hwnd, hdc)
        if len(self.model) > self.VISIBLE_MAX_ITEM:
            h += self.ARROW_HEIGHT * 2
        w = max(self.minItemWidth, w)
        return (w, h)
    
    def getItemIdxAt(self, y):
        if not self.model:
            return -1
        sy = 0
        for i in range(self.startIdx, min(self.startIdx + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            ih = self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
            if y >= sy and y < sy + ih:
                return i
            sy += ih
        return -1

    def scroll(self, delta):
        if not self.model or len(self.model) <= self.VISIBLE_MAX_ITEM:
            return
        idx = self.startIdx - delta
        if delta < 0:
            maxIdx = len(self.model) - self.VISIBLE_MAX_ITEM
            idx = min(idx, maxIdx)
        else:
            idx = max(idx, 0)
        if self.startIdx == idx:
            return
        self.startIdx = idx
        w, h = self.calcSize()
        self.resize(w, h)
        self.invalidWindow()

    def drawUpDownArrow(self, hdc):
        if not self.model:
            return
        w, h = self.getClientSize()
        cx = w // 2
        AW, AH = 4, 4
        self.drawer.use(hdc, self.drawer.getBrush(0x333333))
        self.drawer.use(hdc, win32gui.GetStockObject(win32con.NULL_PEN))
        if self.startIdx > 0:
            sy = 2
            pts = [(cx, sy), (cx + AW, AH + sy), (cx - AW, AH + sy)]
            win32gui.Polygon(hdc, pts)
        if len(self.model) > self.startIdx + self.VISIBLE_MAX_ITEM:
            sy = h - AH - 3
            pts = [(cx, sy + AH), (cx + AW, sy), (cx - AW, sy)]
            win32gui.Polygon(hdc, pts)

    def drawRightArrow(self, hdc, rect):
        AW, AH = 6, 8
        self.drawer.use(hdc, self.drawer.getBrush(0x333333))
        self.drawer.use(hdc, win32gui.GetStockObject(win32con.NULL_PEN))
        sy = (rect[3] - rect[1] - AH) // 2 + rect[1]
        sx = rect[2] + (self.css['paddings'][2] - AW) // 2
        pts = [(sx, sy), (sx + AW, AH // 2 + sy), (sx, AH + sy)]
        win32gui.Polygon(hdc, pts)

    def onDraw(self, hdc):
        super().onDraw(hdc)
        if not self.model:
            return
        self.drawUpDownArrow(hdc)
        w = self.getClientSize()[0]
        sy = 0 if len(self.model) <= self.VISIBLE_MAX_ITEM else self.ARROW_HEIGHT
        rc = [self.css['paddings'][0], sy, w - self.css['paddings'][2], sy]
        for i in range(self.startIdx, min(self.startIdx + self.VISIBLE_MAX_ITEM, len(self.model))):
            m = self.model[i]
            title = m.get('title', '')
            ih = self.SEPRATOR_HEIGHT if title == 'LINE' else self.rowHeight
            rc[3] += ih
            if i == self.selIdx and title != 'LINE':
                rcs = [0, rc[1], w, rc[3]]
                self.drawer.fillRect(hdc, rcs, self.css['selBgColor'])
            if title == 'LINE':
                self.drawer.drawLine(hdc, rc[0], rc[1], rc[2], rc[1], 0x999999, width = 1)
            else:
                color = self.css['textColor'] if m.get('enable', True) else self.css['disableTextColor']
                if m.get('render', None):
                    render = m['render']
                    render(self, hdc, rc[ : ], m)
                else:
                    checked = m.get('checked', None)
                    if checked == False or checked == True:
                        self.drawCheckBox(hdc, m, rc)
                    self.drawer.drawText(hdc, title, rc, color, win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_WORDBREAK)
                    if m.get('sub-menu', None):
                        self.drawRightArrow(hdc, rc[ : ])
            rc[1] = rc[3]
    
    def drawCheckBox(self, hdc, item, rowRect):
        checked = item.get('checked', None)
        if not isinstance(checked, bool):
            return
        box = [0, rowRect[1], self.css['paddings'][0], rowRect[3]]
        BOX_IN = 6
        x = ((box[2] - box[0]) - BOX_IN) // 2
        y = ((box[3] - box[1]) - BOX_IN) // 2
        boxIn = [box[0] + x, box[1] + y, box[0] + x + BOX_IN, box[1] + y + BOX_IN]
        BOX_OUT = 12
        x = ((box[2] - box[0]) - BOX_OUT) // 2
        y = ((box[3] - box[1]) - BOX_OUT) // 2
        boxOut = [box[0] + x, box[1] + y, box[0] + x + BOX_OUT, box[1] + y + BOX_OUT]
        self.drawer.drawRect(hdc, boxOut, 0x606060)
        if checked:
            self.drawer.fillRect(hdc, boxIn, 0x338833)
    
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_MOUSEMOVE:
            y = (lParam >> 16) & 0xffff
            idx = self.getItemIdxAt(y)
            if self.selIdx != idx and idx >= 0 and self.model[idx].get('title', '') != 'LINE':
                self.selIdx = idx
                self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONUP:
            y = (lParam >> 16) & 0xffff
            idx = self.getItemIdxAt(y)
            if idx < 0:
                self.hide()
                return True
            item = self.model[idx]
            if idx >= 0 and item.get('title', '') != 'LINE' and item.get('enable', True):
                if item.get('sub-menu', None):
                    sub = item['sub-menu']
                    if callable(sub): sub = sub(item)
                    for it in sub:
                        if not it.get('name', None):
                            it['name'] = item.get('name', None)
                    self.setModel(sub)
                    w, h = self.calcSize()
                    self.resize(w, h)
                    self.invalidWindow()
                    return True
                self.hide()
                if item.get('checked', None) != None:
                    item['checked'] = not item['checked']
                self.notifyListener(self.Event('Select', self, item = item, model = self.model))
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = delta - 0xffff - 1
            delta = delta // 120
            self.scroll(delta)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners :  Select = {src, day: int, sday: YYYY-MM-DD}
class DatePopupWindow(NoActivePopupWindow):
    TOP_HEADER_HEIGHT = 40
    PADDING = 10

    def __init__(self) -> None:
        super().__init__()
        self.preBtnRect = None
        self.nextBtnRect = None
        self.curSelDay = None # datetime.date object
        self.setSelDay(None)

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        W, H = 250, 240
        super().createWindow(parentWnd, (0, 0, W, H), style, className, title)
        BTN_W, BTN_H = 20, 20
        self.nextBtnRect = (W - BTN_W - 5, 10, W - 5, 30)
        self.preBtnRect = (W - BTN_W * 2 - 15, 10, W - BTN_W - 15, 30)

    # x, y is screen pos
    def show(self, x, y):
        super().show(x, y)
        self.setSelDay(self.curSelDay)

    def onDraw(self, hdc):
        self.drawHeader(hdc, self.curYear, self.curMonth)
        self.drawContent(hdc, self.curYear, self.curMonth)

    def drawHeader(self, hdc, year, month):
        title = f'{year}年{month}月'
        self.drawer.drawText(hdc, title, (0, 10, 100, self.TOP_HEADER_HEIGHT), 0xcccccc)
        #self.drawer.drawRect2(hdc, self.nextBtnRect, 0x444444)
        #self.drawer.drawRect2(hdc, self.preBtnRect, 0x444444)
        self.drawer.drawText(hdc, '<<', self.preBtnRect, 0xcccccc)
        self.drawer.drawText(hdc, '>>', self.nextBtnRect, 0xcccccc)

    def drawContent(self, hdc, year, month):
        today = datetime.date.today()
        days = self.calcDays(year, month)
        sy = self.TOP_HEADER_HEIGHT
        w, h = self.getClientSize()
        ITEM_WIDTH = (w - self.PADDING * 2) / 7
        ITEM_HEIGHT = (h - self.TOP_HEADER_HEIGHT - self.PADDING) / ((len(days) + 6) // 7 + 1)
        XQ = ['一', '二', '三', '四', '五', '六' ,'日']
        XQ.extend(days)
        days = XQ
        DPY = (ITEM_HEIGHT - 14) // 2
        sy = self.TOP_HEADER_HEIGHT
        for i, day in enumerate(days):
            if i > 0 and i % 7 == 0:
                sy += ITEM_HEIGHT
            c = i % 7
            if not day:
                continue
            rc = [self.PADDING + int(c * ITEM_WIDTH), int(sy), self.PADDING + int(c * ITEM_WIDTH + ITEM_WIDTH), int(sy + ITEM_HEIGHT)]
            if self.curSelDay == day:
                self.drawer.drawRect(hdc, rc, 0x00aa00)
            rc[1] += int(DPY)
            txt = day if type(day) == str else str(day.day)
            if isinstance(day, datetime.date) and day == today:
                self.drawer.drawText(hdc, txt, rc, 0x5555ff)
            else:
                self.drawer.drawText(hdc, txt, rc, 0xcccccc)

    def calcDays(self, year, month):
        weeky, num = calendar.monthrange(year, month)
        days = []
        for i in range(0, weeky):
            days.append(None)
        for i in range(0, num):
            d = datetime.date(year, month, i + 1)
            days.append(d)
        return days

    def nextMonth(self):
        m = self.curMonth + 1
        if m == 13:
            self.curMonth = 1
            self.curYear += 1
        else:
            self.curMonth = m
        self.invalidWindow()

    def prevMonth(self):
        m = self.curMonth - 1
        if m == 0:
            self.curMonth = 12
            self.curYear -= 1
        else:
            self.curMonth = m
        self.invalidWindow()

    def getDayOf(self, x, y):
        w, h = self.getClientSize()
        if x < self.PADDING or x > w - self.PADDING or y < self.TOP_HEADER_HEIGHT or y >= h - self.PADDING:
            return None
        days = self.calcDays(self.curYear, self.curMonth)
        ITEM_WIDTH = int((w - self.PADDING * 2) / 7)
        ITEM_HEIGHT = int((h - self.TOP_HEADER_HEIGHT - self.PADDING) / ((len(days) + 6) // 7 + 1))
        if y <= self.TOP_HEADER_HEIGHT + ITEM_HEIGHT:
            return None # in XQ title
        x -= self.PADDING
        y -= self.TOP_HEADER_HEIGHT + ITEM_HEIGHT
        r = y // ITEM_HEIGHT
        c = x // ITEM_WIDTH
        idx = r * 7 + c
        if idx >=0 and idx < len(days):
            return days[idx]
        return None

    # day = int | datetime.date | str
    def setSelDay(self, day):
        curDay = self.curSelDay
        if not day:
            day = datetime.date.today()
            self.curSelDay = None
            self.curYear = day.year
            self.curMonth = day.month
            return
        if type(day) == datetime.date:
            self.curSelDay = day
        elif type(day) == int:
            self.curSelDay = datetime.date(day // 10000, day // 100 % 100, day % 100)
        elif type(day) == str:
            day = int(day.replace('-', ''))
            self.curSelDay = datetime.date(day // 10000, day // 100 % 100, day % 100)
        self.curYear = self.curSelDay.year
        self.curMonth = self.curSelDay.month

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            if x >= self.preBtnRect[0] and x < self.preBtnRect[2] and y >= self.preBtnRect[1] and y < self.preBtnRect[3]:
                self.prevMonth()
            elif x >= self.nextBtnRect[0] and x < self.nextBtnRect[2] and y >= self.nextBtnRect[1] and y < self.nextBtnRect[3]:
                self.nextMonth()
            else:
                day = self.getDayOf(x, y)
                if day:
                    self.setSelDay(day)
                    self.hide()
                    iday = self.curSelDay.year * 10000 + self.curSelDay.month * 100 + self.curSelDay.day
                    sday = self.curSelDay.strftime('%Y-%m-%d')
                    self.notifyListener(self.Event('Select', self, day = iday, sday = sday))
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners :  Select = {src, day: int, sday: YYYY-MM-DD }
class DatePicker(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['textColor'] = 0xcccccc
        self.popWin = DatePopupWindow()
        self.popWin.destroyOnHide = False
        self.popWin.addListener(self.onSelDayChanged, 'DatePopupWindow')

    # day = int | datetime.date | str
    def setSelDay(self, selDay):
        self.popWin.setSelDay(selDay)
        self.invalidWindow()
    
    def getSelDay2(self):
        return self.popWin.curSelDay # datetime.date, may be None

    def getSelDay(self):
        day = self.popWin.curSelDay
        if not day:
            return None
        return f'{day.year}-{day.month :02d}-{day.day :02d}'
    
    def getSelDayInt(self):
        day = self.popWin.curSelDay
        if not day:
            return None
        return day.year * 10000 +  day.month * 100 + day.day

    def onSelDayChanged(self, event, args):
        if args != 'DatePopupWindow' and event.name != 'Select':
            return
        self.invalidWindow()
        event.src = self
        self.notifyListener(event)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.popWin.createWindow(self.hwnd)

    def onDraw(self, hdc):
        w, h = self.getClientSize()
        self.drawer.drawRect(hdc, (0, 0, w, h), self.css['textColor'])
        if not self.getSelDay():
            return
        sy = (h - 2 - 14) // 2
        self.drawer.drawText(hdc, self.getSelDay(), (0, sy, w - 1, h), self.css['textColor'])

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            if win32gui.IsWindowVisible(self.popWin.hwnd):
                self.popWin.hide()
            else:
                rc = win32gui.GetWindowRect(self.hwnd)
                self.popWin.show(rc[0], rc[3])
                self.popWin.msgLoop()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class BaseEditor(BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self._caretCreated = False
        self._caretVisible = False
        self._caretHeight = 0

    def showCaret(self):
        if (not self._caretCreated) or self._caretVisible or (win32gui.GetFocus() != self.hwnd):
            return
        self._caretVisible = True
        win32gui.ShowCaret(self.hwnd)

    def hideCaret(self):
        if (not self._caretCreated) or (not self._caretVisible):
            return
        self._caretVisible = False
        win32gui.HideCaret(self.hwnd)
    
    def setCaretPos(self, x, y):
        if not self._caretCreated:
            return
        win32gui.SetCaretPos(x, y)

    def onSetFocus(self):
        pass
    
    def onKillFocus(self):
        pass
    
    # is ctrl shift key is pressed
    def getKeyState(self, vk):
        return (win32api.GetKeyState(vk) & 0x80000000) != 0

    def copyToClipboard(self, text):
        if not text:
            return False
        pyperclip.copy(text)

        # copy digit text fail, fix by : pip install pywin32 == 301 把pywin32版本降到301
        #win32clipboard.OpenClipboard(None)
        #win32clipboard.EmptyClipboard() # 写入清必须清空，得到剪贴板占有权
        #win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
        #win32clipboard.CloseClipboard()
        return True

    def copyFromClipboard(self, fmt = win32con.CF_TEXT):
        #b = ctypes.windll.user32.OpenClipboard(self.hwnd)
        #if not b:
        #    return ''
        #fmt = 0
        #fmt = ctypes.windll.user32.EnumClipboardFormats(fmt)
        #v = ctypes.windll.user32.GetClipboardData(fmt)

        #ctypes.windll.user32.CloseClipboard()
        val = pyperclip.paste()
        #win32clipboard.OpenClipboard(None)
        #val = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
        #win32clipboard.CloseClipboard()
        return val

    @property
    def lineHeight(self):
        return self.css['fontSize'] + 6
    
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SETFOCUS:
            self._caretCreated = False
            self._caretVisible = False
            ok = win32gui.CreateCaret(hwnd, None, 2, self.lineHeight)
            if ok != 0: # success
                self._caretCreated = True
                self._caretHeight = self.lineHeight
            self.onSetFocus()
            return True
        if msg == win32con.WM_KILLFOCUS:
            if self._caretCreated:
                if self._caretVisible:
                    win32gui.HideCaret(self.hwnd)
                win32gui.DestroyCaret()
            self._caretCreated = False
            self._caretVisible = False
            self.onKillFocus()
            return True
        if msg == win32con.WM_IME_STARTCOMPOSITION:
            return True
        if msg == win32con. WM_IME_COMPOSITION:
            GCS_COMPSTR = 8
            if lParam & GCS_COMPSTR:
                himc = ctypes.windll.imm32.ImmGetContext(hwnd)
                buf = ctypes.create_string_buffer(100)
                ctypes.windll.imm32.ImmGetCompositionStringA(himc, GCS_COMPSTR, buf, 100)
                ctypes.windll.imm32.ImmReleaseContext(hwnd)
                sval = b''
                for i in range(100):
                    if buf[i] != b'\x00': sval += buf[i]
                    else:break
                #print('sval =', sval.decode('utf-8'))
            return False # can't return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners : PressEnter = {src, text}
#             PressTab = {src, text}
class Editor(BaseEditor):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x202020
        self.css['placeHolderColor'] = 0xb0b0b0
        self.css['borderColor'] = 0xdddddd
        self.css['selBgColor'] = 0xf0c0c0
        self.css['paddings'] = (3, 0, 3, 0)
        self.scrollX = 0 # always <= 0
        self.text = ''
        self.insertPos = 0
        self.selRange = None # (beginPos, endPos)
        self.placeHolder = None # str text
        self.popupTipModel = None

    # model = [ {title: xxx, value? : , ...}, ... ] , same as PopupMenu model
    # and post Event(self, PressEnter, text: , value ?: , ...)
    def setPopupTip(self, model : list):
        self.popupTipModel = model

    # tip = int | str | dict
    #      int -> tip model' idx
    #      str -> tip model' name
    #      dict -> tip model' item
    def setSelectItem(self, tip):
        if not self.popupTipModel:
            return
        item = None
        if isinstance(tip, int):
            idx = tip
            if idx < 0 or idx > len(self.popupTipModel):
                return
            item = self.popupTipModel[idx]
        elif isinstance(tip, str):
            for k in self.popupTipModel:
                if k['name'] == tip:
                    item = k
                    break
        elif isinstance(tip, dict):
            item = tip
        if not item:
            return
        self.setText(item['title'])
        self.invalidWindow()
        newEvt = self.Event('PressEnter', self, text = item['title'], **item)
        self.notifyListener(newEvt)

    def setText(self, text):
        self.scrollX = 0
        self.selRange = None
        if not text:
            text = ''
        if not isinstance(text, str):
            text = str(text)
        self.text = text
        self.setInsertPos(0)

    def getText(self):
        return self.text
    
    def setInsertPos(self, pos):
        self.insertPos = pos
        rc = self.getCaretRect()
        if not rc:
            return
        self.setCaretPos(rc[0], rc[1])
        self.showCaret()

    def makePosVisible(self, pos):
        if not self.text or pos < 0:
            return
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        W, H = self.getClientSize()
        W -= self.css['paddings'][2]
        stw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text[0 : pos])
        px = self.scrollX + stw + self.css['paddings'][0]
        if px < self.css['paddings'][0]:
            self.scrollX += self.css['paddings'][0] - px
        elif px > W - self.css['paddings'][2]:
            self.scrollX -= px - (W - self.css['paddings'][2])
        win32gui.ReleaseDC(self.hwnd, hdc)
        self.invalidWindow()

    def setSelRange(self, beginPos, endPos):
        if not self.text:
            self.selRange = None
            return
        beginPos = max(beginPos, 0)
        endPos = max(endPos, 0)
        beginPos = min(beginPos, len(self.text))
        endPos = min(endPos, len(self.text))
        if beginPos == endPos:
            self.selRange = None
            return
        if beginPos > endPos:
            beginPos, endPos = endPos, beginPos
        self.selRange = (beginPos, endPos)

    def deleteSelRangeText(self):
        if not self.selRange:
            return
        txt = self.text[0 : self.selRange[0]]
        txt2 = self.text[self.selRange[1] : ]
        self.text = txt + txt2
        ip = self.insertPos
        if self.insertPos >= self.selRange[0] and self.insertPos < self.selRange[1]:
            ip = self.selRange[0]
        elif self.insertPos >= self.selRange[1]:
            ip = self.insertPos - (self.selRange[1] - self.selRange[0])
        if not self.text:
            ip = 0
            self.scrollX = 0
        self.selRange = None
        self.setInsertPos(ip)
        self.invalidWindow()

    def getXAtPos(self, pos):
        if not self.text or pos < 0:
            return self.css['paddings'][0]
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        tw, *_ = win32gui.GetTextExtentPoint32(hdc, self.text[0 : pos])
        x = self.scrollX + tw + self.css['paddings'][0]
        win32gui.ReleaseDC(self.hwnd, hdc)
        return x
    
    def getPosAtX_Text(self, text, x):
        if not text:
            return 0
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        pos = -1
        totalX = 0
        for i in range(0, len(text)):
            cw, *_ = win32gui.GetTextExtentPoint32(hdc, text[i])
            if x <= totalX + cw // 2:
                pos = i
                break
            totalX += cw
        win32gui.ReleaseDC(self.hwnd, hdc)
        if pos >= 0:
            return pos
        return len(text)

    def getPosAtX(self, x):
        hdc = win32gui.GetDC(self.hwnd)
        pos = self.getPosAtX_Text(self.text, x - self.css['paddings'][0])
        win32gui.ReleaseDC(self.hwnd, hdc)
        return pos
    
    def onChar(self, key):
        if key < 32 or key == 127:
            return
        ch = chr(key)
        self.insertText(ch)

    def insertText(self, text):
        if not text:
            return
        text = text.replace('\r', '').replace('\n', '')
        if self.selRange:
            self.deleteSelRangeText()
        if not self.text:
            self.text = text
        else:
            self.text = self.text[0 : self.insertPos] + text + self.text[self.insertPos : ]
        pos = self.insertPos + len(text)
        self.makePosVisible(pos)
        self.setInsertPos(pos)

    # (left, top, right, bottom)
    def getCaretRect(self):
        cs = self.getClientSize()
        if not cs:
            return None
        W, H = cs
        lh = self.css['fontSize'] + 4
        x = self.getXAtPos(self.insertPos)
        y = (H - lh ) // 2
        return (x, y, x, y + lh)

    def onDraw(self, hdc):
        if not self.text:
            if self.placeHolder:
                rc = (0, 0, *self.getClientSize())
                self.drawer.drawText(hdc, self.placeHolder, rc, color=self.css['placeHolderColor'], align=win32con.DT_LEFT|win32con.DT_SINGLELINE|win32con.DT_VCENTER)
            return
        W, H = self.getClientSize()
        lh = self.css['fontSize']
        y = (H - lh) // 2
        if self.selRange:
            sx = self.getXAtPos(self.selRange[0])
            ex = self.getXAtPos(self.selRange[1])
            src = (sx, y - 2, ex, y + lh + 2)
            self.drawer.fillRect(hdc, src, self.css['selBgColor'])
        rc = (self.scrollX + self.css['paddings'][0], y, W - self.css['paddings'][2], y + lh)
        self.drawer.drawText(hdc, self.text, rc, color=self.css['textColor'], align = win32con.DT_LEFT)

    def _showPopupTip(self):
        if not self.popupTipModel:
            return
        def onCc(evt, args):
            self.setSelectItem(evt.item)
        menu = PopupMenu.create(self.hwnd, self.popupTipModel)
        menu.css['paddings'] = (0, 0, 20, 0)
        menu.addNamedListener('Select', onCc)
        rc = win32gui.GetWindowRect(self.hwnd)
        menu.minItemWidth = rc[2] - rc[0]
        menu.show(rc[0], rc[3])

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            x = lParam & 0xffff
            pos = self.getPosAtX(x)
            self.selRange = None
            self.setInsertPos(pos)
            self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            if wParam & win32con.MK_LBUTTON:
                x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
                pos = self.getPosAtX(x)
                self.setSelRange(self.insertPos, pos)
                self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            if self.text:
                self.setSelRange(0, len(self.text))
                self.invalidWindow()
                return True
            elif self.popupTipModel:
                self._showPopupTip()
                return True
            # else : NO return
        if msg == win32con.WM_IME_CHAR or msg == win32con.WM_CHAR:
            self.onChar(wParam)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_LEFT:
                if self.insertPos > 0:
                    pos = self.insertPos - 1
                    self.selRange = None
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
            elif wParam == win32con.VK_RIGHT:
                if self.text and self.insertPos < len(self.text):
                    pos = self.insertPos + 1
                    self.selRange = None
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
            elif wParam == win32con.VK_DELETE:
                if self.selRange:
                    self.deleteSelRangeText()
                elif self.text and self.insertPos < len(self.text):
                    self.text = self.text[0 : self.insertPos] + self.text[self.insertPos + 1 : ]
                    self.selRange = None
                    self.makePosVisible(self.insertPos)
                    self.setInsertPos(self.insertPos)
                    self.invalidWindow()
            elif wParam == win32con.VK_BACK:
                if self.selRange:
                    self.deleteSelRangeText()
                elif self.text and self.insertPos > 0:
                    self.text = self.text[0 : self.insertPos - 1] + self.text[self.insertPos : ]
                    pos = self.insertPos - 1
                    self.selRange = None
                    self.makePosVisible(pos)
                    self.setInsertPos(pos)
                    self.invalidWindow()
            elif wParam == win32con.VK_RETURN:
                self.notifyListener(self.Event('PressEnter', self, text = self.text))
            elif wParam == win32con.VK_TAB:
                self.notifyListener(self.Event('PressTab', self, text = self.text))
            elif wParam == win32con.VK_HOME:
                self.selRange = None
                self.makePosVisible(0)
                self.setInsertPos(0)
                self.invalidWindow()
            elif wParam == win32con.VK_END:
                self.selRange = None
                pos = len(self.text)
                self.makePosVisible(pos)
                self.setInsertPos(pos)
                self.invalidWindow()
            elif wParam == ord('V') and self.getKeyState(win32con.VK_CONTROL):
                txt = self.copyFromClipboard()
                self.insertText(txt)
            elif wParam == ord('C') and self.getKeyState(win32con.VK_CONTROL) and self.selRange and self.text:
                txt = self.text[self.selRange[0] : self.selRange[1]]
                self.copyToClipboard(txt)
            elif wParam == ord('X') and self.getKeyState(win32con.VK_CONTROL) and self.selRange and self.text:
                txt = self.text[self.selRange[0] : self.selRange[1]]
                if self.copyToClipboard(txt):
                    self.deleteSelRangeText()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners :
class MutiEditor(BaseEditor):
    class Pos:
        def __init__(self, row, col) -> None:
            self.row = row
            self.col = col
        def __eq__(self, oth) -> bool:
            return self.row == oth.row and self.col == oth.col
        def __ne__(self, oth) -> bool:
            return self.row != oth.row or self.col != oth.col
        def __gt__(self, oth):
            if self.row > oth.row:
                return True
            if self.row == oth.row:
                return self.col > oth.col
            return False
        def __ge__(self, oth):
            if self.row > oth.row:
                return True
            if self.row == oth.row:
                return self.col >= oth.col
            return False
        def __lt__(self, oth):
            return oth > self
        def __le__(self, oth):
            return oth >= self

    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x202020
        self.css['borderColor'] = 0xdddddd
        self.css['selBgColor'] = 0xf0c0c0
        self.css['lineNoBgColor'] = 0xE0E0E0
        self.css['lineNoTextColor'] = 0xD3B291
        self.css['paddings'] = (5, 0, 5, 0)
        self.startRow = 0
        self.lines = [] # items of { text,  }
        self.insertPos = None # Pos object
        self.selRange = None # (begin-Pos, end-Pos)
        self.readOnly = False
        self.hasLineNo = False

    def setText(self, text):
        self.selRange = None
        self.lines.clear()
        if not text:
            text = ''
        if not isinstance(text, str):
            text = str(text)
        ls = text.splitlines()
        for l in ls:
            self.lines.append({'text': l})
        #self.setInsertPos(MutiEditor.Pos(0, 0))

    def getText(self):
        txt = ''
        for ln in self.lines:
            txt += ln['text'] + '\n'
        if not txt:
            return txt
        return txt[0 : -1]

    def getLineAttr(self, row, attrName):
        if row >= len(self.lines):
            return None
        ln = self.lines[row]
        if attrName == 'text':
            return ln.get(attrName, '')
        return ln.get(attrName, None)
    
    def makePosVisible(self, pos):
        if not pos or pos.row < 0 or pos.row >= len(self.lines):
            return
        mrn = self.getMaxRowNum()
        if pos.row < self.startRow:
            diff = self.startRow - pos.row
            self.scroll(-diff)
        elif pos.row >= self.startRow + mrn:
            diff = pos.row - (self.startRow + mrn - 1)
            self.scroll(diff)

    def setInsertPos(self, pos):
        self.adjustPos(pos)
        self.insertPos = pos
        if not pos: # clear pos
            self.hideCaret()
        else:
            self.makePosVisible(self.insertPos)
            rc = self.getCaretRect()
            self.setCaretPos(rc[0], rc[1])
            self.showCaret()

    def adjustPos(self, pos):
        if not pos:
            return
        if not self.lines:
            pos.row = 0
            pos.col = 0
            return
        pos.row = min(pos.row, len(self.lines) - 1)
        lt = self.lines[pos.row]['text']
        pos.col = min(pos.col, len(lt))

    def setSelRange(self, beginPos, endPos):
        self.adjustPos(beginPos)
        self.adjustPos(endPos)
        if not beginPos or not endPos:
            self.selRange = None
            return
        self.selRange = (beginPos, endPos)

    def getSelRange(self, sorted):
        if not self.hasSelRange():
            return None
        b, e = self.selRange
        if sorted and b > e:
            return (e, b)
        return self.selRange

    def hasSelRange(self):
        if not self.selRange:
            return False
        return self.selRange[0] != self.selRange[1]

    def getSelRangeText(self):
        if not self.hasSelRange():
            return ''
        b, e = self.getSelRange(True)
        txt = ''
        if b.row == e.row:
            ln = self.getLineAttr(b.row, 'text')
            return ln[b.col : e.col]
        for r in range(b.row, e.row + 1):
            ln = self.getLineAttr(r, 'text')
            if r == b.row:
                txt += ln[b.col : ] + '\n'
            elif r == e.row:
                txt += ln[0 : e.col]
            else:
                txt += ln + '\n'
        return txt

    def updateRowText(self, row, text):
        self.lines[row]['text'] = text
        self.lines[row]['modified'] = True

    def deleteSelRangeText(self):
        if not self.hasSelRange():
            return
        b, e = self.getSelRange(True)
        self.setSelRange(None, None)
        if b.row == e.row:
            if b.row >= len(self.lines):
                return
            ln = self.lines[b.row]['text']
            self.updateRowText(b.row, ln[0 : b.col] + ln[e.col : ])
            return
        for r in range(b.row, e.row + 1):
            if r == b.row:
                self.updateRowText(r, self.lines[r]['text'][0 : b.col])
            elif r == e.row:
                self.updateRowText(r, self.lines[r]['text'][e.col : ])
        for r in range(e.row - 1, b.row, -1):
            self.lines.pop(r)

    def getXAtPos(self, pos):
        if not self.lines or not pos:
            return self.css['paddings'][0]
        if pos.row > len(self.lines):
            return self.css['paddings'][0]
        line = self.lines[pos.row]['text']
        if pos.col > len(line):
            return self.css['paddings'][0]
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        tw, *_ = win32gui.GetTextExtentPoint32(hdc, line[0 : pos.col])
        x = tw + self.css['paddings'][0]
        win32gui.ReleaseDC(self.hwnd, hdc)
        return x

    def getYAtPos(self, pos):
        if not self.lines or not pos:
            return 0
        row = min(pos.row, len(self.lines) - 1)
        return (row - self.startRow) * self.lineHeight
    
    def getColAtX_Text(self, text, x):
        if not text:
            return 0
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        pos = -1
        sx = 0
        for i in range(0, len(text)):
            cw, *_ = win32gui.GetTextExtentPoint32(hdc, text[i])
            if x <= sx + cw // 2:
                pos = i
                break
            if i == len(text) - 1:
                pos = i + 1
                break
            sx += cw
        win32gui.ReleaseDC(self.hwnd, hdc)
        if pos >= 0:
            return pos
        return len(text)

    def getColAtX(self, row, x):
        if not self.lines or row < 0 or row >= len(self.lines):
            return 0
        pos = self.getColAtX_Text(self.lines[row]['text'], x - self.css['paddings'][0])
        return pos
    
    def getRowAtY(self, y):
        if y <= 0:
            return 0
        row = y // self.lineHeight
        row += self.startRow
        if not self.lines:
            return 0
        row = min(row, len(self.lines) - 1)
        return row

    def getPosAtXY(self, x, y):
        row = self.getRowAtY(y)
        col = self.getColAtX(row, x)
        return MutiEditor.Pos(row, col)
    
    def onChar(self, key):
        if key < 32:
            return
        ch = chr(key)
        self.insertText(ch)
        self.invalidWindow()

    def insertText(self, text):
        if not text:
            return
        ip = self.insertPos
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.deleteSelRangeText()
            ip = sr[0]
        if not self.lines:
            self.lines.append({'text': ''})
        if not ip:
            raise Exception('[insertText] Not find insert pos')
        row = ip.row
        col = ip.col
        for ch in text:
            if ch == '\r':
                continue
            if ch == '\n':
                ln = self.lines[row]['text']
                self.updateRowText(row, ln[0 : col])
                row += 1
                self.lines.insert(row, {'text': ''})
                self.updateRowText(row, ln[col : ])
                col = 0
            else:
                tx = self.lines[row]['text']
                self.updateRowText(row, tx[0 : col] + ch + tx[col : ])
                col += 1
        self.setInsertPos(MutiEditor.Pos(row, col))

    # (left, top, right, bottom)
    def getCaretRect(self):
        lh = self.lineHeight #self.css['fontSize'] + 4
        x = self.getXAtPos(self.insertPos)
        sy = self.getYAtPos(self.insertPos)
        dy = (self.lineHeight - lh) // 2
        y = sy + dy
        return (x, y, x, y + lh)

    def left(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.setSelRange(None, None)
            self.setInsertPos(sr[0])
        else:
            self.setSelRange(None, None)
            if self.insertPos and self.insertPos.col > 0:
                self.insertPos.col -= 1
                self.setInsertPos(self.insertPos)
        self.invalidWindow()

    def right(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.setSelRange(None, None)
            self.setInsertPos(sr[1])
        else:
            self.setSelRange(None, None)
            if self.insertPos and self.insertPos.row < len(self.lines):
                line = self.lines[self.insertPos.row]['text']
                if self.insertPos.col < len(line):
                    self.insertPos.col += 1
                    self.setInsertPos(self.insertPos)
        self.invalidWindow()

    def up(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.setSelRange(None, None)
            self.setInsertPos(sr[0])
        else:
            self.setSelRange(None, None)
            if self.insertPos and self.insertPos.row > 0:
                self.insertPos.row -= 1
                self.setInsertPos(self.insertPos)
        self.invalidWindow()

    def down(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.setSelRange(None, None)
            self.setInsertPos(sr[1])
        else:
            self.setSelRange(None, None)
            if self.insertPos and self.insertPos.row < len(self.lines) - 1:
                self.insertPos.row += 1
                self.setInsertPos(self.insertPos)
        self.invalidWindow()

    def delete(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.deleteSelRangeText()
            self.invalidWindow()
            self.setInsertPos(sr[0])
            return
        self.setSelRange(None, None)
        if self.insertPos and self.insertPos.row < len(self.lines):
            row, col = self.insertPos.row, self.insertPos.col
            line = self.lines[row]['text']
            if col < len(line):
                self.updateRowText(row, line[0 : col] + line[col + 1 : ])
            else:
                if row + 1 < len(self.lines):
                    self.updateRowText(row, line + self.lines[row + 1]['text'])
                    self.lines.pop(row + 1)
            self.setInsertPos(self.insertPos)
            self.invalidWindow()

    def back(self):
        if self.hasSelRange():
            sr = self.getSelRange(True)
            self.deleteSelRangeText()
            self.invalidWindow()
            self.setInsertPos(sr[0])
            self.invalidWindow()
            return
        if not self.insertPos or self.insertPos.row >= len(self.lines):
            return
        row, col = self.insertPos.row, self.insertPos.col
        if col <= 0 and row <= 0:
            return
        line = self.lines[row]['text']
        if col == 0:
            ln = len(self.lines[row - 1]['text'])
            self.updateRowText(row - 1, self.lines[row - 1]['text'] + line)
            self.lines.pop(row)
            self.setInsertPos(MutiEditor.Pos(row - 1, ln))
        else:
            self.updateRowText(row, line[0 : col - 1] + line[col : ])
            self.setInsertPos(MutiEditor.Pos(row, col - 1))
        self.invalidWindow()

    def enter(self):
        if self.hasSelRange():
            return
        self.insertText('\n')
        self.invalidWindow()

    def getMaxRowNum(self):
        W, H = self.getClientSize()
        return H // self.lineHeight
    
    def scroll(self, delta):
        mrn = self.getMaxRowNum()
        si = self.startRow
        if delta > 0:
            LESS = int(mrn * 0.5)
            maxRowIdx = len(self.lines) - LESS
            if maxRowIdx < 0:
                maxRowIdx = 0
            self.startRow = min(self.startRow + delta, maxRowIdx)
        else:
            self.startRow = max(self.startRow + delta, 0)
        self.invalidWindow()
        diff = self.startRow - si
        if not self.insertPos or not self._caretCreated or diff == 0:
            return
        # check insertPos visible
        if self.insertPos.row < self.startRow or self.insertPos.row >= self.startRow + mrn:
            self.hideCaret()
        else:
            rc = self.getCaretRect()
            self.setCaretPos(rc[0], rc[1])
            self.showCaret()

    def drawSelRange(self, hdc):
        if not self.hasSelRange():
            return
        W, H = self.getClientSize()
        b, e = self.getSelRange(True)
        if b.row == e.row:
            sy = self.getYAtPos(b)
            sx = self.getXAtPos(b)
            ex = self.getXAtPos(e)
            rc = (sx, sy, ex, sy + self.lineHeight)
            self.drawer.fillRect(hdc, rc, self.css['selBgColor'])
            return
        for r in range(b.row, e.row + 1):
            pos = MutiEditor.Pos(r, 0)
            sy = self.getYAtPos(pos)
            if r == b.row:
                rc = (self.getXAtPos(b), sy, W, sy + self.lineHeight)
            elif r == e.row:
                rc = (self.getXAtPos(pos), sy, self.getXAtPos(e), sy + self.lineHeight)
            else:
                rc = (self.getXAtPos(pos), sy, W, sy + self.lineHeight)
            self.drawer.fillRect(hdc, rc, self.css['selBgColor'])

    def drawRow(self, hdc, row, rc):
        self.drawer.drawText(hdc, self.lines[row]['text'], rc, color = self.css['textColor'], align = win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        lh = self.css['fontSize']
        if self.hasLineNo:
            pds = self.css['paddings']
            lineNoRect = (0, pds[1], pds[0], H)
            self.drawer.fillRect(hdc, lineNoRect, self.css['lineNoBgColor'])
        self.drawSelRange(hdc)
        for r in range(self.startRow, len(self.lines)):
            pos = MutiEditor.Pos(r, 0)
            sy = self.getYAtPos(pos)
            sx = self.getXAtPos(pos)
            rc = (sx, sy, W, sy + self.lineHeight)
            self.drawRow(hdc, r, rc)
            if self.hasLineNo:
                lineNo = r - self.startRow + 1
                rc2 = (lineNoRect[0], rc[1], lineNoRect[2], rc[3])
                self.drawer.drawText(hdc, f'{lineNo :>3d}', rc2, color = self.css['lineNoTextColor'], align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def onSetFocus(self):
        super().onSetFocus()
        #if not self.insertPos:
        #    return
        #x = self.getXAtPos(self.insertPos)
        #y = self.getYAtPos(self.insertPos)
        #self.setCaretPos(x, y)
        #self.showCaret()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            pos = self.getPosAtXY(x, y)
            self.setSelRange(pos, pos)
            self.setInsertPos(pos)
            self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            if wParam & win32con.MK_LBUTTON:
                x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
                pos = self.getPosAtXY(x, y)
                if self.selRange:
                    self.setSelRange(self.selRange[0], pos)
                self.setInsertPos(pos)
                self.invalidWindow()
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            col = self.getColAtX(row, x)
            self.setSelRange(MutiEditor.Pos(row, 0), MutiEditor.Pos(row, col))
            self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = delta - 0xffff - 1
            delta = delta // 120
            self.scroll(- delta * 3)
            win32gui.InvalidateRect(self.hwnd, None, True)
        if msg == win32con.WM_CHAR or msg == win32con.WM_IME_CHAR:
            if not self.readOnly:
                self.onChar(wParam)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_LEFT:
                self.left()
            elif wParam == win32con.VK_RIGHT:
                self.right()
            elif wParam == win32con.VK_DELETE and (not self.readOnly):
                self.delete()
            elif wParam == win32con.VK_BACK and (not self.readOnly):
                self.back()
            elif wParam == win32con.VK_UP:
                self.up()
            elif wParam == win32con.VK_DOWN:
                self.down()
            elif wParam == win32con.VK_RETURN:
                self.enter()
            elif wParam == win32con.VK_TAB:
                for i in range(4):
                    self.onChar(ord(' '))
            elif wParam == win32con.VK_HOME:
                self.setSelRange(None, None)
                if self.insertPos and self.insertPos.row < len(self.lines):
                    row = self.insertPos.row
                    self.setInsertPos(MutiEditor.Pos(row, 0))
                self.invalidWindow()
            elif wParam == win32con.VK_END:
                self.setSelRange(None, None)
                if self.insertPos and self.insertPos.row < len(self.lines):
                    row = self.insertPos.row
                    self.setInsertPos(MutiEditor.Pos(row, len(self.lines[row]['text'])))
                self.invalidWindow()
            elif wParam == ord('A') and self.getKeyState(win32con.VK_CONTROL):
                if self.lines:
                    lastLine = self.lines[-1]['text']
                    self.setSelRange(MutiEditor.Pos(0, 0), MutiEditor.Pos(len(self.lines) - 1, len(lastLine)))
                    self.invalidWindow()
            elif wParam == ord('V') and self.getKeyState(win32con.VK_CONTROL):
                    txt = self.copyFromClipboard()
                    self.insertText(txt)
                    self.invalidWindow()
            elif wParam == ord('C') and self.getKeyState(win32con.VK_CONTROL):
                txt = self.getSelRangeText()
                self.copyToClipboard(txt)
            elif wParam == ord('X') and self.getKeyState(win32con.VK_CONTROL):
                txt = self.getSelRangeText()
                if self.copyToClipboard(txt):
                    self.deleteSelRangeText()
                    self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)   

    def onSetFocus(self):
        if not self.insertPos:
            self.insertPos = MutiEditor.Pos(0, 0)
        rc = self.getCaretRect()
        self.setCaretPos(rc[0], rc[1])
        super().onSetFocus()

    def enableLineNo(self):
        self.hasLineNo = True
        pds = self.css['paddings']
        self.css['paddings'] = (40, pds[1], pds[2], pds[3])

# listeners : Select = {src, item: xxx }
class ComboBox(Editor):
    def __init__(self) -> None:
        super().__init__()
        self.css['paddings'] = (0, 0, 20, 0)
        self.selIdx = -1
        self.editable = False

    def getSelectItem(self):
        if not self.popupTipModel:
            return None
        if self.selIdx < 0 or self.selIdx >= len(self.popupTipModel):
            return None
        return self.popupTipModel[self.selIdx]
    
    # tip = int | str | dict
    #      int -> tip model' idx
    #      str -> tip model' name
    #      dict -> tip model' item
    def setSelectItem(self, tip):
        oldSelIdx = self.selIdx
        self.selIdx = -1
        if not self.popupTipModel:
            return
        item = None
        if isinstance(tip, int):
            idx = tip
            if idx < 0 or idx > len(self.popupTipModel):
                return
            item = self.popupTipModel[idx]
        elif isinstance(tip, str):
            for k in self.popupTipModel:
                if k['name'] == tip:
                    item = k
                    break
        elif isinstance(tip, dict):
            item = tip
        if not item:
            return
        for i, d in enumerate(self.popupTipModel):
            if d == item:
                self.selIdx = i
                break
        self.setText(item['title'])
        self.invalidWindow()
        if self.selIdx != oldSelIdx:
            newEvt = self.Event('Select', self, **item)
            self.notifyListener(newEvt)

    def onDraw(self, hdc):
        super().onDraw(hdc)
        W, H = self.getClientSize()
        rc = (W - self.css['paddings'][2], 1, W - 1, H - 1)
        self.drawer.fillRect(hdc, rc, 0xDEC4B0)
        CW = 6
        x = (rc[2] - rc[0] - CW) // 2 + rc[0]
        y = (rc[3] - rc[1] - CW) // 2 + rc[1]
        pts = [(x, y), (x + CW, y), (x + CW // 2, y + CW)]
        ARROW_COLOR = 0xFF901E
        self.drawer.use(hdc, self.drawer.getPen(ARROW_COLOR))
        self.drawer.use(hdc, self.drawer.getBrush(ARROW_COLOR))
        win32gui.Polygon(hdc, pts)

    def winProc(self, hwnd, msg, wParam, lParam):
        if not self.editable:
            if msg == win32con.WM_LBUTTONDOWN or msg == win32con.WM_MOUSEMOVE or msg == win32con.WM_LBUTTONDBLCLK \
                or msg == win32con.WM_IME_CHAR or msg == win32con.WM_CHAR or msg == win32con.WM_KEYDOWN:
                return True
        if msg == win32con.WM_LBUTTONUP:
            W, H = self.getClientSize()
            x = lParam & 0xffff
            if x >= W - self.css['paddings'][2] or not self.editable:
                self._showPopupTip()
                return True
            # no return
        return super().winProc(hwnd, msg, wParam, lParam)

class ThsShareMemory:
    POS_CODE = 0
    POS_SEL_DAY = 1
    POS_MARK_DAY = 2

    _thread = None

    def __init__(self, create : bool = False, name = 'Ths-Share-window-Memory') -> None:
        self.create = create
        self.listeners = []
        self.shm = None
        self._name = name
        self.open()

    @classmethod
    def instance(cls):
        ins = getattr(cls, '_ins_', None)
        if not ins:
            ins = ThsShareMemory()
            setattr(cls, '_ins_', ins)
            ins.open()
        return ins

    # func = function(code, day)
    def addListener(self, name, func):
        if not name or not func:
            return
        for lt in self.listeners:
            if lt['name'] == name:
                return
        self.listeners.append({'name' : name, 'func' : func})

    def notifyListener(self, curCode, curDay):
        for ls in self.listeners:
            func = ls['func']
            func(curCode, curDay)

    def onListenThread(self):
        curDay, curCode = 0, 0
        while True:
            time.sleep(0.5)
            day = self.readSelDay()
            code = self.readCode()
            if day == 0 or code == 0:
                continue
            if day != curDay or code != curCode:
                curDay = day
                curCode = code
                self.notifyListener(curCode, curDay)

    def open(self):
        if self.shm:
            return
        c = self.create
        if self._open(c):
            return
        self._open(not c)
        
    def _open(self, create):
        try:
            if create:
                SZ = 512
                self.shm = shared_memory.SharedMemory(self._name, True, size = SZ)
                buf = self.shm.buf.cast('i')
                for i in range(SZ // 4):
                    buf[i] = 0
                buf.release()
            else:
                self.shm = shared_memory.SharedMemory(self._name, False)
            if not ThsShareMemory._thread:
                ThsShareMemory._thread = threading.Thread(target = self.onListenThread, daemon = True)
                ThsShareMemory._thread.start()
            return True
        except Exception as e:
            #print('ThsShareMemory.open exception: ', e)
            return False

    def writeCode(self, code):
        if not self.shm:
            return
        try:
            code = int(code)
        except:
            return
        buf = self.shm.buf.cast('i')
        buf[self.POS_CODE] = code
        buf.release()

    # return int
    def readCode(self):
        if not self.shm:
            return
        buf = self.shm.buf.cast('i')
        code = buf[0]
        buf.release()
        return code
    
    def writeSelDay(self, day):
        self._writeDay(day, self.POS_SEL_DAY)

    # return int
    def readSelDay(self):
        return self._readDay(self.POS_SEL_DAY)
    
    def writeMarkDay(self, day):
        self._writeDay(day, self.POS_MARK_DAY)
        
    # return int
    def readMarkDay(self):
        return self._readDay(self.POS_MARK_DAY)
    
    def _writeDay(self, day, pos):
        if not self.shm:
            return
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        buf = self.shm.buf.cast('i')
        buf[pos] = day
        buf.release()

    def _readDay(self, pos):
        if not self.shm:
            return 0
        buf = self.shm.buf.cast('i')
        day = buf[pos]
        buf.release()
        return day

    def writeIntData(self, data, pos):
        if not self.shm:
            return
        buf = self.shm.buf.cast('i')
        buf[pos] = data
        buf.release()

    def readIntData(self, pos):
        if not self.shm:
            return 0
        buf = self.shm.buf.cast('i')
        data = buf[pos]
        buf.release()
        return data

    def close(self):
        if not self.shm:
            return
        self.shm.close()

    def unlink(self):
        if not self.shm:
            return
        self.shm.unlink()

def testGridLayout():
    class TestMain(BaseWindow):
        def __init__(self, gl) -> None:
            super().__init__()
            self.gl = gl

        def onDraw(self, hdc):
            win32gui.SetTextColor(hdc, 0)
            colors = (0xadef22, 0xfeaefe, 0x329f3c, 0xef89ca, 0x9efacc)
            for i, k in enumerate(self.gl.winsInfo):
                pos = gl.winsInfo[k]['position']
                ws = gl.layouts[pos]
                style = ws['style']
                rc = ws['rect']
                self.drawer.fillRect(hdc, rc, colors[i % len(colors)])
                txt = f'{pos} \n horExpand={style["horExpand"]} \n verExpand={style["verExpand"]}'
                self.drawer.drawText(hdc, txt, rc)

            for k in self.gl.layouts:
                ly = self.gl.layouts[k]
                if ly and not ly['content']:
                    x, y = self.gl.getLeftTop(*k)
                    #self.drawer.fillRect(hdc, (x, y, x + 10, y + 10), 0x0000ff)

    rowtp = (50, '20%', '1fr', '2fr', 60, 50, 100)
    coltp = (100, 'auto', '30%', '10%', 60, '10%')
    gl = GridLayout(rowtp, coltp, (5, 10))
    gl.setContent(0, 0, None, style={})
    gl.setContent(0, 1, None, style={'horExpand' : 0})
    gl.setContent(0, 2, None, style={'horExpand' : 0})
    gl.setContent(0, 3, None, style={'horExpand' : 0})
    gl.setContent(0, 5, None, style={'horExpand' : 0})
    
    gl.setContent(2, 0, None, style={'verExpand' : -1})
    gl.setContent(1, 1, None, style={'horExpand' : -1, 'verExpand' : -1})
    gl.setContent(6, 1, None, style={'horExpand' : 1, 'priority': 30})
    gl.setContent(2, 3, None, style={'priority': 30})
    gl.setContent(3, 2, None, style={'priority': 30})
    gl.setContent(5, 4, None, style={'priority': 30})

    main = TestMain(gl)
    main.createWindow(None, (0, 0, 1002, 602), win32con.WS_VISIBLE | win32con.WS_POPUPWINDOW)
    rc = win32gui.GetClientRect(main.hwnd)
    print(rc)
    gl.resize(*rc)
    win32gui.PumpMessages()

def testPopMenu():
    def back(e, ei):
        PopupMenu.show(300, 100, model, menuSel)

    def menuSel(en, ei):
        print(en, ei)

    btn = Button({'title' : 'Hello'})
    btn.createWindow(None, (0, 0, 200, 100), win32con.WS_VISIBLE | win32con.WS_OVERLAPPEDWINDOW)
    model = [{'title': 'Hello 1 你好呀不' },  {'title': 'LINE'}, {'title': 'Hello 2'},
        {'title': 'Hello 3要'}, {'title': 'Hello 4'}, {'title': 'Hello 5'},
        {'title': 'Hello 6 kdil'},  {'title': 'LINE'}, {'title': 'Hello 7 KIL'}]
    btn.addListener(back, None)

if __name__ == '__main__':
    #testGridLayout()
    #testPopMenu()
    label = Label('Hello')
    label.createWindow(None, (300, 200, 300, 300), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE)

    btn = Button({'title': "Ni hao ma"})
    btn.createWindow(label.hwnd, (20, 20, 120, 30))
    
    editor1 = Editor()
    editor1.createWindow(label.hwnd, (20, 20, 200, 30))

    editor2 = ComboBox()
    editor2.editable = False
    editor2.setPopupTip([{'title': 'AAAAA'}, {'title': 'BBBBB'}])
    editor2.createWindow(label.hwnd, (20, 80, 200, 30))
    win32gui.PumpMessages()
