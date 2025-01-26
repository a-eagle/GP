import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from orm import tck_orm, tck_orm
from Download import ths_iwencai
from Tck import kline_utils, conf, mark_utils, utils, cache, ext_table

class ZT_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('1fr', ), (5, 10))
        self.tableWin = ext_table.TimelineTableWindow() #ext_win.EditTableWindow()
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.datePicker = None
        self.tckData = None
        self.tckSearchData = None
        self.searchText = ''
        
        self.inputTips = []
        base_win.ThreadPool.instance().start()

    def runTask(self):
        base_win.ThreadPool.instance().addTask('ZT_NET', self._runTask)

    def _runTask(self):
        sday = self.datePicker.getSelDay()
        if not sday:
            return
        self.loadAllData(sday)
        if not self.tableWin.hwnd:
            return
        self.onQuery(self.editorWin.text)

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        def formateMoney(colName, val, rowData):
            if not val:
                return ''
            if type(val) == int:
                return f'{val} 亿'
            elif type(val) == float:
                return f'{val :.1f} 亿'
            return val
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
                   #{'title': '日期', 'width': 80, 'name': 'day', 'sortable':True , 'fontSize' : 14},
                   {'title': '代码', 'width': 70, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True , 'fontSize' : 14, 'render_': render, 'default': ''},
                   {'title': '类别', 'width': 60, 'name': 'tag', 'sortable':True , 'fontSize' : 14, 'default': ''},
                   {'title': '几天几板', 'width': 100, 'name': 'lbs', 'sortable':True , 'fontSize' : 14, 'default': ''},
                   {'title': '热度', 'width': 60, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   {'title': '成交额', 'width': 100, 'name': 'amount', 'sortable':True , 'fontSize' : 14, 'formater': formateMoney, 'default': 0},
                   {'title': '流通市值', 'width': 100, 'name': 'ltsz', 'sortable':True , 'fontSize' : 14, 'formater': formateMoney, 'default': 0},
                   #{'title': '开盘啦', 'width': 100, 'name': 'kpl_ztReason', 'sortable':True , 'fontSize' : 12},
                   {'title': '同花顺', 'width': 160, 'name': 'ths_ztReason', 'fontSize' : 12, 'default': '', 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   {'title': '', 'width': 10, 'name': 'sp'},
                   #{'title': '同花顺备注', 'width': 120, 'name': 'ths_mark_1', 'fontSize' : 12 , 'editable':True, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '财联社', 'width': 150, 'name': 'cls_ztReason', 'fontSize' : 12 , 'default': '','textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '板块', 'width': 220, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '分时图', 'width': 350, 'name': 'FS', 'render': cache.renderTimeline, 'LOCAL-FS-DAY': None},
                   {'title': '首封时', 'width': 100, 'name': 'firstZtTime', 'sortable':True , 'fontSize' : 14, 'default': ''},
                   {'title': '未封时', 'width': 100, 'name': 'lastZtTime', 'sortable':True , 'fontSize' : 14, 'default': ''},
                   {'title': '封单额', 'width': 100, 'name': 'ztMoney', 'sortable':True , 'fontSize' : 14, 'formater': formateMoney, 'default': 0},
                   #{'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        flowLayout = base_win.FlowLayout(20)
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 30))
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 60, 30))
        btn.addListener(self.onRefresh)
        self.datePicker = dp = base_win.DatePicker()
        dp.createWindow(self.hwnd, (0, 0, 120, 30))
        def onPickDate(evt, args):
            #self.editorWin.setText(evt.sday)
            self._runTask()
        dp.addNamedListener('Select', onPickDate)

        fs = {'margins': (0, 3, 0, 0)}
        flowLayout.addContent(dp)
        flowLayout.addContent(self.editorWin)
        flowLayout.addContent(btn)
        flowLayout.addContent(self.checkBox)
        self.layout.setContent(0, 0, flowLayout, {'horExpand': -1})
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
        
        #self.tableWin.addNamedListener('ContextMenu', self.onContextMenu)
        #sm = base_win.ThsShareMemory.instance()
        #sm.open()
        #sm.addListener('ListenSync_TCK', self.onAutoSync)

    def onContextMenu(self, evt, args):
        row = self.tableWin.selRow
        rowData = self.tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            #mark_utils.saveOneMarkColor({'kind': 'zt', 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
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

    def onRefresh(self, evt, args):
        if evt.name == 'Click':
            self.tckData = None
            self.runTask()
            #self.onQuery(self.editorWin.text)

    def onQuery(self, queryText):
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        self.doSearch(queryText)
        self.tableWin.setData(self.tckSearchData)
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
        
    def loadAllData(self, day):
        self.tckData = None
        self.tableWin.setData(None)
        self.tableWin.invalidWindow()
        thsQr = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day == day).dicts()
        clsQr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day == day).dicts()
        hotZH = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == int(day.replace('-', ''))).dicts()

        rs = ths_iwencai.download_zt_zb(day)
        allDicts = {}
        for d in rs:
            allDicts[d['code']] = d
        for d in hotZH:
            it = allDicts.get(f"{d['code'] :06d}", None)
            if it: it['zhHotOrder'] = d['zhHotOrder']

        htsNewest = hot_utils.DynamicHotZH.instance().getNewestHotZH()
        for d in htsNewest:
            item = htsNewest[d]
            cday = item['day']
            cday = f"{cday // 10000}-{cday // 100 % 100 :02d}-{cday % 100 :02d}"
            if cday != day:
                break
            it = allDicts.get(f"{item['code'] :06d}", None)
            if it:
                it['zhHotOrder'] = item['zhHotOrder']

        for d in thsQr:
            k = d['code']
            it = allDicts.get(k, None)
            if it:
                it['ths_ztReason'] = d['ztReason'].upper()

        for d in clsQr:
            k = d['code']
            obj = allDicts.get(k, None)
            if not obj:
                continue
            detail = d['detail'].upper()
            detail = detail.replace('\r\n', ' | ')
            detail = detail.replace('\n', ' | ')
            if obj:
                #obj['cls_detail'] = detail
                obj['cls_ztReason'] = d['ztReason'].upper()
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
        for d in self.tckData:
            if match(d, qrs, cond):
                rs.append(d)
        self.tckSearchData = rs

if __name__ == '__main__':
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    base_win.ThreadPool.instance().start()
    fp = ZT_Window()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    fp.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()