import win32gui, win32con , win32api, win32ui, win32gui_struct, win32clipboard # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools, io
import ctypes
from ctypes import wintypes

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Word:
    def __init__(self, fontName, fontSize, char = '') -> None:
        self.char = char
        self.fontName = fontName
        self._fontSize = fontSize
        self.bold = False
        self.italic = False
        self.underline = False
        self.bgColor = None
        self.color = None
        self.width = 0

    @property
    def fontSize(self):
        return self._fontSize
    
    @fontSize.setter
    def fontSize(self, val):
        self._fontSize = val
        self.fontChanged()

    def getFont(self):
        drawer = base_win.Drawer.instance()
        weight = 700 if self.bold else 0
        font = drawer.getFont(self.fontName, fontSize = self.fontSize, weight = weight, italic = self.italic, underline = self.underline)
        return font

    def calcWidth(self, hdc):
        if self.width > 0:
            return
        self.width = 0
        if not self.char:
            return
        sdc = win32gui.SaveDC(hdc)
        drawer = base_win.Drawer.instance()
        drawer.use(hdc, self.getFont())
        ch = self.char
        if self.char == '\t':
            ch = '    '
        w, *_ = win32gui.GetTextExtentPoint32(hdc, ch)
        win32gui.RestoreDC(hdc, sdc)
        self.width = w

    def fontChanged(self):
        self.width = 0

    def isSameStyle(self, w):
        if not w:
            return False
        return self.fontName == w.fontName and self.fontSize == w.fontSize and self.bold == w.bold and \
            self.italic == w.italic and self.underline == w.underline and \
            self.bgColor == w.bgColor and self.color == w.color

class Line:
    LINE_PADDING = 4

    def __init__(self, defaultFontSize) -> None:
        self.lineHeight = 0
        self.defaultFontSize = defaultFontSize
        self.words = []

    def invalidSize(self):
        self.lineHeight = 0
        for w in self.words:
            w.invalidSize()

    def changed(self):
        self.lineHeight = 0
        self.calcLineHeight()

    def calcWordsSize(self, hdc):
        for w in self.words:
            w.calcWidth(hdc)
        self.calcLineHeight()

    def calcLineHeight(self):
        if self.lineHeight > 0:
            return self.lineHeight
        h = self.defaultFontSize
        for d in self.words:
            h = max(h, d.fontSize)
        h += self.LINE_PADDING
        self.lineHeight = h
        return h

    def isEmpty(self):
        for w in self.words:
            if w.char:
                return False
        return True

class Pos:
    def __init__(self, row = 0, col = 0) -> None:
        self.row = row
        self.col = col

    def __lt__(self, th):
        if self.row < th.row:
            return True
        if self.row == th.row:
            return self.col < th.col
        return False

    def __gt__(self, th):
        if self.row > th.row:
            return True
        if self.row == th.row:
            return self.col > th.col
        return False

    def __eq__(self, th) -> bool:
        if th is None:
            return False
        return self.row == th.row and self.col == th.col

