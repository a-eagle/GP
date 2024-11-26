from win32.lib.win32con import WS_CHILD, WS_VISIBLE
import win32gui, win32con , win32api, win32ui # pip install pywin32
import threading, time, datetime, sys, os, copy, pyautogui
import os, sys, requests, re

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from THS import ths_win, hot_utils
from Common import base_win, ext_win
from orm import tck_orm, tck_orm
from Download import ths_iwencai, cls
from Tck import kline_utils, conf, mark_utils, utils, cache, ext_table

net_caches = {} # code : zf

class LianBanWindow(base_win.BaseWindow):
    ROW_HEIGHT = 60
    LB_WIDTH = 40
    ITEM_X_SPACE = 3
    ITEM_Y_SPACE = 3
    DAY_HEIGHT = 20

    def __init__(self) -> None:
        super().__init__()
        self.css['bgColor'] = 0xf0f0f0
        self.data = None
        self.items = None
        self.startRow = 0
        self.itemWidth = 0
        self.day = None

    def loadData(self, day):
        if not day:
            return
        self.data = None
        self.items = None
        day = str(day).replace('-', '')
        self.day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
        self.invalidWindow()
        base_win.ThreadPool.instance().addTask(f'LB-{day}', self._loadData, day)

    def _loadData(self, day):
        if type(day) == str:
            day = day.replace('-', '')
        fday = str(day)
        self.data = ths_iwencai.download_zt_lianban(fday)
        if not self.data:
            return
        
        fday = f'{fday[0 : 4]}-{fday[4 : 6]}-{fday[6 : 8]}'
        codes = {}
        q = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day == fday).dicts()
        for it in q:
            code = it['code']
            codes[code] = it
            it['ths_ztReason'] = it['ztReason']
            del it['ztReason']
            del it['name']
        q = tck_orm.CLS_ZT.select(tck_orm.CLS_ZT.code, tck_orm.CLS_ZT.ztReason).where(tck_orm.CLS_ZT.day == fday).dicts()
        for it in q:
            code = it['code']
            if code in codes:
                codes[code]['cls_ztReason'] = it['ztReason']
            else:
                codes[code] = {'cls_ztReason' : it['ztReason']}
        for i, d in enumerate(self.data):
            for j, m in enumerate(d['code_list']):
                code = m['code']
                if code in codes:
                    m.update(codes[code])
        self.buildView()
        self.invalidWindow()

    def buildView(self):
        self.items = None
        if not self.data:
            return
        W, H = self.getClientSize()
        ITEM_MIN_WIDTH = 150
        iw = W - self.LB_WIDTH
        colNum = max(iw // ITEM_MIN_WIDTH, 1)
        self.itemWidth = int(iw / colNum) - self.ITEM_X_SPACE
        row = 0
        items = []
        for i, d in enumerate(self.data):
            vn = 0
            for j, m in enumerate(d['code_list']):
                if not m.get('visible', True):
                    continue
                m['height'] = d['height']
                m['row'] = vn // colNum + row
                m['col'] = vn % colNum
                m['rowIdx'] = vn // colNum
                m['num'] = len(d['code_list'])
                items.append(m)
                vn += 1
            row += (vn + colNum - 1) // colNum
        self.items = items

    def onDraw(self, hdc):
        if not self.day:
            return
        W, H = self.getClientSize()
        drc = (0, 0, W, self.DAY_HEIGHT - 2)
        self.drawer.fillRect(hdc, drc, color = 0xDADAEA)
        self.drawer.drawText(hdc, '    ' + self.day, drc, color = 0xFF00FF, align = win32con.DT_LEFT | win32con.DT_VCENTER | win32con.DT_SINGLELINE)
        if not self.items:
            return
        for it in self.items:
            curRow = it['row'] - self.startRow
            if curRow < 0:
                continue
            y = curRow * (self.ROW_HEIGHT + self.ITEM_Y_SPACE) + self.DAY_HEIGHT
            TEXT_COLOR = 0x202020
            ISP = self.ROW_HEIGHT // 3
            if it['col'] == 0 and it['rowIdx'] == 0:
                rc = (0, y, self.LB_WIDTH - 3, y + self.ROW_HEIGHT)
                self.drawer.fillRect(hdc, rc, color = 0xd0d0d0)
                self.drawer.drawText(hdc, f'{it["height"]}板\n({it["num"]})', rc, color = TEXT_COLOR, align = win32con.DT_CENTER | win32con.DT_VCENTER | win32con.DT_WORDBREAK)
            
            x = self.LB_WIDTH + it['col'] * (self.itemWidth + self.ITEM_X_SPACE)
            rc = (x, y, x + self.itemWidth, y + self.ROW_HEIGHT)
            self.drawer.fillRect(hdc, rc, color = 0xE0E0E0)
            nameRc = (rc[0] + 20, rc[1], rc[0] + 80, rc[1] + ISP)
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 14, weight = 700))
            self.drawer.fillRect(hdc, nameRc, 0xD8D8FF)
            self.drawer.drawText(hdc, it['name'], nameRc, color = TEXT_COLOR, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            self.drawer.use(hdc, self.drawer.getFont(fontSize = 12, weight = 0))
            cc = self.loadCurZF(it['code'])
            if cc is not None:
                zf = cc['zf']
                zfRc = (rc[0], rc[1], rc[2] - 10, rc[1] + ISP)
                color = self.getZFColor(cc)
                self.drawer.drawText(hdc, f'{zf :.2f}%', zfRc, color = color, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE | win32con.DT_RIGHT)
            ZT_REASON_COLOR = 0x404040
            thsZT = it.get('ths_ztReason', None)
            f12 = self.drawer.getFont(fontSize = 12)
            if thsZT:
                self.drawer.use(hdc, f12)
                thsRc = (rc[0], rc[1] + ISP, rc[2], rc[1] + 2 * ISP)
                self.drawer.drawText(hdc, thsZT, thsRc, color = ZT_REASON_COLOR, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)
            clsZT = it.get('cls_ztReason', None)
            if clsZT:
                self.drawer.use(hdc, f12)
                clsRc = (rc[0], rc[3] - ISP, rc[2], rc[3])
                self.drawer.drawText(hdc, clsZT, clsRc, color = ZT_REASON_COLOR, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)

    def getZFColor(self, info):
        if info['zt']:
            return 0xcc2222
        if info['dt']:
            return 0x22aaaa
        color = 0x202020
        if info['zf'] > 0: color = 0x2222ff
        elif info['zf'] < 0: color = 0x22aa22
        return color

    def winProc(self, hwnd, msg, wParam, lParam):
        if msg == win32con.WM_SIZE and wParam != win32con.SIZE_MINIMIZED:
            self.buildView()
            # no return
        if msg == win32con.WM_LBUTTONDBLCLK:
            x, y = lParam & 0xffff, (lParam >> 16) & 0xffff
            self.onDbClick(x, y)
        return super().winProc(hwnd, msg, wParam, lParam)

    def onDbClick(self, x, y):
        pos = self.getItemAt(x, y)
        item = self.getItemByPos(pos)
        if not item:
            return
        self.notifyListener(self.Event('OpenCode', self, data = item))
        
    def getItemAt(self, x, y):
        x -= self.LB_WIDTH
        y -= self.DAY_HEIGHT
        if x < 0 or y < 0:
            return None
        rowIdx = y // (self.ROW_HEIGHT + self.ITEM_Y_SPACE)
        colIdx = x // int(self.itemWidth + self.ITEM_X_SPACE)
        sy = y - rowIdx * (self.ROW_HEIGHT + self.ITEM_Y_SPACE)
        if sy > self.ROW_HEIGHT:
            return None
        sx = x - colIdx * int(self.itemWidth + self.ITEM_X_SPACE)
        if sx > self.itemWidth:
            return None
        return rowIdx + self.startRow, colIdx

    def getItemByPos(self, pos):
        if not self.items or not pos:
            return None
        row, col = pos
        for it in self.items:
            if it['row'] == row and it['col'] == col:
                return it
        return None

    def loadCurZF(self, code):
        zf = net_caches.get(code, None)
        if zf is not None:
            return zf
        base_win.ThreadPool.instance().addTask(f'LB-ZF-{code}', self._loadCurZF, code)
        return None

    def _loadCurZF(self, code):
        url = cls.ClsUrl()
        data = url.loadKline(code, 2)
        if not data or len(data) != 2:
            return
        pre = data[-2].close
        cur = data[-1].close
        zf = (cur - pre) / pre * 100 if pre else 0
        info = net_caches[code] = {'zf': zf}
        # check is ZT
        MZF = 20 if code[0] == '3' or code[0 : 3] == '688' else 10
        icur = int(cur * 100 + 0.5)
        ztPrice = int(pre * (100 + MZF) + 0.5)
        dtPrice = int(pre * (100 - MZF) + 0.5)
        info['zt'] = icur >= ztPrice
        info['dt'] = icur <= dtPrice
        self.invalidWindow()

    def clearData(self):
        self.startRow = 0
        self.day = None
        self.items = None
        self.data = None
        self.invalidWindow()

    def onQuery(self, search : str):
        if not self.items:
            return
        if search is None:
            search = ''
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

        for d in self.data:
            for m in d['code_list']:
                m['visible'] = self.match(m, qrs, cond)
        self.buildView()
        self.invalidWindow()

    def match(self, data, qrs, cond):
        if not qrs:
            return True
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

# 连板天梯
class ZT_Window(base_win.BaseWindow):
    def __init__(self) -> None:
        super().__init__()
        self.layout = base_win.GridLayout((30, '1fr'), ('1fr', '1fr', '1fr', ), (5, 10))
        self.editorWin = base_win.Editor()
        self.editorWin.placeHolder = ' or条件: |分隔; and条件: 空格分隔'
        self.checkBox = base_win.CheckBox({'title': '在同花顺中打开'})
        self.lianBanWins = []
        self.datePicker = None
        self.tckData = None
        self.tckSearchData = None
        self.searchText = ''
        self.inputTips = []

        self.DAYS_NUM = 3

    def loadFromDay(self, lastDay = None):
        today = datetime.date.today()
        today = today.strftime('%Y%m%d')
        days = ths_iwencai.getTradeDays()
        if not lastDay:
            lastDay = days[-1]
        else:
            lastDay = str(lastDay).replace('-', '')
        cdays = []
        for i in range(len(days) - 1, 0, -1):
            if lastDay >= days[i]:
                if len(cdays) < self.DAYS_NUM:
                    cdays.append(str(days[i]))
                else:
                    break
        for i, day in enumerate(cdays):
            self.lianBanWins[i].loadData(day)

    def createWindow(self, parentWnd, rect, style = win32con.WS_VISIBLE | win32con.WS_CHILD, className='STATIC', title=''):
        super().createWindow(parentWnd, rect, style, className, title)
        flowLayout = base_win.FlowLayout(20)
        self.checkBox.createWindow(self.hwnd, (0, 0, 150, 30))
        self.editorWin.createWindow(self.hwnd, (0, 0, 300, 30))
        btn = base_win.Button({'title': '刷新'})
        btn.createWindow(self.hwnd, (0, 0, 60, 30))
        btn.addListener(self.onRefresh)
        self.datePicker = dp = base_win.DatePicker()
        dp.createWindow(self.hwnd, (0, 0, 120, 30))
        def onPickDate(evt, args):
            self.runTask(evt.sday)
        dp.addNamedListener('Select', onPickDate)
        for i in range(self.DAYS_NUM):
            win = LianBanWindow()
            self.lianBanWins.append(win)
            win.createWindow(self.hwnd, (0, 0, 1, 1))
            self.layout.setContent(1, i, win)
            win.addNamedListener('OpenCode', self.onOpenCode)

        fs = {'margins': (0, 3, 0, 0)}
        flowLayout.addContent(dp)
        flowLayout.addContent(self.editorWin)
        flowLayout.addContent(btn)
        flowLayout.addContent(self.checkBox)
        self.layout.setContent(0, 0, flowLayout, {'horExpand': -1})
        
        def onPressEnter(evt, args):
            q = evt.text.strip()
            self.onQuery(q)
            if q and (q not in self.inputTips):
                self.inputTips.append(q)
        self.editorWin.addNamedListener('PressEnter', onPressEnter, None)

    def onRefresh(self, evt, args):
        if evt.name == 'Click':
            self.runTask()

    def runTask(self, lastDay = None):
        base_win.ThreadPool.instance().addTask('ZT_LIANBAN_NET', self.loadFromDay, lastDay)

    def onQuery(self, queryText):
        for win in self.lianBanWins:
            win.onQuery(queryText)
    
    def onOpenCode(self, evt, args):
        data = evt.data
        if not data:
            return
        if self.checkBox.isChecked():
            kline_utils.openInThsWindow(data)
        else:
            win = kline_utils.openInCurWindow_Code(self, data)
        
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

    
if __name__ == '__main__':
    base_win.ThreadPool.instance().start()
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    fp = ZT_Window()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    h = 500
    fp.createWindow(None, (0, SH - h - 35, SW, h), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.layout.resize(0, 0, w, h)
    #fp.loadData(20241121)
    win32gui.ShowWindow(fp.hwnd, win32con.SW_MAXIMIZE)
    win32gui.PumpMessages()