import win32gui, win32ui, win32con, re, io, traceback, sys, datetime, time, copy
from PIL import Image
import easyocr

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from THS import ths_win, number_ocr
from Common import base_win
from Download import console

#委比
class ThsWbOcrUtils(number_ocr.DumpWindowUtils):
    def __init__(self) -> None:
        self.titleHwnds = set()
        self.wbOcr = number_ocr.NumberOCR('wb', '+-.%0123456789')
        self.ocr = number_ocr.eocr()

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

    def dump_InHomePage(self, hwnd):
        if (not hwnd) or (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        rc = win32gui.GetWindowRect(hwnd)
        w, h = rc[2] - rc[0], rc[3] - rc[1]
        WB_WIN_HEIGHT = 28
        srcSize = w, h + WB_WIN_HEIGHT

        imgFull = self.dumpImg(hwnd, (0, 0, *srcSize))
        LEFT_PADDING = 20
        codeImg = imgFull.crop((LEFT_PADDING, 2, w - LEFT_PADDING, h // 2))
        priceImg = imgFull.crop((LEFT_PADDING, h // 2, w - LEFT_PADDING, h - 1))
        #priceImg.save('D:/price.bmp')
        #codeImg.save('D:/code.bmp')
        #img_PIL.show()

        WB_TXT_WIDTH = 35
        r = max(srcSize[0] - 70, w * 0.6)
        wbImg = imgFull.crop((WB_TXT_WIDTH, srcSize[1] - WB_WIN_HEIGHT + 1, int(r), srcSize[1]))
        #sign = bi.calcSign(wbImg)
        #wbImg = bi.expand(wbImg)
        #wbImg.save('D:/a.bmp')
        return codeImg, priceImg, wbImg
    
    def parseCodeName(self, img, rs):
        bmpBytes = io.BytesIO()
        img.save(bmpBytes, format = 'bmp')
        bits = bmpBytes.getvalue()
        result = self.ocr.readtext(bits, allowlist = '0123456789')
        if not result:
            return False
        code = result[0][1]
        if len(code) < 6:
            return False
        rs['code'] = code[-6 : ]
        rs['name'] = ''
        if rs['code'][0 : 2] not in ('00', '30', '60', '68', '88'):
            return False
        return True
    
    def parsePrice(self, img : Image, rs):
        eimg = number_ocr.EImage(img)
        items = eimg.split()
        if not items:
            return False
        maxHeight, sn = 0, 0
        first = items[0]
        rect = [first[0], 0, 0, img.height]
        for it in items:
            h = it[3] - it[1]
            if maxHeight < h:
                maxHeight = h
            if maxHeight - h >= 4:
                sn += 1
            if sn > 1:
                rect[2] = it[0]
                break
        W = rect[2] - rect[0]
        if W <= 0:
            return False
        priceImg = img.crop(tuple(rect))
        bmpBytes = io.BytesIO()
        priceImg.save(bmpBytes, format = 'bmp')
        bits = bmpBytes.getvalue()
        result = self.ocr.readtext(bits, allowlist = '0123456789.')
        if not result:
            return False
        price = ''
        for r in result:
            price += r[1]
        if len(price) < 3:
            return False
        if '.' not in price:
            price = price[0 : -2] + '.' + price[-2 : ]
        rs['price'] = float(price)
        
        # zhang die & zhang fu
        rect[0] = rect[2]
        rect[2] = img.width
        zdzfImg = img.crop(tuple(rect))
        result2 = self.wbOcr.match(zdzfImg)
        if not result2:
            return False
        ma = re.match(r'([-+]\d+\.\d{2})([-+]\d+\.\d{2})%', result2)
        if not ma:
            return False
        rs['zd'] = float(ma.group(1))
        rs['zf'] = float(ma.group(2))
        return True

    def parseWeiBi(self, wbImg, rs):
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
    
    def findStockTitleHwnd(self, parentWnd, after):
        if not parentWnd:
            return
        while True:
            hwnd = win32gui.FindWindowEx(parentWnd, after, None, None)
            if not hwnd:
                break
            cl = win32gui.GetClassName(hwnd)
            if cl == 'stock_title_page':
                self.titleHwnds.add(hwnd)
            else:
                self.findStockTitleHwnd(hwnd, None)
            after = hwnd

    def getCurStockTitleHwnd(self, thsMainWin):
        rs = list(self.titleHwnds)
        for hwnd in rs:
            if not win32gui.IsWindow(hwnd):
                self.titleHwnds.remove(hwnd)
                continue
            if win32gui.IsWindowVisible(hwnd):
                return hwnd
        self.findStockTitleHwnd(thsMainWin, None)
        for hwnd in self.titleHwnds:
            if win32gui.IsWindowVisible(hwnd):
                return hwnd
        return None

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
                break
            elif gn >= MAX_PIX:
                rs[name + '_sign'] = False
                break

    def runOcr_InHomePage(self, thsMainWin):
        rs = {}
        try:
            hwnd = self.getCurStockTitleHwnd(thsMainWin)
            imgs = self.dump_InHomePage(hwnd)
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
        rs = wb.runOcr_InHomePage(ths.mainHwnd)
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
    #test_wb_main1()
    #test_zs_main2()
    s = ThsZhangShuOcrUtils()
    s.start()
    time.sleep(100)