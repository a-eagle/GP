import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from Download import datafile
from THS import ths_win
from Common import base_win
import mark_utils, kline_utils

MARK_KIND = 'vol-lb'

class VolLBWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        dw = win32api.GetSystemMetrics (win32con.SM_CXFULLSCREEN)
        self.colsNum = 3
        cols = ('1fr ' * self.colsNum).strip().split(' ')
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.listWins = []
        self.daysLabels = []
        self.checkBox = None
        self.dfs = {}
        self.lastDay = 0
        self.codeNames = {}

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
        def formateFloat1(colName, val, rowData):
            return f'{val :.01f}'
        def formateZF(colName, val, rowData):
            return f'{val :.02f}%'
        headers = [{'title': '', 'width': 40, 'name': '#idx' },
                   {'title': 'M', 'width': 20, 'name': 'markColor', 'render': mark_utils.markColorBoxRender, 'sortable':True },
                   {'title': '股票名称', 'width': 80, 'name': 'name', 'render': mark_utils.markColorTextRender},
                   {'title': '行业', 'width': 0, 'name': 'hy', 'stretch': 1, 'render_': mark_utils.markColorTextRender, 'sortable':True},
                   {'title': '成交额', 'width': 70, 'name': 'amount', 'sortable':True, 'formater': formateFloat},
                   {'title': '量比', 'width': 60, 'name': 'lb', 'sortable':True , 'formater': formateFloat1},
                   {'title': '涨幅', 'width': 70, 'name': 'zf', 'sortable':True , 'formater': formateZF}
                   ]
        for i in range(len(self.layout.templateColumns)):
            win = base_win.TableWindow()
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            win.headers = headers
            self.layout.setContent(2, i, win)
            self.listWins.append(win)
            lw = base_win.Label()
            lw.createWindow(self.hwnd, (0, 0, 1, 1))
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
        model = mark_utils.getMarkModel(True)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        menu.addListener(self.onMenuItemSelect, (tabIdx, code, wdata[win.selRow]))
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def findIdx(self, win, code):
        datas = win.sortData or win.data
        for i, d in enumerate(datas):
            if d['code'] == code:
                return i
        return -1
    
    def onMenuItemSelect(self, evt, args):
        if evt.name != 'Select':
            return
        tabIdx, code, rowData = args
        win = self.listWins[tabIdx]
        keys = {'kind' : MARK_KIND, 'code' : code, 'day': rowData['day']}
        mark_utils.saveOneMarkColor(keys, evt.item['markColor'], name = rowData['name'])
        rowData['markColor'] = evt.item['markColor']
        win.invalidWindow()

    def onDbClick(self, evt, idx):
        if evt.name != 'DbClick' and evt.name != 'RowEnter':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInCurWindow_Code(self, data)
        else:
            kline_utils.openInCurWindow_Code(self, data)

    def onSelDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
        self.updateDay(evt.day)

    def loadOneCode(self, code, maxDay, dayNum, rs, names):
        if code in self.dfs:
            df = self.dfs[code]
        else:
            df = self.dfs[code] = datafile.DataFile(code, datafile.DataFile.DT_DAY)
            df.loadData(datafile.DataFile.FLAG_ALL)
        idx = df.getItemIdx(maxDay)
        if idx < 0 or idx < dayNum * 2:
            return
        name = names.get(code, None)
        for i in range(dayNum):
            cur = df.data[idx - i]
            pre = df.data[idx - 1 - i]

            lb = cur.amount / pre.amount
            a = cur.amount / 100000000 # 亿元
            if a < 3.5 or lb < 1.5: # 量比1.5以上, 成交额3.5亿以上
                continue
            item = {}
            item['code'] = code
            if name:
                item.update(name)
            item['zf'] = (cur.close - pre.close) / pre.close * 100 # zhang fu
            item['lb'] = lb
            item['amount'] = a
            item['day'] = f'{cur.day // 10000}-{cur.day // 100 % 100 :02d}-{cur.day % 100 :02d}'
            if cur.day not in rs:
                rs[cur.day] = []
            rs[cur.day].append(item)

    def loadAll(self, day):
        if not self.codeNames:
            ns = ths_orm.THS_GNTC.select(ths_orm.THS_GNTC.code, ths_orm.THS_GNTC.name, ths_orm.THS_GNTC.hy).tuples()
            for n in ns:
                self.codeNames[n[0]] = {'name': n[1], 'hy': n[2]}
        days = datafile.DataFileUtils.calcDays(20230101)
        codes = list(self.dfs.keys()) or datafile.DataFileUtils.listAllCodes()
        if days[-1] != self.lastDay:
            self.dfs.clear()
            self.lastDay = days[-1]
        for i in range(1, len(days)):
            if days[i] == day:
                break
            if days[i] > day:
                day = days[i - 1]
                break
        if day > days[-1]:
            day = days[-1]
        rs = {}
        for c in codes:
            self.loadOneCode(c, day, self.colsNum, rs, self.codeNames)
        daysOrder = list(rs.keys())
        daysOrder.sort(reverse = True)
        daysOrder = daysOrder[0 : self.colsNum]
        for i, d in enumerate(daysOrder):
            cday = f'{d :d}'
            datas = rs[d]
            mark_utils.mergeMarks(datas, MARK_KIND, True)
            self.listWins[i].setData(datas)
            self.listWins[i].invalidWindow()
            sday = cday[0 : 4] + '-' + cday[4 : 6] + '-' + cday[6 : ]
            self.daysLabels[i].setText(sday)

    def updateDay(self, day):
        if type(day) == str:
            day = int(day.replace('-', ''))
        for i in range(self.colsNum):
            self.listWins[i].setData(None)
            self.listWins[i].invalidWindow()
            self.daysLabels[i].setText(None)

        base_win.ThreadPool.instance().start()
        base_win.ThreadPool.instance().addTask('TOP_VOL_LB', self.loadAll, day)

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    tab = VolLBWindow()
    tab.createWindow(None, (0, 0, 1500, 700), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(tab.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()