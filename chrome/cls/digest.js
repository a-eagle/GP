
class ClsDigest  {
    constructor() {
		this._offset = 0;
		this._maxChunkLen = 65536;
		this._padMaxChunkLen = 65600;
		this._heap = new ArrayBuffer(131072);
		this._h32 = new Int32Array(this._heap);
		this._h8 = new Int8Array(this._heap);
	}

    _initState(e, offset) {
		this._offset = 0;
        let buf = new Int32Array(e, offset + 320, 5);
		buf[0] = 1732584193;
		buf[1] = -271733879;
		buf[2] = -1732584194;
		buf[3] = 271733878;
		buf[4] = -1009589776;
	}

    paddingSize(e) { // padding size
		for (e += 9; e % 64 > 0; e += 1 );
		return e;
	}

    _padChunk(e, t) {
		let n = this.paddingSize(e);
        let r = new Int32Array(this._heap, 0, n >> 2);
		this._padChunk_1(r, e);
		this._padChunk_2(r, e, t);
		return n;
	}

    _padChunk_1(e, t){
        let n = new Uint8Array(e.buffer)
		let r = t % 4;
		let o = t - r;
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
		for (let i = 1 + ( t >> 2 ); i < e.length; i++ )
			e[ i ] = 0;
    }

    _padChunk_2(e, t, n) {
		e[t >> 2] |= 128 << 24 - (t % 4 << 3);
		e[14 + (2 + (t >> 2) & -16)] = n / (1 << 29) | 0;
		e[15 + (2 + (t >> 2) & -16)] = n << 3;
	}

    x2d(v) {
        let b0 = v & 0xff;
        let b1 = (v >> 8) & 0xff;
        let b2 = (v >> 16) & 0xff;
        let b3 = (v >> 24) & 0xff;
        return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3;
    }

    _c(e, pos) {
		let n = new Int32Array(e, pos + 320, 5);
		let buf = new Int32Array(5);
		buf[0] = this.x2d(n[0]);
		buf[1] = this.x2d(n[1]);
		buf[2] = this.x2d(n[2]);
		buf[3] = this.x2d(n[3]);
		buf[4] = this.x2d(n[4]);
		return buf;
	}

