import sys, peewee as pw, requests, json, re, traceback, time, datetime

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from orm import ths_orm
from Download import henxin, memcache

def iwencai_search_info(question, intent = 'stock', input_type = 'typewrite'):
    url = 'http://www.iwencai.com/customized/chart/get-robot-data'
    data = {
        'source': 'Ths_iwencai_Xuangu',
        'version': '2.0',
        'query_area': '',
        'block_list': '',
        'add_info' : '{"urp":{"scene":1,"company":1,"business":1},"contentType":"json","searchInfo":true}',
        'question': question,
        'perpage': '100',
        'page': 1,
        'secondary_intent': intent,
        'log_info': '{"input_type":"' + input_type + '"}',
    }
    hx = henxin.Henxin()
    hx.init()
    hexin_v = hx.update()
    headers = {'Accept': 'application/json, text/plain, */*',
                'hexin-v': hexin_v,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/json',
                'Pragma': 'no-cache',
                'Cache-control': 'no-cache',
                'Origin': 'http://www.iwencai.com',
                #'Referer': 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E5%8F%8A%E8%A1%8C%E4%B8%9A%E6%9D%BF%E5%9D%97&querytype=stock',
                }
    #pstr = json.dumps(data, ensure_ascii = False)
    resp = requests.post(url, json = data, headers = headers)
    txt = resp.text
    #f = open('D:/a.json', 'w')
    #f.write(txt)
    #f.close()
    return txt

# 在 i问财搜索结果，(第一面的数据) 列表形的数据
# 例： question = '个股及行业板块' -->  http://www.iwencai.com/unifiedwap/result?w=个股及行业板块&querytype=stock
# @return 数据:list, more-url: str, 结果数量: int
# intent = 'stock' | 'zhishu' 用于指明是个股还是指数
# input_type = 'typewrite' | 'click'   typewrite: 点击搜索的方式查询   click:在url地址上附加查询参数的方式查询
def iwencai_load_page_1(question, intent = 'stock', input_type = 'typewrite'):
    txt = iwencai_search_info(question, intent, input_type)
    js = json.loads(txt)
    answer = js['data']['answer'][0]
    components = answer['txt'][0]['content']['components'][0]
    data = components['data']
    meta = data['meta']
    count = meta['extra']['code_count']
    #info = {'ret': meta['ret'], 'sessionid': meta['sessionid'], 'source': meta['source'], 'logid': js['logid'],
    #        }
    moreUrl = components['config']['other_info']['footer_info']['url']
    moreUrl = 'http://www.iwencai.com' + moreUrl
    ma = re.match('^(.*?perpage=)\d+(.*)$', moreUrl)
    moreUrl = ma.group(1) + '100' + ma.group(2)
    ma = re.match('^(.*?[&?]page=)\d+(.*)$', moreUrl)
    moreUrl = ma.group(1) + '###' + ma.group(2)
    return data['datas'], moreUrl, count

# 按页下载个股数据，每页100个（共5400余个股票）
# page = [2...54] 从第二页开始
def iwencai_load_page_n(page : int, moreUrl):
    url = moreUrl.replace('###', str(page))
    hx = henxin.Henxin()
    hx.init()
    headers = {'Accept': 'application/json, text/plain, */*',
                'hexin-v': hx.update(),
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Encoding': 'gzip, deflate',
                'Pragma': 'no-cache',
                'Cache-control': 'no-cache',
                'content-type': "application/x-www-form-urlencoded",
                'Origin': 'http://www.iwencai.com',
                }
    body = ''
    if '?' in url:
        iq = url.index('?')
        body = url[iq + 1 : ]
        url = url[0 : iq]
    resp = requests.post(url, headers = headers, data = body)
    txt = resp.text
    js = json.loads(txt)
    data = js['answer']['components'][0]['data']
    columns = data['columns']
    datas = data['datas']
    return datas

# 在 i问财搜索结果，返回所有页的数据
# 例： question = '个股及行业板块' -->  http://www.iwencai.com/unifiedwap/result?w=个股及行业板块&querytype=stock
# intent = 'stock' | 'zhishu' 用于指明是个股还是指数
# input_type = 'typewrite' | 'click'
# maxPage = int | None(all pages)
# @return list
def iwencai_load_list(question, intent = 'stock', input_type = 'typewrite', maxPage = None):
    rs = []
    try:
        data1, urlMore, count = iwencai_load_page_1(question, intent, input_type)
        rs.extend(data1)
        if maxPage is None:
            maxPage = (count + 99) // 100
        for i in range(2, maxPage + 1):
            datas = iwencai_load_page_n(i, urlMore)
            rs.extend(datas)
            time.sleep(1)
    except Exception as e:
        print('Exception: ', question)
        traceback.print_exc()
    return rs

