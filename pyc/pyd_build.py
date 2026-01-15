import os, sys, shutil, py_compile
import distutils.core
import Cython.Build
# pip install nuitka
# nuitka 

DEST_ROOT_DIR = os.path.join(os.path.dirname(__file__), 'GP-pyd')
SRC_ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

pyDirs = {}
pyFiles = []
dirs = set()

def init():
    if not os.path.exists(DEST_ROOT_DIR):
        os.makedirs(DEST_ROOT_DIR)

def buildPycFiles(path, name):
    ls = os.listdir(os.path.join(path, name))
    dirname = os.path.join(DEST_ROOT_DIR, name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    for f in ls:
        file = os.path.join(path, name, f)
        if len(f) < 4 or f[-3 : ] != '.py':
            continue
        py_compile.compile(file, os.path.join(dirname, f + 'c'))

def buildPyc():
    listTopDir(SRC_ROOT_PATH, buildPycFiles)

# todo = function(path, name)
def listTopDir(path, todo):
    ls = os.listdir(path)
    for f in ls:
        if f == 'pyc':
            continue
        sp = os.path.join(path, f)
        if f[0] == '.':
            continue
        if os.path.isdir(sp):
            todo(path, f)

def copyFiles(srcRootPath, srcName):
    s = os.path.join(srcRootPath, srcName)
    if os.path.isdir(s):
        dirname = os.path.join(DEST_ROOT_DIR, srcName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        for ln in os.listdir(s):
            copyFiles(srcRootPath, os.path.join(srcName, ln))
    else:
        d = os.path.join(DEST_ROOT_DIR, srcName)
        shutil.copyfile(s, d)

def copyDataFiles():
    # copyFiles(ROOT_PATH, 'THS\\img')
    # copyFiles(SRC_ROOT_PATH, 'db')
    copyFiles(SRC_ROOT_PATH, 'chrome\\local')
    copyFiles(SRC_ROOT_PATH, 'pyc')
    copyFiles(SRC_ROOT_PATH, 'download\\cls-sign.dll')

def copyPyFiles(path, name):
    ls = os.listdir(os.path.join(path, name))
    dirname = os.path.join(DEST_ROOT_DIR, name)
    dirs.add(dirname)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    for f in ls:
        sfile = os.path.join(path, name, f)
        if len(f) < 4 or f[-3 : ] != '.py':
            continue
        dfile = os.path.join(dirname, f)
        shutil.copyfile(sfile, dfile)
        if f in pyFiles:
            raise Exception('Same py file', dfile)
        pyDirs[f[0 : -3]] = name
        pyFiles.append(dfile)

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

def cleanAll():
    for d in dirs:
        removeDir(d)
    buildDir = os.path.join(DEST_ROOT_DIR, 'build')
    removeDir(buildDir)

def cleanPyAndCFiles():
    for f in pyFiles:
        os.remove(f)
        os.remove(f'{f[0 : -3]}.c')

def movePyd():
    for ln in os.listdir(DEST_ROOT_DIR):
        if len(ln) <= 4 or ln[-4 : ] != '.pyd':
            continue
        bname = ln[0 : ln.index('.')]
        dir = pyDirs[bname]
        shutil.move(os.path.join(DEST_ROOT_DIR, ln), os.path.join(DEST_ROOT_DIR, dir, ln))

if __name__ == '__main__':
    init()
    listTopDir(SRC_ROOT_PATH, copyPyFiles)
    os.chdir(DEST_ROOT_DIR)
    sys.argv.append('build_ext')
    sys.argv.append('--inplace')
    distutils.core.setup(ext_modules = Cython.Build.cythonize(pyFiles))
    cleanPyAndCFiles()
    movePyd()
    buildDir = os.path.join(DEST_ROOT_DIR, 'build')
    removeDir(buildDir)
    copyDataFiles()