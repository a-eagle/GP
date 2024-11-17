import win32gui, win32con , win32api, win32ui, win32gui_struct, win32clipboard # pip install pywin32
import threading, time, datetime, sys, os, copy, calendar, functools
import ctypes

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Word:
    def __init__(self, fontSize) -> None:
        self.char = ''
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

    def invalidSize(self):
        self.width = self.height = 0

class Line:
    LINE_PADDING = 6

    def __init__(self, fontSize) -> None:
        self._fontSize = fontSize
        self._lineHeight = fontSize + self.LINE_PADDING
        self.words = []

    def invalidSize(self):
        self._lineHeight = 0
        for w in self.words:
            w.invalidSize()

    def calcSize(self, hdc):
        for w in self.words:
            w.calcSize(hdc)
        self.calcLineHeight()

    def calcLineHeight(self):
        h = self._fontSize
        for d in self.words:
            d.calcSize()
            h = max(h, d.height)
        h += self.LINE_PADDING
        self._lineHeight = h
        return h

    def insertWord(self, col, word : Word):
        if not word:
            return
        if col >= 0 and col <= len(self.words):
            self.words.insert(word)

class Pos:
    def __init__(self, row = 0, col = 0) -> None:
        self.row = row
        self.col = col

class RichEditorModel:
    def __init__(self) -> None:
        self.lines = [] # Line objects

    def insertLine(self, lineIdx, line : Line):
        if not line:
            return
        if lineIdx >= 0 and lineIdx <= len(self.lines):
            self.lines.insert(lineIdx, line)

    def insertWord(self, pos : Pos, word : Word):
        if not pos or not word:
            return
        if pos.row < 0 or pos.row >= len(self.lines):
            return
        line : Line = self.lines[pos.row]
        line.insertWord(pos.col, word)

    # before: True: delete before | False: delete after
    def deleteWord(self, pos : Pos, before : bool):
        if not pos:
            return
        if pos.row < 0 or pos.row >= len(self.lines):
            return
        line : Line = self.lines[pos.row]
        


class RichEditorRender:
    def __init__(self) -> None:
        self.lines = [] # Line objects

    def getXY(self, pos : Pos):
        pass
