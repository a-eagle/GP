import json, os, sys, datetime, threading, time
import traceback
import requests, json, logging
import peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import cls_orm, d_orm, ths_orm
from download import console, cls, ths_iwencai

class Server:
    def __init__(self) -> None:
        self.downloadInfos = {'ignore': '2025-04-11'}
        self._lastLoadTime = 0
        self._lastLoadHotTcTime = 0
        self._lastLoadZSTime = 0
        self._lastLoadBkGnTime = 0
        self._lastLoadZSZDTime = 0
        self._lastLoadDegreeTime = 0
        self._lastLoadZT_PanKou = 0

    def now(self):
        return datetime.datetime.now().strftime('%H:%M')
    
    def formatNowTime(self, hasDay):
        ts = datetime.datetime.now()
        if hasDay:
            return ts.strftime('%Y-%m-%d %H:%M')
        return ts.strftime('%H:%M')

    def saveCls_ZT_One(self, it):
        insertNum, updateNum = 0, 0
        obj = cls_orm.CLS_ZT.get_or_none(code = it['code'], day = it['day'])
        if obj:
            if obj.ztReason != it['ztReason'] or obj.detail != it['detail']:
                obj.ztReason = it['ztReason']
                obj.detail = it['detail']
                updateNum += 1
                obj.save()
        else:
            insertNum += 1
            cls_orm.CLS_ZT.create(**it)
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
            console.writeln_1(console.CYAN, '[cls-zt] ', f'{self.now()} save cls zt {day} insert({insertNum}) update({updateNum})')

    def _downloadClsZT(self):
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
            rs = self._downloadClsZT()
            self.saveCls_ZT_List(rs)
        except Exception as e:
            traceback.print_exc()

    def downloadDegree(self):
        url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
        resp = requests.get(url)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        day = js['data']['date']
        degree = js['data']['market_degree']
        degree = int(float(degree) * 100)
        return day, degree

    def downloadScqx(self, tag):
        try:
            now = datetime.datetime.now()
            today = now.strftime('%Y-%m-%d')
            obj = cls_orm.CLS_SCQX.get_or_none(day = today)
            if obj:
                console.writeln_1(console.CYAN, f'[CLS-Degree] {tag}', today, 'skip')
                return True
            url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597'
            resp = requests.get(url)
            txt = resp.content.decode('utf-8')
            js = json.loads(txt)
            day = js['data']['date']
            degree = js['data']['market_degree']
            degree = int(float(degree) * 100)
            fb = cls.ClsUrl().getZDFenBu()
            obj = cls_orm.CLS_SCQX.get_or_none(day = day)
            if not obj:
                fb = json.dumps(fb)
                cls_orm.CLS_SCQX.create(day = day, zhqd = degree, fb = fb)
                console.writeln_1(console.CYAN, f'[CLS-Degree] {tag}', day, ' -> ', degree)
            return True
        except Exception as e:
            traceback.print_exc()
        return False

    def saveDegreeTime(self, day, time, degree):
        obj = cls_orm.CLS_SCQX_Time.get_or_none(day = day, time = time)
        if not obj:
            cls_orm.CLS_SCQX_Time.create(day = day, time = time, zhqd = degree)
    
    def loadOneTime(self):
        if time.time() - self._lastLoadTime < 5 * 60:
            return
        self._lastLoadTime = time.time()
        now = datetime.datetime.now()
        if not ths_iwencai.isTradeDay():
            return
        curTime = now.strftime('%H:%M')
        day = now.strftime('%Y-%m-%d')
        if curTime >= '09:30' and curTime <= '16:00':
            self.downloadClsZT()
        
        if self.downloadInfos.get('ignore', None) == day:
            return
        if curTime > '15:10' and (not self.downloadInfos.get(f'scqx-{day}', False)):
            rs = self.downloadScqx('[1/7]')
            self.downloadInfos[f'scqx-{day}'] = rs
        if curTime >= '15:10' and (not self.downloadInfos.get(f'updown-{day}', False)):
            ok = self.downloadUpDown('[2/7]')
            self.downloadInfos[f'updown-{day}'] = ok
        if curTime >= '15:10' and (not self.downloadInfos.get(f'zs-{day}', False)):
            self.downloadInfos[f'zs-{day}'] = True
            self.downloadZS('[3/7]')
        if curTime >= '15:10' and (not self.downloadInfos.get(f'zs-zd-{day}', False)):
            flag = self.downloadZS_ZD('[4/7]')
            self.downloadInfos[f'zs-zd-{day}'] = flag
        if curTime >= '15:10' and (not self.downloadInfos.get(f'ztpk-{day}', False)):
            self.downloadInfos[f'ztpk-{day}'] = True
            self.downloadZT_PanKou('[5/7]')
        if curTime >= '15:10' and (not self.downloadInfos.get(f'hot-tc-{day}', False)):
            flag = self.downloadHotTcOfLastDay('[6/7]')
            self.downloadInfos[f'hot-tc-{day}'] = flag
        if curTime >= '15:10' and (not self.downloadInfos.get(f'bkgn-{day}', False)) and self.downloadInfos[f'zs-zd-{day}']:
            self.downloadInfos[f'bkgn-{day}'] = True
            self.downloadBkGn('[7/7]')
        

    def loadTimeDegree(self):
        now = datetime.datetime.now()
        if not ths_iwencai.isTradeDay():
            return
        curTime = now.strftime('%H:%M')
        if (curTime >= '09:30' and curTime <= '11:30') or (curTime >= '13:00' and curTime <= '15:00'):
            if (now.minute % 10 <= 2) and (time.time() - self._lastLoadDegreeTime >= 3 * 60):
                curTime = curTime[0 : -1] + '0'
                rs = self.downloadDegree()
                if rs:
                    self._lastLoadDegreeTime = time.time()
                    d, degree = rs
                    self.saveDegreeTime(d, curTime, degree)

    def loadHotTc(self, daysNum = 10):
        try:
            if time.time() - self._lastLoadHotTcTime < 600:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '09:30' or st > '15:30':
                return
            days = ths_iwencai.getTradeDays(daysNum)
            if not days:
                return
            maxDay = cls_orm.CLS_HotTc.select(pw.fn.max(cls_orm.CLS_HotTc.day)).scalar()
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
            return 0
        cday = ds[0]['c_time'].split(' ')[0]
        exists = {}
        qr = cls_orm.CLS_HotTc.select().where(cls_orm.CLS_HotTc.day == cday)
        for it in qr:
            key = it.name + ' ' + it.ctime
            exists[key] = it
        for d in ds:
            cts = d['c_time'].split(' ')
            day, ctime = cts
            key = f'{d["symbol_name"]} {ctime}'
            ex = exists.get(key, None)
            if ex:
                if not ex.code:
                    ex.code = d['symbol_code']
                    ex.save()
            else:
                cls_orm.CLS_HotTc.create(day = day, code = d['symbol_code'], name = d['symbol_name'], up = d['float'] == 'up', ctime = ctime)
        return len(ds)

    def downloadHotTcOfLastDay(self, tag):
        try:
            days = ths_iwencai.getTradeDays()
            if not days:
                return False
            num = self._loadHotTcOfDay(days[-1])
            console.writeln_1(console.CYAN, f'[Cls-HotTc] {tag} {self.formatNowTime(True)} num {num}')
            return num > 0
        except Exception as e:
            traceback.print_exc()
        return False

    # 指数（板块概念）
    def downloadZS(self, tag):
        try:
            rs = cls.ClsUrl().loadAllZS()
            ex = {}
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
            console.writeln_1(console.CYAN, f'[CLS-ZS] {tag} {self.formatNowTime(True)} insert={i} update={u}')
        except Exception as e:
            traceback.print_exc()

    def downloadZS_ZD(self, tag):
        try:
            rs = cls.ClsUrl().loadAllZS_ZD()
            lastDay = ths_iwencai.getTradeDays()[-1]
            today = datetime.date.today().strftime('%Y%m%d')
            if today == lastDay:
                hm = datetime.datetime.now().strftime('%H:%M')
                if hm <= '15:00':
                    return False
            fday = lastDay[0 : 4] + '-' + lastDay[4 : 6] + '-' + lastDay[6 : 8]
            existsNum = cls_orm.CLS_ZS_ZD.select(pw.fn.count()).where(cls_orm.CLS_ZS_ZD.day == fday).scalar()
            if existsNum > 0:
                console.writeln_1(console.CYAN, f'[CLS-ZS-ZD] {tag} {self.formatNowTime(True)} skip')
                return True
            irs = []
            for d in rs:
                m = cls_orm.CLS_ZS_ZD(**d)
                m.day = fday
                irs.append(m)
            cls_orm.CLS_ZS_ZD.bulk_create(irs, 100)
            console.writeln_1(console.CYAN, f'[CLS-ZS-ZD] {tag} {self.formatNowTime(True)} insert num={len(rs)}')
            return True
        except Exception as e:
            traceback.print_exc()
        return False

    # 指数分时
    def downloadZSTimeline(self):
        try:
            if time.time() - self._lastLoadZSZDTime <= 90 * 60:
                return
            st = datetime.datetime.now().strftime('%H:%M')
            if st < '17:00' or st > '18:00':
                return
            qt = cls_orm.CLS_ZS.select()
            u, i = 0, 0
            for it in qt:
                pass
            self._lastLoadZSZDTime = time.time()
            console.writeln_1(console.GREEN, f'[CLS-ZS-ZD] {self.formatNowTime(True)} insert={i} update={u}')
        except Exception as e:
            traceback.print_exc()

    # 个股概念板块，仅更新前后10名的概念指数关联的个股
    def downloadBkGn(self, tag, day = None):
        try:
            # console.writeln_1(console.CYAN, f'[CLS-HyGn] {self.formatNowTime(True)} begin...')
            st = time.time()
            zs = {}
            if not day:
                ts = datetime.datetime.now()
                day = ts.strftime('%Y-%m-%d')
            if type(day) == int:
                day = str(day)
            if len(day) == 8:
                day = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
            def diff(old, new, names):
                flag = False
                for n in names:
                    if getattr(old, n, '') != getattr(new, n, ''):
                        setattr(old, n, getattr(new, n, ''))
                        flag = True
                return flag
            attrs = ('gn', 'gn_code', 'hy', 'hy_code')
            u, i, total = 0, 0, 0
            qr = cls_orm.CLS_ZS_ZD.select().where(cls_orm.CLS_ZS_ZD.day == day).where(cls_orm.CLS_ZS_ZD.pm > 0, cls_orm.CLS_ZS_ZD.pm <= 10)
            exzs = {}
            for obj in qr:
                exzs[obj.code] = obj
            def existsGnBk(c):
                if not c: return False
                for cx in c.split(';'):
                    if cx.strip() in exzs:
                        return True
                return False
            qr = cls_orm.CLS_GNTC.select()
            for obj in qr:
                code = obj.code
                if not existsGnBk(obj.hy_code) and not existsGnBk(obj.gn_code):
                    continue
                info = cls.ClsUrl().loadBkGnOfCode(code, zs)
                total += 1
                if not info:
                    continue
                if obj:
                    if diff(obj, info, attrs):
                        obj.save() # update
                        u += 1
                else:
                    info.save() # create new
                    i += 1
            t = time.time() - st
            t /= 60
            console.writeln_1(console.CYAN, f'[CLS-HyGn] {tag} {self.formatNowTime(True)} check {total}, update {u}, insert {i}, use time: {t :.1f} minutes')
        except Exception as e:
            traceback.print_exc()

    def downloadZT_PanKou(self, tag):
        try:
            rs = self._downloadClsZT()
            full = True
            for r in rs:
                obj = d_orm.ZT_PanKou.get_or_none(day = r['day'], code = r['code'])
                if obj:
                    continue
                pk = cls.ClsUrl().loadPanKou5(r['code'])
                if not pk:
                    full = False
                    continue
                pk = json.dumps(pk)
                d_orm.ZT_PanKou.create(code = r['code'], day = r['day'], info = pk)
            if full:
                self._lastLoadZT_PanKou = time.time()
                console.writeln_1(console.CYAN, f'[Cls-ZT-PanKou] {tag} {self.formatNowTime(True)} ')
        except Exception as e:
            traceback.print_exc()

    # 涨跌停、炸板
    def downloadUpDown(self, tag):
        urls = ['https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=up_pool&way=last_px&sign=a6ab28604a6dbe891cdbd7764799eda1',
                'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=up_open_pool&way=last_px&sign=c178185f9b06e3d9e885ba54a47d68ec',
                'https://x-quote.cls.cn/quote/index/up_down_analysis?app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=down_pool&way=last_px&sign=95d3a7c20bb0313a0bb3445d9faf2d27']
        ok = True
        for url in urls:
            try:
                resp = requests.get(url)
                js = json.loads(resp.text)
                if js['code'] != 200:
                    ok = False
                    continue
                for d in js['data']:
                    if d['is_st']: 
                        continue
                    d['day'] = d['time'][0 : 10]
                    d['time'] = d['time'][11 : ]
                    ex = cls_orm.CLS_UpDown.get_or_none(secu_code = d['secu_code'], day = d['day'])
                    if not ex:
                        obj = cls_orm.CLS_UpDown(**d)
                        if 'type=down_pool' in url:
                            obj.is_down = 1
                        obj.save()
                    else:
                        pass
            except Exception as e:
                print('[downloadUpDown] ', url)
                traceback.print_exc()
        console.writeln_1(console.CYAN, f'[Cls-UpDown] {tag} {self.formatNowTime(True)} ', ('Success' if ok else 'Fail'))
        return ok

def do_reason():
    qr = cls_orm.CLS_ZT.select().where(cls_orm.CLS_ZT.day >= '2024-07-26')
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
    #svr.downloadZS()
    svr.downloadBkGn('[4/7]', 20250508)
    #downloadClsZT()
    #days = ths_iwencai.getTradeDays(100)
    #for day in days:
    #    svr._loadHotTcOfDay(day)
    # svr.loadHotTc(1)
    # svr.downloadZS_ZD('d')
    pass
    #do_reason()