import os, sys, shutil, py_compile, re, functools
import distutils.core
import Cython.Build
from distutils.extension import Extension
# pip install nuitka
# nuitka 

DEST_ROOT_PATH = os.path.join(os.path.dirname(__file__), 'GP-pyd')
SRC_ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

# todo: function(path, isDir)
# filter: function(file, isDir)
def travelDir(rootPath, subPath = '', todo = None, filter = None):
    rs = []
    path = rootPath
    if subPath:
        path = os.path.join(rootPath, subPath)
    ls = os.listdir(path)
    for f in ls:
        sp = os.path.join(path, f)
        if f[0] == '.' or f == '__pycache__':
            continue
        isDir = os.path.isdir(sp)
        if filter and not filter(f, isDir):
            continue
        psp = os.path.join(subPath, f)
        if todo:
            todo(psp, isDir)
        rs.append((psp, isDir))
        if isDir:
            rs.extend(travelDir(rootPath, psp, todo, filter))
    return rs

def copyFile(file, isDir):
    spath = os.path.join(SRC_ROOT_PATH, file)
    dpath = os.path.join(DEST_ROOT_PATH, file)
    if isDir:
        if not os.path.exists(dpath):
            os.makedirs(dpath)
    else:
        shutil.copyfile(spath, dpath)

def copyDataFiles():
    travelDir(SRC_ROOT_PATH, 'chrome\\local', todo = copyFile)
    pycFilter = lambda file, isDir: not isDir and '.' in file and file.index('.') > 0
    travelDir(SRC_ROOT_PATH, 'pyc', todo = copyFile, filter = pycFilter)
    travelDir(SRC_ROOT_PATH, 'db', todo = copyFile)
    # copyFiles(SRC_ROOT_PATH, 'download\\cls-sign.dll')

def removeDir(path):
    if not os.path.exists(path):
        return
    if os.path.isdir(path):
        for ls in os.listdir(path):
            removeDir(os.path.join(path, ls))
        if os.path.exists(path):
            os.removedirs(path)
    else:
        os.remove(path)

def cleanFiles(files):
    for file, isDir in files:
        if isDir: continue
        f = os.path.join(DEST_ROOT_PATH, file)
        os.remove(f)
        os.remove(f'{f[0 : -3]}.c')
    buildDir = os.path.join(DEST_ROOT_PATH, 'build')
    removeDir(buildDir)
    
def buildExceptions(srcFiles):
    exceptions = []
    for file, isDir in srcFiles:
        if isDir:
            continue
        pps = list(os.path.split(file))
        pps[-1] = pps[-1][0 : -3]
        m = '.'.join(pps)
        exceptions.append(Extension(m, [file]))
    return exceptions

if __name__ == '__main__':
    PY_FILTER = lambda file, isDir: file != 'pyc' and (isDir or re.match('.*[.]py$', file) != None)
    srcFiles = travelDir(SRC_ROOT_PATH, todo = copyFile, filter = PY_FILTER)
    os.chdir(DEST_ROOT_PATH)
    sys.argv.append('build_ext')
    sys.argv.append('--inplace')
    exceptions = buildExceptions(srcFiles)
    distutils.core.setup(ext_modules = Cython.Build.cythonize(exceptions))
    cleanFiles(srcFiles)
    copyDataFiles()