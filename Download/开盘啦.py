import re, peewee as pw
import time, os, platform, sys
from PIL import Image as PIL_Image
import win32gui, win32con , win32api, win32ui # pip install pywin32
import requests, json, hashlib, random, easyocr
import pyautogui

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm, tck_orm
from Download import henxin

hx = henxin.HexinUrl()

TMP_FILE = 'D:/_kpl_.bmp'
KPL_OCR_FILE = 'D:/kpl-ocr.txt'

# 开盘啦截图
class KPL_Image:
    startY = -1

    def __init__(self, imgPIL):
        self.imgPIL : PIL_Image = imgPIL
        self.pixs = imgPIL.load()
        #self.pixs = list(self.imgPIL.getdata())
        self.rowsRect = [] # array of (left, top, right, bottom)
        self.width = self.imgPIL.width
        self.height = self.imgPIL.height

    def getPixel(self, x, y):
        #pos = y * self.imgPIL.width + x
        #pix = self.pixs[pos]
        pix = self.pixs[x, y]
        v = (pix[0] << 16) | (pix[1] << 8) | pix[2]
        return v

    def setPixel(self, x, y, color):
        r, g, b = (color >> 16) & 0xff, (color >> 8) & 0xff, color & 0xff
        self.pixs[x, y] = (r, g, b)

    def drawBox(self, rect, color):
        for x in range(rect[0], rect[2]):
            self.setPixel(x, rect[1], color)
        for x in range(rect[0], rect[2]):
            self.setPixel(x, rect[3] - 1, color)
        for y in range(rect[1], rect[3]):
            self.setPixel(rect[0], y, color)
        for y in range(rect[1], rect[3]):
            self.setPixel(rect[2] - 1, y, color)

    def fillBox(self, rect, color):
        for x in range(rect[0], rect[2]):
            for y in range(rect[1], rect[3]):
                self.setPixel(x, y, color)

    # colors = []
    # return y, or -1
    def getRowOfColors(self, sx, ex, sy, ey, colors):
        ey = min(ey, self.height) - len(colors)
        ey = max(ey, sy)
        for i in range(sy, ey):
            rc = False
            for j, color in enumerate(colors):
                rc = self.rowColorIs(sx, ex, i + j, color)
                if not rc:
                    break
            if rc:
                return i
        return -1

    # colors = []
    # return x, or -1
    def getColOfColors(self, sx, ex, sy, ey, colors):
        ex = min(ex, self.width) - len(colors)
        ex = max(sx, ex)
        for i in range(sx, ex):
            rc = False
            for j, color in enumerate(colors):
                rc = self.colColorIs(sy, ey, i + j, color)
                if not rc:
                    break
            if rc:
                return i
        return -1

    def rowColorIs(self, sx, ex, y, color):
        for x in range(sx, min(ex, self.imgPIL.width)):
            if self.getPixel(x, y) != color:
                return False
        return True
    
    # [sy, ey)
    def colColorIs(self, sy, ey, x, color):
        for y in range(sy, min(ey, self.imgPIL.height)):
            ncolor = self.getPixel(x, y)
            if ncolor != color:
                return False
        return True

    def splitRows(self, MIN_ROW_HEIGHT = 50):
        startY = self.getRowOfColors(140, 160, 0, self.height, [0xf3f3f3, 0xf3f3f3, 0xf3f3f3])
        if startY < 0:
            raise Exception('KPL_Image.splitRows not find startY 1')
        self.findRectNotExistsColor2((140, startY, 160, startY + 50), (20, 1), 0xf3f3f3)
        if startY < 0:
            raise Exception('KPL_Image.splitRows not find startY 2')
        startY += 2
        y = startY
        while y < self.height:
            pix0 = self.getPixel(0, y)
            if pix0 == 0xffffff:
                y += 1
                continue
            rowRect = [0, startY, self.width, y]
            startY = y + 1
            if rowRect[3] - rowRect[1] >= MIN_ROW_HEIGHT:
                self.rowsRect.append(rowRect)
                #print(rowRect, rowRect[3] - rowRect[1])
            y += 1

    def checkFinish(self):
        if not self.rowsRect:
            return False
        lastRect = self.rowsRect[-1]
        lastY = lastRect[3] + 5
        if self.height - lastY < 35:
            return False
        white = self.rectIsColor((5, lastY, 140, self.height - 5), 0xffffff)
        return white
    
    def copyImage(self, rect):
        img = self.imgPIL.crop(rect)
        return img

    # return 0 ~ 100
    # img1, img2 is Image object
    def similar(self, rect, img2, rect2):
        img1 = self
        sx1, sy1, ex1, ey1 = rect
        sx2, sy2, ex2, ey2 = rect2
        tW, tH = ex1 - sx1, ey1 - sy1
        oW, oH = ex2 - sx2, ey2 - sy2
        if tW != oW or tH != oH:
            return 0 # size not equal
        matchNum = 0
        for x in range(tW):
            for y in range(tH):
                if img1.getPixel(x + sx1, y + sy1) == img2.getPixel(x + sx2, y + sy2):
                    matchNum += 1
        val = matchNum * 100 / (tW * tH)
        return val

    def rectIsColor(self, rect, color):
        for x in range(rect[0], rect[2], 1):
            for y in range(rect[1], rect[3], 1):
                if self.getPixel(x, y) != color:
                    return False
        return True
    
    def rectExistsColor(self, rect, color):
        for x in range(rect[0], rect[2], 1):
            for y in range(rect[1], rect[3], 1):
                if self.getPixel(x, y) == color:
                    return True
        return False

    # :return (sx, sy, ex, ey), not find return None
    def findRectIsColor(self, srcRect, size, color):
        w, h = size
        for x in range(srcRect[0], srcRect[2]- w, 1):
            for y in range(srcRect[1], srcRect[3] - h, 1):
                if self.rectIsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
    
    #横向优先查找
    def findRectNotExistsColor(self, srcRect, size, color):
        w, h = size
        for x in range(srcRect[0], srcRect[2]- w, 1):
            for y in range(srcRect[1], srcRect[3] - h, 1):
                if not self.rectExistsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
    
    #竖向优先查找
    def findRectNotExistsColor2(self, srcRect, size, color):
        w, h = size
        for y in range(srcRect[1], srcRect[3] - h, 1):
            for x in range(srcRect[0], srcRect[2]- w, 1):
                if not self.rectExistsColor((x, y, x + w, y + h), color):
                    return (x, y, x + w, y + h)
        return None
    
    def replaceColor(self, rect, srcColor, destColor):
        for x in range(rect[0], rect[2]):
            for y in range(rect[1], rect[3]):
                if self.getPixel(x, y) == srcColor:
                    self.setPixel(x, y, destColor)
    
    # 二值化图片
    def toBinaryValImage(self):
        WHITE_COLOR = 0xffffff
        for x in range(self.width):
            for y in range(self.height):
                color = self.getPixel(x, y)
                color = int(0.299 * (color >> 16) + 0.578 * ((color >> 8) & 0xff) + 0.114 * (color & 0xff))
                if color < 200:
                    color = 0
                else:
                    color = 0xffffff
                self.setPixel(x, y, color)

    @staticmethod
    def dump(hwnd):
        dc = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        rect = win32gui.GetClientRect(hwnd)
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)
        srcSize = (w, h)
        srcPos = (0, 0)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bits = saveBitMap.GetBitmapBits(True)
        img_PIL = PIL_Image.frombuffer('RGB',(w, h), bits, 'raw', 'BGRX', 0, 1) # bmpinfo['bmWidth']
        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return img_PIL

