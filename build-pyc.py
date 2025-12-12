import py_compile, os, re, sys

def buildPyFiles(path):
    ls = os.listdir(path)
    for f in ls:
        sp = os.path.join(path, f)
        if os.path.isdir(sp):
            buildPyFiles(sp)
            continue
        if len(f) < 3 or f[-3 : ] != '.py':
            continue
        dirname = os.path.dirname(sp[2 : ])
        dirname = os.path.join('pyc', dirname)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        py_compile.compile(sp, os.path.join(dirname, f + 'c'))

if __name__ == '__main__':
    buildPyFiles('.')