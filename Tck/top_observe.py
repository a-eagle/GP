import win32gui, win32con , win32api, win32ui, pyautogui # pip install pywin32
import threading, time, datetime, sys, os, copy
import os, sys, requests

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import tck_def_orm
from THS import hot_utils
from Common import base_win
from Tck import  kline_utils, mark_utils, cache, utils

class MyWindow(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        #self.css['bgColor'] = 0x202020
        self.checkBox_THS = None
        self.tableWin = None
        self.kindCombox = None

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        self.checkBox_THS = base_win.CheckBox({'title': '在同花顺中打开'})
        self.checkBox_THS.createWindow(self.hwnd, (0, 0, 150, 30))
        flowLayout = base_win.FlowLayout()
        flowLayout.addContent(self.checkBox_THS, {'margins': (10, 0, 10, 0)})
        self.kindCombox = base_win.ComboBox()
        self.kindCombox.setPopupTip([{'title': '默认', 'kind': 'def'}, {'title': '涨停观察股', 'kind': 'zt'}])
        self.kindCombox.createWindow(self.hwnd, (0, 0, 150, 30))
        flowLayout.addContent(self.kindCombox)

        def formateMoney(colName, val, rowData):
            return f'{val}亿'
        def dayFormate(colName, val, rowData):
            if not val:
                return ''
            if isinstance(val, datetime.date):
                return f'{val.month :02d}-{val.day :02d}'
            if isinstance(val, str):
                return val[5 : ]
            return val
        def hotSorter(colName, val, rowData, allDatas, asc):
            return val if val is not None else 1000

        headers = [
                   {'title': '', 'width': 30, 'name': '#idx' },
                   {'title': 'M', 'width': 30, 'name': 'markColor', 'sortable':True , 'render': mark_utils.markColorBoxRender, 'sorter': mark_utils.sortMarkColor },
                   {'title': '代码', 'width': 80, 'name': 'code', 'sortable':True},
                   {'title': '名称', 'width': 80, 'name': 'name', 'sortable':True, 'render': mark_utils.markColorTextRender },
                   {'title': '市值', 'width': 80, 'name': 'zsz', 'sortable':True, 'formater': formateMoney},
                   {'title': '热度', 'width': 80, 'name': 'zhHotOrder', 'sortable':True, 'sorter': hotSorter},
                   {'title': '板块', 'width': 200,  'name': 'bk', 'sortable':True, 'fontSize': 12},
                   {'title': '加入日期', 'width': 140, 'name': 'day', 'sortable':True , 'formater_': dayFormate, 'textAlign': win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_SINGLELINE},
                   {'title': '分时', 'width': 300, 'name': 'code', 'stretch_': 1,  'render': cache.renderTimeline}
                   ]
        self.tableWin = win = base_win.TableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        win.rowHeight = 50
        win.enableDrag = True
        win.createWindow(self.hwnd, (0, 0, 1, 1))
        win.headers = headers
        win.addListener(self.onDbClick)
        win.addNamedListener('ContextMenu', self.onContextMenu)
        win.addNamedListener('DragEnd', self.onDragMove)
        self.kindCombox.addNamedListener('Select', self.onSelectKind)

        rows = (30, '1fr')
        cols = ('1fr', )
        self.layout = base_win.GridLayout(rows, cols, (5, 10))
        self.layout.setContent(0, 0, flowLayout)
        self.layout.setContent(1, 0, win)

    def onShow(self):
        idx = self.kindCombox.selIdx
        if idx < 0:
            self.kindCombox.setSelectItem(0)
        else:
            item = self.kindCombox.popupTipModel[idx]
            self.initMySelect(item['kind'])

    def onSelectKind(self, evt, args):
        kind = evt.kind
        self.initMySelect(kind)

    def initMySelect(self, kind):
        hots = hot_utils.DynamicHotZH.ins.getNewestHotZH()
        rs = []
        q = tck_def_orm.MyObserve.select().where(tck_def_orm.MyObserve.kind == kind).dicts() # .order_by(tck_def_orm.MyObserve.order.asc())
        for it in q:
            rs.append(it)
            h = hots.get(int(it['code']), None)
            it['zhHotOrder'] = h['zhHotOrder'] if h else None
            bk = utils.get_THS_GNTC(it['code'])
            if bk:
                it['bk'] = bk['hy_2_name'] + '-' + bk['hy_3_name']
                it['ltsz'] = bk['ltsz']
                it['zsz'] = bk['zsz']
        mark_utils.mergeMarks(rs, 'observe-' + kind, False)
        self.tableWin.setData(rs)
        self.tableWin.setSortHeader(self.tableWin.getHeaderByName('bk'), 'ASC')
        self.tableWin.invalidWindow()

        for idx, d in enumerate(self.tableWin.getData()):
            order = idx + 1
            #tck_def_orm.MyObserve.update(order = order).where(tck_def_orm.MyObserve.id == d['id']).execute()

    def onDragMove(self, evt, args):
        pass

    def onContextMenu(self, evt, args):
        tableWin = evt.src
        row = tableWin.selRow
        kind = self.kindCombox.getSelectItem()['kind']
        rowData = tableWin.getData()[row] if row >= 0 else None
        model = mark_utils.getMarkModel(row >= 0)
        model.append({'title': 'LINE'})
        model.append({'title': '- 删除', 'name': 'del', 'enable': rowData is not None})
        model.append({'title': '导出', 'name': 'export'})
        model.append({'title': '导入', 'name': 'import'})
        menu = base_win.PopupMenu.create(self.hwnd, model)
        def onMenuItem(evt, rd):
            if evt.item['name'] == 'del':
                tck_def_orm.MyObserve.delete().where(tck_def_orm.MyObserve.code == rowData['code'], tck_def_orm.MyObserve.kind == kind).execute()
                dts : list = tableWin.getData()
                dts.pop(row)
            elif evt.item['name'] == 'export':
                pass
            elif evt.item['name'] == 'import':
                pass
            else:
                mark_utils.saveOneMarkColor({'kind': 'observe-' + kind, 'code': rowData['code']}, evt.item['markColor'], endDay = rowData['day'])
                rd['markColor'] = evt.item['markColor']
            tableWin.invalidWindow()
        menu.addNamedListener('Select', onMenuItem, rowData)
        x, y = win32gui.GetCursorPos()
        menu.show(x, y)
    
    def onDbClick(self, evt, idx):
        if evt.name != 'DbClick' and evt.name != 'RowEnter':
            return
        data = evt.data
        if not data:
            return
        if self.checkBox_THS.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            win = kline_utils.openInCurWindow_Code(self, data)
            win.setCodeList(evt.src.getData())

if __name__ == '__main__':
    fp = MyWindow()
    fp.createWindow(None, (0, 0, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    #fp.layout.resize(0, 0, w, h)
    win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()