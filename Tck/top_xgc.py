import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, tck_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from Tck import kline_utils, cache, mark_utils, utils

#选股池
class XGC_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (60, 120, 400, 120, 60, 60, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = ext_win.EditTableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        self.editorWin = base_win.ComboBox()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.editorWin.editable = True
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.datePicker = base_win.DatePicker()
        self.qcCheckBox = base_win.CheckBox({'title': '去重'})

        self.ztListData = None
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
        def getLocalFsDay(rowData):
            return rowData['day']
        headers = [ {'title': '', 'width': 40, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   #{'title': '日期', 'width': 100, 'name': 'day', 'sortable':False , 'fontSize' : 14},
                   {'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '日期', 'width': 90, 'name': 'day', 'sortable':True , 'fontSize' : 14},
                   {'title': '代码', 'width': 70, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 90, 'name': 'name', 'sortable':False , 'fontSize' : 14, 'render': mark_utils.markColorTextRender},
                   {'title': '流通盘', 'width': 80, 'name': 'ltsz', 'sortable':True , 'fontSize' : 14, 'formater': formateLtsz},
                   {'title': '热度', 'width': 80, 'name': 'hots', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   {'title': '板块', 'width': 200, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '同花顺', 'width': 200, 'name': 'ths_ztReason', 'sortable':True , 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '财联社', 'width': 200, 'name': 'cls_ztReason', 'sortable':True , 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '', 'width': 15, 'name':'xx-no-1'},
                   {'title': '分时图', 'width': 250, 'name': 'FS', 'render': cache.renderTimeline, 'LOCAL-FS-DAY': getLocalFsDay},
                   #{'title': '详情', 'width': 0, 'name': '_detail_', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers
        self.datePicker.createWindow(self.hwnd, (0, 0, 1, 1))
        def onPickDay(evt, args):
            self.loadAllData()
            self.onQuery()
        self.datePicker.addNamedListener('Select', onPickDay)
        lb = base_win.Label('开始日期')
        lb.createWindow(self.hwnd, (0, 0, 1, 1))
        self.layout.setContent(0, 0, lb)
        self.layout.setContent(0, 1, self.datePicker)
        self.layout.setContent(0, 2, self.editorWin)
        self.layout.setContent(0, 3, self.checkBox)
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 1, 1))
        btn.addNamedListener('Click', self.onRefresh)
        self.qcCheckBox.createWindow(self.hwnd, (0, 0, 1, 1))
        def onCheck(evt, args):
            self.onQuery()
        self.qcCheckBox.addNamedListener('Checked', onCheck)
        self.layout.setContent(0, 4, self.qcCheckBox)
        self.layout.setContent(0, 5, btn)

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
        from Tck import conf
        model = conf.top_hot_tips
        for q in self.inputTips:
            finded = False
            for m in model:
                if q.strip() == m['title']:
                    finded = True
                    break
            if not finded:
                model.append({'title': q})
        self.editorWin.setPopupTip(model)

    def onRefresh(self, evt, args):
        self.loadAllData()
        self.onQuery()

    def onQuery(self):
        queryText = self.editorWin.text
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.doSearch(queryText)
        self.tableWin.setData(self.searchData)
        if self.searchData:
            mark_utils.mergeMarks(self.searchData, 'xgc', False)
        self.tableWin.invalidWindow()

    def onContextMenu(self, evt, args):
        row = self.tableWin.selRow
        rowData = self.tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            mark_utils.saveOneMarkColor({'kind': 'xgc', 'code': rowData['code']}, evt.item['markColor']) # , endDay = rowData['day']
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
        
    def loadAllData(self):
        self.ztListData = None
        selDay = self.datePicker.getSelDayInt()
        if not selDay:
            return
        selDayStr = f'{selDay // 10000}-{selDay // 100 % 100 :02d}-{selDay % 100 :02d}'
        qr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day >= selDayStr).dicts()
        qr2 = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day >= selDayStr).dicts()
        ztList, ztMap = [], {}
        for q in qr:
            q['cls_ztReason'] = q['ztReason']
            del q['ztReason']
            ztList.append(q)
            ztMap[q['day'] + ':' + q['code']] = q
        for q in qr2:
            key = q['day'] + ':' + q['code']
            if key in ztMap:
                ztMap[key]['ths_ztReason'] = q['ztReason']
            else:
                q['ths_ztReason'] = q['ztReason']
                del q['ztReason']
                ztList.append(q)
                ztMap[key] = q

        qr = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day >= selDay).dicts()
        lastHotsDay = None
        for d in qr:
            day = d['day']
            sday = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
            code = f"{d['code'] :06d}"
            key = f'{sday}:{code}'
            item = ztMap.get(key, None)
            if item: item['hots'] = d['zhHotOrder']
            lastHotsDay = day
        if lastHotsDay != hot_utils.getLastTradeDay():
            hotZH = hot_utils.calcHotZHOnLastDay()
            for d in hotZH:
                day = d['day']
                sday = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
                code = f"{d['code'] :06d}"
                key = f'{sday}:{code}'
                item = ztMap.get(key, None)
                if item: item['hots'] = d['zhHotOrder']

        for item in ztList:
            obj = utils.get_THS_GNTC(item['code'])
            if obj:
                item.update(obj)
        self.ztListData = ztList

    def doSearch(self, search : str):
        self.searchText = search
        if not self.ztListData:
            self.searchData = None
            return
        qc = self.qcCheckBox.isChecked()
        orgDatas = self.ztListData
        if qc:
            orgDatas = []
            ex = {}
            for it in self.ztListData:
                if it['code'] not in ex:
                    ex[it['code']] = it
                    orgDatas.append(it)
        if not search or not search.strip():
            self.searchData = orgDatas
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
                    if ('_id' in k or k == '_detail_'):
                        continue
                    if isinstance(data[k], str) and (q in data[k].upper()):
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
        for d in orgDatas:
            if match(d, qrs, cond):
                rs.append(d)
        self.searchData = rs

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    win = XGC_Window()
    win.createWindow(None, (0, 100, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win.layout.resize(0, 0, *win.getClientSize())
    win32gui.PumpMessages()