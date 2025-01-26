import peewee as pw
import requests, json, traceback
import datetime, time, sys, os

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import lhb_orm

class Server:
    def __init__(self) -> None:
        self._lastLoadTime = 0
        self.debug = False

    # yyyy-mm-dd
    # return [ {code, name}, ... ]
    def loadOneDayTotal(self, day):
        try:
            url = 'http://page2.tdx.com.cn:7615/TQLEX?Entry=CWServ.tdxsj_lhbd_lhbzl'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
                        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                        'Referer': 'http://page2.tdx.com.cn:7615/site/tdxsj/html/tdxsj_lhbd.html'}
            params = '{' + f"'Params': ['0', '{day}', '1']" + '}'
            orgRes = requests.post(url, data=params, headers = headers)
            txt = orgRes.text
            rs = json.loads(txt)
            if ('ErrorCode' not in rs) or (rs['ErrorCode'] != 0):
                print('Error[loadOneDayTotal]: load tdx long hu bang error. day=', day)
                return None
            infos = rs['ResultSets'][0]['Content']
            v = []
            for it in infos:
                v.append({'code': it[0], 'name': it[1]})
            return v
        except Exception as e:
            traceback.print_exc()
        return []

    def getColInfo(self, colNames : list, cnt : list, name : str):
        idx = colNames.index(name)
        return cnt[idx]

    def isExsitsCnt(self, idx, colNames, title, cnt, cols):
        titleIdx = colNames.index(title)
        cols = [ colNames.index(c) for c in cols ]
        org = cnt[idx]
        for i in range(0, idx):
            cur = cnt[i]
            if cur[titleIdx] != org[titleIdx]:
                continue
            flag = True
            for c in cols:
                if cur[c] != org[c]:
                    flag = False
                    break
            if flag:
                return True
        return False
        
    def loadOneGP(self, code, day, name):
        url = 'http://page2.tdx.com.cn:7615/TQLEX?Entry=CWServ.tdxsj_lhbd_ggxq'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.105 Safari/537.36',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        params = {'Params': ['1', code, day] }
        orgRes = requests.post(url, data=json.dumps(params), headers = headers)
        txt = orgRes.text
        rs = json.loads(txt)
        if ('ErrorCode' not in rs) or (rs['ErrorCode'] != 0):
            print('Error[loadOneGP]: load tdx long hu bang error. day=', day)
            return None
            
        totalInfo = rs['ResultSets'][0]
        # T004(代码), T012（上榜原因）, cjl（成交量）, cje（成交额）, closepri（收盘价）, zdf（涨跌幅）
        totalColNames = totalInfo['ColName']
        totalInfoCnt = totalInfo['Content']

        results = {}
        titlesInfo = {'hasCurDay': False, 'has3Days': False}
        for r in totalInfoCnt:
            title = self.getColInfo(totalColNames, r, 'T012')
            is3 = '累计' in title
            if is3:
                if titlesInfo['has3Days']:
                    continue
                else:
                    titlesInfo['has3Days'] = True
            else:
                if titlesInfo['hasCurDay']:
                    continue
                else:
                    titlesInfo['hasCurDay'] = True
            obj = {'day': day, 'code': code, 'name': name, 
                'price': self.getColInfo(totalColNames, r, 'closepri'), 
                'zd': self.getColInfo(totalColNames, r, 'zdf'),
                #'vol': getColInfo(totalColNames, r, 'cjl'),
                'cjje': self.getColInfo(totalColNames, r, 'cje'), 
                'title': title,
                'mrje': 0, 'mcje': 0, 'jme': 0, 'famous': '', 'famousBuy':'', 'famousSell': '', 'detail': []} # 'mrjeRate': 0, 'mcjeRate': 0,
            results[ title ] = obj

        infos = rs['ResultSets'][1]
        infosColNames = infos['ColName']
        infosCnt = infos['Content']

        def toInt(a):
            return int(a)

        for idx, it in enumerate(infosCnt):
            # 'yz': it[2],
            # ["T007", "T004", "T008", "T009", "T010", "je", "T012", "T006", "T011", "T015", "yxyz", "gsd", "bq1", "bq2", "bq3", "bq4"]
            title = self.getColInfo(infosColNames, it, 'T012')
            if title not in results:
                continue
            curInfo = results[title]

            if self.isExsitsCnt(idx, infosColNames, 'T012', infosCnt, ('T008', 'T009', 'T010')):
                continue
            
            yyb = self.getColInfo(infosColNames, it, 'T008') or ''
            yzDesc = self.getColInfo(infosColNames, it, 'bq1') or ''
            mrje = self.getColInfo(infosColNames, it, 'T009') or 0
            mcje = self.getColInfo(infosColNames, it, 'T010') or 0
            jme = self.getColInfo(infosColNames, it, 'je') or 0
            bs = self.getColInfo(infosColNames, it, 'T006') # 'B' or 'S'
            curInfo['detail'].append({'yyb': yyb, 'yz': yzDesc, 'mrje': toInt(mrje), 'mcje': toInt(mcje), 'jme': toInt(jme), 'bs': bs})
            curInfo['mrje'] += mrje
            curInfo['mcje'] += mcje
            curInfo['jme'] += jme

            if not yzDesc:
                continue
            jme /= 10000
            if bs == 'B':
                famousBuy = f'{yzDesc}(+{jme:.1f}); '
                curInfo['famousBuy'] += famousBuy
            elif bs == 'S':
                famousSell = f'{yzDesc}({jme:.1f}); '
                curInfo['famousSell'] += famousSell

        for k, v in results.items():
            if v['famousBuy'] or v['famousSell']:
                v['famous'] = v['famousBuy'] + ' // ' + v['famousSell']
            del v['famousBuy']
            del v['famousSell']
            #print(curInfo['title'], curInfo['mrje'], curInfo['mcje'], curInfo['jme'], curInfo['famous'], sep=' / ')

        datas = []
        for k in results:
            rs = results[k]
            #rs['mrjeRate'] = int(rs['mrje'] * 100 / rs['cjje'])
            #rs['mcjeRate'] = int(rs['mcje'] * 100 / rs['cjje'])
            rs['mrje'] /= 10000 # 万 -> 亿
            rs['mcje'] /= 10000
            rs['jme'] /= 10000
            rs['cjje'] /= 10000
            rs['detail'] = json.dumps(rs['detail'])
            datas.append(rs)
        return datas

    # yyyy-mm-dd
    def loadOneDayLHB(self, day):
        cc = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.day == day).count()
        result = []
        gps = self.loadOneDayTotal(day)
        if ((not gps) or (cc == len(gps))):
            return True

        q = lhb_orm.TdxLHB.select().where(lhb_orm.TdxLHB.day == day)
        oldDatas = [d.code for d in q]

        for gp in gps:
            if gp['code'] in oldDatas:
                continue
            scode = gp['code'][0]
            if scode != '3' and scode != '0' and scode != '6':
                continue
            r = self.loadOneGP(gp['code'], day, gp['name'])
            result.extend(r)
        with lhb_orm.db_lhb.atomic():
            for batch in pw.chunked(result, 10):
                dd = lhb_orm.TdxLHB.insert_many(batch)
                dd.execute()
        if len(result) > 0:
            lt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            print(f'[LHB] {lt} Success insert  {len(result)} rows for day {day}')
        return True

    #runLock = threading.RLock()
    def loadTdxLHB(self, dayFrom = None):
        if not dayFrom:
            dayFrom = datetime.date(2023, 1, 1)
        cursor = lhb_orm.db_lhb.cursor()
        rs = cursor.execute('select min(日期), max(日期) from tdxlhb').fetchall()
        rs = rs[0]
        if rs[0]:
            minDay = datetime.datetime.strptime(rs[0], '%Y-%m-%d').date()
            maxDay = datetime.datetime.strptime(rs[1], '%Y-%m-%d').date()
        else:
            minDay = dayFrom
            maxDay = dayFrom

        today = datetime.date.today()
        delta = datetime.timedelta(days=1)
        while dayFrom  <= today:
            if dayFrom.isoweekday() >= 6:
                dayFrom = dayFrom + delta
                continue
            if dayFrom < maxDay:
                #print('Skip ' + str(dayFrom))
                pass
            else:
                #print('Load day ' + str(dayFrom))
                self.loadOneDayLHB(dayFrom.strftime('%Y-%m-%d'))
                time.sleep(1.2)
            dayFrom = dayFrom + delta
    
    def loadOneTime(self):
        try:
            if time.time() - self._lastLoadTime <= 20 * 60:
                return
            self._lastLoadTime = time.time()
            now = datetime.datetime.now()
            curTime = now.strftime('%H:%M')
            if now.isoweekday() < 6 and curTime > '15:00' and curTime < '21:00': # 周一至周五, 晚上8点
                self.loadTdxLHB()
        except Exception as e:
            traceback.print_exc()

    
if __name__ == '__main__':
    svr = Server()
    svr.debug = True
    #svr.loadOneGP('000062', '2024-08-20', '深圳华强')
    svr.loadTdxLHB(datetime.date(2023, 1, 1))

    