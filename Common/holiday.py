import datetime

days = [
    20240404, 20240405, 20240501, 20240502, 20240503, 20240610,
    20240916, 20240917, 20241001, 20241002, 20241003, 20241004, 20241007
]

# day = str | int | datetime | date
def isHoliday(day):
    if not day:
        return False
    if type(day) == str:
        day = day.replace('-', '')
        day = int(day)
    elif isinstance(day, datetime.datetime) or isinstance(day, datetime.date):
        day = day.strftime('%Y%M%d')
        day = int(day)
    if type(day) != int:
        raise Exception('[holiday.isHoliday] param error, day=', day)
    return day in days