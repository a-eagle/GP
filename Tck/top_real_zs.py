import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from db import tck_orm, zs_orm
from Tck import kline_utils, conf, mark_utils, utils

# 涨速
class ZS_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), (200, '1fr', ), (5, 10))
        self.tableWin = ext_win.EditTableWindow()
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.tckData = None
        self.tckSearchData = None
        self.searchText = ''
        self.inputTips = []

    def runTask(self):
        base_win.ThreadPool.instance().addTask('ZS-REAL', self._runTask)

    def _runTask(self):
        self.loadAllData()
        if not self.tableWin.hwnd:
            return
        self.onQuery(self.editorWin.text)

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
                   {'title': '时间', 'width': 80, 'name': 's_minuts', 'sortable':True , 'fontSize' : 14},
                   {'title': '代码', 'width': 50, 'name': 'code', 'sortable':True , 'fontSize' : 14},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True , 'fontSize' : 14},
                   {'title': '涨速', 'width': 60, 'name': 'zf', 'sortable':True , 'fontSize' : 14, 'formater': formateZS},
                   
                   #{'title': '热度', 'width': 60, 'name': 'zhHotOrder', 'sortable':True , 'fontSize' : 14, 'sorter': sortHot},
                   #{'title': '开盘啦', 'width': 100, 'name': 'kpl_ztReason', 'sortable':True , 'fontSize' : 12},
                   #{'title': '连板', 'width': 60, 'name': 'ths_status', 'sortable':True , 'fontSize' : 12},
                   #{'title': '同花顺', 'width': 150, 'name': 'ths_ztReason', 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True},
                   #{'title': '', 'width': 10, 'name': 'sp'},
                   #{'title': '同花顺备注', 'width': 120, 'name': 'ths_mark_1', 'fontSize' : 12 , 'editable':True, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   #{'title': '财联社', 'width': 120, 'name': 'cls_ztReason', 'fontSize' : 12 ,'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER, 'sortable':True },
                   {'title': '板块', 'width': 220, 'name': 'hy', 'sortable':True , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   #{'title': '财联社详细', 'width': 0, 'name': 'cls_detail', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        flowLayout = base_win.FlowLayout(20)
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 30))
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 60, 30))
        btn.addListener(self.onRefresh)
        dp = base_win.DatePicker()
        dp.createWindow(self.hwnd, (0, 0, 120, 30))
        def onPickDate(evt, args):
            self.runTask()
        dp.addNamedListener('Select', onPickDate)

        flowLayout.addContent(dp)
        flowLayout.addContent(self.editorWin)
        flowLayout.addContent(btn)
        flowLayout.addContent(self.checkBox)
        self.layout.setContent(0, 0, flowLayout, {'horExpand': -1})
        self.layout.setContent(1, 1, self.tableWin, {'horExpand': -1})
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)
        self.tableWin.addListener(self.onDbClick, None)
        self.tableWin.addNamedListener('ContextMenu', self.onContextMenu)
        sm = base_win.ThsShareMemory.instance()
        sm.open()

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

    def onRefresh(self, evt, args):
        if evt.name == 'Click':
            self.tckData = None
            base_win.ThreadPool.instance().addTask('TCK', self.runTask)
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
        
    def loadAllData(self):
        if self.tckData != None:
            return
        #today = datetime.date.today()
        #fd = today - datetime.timedelta(days = 60)
        #fromDay = f"{fd.year}-{fd.month :02d}-{fd.day :02d}"
        #kplQr = tck_orm.KPL_ZT.select().where(tck_orm.KPL_ZT.day >= fromDay).order_by(tck_orm.KPL_ZT.day.desc(), tck_orm.KPL_ZT.id.asc()).dicts()
        #thsQr = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day >= fromDay).dicts()
        #clsQr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day >= fromDay).dicts()
        days = hot_utils.getTradeDaysByHot()
        qr = zs_orm.RealZSModel.select().where(zs_orm.RealZSModel.day >= days[-1]).dicts()
        
        datas = []
        for d in qr:
            m = d['minuts']
            d['s_minuts'] = f'{m // 10000 :02d}:{m // 100 % 100 :02d}:{m % 100 :02d}' 
            nn = utils.get_THS_GNTC(d['code'])
            if nn:
                d.update(nn)
            
            datas.append(d)

        #htsNewest = hot_utils.DynamicHotZH.instance().getNewestHotZH()
        #for d in htsNewest:
        #    item = htsNewest[d]
        #    day = item['day']
        #    day = f"{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}"
        #    k = f"{day}:{item['code'] :06d}"
        #    hots[k] = item['zhHotOrder']
      
        #rs.sort(key = lambda d : d['day'], reverse = True)
        self.tckData = datas

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
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    base_win.ThreadPool.instance().start()
    fp = ZS_Window()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    fp.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()