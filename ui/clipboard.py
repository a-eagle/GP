import ctypes, traceback, chardet
import ctypes.wintypes

# Define necessary constants
CF_TEXT = 1
CF_LOCALE = 16
CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040
GHND = GMEM_MOVEABLE | GMEM_ZEROINIT

# Set up the required functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

GlobalAlloc = kernel32.GlobalAlloc
# GlobalAlloc.argtypes = ctypes.wintypes.UINT, ctypes.wintypes.SIZE_T
GlobalAlloc.argtypes = ctypes.wintypes.UINT, ctypes.c_size_t
GlobalAlloc.restype = ctypes.wintypes.HGLOBAL

GlobalLock = kernel32.GlobalLock
GlobalLock.argtypes = ctypes.wintypes.HGLOBAL,
GlobalLock.restype = ctypes.c_void_p

GlobalUnlock = kernel32.GlobalUnlock
GlobalUnlock.argtypes = ctypes.wintypes.HGLOBAL,
GlobalUnlock.restype = ctypes.wintypes.BOOL

memcpy = ctypes.cdll.msvcrt.memcpy
memcpy.argtypes = ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t

GlobalFree = kernel32.GlobalFree
GlobalFree.argtypes = ctypes.wintypes.HGLOBAL,
GlobalFree.restype = ctypes.wintypes.HGLOBAL

OpenClipboard = user32.OpenClipboard
OpenClipboard.argtypes = ctypes.wintypes.HWND,
OpenClipboard.restype = ctypes.wintypes.BOOL

EmptyClipboard = user32.EmptyClipboard
EmptyClipboard.argtypes = None
EmptyClipboard.restype = ctypes.wintypes.BOOL

SetClipboardData = user32.SetClipboardData
SetClipboardData.argtypes = ctypes.wintypes.UINT, ctypes.wintypes.HANDLE
SetClipboardData.restype = ctypes.wintypes.HANDLE

CloseClipboard = user32.CloseClipboard
CloseClipboard.argtypes = None
CloseClipboard.restype = ctypes.wintypes.BOOL

GetClipboardData = user32.GetClipboardData
GetClipboardData.argtypes = ctypes.wintypes.UINT,
GetClipboardData.restype = ctypes.wintypes.HANDLE

# Function to set the clipboard text
def copy(text, encoding = 'utf-8'):
    if text == None:
        text = ''
    if type(text) != str:
        text = str(text)
    try:
        OpenClipboard(None)
        EmptyClipboard()
        # Allocate global memory and lock it
        data = ctypes.create_string_buffer(text.encode(encoding))
        handle = GlobalAlloc(GHND, len(data))
        data_ptr = GlobalLock(handle)
        # Copy data to global memory
        memcpy(data_ptr, ctypes.addressof(data), len(data))
        # Unlock and set clipboard data
        GlobalUnlock(handle)
        SetClipboardData(CF_TEXT, handle)
    except Exception as e:
        traceback.print_exc()
    finally:
        CloseClipboard()

def paste():
    dtxt = ''
    try:
        OpenClipboard(None)
        handle = GetClipboardData(CF_TEXT)
        data = GlobalLock(handle)
        bs = ctypes.c_char_p(data).value
        GlobalUnlock(handle)
        enc = chardet.detect(bs)
        uu = enc['encoding']
        if not uu: uu = 'gb2312'
        dtxt = bs.decode(uu)
    finally:
        CloseClipboard()
    return dtxt

copy('明长起ACCAbc你好吗d')
print(paste())