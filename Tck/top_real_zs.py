import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import speed_orm, ths_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from orm import tck_orm
from Tck import kline_utils, conf, mark_utils, utils, cache, ext_table

# 涨速
class ZS_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('1fr', ), (5, 10))
        self.tableWin = ext_table.TimelineTableWindow()
        self.editorWin = base_win.Editor()
        self.datePicker = None
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBoxGn = base_win.CheckBox({'title': '搜索时包括概念'})
        self.searchModeWin = base_win.ComboBox()
        self.dbWin = base_win.ComboBox()
        self.autoCB = base_win.CheckBox({'title': '自动显示分时图'})
        self.tckData = None
        self.lastSearchText = ''
        self.searchIdx = -1
        self.inputTips = []

    def runTask(self):
        base_win.ThreadPool.instance().addTask('ZS-REAL', self._runTask)

    def _runTask(self):
        self.loadAllData()
        if not self.tableWin.hwnd:
            return
        self.doSearch(self.editorWin.text)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateZS(colName, val, rowData):
            return f'{val :.1f}%'
        
        def sortHot(colName, val, rowData, allDatas, asc):
            if val == None:
                return 1000
            return val

        headers = [ {'title': '', 'width': 30, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   {'title': '日期', 'width': 80, 'name': 'day', 'sortable':True , 'fontSize' : 14},
                   {'title': '时间', 'width': 80, 'name': 'minuts', 'sortable':True , 'fontSize' : 14},
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True , 'fontSize' : 14, 'render': mark_utils.markColorTextRender},
                   {'title': '涨速A', 'width': 80, 'name': 'zf', 'sortable':True , 'fontSize' : 14, 'formater': formateZS},
                   {'title': '热度', 'width': 80, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   {'title': '同花顺', 'width': 150, 'name': 'ths_ztReason', 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   {'title': '', 'width': 10, 'name': 'sp'},
                   {'title': '财联社', 'width': 120, 'name': 'cls_ztReason', 'fontSize' : 12 ,'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '板块', 'width': 220, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '分时图', 'width': 350, 'name': 'FS', 'render': self.renderTimeline, 'LOCAL-FS-DAY': self.getCurDayFs},
                   ]
        flowLayout = base_win.FlowLayout(20)
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 30))
        self.checkBoxGn.createWindow(self.hwnd, (0, 0, 150, 30))
        self.searchModeWin.setPopupTip([{'key': 'DingWei', 'title':'定位搜索' }, {'key': 'Filter', 'title':'过滤搜索' }])
        self.searchModeWin.createWindow(self.hwnd, (0, 0, 100, 30))
        self.dbWin.setPopupTip([{'key': 'real', 'title':'实时数据' }, {'key': 'local', 'title':'本地数据' }])
        self.dbWin.createWindow(self.hwnd, (0, 0, 100, 30))
        self.dbWin.setSelectItem(0)
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.css['selBgColor'] = 0xd0d0d0
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 60, 30))
        btn2 = base_win.Button({'title': '同步'})
        btn2.createWindow(self.hwnd, (0, 0, 60, 30))
        self.autoCB.createWindow(self.hwnd, (0, 0, 120, 30))
        btn.addNamedListener('Click', self.onRefresh)
        btn2.addNamedListener('Click', self.onSync)
        self.datePicker = dp = base_win.DatePicker()
        dp.createWindow(self.hwnd, (0, 0, 120, 30))
        def onPickDate(evt, args):
            self.runTask()
        dp.addNamedListener('Select', onPickDate)

        flowLayout.addContent(dp)
        flowLayout.addContent(self.dbWin)
        flowLayout.addContent(self.searchModeWin)
        flowLayout.addContent(self.checkBoxGn, {'margins': (20, 0, 0, 0)})
        flowLayout.addContent(self.editorWin)
        flowLayout.addContent(btn)
        flowLayout.addContent(btn2)
        flowLayout.addContent(self.checkBox)
        flowLayout.addContent(self.autoCB)
        self.layout.setContent(0, 0, flowLayout, {'horExpand': -1})
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.doSearch(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.tableWin.addNamedListener('ContextMenu', self.onContextMenu)
        self.tableWin.addNamedListener('SelectRow', self.onSelectRow)
        self.searchModeWin.setSelectItem(0)
        self.searchModeWin.addNamedListener('Select', self.onChangeSearchMode)
        self.dbWin.addNamedListener('Select', self.onDbChanged)
        sm = base_win.ThsShareMemory.instance()
        sm.open()

    def onDbChanged(self, evt, args):
        self.loadAllData()
        self.doSearch(self.editorWin.text)

    def getCurDayFs(self):
        today = datetime.date.today()
        today = today.strftime('%Y-%m-%d')
        selDay = self.datePicker.getSelDay()
        if today == selDay or not selDay:
            return None
        return selDay

    def onChangeSearchMode(self, evt, args):
        self.searchIdx = -1
        if self.isDingWeiSearch():
            self.tableWin.setData(self.tckData)
            self.tableWin.invalidWindow()
        self.doSearch(self.editorWin.getText())

    def onSelectRow(self, evt, args):
        if evt.data:
            evt.data['show-fs'] = True

    # 分时图
    def renderTimeline(self, win : base_win.TableWindow, hdc, row, col, colName, value, rowData, rect):
        if rowData.get('show-fs', False) or self.autoCB.isChecked():
            rowData['show-fs'] = True
            cache.renderTimeline(win, hdc, row, col, colName, value, rowData, rect)

    def onContextMenu(self, evt, args):
        row = self.tableWin.selRow
        rowData = self.tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            #mark_utils.saveOneMarkColor({'kind': 'real-zs', 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
            rd['markColor'] = evt.item['markColor']
            self.tableWin.invalidWindow()
        menu.addNamedListener('Select', onMenuItem, rowData)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def onSync(self, evt, args):
        sm = base_win.ThsShareMemory.instance()
        code = sm.readCode()
        if not code:
            return
        code = f'{code :06d}'
        name = ''
        if code[0 : 2] == '88':
            obj = ths_orm.THS_ZS.get_or_none(code == code)
            if obj: name = obj.name
        else:
            obj = utils.get_THS_GNTC(code)
            if obj: name = obj['name']
        txt = code + ('' if not name else ' | ' + name)
        self.editorWin.setText(txt)
        self.editorWin.invalidWindow()
        self.doSearch(txt)

    def onRefresh(self, evt, args):
        self.runTask()

    def onDbClick(self, evt, args):
        if evt.name != 'RowEnter' and evt.name != 'DbClick':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            win = kline_utils.openInCurWindow_Code(self, data)
            win.setCodeList(self.tableWin.getData(), self.tableWin.selRow)
        
    def loadAllData(self):
        self.tckData = None
        self.tableWin.setData(None)
        self.searchIdx = -1
        self.tableWin.invalidWindow()
        day = self.datePicker.getSelDay2()
        if not day:
            return
        iday = self.datePicker.getSelDayInt()
        endDay = self.datePicker.getSelDay()
        fd = day - datetime.timedelta(days = 45)
        fromDay = f"{fd.year}-{fd.month :02d}-{fd.day :02d}"
        thsRs = {}
        clsRs = {}
        thsQr = tck_orm.THS_ZT.select(tck_orm.THS_ZT.code, tck_orm.THS_ZT.ztReason).where(tck_orm.THS_ZT.day >= fromDay, tck_orm.THS_ZT.day <= endDay).tuples()
        clsQr = tck_orm.CLS_ZT.select(tck_orm.CLS_ZT.code, tck_orm.CLS_ZT.ztReason).where(tck_orm.CLS_ZT.day >= fromDay, tck_orm.CLS_ZT.day <= endDay).tuples()
        dbWhere = self.dbWin.getSelectItem()
        if dbWhere['key'] == 'real':
            qr = speed_orm.RealSpeedModel.select().where(speed_orm.RealSpeedModel.day == iday).dicts()
        else:
            qr = speed_orm.LocalSpeedModel.select().where(speed_orm.LocalSpeedModel.day == iday).order_by(speed_orm.LocalSpeedModel.fromMinute.asc()).dicts()
        hots = hot_utils.DynamicHotZH.instance().getHotsZH(iday)
        for q in thsQr:
            thsRs[q[0]] = q[1]
        for q in clsQr:
            clsRs[q[0]] = q[1]
        datas = []
        for d in qr:
            d['day'] = utils.formatDate(d['day'])
            if 'fromMinute' in d:
                m = d['fromMinute'] * 100
            else:
                m = d['minuts']
            d['minuts'] = f'{m // 10000 :02d}:{m // 100 % 100 :02d}:{m % 100 :02d}'
            code = d['code']
            d['ths_ztReason'] = thsRs.get(code, '')
            d['cls_ztReason'] = clsRs.get(code, '')
            nn = utils.get_THS_GNTC(code)
            if nn:
                d['name'] = nn['name']
                d['gn'] = nn['gn']
                d['hy'] = nn['hy']
            if hots and int(code) in hots:
                d['zhHotOrder'] = hots[int(code)]['zhHotOrder']
            datas.append(d)
        self.tckData = datas
        self.tableWin.setData(datas)
        self.tableWin.invalidWindow()

    def getSearchCond(self, search):
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
        return qrs, cond

    def isDingWeiSearch(self):
        item = self.searchModeWin.getSelectItem()
        return item['key'] == 'DingWei'

    def doSearch(self, search : str):
        if search is None: search = ''
        search = search.strip().upper()
        if self.isDingWeiSearch():
            if search != self.lastSearchText or not search:
                self.searchIdx = -1
            self.lastSearchText = search
            if not search:
                return
            qrs, cond = self.getSearchCond(search)
            self.doSearchDW(qrs, cond)
        else:
            #if self.lastSearchText == search:
            #    return
            self.lastSearchText = search
            if not search:
                self.tableWin.setData(self.tckData)
                self.tableWin.invalidWindow()
                return
            qrs, cond = self.getSearchCond(search)
            self.doSearchFilter(qrs, cond)

    def doSearchFilter(self, qrs, cond):
        rs = []
        for d in self.tckData:
            if self.match(d, qrs, cond):
                rs.append(d)
        self.tableWin.setData(rs)
        self.tableWin.invalidWindow()

    def doSearchDW(self, qrs, cond):
        for i in range(self.searchIdx + 1, len(self.tckData)):
            d = self.tckData[i]
            if self.match(d, qrs, cond):
                self.searchIdx = i
                break
        if self.searchIdx >= 0:
            self.tableWin.setSelRow(self.searchIdx)
            self.tableWin.showRow(self.searchIdx)

    def match(self, data, qrs, cond):
        if not qrs:
            return True
        hasGn = self.checkBoxGn.isChecked()
        for q in qrs:
            fd = False
            for k in data:
                if not hasGn and k == 'gn':
                    continue
                if ('_id' not in k) and isinstance(data[k], str) and (q in data[k]):
                    fd = True
                    break
            if cond == 'AND' and not fd:
                return False
            if cond == 'OR' and fd:
                return True
        if cond == 'AND':
            return True
        return False

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    base_win.ThreadPool.instance().start()
    win = ZS_Window()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    win.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = win.getClientSize()
    win.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()