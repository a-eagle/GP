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
        self.data = ths_iwencai.download_lianban(fday)
        if not self.data:
            return
        self.buildView()
        fday = f'{fday[0 : 4]}-{fday[4 : 6]}-{fday[6 : 8]}'
        codes = {}
        q = tck_orm.THS_ZT.select().where(tck_orm.THS_ZT.day == fday).dicts()
        for it in q:
            code = it['code']
            codes[code] = it
            it['ths_ztReason'] = it['ztReason']
            del it['ztReason']
            del it['name']
        q = tck_orm.CLS_ZT.select(tck_orm.CLS_ZT.ztReason).where(tck_orm.CLS_ZT.day == fday).dicts()
        for it in q:
            code = it['code']
            if code in codes:
                codes[code]['cls_ztReason'] = it['ztReason']
            else:
                codes[code] = {'cls_ztReason' : it['ztReason']}
        for d in self.items:
            code = d['code']
            if code in codes:
                d.update(codes[code])
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
            for j, m in enumerate(d['code_list']):
                m['height'] = d['height']
                m['row'] = j // colNum + row
                m['col'] = j % colNum
                m['rowIdx'] = j // colNum
                m['num'] = len(d['code_list'])
                items.append(m)
            row += (len(d['code_list']) + colNum - 1) // colNum
        self.items = items

    def onDraw(self, hdc):
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
            self.drawer.fillRect(hdc, rc, color = 0xd0d0d0)
            nameRc = (rc[0] + 10, rc[1], rc[0] + 80, rc[1] + ISP)
            self.drawer.drawText(hdc, it['name'], nameRc, color = TEXT_COLOR, align = win32con.DT_VCENTER | win32con.DT_SINGLELINE)
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
                clsRc = (rc[0], rc[2] - ISP, rc[2], rc[2])
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
        return super().winProc(hwnd, msg, wParam, lParam)

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

if __name__ == '__main__':
    ins = base_win.ThsShareMemory.instance()
    ins.open()
    base_win.ThreadPool.instance().start()
    fp = LianBanWindow()
    SW = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SH = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    W, H = 450, 500
    fp.createWindow(None, (0, 0, W, H), win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE)
    w, h = fp.getClientSize()
    fp.loadData(20241121)
    win32gui.ShowWindow(fp.hwnd, win32con.SW_SHOW)
    win32gui.PumpMessages()