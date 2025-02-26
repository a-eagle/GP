import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re
import peewee as pw

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
        self.layout = base_win.GridLayout(rows, ('1fr', ), (5, 10))
        self.tableWin = ext_win.EditTableWindow()
        self.tableWin.css['selBgColor'] = 0xEAD6D6
        self.editorWin = base_win.ComboBox()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.editorWin.editable = True
        self.openInThsWin = base_win.CheckBox({'title': '在同花顺中打开'})
        self.datePicker = base_win.DatePicker()
        self.qcCheckBox = base_win.CheckBox({'title': '去重'})
        self.hotTcNamesWin = base_win.ComboBox()

        self.ztListData = None
        self.searchData = None
        self.searchText = ''
        self.inputTips = []
        self.clsHotGns = {} # {day: [], ...}

    def createWindow(self, parentWnd, rect, style=win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title='涨停+热点概念（选股）'):
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
                   {'title': '关联财联社热点', 'width': 250, 'name': 'hotTcName', 'sortable':True , 'fontSize' : 12,  'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   {'title': '分时图', 'width': 250, 'name': 'FS', 'render': cache.renderTimeline, 'LOCAL-FS-DAY': getLocalFsDay},
                   #{'title': '详情', 'width': 0, 'name': '_detail_', 'stretch': 1 , 'fontSize' : 12, 'textAlign': win32con.DT_LEFT | win32con.DT_WORDBREAK | win32con.DT_VCENTER},
                   ]
        
        flowLayout = base_win.FlowLayout(20)
        self.openInThsWin.createWindow(self.hwnd, (0, 0, 160, 30))
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        self.tableWin.createWindow(self.hwnd, (0, 0, 1, 1))
        self.tableWin.rowHeight = 50
        self.tableWin.headers = headers
        self.datePicker.createWindow(self.hwnd, (0, 0, 120, 30))
        def onPickDay(evt, args):
            self.loadClsHotGnBySelDays()
            self.loadAllData()
            self.onQuery()
        self.datePicker.addNamedListener('Select', onPickDay)
        #lb = base_win.Label('日期')
        #lb.createWindow(self.hwnd, (0, 0, 40, 30))
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 50, 30))
        btn.addNamedListener('Click', self.onRefresh)
        self.qcCheckBox.createWindow(self.hwnd, (0, 0, 60, 30))
        def onCheck(evt, args):
            self.onQuery()
        self.qcCheckBox.addNamedListener('Checked', onCheck)
        self.hotTcNamesWin.createWindow(self.hwnd, (0, 0, 150, 30))
        self.hotTcNamesWin.addNamedListener('Select', self.onSelectHotTc)
        
        #flowLayout.addContent(lb)
        flowLayout.addContent(self.datePicker, {'margins': (100, 0, 0, 0)})
        flowLayout.addContent(self.hotTcNamesWin)
        flowLayout.addContent(self.editorWin)
        flowLayout.addContent(btn)
        flowLayout.addContent(self.qcCheckBox)
        flowLayout.addContent(self.openInThsWin)
        self.layout.setContent(0, 0, flowLayout, {'horExpand': -1})
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
        self.searchData = self.filterHotTc(self.searchData)
        self.tableWin.setData(self.searchData)
        if self.searchData:
            mark_utils.mergeMarks(self.searchData, 'xgc', False)
        self.tableWin.invalidWindow()

    def filterHotTc(self, datas):
        if not datas:
            return datas
        rs = []
        ht = self.hotTcNamesWin.getSelectItem()
        ffCode = None
        if ht and ht.get('code', None):
            ffCode = ht['code']
        from Tck import utils
        for d in datas:
            day = d['day']
            #d['hotTcCode'] = ''
            d['hotTcName'] = ''
            d['hotTcMaxNum'] = 0
            hots = []
            gns = self.clsHotGns.get(day)
            if not gns:
                continue
            obj = utils.cls_gntc_s.get(d['code'])
            if not obj:
                continue
            for gn in gns:
                code, name, num = gn
                if code in (obj['hy_code'] or '') or code in (obj['gn_code'] or ''):
                    d['hotTcMaxNum'] = max(d['hotTcMaxNum'], num)
                    hots.append(gn)
            if d['hotTcMaxNum'] == 0:
                continue
            fd = False
            for i, gn in enumerate(hots):
                #d['hotTcCode'] += gn[0] + ';'
                d['hotTcName'] += f"{gn[1]}{gn[2]}"
                if i != len(hots) - 1:
                    d['hotTcName'] += ' | '
                if not ffCode or gn[0] == ffCode:
                    fd = True
            if fd:
                rs.append(d)
        return rs

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
        if self.openInThsWin.isChecked():
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
        qr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day == selDayStr).dicts()
        qr2 = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day == selDayStr).dicts()
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

        qr = ths_orm.THS_HotZH.select().where(ths_orm.THS_HotZH.day == selDay).dicts()
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
                    if ('_id' in k or k == 'detail'):
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
    
    def loadClsHotGnBySelDays(self):
        selDay = self.datePicker.getSelDay()
        if not selDay:
            return
        qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.day.distinct()).where(tck_orm.CLS_HotTc.day == selDay).tuples()
        for it in qr:
            day = it[0]
            self.loadClsHotGn(day)
        hotTc = self.clsHotGns.get(selDay)
        model = [{'title': '  <All>', 'code': '', 'hot-name': '', 'num': 0}]
        if hotTc:
            for h in hotTc:
                code, name, num = h
                model.append({'title': f'{num: 3d}  {name}', 'code': code, 'hot-name': name, 'num': num})
        self.hotTcNamesWin.setPopupTip(model)

    def onSelectHotTc(self, evt, args):
        self.onQuery()

    def loadClsHotGn(self, lastDay, limitDaysNum = 10):
        qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.day.distinct()).order_by(tck_orm.CLS_HotTc.day.desc()).tuples()
        days = []
        for it in qr:
            if (lastDay is None) or (it[0] <= lastDay):
                days.append(it[0])
            if len(days) >= limitDaysNum: # 仅显示近N天的热点概念
                break
        if not days:
            self.clsHotGns[lastDay] = None
            return
        fromDay = days[-1]
        endDay = days[0]
        rs = []
        qr = tck_orm.CLS_HotTc.select(tck_orm.CLS_HotTc.code, tck_orm.CLS_HotTc.name, pw.fn.count()).where(tck_orm.CLS_HotTc.day >= fromDay, tck_orm.CLS_HotTc.day <= endDay, tck_orm.CLS_HotTc.up == True).group_by(tck_orm.CLS_HotTc.name).tuples()
        for it in qr:
            clsCode, clsName, num = it
            rs.append((clsCode, clsName.strip(), num))
        rs.sort(key = lambda k : k[2], reverse = True)
        self.clsHotGns[lastDay] = rs

if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    win = XGC_Window()
    win.createWindow(None, (0, 100, 1500, 700), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    win.layout.resize(0, 0, *win.getClientSize())
    win32gui.ShowWindow(win.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()