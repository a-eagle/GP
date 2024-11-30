import win32gui, win32con , win32api, win32ui # pip install pywin32
import os, sys, io
from PIL import Image as PIL_Image

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class CellEditor(base_win.Editor):
    def __init__(self) -> None:
        super().__init__()
        self.css['borderColor'] = 0x2020D0
        self.row = 0
        self.col = 0
        self.inEdit = False

# headers = [ {..., editable: True | False(default)}, ... ]
# listeners = 'CellChanged' = {src, row, col, data(is row data), header, model}
#             'ClickCell' = {src, row, col, data(is row data), header, model}
class EditTableWindow(base_win.TableWindow):
    def __init__(self) -> None:
        super().__init__()
        self.editor = CellEditor()
        self.editor.addListener(self.onPressEnter)
        self.trimText = True

    def beginEdit(self, row, col):
        if row < 0 or col < 0:
            return
        self.editor.inEdit = True
        self.editor.row = row
        self.editor.col = col
        sx = self.getColumnX(col)
        sy = self.getYOfRow(row)
        cw = self.getColumnWidth(col, self.headers[col]['name'])
        ch = self.rowHeight
        if not self.editor.hwnd:
            self.editor.createWindow(self.hwnd, (0, 0, 1, 1))
        win32gui.SetWindowPos(self.editor.hwnd, 0, sx, sy, cw, ch, win32con.SWP_NOZORDER)
        hd = self.headers[col]
        rowData = self.data[row]
        cellVal = rowData[hd['name']]
        if cellVal == None:
            cellVal = ''
        self.editor.setText(str(cellVal))
        W, H = self.getClientSize()
        win32gui.ShowWindow(self.editor.hwnd, win32con.SW_SHOW)
        win32gui.SetFocus(self.editor.hwnd)
        self.editor.setInsertPos(len(self.editor.text))
        self.editor.setSelRange(0, len(self.editor.text))
        self.editor.invalidWindow()

    def endEdit(self):
        if not self.editor.inEdit:
            return
        self.editor.inEdit = False
        win32gui.ShowWindow(self.editor.hwnd, win32con.SW_HIDE)
        win32gui.SetFocus(self.hwnd)
        row = self.editor.row
        col = self.editor.col
        hd = self.headers[col]
        rowData = self.data[row]
        #cellVal = rowData[hd['name']]
        #if cellVal == self.editor.text:
        #    return
        txt = self.editor.text.strip() if self.trimText else self.editor.text
        rowData[hd['name']] = txt
        self.notifyListener(self.Event('CellChanged', self, row = row, col = col, data = rowData, header = hd, model = self.data))

    def onPressEnter(self, evt, args):
        if evt.name == 'PressEnter':
            self.endEdit()
        elif evt.name == 'PressTab':
            col = self.editor.col + 1
            self.endEdit()
            if col < len(self.headers):
                self.beginEdit(self.editor.row, col)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONDOWN:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.endEdit()
            self.onClick(x, y)
            return True
        if msg == win32con.WM_LBUTTONUP:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            col = self.getColAtX(x)
            if row < 0 or col < 0:
                return True
            dx = self.sortData if self.sortData else self.data
            self.notifyListener(self.Event('ClickCell', self, row = row, col = col, data =  dx[row], model = dx))
            return True
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            row = self.getRowAtY(y)
            col = self.getColAtX(x)
            if row < 0 or col < 0:
                return True
            if self.headers[col].get('editable', False):
                self.beginEdit(row, col)
                return True
            dx = self.sortData if self.sortData else self.data
            self.notifyListener(self.Event('DbClick', self, x = x, y = y, row = row, data = dx[row], model = dx))
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class CellRenderWindow(base_win.BaseWindow):

    # templateColumns = 分列, 设置宽度  整数固定: 200 ; 自动: 'auto'; 片段: 1fr | 2fr; 百分比: 15% 
    #       Eg: (200, '1fr', '2fr', '15%')
    def __init__(self, templateColumns, colsGaps = 5) -> None:
        super().__init__()
        self.templateColumns = templateColumns
        self.colsGaps = colsGaps
        self.paddings = (2, 2, 2, 2)
        self.rows = []

    # rowInfo = { height: int | function(cell object), 
    #             bgColor: None | int | function(cell object),
    #             margin: None | int | (top, bottom) margin
    #           }
    # cell = { text: str | function(cell object),
    #          paddings: None | (l, t, r, b)
    #          span: int (default is 1) 跨列数
    #          bgColor: None | int | function(cell object), 
    #          color: None | int | function(cell object),
    #          textAlign: int | None,
    #          fontSize: int | None, 
    #          fontWeight: int | None 
    #          render: None | function(rowInfo, cell, win, hdc, rect)
    #       }
    # cell = function(rowInfo, cellIdx)
    def addRow(self, rowInfo, *cells):
        self.rows.append({'rowInfo': rowInfo, 'cells': cells})

    def getContentHeight(self):
        h = self.paddings[1] + self.paddings[3]
        for row in self.rows:
            rowInfo = row['rowInfo']
            margin = rowInfo.get('margin', 0)
            if isinstance(margin, int):
                margin = (margin, margin)
            h += margin[0] + rowInfo['height'] + margin[1]
        return h

    def insertRow(self, insertIdx, rowInfo, *cells):
        self.rows.insert(insertIdx, {'rowInfo': rowInfo, 'cells': cells})
    
    def getColWidth(self, col, span, colsWidth):
        if span <= 0:
            return 0
        w = 0
        j = 0
        for i in range(0, span):
            if i + col < len(colsWidth):
                w += colsWidth[i + col]
                j += 1
        if j > 0:
            w += (j - 1) * self.colsGaps
        return w

    def _drawRow(self, hdc, rc, rowInfo):
        if 'bgColor' in rowInfo and type(rowInfo['bgColor']) == int:
            self.drawer.fillRect(hdc, rc, rowInfo['bgColor'])

    def _drawCells(self, hdc, cells, colsWidth, sx, sy, rowInfo):
        colIdx = 0
        for i in range(len(cells)):
            cell = cells[i]
            if callable(cell):
                cell = cell(rowInfo, i)
            if cell == None:
                cell = {}
            span = cell.get('span', 1)
            cw = self.getColWidth(colIdx, span, colsWidth)
            rc2 = [sx, sy, sx + cw, sy + rowInfo['height']]
            self.drawCell(hdc, rc2, cell, i, rowInfo)
            sx += cw + self.colsGaps
            colIdx += span

    def onDraw(self, hdc):
        W, H = self.getClientSize()
        CW = W - self.paddings[0] - self.paddings[2]
        colsWidth = self._parseTemplate(self.templateColumns, CW, self.colsGaps)

        sy = self.paddings[1]
        for row in self.rows:
            sx = self.paddings[0]
            rowInfo = row['rowInfo']
            margin = rowInfo.get('margin', 0)
            if isinstance(margin, int):
                margin = (margin, margin)
            sy += margin[0]
            rc = (sx, sy, W - self.paddings[2], sy + rowInfo['height'])
            self._drawRow(hdc, rc, rowInfo)
            cells = row['cells']
            self._drawCells(hdc, cells, colsWidth, sx, sy, rowInfo)
            sy += rowInfo['height'] + margin[1]

    def drawCell(self, hdc, rect, cell, cellIdx, rowInfo):
        if not cell:
            return
        if 'bgColor' in cell and type(cell['bgColor']) == int:
            self.drawer.fillRect(hdc, rect, cell['bgColor'])
        pd = cell.get('paddings', None)
        if pd:
            rect[0] += pd[0]
            rect[1] += pd[1]
            rect[2] -= pd[2]
            rect[3] -= pd[3]
        fontSize = cell.get('fontSize', self.css['fontSize'])
        fontWeight = cell.get('fontWeight', self.css['fontWeight'])
        self.drawer.use(hdc, self.drawer.getFont(fontSize = fontSize, weight = fontWeight))
        color = cell.get('color', self.css['textColor'])
        align = cell.get('textAlign', win32con.DT_LEFT)
        text = cell.get('text', None)
        txt = None
        if isinstance(text, str):
            txt = text
        elif callable(text):
            txt = text(cell)
        self.drawer.drawText(hdc, txt, rect, color = color, align = align)
        render = cell.get('render', None)
        if callable(render):
            render(rowInfo, cell, self, hdc, rect)

    def _parseTemplate(self, template, wh, gap):
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

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)

