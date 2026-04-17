import win32gui, win32con , win32api, os, sys

import pyd_build
sys.path.append(pyd_build.SRC_ROOT_PATH)
from Server import sync_db_server

if __name__ == '__main__':
    print('Start db sync server')
    client = sync_db_server.Client()
    client.start()