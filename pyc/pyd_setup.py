import os, sys, shutil
import distutils.core
import Cython.Build

import pyc_build

files = []

def copyPyFiles(path, name):
    ls = os.listdir(os.path.join(path, name))
    dirname = os.path.join(pyc_build.DEST_DIR, name)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    for f in ls:
        sfile = os.path.join(path, name, f)
        if len(f) < 4 or f[-3 : ] != '.py':
            continue
        dfile = os.path.join(dirname, f)
        shutil.copyfile(sfile, dfile)
        files.append(dfile)

pyc_build.listTopDir(pyc_build.ROOT_PATH, copyPyFiles)

distutils.core.setup(ext_modules = Cython.Build.cythonize(files))

for ff in files:
    os.remove(ff)


# nuitka 