class RichTextRender:
    def __init__(self, lineHeight = 20) -> None:
        self.specs = []
        self.lineHeight = lineHeight
    
    # text: str | function(args)
    # color: int | function(args)
    # bgColor: int | function(args)
    # fontSize: int
    # args: any param, used for function
    def addText(self, text, color = None, bgColor = None, fontSize = 12, args = None):
        self.specs.append({'text': text, 'color': color, 'bgColor': bgColor, 'fontSize': fontSize, 'args': args})

    def _getAttr(self, spec, attr):
        val = None
        if callable(spec[attr]):
            val = spec[attr](spec['args'])
        else:
            val = spec[attr]
        return val

    def _calcSpecsRect(self, hdc, drawer : base_win.Drawer, rect):
        SX, SY = rect[0], rect[1]
        EX, EY = rect[2], rect[3]
        x, y = SX, SY
        for item in self.specs:
            text = self._getAttr(item, 'text')
            fnt = drawer.getFont(fontSize = item['fontSize'])
            drawer.use(hdc, fnt)
            sw, *_ = win32gui.GetTextExtentPoint32(hdc, text)
            if sw + x <= EX:
                item['rect'] = (x, y, x + sw, y + self.lineHeight)
            else:
                x = SX
                y += self.lineHeight
                item['rect'] = (x, y, x + sw, y + self.lineHeight)
            x += sw

    def draw(self, hdc, drawer : base_win.Drawer, rect):
        sdc = win32gui.SaveDC(hdc)
        W, H = rect[2] - rect[0], rect[3] - rect[1]
        EY = rect[3]
        self._calcSpecsRect(hdc, drawer, rect)
        for item in self.specs:
            rc = item['rect']
            if rc[1] >= EY: #or rc[3] > EY
                continue
            fnt = drawer.getFont(fontSize = self._getAttr(item, 'fontSize'))
            drawer.use(hdc, fnt)
            bg = self._getAttr(item, 'bgColor')
            if type(bg) == int:
                drawer.fillRect(hdc, rc, bg)
            drawer.drawText(hdc, self._getAttr(item, 'text'), rc, color = self._getAttr(item, 'color'), align = win32con.DT_LEFT | win32con.DT_SINGLELINE | win32con.DT_VCENTER)
        win32gui.RestoreDC(hdc, sdc)
            

