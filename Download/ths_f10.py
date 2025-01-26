import os, json, sys
from bs4 import BeautifulSoup
import pyautogui as pa
import time, re


sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from Download import fiddler
from orm import ths_orm

BASE_PATH = 'D:/thsdata/f10/'

if not os.path.exists(BASE_PATH):
    os.makedirs(BASE_PATH)

# str to float, strip not numbers
def toFloat(s):
    s = str(s)
    try:
        return float(s)
    except:
        pass
    ss = ''
    for i in s:
        if (i >= '0' and i <= '9') or (i == '.'):
            ss += i
    if ss == '':
        return 0
    return float(ss)

# str to int, strip not numbers
def toInt(s):
    s = str(s)
    try:
        return int(s)
    except:
        pass
    ss = ''
    for i in s:
        if (i >= '0' and i <= '9') or (i == '.'):
            ss += i
    if ss == '':
        return 0
    return int(ss)

#最新动态
class LoadNewest:
    def saveDB(self, objx):
        obj = ths_orm.THS_Newest.get_or_none(code = objx['code'])
        if (obj):
            obj.update(**objx)
            obj.save()
        else:
            ths_orm.THS_Newest.create(**objx)

    def load(self, code):
        f = open(BASE_PATH + code + '-最新动态.html', 'r', encoding= 'gbk')
        txt = f.read()
        f.close()
        soup = BeautifulSoup(txt, 'html5lib')
        title = soup.title.string
        idx = title.index('(')
        name = title[0 : idx]
        obj = {'code' : code, 'name': name}

        tag = '总市值：'
        pos = txt.index(tag) + len(tag)
        zszTxt = txt[pos : pos + 100]
        if 'stockzsz' not in zszTxt:
            print('Load 最新动态: Not find stockzsz')
            raise Exception()
        pos = zszTxt.index('stockzsz') + len('stockzsz')
        zszTxt = zszTxt[pos : pos + 20]
        zsz = toInt(zszTxt)
        obj['zsz'] = zsz

        idx = txt.find('公司亮点：')
        if idx < 0:
            print('Load 最新动态: Not find 公司亮点')
            raise Exception()
        idx = txt.find('title="', idx) + 7
        idx2 = txt.find('"', idx)
        liangDian = txt[idx : idx2]
        obj['gsld'] = liangDian

        tag = "财务分析："
        idx = txt.find(tag)
        if idx > 0:
            bidx = txt.find('<div', idx)
            eidx = txt.find('</div>', bidx)
            cwfxTxt = txt[bidx : eidx + 6]
            soup = BeautifulSoup(cwfxTxt, 'html5lib')
            cwfx = ''
            for ch in soup.select('a'):
                cwfx += ch.contents[0] + ';'
            obj['cwfx'] = cwfx
        print('Load 最新动态：', obj)
        self.saveDB(obj)

#前十大流通股东
class LoadTHS_Top10_LTGD:
    def saveDB(self, objx):
        obj = ths_orm.THS_Top10_LTGD.get_or_none(code = objx['code'], day = objx['day'])
        if (obj):
            obj.update(**objx)
            obj.save()
        else:
            ths_orm.THS_Top10_LTGD.create(**objx)

    def load(self, code):
        f = open(BASE_PATH + code + '-股东研究.html', 'r', encoding= 'gbk')
        txt = f.read()
        f.close()
        soup = BeautifulSoup(txt, 'html5lib')
        li = soup.select('#bd_1 > div.m_tab > ul > li > a')
        if not li:
            # 新股可能没有这些信息
            print('Load Error: 股东研究 ', code, '未找到id = bd_1 下的li元素')
            raise Exception()
        days = []
        for l in li:
            days.append(l.contents[0])
        if not days:
            print('Load Error: 股东研究 ', code, '未找到days')
            raise Exception()
        
        captions = soup.select('#bd_1 table > caption')
        if not captions:
            print('Load Error: 股东研究 ', code, '未找到id = bd_1 下的caption元素')
            raise Exception()
        for i, cp in enumerate(captions):
            obj = {'code': code, 'day': days[i]}
            ems = cp.find_all('em')
            for em in ems:
                if em.contents[0] and '%' in em.contents[0]:
                    obj['rate'] = float(em.contents[0].replace('%', ''))
                    break
            self.saveDB(obj)
            print('Load 股东研究：', code, '前十大流通股东', obj)

