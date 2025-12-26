import win32gui, win32ui, win32con, re, io, traceback, sys, datetime, time, copy, os
from PIL import Image
#from cnocr import CnOcr

# pip install cnocr -i  https://pypi.tuna.tsinghua.edu.cn/simple
# https://blog.csdn.net/bugang4663/article/details/131687243?spm=1001.2014.3001.5501

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from THS import ths_win, number_ocr
from ui import base_win

#委比
class ThsWbOcrUtils(number_ocr.DumpWindowUtils):
    def __init__(self) -> None:
        self.titleHwnds = set()
        self.wbOcr = number_ocr.NumberOCR('wb', '+-.%0123456789')
        #self.codeOcr = CnOcr(cand_alphabet = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])

    # wb = 委比 28.45
    # diff = 委差
    # price = 当前成交价
    def calcBS(self, rs):
        if (not rs) or ('wb' not in rs) or ('diff' not in rs):
            return
        wb, diff, price = rs['wb'], rs['diff'], rs['price']
        if wb == 0:
            return
        wb /= 100
        sumv = diff / wb
        b = int((sumv + diff) / 2)
        s = int(b - diff)
        buy = abs(int(b * 100 * price / 10000))
        sell = abs(int(s * 100 * price / 10000))
        rs['buy'] = buy # 万元
        rs['sell'] = sell # 万元

    def dumpStockTitleWindow(self, thsMainWin):
        if (not thsMainWin) or (not win32gui.IsWindow(thsMainWin)) or (not win32gui.IsWindowVisible(thsMainWin)):
            return None
        hwnd = self.findWindow(thsMainWin, 'stock_title_page', '')
        if not hwnd:
            return None
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        WB_WIN_HEIGHT = 30
        srcSize = w, h + WB_WIN_HEIGHT
        imgFull = self.dumpImg(hwnd, (0, 0, *srcSize))
        LEFT_PADDING = 3
        codeImg = imgFull.crop((LEFT_PADDING, 2, w - LEFT_PADDING, h // 2))
        priceImg = imgFull.crop((LEFT_PADDING, h // 2, w - LEFT_PADDING, h - 1))

        WB_TXT_WIDTH = 35
        r = max(srcSize[0] - 70, w * 0.6)
        wbImg = imgFull.crop((WB_TXT_WIDTH, srcSize[1] - WB_WIN_HEIGHT + 1, int(r), srcSize[1]))
        wbEImg = number_ocr.EImage(wbImg)
        y = wbEImg.findRowColorIs(0, wbImg.width, 255)
        wbImg = wbImg.crop((0, 0, wbImg.width, y))
        #sign = bi.calcSign(wbImg)
        #wbImg = bi.expand(wbImg)
        # wbImg.save('D:/a.bmp')
        return codeImg, priceImg, wbImg
    
    def dumpStockUnitWindow(self, thsMainWin):
        if (not thsMainWin) or (not win32gui.IsWindow(thsMainWin)) or (not win32gui.IsWindowVisible(thsMainWin)):
            return None
        hwnd = self.findWindow(thsMainWin, '#32770', '个股单元表')
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        ROW_NUM = 4 # 一共4行
        imgFull = self.dumpImg(hwnd, (0, 0, w, int(h / ROW_NUM)))
        # imgFull.save('D:/price.bmp')
        return imgFull
    
    def parseCodeName(self, img : Image, rs):
        # img.save('D:/code.bmp')
        code = number_ocr.readCodeFromImage(img)
        if not code:
            return False
        rs['code'] = code
        rs['name'] = ''
        if rs['code'][0 : 2] not in ('00', '30', '60', '68', '88'):
            return False
        return True
    
    def parsePrice(self, img : Image, rs):
        #img.save('D:/price.bmp')
        try:
            rs['price'] = 0
            text = number_ocr.readTextfromImage(img, whitelist = '0123456789+-.')
            text = text.strip()
            cc = re.compile('^[+-]?\\d+[.]\d+')
            ma = cc.match(text)
            if ma:
                text = ma.group()
                rs['price'] = float(text)
        except Exception as e:
            print(f'Error: [parsePrice] price text =[{text}]')
            traceback.print_exc()
            return False
        return True

    def parseWeiBi(self, wbImg, rs):
        # wbImg.save('D:/wb.bmp')
        wsstrs = self.wbOcr.match(wbImg)
        if not wsstrs:
            return False
        cc = re.compile('^([+-]?\\d+[.]*\\d*)%\s*([+-]?\\d+)')
        ma = cc.match(wsstrs)
        if not ma:
            return False
        rs['wb'] = float(ma.group(1))
        rs['diff'] = int(ma.group(2))
        return True
    
    def parseNumSign(self, rs : dict, img : Image, name):
        rc = rs[name + '_pos']
        y = (rc[1] + rc[3]) // 2
        #print(rc, 'y = ', y)
        MAX_PIX = 5
        rn, gn = 0, 0
        w, h = img.size
        for x in range(rc[0], max(rc[2], w)):
            r, g, b = img.getpixel((x, y))
            #print(rgb, end = ' ')
            if r > g * 2 and r > b * 2:
                rn += 1
            elif g > r * 2 and g > b * 2:
                gn += 1
            if rn >= MAX_PIX:
                rs[name + '_sign'] = True
            elif gn >= MAX_PIX:
                rs[name + '_sign'] = False

    def findWindow(self, parentWnd, className, title):
        if not parentWnd:
            return None
        hwnd = win32gui.GetWindow(parentWnd, win32con.GW_CHILD)
        rs = None
        while hwnd:
            if not win32gui.IsWindowVisible(hwnd):
                hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
                continue
            cl = win32gui.GetClassName(hwnd)
            t = win32gui.GetWindowText(hwnd)
            if cl == className:
                if type(title) == str and t == title:
                    rs = hwnd
                    break
                elif isinstance(title, re.Pattern) and title.fullmatch(t):
                    rs = hwnd
                    break
            if rs:
                break
            xrs = self.findWindow(hwnd, className, title)
            if xrs:
                rs = xrs
                break
            hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        return rs

    def parseNW_Pan(self, txt, name, rs):
        W = 1
        if '万' in txt:
            W = 10000
            txt = txt.replace('万', '')
        p = int(float(txt) * W)
        v = int(p * rs['price'] * 100) # 元
        rs[name] = p
        rs[name + 'Amount'] = v
        if v >= 100000000:
            rs[name + 'AmountFmt'] = f'{v / 100000000 :.1f}亿'
        else:
            rs[name + 'AmountFmt'] = f'{v // 10000}万'

    def parseStockUnit(self, img, rs):
        eimg = number_ocr.EImage(img)
        img = eimg.expand()
        bits = self.imgToBmpBytes(img)
        result = self.ocr.readtext(bits, allowlist = '0123456789.万外盘内盘')
        txt = ''
        for r in result:
            txt += r[1]
        p = re.compile('^外盘(.*?)内盘(.*)')
        rt = p.findall(txt)[0]
        neiPan, waiPan = rt[0], rt[1]
        self.parseNW_Pan(neiPan, 'waiPan', rs)
        self.parseNW_Pan(waiPan, 'neiPan', rs)

    def runOcr(self, thsMainWin):
        rs = {}
        try:
            imgs = self.dumpStockTitleWindow(thsMainWin)
            if not imgs:
                return None
            codeImg, priceImg, wbImg = imgs
            if not self.parseCodeName(codeImg, rs):
                return None
            if not self.parsePrice(priceImg, rs):
                return rs
            if not self.parseWeiBi(wbImg, rs):
                return rs
            self.calcBS(rs)
            # img = self.dumpStockUnitWindow(thsMainWin)
            # self.parseStockUnit(img, rs)
            return rs
        except Exception as e:
            traceback.print_exc()
            print('ths_ocr:', rs)
        return rs

# 涨速排名
class ThsZhangShuOcrUtils(number_ocr.DumpWindowUtils):
    MIN_ZHANG_SU = 4 # 最小涨速

    def __init__(self) -> None:
        super().__init__()
        self.ocr = number_ocr.eocr() # ch_sim
        self.today = None
        self.datas = {} # code : []
        self.thread = base_win.TimerThread()
        self.thread.addIntervalTask('ZS-OCR', 10, self.run)

    def start(self):
        from orm import speed_orm
        today = datetime.date.today()
        iday = today.year * 10000 + today.month * 100 + today.day
        qr = speed_orm.RealSpeedModel.select().where(speed_orm.RealSpeedModel.day == iday)
        for it in qr:
            v = copy.copy(it.__data__)
            v['obj'] = it
            if it.code not in self.datas:
                self.datas[it.code] = []
            self.datas[it.code].append(v)
        self.today = iday
        self.thread.start()

    def dumpZhangShu(self, hwnd):
        if (not hwnd) or (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        if w < 600 or h < 200:
            return None
        ZHANG_SU_MAX_RECT = (230, 50, 600, 500) # 涨速区域最大范围
        imgFull = self.dumpImg(hwnd, ZHANG_SU_MAX_RECT)

        beImg = number_ocr.BaseEImage(imgFull)
        #beImg.bImg.save('D:/zs-full.bmp')
        #img_PIL.show()
        SEARCH_BOX_SIZE = (2, 50)
        startSplitVerLineX = beImg.horSearchBoxColor(0, beImg.bImg.height // 2, *SEARCH_BOX_SIZE, 255)
        if startSplitVerLineX < 0:
            return None
        startSplitVerLineX += 2
        ZHANG_SU_MIN_WIDTH = 200
        endSplitVerLineX = beImg.horSearchBoxColor(startSplitVerLineX + ZHANG_SU_MIN_WIDTH, beImg.bImg.height // 2, *SEARCH_BOX_SIZE, 255)
        if endSplitVerLineX < 0:
            return None
        PRICE_AREA_WIDTH = 62 # 代码区，宽62
        codeImg = imgFull.crop((startSplitVerLineX, 0, startSplitVerLineX + PRICE_AREA_WIDTH, beImg.bImg.height))
        #codeImg.save('D:/code.bmp')

        ZHANG_FU_AREA_WIDTH = 65 # 涨幅区，宽65
        sx = endSplitVerLineX - ZHANG_FU_AREA_WIDTH
        priceImg = imgFull.crop((sx, 0, endSplitVerLineX, beImg.bImg.height))
        #priceImg.save('D:/price.bmp')
        return codeImg, priceImg
    
    def runOcr(self, thsMainWnd):
        imgs = self.dumpZhangShu(thsMainWnd)
        if not imgs:
            return None
        codeImg, zfImg = imgs
        bits = self.imgToBmpBytes(codeImg)
        codes = self.ocr.readtext(bits, allowlist ='0123456789')
        bits = self.imgToBmpBytes(zfImg)
        zfs = self.ocr.readtext(bits, allowlist ='0123456789.+-%')

        arr = []
        nowTime = time.time()
        now = datetime.datetime.now()
        day = now.year * 10000 + now.month * 100 + now.day
        minuts = now.hour * 10000 + now.minute * 100 + now.second
        num = min(len(codes), len(zfs))
        for i in range(num):
            codeInfo = codes[i]
            zfInfo = zfs[i]
            if codeInfo[2] > 0.7 and len(codeInfo[1]) == 6:
                zf = zfInfo[1]
                if zf[0] == '+':
                    zf = zf[1 : ]
                elif zf[0] == '-':
                    continue
                if '%' in zf:
                    zf = zf[0 : zf.index('%')]
                zf = float(zf)
                if zf < self.MIN_ZHANG_SU:
                    continue
                item = {'code' : codeInfo[1], 'day' : day, 'minuts' : minuts, 'zf': zf, 'time': int(nowTime)}
                #print(item)
                arr.append(item)
        return arr

    def checkTime(self):
        now = datetime.datetime.now()
        wk = now.weekday()
        if wk > 4: # week 6, 7
            return False
        st = now.strftime('%H:%M:%S')
        if st >= '09:30:00' and st <= '11:30:00':
            return True
        if st >= '13:00:00' and st <= '15:00:00':
            return True
        return False
    
    def print(self, rs):
        from Tck import utils
        if not rs:
            now = datetime.datetime.now()
            st = now.strftime('%H:%M:%S')
            print('ZS-OCR: ', st, 'None')
            return
        m = rs[0]['minuts']
        print('ZS-OCR: ', f'{m // 10000:02d}:{m // 100 % 100:02d}:{m % 100:02d}', f'--> {len(rs)}')
        COL_NUM = 4
        for i in range(len(rs)):
            end = '\n' if (i + 1) % COL_NUM == 0 else ' | '
            r = rs[i]
            obj = utils.get_THS_GNTC(r['code'])
            name = obj['name'] if obj and obj['name'] else ''
            sx = 0
            for n in name:
                sx += 1 if ord(n) < 255 else 2
            name += ' ' * (8 - sx)
            prefix = ''
            sufix = ''
            if r['op'] == 'Create':
                prefix = '\033[31m'
                sufix = '\033[0m'
            elif r['op'] == 'Update':
                prefix = '\033[36m'
                sufix = '\033[0m'
            print(prefix, f'  {r["code"]} {name} {r["zf"] :>5.2f}%', sufix, sep = '', end = end)
        if len(rs) % COL_NUM != 0:
            print('')
    
    def run(self):
        try:
            if not self.checkTime():
                return
            ths = ths_win.ThsWindow()
            ths.init()
            if not ths.mainHwnd:
                return
            ths.showMax()
            rs = self.runOcr(ths.mainHwnd)
            self.saveOcrResult(rs)
            #self.print(rs)
        except Exception as e:
            traceback.print_exc()
            pass

    def saveOcrResult(self, rs):
        if not rs:
            return
        from orm import speed_orm
        first = rs[0]
        if first['day'] != self.today:
            self.today = first['day']
            self.datas.clear()
        for r in  rs:
            code = r['code']
            r['op'] = 'NoOp'
            if code not in self.datas:
                self.datas[code] = [r]
                obj = speed_orm.RealSpeedModel.create(code = r['code'], day = r['day'], minuts = r['minuts'], zf = r['zf'], time = r['time'])
                r['obj'] = obj
                r['op'] = 'Create'
                continue
            last = self.datas[code][-1]
            if last['zf'] < r['zf']:
                if last['time'] - r['time'] > 10 * 60:
                    obj = speed_orm.RealSpeedModel.create(code = r['code'], day = r['day'], minuts = r['minuts'], zf = r['zf'], time = r['time'])
                    r['obj'] = obj
                    cl = self.datas[code]
                    cl.append(r)
                    r['op'] = 'Create'
                else:
                    obj = last['obj']
                    obj.zf = last['zf'] = r['zf']
                    obj.save()
                    r['op'] = 'Update'

def test_wb_main1():
    ths = ths_win.ThsWindow()
    ths.init()
    wb = ThsWbOcrUtils()
    while True:
        rs = wb.runOcr(ths.mainHwnd)
        print(rs)
        #break
        time.sleep(10)

def test_zs_main2():
    thsWin = ths_win.ThsWindow()
    thsWin.init()
    thsWin.showMax()
    zs = ThsZhangShuOcrUtils()
    dst = {}
    while True:
        #ts = time.time()
        rs = zs.runOcr(thsWin.mainHwnd, 4)
        #ts2 = time.time()
        #print('use time:', ts2 - ts)
        time.sleep(10)
        break

if __name__ == '__main__':
    thsWin = ths_win.ThsWindow()
    thsWin.init()
    import platform
    print(platform.node())
    s = ThsWbOcrUtils()
    # s.runOcr(thsWin.mainHwnd)
    print(f'mainWin={thsWin.mainHwnd :X}')
    while True:
        rs = s.runOcr(thsWin.mainHwnd)
        print(rs)
        time.sleep(3)
        break
    # time.sleep(100)