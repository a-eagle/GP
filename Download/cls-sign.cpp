#pragma warning(disable : 4996)
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 小端 -> 大端
int x2d(int v) {
	unsigned char b0 = v & 0xff;
	unsigned char b1 = (v >> 8) & 0xff;
	unsigned char b2 = (v >> 16) & 0xff;
	unsigned char b3 = (v >> 24) & 0xff;
	return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
}

class ArrayBuffer {
public:
	char *buf;
	int byteLength;
protected:	
	bool needFree;
public:	
	ArrayBuffer(int length) {
		this->byteLength = length;
		this->needFree = true;
		this->buf = (char *)malloc(length);
		memset(this->buf, 0, length);
	}
	
	ArrayBuffer(ArrayBuffer *buf, int offset, int length) {
		this->byteLength = length;
		this->needFree = false;
		this->buf = (char *)(buf->buf) + offset;
	}
	
	void printBytes(int offset, int length) {
		char *p = buf + offset;
		for (char *pp = p; pp < p + length; ++pp) {
			printf("[%d] = %d \n", pp - p, (int)*pp);
		}
	}
	
	void printInts(int offset, int length) {
		char *p = buf + offset;
		int *start = (int *)p;
		for (int *pp = start; pp < start + length; ++pp) {
			printf("[%d] = %d \n", pp - start, *pp);
		}
	}
	
	~ArrayBuffer() {
		if (this->buf && this->needFree) {
			free(this->buf);
			this->buf = NULL;
			//printf("~ArrayBuffer free this = %p \n", this);
		}
			
	}
};

class TypeArray {
public:
	ArrayBuffer *arrbuf;
	int itemSize;
	int length;
	int byteLength;
	const char *debugName;
	
	TypeArray(int length, int itemSize) {
		this->itemSize = itemSize;
		this->length = length;
		this->byteLength = itemSize * length;
		this->arrbuf = new ArrayBuffer(this->byteLength);
		this->debugName = "";
	}
	
	TypeArray(ArrayBuffer* buf, int offset, int itemSize, int length) {
		if (length < 0) {
			int less = buf->byteLength - offset;
			length = less / itemSize;
		}
		this->itemSize = itemSize;
		this->length = length;
		this->byteLength = itemSize * length;
		this->arrbuf = new ArrayBuffer(buf, offset, length * itemSize);
		this->debugName = "";
	}
	
	char *buffer() {
		return (char *)this->arrbuf->buf;
	}
	
	~TypeArray() {
		delete this->arrbuf;
	}
};

class Int8Array : public TypeArray {
public:
	Int8Array(int length) : TypeArray(length, 1) {
	}
	
	Int8Array(ArrayBuffer* buf, int offset = 0, int length = -1) : TypeArray(buf, offset, 1, length) {
	}
	
	char *buffer() {
		return (char *)this->arrbuf->buf;
	}
	
	char & operator[](int idx) {
		return buffer()[idx];
	}
	~Int8Array() {
		//printf("~Int8Array : this = %p debugName = %s ;\n", this, this->debugName);
	}
};

class UInt8Array : public TypeArray {
public:
	UInt8Array(int length) : TypeArray(length, 1) {
	}
	
	UInt8Array(ArrayBuffer* buf, int offset = 0, int length = -1) : TypeArray(buf, offset, 1, length) {
	}
	
	unsigned char *buffer() {
		return (unsigned char *)this->arrbuf->buf;
	}
	unsigned char & operator[](int idx) {
		return buffer()[idx];
	}
	~UInt8Array() {
		//printf("~UInt8Array : this = %p debugName = %s ;\n", this, this->debugName);
	}
};

class Int32Array : public TypeArray {
public:
	Int32Array(int length) : TypeArray(length, 4) {
	}
	
	Int32Array(ArrayBuffer* buf, int offset = 0, int length = -1) : TypeArray(buf, offset, 4, length) {
	}
	
	int *buffer() {
		return (int *)this->arrbuf->buf;
	}
	int & operator[](int idx) {
		return buffer()[idx];
	}
	~Int32Array() {
		//printf("~Int32Array : this = %p debugName = %s ;\n", this, this->debugName);
	}
};

class UInt32Array : public TypeArray {
public:
	UInt32Array(int length) : TypeArray(length, 4) {
	}
	
	UInt32Array(ArrayBuffer* buf, int offset = 0, int length = -1) : TypeArray(buf, offset, 4, length) {
	}
	
