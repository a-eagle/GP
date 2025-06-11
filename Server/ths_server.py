import peewee as pw
import threading
import requests, json, traceback
import datetime, time, sys, os, re


sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import d_orm, ths_orm, cls_orm
from download import henxin, console, ths_iwencai
from utils import hot_utils

class Server:
    def __init__(self) -> None:
        self.last_zt_time = 0
        self.last_zs_time = 0
        self.last_dde_time = 0
        self.last_hot_time = 0
        self.last_hotzh_time = 0
        self.downloadInfos = {}
        
    def formatZtTime(self, ds):
        if not ds:
            return None
        ds = float(ds)
        sc = time.localtime(ds)
        f = f'{sc.tm_hour :02d}:{sc.tm_min :02d}:{sc.tm_sec :02d}'
        return f

    def formatNowTime(self, hasDay):
        ts = datetime.datetime.now()
        if hasDay:
            return ts.strftime('%Y-%m-%d %H:%M')
        return ts.strftime('%H:%M')

    # 下载同花顺涨停信息(分页下载)
    # day = YYYYMMDD
    # pageIdx = 1, 2 ....
    def downloadOnePageZT(self, day, pageIdx):
        today = datetime.date.today()
        today = today.strftime('%Y%m%d')
        PAGE_SIZE = 50
        ct = int(time.time() * 1000)
        pday = "" if day == today else day
        url = f'https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?page={pageIdx}&limit={PAGE_SIZE}&field=199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004&filter=HS,GEM2STAR&date={pday}&order_field=330324&order_type=0&_={ct}'
        hx = henxin.Henxin()
        hx.init()
        param = hx.update()
        session = requests.Session()
        session.headers = {
            'Accept': 'text/plain, */*; q=0.01',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html',
            'Cookie': 'v=' + param
        }
        resp = session.get(url)
        if resp.status_code != 200:
            print('[ths_zt_downloader.downloadOne] Error:', resp)
            raise Exception()
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        if js['status_code'] != 0:
            print('[ths_zt_downloader.downloadOne] Json Fail 1: ', js, day)
            raise Exception()
        data = js['data']
        total = data['page']['total']
        curPage = data['page']['page']
        pageCount = data['page']['count']
        date = data['date']
        infos = data['info']
        date = date[0 : 4] + '-' + date[4 : 6] + '-' + date[6 : 8]
        ds = {}
        for it in infos:
            status = it['high_days'] or ''
            matchObj = re.match('^(\d+)天(\d+)板$', status)
            if matchObj:
                t = matchObj.group(1)
                b = matchObj.group(2)
                if t == b:
                    status = t + '板'
            ds[it['code']] = {'code': it['code'], 'name': it['name'], 'ztReason': it['reason_type'],
                            'status': status, 'day': date, 'ztTime': self.formatZtTime(it['first_limit_up_time'])}
        rs = {'total': total, 'day': date, 'curPage':curPage, 'pageCount':pageCount, 'data': ds}
        return rs

    # 下载同花顺涨停信息
    # day = int, str, date, datetime
    def downloadOneDayZT(self, day):
        datas = {}
        if type(day) == int:
            day = str(day)
        elif type(day) == str:
            day = day.replace('-', '')
        elif isinstance(day, datetime.date):
            day = day.year * 10000 + day.month * 100 + day.day
        curPage = 1
        pageCount = 1
        while curPage <= pageCount:
            rs = self.downloadOnePageZT(day, curPage)
            datas.update(rs['data'])
            pageCount = rs['pageCount']
            curPage += 1
        return datas

    # 保存同花顺涨停信息
    def saveZT(self, day, datas):
        insertNum, updateNum = 0, 0
        # save to db
        for k in datas:
            it = datas[k]
            if not it['ztReason'] or it['ztReason'] == '其它':
                continue
            obj = ths_orm.THS_ZT.get_or_none(day = it['day'], code=it['code'])
            if not obj:
                it['name'] = it['name'].replace(' ', '')
                ths_orm.THS_ZT.create(**it)
                insertNum += 1
                continue
            if obj.status != it['status'] or obj.ztReason != it['ztReason']:
                #print('old:', obj.status, obj.ztReason)
                #print('new:', it['status'], it['ztReason'])
                if it['status']:
                    obj.status = it['status']
                if it['ztReason']:
                    obj.ztReason = it['ztReason']
                obj.updateTime = datetime.datetime.now()
                obj.save()
                updateNum += 1
        if insertNum or updateNum:
            console.writeln_1(console.YELLOW, f'[THS-zt] {self.formatNowTime(False)}', f'{day} insert {insertNum}, update {updateNum}')

    def downloadSaveOneDayTry(self, day):
        try:
            datas = self.downloadOneDayZT(day)
            self.saveZT(day, datas)
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
        day = day.strftime('%Y%m%d')
        tdays = ths_iwencai.getTradeDays()
        if day in tdays:
            return True
        return False

    def autoLoadHistory(self, fromDay = 20230301):
        fromDay = datetime.date(fromDay // 10000, fromDay // 100 % 100, fromDay % 100)
        one = datetime.timedelta(days = 1)
        today = datetime.date.today()
        while fromDay <= today:
            if self.acceptDay(fromDay):
                self.downloadSaveOneDayTry(fromDay.year * 10000 + fromDay.month * 100 + fromDay.day)
            fromDay += one
            time.sleep(2)

    def downloadSaveHot(self):
        try:
            rs = ths_iwencai.download_hot()
            num = ths_iwencai.save_hot(rs)
            console.write_1(console.RED, f'[hot-server] {self.formatNowTime(False)}')
            if num > 0:
                day = rs[0].day
                _time = f'{rs[0].time // 100}:{rs[0].time % 100 :02d}'
                console.writeln_1(console.RED, f'success, insert {day} {_time} num:{num}')
            else:
                console.writeln_1(console.RED, f'fail ')
            return num > 0
        except Exception as e:
            traceback.print_exc()
        return False

    def downloadSaveVolTop100(self, tag, day = None):
        try:
            rs = ths_iwencai.download_vol_top100(day)
            if not rs:
                return False
            day = rs[0]['day']
            obj = d_orm.HotVol.get_or_none(d_orm.HotVol.day == day)
            if not obj:
                vols = [d['vol'] for d in rs]
                item = d_orm.HotVol()
                item.day = day
                for i in (1, 10, 20, 50, 100):
                    setattr(item, f'p{i}', int(vols[i - 1]))
                rg = [('avg10', 0, 10), ('avg20', 10, 20), ('avg50',20, 50), ('avg100',50, 100)]
                for r in rg:
                    avg = sum(vols[r[1] : r[2]]) / (r[2] - r[1])
                    setattr(item, f'avg{r[1]}_{r[2]}', int(avg))
                item.save()
            console.writeln_1(console.GREEN, f'[Vol-Top100] {tag} {self.formatNowTime(False)}')
            return True
        except Exception as e:
            traceback.print_exc()
            console.writeln_1(console.GREEN, f'[Vol-Top100] {tag} Fail')
        return False

    def downloadSaveZs(self, tag):
        try:
            rs = ths_iwencai.download_zs_zd()
            num = ths_iwencai.save_zs_zd(rs)
            console.write_1(console.GREEN, f'[THS-ZS] {tag} {self.formatNowTime(False)}')
            if rs:
                console.writeln_1(console.GREEN, f"Save ZS success, insert {rs[0].day} num: {num} ")
            else:
                console.writeln_1(console.GREEN, f"Save ZS, no data ")
            return len(rs) > 0
        except Exception as e:
            traceback.print_exc()
            console.writeln_1(console.GREEN, f"Save ZS Fail")
        return False

    def downloadSaveDde(self):
        try:
            rs = ths_iwencai.download_dde_money()
            ok = ths_iwencai.save_dde_money(rs)
            console.write_1(console.PURPLE, f'[THS-DDE] {self.formatNowTime(True)}')
            if ok:
                console.writeln_1(console.PURPLE, 'success, save num: ', len(rs))
            else:
                console.writeln_1(console.PURPLE, 'fail')
            return ok
        except Exception as e:
            traceback.print_exc()
        return False

    def download_hygn(self, tag):
        try:
            upd = ths_iwencai.download_hygn()
            console.writeln_1(console.GREEN, f'[THS-HyGn] {tag} {self.formatNowTime(True)} update {upd}')
            return True
        except Exception as e:
            traceback.print_exc()
            console.writeln_1(console.GREEN, f'[THS-HyGn] {tag} Fail')
        return False

    def download_hygn_ttm(self, tag):
        try:
            ds = ths_iwencai.download_hygn_pe()
            console.writeln_1(console.GREEN, f'[THS-HyGn-PeTtm] {tag} {self.formatNowTime(True)} update {ds}')
            return True
        except Exception as e:
            traceback.print_exc()
            console.writeln_1(console.GREEN, f'[THS-HyGn-PeTtm] {tag} Fail')
        return False

    def download_dt(self, tag, day = None):
        try:
            datas = ths_iwencai.download_zt_dt(day, 'dt')
            unum = 0
            for d in datas:
                if not d['is_down']:
                    continue
                obj = cls_orm.CLS_UpDown.get_or_none(cls_orm.CLS_UpDown.secu_code == d['secu_code'], cls_orm.CLS_UpDown.day == d['day'])
                if obj:
                    obj.up_reason = d['up_reason']
                    obj.updateTime = datetime.datetime.now()
                    obj.save()
                    unum += 1
            console.writeln_1(console.GREEN, f'[THS-DT] {tag} {self.formatNowTime(True)} update {unum}')
            return True
        except Exception as e:
            traceback.print_exc()
            console.writeln_1(console.GREEN, f'[THS-DT] {tag} Fail')
        return False

    def loadOneTime(self):
        now = datetime.datetime.now()
        day = now.strftime('%Y%m%d')
        fday = now.strftime('%Y-%m-%d')
        if not self.acceptDay(now):
            return
        curTime = now.strftime('%H:%M')

        # 下载同花顺涨停信息
        if (curTime >= '09:30' and curTime < '11:40') or (curTime >= '13:00' and curTime <= '17:30'):
            if time.time() - self.last_zt_time >= 5 * 60: # 5分钟
                self.downloadSaveOneDayTry(day)
                self.last_zt_time = time.time()
        # 计算热度综合排名
        if curTime >= '15:05' and (not self.downloadInfos.get(f'zh-hots-{day}', False)):
            self.downloadInfos[f'zh-hots-{day}'] = True
            hot_utils.calcAllHotZHAndSave()
            console.writeln_1(console.GREEN, f'[THS-ZH-hot] [1/5] {self.formatNowTime(False)}', ' calc hot ZH success')
        # 下载成交量前100信息
        if curTime >= '15:05' and not self.downloadInfos.get(f'vol-top100-{day}', False):
            self.downloadInfos[f'vol-top100-{day}'] = True
            self.downloadSaveVolTop100('[2/5]')
        # 下载同花顺指数涨跌信息
        if curTime >= '15:05' and not self.downloadInfos.get(f'zs-{day}', False):
            self.downloadInfos[f'zs-{day}'] = True
            self.downloadSaveZs('[3/5]')
        # 下载个股板块概念信息
        if (curTime >= '15:05') and not self.downloadInfos.get(f'hygn-{day}', False) and now.weekday() == 1: # 每周二
            self.downloadInfos[f'hygn-{day}'] = True
            self.download_hygn('[4/5]')
        # 下载个股PeTTM
        if (curTime >= '20:00') and not self.downloadInfos.get(f'hygn_ttm-{day}', False) and now.weekday() == 2: # 每周三
            ok = self.download_hygn_ttm('')
            self.downloadInfos[f'hygn_ttm-{day}'] = ok
        # 下载个股跌停
        if (curTime >= '22:00') and not self.downloadInfos.get(f'dt-{day}', False):
            ok = self.download_dt('[5/5]')
            self.downloadInfos[f'dt-{day}'] = ok

    def loadHotsOneTime(self):
        now = datetime.datetime.now()
        #day = now.strftime('%Y%m%d')
        if not self.acceptDay(now):
            return
        curTime = now.strftime('%H:%M')

        # 下载热度信息
        if (curTime >= '09:30' and curTime <= '11:30') or (curTime >= '13:00' and curTime <= '15:00'):
            if (now.minute % 5 <= 1) and (time.time() - self.last_hot_time >= 3 * 60):
                self.last_hot_time = time.time()
                self.downloadSaveHot()

if __name__ == '__main__':
    #autoLoadHistory(20240708)
    #downloadOneDay(20240702)
    s = Server()
    # s.downloadSaveVolTop100('[4]', 20250402)
    # ex = []
    # for d in d_orm.HotVol.select():
    #     ex.append(d.day.replace('-', ''))
    # tds = ths_iwencai.getTradeDays(200)
    # for d in tds:
    #     if d in ex:
    #         continue
    #     time.sleep(1)
    #     s.downloadSaveVolTop100(d, d)
    s.download_dt('a', '2025-04-29')

