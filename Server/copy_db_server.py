import json, os, sys, datetime, threading, time, inspect, platform
import traceback, base64
import requests, json, logging
import peewee as pw, flask, flask_cors

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from download import console

def loadDbFile(fileName):
    print(f'Copy {fileName} ...', end = ' ')
    resp = requests.get(f'http://113.44.136.221:8090/load-db-file/{fileName}')
    txt = resp.content.decode()
    rs = json.loads(txt)
    if rs['status'] != 'OK':
        print('[loadDbFile] Error:', rs)
    bs = base64.b64decode(rs['data'])
    path = __file__[0 : __file__.upper().index('GP') + 2]
    path = os.path.join(path, 'db', fileName)
    f = open(path, 'wb')
    f.write(bs)
    f.close()
    print('--> OK')

def listAllDbFiles():
    resp = requests.get(f'http://113.44.136.221:8090/list-db-files')
    txt = resp.content.decode()
    files = json.loads(txt)
    return files

def loadAllDbFiles():
    files = listAllDbFiles()
    for f in files:
        loadDbFile(f)

if __name__ =='__main__':
    loadAllDbFiles()
    print('-----END---------')
    os.system('pause')