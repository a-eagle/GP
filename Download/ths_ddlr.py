import peewee as pw
from peewee import fn
import os, json, time, sys, pyautogui, io, datetime, win32api, win32event, winerror

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])

from orm import ths_orm

BASE_STRUCT_PATH = 'D:/ThsData/ddlr-struct/'
BASE_DETAIL_PATH = 'D:/ThsData/ddlr-detail-src/'
DEST_DETAIL_PATH = 'D:/ThsData/ddlr-detail/'

if not os.path.exists(BASE_STRUCT_PATH):
    os.makedirs(BASE_STRUCT_PATH)
if not os.path.exists(BASE_DETAIL_PATH):
    os.makedirs(BASE_DETAIL_PATH)
if not os.path.exists(DEST_DETAIL_PATH):
    os.makedirs(DEST_DETAIL_PATH)

def codeExists(code):
    e1 = os.path.exists(BASE_STRUCT_PATH + code)
    e2 = os.path.exists(BASE_DETAIL_PATH + code)
    return e1 and e2

def isCode(name):
    if not name:
        return False
    if len(name) != 6:
        return False
    for i in range(len(name)):
        if name[i] > '9' or name[i] < '0':
            return False
    return True

def getNameByCode(code):
    n = ths_orm.THS_Newest.get_or_none(ths_orm.THS_Newest.code == code)
    if not n:
        return ''
    return n.name

class ThsDdlrStructLoader:
    def _loadFileData(self, path):
        data = {}
        f = open(path, 'r', encoding= 'utf8')
        lines = f.readlines()
        f.close()
        i = 0
        while i < len(lines) - 1:
            heads = lines[i].strip().split('\t')
            if len(heads) != 4 or len(lines[i + 1]) < 10:
                i += 1
                continue
            curTime, code, day, n = heads
            curDay, curTime = curTime.split(' ')
            curDay = curDay.replace('-', '')
            curTime = curTime[0 : 5] # hh:mm
            if curDay == day:
                if curTime < '15:00':
                    i += 2
                    continue
                
            js = json.loads(lines[i + 1])
            if js['code'] != 0:
                continue
            row = {'code' : code, 'day' : day}
            keys = ['activeIn', 'activeOut', 'positiveIn', 'positiveOut']
            for k in keys:
                row[k] = js['data'][k] / 100000000 # 亿
            row['total'] = row['activeIn'] + row['positiveIn'] - row['activeOut'] - row['positiveOut']
            data[day] = row
            i += 2
        
        # merge data
        rt = []
        for k, v in data.items():
            rt.append(v)
        return rt

    def loadOneFile(self, code, remove = True):
        filePath = BASE_STRUCT_PATH + code
        if not os.path.exists(filePath):
            return
        data = self._loadFileData(filePath)
        if len(data) <= 0:
            return
        self.mergeSavedData(data)
        if remove:
            os.remove(filePath)

    def loadAllFileData(self):
        fs = os.listdir(BASE_STRUCT_PATH)
        rs = [f for f in fs if isCode(f) ]
        print('找到大单结构数据: ', len(rs), '个')
        for f in rs:
            self.loadOneFile(f)

    def mergeSavedData(self, datas):
        code = datas[0]['code']
        name = getNameByCode(code)
        maxDay = ths_orm.THS_DDLR.select(pw.fn.Max(ths_orm.THS_DDLR.day)).where(ths_orm.THS_DDLR.code == code).scalar()
        if not maxDay:
            maxDay = ''
        for d in datas:
            if d['day'] > maxDay:
                d['name'] = name
                ths_orm.THS_DDLR.create(**d)

