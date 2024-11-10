import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import tck_def_orm, ths_orm
from Common import base_win, sheet
from Tck import kline_utils

class DailyWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.css['paddings'] = (0, 0, 0, 0)
        rows = (30, '1fr')
        self.cols = (200, 150, 80, 80, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = base_win.TableWindow()
        self.sheetWin = sheet.SheetWindow()
        self.sheetWin.css['enableVerGridLine'] = False
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        #base_win.ThreadPool.addTask()
        self.curData = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortPM(colName, val, rowData, allDatas, asc):
            return val
        def formater_1(colName, val, rowData):
            return '*' if val == True else ''
        def formater_2(colName, val, rowData):
            day = int(rowData['day'].replace('-', ''))
            day = datetime.date(day // 10000, day // 100 % 100, day % 100)
            w = day.weekday()
            return '一二三四五六日'[w]

        headers = [ {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': '日期', 'width': 0, 'stretch': 1, 'name': 'day', 'sortable':True },
                   {'title': '', 'width': 40, 'name': '_week', 'formater' : formater_2},
                   {'title': '', 'width': 20, 'name': '_updated', 'formater' : formater_1}
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.sheetWin.createWindow(self.hwnd, (0, 0, 1, 1))
        addBtn = base_win.Button({'title': 'Add', 'name': 'Add'})
        addBtn.createWindow(self.hwnd, (0, 0, 50, 25))
        addBtn.addNamedListener('Click', self.onInsertDay)
        delBtn = base_win.Button({'title': 'Delete', 'name': 'Delete'})
        delBtn.createWindow(self.hwnd, (0, 0, 50, 25))
        delBtn.addNamedListener('Click', self.onDeleteDay)
        fl = base_win.FlowLayout()
        fl.lineHeight = 30
        fl.addContent(addBtn, {'margins': (10, 0, 0, 0)})
        fl.addContent(delBtn)
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        openBtn = base_win.Button({'title': '打开'})
        openBtn.createWindow(self.hwnd, (0, 0, 1, 1))

        self.layout.setContent(0, 0, fl)
        self.layout.setContent(0, 1, self.checkBox)
        self.layout.setContent(0, 2, openBtn)

        self.layout.setContent(1, 0, self.tableWin)
        self.layout.setContent(1, 1, self.sheetWin, {'horExpand': -1})
        self.tableWin.addNamedListener('SelectRow', self.onSelDay, None)
        self.sheetWin.addNamedListener('Save', self.onSheetSave, None)
        self.sheetWin.addNamedListener('model.updated', self.onModelUpdated)
        openBtn.addNamedListener('Click', self.onOpen)
        self.loadDays()
        W, H = self.getClientSize()
        pd = self.css['paddings']
        self.layout.resize(pd[0], pd[1], W - pd[0] - pd[2], H - pd[1] - pd[3])

    def getRefDay(self, row, col):
        if col <= 0 or row <= 0:
            return None
        p1 = re.compile(r'\d{1,2}[.-/]\d{1,2}')
        # 仅查找A列
        day = None
        while row >= 0:
            cell = self.sheetWin.model.getCell(row, 0)
            if not cell:
                row -= 1
                continue
            txt = cell.getText() or ''
            txt = txt.strip()
            lv = p1.search(txt)
            if lv:
                day = lv.group(0)
                break
            row -= 1
        if not day:
            return None
        year = self.curData['day'][0 : 4]
        days = re.split('[.-/]', day)
        day = f'{year}-{int(days[0]) :02d}-{int(days[1]) :02d}'
        return day

    def onOpen(self, evt, args):
        selRange = self.sheetWin.selRange
        if not selRange or selRange[0] < -1 or selRange[1] < -1:
            return
        sr, sc, er, ec = self.sheetWin.formatRange(selRange)
        cell = self.sheetWin.model.getCell(sr, sc)
        if not cell or not cell.getText():
            return
        txt = cell.getText()
        rx = re.compile('\d{6}')
        codes = rx.findall(txt)
        if not codes:
            return
        day = self.getRefDay(sr, sc)
        if len(codes) == 1:
            self.openOneCode(codes[0], day)
            return
        model = []
        cinfos = {}
        qr = ths_orm.THS_GNTC.select().where(ths_orm.THS_GNTC.code.in_(codes)).dicts()
        for d in qr:
            cinfos[d['code']] = d['name']
        qr = ths_orm.THS_ZS_ZD.select(ths_orm.THS_ZS_ZD.code, ths_orm.THS_ZS_ZD.name).distinct().where(ths_orm.THS_ZS_ZD.code.in_(codes)).dicts()
        for d in qr:
            cinfos[d['code']] = d['name']
        for code in codes:
            name = cinfos.get(code, '')
            model.append({'name': name, 'code': code, 'title': f'{name} ({code})', 'day': day})
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, args):
            item = evt.item
            self.openOneCode(item['code'], item['day'])
        menu.addNamedListener('Select', onMenuItem)
        pos = win32gui.GetCursorPos()
        menu.show(*pos)
        
    def openOneCode(self, code, day):
        inThs = self.checkBox.isChecked()
        data = {'code': code, 'day': day}
        if inThs:
            kline_utils.openInThsWindow(data)
        else:
            kline_utils.openInCurWindow(self, data)

    def onModelUpdated(self, evt, args):
        if not self.curData:
            return
        self.curData['_updated'] = evt.updated
        self.tableWin.invalidWindow()

    def loadDays(self):
        qr = tck_def_orm.DailyFuPan.select().order_by(tck_def_orm.DailyFuPan.day.desc()).dicts()
        datas = []
        for d in qr:
            d['_updated'] = False
            d['_model'] = None
            datas.append(d)
        self.tableWin.setData(datas)

    def onInsertDay(self, evt, args):
        def onPeekDay(evt, args):
            obj = tck_def_orm.DailyFuPan.get_or_none(day = evt.sday)
            if obj: return # exists
            tck_def_orm.DailyFuPan.create(day = evt.sday)
            self.loadDays()
            for i, d in enumerate(self.tableWin.getData()):
                if d['day'] == evt.sday:
                    self.tableWin.setSelRow(i)
                    self.tableWin.invalidWindow()
        pp = base_win.DatePopupWindow()
        pp.addNamedListener('Select', onPeekDay)
        pp.createWindow(evt.src.hwnd)
        rc = win32gui.GetWindowRect(evt.src.hwnd)
        pp.show(rc[0], rc[3])

    def onDeleteDay(self, evt, args):
        selRow = self.tableWin.selRow
        datas = self.tableWin.getData()
        if selRow < 0 or not datas or selRow >= len(datas):
            return
        tck_def_orm.DailyFuPan.delete_by_id(datas[selRow]['id'])
        datas.pop(selRow)
        if selRow > 0:
            selRow -= 1
        if selRow >= len(datas):
            selRow = -1
        self.tableWin.setSelRow(selRow)
        self.tableWin.invalidWindow()

    def onSheetSave(self, evt, args):
        model : sheet.SheetModel = evt.model
        info = model.serialize()
        if not self.curData:
            return
        model.setUpdated(False)
        self.curData['info'] = info
        qr = tck_def_orm.DailyFuPan.update({'info': info}).where(tck_def_orm.DailyFuPan.id == self.curData['id'])
        qr.execute()
        self.tableWin.invalidWindow()
    
    def openInThsWindow(self, data):
        pass
        
    def onSelDay(self, evt, args):
        data = evt.data
        self.curData = data
        if not data:
            self.sheetWin.setModel(sheet.SheetModel())
            self.sheetWin.invalidWindow()
            return
        if not data['_model']:
            data['_model'] = sheet.SheetModel.unserialize(data['info'])
        self.sheetWin.setModel(data['_model'])
        self.sheetWin.invalidWindow()

    def winProc(self, hwnd, msg, wParam, lParam):
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    win = DailyWindow()
    win.createWindow(None, (0, 0, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
    win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()