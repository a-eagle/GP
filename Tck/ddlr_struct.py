import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from Download import datafile
from Download import henxin, ths_ddlr
from THS import ths_win
from Common import base_win
import ddlr_detail, kline_utils, kline

class DddlrStructWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        dw = win32api.GetSystemMetrics (win32con.SM_CXFULLSCREEN)
        self.colsNum = min(dw // 330, 5)
        cols = ('1fr ' * self.colsNum).strip().split(' ')
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.listWins = []
        self.daysLabels = []
        self.checkBox = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        datePicker = base_win.DatePicker()
        datePicker.createWindow(self.hwnd, (0, 0, 200, 30))
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox.createWindow(self.hwnd, (0, 0, 200, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, datePicker)
        absLayout.setContent(230, 0, self.checkBox)
        self.layout.setContent(0, 0, absLayout)
        def formateFloat(colName, val, rowData):
            return f'{val :.02f}'
        headers = [{'title': '', 'width': 40, 'name': '#idx' },
                   {'title': '股票名称', 'width': 0, 'stretch': 1, 'name': 'name', 'sortable':True  },
                   {'title': '净流入', 'width': 70, 'name': 'total', 'formater': formateFloat, 'sortable':True  },
                   {'title': '流入', 'width': 70, 'name': 'in', 'formater': formateFloat, 'sortable':True },
                   {'title': '流出', 'width': 70, 'name': 'out', 'formater': formateFloat , 'sortable':True }]
        for i in range(len(self.layout.templateColumns)):
            win = base_win.TableWindow()
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            win.headers = headers
            self.layout.setContent(2, i, win)
            self.listWins.append(win)
            lw = win32gui.CreateWindow('STATIC', '', win32con.WS_VISIBLE|win32con.WS_CHILD, 0, 0, 1, 1, self.hwnd, None, None, None)
            self.daysLabels.append(lw)
            self.layout.setContent(1, i, lw)
            win.addListener(self.onDbClick, i)
            win.addListener(self.onContextMenu, i)
        datePicker.addListener(self.onSelDayChanged, None)
        # init view
        today = datetime.date.today()
        day = today.strftime('%Y%m%d')
        self.updateDay(day)

    def onContextMenu(self, evt, tabIdx):
        if evt.name != 'ContextMenu':
            return
        win : base_win.TableWindow = self.listWins[tabIdx]
        if win.selRow < 0:
            return
        wdata = win.sortData or win.data
        code = wdata[win.selRow]['code']
        model = [{'title': '关联选中', 'name': 'GLXZ'}]
        menu = base_win.PopupMenu.create(self.hwnd, model)
        menu.addListener(self.onMenuItemSelect, (tabIdx, code))
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def findIdx(self, win, code):
        datas = win.sortData or win.data
        for i, d in enumerate(datas):
            if d['code'] == code:
                return i
        return -1

    def glxz(self, tabIdx, code):
        curTabWin = self.listWins[tabIdx]
        sortHeader, sortSate = curTabWin.sortHeader['header'], curTabWin.sortHeader['state']
        shIdx = -1
        for i, hd in enumerate(curTabWin.headers):
            if sortHeader == hd:
                shIdx = i
                break
        for i, win in enumerate(self.listWins):
            if i == tabIdx:
                continue
            if shIdx < 0:
                win.setSortHeader(None, None)
            else:
                win.setSortHeader(win.headers[shIdx], sortSate)
            idx = self.findIdx(win, code)
            win.selRow = idx
            win.showRow(idx)
            win.invalidWindow()
    
    def onMenuItemSelect(self, evt, args):
        if evt.name != 'Select':
            return
        if evt.item['name'] == 'GLXZ':
            tabIdx, code = args
            self.glxz(tabIdx, code)

    def onDbClick(self, evt, idx):
        if evt.name != 'DbClick' and evt.name != 'RowEnter':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(self, data)
        else:
            kline_utils.openInCurWindow(self, data)

    def onSelDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
        self.updateDay(evt.day)

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        day = day.replace('-', '')
        q = ths_orm.THS_DDLR.select(ths_orm.THS_DDLR.day).distinct().where(ths_orm.THS_DDLR.day <= day).order_by(ths_orm.THS_DDLR.day.desc()).limit(self.colsNum).tuples()
        for i, d in enumerate(q):
            cday = d[0]
            ds = ths_orm.THS_DDLR.select().where(ths_orm.THS_DDLR.day == cday)
            datas = [d.__data__ for d in ds]
            for xd in datas:
                xd['in'] = xd['activeIn'] + xd['positiveIn']
                xd['out'] = xd['activeOut'] + xd['positiveOut']
            self.listWins[i].setData(datas)
            self.listWins[i].invalidWindow()
            sday = cday[0 : 4] + '-' + cday[4 : 6] + '-' + cday[6 : ]
            win32gui.SetWindowText(self.daysLabels[i], sday)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    tab = base_win.TableWindow()
    tab.createWindow(None, (0, 0, 400, 100), win32con.WS_OVERLAPPEDWINDOW)
    tab.headers = [{'title': '', 'width': 40, 'name': '#idx' },
                   {'title': '股票名称', 'width': 0, 'stretch': 1, 'name': 'name' },
                   {'title': '净流入', 'width': 70, 'name': 'total' },
                   {'title': '流入', 'width': 70, 'name': 'in'},
                   {'title': '流出', 'width': 70, 'name': 'out'}]
    win32gui.ShowWindow(tab.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()