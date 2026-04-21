import os, sys, functools, copy, datetime, json, time, traceback
import win32gui, win32con, win32api

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def isLargeScreen():
    sx = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    return sx > 2000

def isSmalScreen():
    return not isLargeScreen()

if not isLargeScreen(): 
    # small screen
    TEXT_SIZE = 14
    INDICATOR_TEXT_SIZE = 14
    INDICATOR_CUSTOM_WIDTH = 80
    INDICATOR_CUSTOM_HEIGHT = 30
    INDICATOR_DAY_HEIGHT = 20
    INDICATOR_THSZT_HEIGHT = 50
    INDICATOR_CLSZT_HEIGHT = 50
    INDICATOR_THSZT_TEXT_SIZE = 12
    INDICATOR_ZSZD_PM_HEIGHT = 50
    INDICATOR_ZS_ZT_NUM_HEIGHT = 80
    INDICATOR_HOT_TEXT_SIZE = 15
    BKGN_VIEW_TEXT_SIZE = 12
    CODE_DEF_TEXT_SIZE = 14
    CODE_TEXT_SIZE = 15
    INDICATOR_RATE_HEIGHT = 60
else:
    # large screen
    TEXT_SIZE = 16
    INDICATOR_TEXT_SIZE = 16
    INDICATOR_CUSTOM_WIDTH = 100
    INDICATOR_CUSTOM_HEIGHT = 35
    INDICATOR_DAY_HEIGHT = 25
    INDICATOR_THSZT_HEIGHT = 50
    INDICATOR_CLSZT_HEIGHT = 70
    INDICATOR_THSZT_TEXT_SIZE = 14
    INDICATOR_ZSZD_PM_HEIGHT = 70
    INDICATOR_ZS_ZT_NUM_HEIGHT = 90
    INDICATOR_HOT_TEXT_SIZE = 17
    BKGN_VIEW_TEXT_SIZE = 14
    CODE_DEF_TEXT_SIZE = 16
    CODE_TEXT_SIZE = 17
    INDICATOR_RATE_HEIGHT = 80