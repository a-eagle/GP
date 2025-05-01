def _int(val, size):
    maxVal = (1 << size - 1) - 1
    minVal = - (1 << size - 1)
    val = val & ((1 << size) - 1)
    if val > maxVal:
        return minVal + (val - maxVal - 1)
    elif val < minVal:
        return maxVal - (minVal - val - 1)
    return val

def _uint(val, size):
    val = val & ((1 << size) - 1)
    return val

def int32(val):
    return _int(val, 32)

def uint32(val):
    return _uint(val, 32)

def int8(val):
    return _int(val, 8)

def uint8(val):
    return _uint(val, 8)

def x2d(v):
    b0 = v & 0xff
    b1 = (v >> 8) & 0xff
    b2 = (v >> 16) & 0xff
    b3 = (v >> 24) & 0xff
    return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3

def _pointer(arr : bytearray, offset, size : int):
    val = 0
    for i in range(size):
        val |= arr[offset + i] << i * 8
    return val

def int32p(arr : bytearray, offset):
    return _pointer(arr, offset, 4)

class ArrayBuffer:
    def __init__(self, *args):
        self.byteLength = 0
        self.buf = None
        self.offset = 0
        if len(args) == 1:
            self.new_1(*args)
        else:
            self.new_2(*args)
    
    def new_1(self, length):
        self.offset = 0
        self.byteLength = length
        self.buf = bytearray(length)

    def new_2(self, buf, offset, length):
        self.byteLength = length
        self.offset = offset
        self.buf = buf.buf
    
    def printBytes(self, offset, length):
        px = self.offset + offset
        for i in range(length):
            print(f"[{i}] = {self.buf[px + i]}")

    def printInts(self, offset, length):
        px = self.offset + offset
        for i in range(length):
            print(f"[{i}] = {int32p(self.buf, px + i * 4)}")

class TypeArray:
    def __init__(self, *args):
        self.arrbuf = None
        self.itemSize = 0
        self.length = 0
        self.byteLength = 0
        self.debugName = ''
        self._new(*args)

    def _new(self, *args):
        pass

    def new_1(self, itemSize, length):
        self.itemSize = itemSize
        self.length = length
        self.byteLength = itemSize * length
        self.arrbuf = ArrayBuffer(self.byteLength)

    def new_2(self, itemSize, buf, offset = 0, length = -1):
        if length < 0:
            less = buf.byteLength - offset
            length = less / itemSize
        self.itemSize = itemSize
        self.length = length
        self.byteLength = itemSize * length
        self.arrbuf = ArrayBuffer(buf, offset, length * itemSize)

    def _buffer(self, idx, typeSize, sign):
        val = _pointer(self.arrbuf.buf, self.arrbuf.offset + idx * typeSize, typeSize)
        if sign:
            return _int(val, typeSize * 8)
        return _uint(val, typeSize * 8)

    def _set_buffer(self, idx, typeSize, value, sign):
        px = self.arrbuf.offset + idx * typeSize
        uvalue = _uint(value, typeSize * 8)
        for i in range(typeSize):
            v = uint8(uvalue >> i * 8)
            self.arrbuf.buf[px + i] = v

class Int8Array(TypeArray):
    def __init__(self, *args):
        super().__init__(*args)

    def _new(self, *args):
        if type(args[0]) == int:
            self.new_1(1, *args)
        else:
            self.new_2(1, *args)

    def buffer(self, idx):
        return self._buffer(idx, 1, True)

    def __getitem__(self, idx):
        return self.buffer(idx)

    def __setitem__(self, idx, val):
        self._set_buffer(idx, 1, val, True)

class UInt8Array(TypeArray):
    def __init__(self, *args):
        super().__init__(*args)

    def _new(self, *args):
        if type(args[0]) == int:
            self.new_1(1, *args)
        else:
            self.new_2(1, *args)

    def buffer(self, idx):
        return self._buffer(idx, 1, False)

    def __getitem__(self, idx):
        return self.buffer(idx)

    def __setitem__(self, idx, val):
        self._set_buffer(idx, 1, val, False)

