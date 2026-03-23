import peewee as pw
import os, sys, datetime

path = os.path.dirname(os.path.dirname(__file__))
sys.path.append(path)

class ModelManager:
    USE_MYSQL = True
    USE_SQLITE = False

    @classmethod
    def getColumns(clazz, model : pw.Model):
        tableName = model._meta.table_name
        db : pw.SqliteDatabase = model._meta.database
        if clazz.USE_SQLITE:
            cc = db.execute_sql(f"PRAGMA table_info({tableName})")
        elif clazz.USE_MYSQL:
            cc = db.execute_sql(f"desc {tableName}")
        rs = cc.fetchall()
        cols = []
        for col in rs:
            if clazz.USE_SQLITE:
                colName = col[1]
            elif clazz.USE_MYSQL:
                colName = col[0]
            cols.append(colName)
        return cols

    @classmethod
    def listTables(clazz, db : pw.SqliteDatabase):
        if clazz.USE_SQLITE:
            cc = db.execute_sql('select name from sqlite_master where type="table"')
        elif clazz.USE_MYSQL:
            cc = db.execute_sql('show tables')
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
        sql = f"ALTER TABLE {tableName} rename COLUMN {oldColumnName} to {columnName}" # sqlite & mysql 8.0
        db : pw.SqliteDatabase = model._meta.database
        db.execute_sql(sql)

    @classmethod
    def renameTable(clazz, db : pw.SqliteDatabase, oldTableName : str, newTableName : str):
        if oldTableName == newTableName:
            return
        if not clazz.hasTable(db, oldTableName):
            return
        if clazz.USE_SQLITE:
            sql = f"ALTER TABLE {oldTableName} rename to {newTableName}"
        elif clazz.USE_MYSQL:
            sql = f"ALTER TABLE {oldTableName} rename {newTableName}"
        db.execute_sql(sql)

    # move table from a database to another database
    @classmethod
    def copyTableData(clazz, fromDb : pw.SqliteDatabase, destModel : pw.Model, srcTableName = None, descSrcColsMap : dict = {}, modifyFunc = None):
        cols = [] # (field.name, column_name)
        for k in destModel._meta.columns:
            field = destModel._meta.columns[k]
            if k == 'id':
                continue
            if field.name in descSrcColsMap:
                cols.append((field.name, descSrcColsMap[field.name]))
            else:
                cols.append((field.name, field.column_name))
        #print(cols)
        # build query select sql
        c = map(lambda x: x[1], cols)
        if not srcTableName:
            srcTableName = destModel._meta.table_name
        sql = 'select ' + ', '.join(c) + ' from ' + srcTableName
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
    # updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    # sex = pw.CharField(null = True, default = datetime.date.today, column_name = 'sex_n') #
    # paiMing = pw.IntegerField(default = 10)
    # score = pw.IntegerField(column_name = 'cc_score', default = 0)

    class Meta:
        # database = db_test
        table_name = 'TestModel_New'

def test_ModelManager():
    db_test = pw.SqliteDatabase(f'db/test.db')
    TestModel._meta.database = db_test
    db_test.create_tables([TestModel])
    # ModelManager.addField(TestModel, TestModel.paiMing)
    # ModelManager.addField(TestModel, TestModel.sex)
    # ModelManager.addField(TestModel, TestModel.score)
    # ModelManager.renameField(TestModel, TestModel.score, 'score')
    # ModelManager.renameTable(db_test, 'TestModel_N', 'TestModel_New')
    
    # tb = TestModel.get_by_id(3)
    # m = TestModel.update(tb.__data__, id = 10, old = 25).where(TestModel.id == tb.id)
    # m.execute()
    # print(m)

    # TestModel.create(user = 'user4')
    
if __name__ == '__main__':
    test_ModelManager()
    pass