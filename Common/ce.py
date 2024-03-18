import win32gui, win32con , win32api, win32ui, win32event, win32process # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools
import traceback, io

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win
from Common.base_win import MutiEditor

class CodeEditor(MutiEditor):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xfdfdfd
        self.css['fontName'] = '新宋体'
        self.paddingX = 40
        self.KEYS = ('def', 'None', 'False', 'True', 'and', 'or', 
                    'break', 'class', 'continue', 'del', 'if', 'elif', 'else',
                    'for', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 
                    'pass', 'return', 'while', 'super', 'from')
        self.DEF_FUNCS = ('print', 'range', 'list', 'input' )
        self.COLORS = {
            'KEY': 0x0077ff, 'DEF_FUNC': 0x900090, 'STR': 0x808080
        }
        self.excInfo = None # {lineno, exc, }

    def insertText(self, text):
        if text:
            text = text.replace('\t', '    ')
        return super().insertText(text)

    def updateRowText(self, row, text):
        super().updateRowText(row, text)
        if self.excInfo and self.excInfo['lineno'] == row + 1:
            self.excInfo = None

    def drawLeadings(self, hdc, row, rc):
        line = self.lines[row]['text']
        numSpace = 0
        for ch in line:
            if ch == ' ': numSpace += 1
            else: break
        numLD = numSpace // 4
        scw, *_ = win32gui.GetTextExtentPoint32(hdc, ' ')
        scw *= 4
        for i in range(numLD):
            sx = scw * i + rc[0]
            self.drawer.drawLine(hdc, sx, rc[1], sx, rc[3], 0xd0d0d0)

    def drawRow(self, hdc, row, rc):
        if self.excInfo and self.excInfo['lineno'] == row + 1:
            self.drawer.drawRect(hdc, rc, 0x0000ff)
        align = win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER
        self.drawLeadings(hdc, row, rc)
        b = 0
        sx = 0
        tokens = self.lines[row]['tokens']
        line = self.lines[row]['text']
        for i in range(len(tokens)):
            tk = tokens[i]
            if b != tk['b']:
                irc = (sx + rc[0], rc[1], rc[0] + tk['sx'], rc[3])
                cotx = line[b : tk['b']]
                self.drawer.drawText(hdc, cotx, irc, color = self.css['textColor'], align = align)
            irc = (rc[0] + tk['sx'], rc[1], rc[0] + tk['ex'], rc[3])
            self.drawer.drawText(hdc, tk['name'], irc, color = self.COLORS[tk['type']], align = align)
            b = tk['e']
            sx = tk['ex']
        # draw tail
        if b == len(line):
            return
        if len(tokens) == 0:
            self.drawer.drawText(hdc, line, rc, color = self.css['textColor'], align = align)
        else:
            tk = tokens[-1]
            irc = (tk['ex'] + rc[0], rc[1], rc[2], rc[3])
            self.drawer.drawText(hdc, line[tk['e'] : ], irc, color = self.css['textColor'], align = align)
        

    def participles(self, txt):
        #isalpha = lambda ch : (ch >= 'A' and ch <= 'Z') or (ch >= 'a' and ch <= 'z')
        buf = io.StringIO()
        buf.write(txt)
        tokens = []
        if not txt:
            return tokens
        
        # find strs
        b = -1
        dsq_1 = 0
        for i in range(len(txt)):
            ch = txt[i]
            if ch != "'" and ch != '"':
                continue
            dsq = 1 if ch == "'" else 2
            if b == -1:
                b = i
                dsq_1 = dsq
            else:
                if dsq_1 == dsq:
                    tk = txt[b : i + 1]
                    tokens.append({'type' : 'STR', 'name': tk, 'b': b, 'e': i + 1}) # type = KEY | DEF_FUNC | STR
                    buf.seek(b)
                    buf.write(' ' * len(tk))
                    b = -1
                    dsq_1 = 0

        # find keys...
        b = -1
        buf.seek(0)
        for i in range(len(txt) + 1):
            if i == len(txt):
                ch = ' '
            else:
                ch = buf.read(1)  #txt[i]
            if (ch >= 'A' and ch <= 'Z') or (ch >= 'a' and ch <= 'z'):
                if b == -1:
                    b = i
                continue
            if b == -1:
                continue
            # is not alpha
            tk = txt[b : i]
            if tk in self.KEYS:
                tokens.append({'type' : 'KEY', 'name': tk, 'b': b, 'e': i}) # type = KEY | DEF_FUNC | STR
            elif tk in self.DEF_FUNCS:
                tokens.append({'type' : 'DEF_FUNC', 'name': tk, 'b': b, 'e': i}) # type = KEY | DEF_FUNC | STR
            b = -1
        tokens.sort(key = lambda t : t['b'])
        return tokens

    def beautiful(self, row, hdc):
        nd = self.lines[row].get('modified', True)
        if not nd:
            return
        self.lines[row]['modified'] = False
        tokens = self.participles(self.lines[row]['text'])
        self.lines[row]['tokens'] = tokens
        line = self.lines[row]['text']
        for tk in tokens:
            pre = line[0 : tk['b']]
            scw, *_ = win32gui.GetTextExtentPoint32(hdc, pre)
            pre = line[0 : tk['e']]
            ecw, *_ = win32gui.GetTextExtentPoint32(hdc, pre)
            tk['sx'] = scw
            tk['ex'] = ecw

    def drawLineNo(self, hdc):
        _, H = self.getClientSize()
        w = self.paddingX - 5
        rc = (0, 0, w, H)
        self.drawer.fillRect(hdc, rc, 0xdddddd)
        for i in range(self.startRow, len(self.lines)):
            hd = f'{i + 1}'
            sy = self.getYAtPos(MutiEditor.Pos(i, 0))
            self.drawer.drawText(hdc, hd, (0, sy, w - 10, sy + self.lineHeight), color = 0x908070, align = win32con.DT_RIGHT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def onDraw(self, hdc):
        for r in range(len(self.lines)):
            self.beautiful(r, hdc)
        super().onDraw(hdc)
        self.drawLineNo(hdc)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_KEYDOWN and wParam == win32con.VK_F5:
            self.notifyListener('Run', {'src': self, 'code': self.getText()})
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class Console(base_win.BaseEditor):
    PADDING_LEFT = 5
    def __init__(self) -> None:
        super().__init__()
        self.infos = [] # item of {text, color}
        self.lineHeight = 24
        self.css['fontSize'] = 18
        self.css['inputColor'] = 0xff3333
        self.startRow = 0
        self.stdout = None
        self.stdin = None
        self.reading = False
        self.myin = ''
        self.event = None

    def redirect(self):
        self.clear()
        self.stdout = sys.stdout
        self.stdin = sys.stdin
        sys.stdout = self
        sys.stdin = self

    def restore(self):
        sys.stdout = self.stdout
        sys.stdin = self.stdin

    def write(self, msg : str):
        if msg == None:
            msg = 'None'
        if not isinstance(msg, str):
            msg = str(msg)
        for ch in msg:
            self.addChar(ch)
        self.makeLastVisible()

    def makeLastVisible(self):
        W, H = self.getClientSize()
        mx = H // self.lineHeight
        if not self.infos:
            return
        idx = len(self.infos) - self.startRow - 1
        if idx >= mx:
            self.startRow += idx - mx + 1
            self.invalidWindow()
    
    def showInput(self):
        # make last row visible
        self.makeLastVisible()
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        lastTxt = ''
        sy = 0
        if self.infos:
            lastTxt = self.infos[-1]['text']
            sy = (len(self.infos) - 1 - self.startRow) * self.lineHeight
        scw, *_ = win32gui.GetTextExtentPoint32(hdc, lastTxt + self.myin)
        win32gui.ReleaseDC(self.hwnd, hdc)
        self.setCaretPos(scw + self.PADDING_LEFT, sy)
        self.showCaret()

    def setFocus(self):
        th, *_ = win32process.GetWindowThreadProcessId(self.hwnd)
        win32process.AttachThreadInput(win32api.GetCurrentThreadId(), th, True)
        win32gui.SetFocus(self.hwnd)

    def readline(self):
        # begin read
        self.event = win32event.CreateEvent(None, True, False, f'_io_read_{id(self)}')
        self.myin = ''
        self.reading = True
        self.setFocus()
        sig = win32event.WaitForSingleObject(self.event, 0xffffffff)
        self.reading = False
        # sig == WAIT_OBJECT_0
        val = self.myin
        self.myin = ''
        win32api.CloseHandle(self.event)
        self.event = None
        return val

    def newRow(self, color = 0x202020):
        self.infos.append({'text': '', 'color': color})

    def addText(self, txt, color = 0x202020):
        if not txt:
            return
        for ch in txt:
            self.addChar(ch, color)

    def addChar(self, ch, color = 0x202020):
        if not self.infos:
            self.newRow(color)
        if ch == '\r':
            return
        if ch == '\n':
            self.newRow(color)
        else:
            self.infos[-1]['text'] += ch
            self.infos[-1]['color'] = color
    
    def clear(self):
        self.startRow = 0
        self.infos.clear()
        self.myin = ''
        self.invalidWindow()

    def addException(self, log):
        if not log:
            return
        for ch in log:
            self.addChar(ch, 0x0000D0)
        self.invalidWindow()
    
    def onDraw(self, hdc):
        align = win32con.DT_VCENTER | win32con.DT_LEFT | win32con.DT_SINGLELINE
        W, H = self.getClientSize()
        sy = 0
        for r in range(self.startRow, len(self.infos)):
            info = self.infos[r]
            rc = (self.PADDING_LEFT, sy, W, sy + self.lineHeight)
            self.drawer.drawText(hdc, info['text'], rc, color = info['color'], align = align)
            if info.get('input', None):
                sx, *_ = win32gui.GetTextExtentPoint32(hdc, info['text'])
                rc = (self.PADDING_LEFT + sx, sy, W, sy + self.lineHeight)
                self.drawer.drawText(hdc, info['input'], rc, color = self.css['inputColor'], align = align)
            sy += self.lineHeight

        if self.reading and self.myin:
            lx = self.infos[-1]['text'] if self.infos else ''
            sx, *_ = win32gui.GetTextExtentPoint32(hdc, lx)
            sy = 0
            if self.infos:
                sy = (len(self.infos) - 1 - self.startRow) * self.lineHeight
            rc = (self.PADDING_LEFT + int(sx), sy, W, sy + self.lineHeight)
            self.drawer.drawText(hdc, self.myin, rc, color = self.css['inputColor'], align = align)

    def endInput(self):
        if not self.infos:
            self.newRow()
        last = self.infos[-1]
        last['input'] = self.myin
        self.newRow()
        self.makeLastVisible()
        self.reading = False
        self.hideCaret()
        self.invalidWindow()
        win32event.SetEvent(self.event)

    def onChar(self, ch):
        if ch == win32con.VK_RETURN:
            self.endInput()
            return
        if ch == win32con.VK_BACK:
            if self.myin:
                self.myin = self.myin[0 : -1]
                self.invalidWindow()
                self.showInput()
            return
        if ch == 127 or ch < 32:
            return
        self.myin += chr(ch)
        self.invalidWindow()
        self.showInput()

    def onSetFocus(self):
        super().onSetFocus()
        self.showInput()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            if self.reading:
                win32gui.SetFocus(self.hwnd)
            return True
        if msg == win32con.WM_CHAR or msg == win32con.WM_IME_CHAR:
            if self.reading:
                self.onChar(wParam)
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

def formatException(ex):
    exs : list = ex.splitlines()
    exs.reverse()
    TAG = '  File "<string>", line '
    rs = []
    for n in exs:
        if n.startswith(TAG):
            rs.append(n)
            break
        rs.append(n)
    rs.reverse()
    line = rs[0].split(',')
    ln = line[1].replace('line ', '')
    lineno = int(ln)
    txt = '\n'.join(rs)
    return {'lineno': lineno, 'exc' : txt}

def runCode_(code, editor : CodeEditor, console : Console):
    editor.excInfo = None
    editor.invalidWindow()
    console.clear()
    console.redirect()
    try:
        exec(code, {}, {})
    except Exception as e:
        #excName, excVal, exc_traceback = sys.exc_info()
        ex = traceback.format_exc()
        exc = formatException(ex)
        editor.excInfo = exc
        editor.invalidWindow()
        console.addException(exc['exc'])
    console.restore()

def runCode(evtName, evt, console):
    if evtName != 'Run':
        return
    base_win.ThreadPool.addTask('run', runCode_, evt['code'], evt['src'], console)
    base_win.ThreadPool.start()

if __name__ == '__main__':
    label = base_win.Label()
    label.css['bgColor'] = 0x505050
    label.createWindow(None, (150, 0, 1000, 700), win32con.WS_OVERLAPPEDWINDOW  | win32con.WS_VISIBLE, title='高绾卿')
    editor = CodeEditor()
    editor.createWindow(label.hwnd, (0, 0, 1, 1))
    console = Console()
    console.css['bgColor'] = 0xdddddd
    console.createWindow(label.hwnd, (0, 0, 1, 1))
    editor.addListener(runCode, console)

    layout = base_win.GridLayout(('3fr', '1fr'), ('100%', ), (5, 5))
    layout.setContent(0, 0, editor)
    layout.setContent(1, 0, console)
    W, H = label.getClientSize()
    layout.resize(0, 0, W, H)
    win32gui.PumpMessages()