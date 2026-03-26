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