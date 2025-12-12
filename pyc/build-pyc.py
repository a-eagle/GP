import py_compile, os, re, sys

def buildPyFiles(name, path):
    nn = os.path.join(path, name)
    ls = os.listdir(nn)
    baseDir = os.path.dirname(__file__)
    for f in ls:
        if len(f) < 3 or f[-3 : ] != '.py':
            continue
        dirname = os.path.join(baseDir, name)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        file = os.path.join(path, name, f)
        py_compile.compile(file, os.path.join(dirname, f + 'c'))

def listTopDir(path):
    ls = os.listdir(path)
    for f in ls:
        if f == 'pyc':
            continue
        sp = os.path.join(path, f)
        if f[0] == '.':
            continue
        if os.path.isdir(sp):
            buildPyFiles(f, path)
            continue


if __name__ == '__main__':
    listTopDir(os.path.dirname(os.path.dirname(__file__)))