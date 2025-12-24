import win32gui, win32con , win32api, os, sys

# import pyc_build
# sys.path.append(pyc_build.DEST_DIR)
from chrome import chrome_server
from Server import sync_db_server

if __name__ == '__main__':
    print('Start db sync server')
    client = sync_db_server.Client()
    client.start()