import os, sys, shutil
import distutils.core
import Cython.Build

import pyc_build

pyDirs = {}
pyFiles = []
dirs = set()

def copyPyFiles(path, name):
    ls = os.listdir(os.path.join(path, name))
    dirname = os.path.join(pyc_build.DEST_DIR, name)
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
    buildDir = os.path.join(pyc_build.DEST_DIR, 'build')
    removeDir(buildDir)

def cleanPyAndCFiles():
    for f in pyFiles:
        os.remove(f)
        os.remove(f'{f[0 : -3]}.c')

def movePyd():
    for ln in os.listdir(pyc_build.DEST_DIR):
        if len(ln) <= 4 or ln[-4 : ] != '.pyd':
            continue
        bname = ln[0 : ln.index('.')]
        dir = pyDirs[bname]
        shutil.move(os.path.join(pyc_build.DEST_DIR, ln), os.path.join(pyc_build.DEST_DIR, dir, ln))

if __name__ == '__main__':
    pyc_build.listTopDir(pyc_build.ROOT_PATH, copyPyFiles)
    os.chdir(pyc_build.DEST_DIR)
    sys.argv.append('build_ext')
    sys.argv.append('--inplace')
    distutils.core.setup(ext_modules = Cython.Build.cythonize(pyFiles))
    cleanPyAndCFiles()
    movePyd()
    buildDir = os.path.join(pyc_build.DEST_DIR, 'build')
    removeDir(buildDir)
    pyc_build.copyDataFiles()


# pip install nuitka
# nuitka 