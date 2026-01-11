import sys, peewee as pw, requests, json, re, traceback, time, datetime, os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from orm import ths_orm, d_orm
from download import henxin, memcache, console

class ThsColumns:
    def __init__(self, item) -> None:
        self.item = None
        self.names = {}
        self._setItem(item)

    def getColumnNames(self, item, partColumnName):
        names = []
        for k in item:
            if partColumnName in k:
                names.append(k)
        return names
    
    def getColumnDay(self, columnName):
        if '[' in columnName:
            b = columnName.index('[')
            e = columnName.index(']')
            return columnName[b + 1 : e]
        return ''
    
    @staticmethod
    def getItemColumnDay(self, item, baseColumnName):
        for k in item:
            if baseColumnName + '[' in k:
                b = k.index('[')
                e = k.index(']')
                return k[b + 1 : e]
        return ''
    
    def _setItem(self, item):
        self.item = item
        self.names.clear()
        for k in item:
            if '[' in k:
                bname = k[0 : k.index('[')]
            else:
                bname = k
            if type(self.names.get(bname, None)) == list:
                self.names[bname].append(k)
            elif self.names.get(bname, None) != None:
                old = self.names[bname]
                self.names[bname] = [old, k]
            else:
                self.names[bname] = k

    def cast(self, val, _type, defaultVal):
        try:
            if val == None:
                return defaultVal
            rs = _type(val)
            if _type == str:
                rs = rs.strip()
            return rs
        except Exception as e:
            pass
            # traceback.print_exc()
            # print('[ths_iwencai.ThsColumns.cast] ', val)
        return defaultVal

    def getColumnValue(self, baseColumnName, _type, defaultVal = '', listValue = False):
        fullName = self.names.get(baseColumnName, None)
        if not fullName:
            return defaultVal
        if type(fullName) == str:
            val = self.cast(self.item[fullName], _type, defaultVal)
            return val
        if type(fullName) == list:
            rs = []
            fullName.sort()
            for n in fullName:
                val = self.cast(self.item[n], _type, defaultVal)
                rs.append((n, val))
            if not listValue:
                return rs[0][1] # use first value
            return rs
        return defaultVal
    
    def getColumnValue_Part(self, partColumnName, _type, defaultVal = ''):
        name = None
        num = 0
        for k in self.item:
            if partColumnName in k:
                name = k
                num += 1
        if num > 1:
            print('[ths_iwencai.ThsColumns.getColumnValue2] not unicode column name: ', partColumnName)
            return defaultVal
        if name and num == 1:
            val = self.cast(self.item[name], _type, defaultVal)
            return val
        return defaultVal

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
    moreUrl = None
    if 'other_info' in components['config']:
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
def iwencai_load_list(question, intent = 'stock', input_type = 'typewrite', maxPage = None, internalTime = 5):
    rs = []
    try:
        data1, urlMore, count = iwencai_load_page_1(question, intent, input_type)
        rs.extend(data1)
        if maxPage is None:
            maxPage = (count + 99) // 100
        if not urlMore:
            maxPage = 1
        for i in range(2, maxPage + 1):
            time.sleep(1)
            datas = iwencai_load_page_n(i, urlMore)
            rs.extend(datas)
            time.sleep(internalTime)
    except Exception as e:
        print('Exception: ', question)
        traceback.print_exc()
    return rs

def modify_hygn_code(obj : ths_orm.THS_GNTC, zsInfos):
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

def modify_hygn_attrs(srcModel, destDict, attrs):
    changed = False
    for a in attrs:
        if getattr(srcModel, a) != destDict[a]:
            setattr(srcModel, a, destDict[a])
            changed = True
    return changed

def hygn_spliter(val : str):
    if not val:
        return []
    sp = val.split(';')
    rs = []
    for s in sp:
        s = s.strip()
        if s:
            rs.append(s)
    return rs

