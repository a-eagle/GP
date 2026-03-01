import peewee as pw
import os, sys, datetime

path = os.path.dirname(os.path.dirname(__file__))

class ModelManager:
    @classmethod
    def getColumns(clazz, model : pw.Model):
        tableName = model._meta.table_name
        db : pw.SqliteDatabase = model._meta.database
        cc = db.execute_sql(f"PRAGMA table_info({tableName})")
        rs = cc.fetchall()
        cols = []
        for col in rs:
            colName = col[1]
            cols.append(colName)
        return cols

    @classmethod
    def listTables(clazz, db : pw.SqliteDatabase):
        cc = db.execute_sql('select name from sqlite_master where type="table"')
        rs = cc.fetchall()
        names = []
        for r in rs:
            names.append(r[0])
        return names

    @classmethod
    def hasColumn(clazz, model : pw.Model, columnName : str):
        cols = clazz.getColumns(model)
        return columnName in cols

    @classmethod
    def hasTable(clazz, db : pw.SqliteDatabase, tableName : str):
        tbs = clazz.listTables(db)
        return tableName in tbs

    @classmethod
     # modify table of add field
    def addField(clazz, model : pw.Model, field : pw.Field):
        # field : pw.Field = model._meta.fields.get(fieldName, None)
        columnName = field.column_name
        if clazz.hasColumn(model, columnName):
            return
        tableName = model._meta.table_name
        sql = f"alter table {tableName} add column {columnName} {field.field_type}"
        if hasattr(field, 'max_length'):
            sql += f'({field.max_length})'
        # if field.null == False:
        #     sql += ' NOT NULL '
        db : pw.SqliteDatabase = model._meta.database
        db.execute_sql(sql)

    @classmethod
    def renameField(clazz, model : pw.Model, field : pw.Field, oldColumnName : str):
        columnName = field.column_name
        if columnName == oldColumnName:
            return
        if not clazz.hasColumn(model, oldColumnName):
            return
        tableName = model._meta.table_name
        sql = f"ALTER TABLE {tableName} rename COLUMN {oldColumnName} to {columnName}"
        db : pw.SqliteDatabase = model._meta.database
        db.execute_sql(sql)

    @classmethod
    def renameTable(clazz, db : pw.SqliteDatabase, oldTableName : str, newTableName : str):
        if oldTableName == newTableName:
            return
        if not clazz.hasTable(db, oldTableName):
            return
        sql = f"ALTER TABLE {oldTableName} rename to {newTableName}"
        db.execute_sql(sql)

    # move table from a database to another database
    @classmethod
    def moveTableData(clazz, fromDb : pw.SqliteDatabase, destModel : pw.Model, modifyFunc = None):
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
            if modifyFunc:
                modifyFunc(item)
        destModel.bulk_create(inserts, 50)

class TestModel(pw.Model):
    user = pw.CharField() #
    old = pw.IntegerField(null = True, default = 0, column_name = 'OLD_x')
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    sex = pw.CharField(null = True, default = datetime.date.today, column_name = 'sex_n') #
    paiMing = pw.IntegerField(default = 10)
    score = pw.IntegerField(column_name = 'cc_score')

    class Meta:
        # database = db_test
        table_name = 'TestModel_New'

def test_ModelManager():
    db_test = pw.SqliteDatabase(f'test.db')
    TestModel._meta.database = db_test
    # db_test.create_tables([TestModel])
    ModelManager.addField(TestModel, TestModel.paiMing)
    ModelManager.addField(TestModel, TestModel.sex)
    # ModelManager.addField(TestModel, TestModel.score)
    # ModelManager.renameField(TestModel, TestModel.score, 'score')
    # ModelManager.renameTable(db_test, 'TestModel_N', 'TestModel_New')
    tb = TestModel()
    tb.create(user = 'xde', old = 15, sex = 'MF')
    
def move_cls():
    import cls_orm
    db_tck = pw.SqliteDatabase(f'{path}/db/tck.db')
    ModelManager.moveTableData(db_tck, cls_orm.CLS_UpDown)
    ModelManager.moveTableData(db_tck, cls_orm.CLS_SCQX)
    ModelManager.moveTableData(db_tck, cls_orm.CLS_SCQX_Time)
    ModelManager.moveTableData(db_tck, cls_orm.CLS_HotTc)
    ModelManager.moveTableData(db_tck, cls_orm.CLS_ZT)

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
    test_ModelManager()
    pass