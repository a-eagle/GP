import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import tck_orm
from Download import console

class Server:
    def __init__(self) -> None:
        self._runInfo = {}
        self._lastLoadTime = 0

    def now(self):
        return datetime.datetime.now().strftime('%H:%M')

    def saveCls_ZT_One(self, it):
        insertNum, updateNum = 0, 0
        obj = tck_orm.CLS_ZT.get_or_none(code = it['code'], day = it['day'])
        if obj:
            if obj.ztReason != it['ztReason'] or obj.detail != it['detail']:
                obj.ztReason = it['ztReason']
                obj.detail = it['detail']
                updateNum += 1
                obj.save()
        else:
            insertNum += 1
            tck_orm.CLS_ZT.create(**it)
        return insertNum, updateNum

    def saveCls_ZT_List(self, its):
        day = None
        insertNum, updateNum = 0, 0
        for it in its:
            day = it['day']
            ins, upd = self.saveCls_ZT_One(it)
            insertNum += ins
            updateNum += upd
        if insertNum > 0 or updateNum > 0:
            console.writeln_1(console.CYAN, '[cls-server] ', f'{self.now()} save cls zt {day} insert({insertNum}) update({updateNum})')

    def __downloadClsZT(self):
        url = 'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=7.7.5&type=up_pool&way=last_px&sign=a820dce18412fac3775aa940d0b00dcb'
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        if js['code'] != 200:
            return
        data = js['data']
        rs = []
        for item in data:
            if item['is_st'] != 0:
                continue
            obj = {'code' : item['secu_code'], 'name': item['secu_name'], 'lbs': item['limit_up_days'] }
            if not obj['code']:
                continue
            if len(obj['code']) == 8:
                obj['code'] = obj['code'][2 : ]
            # obj.ztTime = item.time.substring(11, 16);
            obj['day'] = item['time'][0 : 10]
            obj['ztReason'] = ''
            rz : str = item['up_reason'].strip()
            idx = rz.find('|')
            if idx > 0 and idx < 30 and (not rz.startswith('1.')):
                obj['ztReason'] = rz[0 : idx].strip()
                obj['detail'] = rz[idx + 1 : ].strip()
            else:
                obj['detail'] = rz
            if obj['ztReason'] != '--':
                rs.append(obj)
        return rs

    def downloadClsZT(self):
        try:
            rs = self.__downloadClsZT()
            self.saveCls_ZT_List(rs)
        except Exception as e:
            traceback.print_exc()

    def acceptDay(self, day):
        if type(day) == str:
            day = day.replace('-', '')
            day = int(day)
        if type(day) == int:
            day = datetime.date(day // 10000, day // 100 % 100, day % 100)
        if day.weekday() >= 5:
            return False
        return True

    def tryDownloadDegree(self):
        try:
            now = datetime.datetime.now()
            today = now.strftime('%Y-%m-%d')
            obj = tck_orm.CLS_SCQX.get_or_none(day = today)
            if obj:
                return
            url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            day = js['data']['date']
            degree = js['data']['market_degree']
            degree = int(float(degree) * 100)
            obj = tck_orm.CLS_SCQX.get_or_none(day = day)
            if not obj:
                tck_orm.CLS_SCQX.create(day = day, zhqd = degree)
                console.write_1(console.CYAN, '[cls-server] ')
                print(' load degree: ', day, ' -> ', degree)
            return True
        except Exception as e:
            traceback.print_exc()
            return False
    
    def loadOneTime(self):
        if time.time() - self._lastLoadTime < 5 * 60:
            return
        self._lastLoadTime = time.time()
        now = datetime.datetime.now()
        if not self.acceptDay(now):
            return
        curTime = now.strftime('%H:%M')
        day = now.strftime('%Y-%m-%d')
        if curTime > '15:00' and (day not in self._runInfo):
            ok = self.tryDownloadDegree()
            if ok:
                self._runInfo[day] = True
        if curTime >= '09:30' and curTime <= '16:00':
            self.downloadClsZT()

def do_reason():
    qr = tck_orm.CLS_ZT.select().where(tck_orm.CLS_ZT.day >= '2024-07-26')
    for it in qr:
        if it.ztReason or not it.detail:
            continue
        rz : str = it.detail.strip()
        idx = rz.find('|')
        if idx > 0 and idx < 30 and (not rz.startswith('1.')):
            it.ztReason = rz[0 : idx].strip()
            it.detail = rz[idx + 1 : ].strip()
            it.save()

if __name__ == '__main__':
    #downloadClsZT()
    #tryDownloadDegree()
    pass
    #do_reason()