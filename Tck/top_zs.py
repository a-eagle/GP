import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from Common import base_win
from Tck import kline_utils, mark_utils 

MIN_MONEY = 0

class ZSWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, 20, '1fr')
        cw = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        n = 4 if cw > 1600 else 3
        self.cols = ('1fr', ) * n
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.listWins = []
        self.daysLabels =[]
        self.checkBox_THS = None
        self.checkBox_Only = None
        self.datePicker = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.datePicker = base_win.DatePicker()
        self.datePicker.createWindow(self.hwnd, (10, 10, 150, 30))
        self.checkBox_THS = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox_THS.createWindow(self.hwnd, (0, 0, 150, 30))
        self.checkBox_Only = base_win.CheckBox({'title': '仅显示标记指数'})
        self.checkBox_Only.createWindow(self.hwnd, (0, 0, 150, 30))
        absLayout = base_win.AbsLayout()
        absLayout.setContent(0, 0, self.datePicker)
        absLayout.setContent(230, 0, self.checkBox_THS)
        absLayout.setContent(400, 0, self.checkBox_Only)
        self.layout.setContent(0, 0, absLayout)

        def formateRate(colName, val, rowData):
            return f'{val :.02f}%'
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            if val > 0:
                return val
            elif val < 0:
                return len(allDatas) + val + 100
            # == 0
            if asc:
                return 10000
            return -10000
        
        headers = [{'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '代码', 'width': 60, 'name': 'code'},
                   {'title': '指数名称', 'width': 0, 'stretch': 1, 'name': 'name', 'sortable':True, 'render': mark_utils.markColorTextRender },
                   {'title': '成交额', 'width': 60, 'name': 'money', 'formater': formateMoney , 'sortable':True },
                   {'title': '涨幅', 'width': 60, 'name': 'zdf', 'formater': formateRate, 'sortable':True },
                   {'title': '一级排名', 'width': 70, 'name': 'zdf_topLevelPM', 'sorter': sortPM, 'sortable':True },
                   {'title': '全市排名', 'width': 70, 'name': 'zdf_PM', 'sorter': sortPM, 'sortable':True }]
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
        self.datePicker.addListener(self.onSelDayChanged, None)
        self.checkBox_Only.addNamedListener('Checked', self.onOnlyChecked)
        # init view
        today = datetime.date.today()
        day = today.strftime('%Y%m%d')
        self.datePicker.setSelDay(day)
        self.updateDay(day)

    def getMarksCode(self):
        qr = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.code).where(ths_orm.THS_ZS_ZD.markColor.is_null(False)).distinct().tuples()
        ex = []
        for d in qr:
            ex.append(d[0])
        return ex

    def onOnlyChecked(self, evt, args):
        day = self.datePicker.getSelDay()
        self.updateDay(day)
        
    def onContextMenu(self, evt, tabIdx):
        if evt.name != 'ContextMenu':
            return
        win : base_win.TableWindow = self.listWins[tabIdx]
        wdata = win.getData()
        rowData = wdata[win.selRow] if win.selRow >= 0 else None
        code = rowData['code'] if rowData else None
        model = [{'title': '关联选中', 'name': 'GL', 'enable': win.selRow >= 0}, 
                 {'title': '标记红色重点', 'name': 'MARK_RED', 'enable': win.selRow >= 0}, 
                 {'title': '标记蓝色观察', 'name': 'MARK_BLUE', 'enable': win.selRow >= 0}, 
                 {'title': '标记绿色负面', 'name': 'MARK_GREEN', 'enable': win.selRow >= 0}, 
                 {'title': 'LINE'},
                 {'title': '取消颜色标记', 'name': 'MARK_CANCEL', 'enable': win.selRow >= 0},
                 {'title': '取消颜色标记[不限日期]', 'name': 'MARK_CANCEL_NOLIMIT', 'enable': win.selRow >= 0}, 
                 {'title': '筛选标记', 'name': 'MARK_FILTER'}]
        menu = base_win.PopupMenu.create(self.hwnd, model)
        menu.addListener(self.onMenuItemSelect, (tabIdx, code, rowData))
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def findIdx(self, win, code):
        datas = win.getData() or []
        for i, d in enumerate(datas):
            if d['code'] == code:
                return i
        return -1
    
    def onMenuItemSelect(self, evt, args):
        if evt.name != 'Select':
            return
        tabIdx, code, rowData = args
        MARKS = ('MARK_RED', 'MARK_BLUE', 'MARK_GREEN')
        if evt.item['name'] == "GL":
            for i, win in enumerate(self.listWins):
                if i == tabIdx:
                    continue
                idx = self.findIdx(win, code)
                win.selRow = idx
                win.showRow(idx)
                win.invalidWindow()
        elif evt.item['name'] in MARKS:
            MARK_VAL = 1 + MARKS.index(evt.item['name'])
            qr = ths_orm.THS_ZS_ZD.update({ths_orm.THS_ZS_ZD.markColor : MARK_VAL}).where(ths_orm.THS_ZS_ZD.id == rowData['id'])
            qr.execute()
            rowData['markColor'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_CANCEL':
            MARK_VAL = None
            qr = ths_orm.THS_ZS_ZD.update({ths_orm.THS_ZS_ZD.markColor : MARK_VAL}).where(ths_orm.THS_ZS_ZD.id == rowData['id'])
            qr.execute()
            rowData['markColor'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_CANCEL_NOLIMIT':
            MARK_VAL = None
            qr = ths_orm.THS_ZS_ZD.update({ths_orm.THS_ZS_ZD.markColor : MARK_VAL}).where(ths_orm.THS_ZS_ZD.code == rowData['code'])
            qr.execute()
            rowData['markColor'] = MARK_VAL
            self.listWins[tabIdx].invalidWindow()
        elif evt.item['name'] == 'MARK_FILTER':
            tabWin : base_win.TableWindow = self.listWins[tabIdx]
            day = tabWin._day
            fm = getattr(tabWin, '_filter_mark_', False)
            cnd = (ths_orm.THS_ZS_ZD.day == day) & (ths_orm.THS_ZS_ZD.money >= MIN_MONEY)
            if self.checkBox_Only.isChecked():
                mc = self.getMarksCode()
                cnd = cnd & ths_orm.THS_ZS_ZD.code.in_(mc)
            if not fm:
                cnd = cnd & ths_orm.THS_ZS_ZD.markColor.is_null(False)
                qr = ths_orm.THS_ZS_ZD.select().where(cnd).dicts()
                rs = [d for d in qr]
            else:
                qr = ths_orm.THS_ZS_ZD.select().where(cnd).dicts()
                rs = [d for d in qr]
            setattr(tabWin, '_filter_mark_', not fm)
            tabWin.setData(rs)
            tabWin.invalidWindow()

    def onSelDayChanged(self, evt, args):
        if evt.name != 'Select':
            return
        # TODO: change models
        self.updateDay(evt.day)
    
    def onDbClick(self, evt, idx):
        if evt.name != 'DbClick' and evt.name != 'RowEnter':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox_THS.isChecked():
            self.openInThsWindow(data)
            return
        win = kline_utils.openInCurWindow_ZS(self, data)
        win.setCodeList(evt.src.getData())

    def openInThsWindow(self, data):
        kline_utils.openInThsWindow(data)

    def updateDay(self, day):
        if type(day) == int:
            day = str(day)
        if len(day) == 8:
            day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        
        q = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.day).distinct().where(ths_orm.THS_ZS_ZD.day <= day).order_by(ths_orm.THS_ZS_ZD.day.desc()).limit(len(self.cols)).tuples()
        for i, d in enumerate(q):
            cday = d[0]
            self.updateDay_Table(cday, self.listWins[i])
            self.daysLabels[i].setText(cday)

    def updateDay_Table(self, cday, tableWin):
        cnd = (ths_orm.THS_ZS_ZD.day == cday) & (ths_orm.THS_ZS_ZD.money >= MIN_MONEY)
        if self.checkBox_Only.isChecked():
            mc = self.getMarksCode()
            cnd = cnd & ths_orm.THS_ZS_ZD.code.in_(mc)
        ds = ths_orm.THS_ZS_ZD.select().where(cnd)
        #print(ds)
        datas = [d.__data__ for d in ds]
        tableWin._filter_mark_ = False
        tableWin.setData(datas)
        tableWin._day = cday
        tableWin.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)