def modify_hygn(obj : ths_orm.THS_GNTC, zsInfos):
    gn_code = []
    for g in obj.gn.split(';'):
        gcode = zsInfos.get(g, '')
        gn_code.append(gcode)
    gn_code = ';'.join(gn_code)
    hys = obj.hy.split('-')
    hy_2_code = zsInfos.get(hys[1], '')
    hy_3_code = zsInfos.get(hys[2], '')
    obj.gn_code = gn_code
    obj.hy_2_code = hy_2_code
    obj.hy_3_code = hy_3_code
    obj.hy_2_name = hys[1]
    obj.hy_3_name = hys[2]

# 个股行业概念
# @return update-datas, insert-datas
def download_hygn():
    # 下载所有的 个股行业概念（含当日涨跌信息）
    # code 市盈率(pe)[20240708],  总股本[20240708]  所属概念  所属同花顺行业  最新涨跌幅  最新价 股票简称  总市值[20240717] a股市值(不含限售股)[20240717]
    rs = iwencai_load_list(question = '个股及行业板块,总市值,流通市值,pe,ttm')
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code
    updates = []
    inserts = []
    GP_CODE = ('0', '3', '6')
    for idx, line in enumerate(rs):
        code, name, hy, gn = line['code'], line['股票简称'], line.get('所属同花顺行业'), line.get('所属概念', '')
        if code[0] not in GP_CODE:
            continue
        zsz, ltsz = 0, 0
        for k in line:
            if '总市值' in k: zsz = int(float(line[k])) // 100000000
            elif 'a股市值' in k: ltsz = int(float(line[k])) // 100000000
        hy = hy.strip() if hy else ''
        gn = gn.strip() if gn else ''
        gns = gn.split(';')
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if obj:
            if obj.zsz != zsz or obj.ltsz != ltsz:
                obj.zsz = zsz
                obj.ltsz = ltsz
                obj.save()
            ch = False
            if obj.hy != hy and hy:
                obj.hy = hy
                ch = True
            if obj.gn != gn and gn:
                obj.gn = gn
                ch = True
            if obj.name != name and name:
                obj.name = name
                ch = True
            if ch == True:
                modify_hygn(obj, zsInfos)
                updates.append(obj)
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy, zsz = zsz, ltsz = ltsz)
            modify_hygn(obj, zsInfos)
            inserts.append(obj)
    return updates, inserts

# @return (update-num, insert-num)
def save_hygn(updateDatas, insertDatas):
    for it in updateDatas:
        it.save()
    for it in insertDatas:
        it.save()
    return len(updateDatas), len(insertDatas)


# dde大单净额
# @return data : list (前100 + 后100)
def download_dde_money():
    亿 = 100000000
    rs, *_ = iwencai_load_page_1('个股及行业板块, 最新dde大单净额,按dde净额从大到小排序')
    rs2, *_ = iwencai_load_page_1('个股及行业板块, 最新dde大单净额,按dde净额从小到大排序')
    rs.extend(rs2)
    datas = []
    for row in rs:
        obj = ths_orm.THS_DDE()
        datas.append(obj)
        for k in row:
            v = row[k]
            if k == 'code': obj.code = v
            elif k == '股票简称': obj.name = v
            elif k.startswith('dde大单净额['):
                obj.dde = float(v) / 亿
                day = k[8 : 16]
                obj.day = day[0 : 4] + '-' + day[4 : 6] + '-' + day[6 : 8]
            elif 'dde大单卖出金额' in k: obj.dde_sell = float(v) / 亿
            elif 'dde大单买入金额' in k: obj.dde_buy = float(v) / 亿

    datas.sort(key = lambda d: d.dde, reverse = True)
    ndatas = []
    for i in range(100):
        datas[i].dde_pm = i + 1
        ndatas.append(datas[i])
    for i in range(-1, -101, -1):
        datas[i].dde_pm = i
        ndatas.append(datas[i])
    return ndatas