#机构持股
class LoadJGCG:
    def saveDB(self, objx):
        obj = ths_orm.THS_JGCG.get_or_none(code = objx['code'], day = objx['day'])
        if (obj):
            obj.update(**objx)
            obj.save()
        else:
            ths_orm.THS_JGCG.create(**objx)

    def load(self, code):
        f = open(BASE_PATH + code + '-主力持仓.html', 'r', encoding= 'utf8')
        txt = f.read()
        f.close()
        js = json.loads(txt)
        
        if ('status_code' not in js) or (js['status_code'] != 0 or ('data' not in js)):
            print('Load Error: ', '主力持仓', code)
            raise Exception()
        rs = { 'code' : code }
        for it in js['data']:
            if it['is_updating']:
                continue
            rs['day'] = it['date']
            idx = 0
            for i, c in enumerate(('一季报', '中报', '三季报', '年报')):
                if c in it['date']:
                    idx = i + 1
                    break
            rs['day_sort'] = str(toInt(it['date'])) + '-' + str(idx)
            rs['jjsl'] = it['org_num']
            rs['rate'] = toFloat(it['total_rate'])
            rs['change'] = toInt(it['total_holder_change']) // 10000 #  万股
            self.saveDB(rs)
            print('Load 机构持仓: ', code, rs)

#加载行业对比数据
class LoadHYDB:
    def __init__(self) -> None:
        # 行业信息
        self.hyInfos = {} # {行业名称-日期: {关联股票, ...}, ... }

    def listHydbFiles(self):
        tag = '同行比较'
        fs = os.listdir(BASE_PATH)
        rs = [f for f in fs if tag in f ]
        return rs

    def loadData(self, day, data, cols, hydj, hy):
        key = hy + ':' + day
        if key not in self.hyInfos:
            self.hyInfos[key] = {}
        hyInfo = self.hyInfos[key] = {}

        for d in data:
            obj = { 'hy': hy, 'hydj': hydj, 'day': day}
            for c in cols:
                obj[c[0]] = d[c[1]] if c[1] <= 1  else float(d[c[1]])
            #print(obj)
            code = obj['code']
            hyInfo[code] = obj

    def loadDatas(self, txt, cols, hydj, hy):
        if hy in self.hyInfos:
            return
        js = json.loads(txt)
        for day in js:
            self.loadData(day, js[day], cols, hydj, hy)

    # 行业对比
    def loadFile(self, fileName):
        f = open(BASE_PATH + fileName, 'r', encoding= 'gbk')
        txt = f.read()
        f.close()
        soup = BeautifulSoup(txt, 'html5lib')

        ps = soup.select('.threecate') # 三级、二级 行业分类 <p>
        hyNames = []
        for p in ps:
            nn = ''.join(p.stripped_strings) # 三级行业分类：纺织服饰 -- 服装家纺 -- 非运动服装 （共37家） |  二级行业分类：纺织服饰 -- 服装家纺 （共63家）
            dj = nn[0 : 2] # 三级 | 二级
            hy = nn[7 : nn.find('（')].strip() # 纺织服饰 -- 服装家纺 -- 非运动服装
            hyNames.append((dj, hy))

        if len(hyNames) == 0:
            print('Load 行业对比: ', fileName, '未找到行业排名信息')
            raise Exception()
        print('Load 行业对比: ', fileName, hyNames)

        childs = soup.select('#sortNav > li')
        titles = ('每股收益', '每股净资产', '每股现金流', '净利润', '营业总收入', '总资产', '净资产收益率', '股东权益比例', '销售毛利率', '总股本')
        if len(childs) != len(titles):
            print('行业对比 文件内容发生变更，请修改代码')
            raise Exception()
        for i, it in enumerate(childs):
            if titles[i] != it.string.strip():
                print('行业对比 文件内容发生变更，请修改代码')
                raise Exception()
        
        colInfos = [('code', 0), ('name', 1), ('mgsy', 2), ('mgjzc', 3), ('mgxjl', 4), ('jlr', 5), ('yyzsl', 6), ('zgb', 11)]
        
        p1 = soup.select('#fieldsChartData') # 三级行业数据
        if len(p1) == 1:
            p1x = p1[0]
            txt = p1x['value']
            self.loadDatas(txt, colInfos, *hyNames[0])
        p2 = soup.select('#fieldsChart2Data') # 二级行业数据
        if len(p2) == 1:
            p2x = p2[0]
            txt = p2x['value']
            self.loadDatas(txt, colInfos, *hyNames[len(hyNames) - 1])
        
        if len(p1) != 1 and len(p2) != 1:
            print('Load Error: 行业对比 ', fileName, '未找到二级、三级行业数据')
            raise Exception()

    #计算综合排名
    def calcHyPM(self, datas):
        rs = sorted(datas, key = lambda d : d['mgsy'], reverse=True)
        for idx, dt in enumerate(rs):
            dt['mgsyPM'] = idx + 1
        rs = sorted(datas, key = lambda d : d['jlr'], reverse=True)
        for idx, dt in enumerate(rs):
            dt['jlrPM'] = idx + 1
        kf = lambda d : d['mgsyPM'] * 0.4 + d['jlrPM'] * 0.6
        rs = sorted(datas, key = kf)
        for idx, dt in enumerate(rs):
            dt['zhpm'] = idx + 1
        for d in datas:
            del d['mgsyPM']
            del d['jlrPM']

    def calcAllPM(self):
        keys = sorted(self.hyInfos.keys())
        for k in keys:
            datas = self.hyInfos[k]
            #计算数量
            for d in datas.values():
                d['hysl'] = len(datas)
            self.calcHyPM(list(datas.values()))

    def saveDB(self):
        keys = sorted(self.hyInfos.keys())
        for hy in keys:
            datas = self.hyInfos[hy].values()
            for d in datas:
                obj = ths_orm.THS_HYDB.get_or_none(hy = d['hy'], code = d['code'], day = d['day'])
                if obj:
                    obj.update(d)
                    obj.save()
                else:
                    ths_orm.THS_HYDB.create(**d)

    def loadAllFiles(self):
        files =  self.listHydbFiles()
        for f in files:
            self.hyInfos.clear()
            self.loadOneFile(f)

    def loadOneFile(self, fn):
        try:
            self.loadFile(fn)
            self.calcAllPM()
            self.saveDB()
            os.rename(BASE_PATH + fn, BASE_PATH + 'success/' + fn)
        except Exception as e:
            os.rename(BASE_PATH + fn, BASE_PATH + 'fail/' + fn)