class RichEditorModel:
    def __init__(self, css) -> None:
        self.css = css
        self.lines = [Line(self.defaultFontSize())]

    def defaultFontSize(self):
        return self.css['fontSize']
    
    def defaultFontName(self):
        return self.css['fontName']

    def insertWord(self, pos : Pos, word : Word):
        if not pos or not word or not word.char:
            return False
        if not self.isValidPos(pos):
            return False
        line : Line = self.lines[pos.row]
        if word.char != '\n':
            line.words.insert(pos.col, word)
            line.changed()
            pos.col += 1
            return True
        pre = line.words[0 : pos.col]
        suff = line.words[pos.col : ]
        line.words = pre
        line.changed()
        suffLine = Line(self.defaultFontSize())
        suffLine.words = suff
        self.lines.insert(pos.row + 1, suffLine)
        pos.row += 1
        pos.col = 0
        return True

    def beforeDeleteWord(self, pos : Pos):
        if not self.isValidPos(pos):
            return False
        line : Line = self.lines[pos.row]
        if pos.col == 0:
            if pos.row == 0:
                return False
            pre : Line = self.lines[pos.row - 1]
            self.lines.pop(pos.row)
            pos.row -= 1
            pos.col = len(pre.words)
            pre.words.extend(line.words)
            line.words.clear()
            pre.changed()
        else:
            line.words.pop(pos.col - 1)
            pos.col -= 1
            line.changed()
        return True

    def afterDeleteWord(self, pos : Pos):
        if not self.isValidPos(pos):
            return False
        line : Line = self.lines[pos.row]
        if pos.col == len(line.words):
            if pos.row == len(self.lines) - 1:
                return False
            next : Line = self.lines[pos.row + 1]
            line.words.extend(next.words)
            self.lines.pop(pos.row + 1)
            next.words.clear()
            line.changed()
        else:
            line.words.pop(pos.col)
            line.changed()
        return True

    def isValidPos(self, pos : Pos):
        if not pos:
            return False
        if pos.col < 0 or pos.row < 0 or pos.row >= len(self.lines):
            return False
        line : Line = self.lines[pos.row]
        return pos.col <= len(line.words)

    def getPlainText(self, startPos : Pos, endPos : Pos):
        rs = self.getWords(startPos, endPos)
        txt = self.getWordsPlainText(rs)
        return txt

    def getWords(self, startPos : Pos, endPos : Pos):
        if not self.isValidPos(startPos) or not self.isValidPos(endPos):
            return None
        if startPos == endPos:
            return None
        rs = []
        if startPos > endPos:
            startPos, endPos = endPos, startPos
        if startPos.row == endPos.row:
            cline : Line = self.lines[startPos.row]
            rs.extend(cline.words[startPos.col : endPos.col])
            return rs

        sline : Line = self.lines[startPos.row]
        rs.extend(sline.words[startPos.col : len(sline.words)])
        for r in range(startPos.row + 1, endPos.row):
            sline : Line = self.lines[r]
            rs.append(Word(self.defaultFontName(), 1, '\n'))
            rs.extend(sline.words[0 : len(sline.words)])
        sline : Line = self.lines[endPos.row]
        rs.append(Word(self.defaultFontName(), 1, '\n'))
        rs.extend(sline.words[0 : endPos.col])
        return rs

    def delWords(self, startPos : Pos, endPos : Pos):
        if not self.isValidPos(startPos) or not self.isValidPos(endPos):
            return False
        if startPos == endPos:
            return False
        if startPos > endPos:
            startPos, endPos = endPos, startPos
        if startPos.row == endPos.row:
            cline : Line = self.lines[startPos.row]
            del cline.words[startPos.col : endPos.col]
            cline.changed()
            return True
        sline : Line = self.lines[startPos.row]
        del sline.words[startPos.col : len(sline.words)]
        rowIdx = startPos.row + 1
        for r in range(rowIdx, endPos.row):
            sline : Line = self.lines[r]
            sline.words.clear()
            self.lines.pop(rowIdx)
        sline : Line = self.lines[rowIdx]
        if len(sline.words) == endPos.col:
            # del full row
            sline.words.clear()
            self.lines.pop(rowIdx)
        else:
            del sline.words[0 : endPos.col]
            sline.changed()
        return True

    def getRichText(self, startPos : Pos, endPos : Pos):
        rs = self.getWords(startPos, endPos)
        txt = self.getWordsRichText(rs)
        return txt

    def getWordsPlainText(self, words : list):
        if not words:
            return ''
        text = io.StringIO()
        for w in words:
            text.write(w.char)
        return text.getvalue()
        
    def getWordsRichText(self, words : list):
        if not words:
            return ''
        text = io.StringIO()
        groups = []
        last : Word = None
        for w in words:
            if w.char == '\n':
                groups.append('\n')
            elif last == None:
                groups.append([w])
            elif last.isSameStyle(w):
                groups[-1].append(w)
            else:
                groups.append([w])
            last = w
        for ws in groups:
            if ws and isinstance(ws, str):
                text.write(ws)
                continue
            first = ws[0]
            fs = self.getSerializeFontStyle(first)
            text.write(f'<T ')
            if first.fontName and first.fontName != self.defaultFontName():
                text.write(f"fn='{first.fontName}' ")
            if fs != 0:
                text.write(f'fs={fs} ')
            if first.fontSize:
                text.write(f'fz={first.fontSize :X} ')
            if type(first.color) == int:
                text.write(f'c={first.color :X} ')
            if type(first.bgColor) == int:
                text.write(f'bg={first.bgColor :X} ')
            text.write('>')
            for w in ws:
                text.write(w.char)
            text.write('</T>')
        return text.getvalue()

    def getSerializeFontStyle(self, w : Word):
        fs = 0
        if w.bold: fs |= 1
        if w.italic: fs |= 2
        if w.underline: fs |= 4
        return fs

    def insertRichText(self, pos : Pos, text):
        if not text or not self.isValidPos(pos):
            return False
        i = 0
        while True:
            ei, w = self._pullNext(i, text)
            if w and isinstance(w, list):
                for m in w:
                    self.insertWord(pos, m)
            elif w and isinstance(w, Word):
                self.insertWord(pos, w)
            else:
                break
            i = ei
        return True

    def _pullNext(self, i, text : str):
        if i >= len(text):
            return i, None
        if text[i] != '<':
            return i + 1, Word(self.defaultFontName(), self.defaultFontSize(), text[i])
        ei = text.find('>', i)
        if ei < 0:
            return ei, None

        fn = self._getStrAttrVal('fn', text, i, ei)
        fs = self._getNumAttrVal('fs', text, i, ei)
        fz = self._getNumAttrVal('fz', text, i, ei)
        color = self._getNumAttrVal('c', text, i, ei)
        bgColor = self._getNumAttrVal('bg', text, i, ei)
        si = ei + 1
        ei = text.find('</T>', si)
        bei = ei + 4 # skip end tag </T>
        if ei < 0:
            return -1, None
        rs = []
        for i in range(si, ei):
            w = Word(self.defaultFontName(), self.defaultFontSize())
            if fn: w.fontName = fn
            if fz: w.fontSize = fz
            if type(fs) == int:
                if fs & 1: w.bold = True
                if fs & 2: w.italic = True
                if fs & 4: w.underline = True
            if color != None: w.color = color
            if bgColor != None: w.bgColor = bgColor
            w.char = text[i]
            rs.append(w)
        return bei, rs

    def _isalpha(self, ch):
            return (ch >= '0' and ch <= '9') or (ch >= 'a' and ch <= 'z') or (ch >= 'A' and ch <= 'Z')

    def _getNumAttrVal(self, attrName, text, fromIdx, endIdx):
        idx = text.find(f'{attrName}=', fromIdx, endIdx)
        if idx < 0:
            return None
        idx += len(attrName) + 1
        v = ''
        while (idx < endIdx and self._isalpha(text[idx])):
            v += text[idx]
            idx += 1
        return int(v.strip(), base = 16)
    
    def _getStrAttrVal(self, attrName, text, fromIdx, endIdx):
        idx = text.find(f'{attrName}=', fromIdx, endIdx)
        if idx < 0:
            return None
        idx += len(attrName) + 1
        if idx >= endIdx:
            return None
        q = text[idx]
        v = ''
        idx += 1
        while (idx < endIdx and text[idx] != q):
            v += text[idx]
            idx += 1
        if idx < endIdx and text[idx] == q:
            return v.strip()
        return None

