import time, os, platform, io
from PIL import Image
import win32gui, win32con , win32api, win32ui # pip install pywin32
import easyocr

_ecor = None
def eocr():
    global _ecor
    if not _ecor:
        _ecor = easyocr.Reader(['ch_sim'], download_enabled = True ) # ch_sim  en
    return _ecor

class RGBImage:
    def __init__(self, oimg : Image) -> None:
        self.img = oimg
        self.pixs = oimg.load()

    def colColorIs(self, sy, ey, x, color):
        for y in range(sy, min(ey, self.img.height)):
            ncolor = self.pixs[x, y]
            if ncolor != color:
                return False
        return True
    
    # from (sx, sy) search a box (w, h size)
    # return x, not find return -1
    def horSearchBoxColor(self, sx, sy, w, h, color):
        if (sy + h > self.img.height) or (sx + w > self.img.width):
            return -1
        ex = max(sx, self.img.width)
        for x in range(sx, ex):
            f = True
            for s in range(w):
                if not self.colColorIs(sy, sy + h, x + s, color):
                    f = False
                    break
            if f:
                return x
        return -1

class BaseEImage:
    def __init__(self, oimg : Image):
        oimg = oimg.convert('L') # 转为灰度图
        self.bImg : Image = oimg.point(lambda v : 0 if v == 0 else 255) # 二值化图片
        #self.pixs = list(self.imgPIL.getdata())
        self.pixs = self.bImg.load()
        
    #def getPixel(self, x, y):
    #    pos = y * self.bImg.width + x
    #    return self.pixs[pos]

    def rowColorIs(self, sx, ex, y, color):
        for x in range(sx, min(ex, self.bImg.width)):
            if self.pixs[x, y] != color:
                return False
        return True
    
    def findRowColorIs(self, sx, ex, color):
        for y in range(self.bImg.width):
            if self.rowColorIs(sx, ex, y, color):
                return y
        return -1
    
    def colColorIs(self, sy, ey, x, color):
        for y in range(sy, min(ey, self.bImg.height)):
            ncolor = self.pixs[x, y]
            if ncolor != color:
                return False
        return True
    
    # from (sx, sy) search a box (w, h size)
    # return x, not find return -1
    def horSearchBoxColor(self, sx, sy, w, h, color):
        if (sy + h > self.bImg.height) or (sx + w > self.bImg.width):
            return -1
        ex = max(sx, self.bImg.width)
        for x in range(sx, ex):
            f = True
            for s in range(w):
                if not self.colColorIs(sy, sy + h, x + s, color):
                    f = False
                    break
            if f:
                return x
        return -1

    # return [startX, endX)
    def splitVerticalOne(self, startX):
        sx = ex = -1
        for x in range(startX, self.bImg.width):
            if not self.colColorIs(0, self.bImg.height, x, 0):
                sx = x
                break
        for x in range(sx, self.bImg.width):
            if self.colColorIs(0, self.bImg.height, x, 0):
                ex = x
                break
        return (sx, ex)

    def splitVertical(self):
        items = []
        sx = ex = 0
        while True:
            sx, ex = self.splitVerticalOne(ex)
            if sx < 0 or ex < 0:
                break
            items.append((sx, ex))
        return items
    
    def splitHorizontalOne(self, sx, ex):
        sy = ey = -1
        for y in range(self.bImg.height):
            if not self.rowColorIs(sx, ex, y, 0):
                sy = y
                break
        for y in range(sy, self.bImg.height):
            if self.rowColorIs(sx, ex, y, 0):
                ey = y
                break
        return (sy, ey)
    
    def caclColorNumber(self, rect, color):
        sx, sy, ex, ey = rect
        nb = 0
        for x in range(sx, ex):
            for y in range(sy, ey):
                if self.pixs[x, y] == color:
                    nb += 1
        return nb

    # return 0 ~ 100
    # img2 is EImage object
    def similar(self, rect1, img2, rect2):
        sx1, sy1, ex1, ey1 = rect1
        sx2, sy2, ex2, ey2 = rect2
        tW, tH = ex1 - sx1, ey1 - sy1
        oW, oH = ex2 - sx2, ey2 - sy2
        if tW != oW or tH != oH:
            return 0 # size not equal
        matchNum = 0
        pixs1 = self.pixs
        pixs2 = img2.bImg.load()
        for x in range(tW):
            for y in range(tH):
                if pixs1[x + sx1, y + sy1] == pixs2[x + sx2, y + sy2]:
                    matchNum += 1
        val = matchNum * 100 / (tW * tH)
        return val

    def expand(self):
        w, h = self.bImg.size
        SPACE_W = 5
        dw = 30
        items = self.splitVertical()
        for it in items:
            dw += it[1] - it[0] + SPACE_W
        destImg = Image.new('L', (dw, h), 0)

        destPixs = destImg.load()
        srcPixs = self.pixs
        sdx = 5
        for it in items:
            sx, ex = it
            sdx += SPACE_W
            for x in range(sx, ex):
                sdx += 1
                for y in range(h):
                    destPixs[sdx, y] = srcPixs[x, y]
        #destImg.save('D:/d.bmp')
        return destImg

