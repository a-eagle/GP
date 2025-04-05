import sys, win32con, win32gui, win32api
sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Dialog(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.destroyOnHide = True
        self.modal = None

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU, className='STATIC', title='I-Dialog'):
        super().createWindow(parentWnd, rect, style, className, title)

    def setModal(self, modal : bool):
        if self.modal == modal:
            return
        self.modal = modal
        p = self.hwnd
        while True:
            pp = win32gui.GetParent(p)
            if not pp:
                break
            win32gui.EnableWindow(pp, not modal)
            style = win32gui.GetWindowLong(pp, win32con.GWL_STYLE)
            if not (style & win32con.WS_CHILD):
                break

    def showCenter(self):
        pr = win32gui.GetParent(self.hwnd)
        if pr:
            rc = win32gui.GetWindowRect(pr)
        else:
            rc = (0, 0, win32api.GetSystemMetrics(win32con.SM_CXSCREEN), win32api.GetSystemMetrics(win32con.SM_CYSCREEN))
        src = win32gui.GetWindowRect(self.hwnd)
        w = rc[2] - rc[0] - (src[2] - src[0])
        h = rc[3] - rc[1] - (src[3] - src[1])
        x = rc[0] + w // 2
        y = rc[1] + h // 2
        self.show(x, y)

    # screen x, screen y
    def show(self, x, y):
        win32gui.SetWindowPos(self.hwnd, 0, x, y, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE)
        win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
        win32gui.SetActiveWindow(self.hwnd)

    def hide(self):
        if self.modal:
            self.setModal(False)
        win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)

    def close(self):
        if self.modal:
            self.setModal(False)
        #win32gui.CloseWindow(self.hwnd) # is real mean min-size window
        win32gui.SendMessage(self.hwnd, win32con.WM_SYSCOMMAND, win32con.SC_CLOSE, 0)
    
    def onClose(self):
        pass

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_CLOSE:
            self.hide()
            self.onClose()
            if not self.destroyOnHide:
                return 0
            # go through, no return
        return super().winProc(hwnd, msg, wParam, lParam)

# listeners : InputEnd = {src, text, ok = True | False}
class InputDialog(Dialog):
    def __init__(self) -> None:
        super().__init__()
        self.editor = base_win.Editor()
        self.css['bgColor'] = self.editor.css['bgColor']
        self.editor.css['borderColor'] = self.editor.css['bgColor']

    def setText(self, text):
        self.editor.setText(text)

    def getText(self):
        return self.editor.text

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU, className='STATIC', title='Input'): # win32con.WS_CHILD | 
        super().createWindow(parentWnd, rect, style, className, title)
        w, h = self.getClientSize()
        self.editor.createWindow(self.hwnd, (10, 0, w - 20, h))
        self.editor.addListener(self.onPressEnter, None)

    def selectAll(self):
        txt = self.getText()
        if not txt:
            return
        self.editor.setSelRange(0, len(txt))

    def showCenter(self):
        super().showCenter()
        win32gui.SetFocus(self.editor.hwnd)

    def onPressEnter(self, event, args):
        if event.name == 'PressEnter':
            self.close()
            self.notifyListener(self.Event('InputEnd', self, text = self.getText(), ok = True))
    
    def onClose(self):
        self.notifyListener(self.Event('InputEnd', self, text = '', ok = False))

# listeners : InputEnd = {src, text, ok: True | False}
class MultiInputDialog(Dialog):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0x404040
        self.css['paddings'] = (5, 5, 5, 5)
        self.layout = base_win.GridLayout(('1fr', 30), ('1fr', 50, 50), (5, 10))
        self.editor = base_win.MutiEditor()

    def setText(self, text):
        self.editor.setText(text)

    def getText(self):
        return self.editor.text

    def createWindow(self, parentWnd, rect, style = win32con.WS_POPUP | win32con.WS_CAPTION | win32con.WS_SYSMENU, className='STATIC', title='Input'):
        super().createWindow(parentWnd, rect, style, className, title)
        self.editor.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, self.editor, {'horExpand': -1})
        okBtn = base_win.Button({'title': 'OK', 'name': 'ok'})
        okBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(1, 1, okBtn)
        cancelBtn = base_win.Button({'title': 'Cancel', 'name': 'cancel'})
        cancelBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(1, 2, cancelBtn)
        pds = self.css['paddings']
        w, h = self.getClientSize()
        self.layout.resize(pds[0], pds[1], w - pds[0] - pds[2], h - pds[1] - pds[3])

        def onBtn(evt, args):
            self.close()
            ok = evt.info['name'] == 'ok'
            txt = self.editor.getText() if ok else ''
            evt = self.Event('InputEnd', self, text = txt, ok = ok)
            self.notifyListener(evt)
        okBtn.addNamedListener('Click', onBtn)
        cancelBtn.addNamedListener('Click', onBtn)

    def onClose(self):
        # self.notifyListener(self.Event('InputEnd', self, text = '', ok = False))
        pass

