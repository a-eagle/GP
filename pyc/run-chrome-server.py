import win32gui, win32con , win32api, os, sys

import pyd_build
sys.path.append(pyd_build.SRC_ROOT_PATH)
from chrome import chrome_server

if __name__ == '__main__':
    print('Start chrome server')
    svr = chrome_server.Server()
    svr.start()