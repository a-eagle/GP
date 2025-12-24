import py_compile, os, re, sys, shutil

DEST_DIR = os.path.dirname(__file__)
ROOT_PATH = os.path.dirname(os.path.dirname(__file__))

def buildPyFiles(path, name):
    ls = os.listdir(os.path.join(path, name))
    dirname = os.path.join(DEST_DIR, name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    for f in ls:
        file = os.path.join(path, name, f)
        if len(f) < 4 or f[-3 : ] != '.py':
            continue
        py_compile.compile(file, os.path.join(dirname, f + 'c'))

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
        dirname = os.path.join(DEST_DIR, srcName)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        for ln in os.listdir(s):
            copyFiles(srcRootPath, os.path.join(srcName, ln))
    else:
        d = os.path.join(DEST_DIR, srcName)
        shutil.copyfile(s, d)

def buildPyc():
    listTopDir(ROOT_PATH, buildPyFiles)

def copyDataFiles():
    # copyFiles(ROOT_PATH, 'THS\\img')
    copyFiles(ROOT_PATH, 'db')
    copyFiles(ROOT_PATH, 'chrome\\local')
    # copyFiles(ROOT_PATH, 'download\\cls-sign.dll')

if __name__ == '__main__':
    # buildPyc()
    copyDataFiles()