	unsigned int *buffer() {
		return (unsigned int *)this->arrbuf->buf;
	}
	unsigned int & operator[](int idx) {
		return buffer()[idx];
	}
};

class Digest {
public:
	int _offset;
	int _maxChunkLen;
	int _padMaxChunkLen;
	ArrayBuffer *_heap;
	Int32Array *_h32;
	Int8Array *_h8;
	
	Digest() {
		this->_offset = 0;
		this->_maxChunkLen = 65536;
		this->_padMaxChunkLen = 65600;
		this->_heap = new ArrayBuffer(131072);
		this->_h32 = new Int32Array(this->_heap);
		this->_h8 = new Int8Array(this->_heap);
		//printf("_heap = %p, _h32 = %p, _h8 = %p \n", this->_heap, this->_h32, this->_h8);
	}
	
	void _initState(ArrayBuffer *e, int offset) {
		this->_offset = 0;
		Int32Array n(e, offset + 320, 5);
		n.debugName = "[_initState].n";
		int *buf = n.buffer();
		buf[0] = 1732584193;
		buf[1] = -271733879;
		buf[2] = -1732584194;
		buf[3] = 271733878;
		buf[4] = -1009589776;
		// e->printInts(65600 + 320, 5);
	}
	
	int paddingSize( int e ) { // padding size
		for ( e += 9; e % 64 > 0; e += 1 );
		return e;
	}
	
	int _padChunk(int e, int t) {
		int n = paddingSize(e);
		Int32Array r(this->_heap, 0, n >> 2);
		r.debugName = "[_padChunk].r";
		_padChunk_1(r, e);
		_padChunk_2(r, e, t);
		return n;
	}

	void _padChunk_1(Int32Array &e, int t){
        UInt8Array n(e.arrbuf);
		int r = t % 4;
		int o = t - r;
		switch ( r ) {
			case 0:
				n[ o + 3 ] = 0;
			case 1:
				n[ o + 2 ] = 0;
			case 2:
				n[ o + 1 ] = 0;
			case 3:
				n[ o + 0 ] = 0;
		}
		for ( int i = 1 + ( t >> 2 ); i < e.length; i++ )
			e[ i ] = 0;
    }
	void _padChunk_2(Int32Array &e, int t, int n) {
		e[t >> 2] |= 128 << 24 - (t % 4 << 3);
		e[14 + (2 + (t >> 2) & -16)] = n / (1 << 29) | 0;
		e[15 + (2 + (t >> 2) & -16)] = n << 3;
	}

    
    Int32Array * _c(ArrayBuffer *e, int pos) {
		Int32Array n(e, pos + 320, 5 );
		Int32Array *r = new Int32Array( 5 );
		int * buf = r->buffer();
		buf[0] = x2d(n[0]);
		buf[1] = x2d(n[1]);
		buf[2] = x2d(n[2]);
		buf[3] = x2d(n[3]);
		buf[4] = x2d(n[4]);
		//n.arrbuf->printInts(0, 5);
		//r->arrbuf->printInts(0, 5);
		return r;
	}

	void _a2(const char *e, Int8Array *_t, Int32Array *_n, int r, int o, int i) {
		int u = 0;
		int a = i % 4;
		int s = (o + a) % 4;
		int c = o - s;
		Int8Array &t = *_t;
		Int32Array &n = *_n;
		switch (a) {
		case 0:
			t[i] = e[r + 3];
		case 1:
			t[i + 1 - (a << 1) | 0] = e[r + 2];
		case 2:
			t[i + 2 - (a << 1) | 0] = e[r + 1];
		case 3:
			t[i + 3 - (a << 1) | 0] = e[r];
		}
		if (!(o < s + (4 - a))) {
			for (u = 4 - a; u < c; u = u + 4 | 0)
				n[i + u >> 2] = (int)e[r + u] << 24 | (int)e[r + u + 1] << 16 | (int)e[r + u + 2] << 8 | (int)e[r + u + 3];
			switch (s) {
			case 3:
				t[i + c + 1 | 0] = (int)e[r + c + 2];
			case 2:
				t[i + c + 2 | 0] = (int)e[r + c + 1];
			case 1:
				t[i + c + 3 | 0] = (int)e[r + c];
			}
		}
	}
	
	void _a(const char *e, Int8Array *t, Int32Array *i, int u, int a, int s) {
		_a2(e, t, i, u, a, s);
	}
	
