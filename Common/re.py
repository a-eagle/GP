import win32gui, win32con , win32api, win32ui, win32gui_struct, win32clipboard # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools, io
import ctypes

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Word:
    def __init__(self, fontSize, char = '') -> None:
        self.char = char
        self.fontSize = fontSize
        self.bold = False
        self.italic = False
        self.underline = False
        self.bgColor = None
        self.color = None
        self.width = 0
        self.height = 0

    def getFont(self):
        drawer = base_win.Drawer.instance()
        weight = 700 if self.bold else 0
        font = drawer.getFont(fontSize = self.fontSize, weight = weight, italic = self.italic, underline = self.underline)
        return font

    def calcSize(self, hdc):
        if self.height > 0:
            return
        self.height = self.fontSize
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
        self.width = self.height = 0

    def isSameStyle(self, w):
        if not w:
            return False
        return self.fontSize == w.fontSize and self.bold == w.bold and \
            self.italic == w.italic and self.underline == w.underline and \
            self.bgColor == w.bgColor and self.color == w.color

class Line:
    LINE_PADDING = 6

    def __init__(self) -> None:
        self.lineHeight = 0
        self.words = []

    def invalidSize(self):
        self.lineHeight = 0
        for w in self.words:
            w.invalidSize()

    def changed(self):
        self.lineHeight = 0

    def calcSize(self, hdc):
        for w in self.words:
            w.calcSize(hdc)
        self.calcLineHeight(hdc)

    def calcLineHeight(self, hdc):
        if self.lineHeight > 0:
            return
        h = 0
        for d in self.words:
            d.calcSize(hdc)
            h = max(h, d.height)
        h += self.LINE_PADDING
        self.lineHeight = h

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
        return self.row == th.row and self.col == th.col

class RichEditorModel:
    def __init__(self) -> None:
        self.defaultFontSize = 16
        self.lines = [Line()]

    def insertWord(self, pos : Pos, word : Word):
        if not pos or not word or not word.char:
            return
        if not self.isValidPos(pos):
            return
        line : Line = self.lines[pos.row]
        if word.char != '\n':
            line.words.insert(pos.col, word)
            line.changed()
            pos.col += 1
            return
        pre = line.words[0 : pos.col]
        suff = line.words[pos.col : ]
        line.words = pre
        line.changed()
        suffLine = Line()
        suffLine.words = suff
        self.lines.insert(pos.row + 1, suffLine)
        pos.row += 1
        pos.col = 0

    def beforeDeleteWord(self, pos : Pos):
        if not self.isValidPos(pos):
            return
        line : Line = self.lines[pos.row]
        if pos.col == 0:
            if pos.row == 0:
                return
            pre : Line = self.lines[pos.row - 1]
            self.lines.pop(pos.row)
            pre.words.extend(line.words)
            line.words.clear()
            pre.changed()
        else:
            line.words.pop(pos.col - 1)
            pos.col -= 1
            line.changed()

    def afterDeleteWord(self, pos : Pos):
        if not self.isValidPos(pos):
            return
        line : Line = self.lines[pos.row]
        if pos.col == len(line.words):
            if pos.row == len(self.lines) - 1:
                return
            next : Line = self.lines[pos.row + 1]
            line.words.extend(next.words)
            self.lines.pop(pos.row + 1)
            next.words.clear()
            line.changed()
        else:
            line.words.pop(pos.col)
            line.changed()

    def isValidPos(self, pos : Pos):
        if not pos:
            return False
        if pos.col < 0 or pos.row < 0 or pos.row >= len(self.lines):
            return False
        line : Line = self.lines[pos.row]
        return pos.col <= len(line.words)

    def getPlainText(self, startPos : Pos, endPos : Pos):
        rs = self.getWords(startPos, endPos)
        if not rs:
            return ''
        text = io.StringIO()
        for w in rs:
            text.write(w.char)

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
            rs.append(Word(1, '\n'))
            rs.extend(sline.words[0 : len(sline.words)])
        sline : Line = self.lines[endPos.row]
        rs.append(Word(1, '\n'))
        rs.extend(sline.words[0 : endPos.col])
        return rs

    def getRichText(self, startPos : Pos, endPos : Pos):
        rs = self.getWords(startPos, endPos)
        if not rs:
            return ''
        text = io.StringIO()
        groups = []
        last : Word = None
        for w in rs:
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
            if isinstance(ws, str):
                text.write(ws)
                continue
            first = ws[0]
            text.write(f'<Text fs={self.getSerializeFontStyle(first)} c={first.color :X} bg={first.bgColor :X} >')
            for w in ws:
                text.write(w.char)
            text.write('</Text>')
        return text.getvalue()

    def getSerializeFontStyle(self, w : Word):
        fs = 0
        if w.bold: fs |= 1
        if w.italic: fs |= 2
        if w.underline: fs |= 4
        z = w.fontSize or self.defaultFontSize
        fs |= z << 8
        return fs

    def insertRichText(self, pos : Pos, text):
        if not text or not self.isValidPos(pos):
            return
        i = 0
        while True:
            ei, w = self._pullNext(i, text)
            if isinstance(w, list):
                for m in w:
                    self.insertWord(pos, m)
            elif isinstance(w, Word):
                self.insertWord(pos, w)
            else:
                break
            i = ei

    def _pullNext(self, i, text : str):
        if i >= len(text):
            return i, None
        if text[i] != '<':
            return i + 1, Word(self.defaultFontSize, text[i])
        ei = text.find('>', i)
        if ei < 0:
            return ei, None

        fs = self._getNumAttrVal('fs', text, i, ei)
        color = self._getNumAttrVal('c', text, i, ei)
        bgColor = self._getNumAttrVal('bg', text, i, ei)
        si = ei + 1
        ei = text.find('</Text>', si)
        if ei < 0:
            return -1, None
        rs = []
        for i in range(si, ei):
            w = Word(self.defaultFontSize)
            if fs >> 8: w.fontSize = fs >> 8
            if fs & 1: w.bold = True
            if fs & 2: w.italic = True
            if fs & 4: w.underline = True
            if color != None: w.color = color
            if bgColor != None: w.bgColor = bgColor
            w.char = text[i]
            rs.append(w)
        ei += 7
        return ei, rs

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

    def calcSize(self, hdc):
        for w in self.lines:
            w.calcSize(hdc)

