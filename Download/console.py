import os, sys, io
from ctypes import pointer, Structure, windll
from ctypes.wintypes import WORD, SHORT, SMALL_RECT
import ctypes

os.system('') # fix win10 下console 颜色不生效bug

BLACK, RED, GREEN, YELLOW, BLUE, PURPLE, CYAN, WHITE = 0, 1, 2, 3, 4, 5, 6, 7
# PURPLE = 5 # 紫色
# CYAN = 6 # 青
F_CLOSE = 0 # 关闭所有格式，还原为初始状态
F_BOLD = 1 # 高亮显示
F_OBSCURE = 2 # 模糊
F_ITALIC = 3  # 斜体
F_UNDERLINE = 4 # 下划线
F_SLOW_FLASH = 5 # 闪烁（慢)
F_FAST_FLASH = 6 # 闪烁（快)
F_EXCHANGE = 7 # 交换背景色与前景色
F_HIDE = 8 # 隐藏

def write_1(color, *args):
    print(f'\033[{30 + color}m', *args, '\033[0m', end='')

def writeln_1(color, *args):
    print(f'\033[{30 + color}m', *args, '\033[0m')

def writeln_2(color, bgColor, *args):
    print(f'\033[{30 + color};{40 + bgColor}m', *args, '\033[0m')

def write_2(color, bgColor, *args):
    print(f'\033[{30 + color};{40 + bgColor}m', *args, '\033[0m', end='')    

def writeln_3(font, color, bgColor, *args):
    print(f'\033[{font};{30 + color};{40 + bgColor}m', *args, '\033[0m')

def write_3(font, color, bgColor, *args):
    print(f'\033[{font};{30 + color};{40 + bgColor}m', *args, '\033[0m', end='')

#Console.write2( Console.YELLOW, Console.BLACK, 'Hello', 'World AA')
#Console.write3(Console.F_HIDE, Console.RED, Console.BLACK, 'Hello', 'World BB')

logFiles = {}
def log(*args, sep = ' ', endle = '\n', file = 'console.log'):
    path = os.path.dirname(os.path.dirname(__file__))
    path = os.path.join(path, file)
    if file not in logFiles:
        logFiles[file] = open(path, 'a', encoding = 'utf-8')
    buf = io.StringIO()
    for idx, a in enumerate(args):
        buf.write(str(a))
        if idx != len(args) - 1:
            buf.write(sep)
    buf.write(endle)
    fs = logFiles[file]
    fs.write(buf.getvalue())
    fs.flush()

class COORD(Structure):
    _fields_ = [("x", SHORT), ("y", SHORT)]
    def __init__(self, x, y):
        self.x = x
        self.y = y

class CONSOLE_SCREEN_BUFFER_INFO(Structure):
    _fields_ = [("dwSize", COORD), ("dwCursorPosition", COORD),
                ("wAttributes", WORD), ("srWindow", SMALL_RECT),
                ("dwMaximumWindowSize", COORD)]

STD_INPUT_HANDLE = -10
STD_OUTPUT_HANDLE = -11
STD_ERROR_HANDLE = -12

def setCursorPos(x, y):
    hOut = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    ctypes.windll.kernel32.SetConsoleCursorPosition(hOut, COORD(x, y))

def getCursorPos():
    csbi = CONSOLE_SCREEN_BUFFER_INFO()
    hOut = ctypes.windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(hOut, pointer(csbi))
    return csbi.dwCursorPosition.x, csbi.dwCursorPosition.y


if __name__ == '__main__':
    log('Hello world', 15, {'name': 'SEEDDK', 'old': 30})
    pass