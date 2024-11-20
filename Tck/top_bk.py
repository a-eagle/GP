import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, tck_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from Tck import kline_utils, cache, mark_utils, utils, ext_table

class Bk_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.layout = base_win.GridLayout(rows, ('1fr', ), (5, 10))
        self.tableWin = ext_table.TimelineTableWindow() #ext_win.EditTableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.fsBtn = base_win.Button({'title': '最新分时'})
        self.fsDatePicker = base_win.DatePicker()

        self.searchData = None
        self.searchText = ''
        self.inputTips = []

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            return f'{int(val)}'
        def sortHot(colName, val, rowData, allDatas, asc):
            if val == None:
                return 1000
            return val
        def render(win, hdc, row, col, colName, value, rowData, rect):
            model = self.tableWin.getData()
            rowData = model[row]
            color = self.tableWin.css['textColor']
            if rowData.get('ths_mark_3', 0) == 1:
                color = 0x0000dd
            self.drawer.drawText(hdc, value, rect, color, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_LEFT)
        
        def formateLtsz(colName, val, rowData):
            if not val:
                return ''
            return f'{val} 亿'
        
        headers = [ {'title': '', 'width': 40, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   #{'title': '日期', 'width': 100, 'name': 'day', 'sortable':False , 'fontSize' : 14},
                   {'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '代码', 'width': 70, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':False , 'fontSize' : 14, 'render': mark_utils.markColorTextRender},
                   {'title': '流通盘', 'width': 70, 'name': 'ltsz', 'sortable':True , 'fontSize' : 14, 'formater': formateLtsz},
                   {'title': '热度', 'width': 60, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   {'title': '板块', 'width': 220, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '同花顺', 'width': 220, 'name': 'ths_ztReason', 'sortable':True , 'formater': self.getZtReason, 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '财联社', 'width': 150, 'name': 'cls_ztReason', 'sortable':True , 'formater': self.getZtReason, 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '分时图', 'width': 350, 'name': 'FS', 'render': cache.renderTimeline, 'LOCAL-FS-DAY': None, 'sortable':True , 'sorter': cache.sorterTimeline},
                   #{'title': '题材概念', 'width': 0, 'name': 'gn', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        headerLayout = base_win.FlowLayout(20)
        self.checkBox.createWindow(self.hwnd, (0, 0, 100, 30))
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers

        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 1, 1))
        btn.addNamedListener('Click', self.onRefresh)
        self.fsBtn.createWindow(self.hwnd, (0, 0, 60, 30))
        self.fsDatePicker.createWindow(self.hwnd, (0, 0, 100, 30))
        self.fsBtn.addNamedListener('Click', self.onFSNewestClick)
        self.fsDatePicker.addNamedListener('Select', self.onFSDateChanged)
        headerLayout.addContent(self.fsBtn)
        headerLayout.addContent(self.fsDatePicker)
        headerLayout.addContent(self.editorWin)
        btn = base_win.Button({'title': '同步'})
        btn.createWindow(self.hwnd, (0, 0, 60, 30))
        btn.addNamedListener('Click', self.onSync)
        headerLayout.addContent(btn)
        headerLayout.addContent(self.checkBox)

        self.layout.setContent(0, 0, headerLayout, {'horExpand': -1})
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = self.editorWin.getText().strip()
            if q and q not in self.inputTips:
                self.inputTips.insert(0, q)
            self.initTips()
            self.onQuery()
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.editorWin.addNamedListener('Select', onPressEnter, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.tableWin.addNamedListener('ContextMenu', self.onContextMenu)
        self.initTips()

    def initTips(self):
        model = []
        for q in self.inputTips:
            finded = False
            for m in model:
                if q.strip() == m['title']:
                    finded = True
                    break
            if not finded:
                model.append({'title': q})
        self.editorWin.setPopupTip(model)

    def onFSNewestClick(self, evt, args):
        self.fsDatePicker.setSelDay(None)
        self.onFSDateChanged(self.Event('Select', self.fsDatePicker, day = None, sday = None), None)

    def onFSDateChanged(self, evt, args):
        curDay = self.fsDatePicker.getSelDayInt()
        for hd in self.tableWin.headers:
            if hd['name'] == 'FS':
                hd['LOCAL-FS-DAY'] = curDay
                break
        self.tableWin.invalidWindow()

    def onRefresh(self, evt, args):
        self.onQuery()

    def onSync(self, evt, args):
        ins = base_win.ThsShareMemory.instance()
        code = ins.readCode()
        if not code:
            return
        obj = ths_orm.THS_ZS.get_or_none(code = code)
        if not obj:
            return
        self.editorWin.setText(obj.name)
        self.editorWin.invalidWindow()
        self.onQuery()

    def onQuery(self):
        queryText = self.editorWin.text
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.doSearch(queryText)
        self.tableWin.setData(self.searchData)
        #if self.searchData:
        #    mark_utils.mergeMarks(self.searchData, 'bk', False)
        self.tableWin.invalidWindow()

    def onContextMenu(self, evt, args):
        row = self.tableWin.selRow
        rowData = self.tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            #mark_utils.saveOneMarkColor({'kind': 'bk', 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
            rd['markColor'] = evt.item['markColor']
            self.tableWin.invalidWindow()
        menu.addNamedListener('Select', onMenuItem, rowData)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def onDbClick(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            win = kline_utils.openInCurWindow(self, data)
            win.setCodeList(self.tableWin.getData())
        
    def loadHotsData(self):
        selDay = self.fsDatePicker.getSelDayInt()
        lastTraday = hot_utils.getLastTradeDay()
        if not selDay:
            selDay = lastTraday
        hotZH = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == selDay).dicts()
        if not hotZH and lastTraday == selDay:
            hotZH = hot_utils.calcHotZHOnLastDay()
        if not hotZH:
            return None, None
        rs = {}
        sday = f"{selDay // 10000}-{selDay // 100 % 100 :02d}-{selDay % 100 :02d}"
        days = {'day': sday, 'iday':selDay}
        for d in hotZH:
            code = f"{d['code'] :06d}"
            mm = {'code': code, 'zhHotOrder': d['zhHotOrder']}
            rs[code] = mm
        return days, rs

    def getZtReason(self, colName, value, rowData):
        if not value:
            code = rowData['code']
            day = rowData['day']
            if 'ths' in colName:
                thsQr = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.code == code, tck_orm.THS_ZT.day <= day).order_by(tck_orm.THS_ZT.day.desc()).limit(1).dicts()
                for t in thsQr:
                    value = rowData['ths_ztReason'] = t.get('ztReason', None)
                    break
            else:
                clsQr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.code == code, tck_orm.CLS_ZT.day <= day).order_by(tck_orm.CLS_ZT.day.desc()).limit(1).dicts()
                for t in clsQr:
                    value = rowData['cls_ztReason'] = t.get('ztReason', None)
                    #rowData['_detail_'] = t.get('detail', None)
                    break
        return value

    def doSearch(self, search : str):
        self.searchData = None
        self.searchText = search
        if not search or not search.strip():
            return
        search = search.strip().upper()
        if '|' in search:
            qs = search.split('|')
            cond = 'OR'
        else:
            qs = search.split(' ')
            cond = 'AND'
        qrs = []
        for q in qs:
            q = q.strip()
            if q and (q not in qrs):
                qrs.append(q)

        def match(data, qrs, cond):
            for q in qrs:
                fd = False
                for k in data:
                    if ('_id' not in k) and isinstance(data[k], str) and (q in data[k].upper()):
                        fd = True
                        break
                if cond == 'AND' and not fd:
                    return False
                if cond == 'OR' and fd:
                    return True
            if cond == 'AND':
                return True
            return False

        #keys = ('day', 'code', 'name', 'kpl_ztReason', 'ths_ztReason', 'cls_ztReason', 'cls_detail')
        rs = []
        days, hots = self.loadHotsData()
        bks = utils.getAllGNTC()
        for code in bks:
            d = bks[code]
            if not match(d, qrs, cond):
                continue
            d = copy.copy(d)
            rs.append(d)
            if code in hots:
                d.update(hots[code])
            d.update(days)
        rs.sort(key = lambda x : x.get('zhHotOrder', 1000))
        self.searchData = rs

if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    win = Bk_Window()
    win.createWindow(None, (0, 100, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win.layout.resize(0, 0, *win.getClientSize())
    win32gui.PumpMessages()