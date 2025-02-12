import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging
import peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import tck_orm
from Download import console, cls, ths_iwencai

class Server:
    def __init__(self) -> None:
        self._runInfo = {}
        self._lastLoadTime = 0
        self._lastLoadHotTcTime = 0
        self._lastLoadZSTime = 0
        self._lastLoadBkGnTime = 0
        self._lastLoadZSZDTime = 0
        self._lastLoadDegreeTime = 0

    def now(self):
        return datetime.datetime.now().strftime('%H:%M')
    
    def formatNowTime(self, hasDay):
        ts = datetime.datetime.now()
        if hasDay:
            return ts.strftime('%Y-%m-%d %H:%M')
        return ts.strftime('%H:%M')

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
            return day, degree
        except Exception as e:
            traceback.print_exc()
            return None
        
    def saveDegree(self, day, degree):
        obj = tck_orm.CLS_SCQX.get_or_none(day = day)
        if not obj:
            tck_orm.CLS_SCQX.create(day = day, zhqd = degree)
            console.write_1(console.CYAN, '[cls-server] ')
            print(' load degree: ', day, ' -> ', degree)

    def saveDegreeTime(self, day, time, degree):
        obj = tck_orm.CLS_SCQX_Time.get_or_none(day = day, time = time)
        if not obj:
            tck_orm.CLS_SCQX_Time.create(day = day, time = time, zhqd = degree)
    
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
            rs = self.tryDownloadDegree()
            if rs:
                d, degree = rs
                self.saveDegree(d, degree)
                self._runInfo[day] = True
        if curTime >= '09:30' and curTime <= '16:00':
            self.downloadClsZT()
            
        self.downloadZS()
        self.downloadBkGn()

    def loadTimeDegree(self):
        now = datetime.datetime.now()
        if not self.acceptDay(now):
            return
        curTime = now.strftime('%H:%M')
        if (curTime >= '09:30' and curTime <= '11:30') or (curTime >= '13:00' and curTime <= '15:00'):
            if (now.minute % 10 <= 2) and (time.time() - self._lastLoadDegreeTime >= 3 * 60):
                curTime = curTime[0 : -1] + '0'
                rs = self.tryDownloadDegree()
                if rs:
                    self._lastLoadDegreeTime = time.time()
                    d, degree = rs
                    self.saveDegreeTime(d, curTime, degree)

    def loadHotTc(self, daysNum = 10):
        try:
            if time.time() - self._lastLoadHotTcTime < 30:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '09:30' or st > '15:00':
                return
            days = ths_iwencai.getTradeDays(daysNum)
            if not days:
                return
            maxDay = tck_orm.CLS_HotTc.select(pw.fn.max(tck_orm.CLS_HotTc.day)).scalar()
            if not maxDay:
                maxDay = days[- min(daysNum, len(days))]
            maxDay = maxDay.replace('-', '')
            for d in days:
                if d >= maxDay:
                    self._loadHotTcOfDay(d)
            self._lastLoadHotTcTime = time.time()
        except Exception as e:
            traceback.print_exc()

    def _loadHotTcOfDay(self, day):
        url = cls.ClsUrl()
        ds = url.loadHotTC(day)
        if not ds:
            return
        cday = ds[0]['c_time'].split(' ')[0]
        exists = {}
        qr = tck_orm.CLS_HotTc.select().where(tck_orm.CLS_HotTc.day == cday)
        for it in qr:
            key = it.name + ' ' + it.ctime
            exists[key] = True
        for d in ds:
            cts = d['c_time'].split(' ')
            day, ctime = cts
            key = f'{d["symbol_name"]} {ctime}'
            if exists.get(key, False):
                continue
            tck_orm.CLS_HotTc.create(day = day, name = d['symbol_name'], up = d['float'] == 'up', ctime = ctime)

    # 指数（板块概念）
    def downloadZS(self):
        try:
            if time.time() - self._lastLoadZSTime < 90 * 60:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '15:00' or st > '16:00':
                return
            rs = cls.ClsUrl().loadAllZS()
            ex = {}
            from orm import cls_orm
            qt = cls_orm.CLS_ZS.select()
            u, i = 0, 0
            for it in qt:
                ex[it.code] = it
            for it in rs:
                if it['code'] in ex:
                    zs = ex[it['code']]
                    if zs.name != it['name']:
                        zs.name = it['name']
                        zs.save()
                        u += 1
                else:
                    cls_orm.CLS_ZS.create(code = it['code'], name = it['name'], type_ = it['type_'])
                    i += 1
            self._lastLoadZSTime = time.time()
            console.writeln_1(console.GREEN, f'[CLS-ZS] {self.formatNowTime(True)} insert={i} update={u}')
        except Exception as e:
            traceback.print_exc()

    # 指数分时
    def downloadZSTimeline(self):
        try:
            if time.time() - self._lastLoadZSZDTime <= 90 * 60:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '17:00' or st > '18:00':
                return
            from orm import cls_orm
            qt = cls_orm.CLS_ZS.select()
            u, i = 0, 0
            for it in qt:
                pass
            self._lastLoadZSZDTime = time.time()
            console.writeln_1(console.GREEN, f'[CLS-ZS-ZD] {self.formatNowTime(True)} insert={i} update={u}')
        except Exception as e:
            traceback.print_exc()

    # 个股概念板块
    def downloadBkGn(self):
        try:
            if time.time() - self._lastLoadBkGnTime < 90 * 60:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '15:00' or st > '16:00':
                return
            console.writeln_1(console.CYAN, f'[CLS-HyGn] {self.formatNowTime(True)} begin...')
            from orm import ths_orm, cls_orm
            qr = ths_orm.THS_GNTC.select().dicts()
            zs = {}
            def diff(old, new, names):
                flag = False
                for n in names:
                    if getattr(old, n, '') != getattr(new, n, ''):
                        setattr(old, n, getattr(new, n, ''))
                        flag = True
                return flag
            attrs = ('name', 'gn', 'gn_code', 'hy', 'hy_code')
            u, i = 0, 0
            for it in qr:
                code = it['code']
                name = it['name']
                info = cls.ClsUrl().loadBkGnOfCode(code, zs)
                if not info:
                    continue
                info.name = name
                obj = cls_orm.CLS_GNTC.get_or_none(code = code)
                if obj:
                    if diff(obj, info, attrs):
                        obj.save() # update
                        u += 1
                else:
                    info.save() # create new
                    i += 1
            self._lastLoadBkGnTime = time.time()
            console.writeln_1(console.CYAN, f'[CLS-HyGn] {self.formatNowTime(True)} update {u}, insert {i}')
        except Exception as e:
            traceback.print_exc()

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
    svr = Server()
    svr.downloadZS()
    svr.downloadBkGn()
    #downloadClsZT()
    obj = tck_orm.CLS_SCQX_Time.get_or_none(day = '2025-02-07')
    print(obj)
    pass
    #do_reason()