# 个股行业概念
# @return update-datas, insert-datas
def download_hygn():
    rs = iwencai_load_list(question = '个股及行业板块,流通a股,限售股,流通市值,总市值') # ,maxPage = 1
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code
    GP_CODE = ('0', '3', '6')
    ATTRS = ('code', 'name', 'hy', 'gn') #, 'zgb', 'ltag', 'xsg', 'ltsz', 'zsz')
    ATTRS_D = ('code', '股票简称', '所属同花顺行业', '所属概念') #, '总股本', '流通a股', '限售股合计', 'a股市值(不含限售股)', '总市值')
    ATTRS_D_T = (str, str, str, str) #float, float, float, float, float, float)
    DIFF_ATTRS = ('name', 'hy')
    inserts, updates, diffs = [], [], []
    for idx, line in enumerate(rs):
        columns = ThsColumns(line)
        dest = {}
        for idx, a in enumerate(ATTRS):
            dest[a] = columns.getColumnValue(ATTRS_D[idx], ATTRS_D_T[idx])
        if dest['code'][0] not in GP_CODE:
            continue
        obj : ths_orm.THS_GNTC = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == dest['code'])
        if not obj:
            obj = ths_orm.THS_GNTC(**dest)
            modify_hygn_code(obj, zsInfos)
            inserts.append(obj)
        else:
            gncc = obj.gn_code
            diffrents = obj.diff(dest, attrNames = DIFF_ATTRS)
            dfGN = obj.diffAttrOfList('gn', dest['gn'], hygn_spliter)
            if dfGN:
                diffrents['gn'] = dfGN
            if diffrents:
                updates.append(obj)
                modify_hygn_code(obj, zsInfos)
                if 'gn' in diffrents:
                    diffrents['gn_code'] = (gncc, obj.gn_code)
                obj.updateTime = datetime.datetime.now()
                diffRs = d_orm.createDiffBkGn(obj.code, obj.name, diffrents)
                if diffRs:
                    diffs.extend(diffRs)
    
    console.log('inserts-------')
    console.log([d.__data__ for d in inserts])
    console.log('updates-------')
    console.log([d.__data__ for d in updates])
    console.log('diffs-------')
    console.log([d.__data__ for d in diffs])

    if inserts:
        ths_orm.THS_GNTC.bulk_create(inserts, 100)
    if updates:
        UPDATE_ATTRS = (*ATTRS, 'updateTime')
        ths_orm.THS_GNTC.bulk_update(updates, UPDATE_ATTRS, 100)
    if diffs:
        d_orm.DiffBkGnModel.bulk_create(diffs, 100)
    
    return len(inserts), len(updates)

# 个股行业概念 
# return 是否有修改
def download_hygn_by_code(code):
    if type(code) == int:
        code = f'{code :06d}'
    if code[0] not in '036':
        return False
    rs = iwencai_load_list(question = f'{code} 行业,概念,流通市值,总市值') # ,maxPage = 1
    if not rs:
        return False
    info = rs[0]
    ATTRS = ('name', 'hy', 'gn', 'zgb', 'ltsz', 'zsz')
    ATTRS_D = ('股票简称', '所属同花顺行业', '所属概念', '总股本', 'a股市值(不含限售股)', '总市值')
    ATTRS_D_T = (str, str, str, float, float, float, float)
    columns = ThsColumns(info)
    dest = {'code': code}
    for k in info:
        if (k not in ATTRS_D) or (not info[k]):
            continue
        idx = ATTRS_D.index(k)
        dest[ATTRS[idx]] = columns.getColumnValue(ATTRS_D[idx], ATTRS_D_T[idx])
    obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == dest['code'])
    if obj:
        changed = modify_hygn_attrs(obj, dest, ATTRS)
        if 'hy' in obj._dirty or 'gn' in obj._dirty:
            modify_hygn_code_2(obj)
        if changed:
            obj.updateTime = datetime.datetime.now()
            obj.save()
    else:
        obj = ths_orm.THS_GNTC(**dest)
        changed = True
        modify_hygn_code_2(obj)
        obj.save()
    return changed