# ClickItem = {src, item: obj}
class OptionsWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.data = None # list of {'title' : xxx, 'value': xxx, ...}

        self.rects = None # data's rect list
        self.css['paddings'] = (3, 2, 3, 2)
        self.css['itemHorSpace'] = 10
        self.css['itemVerSpace'] = 10
        self.css['itemDelWidth'] = 20
        self.css['itemBgColor'] = 0x202020
        self.css['itemBorderColor'] = 0x404040
        self.css['lineHeight'] = 20
        
        self.editable = True # 是否是可编辑的（可删除）

    def setData(self, data):
        self.data = data
        self._calcRects()
        self.invalidWindow()
    
    def _calcRects(self):
        self.rects = []
        if not self.data:
            return
        ws = []
        hdc = win32gui.GetDC(self.hwnd)
        self.drawer.use(hdc, self.getDefFont())
        for d in self.data:
            title = d.get('title', '')
            cw, *_ = win32gui.GetTextExtentPoint32(hdc, title)
            cw += self.css['itemDelWidth'] + 8
            ws.append(cw)
        win32gui.ReleaseDC(self.hwnd, hdc)
        W, H = self.getClientSize()
        pds = self.css['paddings']
        W -= pds[2]
        LH = self.css['lineHeight']
        sx = pds[0]
        sy = pds[1]
        for w in ws:
            if sx + w > W:
                sx = pds[0]
                sy += LH + self.css['itemVerSpace']
            it = [sx, sy, sx + w, sy + LH]
            self.rects.append(it)
            sx += w + self.css['itemHorSpace']

    def onDraw(self, hdc):
        if not self.data or not self.rects:
            return
        for i, d in enumerate(self.data):
            self.drawItem(hdc, i)

    # return text-rect, del-rect
    def _getTextDelRect(self, idx):
        rc = self.rects[idx]
        if not self.editable:
            return rc, None
        rcText = (rc[0], rc[1], rc[2] - self.css['itemDelWidth'], rc[3])
        rcDel = (rcText[2], rc[1], rc[2], rc[3])
        return rcText, rcDel

    def drawItem(self, hdc, i):
        rcText, rcDel = self._getTextDelRect(i)
        rc = self.rects[i]
        if isinstance(self.css['itemBgColor'], int):
            self.drawer.fillRect(hdc, rc, self.css['itemBgColor'])
        if isinstance(self.css['itemBorderColor'], int):
            self.drawer.drawRect(hdc, rc, self.css['itemBorderColor'])
            if rcDel != None:
                x = rcDel[0]
                self.drawer.drawLine(hdc, x, rc[1], x, rc[3], self.css['itemBorderColor'])
        self.drawer.drawText(hdc, self.data[i].get('title', None), rcText, self.css['textColor'], align=win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        if rcDel != None:
            self.drawer.drawText(hdc, 'x', rcDel, self.css['textColor'], align=win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def onClick(self, x, y):
        if not self.rects:
            return
        for i in range(len(self.rects)):
            rcText, rcDel = self._getTextDelRect(i)
            if rcDel and x >= rcDel[0] and x < rcDel[2] and y >= rcDel[1] and y < rcDel[3]: # in del rect
                self.rects.pop(i)
                self.data.pop(i)
                self.invalidWindow()
                break
            if x >= rcText[0] and x < rcText[2] and y >= rcText[1] and y < rcText[3]: # in text rect:
                self.notifyListener(self.Event('ClickItem', self, item = self.data[i]))
                break

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_LBUTTONUP:
            x, y = (lParam & 0xffff), (lParam >> 16) & 0xffff
            self.onClick(x, y)
            return True
        if msg == win32con.WM_SIZE and  wParam != win32con.SIZE_MINIMIZED:
            self._calcRects()
            self.invalidWindow()
            # no return, go through
        return super().winProc(hwnd, msg, wParam, lParam)

def testCellRenderWin():
    win = CellRenderWindow((50, 100, '10%', '1fr', '1fr'), 10)
    win.addRow({'height': 40, 'margin': 20}, 
                {'text': '(0, 0)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'text': '(0, 1)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'text': '(0, 2)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                {'bgColor':0xaabbcc},
                {'text': '(0, 4)', 'color': 0xff00ff, 'bgColor':0xaabbcc},
                )
    win.addRow({'height': 80, 'bgColor_': 0xdd88ff, 'margin': 5},
                {'text': '(0, 0)', 'color': 0xff00ff, 'bgColor':0xdd88ff, 'span': 2},
                {'text': '(0, 2)', 'color': 0xff00ff, 'bgColor':0xdd88ff, 'span': 2},
                {'text': '(0, 4)', 'color': 0xff00ff, 'bgColor':0xdd88ff,  'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE},
                )
    win.createWindow(None, (100, 100, 600, 400), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)

def testOptionsWindow():
    win = OptionsWindow()
    win.editable = True
    win.createWindow(None, (100, 100, 300, 250), win32con.WS_OVERLAPPEDWINDOW)
    data = []
    for i in range(20):
        data.append({'title': f'Value {i}'})
    win.setData(data)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)

class ImageWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.img : PIL_Image = None

    def onDraw(self, hdc):
        win32gui.BitBlt(hdc, 0, 0, )
        pass
