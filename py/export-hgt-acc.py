import pymysql
from time import sleep
from selenium import webdriver
import traceback
import os
import shutil


# file "acc-data" rows format:
# 日期  代码  资金  持股数量  沪股通占比  总市值
#day code zj cgsl per zsz , split by \t

#导出命令
#select _day, _code, _zj, _cgsl, _per, _zsz from _hgt_acc into outfile 'D:/vscode/py/acc-data';


mysql_conn = pymysql.connect(host= '127.0.0.1', port= 3306, user= 'root', password= 'root', db= 'tdx_f10')

FILE_NAME = 'data-acc'

def main():
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)
    curPath = os.path.dirname(__file__)
    filePath = curPath + '\\' +  FILE_NAME
    filePath = filePath.replace('\\', '/')

    cursor = mysql_conn.cursor()
    sql = "select _day, _code, _zj, _cgsl, _per, _zsz from _hgt_acc where _day >= {} into outfile '{}' ".format(20220101, filePath)
    cursor.execute(sql)
    
try:
    main()
except Exception as e:
    traceback.print_exc()

mysql_conn.close()
print('Export End, Exit')
sleep(1)