# listeners: InputEnd = {src, ok : True | False}
class ConfirmDialog(Dialog):
    # info : tip msg
    def __init__(self, info : str) -> None:
        super().__init__()
        self.info = info

    def createWindow(self, parentWnd, rect = (0, 0, 300, 150), style = win32con.WS_POPUP | win32con.WS_CAPTION, className='STATIC', title='I-ConfirmDialog'):
        super().createWindow(parentWnd, rect, style, className, title)
        w, h = self.getClientSize()
        layout = base_win.GridLayout(('1fr', 25), ('1fr', 60, 60), (10, 20))
        label = base_win.Label(self.info)
        label.createWindow(self.hwnd, (0, 0, 1, 1))
        okBtn = base_win.Button({'title': 'OK'})
        okBtn.createWindow(self.hwnd, (0, 0, 1, 1))
        calncelBtn = base_win.Button({'title': 'Cancel'})
        calncelBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        layout.setContent(0, 0, label, {'horExpand': -1})
        layout.setContent(1, 1, okBtn)
        layout.setContent(1, 2, calncelBtn)
        layout.resize(10, 10, w - 20, h - 15)
        okBtn.addListener(self.onListen, True)
        calncelBtn.addListener(self.onListen, False)

    def onListen(self, evt, ok):
        if evt.name != 'Click':
            return
        self.close()
        self.notifyListener(self.Event('InputEnd', self, ok = ok))

    def onClose(self):
        self.notifyListener(self.Event('InputEnd', self, ok = False))

# listeners : InputEnd = {src, color: int }
class PopupColorWindow(base_win.NoActivePopupWindow):
    COL_NUM = 13
    ROW_NUM = 9
    CELL_SIZE = 20

    def __init__(self) -> None:
        super().__init__()
        self.destroyOnHide = True
        self.css['borderColor'] = None
        self.COLORS = [0x000033,0x001933,0x003333,0x003319,0x003300,0x193300,0x333300,0x331900,0x330000,0x330019,0x330033,0x190033,0x000000,0x000066,0x003366,0x006666,0x006633,0x006600,0x336600,0x666600,0x663300,0x660000,0x660033,0x660066,0x330066,0x202020,0x000099,0x004C99,0x009999,0x00994C,0x009900,0x4C9900,0x999900,0x994C00,0x990000,0x99004C,0x990099,0x4C0099,0x404040,0x0000CC,0x0066CC,0x00CCCC,0x00CC66,0x00CC00,0x66CC00,0xCCCC00,0xCC6600,0xCC0000,0xCC0066,0xCC00CC,0x6600CC,0x606060,0x0000FF,0x0080FF,0x00FFFF,0x00FF80,0x00FF00,0x80FF00,0xFFFF00,0xFF8000,0xFF0000,0xFF007F,0xFF00FF,0x7F00FF,0x808080,0x3333FF,0x3399FF,0x33FFFF,0x33FF99,0x33FF33,0x99FF33,0xFFFF33,0xFF9933,0xFF3333,0xFF3399,0xFF33FF,0x9933FF,0xA0A0A0,0x6666FF,0x66B2FF,0x66FFFF,0x66FFB2,0x66FF66,0xB2FF66,0xFFFF66,0xFFB266,0xFF6666,0xFF66B2,0xFF66FF,0xB266FF,0xC0C0C0,0x9999FF,0x99CCFF,0x99FFFF,0x99FFCC,0x99FF99,0xCCFF99,0xFFFF99,0xFFCC99,0xFF9999,0xFF99CC,0xFF99FF,0xCC99FF,0xE0E0E0,0xCCCCFF,0xCCE5FF,0xCCFFFF,0xCCFFE5,0xCCFFCC,0xE5FFCC,0xFFFFCC,0xFFE5CC,0xFFCCCC,0xFFCCE5,0xFFCCFF,0xE5CCFF,0xFFFFFF]

    def getColorAtXY(self, x, y):
        row = y // self.CELL_SIZE
        col = x // self.CELL_SIZE
        return self.getColor(row, col)

    def getColor(self, row, col):
        idx = row * self.COL_NUM + col
        if idx >= 0 and idx < len(self.COLORS):
            return self.COLORS[idx]
        return None

    def onDraw(self, hdc):
        for r in range(self.ROW_NUM):
            for c in range(self.COL_NUM):
                sx = c * self.CELL_SIZE
                sy = r * self.CELL_SIZE
                rc = (sx + 1, sy + 1, sx + self.CELL_SIZE, sy + self.CELL_SIZE)
                self.drawer.fillRect(hdc, rc, self.getColor(r, c))
        self.drawer.drawRect(hdc, (0, 0, *self.getClientSize()), self.css['bgColor'])

    def createWindow(self, parentWnd, rect = None, style = win32con.WS_POPUP | win32con.WS_CHILD, className='STATIC', title=''):
        W = self.CELL_SIZE * self.COL_NUM
        H = self.CELL_SIZE * self.ROW_NUM
        if rect:
            rect = (rect[0], rect[1], W, H)
        else:
            rect = (0, 0, W, H)
        super().createWindow(parentWnd, rect, style, className, title)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            color = self.getColorAtXY(x, y)
            self.hide()
            if color is not None:
                self.notifyListener(self.Event('InputEnd', self, color = color))
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

if __name__ == '__main__':
    #cw = PopupColorWindow()
    #cw.createWindow(None, (100, 100, 0, 0)) # , win32con.WS_OVERLAPPEDWINDOW
    
    #cw = ConfirmDialog("确认删除吗？")
    #cw.createWindow(None)
    #cw.showCenter()

    cw = MultiInputDialog()
    cw.destroyOnHide = False
    cw.createWindow(None, (0, 0, 300, 150), style = win32con.WS_POPUPWINDOW)

    win32gui.ShowWindow(cw.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()