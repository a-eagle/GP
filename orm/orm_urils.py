import peewee as pw
import os, sys

path = os.path.dirname(os.path.dirname(__file__))

# move table from a database to another database
def move_table_data(fromDb, modelClass : pw.Model, ops = None):
    cols = [] # (field.name, column_name)
    for k in modelClass._meta.columns:
        field = modelClass._meta.columns[k]
        if k == 'id':
            continue
        cols.append((field.name, field.column_name))
    #print(cols)
    # build query select sql
    c = map(lambda x: x[1], cols)
    sql = 'select ' + ', '.join(c) + ' from ' + modelClass._meta.table_name
    cc = fromDb.cursor()
    cc.execute(sql)
    rs = cc.fetchall()
    inserts = []
    for row in rs:
        params = {}
        for i, c in enumerate(cols):
            params[c[0]] = row[i]
        #print(params)
        item = modelClass(**params)
        inserts.append(item)
        if ops:
            ops(item)
    modelClass.bulk_create(inserts, 50)
    
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

if __name__ == '__main__':
    pass