class ThsDdlrDetailLoader:
    def __init__(self) -> None:
        self.tradeDays = self.getMaxTradeDays()
        #print(self.tradeDays)
        pass

    def getMaxTradeDays(self):
        query = ths_orm.THS_Hot.select(ths_orm.THS_Hot.day).distinct().order_by(ths_orm.THS_Hot.day.desc()).limit(100).tuples()
        #print(query)
        maxDays = [str(d[0]) for d in query]
        return maxDays

    def getTradeDay(self, writeDay):
        for d in self.tradeDays:
            if writeDay >= d:
                return d
        raise Exception('出错了')

    def loadAllFilesData(self):
        fs = os.listdir(BASE_DETAIL_PATH)
        #print('找到大单详细数据: ', len(fs), '个')
        for f in fs:
            if not isCode(f):
                continue
            self.loadOneFile(f, True)
    
    def loadOneFile(self, code, remove = True):
        fp = BASE_DETAIL_PATH + code
        destfp = DEST_DETAIL_PATH + code + '.dd'
        if not os.path.exists(fp):
            return False
        srcData = self.readSrcFile(fp)
        self.writeDestData(srcData, destfp)
        if remove:
            os.remove(fp)
    
    # 写入 xxxxxx.dd 文件， 数据格式： 日期;开始时间,结束时间,买卖方式(1:主动买 2:被动买 3:主动卖 4:被动卖),成交金额(万元); ...
    def writeDestData(self, srcData, destFileName):
        if srcData == None:
            srcData = []
        rw, days, destData = self.readDestFile(destFileName)
        # merge src and dest data
        mdata = []
        for sd in srcData:
            day, line = sd
            if day in days:
                continue
            mdata.append(line)
            days.add(day)
        if rw:
            df = open(destFileName, 'w', encoding='utf8')
            for d in destData:
                df.write(d)
                df.write('\n')
        else:
            df = open(destFileName, 'a', encoding='utf8')
        for d in mdata:
            df.write(d)
            df.write('\n')
        df.close()
    
    def readSrcFile(self, fileName):
        if not fileName:
            return None
        f = open(fileName, 'r', encoding= 'utf8')
        lines = f.readlines()
        f.close()
        i = 0
        rs = []
        while i < len(lines) - 1:
            heads = lines[i].strip().split('\t')
            if len(heads) != 2 or len(lines[i + 1]) < 10:
                i += 1
                continue
            curTime, code = heads
            curDay, curTime = curTime.split(' ')
            curDay = curDay.replace('-', '')
            curTime = curTime[0 : 5] # hh:mm
            tradeDay = self.getTradeDay(curDay)
            ld = json.loads(lines[i + 1])
            if ld['code'] != 0:
                i += 2
                continue
            sio = io.StringIO()
            sio.write(tradeDay + ';')
            for d in ld['data']:
                v = d['firstTime'][0 : 6] + ',' + d['lastTime'][0 : 6] + ',' + str(d['stats']) + ',' + str(int(d['totalMoney'] / 10000 + 0.5)) + ',' + str(d['tradeVol'] // 100) + ';'
                sio.write(v)
            rs.append((tradeDay, sio.getvalue()))
            i += 2
        return rs
        
    def readDestFile(self, destfp):
        if not os.path.exists(destfp):
            return True, set(), []
        f = open(destfp, 'r', encoding= 'utf8')
        lines = f.readlines()
        f.close()
        rs = []
        rw = False
        existsDays = set()
        for line in lines:
            line : str = line.strip()
            if not line:
                rw = True
                continue
            day = line[0 : line.index(';')]
            if day in existsDays:
                rw = True
                continue
            existsDays.add(day)
            rs.append(line)
        return rw, existsDays, rs

class ThsDdlrDetailData:

    def __init__(self, code) -> None:
        self.code = code
        # [{day :'YYYY-MM-DD', data: [(minutes, bs, money, vol), ...], ... ]   
        # minutes int value . eg: 930 ==> '09:30' ; bs -> 1:主动买 2:被动买 3:主动卖 4:被动卖;  money :万元 vol:手
        self.data = []
        self._loadFile()

    def getDataAtDay(self, day):
        if type(day) == int:
            day = f'{day // 10000}-{day // 100 % 100 :02d}-{day % 100 :02d}'
        for item in self.data:
            if item['day'] == day:
                return item['data']
        return None

    # return [fromIdx, endIdx)
    def getMiniteDataRange(self, dayData, fromIdx):
        if fromIdx < 0 or fromIdx >= len(dayData):
            return None
        minute = dayData[fromIdx]['beginTime']
        for i in range(fromIdx, len(dayData)):
            if minute != dayData[i]['beginTime']:
                break
            i += 1
        return (fromIdx, i)

    def _loadOneLine(self, line):
        rs = {}
        spec = line.split(';')
        rs['day'] = spec[0][0 : 4] + '-' + spec[0][4 : 6] + '-' + spec[0][6 : 8]
        rs['data'] = []
        md = None
        for i in range(1, len(spec)):
            if not spec[i].strip():
                continue
            items = spec[i].split(',')
            if len(items) == 3:
                _btime, bs, money = items
                vol = 0
                _etime = _btime
            elif len(items) == 5:
                _btime, _etime, bs, money, vol = items
                _btime = int(_btime) // 100
                _etime = int(_etime) // 100
            else:
                print('[ThsDdlrDetailData._loadOneLine], Error Data:', items)
                continue
            obj = {'beginTime': int(_btime), 'endTime':int(_etime), 'bs': int(bs), 'money': int(money), 'vol': int(vol) }
            rs['data'].append(obj)
            #rs['data'].append((int(_btime), int(_etime), int(bs), int(money), int(vol)))
        # sort data by end time
        rs['data'] = sorted(rs['data'], key= lambda d : d['beginTime'])
        return rs

    def _loadFile(self):
        fp = DEST_DETAIL_PATH + self.code + '.dd'
        if not os.path.exists(fp):
            return
        f = open(fp, 'r')
        while True:
            line = f.readline().strip()
            if not line:
                break
            item = self._loadOneLine(line)
            if len(self.data) > 0 and self.data[-1]['day'] == item['day']:
                self.data[-1] = item # 重复数据 replace it
            else:
                self.data.append(item)
        f.close()


if __name__ == '__main__':
    ddlr = ThsDdlrDetailLoader()
    ddlr.loadAllFilesData()