def save_dde_money(rs):
    if not rs:
        return False
    day = rs[0].day
    count = ths_orm.THS_DDE.select(pw.fn.count()).where(ths_orm.THS_DDE.day == day).scalar()
    if count > 0:
        return False # alreay exists
    ths_orm.THS_DDE.bulk_create(rs, 50)
    return True

# 个股热度排名
# http://www.iwencai.com/unifiedwap/result?w=个股热度排名<%3D200且个股热度从大到小排名&querytype=stock
# code, 股票简称, 个股热度[20240709], 个股热度排名[20240709]
def download_hot():
    rs = iwencai_load_list('个股热度排名<=200且个股热度从大到小排名')
    now = datetime.datetime.now()
    _time = now.hour * 100 + now.minute
    hots = []
    for row in rs:
        obj = ths_orm.THS_Hot()
        obj.time = _time
        for k in row:
            if k == 'code': obj.code = int(row[k])
            elif '个股热度排名[' in k:
                obj.day = int(k[7 : 15])
                v = row[k]
                obj.hotOrder = int(v[0 : v.index('/')])
            elif '个股热度[' in k:
                obj.hotValue = int(row[k]) // 10000
        #c0 = f'{obj.code :06d}'[0]
        #if c0 in ('0', '3', '6'):
        hots.append(obj)
    return hots

# @return 数量
def save_hot(hots):
    ths_orm.THS_Hot.bulk_create(hots, 50)
    return len(hots)

# 指数涨跌信息
# http://www.iwencai.com/unifiedwap/result?w=同花顺概念指数或同花顺行业指数按涨跌幅排序&querytype=zhishu
# @return  data : list
# code, 指数简称, 指数@涨跌幅:前复权[20240709]
def download_zs_zd():
    rs = iwencai_load_list('同花顺概念指数或同花顺行业指数按涨跌幅排序', 'zhishu', 'click')
    datas = []
    亿 = 100000000
    RK = '指数@涨跌幅:前复权['
    for row in rs:
        obj = ths_orm.THS_ZS_ZD()
        datas.append(obj)
        for k in row:
            if k == 'code': obj.code = row[k]
            elif k == '指数简称': obj.name = row[k]
            elif RK in k:
                day = k[len(RK) : len(RK) + 8]
                obj.day = f'{day[0 : 4]}-{day[4 : 6]}-{day[6 : 8]}'
                obj.zdf = float(row[k])
            elif '成交量' in k: obj.vol = int(float(row[k]) / 亿)
            elif '成交额' in k: obj.money = int(float(row[k]) / 亿)
            elif '开盘价' in k: obj.open = float(row[k])
            elif '最高价' in k: obj.high = float(row[k])
            elif '收盘价' in k: obj.close = float(row[k])
            elif '换手率' in k: obj.rate = float(row[k])
    return datas

def save_zs_zd(datas):
    for i in range(len(datas)):
        if i <= len(datas) // 2:
            datas[i].zdf_PM = i + 1
        else:
            datas[i].zdf_PM = i - len(datas)
    subGn = ('AIGC概念', 'ChatGP概念', 'MLOps概念', 'MCU芯片', '中芯国际概念', '光刻胶', 'EDR概念', '比亚迪概念', '钠离子电池',
             '钒电池', 'PVDF概念', '高压快冲', '血氧仪', '智能家居', '智能音箱', '智能穿戴', '无线耳机', '核电', '光热发电',
             '风电', '光伏概念', '光伏建筑', '钙钛矿电池', 'TOPCON电池', 'HJT电池', '超超临界发电', '生物质能发电',
             '数据中心', '信创', '网络安全', '国产操作系统', '数字货币', '数字乡村')
    topLevels = [d for d in datas if d.code[0 : 3] != '884' and (d.name not in subGn)]
    for i in range(len(topLevels)):
        if i <= len(topLevels) // 2:
            topLevels[i].zdf_topLevelPM = i + 1
        else:
            topLevels[i].zdf_topLevelPM = i - len(topLevels)
    day = datas[0].day
    q = ths_orm.THS_ZS_ZD.select().where(ths_orm.THS_ZS_ZD.day == day).dicts()
    ex = {}
    for it in q:
        ex[it['code']] = True
    ndatas = []
    for it in datas:
        if it.code not in ex:
            ndatas.append(it)
    ths_orm.THS_ZS_ZD.bulk_create(ndatas, 50)
    return len(ndatas)