def modify_hygn_code_2(obj):
    zsInfos = {}
    qr = ths_orm.THS_ZS.select()
    for q in qr:
        zsInfos[q.name] = q.code
    modify_hygn_code(obj, zsInfos)

# download_hygn_by_code('002407')

# 个股信息(市盈率 ttm)
def download_hygn_pe():
    rs = iwencai_load_list(question = '静态市盈率,市盈率(ttm)')
    if not rs:
        return None
    updateNum = 0
    for item in rs:
        columns = ThsColumns(item)
        code = columns.getColumnValue('code', str, '')
        pe = columns.getColumnValue('静态市盈率(中证发布)', float, None)
        peTTM = columns.getColumnValue('市盈率(pe,ttm)', float, None)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if not obj:
            continue
        if obj.peTTM != peTTM or obj.pe != pe:
            obj.updateTime = datetime.datetime.now()
        obj.peTTM = peTTM
        obj.pe = pe
        obj.save()
        updateNum += 1
    return updateNum

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
        # if abs(it.zdf_PM) > 100: # 排名100以后的不看
            # continue
        if it.code not in ex:
            ndatas.append(it)
    ths_orm.THS_ZS_ZD.bulk_create(ndatas, 50)
    return len(ndatas)

# 查找个股近30天的dde信息
#  dde-info = {时间, 股票简称, dde大单净额, dde大单卖出金额, dde大单买入金额, 股票代码, dde大单净量, dde散户数量}
# @return list of dde-info
def download_one_dde(code):
    txt = iwencai_search_info(f'{code}, dde')
    js = json.loads(txt)
    answer = js['data']['answer'][0]
    components = answer['txt'][0]['content']['components']
    datas = components[-1]['data']['datas']
    return datas

# 查找涨停 、炸板、跌停个股
# day = int | str
# tag = 'ZT' | 'DT'
def download_zt_dt(day = None, tag  = None):
    if not day:
        day = ''
    if not tag:
        tag = 'ZT | DT'
    tag = tag.upper()
    if isinstance(day, str):
        day = day.replace('-', '')
    elif isinstance(day, int):
        day = str(day)
    datas, datas2 = [], []
    if 'ZT' in tag:
        qs = day + ' 涨停或者曾涨停,非st,成交额,收盘价,涨跌幅'
        datas = iwencai_load_list(qs) or []
    if 'DT' in tag:
        qs = day + ' 跌停,非st,成交额,收盘价,涨跌幅'
        datas2 = iwencai_load_list(qs) or []
    datas.extend(datas2)
    rs = []
    if not datas:
        return rs
    # find day
    fday = None
    for k in datas[0]:
        if '连续涨停天数[' in k or '连续跌停天数[' in k:
            day = k[k.index('[') + 1 : k.index(']')]
    fday = day[0 : 4] + '-' + day[4 : 6] + '-' +  day[6 : 8]
    for it in datas:
        code = it['code']
        if code[0] not in ('0', '3', '6'):
            continue
        obj = {}
        obj['code'] = it['code']
        if code[0] == '6': obj['secu_code'] = 'sh' + code
        else: obj['secu_code'] = 'sz' + code
        obj['secu_name'] = obj['name'] = it['股票简称']
        obj['day'] = fday
        lbs = it.get(f'连续涨停天数[{day}]', 0)
        dts = it.get(f'连续跌停天数[{day}]', 0)
        obj['limit_up_days'] = lbs
        obj['is_down'] = 1 if dts else 0
        ztTime = it.get(f'首次涨停时间[{day}]', '')
        dtTime = it.get(f'首次跌停时间[{day}]', '')
        obj['time'] = (ztTime or dtTime or '').strip()
        rr = it.get(f'涨停原因类别[{day}]', '')
        rr2 = it.get(f'跌停原因类型[{day}]', '')
        obj['up_reason'] = rr or rr2
        obj['last_px'] = 0
        obj['change'] = 0
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