	int charCodeAt(char *p, int idx) {
		return (int)p[idx];
	}
	
	void _write(const char *e, int t, int n, int r = 0) {
		this->_a(e, this->_h8, this->_h32, t, n, r);
	}
	
	void hash(int e, int t) {
		Int32Array r(this->_heap);
		e = e | 0;
        t = t | 0;
        int n = 0,
            o = 0,
            i = 0,
            u = 0,
            a = 0,
            s = 0,
            c = 0,
            f = 0,
            p = 0,
            l = 0,
            d = 0,
            h = 0,
            y = 0,
            v = 0;
        i = r[t + 320 >> 2] | 0;
        a = r[t + 324 >> 2] | 0;
        c = r[t + 328 >> 2] | 0;
        p = r[t + 332 >> 2] | 0;
        d = r[t + 336 >> 2] | 0;
        for (n = 0;
            (n | 0) < (e | 0); n = n + 64 | 0) {
            u = i;
            s = a;
            f = c;
            l = p;
            h = d;
            for (o = 0;
                (o | 0) < 64; o = o + 4 | 0) {
                v = r[n + o >> 2] | 0;
                y = ((i << 5 | (unsigned int)i >> 27) + (a & c | ~a & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0;
                d = p;
                p = c;
                c = a << 30 | (unsigned int)a >> 2;
                a = i;
                i = y;
                r[e + o >> 2] = v;
            }
            for (o = e + 64 | 0;
                (o | 0) < (e + 80 | 0); o = o + 4 | 0) {
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (unsigned int)(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31;
                y = ((i << 5 | (unsigned int)i >> 27) + (a & c | ~a & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0;
                d = p;
                p = c;
                c = a << 30 | (unsigned int)a >> 2;
                a = i;
                i = y;
                r[o >> 2] = v;
            }
            for (o = e + 80 | 0;
                (o | 0) < (e + 160 | 0); o = o + 4 | 0) {
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (unsigned int)(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31;
                y = ((i << 5 | (unsigned int)i >> 27) + (a ^ c ^ p) | 0) + ((v + d | 0) + 1859775393 | 0) | 0;
                d = p;
                p = c;
                c = a << 30 | (unsigned int)a >> 2;
                a = i;
                i = y;
                r[o >> 2] = v;
            }
            for (o = e + 160 | 0;
                (o | 0) < (e + 240 | 0); o = o + 4 | 0) {
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (unsigned int)(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31;
                y = ((i << 5 | (unsigned int)i >> 27) + (a & c | a & p | c & p) | 0) + ((v + d | 0) - 1894007588 | 0) | 0;
                d = p;
                p = c;
                c = a << 30 | (unsigned int)a >> 2;
                a = i;
                i = y;
                r[o >> 2] = v;
            }
            for (o = e + 240 | 0;
                (o | 0) < (e + 320 | 0); o = o + 4 | 0) {
                v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (unsigned int)(r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >> 31;
                y = ((i << 5 | (unsigned int)i >> 27) + (a ^ c ^ p) | 0) + ((v + d | 0) - 899497514 | 0) | 0;
                d = p;
                p = c;
                c = a << 30 | (unsigned int)a >> 2;
                a = i;
                i = y;
                r[o >> 2] = v;
            }
            i = i + u | 0;
            a = a + s | 0;
            c = c + f | 0;
            p = p + l | 0;
            d = d + h | 0;
        }
        r[t + 320 >> 2] = i;
        r[t + 324 >> 2] = a;
        r[t + 328 >> 2] = c;
        r[t + 332 >> 2] = p;
        r[t + 336 >> 2] = d;
	}
	
	void _coreCall(const char *e, int t, int n, int r, bool o) {
		int i = n;
		this->_write(e, t, n);
		if (o) 
			i = this->_padChunk(n, r);
		this->hash(i, this->_padMaxChunkLen);
	}
	
	TypeArray *rawDigest(const char *e) {
		int t = strlen(e);
		this->_initState(this->_heap, this->_padMaxChunkLen);
		int n = 0, r = this->_maxChunkLen;
		this->_coreCall(e, n, t - n, t, true);
		Int32Array *v = this->_c(this->_heap, this->_padMaxChunkLen);
		return v;
	}
	
	char *toHex(ArrayBuffer *e) {
		UInt8Array t(e);
		int LEN = e->byteLength * 2 + 1;
		char *r = (char *)malloc(LEN);
		memset(r, 0, LEN);
		for (int o = 0; o < e->byteLength; o++) {
			char tmp[4] = {0};
			sprintf(tmp, "%02x", t[o]);
			strcat(r, tmp);
		}
		return r;
	}
	
	char *digest(const char *e) {
		TypeArray *d1 = this->rawDigest(e);
		//d1->arrbuf->printBytes(0, 20);
		char *s = this->toHex(d1->arrbuf);
		delete d1;
		//printf("[digest] = [%s] \n", s);
		return s;
	}

};

class Bytes {
public:
	int capacity;
	char *buf;
	int length;

	Bytes(int capacity) {
		this->length = 0;
		this->capacity = capacity;
		this->buf = (char *)malloc(capacity);
		memset(this->buf, 0, capacity);
	}

	void push(char ch) {
		this->buf[this->length++] = ch;
	}

	char at(int idx) {
		return this->buf[idx];
	}

	void print() {
		for (int i = 0; i < length; i++) {
			printf("[%d] = %d \n", i, at(i));
		}
	}

	void printu() {
		for (int i = 0; i < length; i++) {
			printf("[%d] = %d \n", i, (unsigned char)at(i));
		}
	}

	~Bytes() {
		free(this->buf);
		this->buf = NULL;
	}
};

class Array32 {
public:
	int capacity;
	int *buf;
	int length;

	Array32(int capacity) {
		this->length = 0;
		this->capacity = capacity;
		this->buf = (int *)malloc(capacity * sizeof(int));
		memset(this->buf, 0, capacity * sizeof(int));
	}

	int & operator[](int idx) {
		if (this->length <= idx) {
			this->length = idx + 1;
		}
		return this->buf[idx];
	}

	int at(int idx) {
		return this->buf[idx];
	}

	void print() {
		for (int i = 0; i < this->length; i++) {
			printf("[%d] = %d \n", i, this->buf[i]);
		}
	}

	~Array32() {
		free(this->buf);
		this->buf = NULL;
	}
};

class Bin2Hex {
public:
	Bin2Hex() {
	}

	char *run(char *e) {
		Array32 *dv = u(e);
		Bytes *r = wordsToBytes(dv);
		//r->printu();
		char *s = bytesToHex(r);
		delete r;
		delete dv;
		return s;
	}

	Array32 *u(char *_e) {
		Bytes *e = stringToBytes(_e);
		Array32 *_a = bytesToWords(e);
		Array32 &a = *_a;
		int s = 8 * e->length;
		int c = 1732584193, f = -271733879, p = -1732584194, l = 271733878, d = 0; // TODO: may be unsigned int ?
		for (; d < a.length; d++) {
			a[d] = 16711935 & (a[d] << 8 | (unsigned int)a[d] >> 24) | 4278255360 & (a[d] << 24 | (unsigned int)a[d] >> 8);
		}
		a[(unsigned int)s >> 5] |= 128 << s % 32;
		a[14 + ((unsigned int)s + 64 >> 9 << 4)] = s;
		// a.print();
		for (d = 0; d < a.length; d += 16) {
			int g = c,
				b = f,
				w = p,
				x = l;
			c = _ff(c, f, p, l, a[d + 0], 7, -680876936),
			l = _ff(l, c, f, p, a[d + 1], 12, -389564586),
			p = _ff(p, l, c, f, a[d + 2], 17, 606105819),
			f = _ff(f, p, l, c, a[d + 3], 22, -1044525330),
			c = _ff(c, f, p, l, a[d + 4], 7, -176418897),
			l = _ff(l, c, f, p, a[d + 5], 12, 1200080426),
			p = _ff(p, l, c, f, a[d + 6], 17, -1473231341),
			f = _ff(f, p, l, c, a[d + 7], 22, -45705983),
			c = _ff(c, f, p, l, a[d + 8], 7, 1770035416),
			l = _ff(l, c, f, p, a[d + 9], 12, -1958414417),
			p = _ff(p, l, c, f, a[d + 10], 17, -42063),
			f = _ff(f, p, l, c, a[d + 11], 22, -1990404162),
			c = _ff(c, f, p, l, a[d + 12], 7, 1804603682),
			l = _ff(l, c, f, p, a[d + 13], 12, -40341101),
			p = _ff(p, l, c, f, a[d + 14], 17, -1502002290),
			c = _gg(c, f = _ff(f, p, l, c, a[d + 15], 22, 1236535329), p, l, a[d + 1], 5, -165796510),
			l = _gg(l, c, f, p, a[d + 6], 9, -1069501632),
			p = _gg(p, l, c, f, a[d + 11], 14, 643717713),
			f = _gg(f, p, l, c, a[d + 0], 20, -373897302),
			c = _gg(c, f, p, l, a[d + 5], 5, -701558691),
			l = _gg(l, c, f, p, a[d + 10], 9, 38016083),
			p = _gg(p, l, c, f, a[d + 15], 14, -660478335),
			f = _gg(f, p, l, c, a[d + 4], 20, -405537848),
			c = _gg(c, f, p, l, a[d + 9], 5, 568446438),
			l = _gg(l, c, f, p, a[d + 14], 9, -1019803690),
			p = _gg(p, l, c, f, a[d + 3], 14, -187363961),
			f = _gg(f, p, l, c, a[d + 8], 20, 1163531501),
			c = _gg(c, f, p, l, a[d + 13], 5, -1444681467),
			l = _gg(l, c, f, p, a[d + 2], 9, -51403784),
			p = _gg(p, l, c, f, a[d + 7], 14, 1735328473),
			c = _hh(c, f = _gg(f, p, l, c, a[d + 12], 20, -1926607734), p, l, a[d + 5], 4, -378558),
			l = _hh(l, c, f, p, a[d + 8], 11, -2022574463),
			p = _hh(p, l, c, f, a[d + 11], 16, 1839030562),
			f = _hh(f, p, l, c, a[d + 14], 23, -35309556),
			c = _hh(c, f, p, l, a[d + 1], 4, -1530992060),
			l = _hh(l, c, f, p, a[d + 4], 11, 1272893353),
			p = _hh(p, l, c, f, a[d + 7], 16, -155497632),
			f = _hh(f, p, l, c, a[d + 10], 23, -1094730640),
			c = _hh(c, f, p, l, a[d + 13], 4, 681279174),
			l = _hh(l, c, f, p, a[d + 0], 11, -358537222),
			p = _hh(p, l, c, f, a[d + 3], 16, -722521979),
			f = _hh(f, p, l, c, a[d + 6], 23, 76029189),
			c = _hh(c, f, p, l, a[d + 9], 4, -640364487),
			l = _hh(l, c, f, p, a[d + 12], 11, -421815835),
			p = _hh(p, l, c, f, a[d + 15], 16, 530742520),
			c = _ii(c, f = _hh(f, p, l, c, a[d + 2], 23, -995338651), p, l, a[d + 0], 6, -198630844),
			l = _ii(l, c, f, p, a[d + 7], 10, 1126891415),
			p = _ii(p, l, c, f, a[d + 14], 15, -1416354905),
			f = _ii(f, p, l, c, a[d + 5], 21, -57434055),
			c = _ii(c, f, p, l, a[d + 12], 6, 1700485571),
			l = _ii(l, c, f, p, a[d + 3], 10, -1894986606),
			p = _ii(p, l, c, f, a[d + 10], 15, -1051523),
			f = _ii(f, p, l, c, a[d + 1], 21, -2054922799),
			c = _ii(c, f, p, l, a[d + 8], 6, 1873313359),
			l = _ii(l, c, f, p, a[d + 15], 10, -30611744),
			p = _ii(p, l, c, f, a[d + 6], 15, -1560198380),
			f = _ii(f, p, l, c, a[d + 13], 21, 1309151649),
			c = _ii(c, f, p, l, a[d + 4], 6, -145523070),
			l = _ii(l, c, f, p, a[d + 11], 10, -1120210379),
			p = _ii(p, l, c, f, a[d + 2], 15, 718787259),
			f = _ii(f, p, l, c, a[d + 9], 21, -343485551),
			c = (unsigned int)(c + g) >> 0,
			f = (unsigned int)(f + b) >> 0,
			p = (unsigned int)(p + w) >> 0,
			l = (unsigned int)(l + x) >> 0;
		}
		unsigned int cc = (unsigned int)c;
		unsigned int cf = (unsigned int)f;
		unsigned int cp = (unsigned int)p;
		unsigned int cl = (unsigned int)l;

		Array32 *arr = new Array32(4);
		arr->operator[](0) = c;
		arr->operator[](1) = f;
		arr->operator[](2) = p;
		arr->operator[](3) = l;
		endianArray(arr);

		//arr->print();
		return arr;
	}

	// e 必须是单字节的字符串
	Bytes *stringToBytes(char *e) {
		// unescape( encodeURIComponent( e )
		Bytes *t = new Bytes(strlen(e) * 2 + 2);
		for (int n = 0; n < strlen(e); n++)
			t->push(255 & e[n]);
		return t;
	}

	Array32 *bytesToWords(Bytes *e) {
		Array32 *_t = new Array32(e->length);
		Array32 &t = *_t;
		unsigned int r = 0;
		for (int n = 0; n < e->length; n++, r += 8) 
			t[r >> 5] |= e->at(n) << 24 - r % 32;
		return _t;
	}

	Bytes *wordsToBytes(Array32 *e) {
		Bytes *t = new Bytes(e->length * 8);
		for (int n = 0; n < 32 * e->length; n += 8) {
			unsigned int v = (unsigned int)e->at((unsigned int)n >> 5);
			char m = (unsigned int)v >> 24 - n % 32 & 255;
			t->push((unsigned char)m);
		}
		return t;
	}

	char *bytesToHex(Bytes *e) {
		const char *H = "0123456789abcdef";
		char *t = (char *)malloc(e->length * 2 + 1);
		memset(t, 0, e->length * 2 + 1);
		for (int n = 0; n < e->length; n++) {
			char tmp[4] = {0};
			int c1 = (unsigned char)e->at(n) >> 4;
			tmp[0] = H[c1];
			int c2 = 15 & e->at(n);
			tmp[1] = H[c2];
			strcat(t, tmp);
		}
		return t;
	}

	int _ff(int e, int t, int n, int r, int o, int i, int u) {
		int a = e + (t & n | ~t & r) + ((unsigned int)o >> 0) + u;
		return (a << i | (unsigned int)a >> 32 - i) + t;
	}
	int _gg(int e, int t, int n, int r, int o, int i, int u) {
		int a = e + (t & r | n & ~r) + ((unsigned int)o >> 0) + u;
		return (a << i | (unsigned int)a >> 32 - i) + t;
	}
	int _hh (int e, int t, int n, int r, int o, int i, int u) {
		int a = e + (t ^ n ^ r) + ((unsigned int)o >> 0) + u;
		return (a << i | (unsigned int)a >> 32 - i) + t;
	}
	int _ii(int e, int t, int n, int r, int o, int i, int u) {
		int a = e + (n ^ (t | ~r)) + ((unsigned int)o >> 0) + u;
		return (a << i | (unsigned int)a >> 32 - i) + t;
	}
	
	unsigned int rotl(unsigned int e, int t) {
		return e << t | (unsigned int)e >> 32 - t;
	}

	unsigned int endianInt(unsigned int e) {
		return 16711935 & rotl(e, 8) | 4278255360 & rotl(e, 24);
	}

	Array32* endianArray(Array32 *e) {
		for (int t = 0; t < e->length; t++)
			e->operator[](t) = endianInt(e->at(t));
		return e;
	}

};

Digest _digest_obj;
Bin2Hex _b2h_obj;

extern "C" {
	// urlParam = "a=xx&b=xx&c=xxx"
	// 要求： url 参数名必须是从小到大的顺序, 参数a必须是b的前面
	__declspec(dllexport) char *digest(const char *urlParam);
	__declspec(dllexport) char* test(char *urlParam);
	__declspec(dllexport) int add(int a, int b);
}

char *digest(const char *urlParam) {
	char *dx = _digest_obj.digest(urlParam);
	char *rs = _b2h_obj.run(dx);
	free(dx);
	return rs;
}

char * test(char *urlParam) {
	char *p = (char *)malloc(1024);
	*p = 0;
	strcpy(p, urlParam);
	strcat(p, "-HELLO");
	printf("CO CAO \n");
	//printf("call test() %s\n", urlParam);
	return p;
}

int add(int a, int b) {
	// printf("Add %d + %d \n", a, b);
	return a + b;
}


int main() {
	Digest d;
	Bin2Hex bh;
	
	const char *s = "app=CailianpressWeb&fields=date,minute,last_px,business_balance,business_amount,open_px,preclose_px,av_px&os=web&secu_code=sz001255&sv=7.7.5";
	char *dx = d.digest(s);
	printf("%s\n", dx);
	char *rs = bh.run(dx);
	free(dx);
	printf("rs = %s \n", rs);
	
	printf("\n-------------\n");
	s = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012";
	dx = d.digest(s);
	printf("%s\n", dx);
	rs = bh.run(dx);
	free(dx);
	printf("rs = %s \n", rs);
}