# 查找个股近30天的dde信息
#  dde-info = {时间, 股票简称, dde大单净额, dde大单卖出金额, dde大单买入金额, 股票代码, dde大单净量, dde散户数量}
# @return list of dde-info
def download_one_dde(code):
    KIND = 'DDE'
    if not memcache.cache.needUpdate(code, KIND):
        return memcache.cache.getCache(code, KIND)
    txt = iwencai_search_info(f'{code}, dde')
    js = json.loads(txt)
    answer = js['data']['answer'][0]
    components = answer['txt'][0]['content']['components']
    datas = components[-1]['data']['datas']
    memcache.cache.saveCache(code, datas, KIND)
    return datas

# 查找涨停或炸板个股
# day = int | str
def download_zt_zb(day = None):
    if not day:
        day = ''
    if isinstance(day, str):
        day = day.replace('-', '')
        day = int(day)
    qs = ''
    if day:
        y, m, d = day // 10000, day // 100 % 100, day % 100
        qs = f'{y}年{m}月{d}日'
    qs += '涨停或者曾涨停,非st,成交额'
    datas = iwencai_load_list(qs)
    if not datas:
        return None
    # find day
    rday = None
    for k in datas[0]:
        if '首次涨停时间[' in k:
            rday = k[len('首次涨停时间[') : k.index(']')]
            break
    if not rday:
        print('Error [ths_iwencai].download_zt_zb not find day')
        return None
    rs = []
    fday = rday[0 : 4] + '-' + rday[4 : 6] + '-' +  rday[6 : 8]
    for it in datas:
        code = it['code']
        if code[0] not in ('0', '3', '6'):
            continue
        obj = {}
        obj['code'] = it['code']
        obj['day'] = fday
        a = it.get(f'曾涨停[{rday}]', None)
        obj['tag'] = '炸板' if a else '涨停'
        obj['lbs'] = it.get(f'几天几板[{rday}]', '')
        obj['name'] = it['股票简称']
        obj['lastZtTime'] = it.get(f'最终涨停时间[{rday}]', '')
        obj['firstZtTime'] = it.get(f'首次涨停时间[{rday}]', '')
        obj['kbs'] = int(it.get(f'涨停开板次数[{rday}]', 0))
        obj['reason'] = it.get(f'涨停原因类别[{rday}]', '')
        m = it.get(f'涨停封单额[{rday}]', None)
        obj['ztMoney'] = float(m) / 100000000 if m else None
        obj['ltsz'] = int(float(it.get(f'a股市值(不含限售股)[{rday}]', 0)) / 100000000) # 亿元
        obj['amount'] = int(float(it.get(f'成交额[{rday}]', 0))) // 100000000 # 亿元
        obj['vol'] = int(float(it.get(f'成交量[{rday}]', 0))) # 手
        rs.append(obj)
    return rs

# 连板天梯
def download_zt_lianban(day = None):
    if type(day) == str:
        day = day.replace('-', '')
    if day is None:
        day = ''
    try:
        url = f'https://data.10jqka.com.cn/dataapi/limit_up/continuous_limit_up?filter=HS,GEM2STAR&date={day}'
        resp = requests.get(url)
        if resp.status_code != 200:
            return None
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        if js['status_code'] != 0:
            print('[ths_iwencai.download_lianban] Error: ', js['status_msg'])
            return None
        data = js['data']
        return data
    except Exception as e:
        traceback.print_exc()
    return None

def getTradeDays(prev = 60):
    try:
        today = datetime.date.today()
        today = today.strftime('%Y%m%d')
        url = f'http://data.10jqka.com.cn/dataapi/limit_up/trade_day?date={today}&stock=stock&next=1&prev={prev}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3'
        }
        resp = requests.get(url, headers = headers)
        txt = resp.content.decode('utf-8')
        js = json.loads(txt)
        data = js['data']
        rs = data['prev_dates']
        if data['trade_day']:
            rs.append(today)
        return rs
    except Exception as e:
        traceback.print_exc()
    return None

def getTradeDays_Cache(prev = 60):
    CODE = f'TradeDays-{prev}'
    KIND = '30-minuts'
    if not memcache.cache.needUpdate(CODE, KIND):
        ca = memcache.cache.getCache(CODE, KIND)
        return ca
    rs = getTradeDays(prev)
    if rs:
        memcache.cache.saveCache(CODE, rs, KIND)
    return rs


if __name__ == '__main__':
    # data = iwencai_load_list('个股成交额排名, 20250312', maxPage = 2)
    ds = getTradeDays_Cache()
    print(ds)
    pass