def getTradeDays(prev = 600):
    try:
        key = f'TradeDays-{prev}'
        item = memcache.cache.getCache(key)
        if item:
            return item
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
        memcache.cache.saveCache(key, rs, 60 * 60)
        return rs
    except Exception as e:
        traceback.print_exc()
    return None

def getTradeDaysInt(prev = 600):
    days = getTradeDays(prev)
    if not days:
        return days
    return [int(d) for d in days]

# 查找前100个股成交量
# day = int | str
def download_vol_top100(day = None):
    if not day:
        day = ''
    if isinstance(day, str):
        day = day.replace('-', '')
    elif isinstance(day, int):
        day = str(day)
    qs = day + ' 成交额从大到小排名前100,且换手率大于5%,非北证'
    datas = iwencai_load_list(qs)
    if not datas:
        return None
    # find day
    rs = []
    fday = None
    for k in datas[0]:
        if '成交额[' in k and ']' in k:
            day = fday = k[4 : k.index(']')]
            fday = fday[0 : 4] + '-' + fday[4 : 6] + '-' +  fday[6 : 8]
            break
    for idx, it in enumerate(datas):
        obj = {}
        obj['code'] = it['code']
        obj['name'] = it['股票简称']
        obj['day'] = fday
        amount = it.get(f'成交额[{day}]', '0')
        obj['vol'] = float(amount) / 100000000 # 亿元
        obj['pm'] = idx + 1
        rs.append(obj)
    return rs

# 近三年净利润
def download_jrl():
    datas = iwencai_load_list('近4年净利润', maxPage = None)
    rs = []
    for idx, it in enumerate(datas):
        obj = {}
        column = ThsColumns(it)
        obj['code'] = it['code']
        obj['name'] = it['股票简称']
        yysl = column.getColumnValue('营业收入', float, listValue = True)
        yyslVal = []
        for y in yysl:
            yd = column.getColumnDay(y[0])
            yyslVal.append((yd, y[1]))
        jrl = column.getColumnValue('归属于母公司所有者的净利润', float, listValue = True)
        jrlVal = []
        for y in jrl:
            yd = column.getColumnDay(y[0])
            jrlVal.append((yd, y[1]))
        yyslVal.sort(key = lambda k: k[0], reverse = True)
        jrlVal.sort(key = lambda k: k[0], reverse = True)
        obj['yysr'] = json.dumps(yyslVal)
        obj['jrl'] = json.dumps(jrlVal)
        rs.append(obj)
    return rs

# 近四季度净利润
def download_jrl_2():
    datas = iwencai_load_list('近4季度净利润', maxPage = None)
    rs = []
    for idx, it in enumerate(datas):
        obj = {}
        column = ThsColumns(it)
        obj['code'] = it['code']
        obj['name'] = it['股票简称']
        jrl = column.getColumnValue('归属于母公司所有者的净利润', float, listValue = True)
        jrlVal = []
        for y in jrl:
            yd = column.getColumnDay(y[0])
            jrlVal.append((yd, y[1]))
        jrlVal.sort(key = lambda k: k[0], reverse = True)
        obj['jrl_2'] = json.dumps(jrlVal)
        rs.append(obj)
    return rs

def isTradeDay():
    lastDay = getTradeDays()[-1]
    today = datetime.date.today().strftime('%Y%m%d')
    return lastDay == today

if __name__ == '__main__':
    from orm import ths_orm
    # ds = download_codes(20250401)
    #iwencai_load_list('个股热度排名<=200且个股热度从大到小排名')
    #num = download_hygn()
    #num2 = download_hygn_pe()

    download_hygn()
    
