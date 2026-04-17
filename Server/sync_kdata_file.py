import json, os, sys, datetime, threading, time, inspect, platform, base64, struct
import traceback
import requests, json, logging
import peewee as pw, flask, flask_cors

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import datafile, ths_iwencai

class Client:
    def __init__(self) -> None:
        self.PAGE_SIZE = 100

    def getServerCodesCount(self):
        resp = requests.get('http://localhost:8070/getCodesCount')
        js = json.loads(resp.text)
        return js['count']

    def getServerLatestDay(self):
        resp = requests.get('http://localhost:8070/getLatestDay')
        js = json.loads(resp.text)
        return js['day']

    def getServerKdatas(self, fromDay : int, page : int):
        url = f'http://localhost:8070/getKDatas/{fromDay}/{page}/{self.PAGE_SIZE}'
        resp = requests.get(url)
        datas = resp.content
        if not datas:
            return
        rs = self.decodeKdatas(datas)
        print(f'[getServerKdatas] {fromDay} {page}:', rs)
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
            # for c in range(cnum):
            #     ds = struct.unpack_from('L7f', bs, pi + c * 32)
            #     print('  ', ds)
            pi += 32 * cnum
        return rs

    def writeKdatas(self, datas):
        pass

    def download(self, fromDay : int):
        print('[download] begin...')
        count = self.getServerCodesCount()
        pageNum = (count + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        for i in range(pageNum):
            print('[load page]', i + 1)
            datas = self.getServerKdatas(fromDay, i + 1)
            self.writeKdatas(datas)
        print('[download] end')

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        # log.disabled = True
        flask_cors.CORS(self.app)

    def start(self):
        self.app.add_url_rule('/getLatestDay', view_func = self.getLatestDay, methods = ['GET', 'POST'])
        self.app.add_url_rule('/getCodesCount', view_func = self.getCodesCount, methods = ['GET', 'POST'])
        self.app.add_url_rule('/getKDatas/<fromDay>/<page>/<pageSize>', view_func = self.getKDatas, methods = ['GET', 'POST'])
        self.app.run('0.0.0.0', 8070, use_reloader = False, debug = False)

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
        tdays = ths_iwencai.getTradeDaysInt()
        if fromDay not in tdays:
            return flask.Response(b'', mimetype = 'application/octet-stream')
        idx = tdays.index(fromDay)
        numDays = len(tdays) - idx
        buf = bytearray()
        fs = kd.getLocalCodes()
        fs = fs[(page - 1) * pageSize : page * pageSize]
        buf.extend(struct.pack('L', len(fs)))
        for i, code in enumerate(fs):
            print(f'--[{i + (page - 1) * pageSize}]--', end='')
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
        print(f'--write---{code}---->')
        for bi in range(fi, numDays):
            buf.extend(bs[32 * bi : 32 * bi + 32])
            print('   ', struct.unpack('L7f', bs[32 * bi : 32 * bi + 32]))

if __name__ == '__main__':
    IS_SERVER = 0

    if IS_SERVER:
        svr = Server()
        svr.start()
    else:
        client = Client()
        # print(client.getServerCodesCount())
        # print(client.getServerLatestDay())
        client.getServerKdatas(20260407, 1)
