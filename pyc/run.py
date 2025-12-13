import win32gui, win32con , win32api, os, sys

# import pyc_build
# sys.path.append(pyc_build.DEST_DIR)
from chrome import chrome_server
from Server import sync_db_server

if __name__ == '__main__':
    print('1. Start chrome server')
    print('2. Start db sync server')
    cmd = input('Select index: ')
    if cmd == '1':
        svr = chrome_server.Server()
        svr.start()
    elif cmd == '2':
        client = sync_db_server.Client()
        client.start()