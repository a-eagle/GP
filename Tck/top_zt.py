import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from orm import tck_orm, tck_orm
from Tck import kline_utils, conf, mark_utils, utils


class ZT_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        rows = (30, '1fr')
        self.cols = (60, 300, 120, 40, 150, 120, '1fr')
        self.layout = base_win.GridLayout(rows, self.cols, (5, 10))
        self.tableWin = ext_win.EditTableWindow()
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.autoSyncCheckBox = base_win.CheckBox({'title': '自动同步显示'})
        self.tckData = None
        self.tckSearchData = None
        self.searchText = ''
        
        self.inputTips = []
        
        base_win.ThreadPool.instance().addTask('TCK', self.runTask)

    def runTask(self):
        self.loadAllData()
        if not self.tableWin.hwnd:
            return
        self.onQuery(self.editorWin.text)

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
        headers = [ {'title': '', 'width': 30, 'name': '#idx','textAlign': win32con.DT_SINGLELINE | win32con.DT_CENTER | win32con.DT_VCENTER },
                   {'title': '日期', 'width': 80, 'name': 'day', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True , 'fontSize' : 14, 'render': render},
                   #{'title': '代码', 'width': 50, 'name': 'code', 'sortable':True , 'fontSize' : 12},
                   {'title': '热度', 'width': 60, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   #{'title': '开盘啦', 'width': 100, 'name': 'kpl_ztReason', 'sortable':True , 'fontSize' : 12},
                   {'title': '连板', 'width': 60, 'name': 'ths_status', 'sortable':True , 'fontSize' : 12},
                   {'title': '同花顺', 'width': 150, 'name': 'ths_ztReason', 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   {'title': '', 'width': 10, 'name': 'sp'},
                   #{'title': '同花顺备注', 'width': 120, 'name': 'ths_mark_1', 'fontSize' : 12 , 'editable':True, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '财联社', 'width': 120, 'name': 'cls_ztReason', 'fontSize' : 12 ,'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '板块', 'width': 150, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        self.checkBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.autoSyncCheckBox.createWindow(self.hwnd, (0, 0, 1, 1))
        self.editorWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 40
        self.tableWin.headers = headers
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 1, 1))
        btn.addListener(self.onRefresh)
        self.layout.setContent(0, 0, btn)
        self.layout.setContent(0, 1, self.editorWin)
        dp = base_win.DatePicker()
        dp.createWindow(self.hwnd, (0, 0, 1, 1))
        def onPickDate(evt, args):
            self.editorWin.setText(evt.sday)
            self.onQuery(evt.sday)
        dp.addNamedListener('Select', onPickDate)
        self.layout.setContent(0, 2, dp)
        self.layout.setContent(0, 4, self.checkBox)
        self.layout.setContent(0, 5, self.autoSyncCheckBox)
        self.layout.setContent(1, 0, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.editorWin.addNamedListener('DbClick', self.onDbClickEditor, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.tableWin.addListener(self.onEditCell, None)
        
        self.tableWin.addNamedListener('ContextMenu', self.onContextMenu)
        sm = base_win.ThsShareMemory.instance()
        sm.open()
        sm.addListener('ListenSync_TCK', self.onAutoSync)

    def onContextMenu(self, evt, args):
        row = self.tableWin.selRow
        rowData = self.tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            mark_utils.saveOneMarkColor({'kind': 'zt', 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
            rd['markColor'] = evt.item['markColor']
            self.tableWin.invalidWindow()
        menu.addNamedListener('Select', onMenuItem, rowData)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)

    def onAddCiTiao(self, evt, args):
        txt =  self.editorWin.getText().strip()
        #if not txt:
        #    return
        #obj = tck_def_orm.TCK_CiTiao.get_or_none(name = txt)
        #if not obj:
        #    tck_def_orm.TCK_CiTiao.create(name = txt)

    def onDbClickEditor(self, evt, args):
        model = []
        for s in self.inputTips:
            model.append({'title': s})
        model.append({'title': 'LINE'})
        model.extend(conf.top_zt_tips)
        #for s in tck_def_orm.TCK_CiTiao.select():
        #    model.append({'title': s.name})
        #if len(model) == 1:
        #    return

        def onSelMenu(evt, args):
            self.editorWin.setText(evt.item['title'])
            self.editorWin.invalidWindow()
            self.onQuery(self.editorWin.getText())
        menu = base_win.PopupMenu.create(self.editorWin.hwnd, model)
        menu.addNamedListener('Select', onSelMenu)
        menu.minItemWidth = self.editorWin.getClientSize()[0]
        menu.show()

    def onEditCell(self, evt, args):
        if evt.name != 'CellChanged':
            return
        colName = evt.header['name']
        if colName != 'ths_mark_1':
            return
        val = evt.data.get(colName, '')
        _id = evt.data['ths_id']
        qr = tck_orm.THS_ZT.update({tck_orm.THS_ZT.mark_1 : val}).where(tck_orm.THS_ZT.id == _id)
        qr.execute()

    def onAutoSync(self, code, day):
        checked = self.autoSyncCheckBox.isChecked()
        if not checked:
            return
        code = f'{code :06d}'
        txt = self.editorWin.text
        if txt == code:
            return
        self.editorWin.setText(code)
        self.editorWin.invalidWindow()
        self.onQuery(self.editorWin.text)

    def onRefresh(self, evt, args):
        if evt.name == 'Click':
            self.tckData = None
            base_win.ThreadPool.instance().addTask('TCK', self.runTask)
            #self.onQuery(self.editorWin.text)

    def onQuery(self, queryText):
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.loadAllData()
        self.doSearch(queryText)
        self.tableWin.setData(self.tckSearchData)
        if self.tckSearchData:
            mark_utils.mergeMarks(self.tckSearchData, 'zt', False)
        self.tableWin.invalidWindow()
    
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
        if self.tckData != None:
            return
        today = datetime.date.today()
        fd = today - datetime.timedelta(days = 60)
        fromDay = f"{fd.year}-{fd.month :02d}-{fd.day :02d}"
        #kplQr = tck_orm.KPL_ZT.select().where(tck_orm.KPL_ZT.day >= fromDay).order_by(tck_orm.KPL_ZT.day.desc(), tck_orm.KPL_ZT.id.asc()).dicts()
        thsQr = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day >= fromDay).dicts()
        clsQr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day >= fromDay).dicts()
        hotZH = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day >= int(fromDay.replace('-', ''))).dicts()
        
        allDicts = {}
        cls = []
        hots = {}
        rs = []
        for d in hotZH:
            day = d['day']
            day = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
            k = f"{day}:{d['code'] :06d}"
            hots[k] = d['zhHotOrder']

        htsNewest = hot_utils.DynamicHotZH.instance().getNewestHotZH()
        for d in htsNewest:
            item = htsNewest[d]
            day = item['day']
            day = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
            k = f"{day}:{item['code'] :06d}"
            hots[k] = item['zhHotOrder']

        for d in thsQr:
            k = d['day'] + ':' + d['code']
            allDicts[k] = obj = {'code': d['code'], 'name': d['name'], 'day': d['day'], 'kpl_id': d['id']}
            obj['ths_status'] = d['status']
            obj['ths_ztReason'] = d['ztReason'].upper()
            obj['ths_mark_1'] = d['mark_1']
            obj['ths_mark_2'] = d['mark_2']
            obj['ths_mark_3'] = d['mark_3']
            obj['ths_id'] = d['id']
            obj['zhHotOrder'] = hots.get(k, None)
            obj['day'] = d['day']
            obj['code'] = d['code']
            obj['name'] = d['name']
            rs.append(obj)

        for d in clsQr:
            k = d['day'] + ':' + d['code']
            obj = allDicts.get(k, None)
            detail = d['detail'].upper()
            detail = detail.replace('\r\n', ' | ')
            detail = detail.replace('\n', ' | ')
            if obj:
                obj['cls_detail'] = detail
                obj['cls_ztReason'] = d['ztReason'].upper()
            else:
                d['cls_detail'] = detail
                d['cls_ztReason'] = d['ztReason'].upper()
                d['zhHotOrder'] = hots.get(k, None)
                rs.append(d)
        rs.sort(key = lambda d : d['day'], reverse = True)
        for item in rs:
            obj = utils.get_THS_GNTC(item['code'])
            if obj: item.update(obj)
        self.tckData = rs

    def doSearch(self, search : str):
        self.searchText = search
        if not self.tckData:
            self.tckSearchData = None
            return
        if not search or not search.strip():
            self.tckSearchData = self.tckData
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

        #keys = ('day', 'code', 'name', 'kpl_ztReason', 'ths_ztReason', 'cls_ztReason', 'cls_detail')
        rs = []
        for d in self.tckData:
            if match(d, qrs, cond):
                rs.append(d)
        self.tckSearchData = rs

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE:
            size = self.getClientSize()
            self.layout.resize(0, 0, size[0], size[1])
            self.invalidWindow()
            return True
        return super().winProc(hwnd, msg, wParam, lParam)
    
if __name__ == '__main__':
    pass