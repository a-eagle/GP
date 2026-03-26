import peewee as pw
from playhouse.shortcuts import ReconnectMixin
from playhouse.pool import PooledMySQLDatabase
import sys, datetime, os, inspect, json, time

path = os.path.dirname(os.path.dirname(__file__))

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

class ReconnectMysqlDatabase(ReconnectMixin, pw.MySQLDatabase):
    pass

# db_mysql = ReconnectMysqlDatabase('GP', host='localhost', port=3306, user='root', password='root@2025')
db_mysql = PooledMySQLDatabase('GP', host='localhost', port=3306, user='root', password='root@2025', max_connections = 5)

class DeleteModel(pw.Model):
    keys = ('modelName', 'keyValues')
    modelName = pw.CharField(max_length = 50)
    keyValues = pw.CharField(max_length = 1024)
    updateTime = pw.BigIntegerField(null = True, default = nowTimeInt)

    class Meta:
        database = db_mysql

# 有updateTime属性的才会被纳入数据同步范围
class BaseModel(pw.Model):

    class Meta:
        database = db_mysql

    def delete_instance(self, recursive: bool = False, delete_nullable: bool = False):
        clazz = self.__class__
        keys = getattr(clazz, 'keys', None)
        if keys:
            modelName = clazz.__name__
            kv = {}
            for k in keys:
                kv[k] = getattr(self, k, None)
            keyValues = json.dumps(kv)
            DeleteModel.create(modelName = modelName, keyValues = keyValues)
        return super().delete_instance(recursive, delete_nullable)
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

# 无updateTime，数据库不自动同步更新
class VersionModel(BaseModel):
    name = pw.CharField()
    version = pw.IntegerField()

db_mysql.create_tables([DeleteModel, VersionModel])

class VersionManager:

    @classmethod
    def getVersion(clazz, modelName : str):
        obj = VersionModel.get_or_none(VersionModel.name == modelName)
        if obj:
            return obj.version
        return 0
    
    @classmethod
    def saveVersion(clazz, modelName : str, version : int):
        obj = VersionModel.get_or_none(VersionModel.name == modelName)
        if obj:
            obj.version = version
        else:
            VersionModel.create(name = modelName, version = version)


if __name__ == '__main__':
    print(nowTimeInt())