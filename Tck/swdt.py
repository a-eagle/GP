import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re, io, json
from xml.etree import ElementTree

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, tck_orm, lhb_orm
from Common import base_win, ext_win
from Tck import kline_utils, cache, mark_utils, utils

# 思维导图
class SwdtItem:
    ATTRS = {'fontSize': int, 'color': int, 'bgColor': int, 'borderWidth': int, 'borderColor': int, 'text': str, 'visible': str}

    def __init__(self, fontSize = 14, color = 0x0, bgColor = 0xffffff, borderWidth = 1, borderColor = 0, text = '', visible = 'true') -> None:
        self.text = text
        self.fontSize = fontSize
        self.color = color
        self.bgColor = bgColor
        self.borderWidth = borderWidth
        self.borderColor = borderColor
        self.visible = visible
        self.children = None # an list of Item

class SwdtModel:
    def __init__(self) -> None:
        self.data = [] # list of Item

    def _isColorAttr(self, attr):
        return 'color' in attr.lower()

    def _dumpsItem(self, item):
        buf = io.StringIO()
        buf.write('<item ')
        for k in SwdtItem.ATTRS:
            v = getattr(item, k)
            if self._isColorAttr(k):
                r, g, b = v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff
                v = f'{r :02X}{g :02X}{b :02X}'
            buf.write(f'{k}="{v}" ')
        buf.write('>')
        if item.children:
            for ch in item.children:
                chs = self._dumpsItem(ch)
                buf.write(chs)
        buf.write('</item>')
        return buf.getvalue()

    def dumps(self):
        buf = io.StringIO()
        buf.write('<items>')
        for it in self.data:
            its = self._dumpsItem(it)
            buf.write(its)
        buf.write('</items>')
        return buf.getvalue()

    def _loadsItem(self, elem : ElementTree.Element):
        item = SwdtItem()
        for k in SwdtItem.ATTRS:
            v = elem.get(k, None)
            if v is None:
                continue
            if self._isColorAttr(k):
                v = int(v, 16)
                r, g, b = (v >> 16) & 0xff, (v >> 8) & 0xff, (v & 0xff)
                v = r | (g << 8) | (b << 16)
            else:
                v = SwdtItem.ATTRS[k](v)
            setattr(item, k, v)
        item.children = []
        for ch in elem:
            che = self._loadsItem(ch)
            item.children.append(che)
        return item

    def loads(self, str_):
        self.data.clear()
        if not str_:
            return
        elem = ElementTree.fromstring(str_)
        for ch in elem:
            item = self._loadsItem(ch)
            self.data.append(item)

