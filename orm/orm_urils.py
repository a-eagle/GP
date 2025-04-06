import peewee as pw

path = __file__[0 : __file__.upper().index('GP')]

# move table from a database to another database
def move_table_data(fromDb, modelClass : pw.Model):
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
    modelClass.bulk_create(inserts, 50)
    
    rs = modelClass.select()
    for r in rs:
        print(r.__data__)

# import ths_orm
# move_table_data(ths_orm.db_hot, ths_orm.THS_HotZH)

def move_cls():
    import cls_orm
    db_tck = pw.SqliteDatabase(f'{path}GP/db/tck.db')
    move_table_data(db_tck, cls_orm.CLS_UpDown)
    move_table_data(db_tck, cls_orm.CLS_SCQX)
    move_table_data(db_tck, cls_orm.CLS_SCQX_Time)
    move_table_data(db_tck, cls_orm.CLS_HotTc)
    move_table_data(db_tck, cls_orm.CLS_ZT)

def move_ths():
    import ths_orm
    db = pw.SqliteDatabase(f'{path}GP/db/TCK.db')
    move_table_data(db, ths_orm.THS_ZT)

def move_def():
    import def_orm
    db = pw.SqliteDatabase(f'{path}GP/db/def_tck.db')
    move_table_data(db, def_orm.MySettings)

def move_z():
    import z_orm
    db = pw.SqliteDatabase(f'{path}GP/db/TCK.db')
    move_table_data(db, z_orm.ZT_PanKou)

if __name__ == '__main__':
    pass