class Int32Array(TypeArray):
    def __init__(self, *args):
        super().__init__(*args)

    def _new(self, *args):
        if type(args[0]) == int:
            self.new_1(4, *args)
        else:
            self.new_2(4, *args)

    def buffer(self, idx):
        return self._buffer(idx, 4, True)

    def __getitem__(self, idx):
        return self.buffer(idx)

    def __setitem__(self, idx, val):
        self._set_buffer(idx, 4, val, True)

class UInt32Array(TypeArray):
    def __init__(self, *args):
        super().__init__(*args)

    def _new(self, *args):
        if type(args[0]) == int:
            self.new_1(4, *args)
        else:
            self.new_2(4, *args)

    def buffer(self, idx):
        return self._buffer(idx, 4, False)

    def __getitem__(self, idx):
        return self.buffer(idx)

    def __setitem__(self, idx, val):
        self._set_buffer(idx, 4, val, False)

class Digest:
    def __init__(self):
        self._offset = 0
        self._maxChunkLen = 65536
        self._padMaxChunkLen = 65600
        self._heap = ArrayBuffer(131072)
        self._h32 = Int32Array(self._heap)
        self._h8 = Int8Array(self._heap)

    def _initState(self, e, offset):
        self._offset = 0
        n = Int32Array(e, offset + 320, 5)
        n.debugName = "[_initState].n"
        n[0] = 1732584193
        n[1] = -271733879
        n[2] = -1732584194
        n[3] = 271733878
        n[4] = -1009589776
        # e.printInts(65600 + 320, 5)

    def paddingSize(self, e):
        e += 9
        while e % 64 > 0:
            e += 1
        return e
    
    def _padChunk(self, e, t):
        n = self.paddingSize(e)
        r = Int32Array(self._heap, 0, n >> 2)
        r.debugName = "[_padChunk].r"
        self._padChunk_1(r, e)
        self._padChunk_2(r, e, t)
        return n

    def _padChunk_1(self, e, t):
        n = UInt8Array(e.arrbuf)
        r = t % 4
        o = t - r
        if r == 0:
            n[ o + 3 ] = 0
        elif r == 1:
            n[ o + 2 ] = 0
        elif r == 2:
            n[ o + 1 ] = 0
        elif r == 3:
            n[ o + 0 ] = 0
        i = 1 + ( t >> 2 )
        while i < e.length:
            e[ i ] = 0
            i += 1

    def _padChunk_2(self, e, t, n):
        e[t >> 2] |= 128 << 24 - (t % 4 << 3)
        e[14 + (2 + (t >> 2) & -16)] = n // (1 << 29) | 0
        e[15 + (2 + (t >> 2) & -16)] = n << 3
    
    def _c(self, e, pos):
        n = Int32Array(e, pos + 320, 5)
        r = Int32Array(5)
        r[0] = x2d(n[0])
        r[1] = x2d(n[1])
        r[2] = x2d(n[2])
        r[3] = x2d(n[3])
        r[4] = x2d(n[4])
        return r

    # const char * e
    def _a2(self, e, _t, _n, r, o, i):
        u = 0
        a = i % 4
        s = (o + a) % 4
        c = o - s
        t = _t
        n = _n
        if a == 0:
            t[i] = ord(e[r + 3])
        if a <= 1:
            t[i + 1 - (a << 1) | 0] = ord(e[r + 2])
        if a <= 2:
            t[i + 2 - (a << 1) | 0] = ord(e[r + 1])
        if a <= 3:
            t[i + 3 - (a << 1) | 0] = ord(e[r])

        if not (o < s + (4 - a)):
            u = 4 - a
            while u < c:
                n[i + u >> 2] = ord(e[r + u]) << 24 | ord(e[r + u + 1]) << 16 | \
                    ord(e[r + u + 2]) << 8 | ord(e[r + u + 3])
                u = u + 4 | 0
            if s == 3:
                t[i + c + 1 | 0] = ord(e[r + c + 2])
            if s >= 2:
                t[i + c + 2 | 0] = ord(e[r + c + 1])
            if s >= 1:
                t[i + c + 3 | 0] = ord(e[r + c])
    
    # const char *e
    def _a(self, e, t, i, u, a, s):
        self._a2(e, t, i, u, a, s)
    
    # char *p
    def charCodeAt(self, p, idx):
        return ord(p[idx])
    
    # const char *e
    def _write(self, e, t, n, r = 0):
        self._a(e, self._h8, self._h32, t, n, r)
    
    def hash(self, e, t):
        r = Int32Array(self._heap)
        e = e | 0
        t = t | 0
        n = 0
        o = 0
        i = 0
        u = 0
        a = 0
        s = 0
        c = 0
        f = 0
        p = 0
        l = 0
        d = 0
        h = 0
        y = 0
        v = 0
        i = r[t + 320 >> 2] | 0
        a = r[t + 324 >> 2] | 0
        c = r[t + 328 >> 2] | 0
        p = r[t + 332 >> 2] | 0
        d = r[t + 336 >> 2] | 0
        n = 0
       
        while (n | 0) < (e | 0):
            u = i
            s = a
            f = c
            l = p
            h = d

            o = 0
            while (o | 0) < 64:
                v = r[n + o >> 2] | 0
                y = ((i << 5 | uint32(i) >> 27) + (a & c | ~a & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0
                d = p
                p = c
                c = a << 30 | uint32(a) >> 2
                a = i
                i = y
                r[e + o >> 2] = v
                o = o + 4 | 0
            
            o = e + 64 | 0
            while (o | 0) < (e + 80 | 0):
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | uint32(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31
                y = ((i << 5 | uint32(i) >> 27) + (a & c | ~a & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0
                d = p
                p = c
                c = a << 30 | uint32(a) >> 2
                a = i
                i = y
                r[o >> 2] = v
                o = o + 4 | 0
            
            o = e + 80 | 0
            while (o | 0) < (e + 160 | 0):
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | uint32(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31
                y = ((i << 5 | uint32(i) >> 27) + (a ^ c ^ p) | 0) + ((v + d | 0) + 1859775393 | 0) | 0
                d = p
                p = c
                c = a << 30 | uint32(a) >> 2
                a = i
                i = y
                r[o >> 2] = v
                o = o + 4 | 0
            
            o = e + 160 | 0
            while (o | 0) < (e + 240 | 0):
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | uint32(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31
                y = ((i << 5 | uint32(i) >> 27) + (a & c | a & p | c & p) | 0) + ((v + d | 0) - 1894007588 | 0) | 0
                d = p
                p = c
                c = a << 30 | uint32(a) >> 2
                a = i
                i = y
                r[o >> 2] = v
                o = o + 4 | 0
            
            o = e + 240 | 0
            while (o | 0) < (e + 320 | 0):
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | uint32(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31
                y = ((i << 5 | uint32(i) >> 27) + (a ^ c ^ p) | 0) + ((v + d | 0) - 899497514 | 0) | 0
                d = p
                p = c
                c = a << 30 | uint32(a) >> 2
                a = i
                i = y
                r[o >> 2] = v
                o = o + 4 | 0
            
            i = i + u | 0
            a = a + s | 0
            c = c + f | 0
            p = p + l | 0
            d = d + h | 0
            n = n + 64 | 0
        
        r[t + 320 >> 2] = i
        r[t + 324 >> 2] = a
        r[t + 328 >> 2] = c
        r[t + 332 >> 2] = p
        r[t + 336 >> 2] = d
    
    # const char *e
    def _coreCall(self, e, t, n, r, o):
        i = n
        self._write(e, t, n)
        if o:
            i = self._padChunk(n, r)
        self.hash(i, self._padMaxChunkLen)
    
    # return TypeArray
    # const char *e
    def rawDigest(self, e):
        t = len(e)
        self._initState(self._heap, self._padMaxChunkLen)
        n = 0
        r = self._maxChunkLen
        self._coreCall(e, n, t - n, t, True)
        v = self._c(self._heap, self._padMaxChunkLen)
        return v
    
    def toHex(self, e):
        t = UInt8Array(e)
        import io
        sbuf = io.StringIO()
        for o in range(e.byteLength):
            sbuf.write("%02x" % t[o])
        return sbuf.getvalue()
    
    # const char *e
    def digest(self, e):
        d1 = self.rawDigest(e)
        # d1.arrbuf.printBytes(0, 20)
        s = self.toHex(d1.arrbuf)
        return s

class Bytes:
    def __init__(self, capacity):
        self.length = 0
        self.capacity = capacity
        self.buf = bytearray(capacity)

    # char ch
    def push(self, ch):
        self.buf[self.length] = ch
        self.length += 1

    # return char
    def at(self, idx):
        return self.buf[idx]

    def print(self):
        for i in range(self.length):
            print(f"[{i}] = {self.at(i)}")

    def printu(self):
        for i in range(self.length):
            print(f"[{i}] = { uint8(self.at(i))}")

class Array32:
    def __init__(self, capacity):
        self.length = 0
        self.capacity = capacity
        self.buf = bytearray(capacity * 4)

    def __getitem__(self, idx):
        return self.at(idx)

    def __setitem__(self, idx, val):
        if (self.length <= idx):
            self.length = idx + 1
        val = int32(val)
        for i in range(4):
            self.buf[idx * 4 + i] = uint8(val >> i * 8)

    def at(self, idx):
        return int32p(self.buf, idx * 4)

    def print(self):
        for i in range(self.length):
            print(f"[{i}] = {self.buf[i]} ")

class Bin2Hex:
    # return char *
    # char *e
    def run(self, e):
        dv = self.u(e)
        r = self.wordsToBytes(dv)
        s = self.bytesToHex(r)
        return s

    # return  Array32
    # char *_e
    def u(self, _e):
        e = self.stringToBytes(_e)
        _a = self.bytesToWords(e)
        a = _a
        s = 8 * e.length
        c = 1732584193
        f = -271733879
        p = -1732584194
        l = 271733878 
        d = 0
        while d < a.length:
            a[d] = 16711935 & (a[d] << 8 | uint32(a[d]) >> 24) | 4278255360 & (a[d] << 24 | uint32(a[d]) >> 8)
            d += 1
        a[uint32(s) >> 5] |= 128 << s % 32
        a[14 + (uint32(s) + 64 >> 9 << 4)] = s
        
        d = 0
        while d < a.length:
            g = c
            b = f
            w = p
            x = l
            c = self._ff(c, f, p, l, a[d + 0], 7, -680876936)
            l = self._ff(l, c, f, p, a[d + 1], 12, -389564586)
            p = self._ff(p, l, c, f, a[d + 2], 17, 606105819)
            f = self._ff(f, p, l, c, a[d + 3], 22, -1044525330)
            c = self._ff(c, f, p, l, a[d + 4], 7, -176418897)
            l = self._ff(l, c, f, p, a[d + 5], 12, 1200080426)
            p = self._ff(p, l, c, f, a[d + 6], 17, -1473231341)
            f = self._ff(f, p, l, c, a[d + 7], 22, -45705983)
            c = self._ff(c, f, p, l, a[d + 8], 7, 1770035416)
            l = self._ff(l, c, f, p, a[d + 9], 12, -1958414417)
            p = self._ff(p, l, c, f, a[d + 10], 17, -42063)
            f = self._ff(f, p, l, c, a[d + 11], 22, -1990404162)
            c = self._ff(c, f, p, l, a[d + 12], 7, 1804603682)
            l = self._ff(l, c, f, p, a[d + 13], 12, -40341101)
            p = self._ff(p, l, c, f, a[d + 14], 17, -1502002290)
            f = self._ff(f, p, l, c, a[d + 15], 22, 1236535329)
            c = self._gg(c, f, p, l, a[d + 1], 5, -165796510)
            l = self._gg(l, c, f, p, a[d + 6], 9, -1069501632)
            p = self._gg(p, l, c, f, a[d + 11], 14, 643717713)
            f = self._gg(f, p, l, c, a[d + 0], 20, -373897302)
            c = self._gg(c, f, p, l, a[d + 5], 5, -701558691)
            l = self._gg(l, c, f, p, a[d + 10], 9, 38016083)
            p = self._gg(p, l, c, f, a[d + 15], 14, -660478335)
            f = self._gg(f, p, l, c, a[d + 4], 20, -405537848)
            c = self._gg(c, f, p, l, a[d + 9], 5, 568446438)
            l = self._gg(l, c, f, p, a[d + 14], 9, -1019803690)
            p = self._gg(p, l, c, f, a[d + 3], 14, -187363961)
            f = self._gg(f, p, l, c, a[d + 8], 20, 1163531501)
            c = self._gg(c, f, p, l, a[d + 13], 5, -1444681467)
            l = self._gg(l, c, f, p, a[d + 2], 9, -51403784)
            p = self._gg(p, l, c, f, a[d + 7], 14, 1735328473)
            f = self._gg(f, p, l, c, a[d + 12], 20, -1926607734)
            c = self._hh(c, f, p, l, a[d + 5], 4, -378558)
            l = self._hh(l, c, f, p, a[d + 8], 11, -2022574463)
            p = self._hh(p, l, c, f, a[d + 11], 16, 1839030562)
            f = self._hh(f, p, l, c, a[d + 14], 23, -35309556)
            c = self._hh(c, f, p, l, a[d + 1], 4, -1530992060)
            l = self._hh(l, c, f, p, a[d + 4], 11, 1272893353)
            p = self._hh(p, l, c, f, a[d + 7], 16, -155497632)
            f = self._hh(f, p, l, c, a[d + 10], 23, -1094730640)
            c = self._hh(c, f, p, l, a[d + 13], 4, 681279174)
            l = self._hh(l, c, f, p, a[d + 0], 11, -358537222)
            p = self._hh(p, l, c, f, a[d + 3], 16, -722521979)
            f = self._hh(f, p, l, c, a[d + 6], 23, 76029189)
            c = self._hh(c, f, p, l, a[d + 9], 4, -640364487)
            l = self._hh(l, c, f, p, a[d + 12], 11, -421815835)
            p = self._hh(p, l, c, f, a[d + 15], 16, 530742520)
            f = self._hh(f, p, l, c, a[d + 2], 23, -995338651)
            c = self._ii(c, f, p, l, a[d + 0], 6, -198630844)
            l = self._ii(l, c, f, p, a[d + 7], 10, 1126891415)
            p = self._ii(p, l, c, f, a[d + 14], 15, -1416354905)
            f = self._ii(f, p, l, c, a[d + 5], 21, -57434055)
            c = self._ii(c, f, p, l, a[d + 12], 6, 1700485571)
            l = self._ii(l, c, f, p, a[d + 3], 10, -1894986606)
            p = self._ii(p, l, c, f, a[d + 10], 15, -1051523)
            f = self._ii(f, p, l, c, a[d + 1], 21, -2054922799)
            c = self._ii(c, f, p, l, a[d + 8], 6, 1873313359)
            l = self._ii(l, c, f, p, a[d + 15], 10, -30611744)
            p = self._ii(p, l, c, f, a[d + 6], 15, -1560198380)
            f = self._ii(f, p, l, c, a[d + 13], 21, 1309151649)
            c = self._ii(c, f, p, l, a[d + 4], 6, -145523070)
            l = self._ii(l, c, f, p, a[d + 11], 10, -1120210379)
            p = self._ii(p, l, c, f, a[d + 2], 15, 718787259)
            f = self._ii(f, p, l, c, a[d + 9], 21, -343485551)
            c = uint32(int32(c) + int32(g)) >> 0
            f = uint32(int32(f) + int32(b)) >> 0
            p = uint32(int32(p) + int32(w)) >> 0
            l = uint32(int32(l) + int32(x)) >> 0

            d += 16

        arr = Array32(4)
        arr[0] = c
        arr[1] = f
        arr[2] = p
        arr[3] = l
        self.endianArray(arr)
        return arr

    # char *e
    def stringToBytes(self, e):
        t = Bytes(len(e) * 2 + 2)
        for n in range(len(e)):
            t.push(255 & ord(e[n]))
        return t

    def bytesToWords(self, e):
        _t = Array32(e.length)
        t = _t
        r = 0
        n = 0
        while n < e.length:
            # px = t[r >> 5] | (e.at(n) << 24 - r % 32)
            t[r >> 5] |= e.at(n) << 24 - r % 32
            n += 1
            r += 8
        return _t

    def wordsToBytes(self, e):
        t = Bytes(e.length * 8)
        n = 0
        while n < 32 * e.length:
            v = uint32(e.at(uint32(n) >> 5))
            m = uint32(v) >> 24 - n % 32 & 255
            t.push(uint8(m))
            n += 8
        return t

    # return  char *
    def bytesToHex(self, e):
        H = "0123456789abcdef"
        import io
        t = io.StringIO()
        for n in range(e.length):
            c1 = uint8(e.at(n)) >> 4
            t.write(H[c1])
            c2 = 15 & e.at(n)
            t.write(H[c2])
        rs = t.getvalue()
        return rs

    def _ff(self, e, t, n, r, o, i, u):
        a = int32(e) + int32(t & n | ~t & r) + int32((uint32(o) >> 0)) + int32(u)
        a = int32(a)
        m = int32((a << i | uint32(a) >> 32 - i) + int32(t))
        return int32(m)

    def _gg(self, e, t, n, r, o, i, u):
        a = int32(e) + int32(t & r | n & ~r) + int32(uint32(o) >> 0) + int32(u)
        a = int32(a)
        m = int32(a << i | uint32(a) >> 32 - i) + int32(t)
        return int32(m)

    def _hh(self, e, t, n, r, o, i, u):
        a = int32(e) + int32(t ^ n ^ r) + int32(uint32(o) >> 0) + int32(u)
        a = int32(a)
        m = int32(a << i | uint32(a) >> 32 - i) + int32(t)
        return int32(m)

    def _ii(self, e, t, n, r, o, i, u):
        a = int32(e) + int32(n ^ (t | ~r)) + int32(uint32(o) >> 0) + int32(u)
        m = int32(a << i | uint32(a) >> 32 - i) + int32(t)
        return int32(m)
    
    # return unsigned int 
    # unsigned int e
    def rotl(self, e, t):
        return uint32(e << t | uint32(e) >> 32 - t)

    def endianInt(self, e):
        return 16711935 & self.rotl(e, 8) | 4278255360 & self.rotl(e, 24)

    def endianArray(self, e):
        for t in range(e.length):
            e[t] = self.endianInt(e.at(t))
        return e

dig = Digest()
b2h = Bin2Hex()

def signByStr(urlParam):
	dx = dig.digest(urlParam)
	rs = b2h.run(dx)
	return rs

if __name__ == '__main__':
    import cls
    PX = 'app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz001255&sv=7.7.5'
    params = cls.signByStr(PX)
    print(params)
    print('================')

    # 
    params = signByStr(PX)
    print(params)

## 说明：  
#     python版的digest(urlParam)，在urlParam中含有中文时，会出问题
#     因为python中一个中文字符是当作一个字符来处理的，而C版本的则会当成多字节处理