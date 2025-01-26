import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import cls
from Common import base_win
from Tck import mark_utils

class HotTCWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        #self.css['bgColor'] = 0x202020
        self.tableWin = None
        self.detalWin = None
        self.daysCombox = None
        self.detailDatas = []

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        flowLayout = base_win.FlowLayout()
        self.daysCombox = base_win.ComboBox()
        self.daysCombox.setPopupTip([{'title': '近5日', 'val': 5}, {'title': '近10日', 'val': 10}])
        self.daysCombox.createWindow(self.hwnd, (0, 0, 150, 30))
        flowLayout.addContent(self.daysCombox)

        def formateMoney(colName, val, rowData):
            return f'{val}亿'
        def hotSorter(colName, val, rowData, allDatas, asc):
            return val if val is not None else 1000

        headers = [
                   {'title': '', 'width': 30, 'name': '#idx' },
                   #{'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render_': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '名称', 'width': 0, 'stretch': 1, 'name': 'name', 'sortable':True, 'render_': mark_utils.markColorTextRender , 'fontSize': 14},
                   {'title': '涨', 'width': 70,  'name': 'up', 'sortable':True, 'fontSize': 14},
                   {'title': '跌', 'width': 70,  'name': 'down', 'sortable':True, 'fontSize': 14},
                   {'title': '总', 'width': 70,  'name': 'sum', 'sortable':True, 'fontSize': 14},
                   ]
        self.tableWin = win = base_win.TableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        win.rowHeight = 30
        #win.enableDrag = True
        win.createWindow(self.hwnd, (0, 0, 1, 1))
        win.headers = headers
        win.addNamedListener('SelectRow', self.onSelectRow)
        #win.addNamedListener('ContextMenu', self.onContextMenu)
        #win.addNamedListener('DragEnd', self.onDragMove)
        self.daysCombox.addNamedListener('Select', self.onSelectDays)

        def formateFx(colName, val, rowData):
            if val == 'up':
                return '涨'
            return '跌'
        headers2 = [
            {'title': '', 'width': 30, 'name': '#idx' },
            {'title': '名称', 'width': 150,  'name': 'symbol_name', 'fontSize': 14},
            {'title': '星期', 'width': 80,  'name': 'datetime-fmt', 'fontSize': 14},
            {'title': '时间', 'width': 250,  'name': 'c_time', 'fontSize': 14},
            {'title': '涨跌', 'width': 70,  'name': 'float', 'fontSize': 14, 'formater': formateFx},
        ]
        self.detalWin = base_win.TableWindow()
        self.detalWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.detalWin.css['selBgColor'] = 0xEAD6D6
        self.detalWin.rowHeight = 30
        self.detalWin.headers = headers2

        rows = (30, '1fr')
        cols = (400, '1fr')
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.layout.setContent(0, 0, flowLayout)
        self.layout.setContent(1, 0, win)
        self.layout.setContent(1, 1, self.detalWin)

    def onShow(self):
        idx = self.daysCombox.selIdx
        if idx < 0:
            self.daysCombox.setSelectItem(0)
        else:
            item = self.daysCombox.popupTipModel[idx]
            self.initMySelect(item['val'])

    def onSelectDays(self, evt, args):
        self.initMySelect(evt.val)

    def initMySelect(self, days):
        pass
        base_win.ThreadPool.instance().addTask('load-cls-hots', self.initMySelect_, days)

    def initMySelect_(self, days):
        rs = []
        n = 0
        curDay = datetime.date.today()
        while n <= days:
            url = cls.ClsUrl()
            ds = url.loadHotTC(curDay)
            if ds:
                rs.extend(ds)
                n += 1
            curDay -= datetime.timedelta(days = 1)
        #mark_utils.mergeMarks(rs, 'cls-hot-tc', False)
        sums = {}
        ds = []
        for it in rs:
            if 'symbol_name' not in it:
                continue
            self.formatObject(it)
            name = it['symbol_name']
            if name not in sums:
                sums[name] = {'name': name, 'up': 0, 'down': 0, 'sum': 0}
                ds.append(sums[name])
            sums[name][it['float']] += 1
            sums[name]['sum'] += 1
        self.detailDatas = rs
        self.tableWin.setData(ds)
        self.tableWin.setSortHeader(self.tableWin.getHeaderByName('up'), 'DSC')
        self.tableWin.invalidWindow()

    def onDragMove(self, evt, args):
        pass

    def onContextMenu(self, evt, args):
        pass

    def formatObject(self, obj):
        c_time = obj['c_time']
        ds = datetime.datetime.strptime(c_time, '%Y-%m-%d %H:%M:%S')
        obj['datetime'] = ds
        w = ds.weekday()
        obj['datetime-fmt'] = '周' + '一二三四五六日'[w]
    
    def onSelectRow(self, evt, args):
        rs = []
        name = evt.data['name']
        for it in self.detailDatas:
            if it['symbol_name'] == name:
                rs.append(it)
        self.detalWin.setData(rs)
        self.detalWin.invalidWindow()

if __name__ == '__main__':
    fp = HotTCWindow()
    fp.createWindow(None, (0, 0, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()