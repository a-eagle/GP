import json, os, sys, datetime, threading, time, inspect, platform, base64, struct
import traceback
import requests, json, logging
import peewee as pw, flask, flask_cors

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import datafile, ths_iwencai, config
from utils import cutils

class Client:
    def __init__(self) -> None:
        self.PAGE_SIZE = 100

    def getLocalLatestDay(self):
        d = datafile.KLineDownloader()
        day = d.getLocalLatestDay()
        return day
        
    def getServerCodesCount(self):
        resp = requests.get(f'{config.SYNC_KDATA_SERVER_BASE_URL}/getCodesCount')
        js = json.loads(resp.text)
        return js['count']

    def getServerLatestDay(self):
        resp = requests.get(f'{config.SYNC_KDATA_SERVER_BASE_URL}/getLatestDay')
        js = json.loads(resp.text)
        return js['day']

    def getServerKdatas(self, fromDay : int, page : int):
        url = f'{config.SYNC_KDATA_SERVER_BASE_URL}/getKDatas/{fromDay}/{page}/{self.PAGE_SIZE}'
        resp = requests.get(url)
        datas = resp.content
        if not datas:
            return None
        rs = self.decodeKdatas(datas)
        return rs
        
    def decodeKdatas(self, bs):
        rs = []
        codeNum = struct.unpack_from('L', bs, 0)[0]
        pi = 4
        for i in range(codeNum):
            code = struct.unpack_from('6s', bs, pi)[0]
            code = code.decode('utf-8')
            pi += 6
            cnum = struct.unpack_from('L', bs, pi)[0]
            pi += 4
            rs.append({'code': code, 'kdata-num': cnum, 'kdatas': bs[pi : pi + 32 * cnum]})
            pi += 32 * cnum
        return rs

    def writeKdata(self, code, num, datas):
        dl = datafile.KLineDownloader()
        rs = []
        for i in range(num):
            dd = struct.unpack_from('L7f', datas, i * 32)
            item = datafile.ItemData(day = dd[0], open = dd[1], close = dd[2], low = dd[3], high = dd[4], vol = dd[5], amount = dd[6], rate = dd[7])
            rs.append(item)
        dl.mergeWrite(code, rs)

    def getFromDay(self):
        tdays = cutils.getTradeDaysInt()
        curDay = self.getLocalLatestDay()
        idx = tdays.index(curDay)
        if idx >= len(tdays) - 1:
            return None, None
        nextDay = tdays[idx + 1]
        svrDay = self.getServerLatestDay()
        if nextDay > svrDay:
            return None
        return curDay, nextDay

    def download(self, fromPage = 0):
        curDay, fromDay = self.getFromDay()
        if not fromDay:
            print('[download] kdata not need to download')
            return True
        print('[download] begin...')
        startTime = time.time()
        print(f'  {curDay} -> {self.getServerLatestDay()}')
        count = self.getServerCodesCount()
        pageNum = (count + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        flag = True
        for i in range(fromPage, pageNum):
            print('[load page]', i + 1)
            datas = self.getServerKdatas(fromDay, i + 1)
            if not datas:
                flag = False
                break
            for item in datas:
                self.writeKdata(item['code'], item['kdata-num'], item['kdatas'])
        useTime = (time.time() - startTime) / 60
        print(f'[download] end, use time: {useTime :.1f} minutes, ', 'success' if flag else 'fail')
        return flag

    def start(self):
        from download import tdx
        def acceptTime():
            nowTime = datetime.datetime.now().strftime("%H:%M")
            if not (nowTime >= '15:00' and nowTime <= '15:30'): # 服务器下数据时间
                return True
            return cutils.isTradeDay()

        klineTry = tdx.Try(acceptTime, 3, self.download, intervalTime = 10 * 60, userNoInputTime = 0, ignoreDay = 0)
        while True:
            klineTry.check()
            time.sleep(5 * 60)

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        # log.disabled = True
        flask_cors.CORS(self.app)

    def start(self):
        self.unlock()
        self.thread = threading.Thread(target = self._run, name='SyncKdataServer', daemon = True)
        self.thread.start()
        self.app.add_url_rule('/getLatestDay', view_func = self.getLatestDay, methods = ['GET', 'POST'])
        self.app.add_url_rule('/getCodesCount', view_func = self.getCodesCount, methods = ['GET', 'POST'])
        self.app.add_url_rule('/getKDatas/<fromDay>/<page>/<pageSize>', view_func = self.getKDatas, methods = ['GET', 'POST'])
        self.app.run('0.0.0.0', 8070, use_reloader = False, debug = False)

    def lock(self):
        path = os.path.join(datafile.PathManager.NET_LDAY_PATH, 'write.lock')
        if not os.path.exists(path):
            f = open(path, 'w')
            f.close()
    
    def unlock(self):
        path = os.path.join(datafile.PathManager.NET_LDAY_PATH, 'write.lock')
        if os.path.exists(path):
            os.remove(path)

    def isLocked(self):
        path = os.path.join(datafile.PathManager.NET_LDAY_PATH, 'write.lock')
        return os.path.exists(path)

    def getLatestDay(self):
        d = datafile.KLineDownloader()
        day = d.getLocalLatestDay()
        if not day:
            day = 0
        return {'day': day}

    def getCodesCount(self):
        dl = datafile.KLineDownloader()
        codes = dl.getLocalCodes()
        return {'count': len(codes)}

    # page = [1...]
    def getKDatas(self, fromDay, page, pageSize):
        fromDay = int(fromDay)
        page = int(page)
        pageSize = int(pageSize)
        kd = datafile.KLineDownloader()
        tdays = cutils.getTradeDaysInt()
        if fromDay not in tdays:
            return flask.Response(b'', mimetype = 'application/octet-stream')
        idx = tdays.index(fromDay)
        numDays = len(tdays) - idx
        buf = bytearray()
        fs = kd.getLocalCodes()
        fs = fs[(page - 1) * pageSize : page * pageSize]
        buf.extend(struct.pack('L', len(fs)))
        for i, code in enumerate(fs):
            if self.isLocked():
                buf = b''
                break
            self.readKdata(code, fromDay, numDays, buf)
        return flask.Response(bytes(buf), mimetype = 'application/octet-stream')

    def readKdata(self, code : str, fromDay, numDays, buf : bytearray):
        path = os.path.join(datafile.PathManager.NET_LDAY_PATH, code)
        fsize = os.path.getsize(path)
        maxDays = fsize // 32
        numDays = min(numDays, maxDays)
        buf.extend(code.encode('utf-8'))
        if numDays == 0:
            buf.extend(struct.pack('L', 0))
            return
        ff = open(path, 'rb')
        ff.seek(- numDays * 32, 2)
        bs = ff.read(numDays * 32)
        ff.close()
        fi = numDays
        for i in range(numDays):
            dd = struct.unpack_from('L7f', bs, 32 * i)
            if dd[0] >= fromDay:
                fi = i
                break
        buf.extend(struct.pack('L', numDays - fi))
        for bi in range(fi, numDays):
            buf.extend(bs[32 * bi : 32 * bi + 32])

    def downloadKLine(self):
        kd = datafile.KLineDownloader()
        lastDay = kd.getLocalLatestDay()
        tdays = cutils.getTradeDaysInt()
        idx = tdays.index(lastDay) + 1
        if idx >= len(tdays):
            return True
        self.lock()
        print('local cur day=', lastDay, 'trade last day=', tdays[-1])
        print('begin download kdata...')
        for i in range(idx, len(tdays)):
            ok = kd.downloadByDay(tdays[i])
            if not ok:
                break
        print('download ', ('success' if ok else 'fail'), '\n')
        self.unlock()
        return ok

    def _run(self):
        from download import tdx
        klineTry = tdx.Try('15:05', 3, self.downloadKLine, intervalTime = 600, userNoInputTime = 0, ignoreDay = 20260414)
        while True:
            klineTry.check()
            time.sleep(60)

if __name__ == '__main__':
    IS_SERVER = config.isServerMachine()

    if IS_SERVER:
        svr = Server()
        svr.start()
    else:
        client = Client()
        print('Server codes count:', client.getServerCodesCount())
        print('Server lastest day:', client.getServerLatestDay())
        print('Client lastest day:', client.getLocalLatestDay())
        client.start()