class EImage(BaseEImage):
    def __init__(self, oimg):
        super().__init__(oimg)
        self.itemsRect = [] # array of (left, top, right, bottom)
        self.split()

    def split(self):
        items = self.splitVertical()
        rs = []
        for sx, ex in items:
            sy, ey = self.splitHorizontalOne(sx, ex)
            rect = (sx, sy, ex, ey)
            rs.append(rect)
        self.itemsRect = rs
        return rs

    # :param img is EImage object
    # :return an index, not find return -1
    def findSameAs(self, img, rect, similarVal = 100):
        for idx, rc in enumerate(self.itemsRect):
            sval = self.similar(rc, img, rect)
            if sval >= similarVal:
                return idx
        return -1

class NumberOCR:
    def __init__(self, baseName, templateDigit):
        plat = platform.node()
        bn = os.path.basename(__file__)
        p = __file__[0 : - len(bn)]
        self.templateImg = EImage(Image.open(f'{p}img/{baseName}-{plat}.bmp'))
        self.templateDigit = templateDigit

    def _matchOne(self, oimg : EImage, oRect):
        MIN_SIMILAR_VAL = 95
        idx = self.templateImg.findSameAs(oimg, oRect, MIN_SIMILAR_VAL)
        if idx >= 0:
            return self.templateDigit[idx]
        return '#'

    def match(self, oimg : Image):
        rimg = EImage(oimg)
        rs = ''
        for rect in rimg.itemsRect:
            rs += self._matchOne(rimg, rect)
        return ''.join(rs)

class BuildTemplateImage:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.destImg = EImage(Image.new('1', size=(200, 20)))

    def copy(self, eimg : EImage, rect):
        targetImg : Image = self.destImg.bImg
        box = eimg.bImg.crop(rect)
        #box.show()
        dx = dy = 4
        if len(self.destImg.itemsRect) > 0:
            lastItem = self.destImg.itemsRect[-1]
            dx += lastItem[2]
        targetImg.paste(box, (dx, dy))
        self.destImg = EImage(targetImg)
        targetImg.show()
        pass

    def dump(self):
        if not win32gui.IsWindowVisible(self.hwnd):
            return None
        dc = win32gui.GetWindowDC(self.hwnd)
        #mdc = win32gui.CreateCompatibleDC(dc)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, 50, 20) # image size 50 x 20
        saveDC.SelectObject(saveBitMap)

        srcSize = (30, 17)
        srcPos = (14, 38)
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img_PIL = Image.frombuffer('RGB',(bmpinfo['bmWidth'], 17), bmpstr, 'raw', 'BGRX', 0, 1)
        #img_PIL.show()
        #print(img_PIL.getcolors(), img_PIL.mode)
        eimg = EImage(img_PIL)
        for rect in eimg.itemsRect:
            sv = self.destImg.findSameAs(eimg, rect, 100)
            if sv < 0:
                self.copy(eimg, rect)

        # destory
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, dc)

    def saveTemplate(self):
        while True:
            self.dump()
            time.sleep(0.5)
            if len(self.destImg.itemsRect) >= 10:
                break
        self.destImg.bImg.save(f'[c] ocr-template-{platform.node()}.bmp')

class DumpWindowUtils:

    # return  PIL.Image
    def dumpImg(self, hwnd, rect):
        if (not hwnd) or (not win32gui.IsWindow(hwnd)) or (not win32gui.IsWindowVisible(hwnd)):
            return None
        dc = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(dc)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        srcSize = rect[2] - rect[0], rect[3] - rect[1]

        saveBitMap.CreateCompatibleBitmap(mfcDC, *srcSize) # image size W x H
        saveDC.SelectObject(saveBitMap)
        #hbr = win32ui.CreateBrush()
        #hbr.CreateSolidBrush(0x000000)
        #saveDC.FillRect((0, 0, W, H), hbr)
        
        srcPos = rect[0], rect[1]
        saveDC.BitBlt((0, 0), srcSize, mfcDC, srcPos, win32con.SRCCOPY)
        #bmpinfo = saveBitMap.GetInfo()
        #imgSize = (bmpinfo['bmWidth'], bmpinfo['bmHeight'])
        bits = saveBitMap.GetBitmapBits(True)
        imgFull = Image.frombuffer('RGB',srcSize, bits, 'raw', 'BGRX', 0, 1)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, dc)
        return imgFull

    def imgToBmpBytes(self, img):
        bmpBytes = io.BytesIO()
        img.save(bmpBytes, format = 'bmp')
        bits = bmpBytes.getvalue()
        return bits


if __name__ == '__main__':
    print(platform.node())
    # 同花顺分析图中的日期窗口
    THS_SELECT_DAY_HWND = 0X1109C
    dtm = BuildTemplateImage(THS_SELECT_DAY_HWND)
    dtm.saveTemplate()