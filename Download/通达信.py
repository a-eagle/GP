import sys, os, pyautogui, win32gui, win32con, time, datetime
import io, psutil, subprocess, win32process, win32event, win32api, winerror
from pywinauto.controls.common_controls import DateTimePickerWrapper # pip install pywinauto
import peewee as pw

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Tdx import datafile, orm

class TdxVolPMTools:
    def __init__(self):
        fromDay = 20230101
        v = orm.TdxVolPMModel.select(pw.fn.max(orm.TdxVolPMModel.day)).scalar()
        v2 = orm.TdxVolTop50ZSModel.select(pw.fn.max(orm.TdxVolTop50ZSModel.day)).scalar()
        self.fromDay = v if v else fromDay
        self.fromDay2 = v2 if v2 else fromDay
        self.codes = None
        self.codeNames = None
        self.days = None
        self.days2 = None
        self.loadAllCodes()
        self.calcDays()
        self.initCodeName()
        self.datafiles = [datafile.DataFile(c, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL) for c in self.codes]
        
    # 加载所有股标代码（上证、深证股），不含指数、北证股票
    def loadAllCodes(self):
        self.codes = datafile.DataFileUtils.listAllCodes()
    
    def calcDays(self):
        self.days = datafile.DataFileUtils.calcDays(self.fromDay)
        self.days2 = datafile.DataFileUtils.calcDays(self.fromDay2)

    def initCodeName(self):
        ths_db = pw.SqliteDatabase(f'{orm.path}GP/db/THS_F10.db')
        sql = 'select code, name from 最新动态'
        csr = ths_db.cursor()
        csr.execute(sql)
        rs = csr.fetchall()
        codeNames = {}
        for r in rs:
            codeNames[r[0]] = r[1]
        self.codeNames = codeNames
        csr.close()
        ths_db.close()
    
    def save(self, datas):
        orm.TdxVolPMModel.bulk_create(datas, 50)
    
    def calcVolOrder_Top500(self):
        dfs = self.datafiles
        bpd = 0
        def sortKey(df):
            idx = df.getItemIdx(bpd)
            if idx < 0:
                return 0
            return df.data[idx].amount

        for day in self.days:
            bpd = day
            newdfs = sorted(dfs, key = sortKey, reverse=True)
            top500 = []
            for i in range(1000):
                nf = newdfs[i]
                code = nf.code
                di = nf.getItemData(day)
                amount =  (di.amount if di else 0) / 100000000
                name = self.codeNames.get(code)
                if not name:
                    name = 'N'
                d = {'code': code, 'name': name, 'day': day, 'amount': amount, 'pm': i + 1}
                top500.append(orm.TdxVolPMModel(**d))
                #print(d)
            self.save(top500)

    # 计算两市成交总额
    def calcSHSZVol(self):
        sh = datafile.DataFile('999999', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        sz = datafile.DataFile('399001', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        zs = []
        for day in self.days:
            d1 = sh.getItemData(day)
            d2 = sz.getItemData(day)
            amount = (d1.amount + d2.amount) // 100000000
            zs.append(orm.TdxVolPMModel(**{'code': '999999', 'name': '上证指数', 'day': day, 'amount': d1.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '399001', 'name': '深证指数', 'day': day, 'amount': d2.amount // 100000000, 'pm': 0}))
            zs.append(orm.TdxVolPMModel(**{'code': '000000', 'name': '两市成交', 'day': day, 'amount': amount, 'pm': 0}))
        self.save(zs)

    #计算两市前50个股成交额的指数
    def calcTop50ZS(self):
        dfs = self.datafiles
        bpd = 0
        def sortKey(df):
            idx = df.getItemIdx(bpd)
            if idx < 0:
                return 0
            return df.data[idx].amount

        for day in self.days2:
            bpd = day
            newdfs = sorted(dfs, key = sortKey, reverse=True)
            top50 = []
            allAmount, allZhangFu = 0, 0
            for i in range(50):
                nf = newdfs[i]
                code = nf.code
                nowIdx = nf.getItemIdx(day)
                di = nf.data[nowIdx]
                pdi = nf.data[nowIdx - 1] if nowIdx > 0 else None
                amount =  (di.amount if di else 0) / 100000000
                zhangFu = 0
                if pdi and pdi.close:
                    zhangFu =  (di.close - pdi.close) * 100 / pdi.close
                #name = self.codeNames.get(code)
                d = {'amount': amount, 'zhangFu': zhangFu}
                top50.append(d)
                #print(d)
            # 计算加权涨幅
            for tp in top50:
                allAmount += tp['amount']
            for tp in top50:
                allZhangFu += tp['amount'] / allAmount * tp['zhangFu']
            avgZhangFu = 0
            for tp in top50:
                avgZhangFu += tp['zhangFu']
            avgZhangFu /= len(top50)
            print('day=', day, 'allAmount=', allAmount, 'allZhangFu=', allZhangFu, 'avgZhangFu=', avgZhangFu)
            orm.TdxVolTop50ZSModel.create(day=day, vol=int(allAmount), zhangFu=allZhangFu, avgZhangFu=avgZhangFu)

class TdxLSTools:
    def __init__(self) -> None:
        fromDay = 20230101
        v = orm.TdxLSModel.select(pw.fn.max(orm.TdxLSModel.day)).scalar()
        if v: fromDay = v
        self.fromDay = fromDay
        self.codes = None
        self.days = None

    def calcOneDayInfo(self, day, sz, sh, dfs):
        item = orm.TdxLSModel()
        item.day = day
        item.amount = (sz.getItemData(day).amount + sh.getItemData(day).amount) // 100000000 # 亿元
        for df in dfs:
            idx = df.getItemIdx(day)
            if idx <= 0:
                continue
            dt = df.data[idx]
            if dt.close > df.data[idx - 1].close:
                item.upNum += 1
            elif dt.close < df.data[idx - 1].close:
                item.downNum += 1
            else:
                item.zeroNum += 1
            zdt = getattr(dt, 'zdt', '')
            if zdt == 'ZT':
                item.ztNum += 1
            elif zdt == 'DT':
                item.dtNum += 1
            else:
                zd = getattr(dt, 'zhangFu', -9999)
                if zd > 0 and zd <= 2:
                    item.z0_2 += 1
                elif zd > 2 and zd <= 5:
                    item.z2_5 += 1
                elif zd > 5 and zd <= 7:
                    item.z5_7 += 1
                elif zd > 7:
                    item.z7 += 1
                elif zd < 0 and zd >= -2:
                    item.d0_2 += 1
                elif zd < -2 and zd >= -5:
                    item.d2_5 += 1
                elif zd < -5 and zd >= -7:
                    item.d5_7 += 1
                elif zd < -7 and zd != -9999:
                    item.d7 += 1
            lbs = getattr(dt, 'lbs', 0)
            if lbs >= 2:
                item.lbNum += 1
            if item.zgb < lbs:
                item.zgb = lbs
            
        return item

    def calcInfo(self):
        self.codes = datafile.DataFileUtils.listAllCodes()
        self.days = datafile.DataFileUtils.calcDays(self.fromDay)
        sh = datafile.DataFile('999999', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        sz = datafile.DataFile('399001', datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL)
        dfs = [datafile.DataFile(c, datafile.DataFile.DT_DAY, datafile.DataFile.FLAG_ALL) for c in self.codes]
        rs = []
        for df in dfs:
            df.calcZDT()
            df.calcZhangFu()
        for day in self.days:
            item = self.calcOneDayInfo(day, sz, sh, dfs)
            rs.append(item)
            print('TdxLSTools.calcInfo item=', item.__data__)
        orm.TdxLSModel.bulk_create(rs, 50)

class TdxDownloader:
    def __init__(self) -> None:
        pass

    def checkProcessStarted(self):
        pids = psutil.pids()
        for pid in pids:
            p = psutil.Process(pid)
            if 'tdxw.exe' in p.name().lower():
                self.pid = pid
                #print('已检测到开启了通达信')
                return True
        return False

    def startProcess(self):
        subprocess.Popen('D:\\Program Files\\new_tdx2\\TdxW.exe', shell=True)
        time.sleep(10)

    def killProcess(self):
        os.system('taskkill /F /IM TdxW.exe')

    def getScreenPos(self, hwnd, x, y, recurcive = True):
        while hwnd:
            #print(f'hwnd={hwnd:X}', win32gui.GetWindowText(hwnd))
            nx, ny , *_ = win32gui.GetWindowRect(hwnd)
            x += nx
            y += ny
            hwnd = win32gui.GetParent(hwnd)
            if not recurcive:
                break
        return (x, y)

    def login(self):
        hwnd = win32gui.FindWindow('#32770', '通达信金融终端V7.642')
        print(f'login hwnd=0x{hwnd :X}')
        if not hwnd:
            raise Exception('Not find Tdx login window')
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(3)
        pwdPos = (250, 300)
        pwdPos = self.getScreenPos(hwnd, *pwdPos)
        pyautogui.click(*pwdPos, duration=0.5)
        for i in range(20):
            pyautogui.press('backspace')
        pyautogui.typewrite('gaoyan2012')

        loginBtnPos = (200, 370)
        loginBtnPos = self.getScreenPos(hwnd, *loginBtnPos)
        pyautogui.click(*loginBtnPos, duration=0.5)
        time.sleep(15)

    def getTdxMainWindow(self):
        mainWnd = win32gui.FindWindow('TdxW_MainFrame_Class', None)
        print(f'main tdx window={mainWnd:X}')
        if not mainWnd:
            raise Exception('Not find tdx main window')
        return mainWnd
    
    def openDownloadDialog(self):
        mainWnd = self.getTdxMainWindow()
        win32gui.SetForegroundWindow(mainWnd)
        btnPos = (433, 35)
        time.sleep(3)
        btnPos = self.getScreenPos(mainWnd, *btnPos)
        pyautogui.click(*btnPos, duration=0.5)
        time.sleep(10)

    def getStartDayForDay(self):
        dirs = datafile.DataFileUtils.getLDayDirs()
        maxday = None
        for d in dirs:
            d = os.path.basename(d)
            if '-' not in d:
                continue
            lday = d.split('-')[-1]
            if not maxday or maxday < lday:
                maxday = lday
        dt = datetime.datetime.strptime(maxday, '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
        return dt    
    
    def getStartDayForTimemimute(self):
        dirs = datafile.DataFileUtils.getMinlineDirs()
        maxday = None
        for d in dirs:
            d = os.path.basename(d)
            if '-' not in d:
                continue
            lday = d.split('-')[-1]
            if not maxday or maxday < lday:
                maxday = lday
        dt = datetime.datetime.strptime(maxday, '%Y%m%d')
        dt = dt + datetime.timedelta(days = 1)
        return dt
    
    def startDownloadForDay(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        selBtnPos = self.getScreenPos(hwnd, 80, 95, False) # 日线和实时行情Button pos
        win32gui.SetForegroundWindow(hwnd)
        pyautogui.click(*selBtnPos, duration = 0.3)
        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForDay()
        fromDayCtrl.set_time(year = startDay.year, month = startDay.month, day = startDay.day)

        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        statusCtrl = win32gui.GetDlgItem(hwnd, 0x4C8) 
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(60)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break
        pyautogui.click(*selBtnPos, duration = 0.3)

    def startDownloadForTimeMinute(self):
        hwnd = win32gui.FindWindow('#32770', '盘后数据下载')
        print(f'download dialog hwnd={hwnd:X}')
        if not hwnd:
            raise Exception('Not find download dialog')
        win32gui.SetForegroundWindow(hwnd)
        selTabPos = self.getScreenPos(hwnd, 130, 35, False) # 一分钟线 tab pos
        pyautogui.click(*selTabPos, duration = 0.3)
        time.sleep(1.5)
        selBtnPos = self.getScreenPos(hwnd, 70, 70, False) # 一分钟线 pos
        pyautogui.click(*selBtnPos, duration = 0.3)

        fromDayCtrl = win32gui.GetDlgItem(hwnd, 0x4D5) # 开始时间控件
        print(f'fromDayCtrl={fromDayCtrl:X}')
        if not fromDayCtrl:
            raise Exception('Not find fromDayCtrl')
        fromDayCtrl = DateTimePickerWrapper(fromDayCtrl)
        startDay = self.getStartDayForTimemimute()
        fromDayCtrl.set_time(year=startDay.year, month=startDay.month, day = startDay.day)
        startBtn = win32gui.FindWindowEx(hwnd, None, 'Button', '开始下载')
        startBtnPos = self.getScreenPos(hwnd, 440, 400, False)
        pyautogui.click(*startBtnPos, duration = 0.3) # 点击下载
        # wait for download end
        time.sleep(2)
        if win32gui.GetWindowText(startBtn) != '取消下载':
            raise Exception('start download Fail')
        while True:
            time.sleep(60)
            if win32gui.GetWindowText(startBtn) == '开始下载':
                break

    def run(self):
        if self.checkProcessStarted():
            self.killProcess()
        pyautogui.hotkey('win', 'd')
        self.startProcess()
        self.login()
        self.openDownloadDialog()
        self.startDownloadForDay()
        self.startDownloadForTimeMinute()
        self.killProcess()

def work():
    tm = datetime.datetime.now()
    ss = tm.strftime('%Y-%m-%d %H:%M')
    print('\033[32m' + ss + '\033[0m')
    # 下载
    tdx = TdxDownloader()
    tdx.run()
    # 计算成交量排名
    t = TdxVolPMTools()
    t.calcVolOrder_Top500()
    t.calcSHSZVol()
    #计算两市行情信息
    t = TdxLSTools()
    t.calcInfo()
    print('\n\n')
    return True

def getDesktopGUILock():
    LOCK_NAME = 'D:/__Desktop_GUI_Lock__'
    mux = win32event.CreateMutex(None, False, LOCK_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        win32api.CloseHandle(mux)
        return None
    return mux

def releaseDesktopGUILock(lock):
    if lock:
        win32api.CloseHandle(lock)

# seconds
def checkUserNoInputTime():
    a = win32api.GetLastInputInfo()
    cur = win32api.GetTickCount()
    diff = cur - a
    sec = diff / 1000
    return sec >= 5 * 60

def getMaxDay(paths):
    md = None
    for p in paths:
        bn = os.path.basename(p)
        if '-' not in bn:
            continue
        sp = bn.split('-')
        if not md:
            md = sp[-1]
        elif md < sp[-1]:
            md = sp[-1]
    return md


def renameDirs():
    ldays = datafile.DataFileUtils.getLDayDirs()
    mins = datafile.DataFileUtils.getMinlineDirs()
    ldaysLast = getMaxDay(ldays)
    minsLast = getMaxDay(mins)
    maxday = max(ldaysLast, minsLast)
    maxday = datetime.datetime.strptime(maxday, '%Y%m%d')
    tds = datafile.DataFileUtils.calcDays(0, True)
    existsLastDay = datetime.datetime.strptime(str(tds[-1]), '%Y%m%d')
    diff = existsLastDay - maxday
    if diff.days < 15:
        return
    maxday += datetime.timedelta(days=1)
    maxday = maxday.strftime('%Y%m%d')
    newName = f'-{maxday}-{tds[-1]}'

    sh1 = os.path.join(datafile.VIPDOC_BASE_PATH, 'sh', 'lday')
    sh2 = os.path.join(datafile.VIPDOC_BASE_PATH, 'sh', 'minline')
    sz1 = os.path.join(datafile.VIPDOC_BASE_PATH, 'sz', 'lday')
    sz2 = os.path.join(datafile.VIPDOC_BASE_PATH, 'sz', 'minline')
    ls = [sh1, sh2, sz1, sz2]
    for s in ls:
        try:
            os.rename(s, s + newName)
            os.mkdir(s)
        except Exception as e:
            print('[renameDirs] fail', e)
            pass

def autoMain():
    os.system('') # fix win10 下console 颜色不生效
    lastDay = 0
    while True:
        today = datetime.datetime.now()
        renameDirs()
        if today.weekday() >= 5: #周六周日
            time.sleep(60 * 60)
            continue
        if lastDay == today.day:
            time.sleep(60 * 60)
            continue
        ts = f"{today.hour:02d}:{today.minute:02d}"
        if ts < '18:05':
            time.sleep(3 * 60)
            continue
        lock = getDesktopGUILock()
        if not lock:
            time.sleep(3 * 60)
            continue
        if work(): #checkUserNoInputTime() and
            lastDay = today.day
        releaseDesktopGUILock(lock)

if __name__ == '__main__':
    #work() # run one time
    autoMain()