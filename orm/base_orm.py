import peewee as pw
import sys, datetime, os, inspect

class BaseModel(pw.Model):
    # return change: diffrents dict object {name: (old, new), ...}  | not change: {} empty dict
    # newObj: peewee.Model object | dict
    # attrNames: list | tuple | dict, compare attrs. if None, then compare all fields
    # excludeAttrNames: list | tuple | dict, not include compare attrs
    # enableDefaults: enable pw.Model fields default value
    def compare(self, newObj, attrNames = None, excludeAttrNames = None, enableDefaults = True):
        if not newObj:
            return False
        if isinstance(newObj, dict):
            getValFunc = lambda o, n : o.get(n, None)
        else:
            getValFunc = lambda o, n : getattr(o, n, None)
        diffrents = self._diffObject(newObj, getValFunc, attrNames, excludeAttrNames, enableDefaults)
        return diffrents

    # compare and modify changes
    # see .compare()
    def diff(self, newObj, attrNames = None, excludeAttrNames = None, enableDefaults = True):
        diffrents = self.compare(newObj, attrNames, excludeAttrNames, enableDefaults)
        for name in diffrents:
            oldVal, newVal = diffrents[name]
            setattr(self, name, newVal)
        return diffrents

    # spliter : function(val) -> list(str)
    # return None | (old, new)
    def diffAttrOfList(self, attrName, newVal, spliter, enableDefaults = True):
        curVal = getattr(self, attrName, None)
        name, _type, defaultVal = self.getAttr(attrName)
        if curVal == None and enableDefaults:
            curVal = defaultVal
        if newVal == None and enableDefaults:
            newVal = defaultVal
        if newVal == curVal:
            return None
        if newVal == None or curVal == None:
            return (curVal, newVal)
        curValList = spliter(curVal)
        newValList = spliter(newVal)
        if len(curValList) != len(newValList):
            setattr(self, name, newVal)
            return (curVal, newVal)
        for d in curValList:
            if d not in newValList:
                setattr(self, name, newVal)
                return (curVal, newVal)
        for d in newValList:
            if d not in curValList:
                setattr(self, name, newVal)
                return (curVal, newVal)
        return None
    
    # return diffrents dict object {name: (old, new), ...}  | {} empty
    def _diffObject(self, newObj, getValFunc, attrNames, excludeAttrNames, enableDefaults):
        diffrents = {}
        attrs = self.getAttrs(attrNames, excludeAttrNames)
        for a in attrs:
            self.diffAttr(a, getValFunc(newObj, a[0]), enableDefaults, diffrents)
        return diffrents

    def diffAttr(self, attr, newVal, enableDefaults, diffrents):
        name, _type, defaultVal = attr
        if callable(defaultVal):
            defaultVal = defaultVal()
        curVal = getattr(self, name, None)
        if curVal == newVal:
            return False
        if enableDefaults and newVal is None:
            if curVal == defaultVal:
                return False
            newVal = defaultVal
        if newVal is not None and type(newVal) != _type:
            newVal = _type(newVal)
        if curVal == newVal:
            return False
        diffrents[name] = (curVal, newVal)
        return True

    # return (name, type, default value)
    def getAttr(self, attrName):
        rs = self.getAttrs([attrName], None)
        return rs[0]

    # return [ (name, type, default value), ..,]
    def getAttrs(self, attrNames, excludeAttrNames):
        fields = self._meta.fields
        defaults = self._meta.defaults
        rs = []
        for name in fields:
            if name == 'id':
                continue
            if attrNames and (name not in attrNames):
                continue
            if excludeAttrNames and (name in excludeAttrNames):
                continue
            f = fields[name]
            defaultVal = None
            if f in defaults:
                defaultVal = defaults[f]
            if isinstance(f, pw._StringField):
                rs.append((name, str, defaultVal))
            elif isinstance(f, pw.IntegerField):
                rs.append((name, int, defaultVal))
            elif isinstance(f, pw.FloatField):
                rs.append((name, float, defaultVal))
            elif isinstance(f, pw.DateTimeField):
                rs.append((name, datetime.datetime, defaultVal))
            elif isinstance(f, pw.DateField):
                rs.append((name, datetime.date, defaultVal))
        return rs

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
    def hasColumn(clazz, model : pw.Model, columnName : str):
        cols = clazz.getColumns(model)
        return columnName in cols

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
        if field.null == False:
            sql += ' NOT NULL '
        db : pw.SqliteDatabase = model._meta.database
        db.execute_sql(sql)

    # TODO  has bug
    @classmethod
    def dropField(clazz, model : pw.Model, columnName: str):
        if not clazz.hasColumn(model, columnName):
            return
        tableName = model._meta.table_name
        sql = f"alter table {tableName} drop column {columnName}"
        db : pw.SqliteDatabase = model._meta.database
        db.execute_sql(sql) # why has bug ?

class TestModel(BaseModel):
    user = pw.CharField() #
    old = pw.IntegerField(null = True, default = 0, column_name = 'OLD_x')
    updateTime = pw.DateTimeField(null = True, default = datetime.datetime.now)

    sex = pw.CharField(null = True, default = datetime.date.today, column_name = 'sex_n') #
    paiMing = pw.IntegerField(default = 10)

    class Meta:
        # database = db_test
        table_name = 'TestModel_N'

def test():
    db_test = pw.SqliteDatabase(f'test.db')
    TestModel._meta.database = db_test
    db_test.create_tables([TestModel])
    ModelManager.dropField(TestModel, 'paiMing')
    ModelManager.addField(TestModel, TestModel.paiMing)
    ModelManager.addField(TestModel, TestModel.sex)
    tb = TestModel()
    tb.create(user = 'xde', old = 15, sex = 'MF')
    

if __name__ == '__main__':
    # test()
    pass
    