class SwdtWindow(base_win.BaseWindow):
    ITEM_SPACE_X = 60
    ITEM_SPACE_Y = 10
    ITEM_INNER_X = 20
    ITEM_INNER_Y = 10

    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xfdfdfd
        self.model = SwdtModel()
        self.needRebuild = True

    def _rdVisible(self, items : list, idx):
        item = items[idx]
        if item.visible == 'false':
            items.pop(idx)
            return
        if not item.children:
            return
        for i in range(len(item.children) - 1, -1, -1):
            self._rdVisible(item.children, i)

    def loads(self, strs):
        self.model.loads(strs)
        for idx in range(len(self.model.data) - 1, -1, -1):
            self._rdVisible(self.model.data, idx)
        self.needRebuild = True
        self.invalidWindow()
    
    def buildViews(self):
        hdc = win32gui.GetDC(self.hwnd)
        for item in self.model.data:
            self._calcItemSize(item, hdc)
        for item in self.model.data:
            self._calcItemXY(item, 0, 0)
        win32gui.ReleaseDC(self.hwnd, hdc)

    def _calcItemSize(self, item : SwdtItem, hdc):
        self.drawer.use(hdc, self.drawer.getFont(fontSize = item.fontSize))
        iw, ih = 0, 0
        for row in item.text.split('\n'):
            _iw, _ih = win32gui.GetTextExtentPoint32(hdc, row)
            iw = max(_iw, iw)
            ih += _ih
        item.width = iw + self.ITEM_INNER_X + item.borderWidth * 2
        item.height = ih + self.ITEM_INNER_Y + item.borderWidth * 2
        if not item.children:
            return
        for it in item.children:
            self._calcItemSize(it, hdc)

    def _calcItemXY(self, item : SwdtItem, sx, sy):
        item.cy = sy
        item.x = sx
        if not item.children:
            item.ch = item.height
            item.y = sy
            return item.height
        cy = sy
        cx = sx + item.width + self.ITEM_SPACE_X
        for c in item.children:
            sh = self._calcItemXY(c, cx, cy)
            cy += sh + self.ITEM_SPACE_Y
        ch = cy - sy - self.ITEM_SPACE_Y
        ch = max(ch, item.height)
        item.y = sy + (ch - item.height) // 2
        item.ch = ch
        return ch

    def onDraw(self, hdc):
        if self.needRebuild:
            self.needRebuild = False
            self.buildViews()
        x = 10
        y = 10
        for it in self.model.data:
            win32gui.SetViewportOrgEx(hdc, x, y)
            y += it.ch + self.ITEM_SPACE_Y
            self.drawItem(hdc, it)
        win32gui.SetViewportOrgEx(hdc, 0, 0) # must set to 0, 0 ??

    def drawItem(self, hdc, item : SwdtItem):
        rc = (item.x, item.y, item.x + item.width, item.y + item.height)
        self.drawer.fillRect(hdc, rc, item.bgColor)
        self.drawer.drawRect(hdc, rc, item.borderColor, item.borderWidth)
        self.drawer.use(hdc, self.drawer.getFont(fontSize = item.fontSize))
        self.drawer.drawText(hdc, item.text, rc, item.color, align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_WORDBREAK)
        if not item.children:
            return
        first = item.children[0]
        last = item.children[-1]
        hey = (rc[3] + rc[1]) // 2
        FDX = 2
        if len(item.children) == 1:
            self.drawer.drawLine(hdc, rc[2], hey, first.x, hey, color = 0x303030, width = FDX)
            self.drawItem(hdc, first)
            return
        hex = rc[2] + self.ITEM_SPACE_X // 2
        self.drawer.drawLine(hdc, rc[2] - 1, hey, hex, hey, color = 0x303030, width = FDX)
        self.drawer.drawLine(hdc, hex, first.y + first.height // 2, hex, last.y + last.height // 2 , color = 0x303030, width = 2)
        for it in item.children:
            self.drawer.drawLine(hdc, hex, it.y + it.height // 2, it.x, it.y + it.height // 2, color = 0x303030, width = FDX)
            self.drawItem(hdc, it)
        
    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            pass
        return super().winProc(hwnd, msg, wParam, lParam)

xml = """
<items>
    <item text="你毁吵中国不是工吵浊" color="000000"  bgColor="FFAA88" fontSize="20" visible = "false">
        <item text="sub ----- 1&#xA;不错啊" > 
            <item text="sub -======= 21" visible = "false" > </item>
            <item text="sub -======= 22" > </item>
        </item>
        <item text="sub ----- 2" visible = "false"> 
            <item text="sub -======= 31" > </item>
            <item text="sub -======= 32" > </item>
        </item>
        <item text="sub ----- 3" > 
            <item text="sub -======= 41" borderColor="FF0088" > </item>
            <item text="sub -======= 42" > </item>
        </item>
    </item>
    <item text="BBBBBBBB" color="000000"  bgColor="FFAA88" fontSize="20" >
        <item text="sub -======= AA" > </item>
    </item>
</items>
"""

if __name__ == '__main__':
    win = SwdtWindow()
    win.createWindow(None, (100, 100, 800, 600), style = win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win.loads(xml)
    #testOptionsWindow()
    win32gui.PumpMessages()