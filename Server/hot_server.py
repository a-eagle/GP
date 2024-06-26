from flask import Flask, url_for, views, abort, make_response, request
# pip install  psutil
import psutil, time, os, threading, datetime
import flask, peewee as pw
import json, os, sys
from flask_cors import CORS 
import traceback
import logging
from multiprocessing import Process

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm
from THS import hot_utils
from Common import holiday
from Download import console

# 热点股票信息
def saveHot():
    hotDay = request.json.get('hotDay')
    hotTime = request.json.get('hotTime')
    hotInfos = request.json.get('hotInfo')

    if holiday.isHoliday(hotDay):
        return {"status": "OK", "msg" : f"{hotDay} is holiday, skip this"}

    for hi in hotInfos:
        hi['day'] = int(hotDay.replace('-', ''))
        hi['time'] = int(hotTime.replace(':', ''))
        hi['code'] = int(hi['code'])
        del hi['name']

    with ths_orm.db_hot.atomic():
        for i in range(0, len(hotInfos), 20):
            ths_orm.THS_Hot.insert_many(hotInfos[i : i + 20]).execute()
    lt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    console.write_1(console.RED, f'[hot-server] ')
    print(f'{lt} saveHot success, insert {hotDay} {hotTime} num:{len(hotInfos)}')
    return {"status": "OK"}

# 热点股票信息
def getHot(code): 
    datas = ths_orm.THS_Hot.select(ths_orm.THS_Hot.day, ths_orm.THS_Hot.time, ths_orm.THS_Hot.hotValue, ths_orm.THS_Hot.hotOrder).where(ths_orm.THS_Hot.code == code)
    nd = [d.__data__ for d in datas]
    return nd

def check_chrome_open():
    try:
        for pid in psutil.pids():
            p = psutil.Process(pid)
            if p.name() == 'chrome.exe':
                return True
    except Exception as e:
        print('[hot_server.check_chrome_open] exception: ', e)
    return True

def sub_process():
    print('in sub_process')
    while True:
        if not check_chrome_open():
            os.startfile('https://cn.bing.com/')
        time.sleep(60 * 5) # 5 minutes
        checkRunCalcHotZH()

def checkRunCalcHotZH():
    now = datetime.datetime.now()
    ts = now.strftime('%H:%M')
    if ts <= '15:05' or ts >= '16:00':
        return
    hot_utils.calcAllHotZHAndSave()

def getMoreHotOrders():
    lastDay = request.args.get('lastDay')
    num = request.args.get('num')
    if not lastDay or lastDay == '0':
        lastDay = datetime.date.today().strftime('%Y%m%d')
    lastDay = int(lastDay)
    num = 200 if not num else int(num)
    q = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.day).distinct().order_by(ths_orm.THS_HotZH.day.desc()).tuples()
    existsDays = [d[0] for d in q]
    hotLastDay = ths_orm.THS_Hot.select(pw.fn.max(ths_orm.THS_Hot.day)).scalar()
    rs = []
    if (lastDay >= hotLastDay) and (hotLastDay not in existsDays):
        nn = hot_utils.calcHotZHOnDay(hotLastDay)[0 : num]
        news = []
        for d in nn:
            name = hot_utils.getNameByCode(d['code'])
            if not name:
                name = f"{d['code'] :06d}"
            news.append(name)
        rs.append({'day': hotLastDay, 'codes': news})
    DAYS_NUM = 5
    for fromIdx, d in enumerate(existsDays):
        if d <= lastDay:
            break
    for i in range(0, DAYS_NUM - len(rs)):
        if i + fromIdx >= len(existsDays):
            break
        day = existsDays[i + fromIdx]
        news = []
        qd = ths_orm.THS_HotZH.select(ths_orm.THS_HotZH.code).where(ths_orm.THS_HotZH.day == day).order_by(ths_orm.THS_HotZH.zhHotOrder.asc()).limit(num).tuples()
        for d in qd:
            name = hot_utils.getNameByCode(d[0])
            if not name:
                name = f"{d[0] :06d}"
            news.append(name)
        rs.append({'day': day, 'codes': news})
    return rs

def saveZS():
    data = request.json
    if len(data) > 0:
        #datas = [orm.THS_ZS_ZD(**d) for d in data]
        num = 0
        for d in data:
            obj = ths_orm.THS_ZS_ZD.get_or_none(code = d['code'], day = d['day'])
            if not obj:
                ths_orm.THS_ZS_ZD.create(**d)
                num += 1
        #orm.THS_ZS_ZD.bulk_create(datas, 100)
        console.write_1(console.GREEN, f'[THS-ZS] ')
        print(f"Save ZS success, insert {data[0]['day']} {num} num")
    else:
        print(f"Save ZS, no data ")
    return {"status": "OK"}

def saveZSFromFile():
    f = open('D:/download/b.json', 'r', encoding = 'utf-8')
    js = json.loads(f.read())
    for item in js:
        ths_orm.THS_ZS_ZD.create(**item)

def startup(app : Flask):
    print('[hot-server]功能: 启动服务, 保存同花顺热点; 保持Chrome始终都启动了。')
    #p = Process(target = sub_process, daemon = True)
    #p.start()
    #print('open check chrome deamon, pid=', p.pid)
    p = threading.Thread(target=sub_process, daemon=True)
    p.start()

    app.add_url_rule('/saveHot', view_func=saveHot, methods=['POST'])
    app.add_url_rule('/getHot/<code>', view_func=getHot,  methods = ['GET'])
    app.add_url_rule('/moreHotOrders', view_func=getMoreHotOrders,  methods = ['GET'])
    app.add_url_rule('/saveZS', view_func=saveZS, methods=['POST'])
