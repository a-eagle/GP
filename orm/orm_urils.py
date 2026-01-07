import peewee as pw
import os, sys

path = os.path.dirname(os.path.dirname(__file__))

# move table from a database to another database
def move_table_data(fromDb, destModel : pw.Model, ops = None):
    cols = [] # (field.name, column_name)
    for k in destModel._meta.columns:
        field = destModel._meta.columns[k]
        if k == 'id':
            continue
        cols.append((field.name, field.column_name))
    #print(cols)
    # build query select sql
    c = map(lambda x: x[1], cols)
    sql = 'select ' + ', '.join(c) + ' from ' + destModel._meta.table_name
    cc = fromDb.cursor()
    cc.execute(sql)
    rs = cc.fetchall()
    inserts = []
    for row in rs:
        params = {}
        for i, c in enumerate(cols):
            params[c[0]] = row[i]
        #print(params)
        item = destModel(**params)
        inserts.append(item)
        if ops:
            ops(item)
    destModel.bulk_create(inserts, 50)
    
    # rs = modelClass.select()
    # for r in rs:
        # print(r.__data__)

# import ths_orm
# move_table_data(ths_orm.db_hot, ths_orm.THS_HotZH)

def move_cls():
    import cls_orm
    db_tck = pw.SqliteDatabase(f'{path}/db/tck.db')
    move_table_data(db_tck, cls_orm.CLS_UpDown)
    move_table_data(db_tck, cls_orm.CLS_SCQX)
    move_table_data(db_tck, cls_orm.CLS_SCQX_Time)
    move_table_data(db_tck, cls_orm.CLS_HotTc)
    move_table_data(db_tck, cls_orm.CLS_ZT)

def move_ths():
    import ths_orm
    db = pw.SqliteDatabase(f'{path}/db/TCK.db')
    move_table_data(db, ths_orm.THS_ZT)

def move_def():
    import def_orm
    db = pw.SqliteDatabase(f'{path}/db/TCK_def.db')
    move_table_data(db, def_orm.MySettings)

def diffDb(dbName):
    newDb = pw.SqliteDatabase(f'db/{dbName}')
    oldDb = pw.SqliteDatabase(f'db/OLD/{dbName}')
    # newDb.connect()
    # oldDb.connect()
    rs = newDb.execute_sql("SELECT name FROM sqlite_master WHERE type='table'")
    tables = []
    for r in rs:
        tables.append(r[0])
    for t in tables:
        sql = f'select count(*) from {t}'
        rs = newDb.execute_sql(sql)
        new = next(iter(rs))[0]
        rs = oldDb.execute_sql(sql)
        old = next(iter(rs))[0]
        # print(t, new, old)
        if new != old:
            print(t, new, old)


# diff all db & db/OLD *.db  of tables record count
def diffDbs():
    dbNames = os.listdir('db')
    for n in range(len(dbNames) - 1, 0, -1):
        if '.db' not in dbNames[n]:
            dbNames.pop(n)
    print(dbNames)

    for d in dbNames:
        if d == 'codes.db':
            continue
        print('--------', d, '---------')
        diffDb(d)

if __name__ == '__main__':
    # diffDbs()
    pass