class RichEditorRender:
    def __init__(self) -> None:
        self.lines = [] # Line objects

    def getXY(self, pos : Pos):
        pass

class RichEditor(base_win.BaseEditor):
    def __init__(self) -> None:
        super().__init__()
        self.css['fontSize'] = 16
        self.css['bgColor'] = 0xfdfdfd
        self.css['textColor'] = 0x202020
        self.css['borderColor'] = 0xdddddd
        self.css['selBgColor'] = 0xC0C0C0
        self.css['lineNoBgColor'] = 0xE4E4E4
        self.css['lineNoTextColor'] = 0x919191
        self.css['insertLineBgColor'] = 0xFFE8E8
        self.css['paddings'] = (40, 0, 0, 0)
        self.startRow = 0
        self.model = RichEditorModel(self.css)
        self.insertPos : Pos = None # Pos object
        self.selRange = None # (begin-Pos, end-Pos)

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        self._onDraw(hdc, W, H)

    def getTextXY(self, pos : Pos):
        if not self.model.isValidPos(pos):
            return None
        if pos.row < self.startRow:
            return None
        y = 0
        for i in range(self.startRow, pos.row):
            ln : Line = self.model.lines[i]
            y += ln.lineHeight
        ln : Line = self.model.lines[pos.row]
        x = 0
        for i in range(0, pos.col):
            x += ln.words[i].width
        return (x, y)
    
    def getXY(self, pos : Pos):
        xy = self.getTextXY(pos)
        if not xy:
            return None
        pds = self.css['paddings']
        x, y = xy
        x += pds[0]
        y += pds[1]
        return (x, y)

    def getInsertPosAtXY(self, x, y):
        pds = self.css['paddings']
        x -= pds[0]
        y -= pds[1]
        if x < 0 or y < 0:
            return None
        sy = 0
        findRow = -1
        for i in range(self.startRow, len(self.model.lines)):
            if sy <= y and y < sy + self.model.lines[i].lineHeight:
                findRow = i
                break
            sy += self.model.lines[i].lineHeight
        if findRow < 0:
            findRow = len(self.model.lines) - 1
        ln : Line = self.model.lines[findRow]
        sx = 0
        for i in range(len(ln.words)):
            w = ln.words[i].width
            if sx <= x and x <= sx + w // 2:
                return Pos(findRow, i)
            elif sx <= x and x < sx + w:
                return Pos(findRow, i + 1)
            sx += w
        return Pos(findRow, len(ln.words))

    def calcWordsSize(self, hdc):
        for w in self.model.lines:
            w.calcWordsSize(hdc)

    def _onDraw(self, hdc, W, H):
        pds = self.css['paddings']
        lineNoRect = (0, pds[1], pds[0], H)
        self.drawer.fillRect(hdc, lineNoRect, self.css['lineNoBgColor'])
        self.calcWordsSize(hdc)
        sy = pds[1]
        sx = pds[0]
        for i in range(self.startRow, len(self.model.lines)):
            if sy >= H - pds[3]:
                break
            line : Line = self.model.lines[i]
            rc = (sx, sy, W - pds[2], sy + line.lineHeight)
            if self.model.isValidPos(self.insertPos) and self.insertPos.row == i:
                # hilight insert line
                self.drawer.fillRect(hdc, rc, color = self.css['insertLineBgColor'])
            sdc = win32gui.SaveDC(hdc)
            self.drawLineContent(hdc, i, rc)
            win32gui.RestoreDC(hdc, sdc)

            sdc = win32gui.SaveDC(hdc)
            lineNo = i - self.startRow + 1
            rc2 = (lineNoRect[0], rc[1], lineNoRect[2], rc[3])
            self.drawer.use(hdc, self.getDefFont())
            self.drawer.drawText(hdc, f'{lineNo :>3d}', rc2, color = self.css['lineNoTextColor'], align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            sy += line.lineHeight
            win32gui.RestoreDC(hdc, sdc)

    def isInSelRange(self, row, col):
        if not self.selRange or row < 0 or col < 0:
            return False
        b, e = self.selRange
        if b == e:
            return False
        if b > e:
            b, e = e, b
        if b.row == e.row:
            if b.row == row:
                return b.col <= col and col < e.col
            return False
        if b.row == row:
            return b.col <= col
        if e.row == row:
            return col < e.col
        if row > b.row and row < e.row:
            return True
        return False
        
    def drawLineContent(self, hdc, lineIdx, rc):
        line = self.model.lines[lineIdx]
        sx = rc[0]
        for i, w in enumerate(line.words):
            sdc = win32gui.SaveDC(hdc)
            self.drawer.use(hdc, w.getFont())
            my = rc[1] + (line.lineHeight - w.fontSize) // 2
            mrc = (sx, my, sx + w.width, my + w.fontSize)
            bg = w.bgColor
            if self.isInSelRange(lineIdx, i):
                bg = self.drawer.blendColor(self.css['selBgColor'], w.bgColor, 0.5)
            if bg is not None:
                self.drawer.fillRect(hdc, (sx, rc[1], sx + w.width, rc[3]), bg)
            c = w.color if w.color != None else self.css['textColor']
            self.drawer.drawText(hdc, w.char, mrc, color = c, align = win32con.DT_LEFT)
            sx += w.width
            win32gui.RestoreDC(hdc, sdc)

    def isPosVisible(self, pos):
        if not self.model.isValidPos(pos):
            return False
        xy = self.getXY(pos)
        if not xy:
            return False
        W, H = self.getClientSize()
        x, y = xy
        if x < W and y < H:
            return True
        return False
        
    def setInsertPos(self, pos):
        if not self.isPosVisible(pos): # clear pos
            self.insertPos = None
            self.hideCaret()
        else:
            self.insertPos = pos
            x, y = self.getXY(pos)
            ln : Line = self.model.lines[pos.row]
            y += (ln.lineHeight - self._caretHeight) // 2
            self.setCaretPos(x, y)
            self.showCaret()

    def setSelRange(self, beginPos, endPos):
        if beginPos == None or endPos == None:
            self.selRange = None
            return
        if type(beginPos) == str and beginPos == 'NotSet':
            beginPos = self.selRange[0] if self.selRange else None
        if type(endPos) == str and endPos == 'NotSet':
            endPos = self.selRange[1] if self.selRange else None
        if beginPos == None or endPos == None:
            self.selRange = None
            return
        self.selRange = (beginPos, endPos)

    def onKey(self, key):
        if not self.model.isValidPos(self.insertPos):
            return
        if not self.isPosVisible(self.insertPos):
            return
        if not self._caretVisible:
            return
        if key == 8:
            #self.onKeyBackspace()
            return
        if key == 127:
            #self.onKeyDelete()
            return
        if key == 10 or key == win32con.VK_RETURN: # return key
            key = 10
        if key < 32 and key != 10 and key != win32con.VK_TAB:
            return
        ch = chr(key)
        if not self.model.insertRichText(self.insertPos, ch):
            return
        self.invalidWindow()
        win32gui.UpdateWindow(self.hwnd) # calc size
        self.setInsertPos(self.insertPos)

    def hasSelRange(self):
        if not self.selRange:
            return False
        b, e = self.selRange
        if b is None or e is None:
            return False
        if self.model.isValidPos(b) and self.model.isValidPos(e):
            return b != e
        return False

    def deleteSelRange(self):
        if not self.hasSelRange():
            return False
        b, e = self.selRange
        if b > e:
            b, e = e, b
        ok = self.model.delWords(b, e)
        if not ok:
            return False
        self.selRange = None
        self.setInsertPos(b)
        self.invalidWindow()
        return True

    def onKeyDelete(self):
        if self.deleteSelRange():
            return
        if self.model.afterDeleteWord(self.insertPos):
            self.invalidWindow()

    def onKeyBackspace(self):
        if self.deleteSelRange():
            return
        if self.model.beforeDeleteWord(self.insertPos):
            self.setInsertPos(self.insertPos)
            self.invalidWindow()

    def scroll(self, delta):
        delta *= 3
        if delta > 0:
            self.startRow = min(self.startRow + delta, len(self.model.lines) - 1)
        else:
            self.startRow = max(self.startRow + delta, 0)
        self.invalidWindow()
        if not self.model.isValidPos(self.insertPos):
            return
        if self.isPosVisible(self.insertPos):
            self.setInsertPos(self.insertPos)
            self.showCaret()
        else:
            self.hideCaret()

    def _copyToClipboard(self, cf, text):
        if not text:
            return False
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalAlloc.argtypes = (wintypes.UINT, wintypes.DWORD)
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL, )
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL, )
        kernel32.GlobalLock.restype = wintypes.LPVOID
        user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
        user32.SetClipboardData.restype = wintypes.HANDLE

        h = kernel32.GlobalAlloc(win32con.GMEM_MOVEABLE, len(text) * 2 + 2)
        if not h:
            return False
        ph = kernel32.GlobalLock(h)
        if not ph:
            return False
        if not getattr(self, 'libc', None):
            libc = ctypes.cdll.LoadLibrary('msvcrt')
            self.libc = libc
        libc = self.libc
        ptext = ctypes.create_unicode_buffer(text)
        libc.memcpy.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
        libc.memcpy(ph, ptext, ctypes.sizeof(ctypes.c_wchar) * (len(text) + 1))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(cf, h)
        return True
    
    def _copyFromClipboard(self, cf):
        if not cf:
            return False
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        kernel32.GlobalAlloc.argtypes = (wintypes.UINT, wintypes.DWORD)
        kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL, )
        kernel32.GlobalUnlock.restype = wintypes.BOOL
        kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL, )
        kernel32.GlobalLock.restype = wintypes.LPVOID
        user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.IsClipboardFormatAvailable.argtypes = (wintypes.UINT, )
        user32.GetClipboardData.restype = wintypes.HANDLE

        if not user32.IsClipboardFormatAvailable(cf):
            return False
        h = user32.GetClipboardData(cf)
        if not h:
            return False
        ph = kernel32.GlobalLock(h)
        if not ph:
            return False
        if not getattr(self, 'libc', None):
            libc = ctypes.cdll.LoadLibrary('msvcrt')
            self.libc = libc
        libc = self.libc
        val = io.StringIO()
        pcst = ctypes.cast(ph, ctypes.c_wchar_p)
        kernel32.GlobalUnlock(h)
        return pcst.value

    def doCopy(self, selRange):
        if not selRange:
            return
        ws = self.model.getWords(selRange[0], selRange[1])
        if not ws:
            return
        text = self.model.getWordsPlainText(ws)
        html = self.model.getWordsRichText(ws)

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        b = user32.OpenClipboard(self.hwnd)
        if not b:
            return
        user32.EmptyClipboard()
        self._copyToClipboard(win32con.CF_UNICODETEXT, text)
        user32.RegisterClipboardFormatA.argtypes = (wintypes.LPCSTR, )
        user32.RegisterClipboardFormatA.restype = wintypes.UINT
        cf = user32.RegisterClipboardFormatA(b'RichEdior_Html')
        if cf: self._copyToClipboard(cf, html)
        user32.CloseClipboard()

    def doPaste(self):
        if not self.model.isValidPos(self.insertPos):
            return
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        b = user32.OpenClipboard(self.hwnd)
        if not b:
            return
        user32.RegisterClipboardFormatA.argtypes = (wintypes.LPCSTR, )
        user32.RegisterClipboardFormatA.restype = wintypes.UINT
        cf = user32.RegisterClipboardFormatA(b'RichEdior_Html')
        val = None
        if cf and user32.IsClipboardFormatAvailable(cf):
            val = self._copyFromClipboard(cf)
        if val is False:
            val = self.copyFromClipboard(win32con.CF_UNICODETEXT)
        if not val:
            return
        self.deleteSelRange()
        if not self.model.isValidPos(self.insertPos):
            return
        self.model.insertRichText(self.insertPos, val)
        self.invalidWindow()
        win32gui.UpdateWindow(self.hwnd)
        self.setInsertPos(self.insertPos)

    def doCut(self):
        if not self.selRange:
            return
        b, e = self.selRange
        if not self.model.isValidPos(b) or not self.model.isValidPos(b):
            return
        if b == e:
            return
        self.doCopy(self.selRange)
        self.deleteSelRange()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            win32gui.SetFocus(self.hwnd)
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            pos = self.getInsertPosAtXY(x, y)
            self.setSelRange(pos, pos)
            self.setInsertPos(pos)
            self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEMOVE:
            if wParam & win32con.MK_LBUTTON:
                x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
                pos = self.getInsertPosAtXY(x, y)
                if pos:
                    self.setSelRange('NotSet', pos)
                    self.setInsertPos(pos)
                self.invalidWindow()
            return True
        if msg == win32con.WM_MOUSEWHEEL:
            delta = (wParam >> 16) & 0xffff
            if delta & 0x8000:
                delta = delta - 0xffff - 1
            delta = delta // 120
            self.scroll(- delta)
            win32gui.InvalidateRect(self.hwnd, None, True)
        if msg == win32con.WM_IME_CHAR or msg == win32con.WM_CHAR:
            self.onKey(wParam)
            return True
        if msg == win32con.WM_KEYDOWN:
            if wParam == win32con.VK_DELETE:
                self.onKeyDelete()
            elif wParam == win32con.VK_BACK:
                self.onKeyBackspace()
            elif wParam == ord('V') and self.getKeyState(win32con.VK_CONTROL):
                self.doPaste()
            elif wParam == ord('C') and self.getKeyState(win32con.VK_CONTROL):
                self.doCopy(self.selRange)
            elif wParam == ord('X') and self.getKeyState(win32con.VK_CONTROL):
                self.doCut()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    editor = RichEditor()
    html = '<T fs=1 c=ff0000 bg=aa33dd >Hello World</T>\n<T fs=5 fz=20 >卡拉ACB123</T>卡拉DEF123\n卡拉CEA123'
    editor.model.insertRichText(Pos(0, 0), html)
    editor.insertPos = Pos(2, 0)
    editor.createWindow(None, (0, 0, 700, 400), style = win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(editor.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()