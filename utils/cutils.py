import time, datetime

def nowTimeInt():
    ms = int(time.time() * 1000 * 1000)
    return ms

def datetimeToInt(dt : datetime.datetime):
    return int(dt.timestamp() * 1000 * 1000)

def updateTimeToDateTime(updateTime):
    if not updateTime:
        return None
    if type(updateTime) == str:
        updateTime = int(updateTime)
    seconds = updateTime / 1000 / 1000
    dt = datetime.datetime.fromtimestamp(seconds)
    return dt

def diffUpdateTime(first, second):
    if type(first) == str:
        first = int(first)
    if type(second) == str:
        second = int(second)
    if type(first) == int:
        first = datetime.datetime.fromtimestamp(first / 1000 / 1000)
    if type(second) == int:
        second = datetime.datetime.fromtimestamp(second / 1000 / 1000)
    return first - second

# date = int | str | datetime | date
# return YYYY-MM-DD
def formateDate(date):
    if not date:
        return None
    if type(date) == int:
        date = str(date)
    if type(date) == str:
        date = date.strip()
        if len(date) == 10:
            return date
        if len(date) == 8:
            return f'{date[0 : 4]}-{date[4 : 6]}-{date[6 : 8]}'
        return date
    if isinstance(date, datetime.date):
        date = date.strftime('%Y-%m-%d')
        return date
    return date

def isMainZs(code):
    if not code:
        return False
    if type(code) == int: code = f'{code :06d}'
    return code == '1A0001' or (code[0 : 3] == '399')

def isBkGnZS(code):
    if not code:
        return False
    if type(code) == int: code = f'{code :06d}'
    return  code[0 : 2] == '88'

def isAnyZs(code):
    if not code:
        return False
    if type(code) == int: code = f'{code :06d}'
    return isMainZs(code) or isBkGnZS(code)

def isCode(code):
    if not code:
        return False
    if type(code) == int: code = f'{code :06d}'
    return (code[0] in '036') and (code[0 : 3] != '399')

# 930, 1400
def getCurTime() -> int:
    now = datetime.datetime.now()
    return now.hour * 100 + now.minute

def isTradeTime():
    now = datetime.datetime.now()
    st = now.strftime('%H:%M')
    if st < '09:30':
        return False
    if st < '11:30':
        return True
    if st < '13:00':
        return False
    if st < '15:00':
        return True
    return False