#---------------------------------------------------------------------
def listFiles(tag = None):
    fs = os.listdir(BASE_PATH)
    fs = sorted(fs)
    if not tag:
        return fs
    ff = lambda n : tag in n
    return filter(ff, fs)
    
def loadAllFile(tag = None):
    fs = listFiles(tag)
    for idx, fn in enumerate(fs):
        print('[%04d]' % (idx + 1), fn)
        code = fn[0 : 6]
        try:
            if '股东研究' in fn:
                LoadTHS_Top10_LTGD().load(code)
            elif '主力持仓' in fn:
                LoadJGCG().load(code)
            elif '最新动态' in fn:
                LoadNewest().load(code)
            os.rename(BASE_PATH + fn, BASE_PATH + 'success/' + fn)
        except Exception as e:
            os.rename(BASE_PATH + fn, BASE_PATH + 'fail/' + fn)

#------------------------------自动下载数据---------------------------------------
# 最新动态 股东研究  主力持仓
class Download_3:
    def __init__(self) -> None:
        self.posList = [(710, 100), (925, 100), (925, 125)]
        self.posIdx = 0
        self.WAIT_TIME = 1.5

    def nextPos(self):
        pos = self.posList[ self.posIdx % 3]
        self.posIdx += 1
        return pos

    #下一个
    def clickNext(self):
        pa.moveTo(1180, 65)
        pa.click()
        time.sleep(self.WAIT_TIME)

    def download(self, num = 5111):
        for i in range(num):
            for k in range(len(self.posList) - 1):
                pos = self.nextPos()
                pa.moveTo(pos[0], pos[1])
                pa.click()
                time.sleep(self.WAIT_TIME)
            self.clickNext()

#下载所有的行业对比
class Download_HYDB:
    def accept(self, d):
        return d.name and ('ST' not in d.name.upper()) and (d.code[0] == '3' or d.code[0] == '0' or d.code[0] == '6')

    def getCodes(self):
        codes = []
        qr = ths_orm.THS_GNTC.select().group_by(ths_orm.THS_GNTC.hy)
        for d in qr:
            if self.accept(d):
                codes.append((d.code, d.name, d.hy))
                continue
            qn = ths_orm.THS_GNTC.select().where(ths_orm.THS_GNTC.hy == d.hy)
            for dx in qn:
                if self.accept(dx):
                    codes.append((dx.code, dx.name, dx.hy))
                    break
        return codes
            

    def download(self):
        pa.moveTo(1380, 125)
        pa.click()
        time.sleep(2.5)

        codes = self.getCodes()
        for c in codes:
            pa.typewrite(c[0], interval = 0.25)
            pa.press("enter")
            time.sleep(2.5)

def autoDownload():
    fd = fiddler.Fiddler()
    fd.open()
    time.sleep(5)
    Download_3().download()
    Download_HYDB().download()
    fd.close()

if __name__ == '__main__':
    # autoDownload()

    # 解析下载的数据文件，并保存
    loadAllFile('股东研究')
    loadAllFile('主力持仓')
    loadAllFile('最新动态')
    LoadHYDB().loadAllFiles()
    