class RichEditorRender:
    def __init__(self) -> None:
        self.lines = [] # Line objects

    def getXY(self, pos : Pos):
        pass

class RichEditor(base_win.BaseEditor):
    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.css['textColor'] = 0x202020
        self.css['borderColor'] = 0xdddddd
        self.css['selBgColor'] = 0xf0c0c0
        self.css['lineNoBgColor'] = 0xE0E0E0
        self.css['lineNoTextColor'] = 0xD3B291
        self.css['paddings'] = (40, 0, 5, 0)
        self.startRow = 0
        self.model = RichEditorModel()
        self.insertPos = None # Pos object
        self.selRange = None # (begin-Pos, end-Pos)

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        self._onDraw(hdc, W, H)

    def _onDraw(self, hdc, W, H):
        pds = self.css['paddings']
        lineNoRect = (0, pds[1], pds[0], H)
        self.drawer.fillRect(hdc, lineNoRect, self.css['lineNoBgColor'])

        self.model.calcSize(hdc)
        #self.drawSelRange(hdc)
        sy = pds[1]
        sx = pds[0]
        for i in range(self.startRow, len(self.model.lines)):
            if sy >= H - pds[3]:
                break
            line : Line = self.model.lines[i]
            rc = (sx, sy, W - pds[2], sy + line.lineHeight)
            self.drawLine(hdc, i, rc)

            lineNo = i - self.startRow + 1
            rc2 = (lineNoRect[0], rc[1], lineNoRect[2], rc[3])
            self.drawer.drawText(hdc, f'{lineNo :>3d}', rc2, color = self.css['lineNoTextColor'], align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            sy += line.lineHeight

    def drawLine(self, hdc, lineIdx, rc):
        line = self.model.lines[lineIdx]
        #groups = []
        #last : Word = None
        #for w in line.words:
        #    if w.isSameStyle(last):
        #        groups[-1].append(w)
        #    else:
        #        groups.append([w])
        #    last = w
        sx = rc[0]
        for w in line.words:
            self.drawer.use(hdc, w.getFont())
            my = rc[1] + (line.lineHeight - w.height) // 2
            mrc = (sx, my, sx + w.width, my + w.height)
            if w.bgColor != None:
                self.drawer.fillRect(hdc, mrc, w.bgColor)
            self.drawer.drawText(hdc, w.char, mrc, color = w.color, align = win32con.DT_LEFT)
            sx += w.width

if __name__ == '__main__':
    editor = RichEditor()
    editor.model.insertRichText(Pos(0, 0), '<Text fs=5 c=daefc0 bg=aa33dd> Hello World 你发</Text>')
    editor.createWindow(None, (0, 0, 700, 400), style = win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(editor.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()