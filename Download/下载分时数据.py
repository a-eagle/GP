import re, peewee as pw
import time, os, platform, sys
from PIL import Image as PIL_Image
import win32gui, win32con , win32api, win32ui # pip install pywin32
import requests, json, hashlib, random, easyocr
import pyautogui

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Download import datafile

def main():
    loader = datafile.DataFileLoader()
    loader.mergeAllMililine()

if __name__ == '__main__':
    main()