class KPL_RowImage(KPL_Image):
    # 股票名称、涨停时间、状态、涨停原因
    COLS_INFO = [(0, 150), (140, 240), (270, 380), (400, 515)]
    COL_NAME = COLS_INFO[0]

    def __init__(self, imgPIL: PIL_Image):
        super().__init__(imgPIL)
        self.model = {}
        self.nameRect = None
        self.codeRect = None

    def isLastEmptyRow(self):
        # last row may be white name
        white = self.rectIsColor((5, 5, self.COL_NAME[1], self.height - 5), 0xffffff)
        return white
    
    def parse(self):
        self.splitColName()

    def skipRowSpace(self, rect, sy, down):
        while sy < rect[3] if down else sy >= rect[1]:
            if not self.rowColorIs(rect[0], rect[2], sy, 0xffffff):
                return sy
            sy += 1 if down else -1
        return -1

    def skipColSpace(self, rect, sx):
        while sx < rect[2]:
            if not self.colColorIs(rect[1], rect[3], sx, 0xffffff):
                return sx
            sx += 1
        return -1

    def getMaxColorRate(self, rect, x, y):
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        if w <= 2 or h <= 2:
            return 0
        color = self.getPixel(x, y)
        r, g, b = (color >> 16) & 0xff, (color >> 8) & 0xff, color & 0xff
        if r == 0 or g == 0 or b == 0:
            return 0
        br = max(r / g, r / b)
        return br

    def parseTag(self, rect):
        w, h = rect[2] - rect[0], rect[3] - rect[1]
        br1 = self.getMaxColorRate(rect, rect[0], rect[1] + h // 2)
        br2 = self.getMaxColorRate(rect, rect[2] - 1, rect[1] + h // 2)
        br3 = self.getMaxColorRate(rect, rect[0] + w // 2, rect[1])
        br4 = self.getMaxColorRate(rect, rect[0] + w // 2, rect[3] - 1)
        br = max(br1, br2, br3, br4)
        if br < 2:
            return
        self.fillBox(rect, 0xffffff)
        if br > 3.5:
            if (w >= h - 1 and w <= h + 1):
                self.model['R'] = True
                self.fillBox(rect, 0xffffff)
            else:
                self.model['HF'] = True
                self.fillBox(rect, 0xffffff)

    def splitColName(self):
        y = 20
        while y < self.height:
            if self.rowColorIs(*self.COL_NAME, y, 0xffffff):
                break
            y += 1
        self.nameRect = [self.COL_NAME[0], 0, self.COL_NAME[1], y]
        self.codeRect = [self.COL_NAME[0], y + 1, self.COL_NAME[1], self.height]
        nameItemsRect = self.splitVertical(self.nameRect)
        codeItemRect = self.splitVertical(self.codeRect)
        for i in range(0, len(nameItemsRect)):
            self.parseTag(nameItemsRect[i])
        #for i in range(0, len(codeItemRect)):
        #    self.parseTag(codeItemRect[i])
        

    def splitVertical(self, rect):
        items = []
        x = rect[0]
        while x < rect[2]:
            x = self.skipColSpace(rect, x)
            if x < 0:
                break
            bx = x
            while not self.colColorIs(rect[1], rect[3], x, 0xffffff):
                x += 1
            ex = x
            if bx == ex:
                continue
            itrect = [bx, rect[1], ex, rect[3]]
            self.trimHorizontal(itrect)
            items.append(itrect)
        return items

    def trimHorizontal(self, rect):
        y = self.skipRowSpace(rect, rect[1], True)
        if y >= 0:
            rect[1] = y
        y = self.skipRowSpace(rect, rect[3] - 1, False)
        if y >= 0:
            rect[3] = y + 1
    
    def caclColorNumber(self, rect, color):
        sx, sy, ex, ey = rect
        nb = 0
        for x in range(sx, ex):
            for y in range(sy, ey):
                if self.getPixel(x, y) == color:
                    nb += 1
        return nb

class OCRUtil:
    def __init__(self, ocr):
        self.ocr = ocr
        self.xiaoWnds = {}
        self.winSize = None
        self.kimg = None
        self.curDay = ''
        self.headLineY = -1
        self.leftArrow = None
        self.rightArrow = None
        self.dayRect = None
        self.models = []
        self.hotVal = None

    def isWinSizeChanged(self):
        hwnd = self.xiaoWnds['contentWin']
        rc = win32gui.GetClientRect(hwnd)
        w, h = rc[2], rc[3]
        if not self.winSize or self.winSize[0] != w or self.winSize[1] != h:
            self.winSize = (w, h)
            return True
        return False

    def checkWindowChanged(self):
        if not self.isWinSizeChanged():
            return
        self.calcHeadLineY()
        self.calcLeftRightArrow()
        self.calcCurDayRect()

    # 涨停
    def updateZT_Image(self):
        hwnd = self.xiaoWnds['contentWin']
        pilImage = KPL_Image.dump(hwnd)
        self.kimg = KPL_Image(pilImage)
        self.checkWindowChanged()
        self.readCurDay()
        self.kimg.splitRows()
        finish = False
        for r in self.kimg.rowsRect:
            nimg = self.kimg.copyImage(r)
            rowImg = KPL_RowImage(nimg)
            if rowImg.isLastEmptyRow():
                finish = True
                break
            model = self.parseRow(rowImg)
            model['day'] = self.curDay
            self.addModel(model)
        self.compareModels()
        if not finish:
            finish = self.kimg.checkFinish()
        return finish

    # 数据分析 (热度值)
    def updateSJFX_Image(self):
        hwnd = self.xiaoWnds['contentWin']
        pilImage = KPL_Image.dump(hwnd)
        self.kimg = KPL_Image(pilImage)
        self.checkWindowChanged()
        self.readCurDay()
        ey = self.kimg.getRowOfColors(10, 60, self.dayRect[1], self.dayRect[1] + 200, [0xE93030])
        if ey < 0:
            raise Exception('[OCRUtil.updateSJFX_Image] not find ey')
        ey += 3
        HOT_WIDTH = 125
        HOT_HEIGHT = 65
        w = win32gui.GetClientRect(hwnd)[2]
        hotRect = [w - HOT_WIDTH, ey, w - 5, ey + HOT_HEIGHT]
        hotImg = self.kimg.copyImage(hotRect)
        hotImg.save(TMP_FILE)
        result = self.ocr.readtext(TMP_FILE)
        self.hotVal = result[0][1]
        print(self.curDay, self.hotVal, sep='\t')
        # check day
        if not re.match(r'\d{4}-\d{2}-\d{2}', self.curDay):
            print(' [updateSJFX_Image] error day')
            return False
        return True

    def compareModels(self):
        for model in self.models:
            if '_success' not in model:
                rs = self.checkModel(model)
                model['_success'] = rs
        for i in range(0, len(self.models) - 1):
            for j in range(i + 1, len(self.models), 1):
                if self.isSameModel(self.models[i], self.models[j]):
                    self.models[j]['_exists'] = True
        for i in range(len(self.models) - 1, -1, -1):
            if '_exists' in self.models[i]:
                self.models.pop(i)

    def writeModels(self, file):
        def fmtName(name):
            apd = 0
            for n in name:
                apd = apd + (1 if ord(n) < 255 else 2)
            return name + ' ' * (8 - apd)
        for model in self.models:
            info = f"{model['day']}\t{fmtName(model['name'])}\t{model['code']}\t{model['ztTime']}\t{model['status']}\t{model['ztReason']}\t{model['ztNum']}"
            print(info)
            if '新上市' in model['status'] or model['ztReason'] == '无':
                continue
            if file:
                file.write(info + '\n')
            if not model['_success']:
                ex = ''
                if '_exception' in model: ex = model['_exception']
                print('\tException ' + ex)
                if file:
                    file.write( '\tException '  + ex + '\n')
            if file:
                file.flush()
        print('sum =', len(self.models))
        if file:
            file.flush()
    
    def clearModels(self):
        self.models = []

    def printeModels(self):
        self.writeModels(None)

    def isSameModel(self, model1, model2):
        return (model1['name'] == model2['name']) and (model1['code'] == model2['code']) and (model1['day'] == model2['day'])

    def addModel(self, model):
        for m in self.models:
            if self.isSameModel(model, m):
                return
        self.models.append(model)

    def parseRow(self, img : KPL_RowImage):
        img.parse()
        codePilImg = img.copyImage(img.codeRect)
        code = self.parseCodeRect(codePilImg)
        img.fillBox(img.codeRect, 0xffffff)
        img.replaceColor([img.width // 2, 0, img.width, img.height], 0xE7F4FF, 0xffffff)
        model = self.parseRowImage(img)
        model['code'] = code
        #print('[OCRUtil.parseRow]', model)
        info = f"{model['name']}\t{model['code']}\t{model['ztTime']}\t{model['status']}\t{model['ztReason']}\t{model['ztNum']}"
        print('[OCRUtil.parseRow]', info)
        return model
    
    def parseCodeRect(self, pilImg):
        pilImg.save(TMP_FILE)
        result = self.ocr.readtext(TMP_FILE)
        if len(result) < 1:
            raise Exception('[parseCodeRect] fail :', result)
        code = result[0][1][0 : 6]
        if code and code[0] == '5':
            code = '6' + code[ 1 : ]
        return code
    
    def adjustZtReason(self, rz):
        if (rz[-1] == '1' or rz[-1] == '/') and (')' not in rz):
            rz = rz[0 : -1] + ')'
        rz = rz.replace('」', ')')
        rz = rz.replace('}', ')')
        rz = rz.replace(']', ')')
        rz = rz.replace('[', '(')
        rz = rz.replace('{', '(')
        rz = rz.replace('霎', '零')
        rz = rz.replace('窭', '零')
        rz = rz.replace('井', '并')
        rz = rz.replace('娈', '变')
        rz = rz.replace('机器入', '机器人')
        rz = rz.replace('-', '一')
        rz = rz.replace('~', '一')
        if rz.find('季报') == 0:
            rz = '一' + rz
        if '(' not in rz and rz != '无':
            for i in range(len(rz) - 1, -1, -1):
                if rz[i] != ')' and  not (rz[i] >= '0' and rz[i] <= '9'):
                    if rz == 0:
                        rz = rz + '()'
                    else:
                        rz = rz[0 : i + 1] + '(' + rz[i + 1 : ]
                    break
        if rz != '无' and rz[-1] != ')':
            rz += ')'
        if 'AR' in rz and 'VR' in rz:
            rz = 'AR/VR/MR' + rz[rz.index('(') : ]
        if 'DRG' in rz and 'DIP' in rz:
            rz = 'DRG/DIP' + rz[rz.index('(') : ]
        if 'CPO' in rz and 'MPO' in rz:
            rz = 'CPO/MPO' + rz[rz.index('(') : ]
        # check num
        num = ''
        if '(' in rz and ')' in rz:
            sx = rz.index('(')
            ex = rz.index(')')
            for i in range(sx + 1, ex, 1):
                if rz[i] >= '0' and rz[i] <= '9':
                    num += rz[i]
            rz = rz[0 : sx]
        return rz, num

    def parseRowImage(self, img):
        #img.imgPIL.show()
        img.imgPIL.save(TMP_FILE)
        result = self.ocr.readtext(TMP_FILE)
        if len(result) < 4:
            raise Exception('[parseRow] fail :', result)
        img.model['name'] = result[0][1]
        img.model['ztTime'] = result[1][1]
        img.model['ztTime'] = img.model['ztTime'].replace('.', ':')
        img.model['status'] = result[2][1]
        rz = result[3][1]
        rz, num = self.adjustZtReason(rz)
        img.model['ztReason'] = rz
        img.model['ztNum'] = num
        return img.model

    def checkModel(self, model):
        mc = model['code']
        obj = ths_orm.THS_Newest.get_or_none(ths_orm.THS_Newest.code == mc)
        if obj and obj.name == model['name']:
            return True
        if '-' in model['name']:
            model['name'] = model['name'].replace('-', '一')
        obj = ths_orm.THS_Newest.get_or_none(ths_orm.THS_Newest.name == model['name'])
        if obj:
            model['code'] = obj.code
            #model['_exception'] = f' Find code {mc}  -> {obj.code} ? '
            return True
        if len(mc) != 6:
            return False
        for c in mc:
            if c < '0' or c > '9':
                return False
        try:
            obj = hx.loadUrlData(hx.getTodayKLineUrl(mc))
            name = obj['name']
        except Exception as e:
            model['_exception'] = ' Net check ' + str(e)
            return False
        if model['name'] == name:
            return True
        if model['name'].replace('酉', '西') == name:
            model['name'] = name
            return True
        if model['name'].replace('曰', '日') == name:
            model['name'] = name
            return True
        if model['name'].replace('壬', '王') == name:
            model['name'] = name
            return True
        if model['name'].replace('娈', '变') == name:
            model['name'] = name
            return True
        if model['name'].replace('夭', '天') == name:
            model['name'] = name
            return True
        model['_exception'] = ' Maybe is ' + name + '? '
        return False

    def calcHeadLineY(self):
        #color = self.kimg.getPixel(self.kimg.width //2, 80)
        #print(f'{color:x}')
        sy = self.kimg.getRowOfColors(self.kimg.width // 2, self.kimg.width // 2 + 100, 1, 200, [0xffffff])
        if sy < 0:
            raise Exception('[calcHeadLineY] fail not find current day line')
        self.headLineY = sy + 3

    def calcCurDayRect(self):
        sy = self.headLineY
        sx = self.leftArrow[2] + 10
        ey = self.kimg.getRowOfColors(sx, sx + 50, sy, sy + 100, [0xf8f8f8])
        if ey < 0:
            ey = sy + 75
        ex = self.rightArrow[0] - 10 if self.rightArrow else self.kimg.width
        rect = [sx, sy, ex, ey]
        upLineRect = self.kimg.findRectNotExistsColor2(rect, (50, 1), 0xffffff)
        rect2= [upLineRect[0], upLineRect[1] + 2, ex, ey]
        downLineRect = self.kimg.findRectNotExistsColor2(rect2, (50, 1), 0xffffff)
        rect = [upLineRect[0] + 2, upLineRect[1] + 2, ex, downLineRect[3] - 2]
        rectx = rect[ : ]
        rectx[0] += 70
        rightLineRect = self.kimg.findRectIsColor(rectx, (4, rect[3] - rect[1] - 1), 0xffffff)
        rect[2] = rightLineRect[2]
        self.dayRect = rect
    
    def readCurDay(self):
        #self.kimg.drawBox(rect, 0xff0000)
        #self.kimg.imgPIL.show()
        dimg = self.kimg.copyImage(self.dayRect)
        dimg.save(TMP_FILE)
        rs = self.ocr.readtext(TMP_FILE)
        txt = ''
        for r in rs:
            txt += r[1]
        if len(txt) == 10:
            self.curDay = txt
            print('[OCRUtil.calcCurrentDay] curDay=', txt)
        else:
            self.curDay = txt
            print('[OCRUtil.calcCurrentDay] curDay=', txt, ' error day')
            #raise Exception('[OCRUtil.calcCurrentDay] not find current day ', txt)

    def calcLeftRightArrow(self):
        sy = self.headLineY
        sx = self.kimg.width // 2 - 30
        rect = [sx, sy, self.kimg.width, sy + 100]
        #self.kimg.drawBox(rect, 0xff0000)
        #self.kimg.imgPIL.show()
        self.leftArrow = self.kimg.findRectIsColor(rect, (5, 5), 0xDADEE5)
        if not self.leftArrow:
            raise Exception('[calcLeftRightArrow] not find leftArrow of day')
        rect[0] = self.leftArrow[0] + 50
        self.rightArrow = self.kimg.findRectIsColor(rect, (10, 10), 0xDADEE5)
        #self.kimg.fillBox(self.leftArrow, 0xff0000)
        #self.kimg.fillBox(self.rightArrow, 0xff0000)
        #self.kimg.imgPIL.show()

    def initXiaoYaoWnd(self):
        xiaoYaoWnd = win32gui.FindWindow('Qt5QWindowIcon', '逍遥模拟器')
        if not xiaoYaoWnd:
            print('Not find 逍遥模拟器')
            return False
        print(f'逍遥模拟器 top hwnd=0x{xiaoYaoWnd :x}')
        self.xiaoWnds['topWnd'] = xiaoYaoWnd
        hwnd = win32gui.FindWindowEx(xiaoYaoWnd, None, 'Qt5QWindowIcon', 'MainWindowWindow')
        self.xiaoWnds['mainWnd'] = hwnd
        hwnd = win32gui.FindWindowEx(hwnd, None, 'Qt5QWindowIcon', 'CenterWidgetWindow')
        self.xiaoWnds['centerWnd'] = hwnd
        hwnd = win32gui.FindWindowEx(hwnd, None, 'Qt5QWindowIcon', 'RenderWindowWindow')
        self.xiaoWnds['renderWnd'] = hwnd
        hwnd = win32gui.FindWindowEx(hwnd, None, 'subWin', 'sub')
        self.xiaoWnds['subWin'] = hwnd
        hwnd = win32gui.FindWindowEx(hwnd, None, 'subWin', 'sub')
        print(f'逍遥模拟器 contentWin=0x{hwnd :x}')
        self.xiaoWnds['contentWin'] = hwnd
        return True

    def checkXiaoYaoWindows(self):
        cw = self.xiaoWnds.get('contentWin', None)
        if not cw or not win32gui.IsWindow(cw):
            return self.initXiaoYaoWnd()
        return True

class MainTools:
    def __init__(self, util) -> None:
        self.util = util

    def loadZT_File(self):
        file = open(KPL_OCR_FILE, encoding='gbk')
        lineNo = 0
        while True:
            lineNo += 1
            line = file.readline().strip()
            if not line:
                break
            its = line.split('\t')
            for i in range(len(its)): its[i] = its[i].strip()
            if len(its) < 7:
                print(f'Line {lineNo} error: ', its)
                break
            day, name, code, ztTime, status, ztReason, ztNum, *_ = its
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', day):
                print(f'Line {lineNo} error: ', its)
                break
            self.save_KPL_ZT(day, code, name, ztTime, status, ztReason, ztNum)

    def save_KPL_ZT(self, day, code, name, ztTime, status, ztReason, ztNum):
        count = tck_orm.KPL_ZT.select(pw.fn.count(tck_orm.KPL_ZT.code)).where(tck_orm.KPL_ZT.code == code, tck_orm.KPL_ZT.day == day)
        #print(count.sql())
        count = count.scalar()
        if not count:
            tck_orm.KPL_ZT.create(name=name, code=code, ztNum=ztNum, ztTime=ztTime, status=status, ztReason=ztReason, day=day)
            print('Save success: ', day, name, code)
        else:
            print('重复项：', day, code, name, ztTime, status, ztReason, ztNum)

    def runOpt(self, opt):
        if opt == 'next-zt-page':
            if self.util.checkXiaoYaoWindows():
                finish = self.util.updateZT_Image()
                #self.util.printeModels()
                print('next...end')
                finish = 'Finish' if finish else False
                return finish
            else:
                print('Xiao Yao window not find')
                return True
        elif opt == 'save-zt':
            file = open(KPL_OCR_FILE, 'a')
            self.util.writeModels(file)
            self.util.clearModels()
            file.close()
            print('save to file success')
        elif opt == 'load-zt-file' or opt == 'l':
            self.loadZT_File()
        elif opt == 'open-zt-file' or opt == 'o':
            notepad = r'C:\Program Files\Notepad++\notepad++.exe'
            win32api.ShellExecute(None, 'open', notepad, KPL_OCR_FILE, None, win32con.SW_SHOW)
        elif opt == 'auto-zt-one' or opt == 'a':
            self.autoLoadOneZT_Page()
        elif opt == 'auto-zt-all':
            self.autoMain_ZT()
        elif opt == 'scqx' or opt == 'x':
            self.autoMain_SJFX(False)
        elif opt == 'auto-scqx':
            self.autoMain_SJFX(True)
        return True

    def autoLoadOneZT_Page(self):
        while True:
            tg = self.runOpt('next-zt-page')
            if tg == 'Finish':
                self.runOpt('save-zt')
                break
            else:
                time.sleep(3)
                self.scrollNextPage()
                time.sleep(3)

    def main(self):
        print('定位到[市场情绪->股票列表->涨停原因排序] ')
        print('定位到[市场情绪->数据分析] ')
        # 'auto-zt-all = auto load all zt pages \n\t' + \
        # 'next-zt-page = next page down  \n\t' + \
        # 'auto-scqx = auto load scqx 定位到[市场情绪->数据分析]\n\t' + \
        tip = 'select options: \n\t' + \
                '[a] auto-zt-one = auto load one zt page  \n\t' + \
                '[s] save-zt = save to file\n\t' + \
                '[l] load-zt-file = load zt data file, save to database\n\t' + \
                '[o] open-zt-file = use notepad++ open zt data file\n\t' + \
                '[x] scqx = load one scqx 定位到[市场情绪->数据分析]\n\t' + \
                'help = print help'
        print(tip)
        while True:
            opt = input('input select: ').strip()
            self.runOpt(opt)
            if opt == 'help':
                print(tip)

    def clickLeftArrow(self):
        rect = self.util.leftArrow
        hwnd = self.util.xiaoWnds['topWnd']
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        hwnd = self.util.xiaoWnds['contentWin']
        rr = win32gui.GetWindowRect(hwnd)
        x = (rect[0] + rect[2]) // 2 + rr[0]
        y = (rect[1] + rect[3]) // 2 + rr[1]
        pyautogui.click(x, y)

    def scrollNextPage(self):
        hwnd = self.util.xiaoWnds['topWnd']
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        hwnd = self.util.xiaoWnds['contentWin']
        rr = win32gui.GetWindowRect(hwnd)
        rect = win32gui.GetClientRect(hwnd)
        x = rect[2] // 2 + rr[0]
        y = rect[3] - 40 + rr[1]
        lastY =  330 + rr[1] #KPL_Image.startY
        pyautogui.moveTo(x, y)
        time.sleep(1)
        pyautogui.dragTo(x, lastY, duration=2)

    def autoMain_ZT(self):
        while True:
            tg = self.runOpt('next-zt-page')
            if tg == 'Finish':
                self.runOpt('save-zt')
                self.clickLeftArrow()
                time.sleep(3)
            else:
                time.sleep(3)
                self.scrollNextPage()
                time.sleep(3)

    def autoMain_SJFX(self, loop):
        print('定位到[市场情绪->数据分析] ')
        while True:
            f = self.util.updateSJFX_Image()
            if not f:
                break
            self.save_KPL_SCQX(self.util.curDay, self.util.hotVal)
            if not loop:
                break
            self.clickLeftArrow()
            time.sleep(3)

    def save_KPL_SCQX(self, day, zhqd):
        obj = tck_orm.KPL_SCQX.get_or_none(tck_orm.KPL_SCQX.day == day)
        if obj:
            obj.zhqd = int(zhqd)
            obj.save()
        else:
            tck_orm.KPL_SCQX.create(day = day, zhqd = zhqd)

if __name__ == '__main__':
    ocr = easyocr.Reader(['ch_sim','en'])
    util = OCRUtil(ocr)
    tools = MainTools(util)
    util.initXiaoYaoWnd()
    tools.main()