    _a2(e, t, n, r, o, i) {
		let u = 0;
		let a = i % 4;
		let s = (o + a) % 4;
		let c = o - s;
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
				n[i + u >> 2] = e[r + u] << 24 | e[r + u + 1] << 16 | e[r + u + 2] << 8 | e[r + u + 3];
			switch (s) {
			case 3:
				t[i + c + 1 | 0] = e[r + c + 2];
			case 2:
				t[i + c + 2 | 0] = e[r + c + 1];
			case 1:
				t[i + c + 3 | 0] = e[r + c];
			}
		}
	}

    _write(e, t, n, r) {
        r = r || 0
		this._a2(e, this._h8, this._h32, t, n, r);
	}
    
    _coreCall(e, t, n, r, o) {
        let i = n;
        this._write(e, t, n);
        if (o)
            i = this._padChunk(n, r);
        this.hash(i, this._padMaxChunkLen);
    }
    
    rawDigest(e) {
        var t = e.byteLength || e.length || e.size || 0;
        this._initState(this._heap, this._padMaxChunkLen);
        var n = 0, r = this._maxChunkLen;
        this._coreCall(e, n, t - n, t, !0);
        return this._c(this._heap, this._padMaxChunkLen)
    }

    toHex(e) {
        for (var n = new Array(256), r = 0; r < 256; r++)
            n[r] = (r < 16 ? "0" : "") + r.toString(16);
		let t = new Uint8Array(e);
        r = new Array(e.byteLength);
		for (let o = 0; o < r.length; o++) {
            r[o] = n[t[o]];
		}
		return r.join("");
	}
	
	digest(e) {
		let d1 = this.rawDigest(e);
		let s = this.toHex(d1);
		return s;
	}

    hash(e, t) {
        let r = new Int32Array(this._heap);
		e = e | 0;
        t = t | 0;
        let n = 0,
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
            u = r[t + 324 >> 2] | 0;
            c = r[t + 328 >> 2] | 0;
            p = r[t + 332 >> 2] | 0;
            d = r[t + 336 >> 2] | 0;
            for (n = 0; (n | 0) < (e | 0); n = n + 64 | 0) {
                a = i;
                s = u;
                f = c;
                l = p;
                h = d;
                for (o = 0; (o | 0) < 64; o = o + 4 | 0) {
                    v = r[n + o >> 2] | 0;
                    y = ((i << 5 | i >>> 27) + (u & c | ~u & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0;
                    d = p;
                    p = c;
                    c = u << 30 | u >>> 2;
                    u = i;
                    i = y;
                    r[e + o >> 2] = v
                }
                for (o = e + 64 | 0; (o | 0) < (e + 80 | 0); o = o + 4 | 0) {
                    v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >>> 31;
                    y = ((i << 5 | i >>> 27) + (u & c | ~u & p) | 0) + ((v + d | 0) + 1518500249 | 0) | 0;
                    d = p;
                    p = c;
                    c = u << 30 | u >>> 2;
                    u = i;
                    i = y;
                    r[o >> 2] = v
                }
                for (o = e + 80 | 0; (o | 0) < (e + 160 | 0); o = o + 4 | 0) {
                    v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >>> 31;
                    y = ((i << 5 | i >>> 27) + (u ^ c ^ p) | 0) + ((v + d | 0) + 1859775393 | 0) | 0;
                    d = p;
                    p = c;
                    c = u << 30 | u >>> 2;
                    u = i;
                    i = y;
                    r[o >> 2] = v
                }
                for (o = e + 160 | 0; (o | 0) < (e + 240 | 0); o = o + 4 | 0) {
                    v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >>> 31;
                    y = ((i << 5 | i >>> 27) + (u & c | u & p | c & p) | 0) + ((v + d | 0) - 1894007588 | 0) | 0;
                    d = p;
                    p = c;
                    c = u << 30 | u >>> 2;
                    u = i;
                    i = y;
                    r[o >> 2] = v
                }
                for (o = e + 240 | 0; (o | 0) < (e + 320 | 0); o = o + 4 | 0) {
                    v = (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) << 1 | (r[o - 12 >> 2] ^ r[o - 32 >> 2] ^ r[o - 56 >> 2] ^ r[o - 64 >> 2]) >>> 31;
                    y = ((i << 5 | i >>> 27) + (u ^ c ^ p) | 0) + ((v + d | 0) - 899497514 | 0) | 0;
                    d = p;
                    p = c;
                    c = u << 30 | u >>> 2;
                    u = i;
                    i = y;
                    r[o >> 2] = v
                }
                i = i + a | 0;
                u = u + s | 0;
                c = c + f | 0;
                p = p + l | 0;
                d = d + h | 0
            }
            r[t + 320 >> 2] = i;
            r[t + 324 >> 2] = u;
            r[t + 328 >> 2] = c;
            r[t + 332 >> 2] = p;
            r[t + 336 >> 2] = d;
	}
}

class ClsBin2Hex {
    run(e) {
        let dv = this.u(e);
        let r = this.wordsToBytes(dv);
        let s = this.bytesToHex(r);
        return s;
    }
    
    u(_e) {
        let e = this.stringToBytes(_e);
        let a = this.bytesToWords(e);
        let s = 8 * e.length;
        let c = 1732584193, f = -271733879, p = -1732584194, l = 271733878, d = 0;
        for (; d < a.length; d++) {
            a[d] = 16711935 & (a[d] << 8 | a[d] >>> 24) | 4278255360 & (a[d] << 24 | a[d] >>> 8);
        }
        a[s >>> 5] |= 128 << s % 32;
        a[14 + (s + 64 >>> 9 << 4)] = s;
        for (d = 0; d < a.length; d += 16) {
            let g = c,
                b = f,
                w = p,
                x = l;
            c = this._ff(c, f, p, l, a[d + 0], 7, -680876936),
            l = this._ff(l, c, f, p, a[d + 1], 12, -389564586),
            p = this._ff(p, l, c, f, a[d + 2], 17, 606105819),
            f = this._ff(f, p, l, c, a[d + 3], 22, -1044525330),
            c = this._ff(c, f, p, l, a[d + 4], 7, -176418897),
            l = this._ff(l, c, f, p, a[d + 5], 12, 1200080426),
            p = this._ff(p, l, c, f, a[d + 6], 17, -1473231341),
            f = this._ff(f, p, l, c, a[d + 7], 22, -45705983),
            c = this._ff(c, f, p, l, a[d + 8], 7, 1770035416),
            l = this._ff(l, c, f, p, a[d + 9], 12, -1958414417),
            p = this._ff(p, l, c, f, a[d + 10], 17, -42063),
            f = this._ff(f, p, l, c, a[d + 11], 22, -1990404162),
            c = this._ff(c, f, p, l, a[d + 12], 7, 1804603682),
            l = this._ff(l, c, f, p, a[d + 13], 12, -40341101),
            p = this._ff(p, l, c, f, a[d + 14], 17, -1502002290),
            c = this._gg(c, f = this._ff(f, p, l, c, a[d + 15], 22, 1236535329), p, l, a[d + 1], 5, -165796510),
            l = this._gg(l, c, f, p, a[d + 6], 9, -1069501632),
            p = this._gg(p, l, c, f, a[d + 11], 14, 643717713),
            f = this._gg(f, p, l, c, a[d + 0], 20, -373897302),
            c = this._gg(c, f, p, l, a[d + 5], 5, -701558691),
            l = this._gg(l, c, f, p, a[d + 10], 9, 38016083),
            p = this._gg(p, l, c, f, a[d + 15], 14, -660478335),
            f = this._gg(f, p, l, c, a[d + 4], 20, -405537848),
            c = this._gg(c, f, p, l, a[d + 9], 5, 568446438),
            l = this._gg(l, c, f, p, a[d + 14], 9, -1019803690),
            p = this._gg(p, l, c, f, a[d + 3], 14, -187363961),
            f = this._gg(f, p, l, c, a[d + 8], 20, 1163531501),
            c = this._gg(c, f, p, l, a[d + 13], 5, -1444681467),
            l = this._gg(l, c, f, p, a[d + 2], 9, -51403784),
            p = this._gg(p, l, c, f, a[d + 7], 14, 1735328473),
            c = this._hh(c, f = this._gg(f, p, l, c, a[d + 12], 20, -1926607734), p, l, a[d + 5], 4, -378558),
            l = this._hh(l, c, f, p, a[d + 8], 11, -2022574463),
            p = this._hh(p, l, c, f, a[d + 11], 16, 1839030562),
            f = this._hh(f, p, l, c, a[d + 14], 23, -35309556),
            c = this._hh(c, f, p, l, a[d + 1], 4, -1530992060),
            l = this._hh(l, c, f, p, a[d + 4], 11, 1272893353),
            p = this._hh(p, l, c, f, a[d + 7], 16, -155497632),
            f = this._hh(f, p, l, c, a[d + 10], 23, -1094730640),
            c = this._hh(c, f, p, l, a[d + 13], 4, 681279174),
            l = this._hh(l, c, f, p, a[d + 0], 11, -358537222),
            p = this._hh(p, l, c, f, a[d + 3], 16, -722521979),
            f = this._hh(f, p, l, c, a[d + 6], 23, 76029189),
            c = this._hh(c, f, p, l, a[d + 9], 4, -640364487),
            l = this._hh(l, c, f, p, a[d + 12], 11, -421815835),
            p = this._hh(p, l, c, f, a[d + 15], 16, 530742520),
            c = this._ii(c, f = this._hh(f, p, l, c, a[d + 2], 23, -995338651), p, l, a[d + 0], 6, -198630844),
            l = this._ii(l, c, f, p, a[d + 7], 10, 1126891415),
            p = this._ii(p, l, c, f, a[d + 14], 15, -1416354905),
            f = this._ii(f, p, l, c, a[d + 5], 21, -57434055),
            c = this._ii(c, f, p, l, a[d + 12], 6, 1700485571),
            l = this._ii(l, c, f, p, a[d + 3], 10, -1894986606),
            p = this._ii(p, l, c, f, a[d + 10], 15, -1051523),
            f = this._ii(f, p, l, c, a[d + 1], 21, -2054922799),
            c = this._ii(c, f, p, l, a[d + 8], 6, 1873313359),
            l = this._ii(l, c, f, p, a[d + 15], 10, -30611744),
            p = this._ii(p, l, c, f, a[d + 6], 15, -1560198380),
            f = this._ii(f, p, l, c, a[d + 13], 21, 1309151649),
            c = this._ii(c, f, p, l, a[d + 4], 6, -145523070),
            l = this._ii(l, c, f, p, a[d + 11], 10, -1120210379),
            p = this._ii(p, l, c, f, a[d + 2], 15, 718787259),
            f = this._ii(f, p, l, c, a[d + 9], 21, -343485551),
            c = (c + g) >>> 0,
            f = (f + b) >>> 0,
            p = (p + w) >>> 0,
            l = (l + x) >>> 0;
        }
        return this.endian([c, f, p, l]);
    }

    stringToBytes(e) {
        for (var t = [], n = 0; n < e.length; n++)
            t.push(255 & e.charCodeAt(n));
        return t
    }

    bytesToWords(e) {
        for (var t = [], n = 0, r = 0; n < e.length; n++, r += 8)
            t[r >>> 5] |= e[n] << 24 - r % 32;
        return t;
    }

    wordsToBytes(e) {
        for (var t = [], n = 0; n < 32 * e.length; n += 8)
            t.push(e[n >>> 5] >>> 24 - n % 32 & 255);
        return t
    }

    bytesToHex(e) {
        for (var t = [], n = 0; n < e.length; n++)
            t.push((e[n] >>> 4).toString(16)),
            t.push((15 & e[n]).toString(16));
        return t.join("")
    }

    _ff(e, t, n, r, o, i, a) {
        var u = e + (t & n | ~t & r) + (o >>> 0) + a;
        return (u << i | u >>> 32 - i) + t;
    }

    _gg(e, t, n, r, o, i, a) {
        var u = e + (t & r | n & ~r) + (o >>> 0) + a;
        return (u << i | u >>> 32 - i) + t;
    }

    _hh(e, t, n, r, o, i, a) {
        var u = e + (t ^ n ^ r) + (o >>> 0) + a;
        return (u << i | u >>> 32 - i) + t;
    }

    _ii(e, t, n, r, o, i, a) {
        var u = e + (n ^ (t | ~r)) + (o >>> 0) + a;
        return (u << i | u >>> 32 - i) + t;
    }

    rotl(e, t) {
        return e << t | e >>> 32 - t;
    }

    endian(e) {
        if (e.constructor == Number)
            return 16711935 & this.rotl(e, 8) | 4278255360 & this.rotl(e, 24);
        for (var t = 0; t < e.length; t++)
            e[t] = this.endian(e[t]);
        return e;
    }
};

function cls_digist(urlParam) {
    let d = new ClsDigest();
    let b = new ClsBin2Hex();
    let dx = d.digest(urlParam);
    let rs = b.run(dx);
    console.log(rs);
    return rs;
}

cls_digist('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz012')
// 99a8a8a01ccc1b7508a0eac200155cda