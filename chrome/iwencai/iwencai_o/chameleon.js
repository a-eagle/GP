var TOKEN_SERVER_TIME = new Date().getTime() / 1000;

class Base64 {
    constructor() {
        this.keys = {};
        this.M = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
        for (let i = 0; i < this.M.length; i++) {
            this.keys[this.M[i]] = i;
        }
    }

    base64Encode(e) {
        let f = [];
        let m = this.M;
        for (let i = 0; i < e.length; ) {
            let d = e[i++] << 16 | e[i++] << 8 | e[i++];
            f.push(m.charAt(d >> 18), m.charAt(d >> 12 & 0x3f), m.charAt(d >> 6 & 0x3f), m.charAt(d & 0x3f));
        }
        f = f.join('');
        return f;
    }

    base64Decode(str) {
        let d = [];
        for (let i = 0; i < str.length; ) {
            let h = this.keys[str.charAt(i++)] << 18 | this.keys[str.charAt(i++)] << 12 | this.keys[str.charAt(i++)] << 6 | this.keys[str.charAt(i++)];
            d.push(h >> 16, h >> 8 & 0xff, h & 0xff);
        }
        // console.log(d);
        return d;
    }

    // data is Array of length 43
    encode(data) {
        let e = 0;
        for (let i = 0; i < data.length; i++) {
            e = (e << 5) - e + data[i];
        }
        let r = e & 0xff;
        e = [3, r];
        for (let i = 0, j = 2; i < data.length; ) {
            e[j++] = data[i++] ^ r & 0xff;
            r = ~(r * 131);
        }
        // console.log(e);
        let f = this.base64Encode(e);
        return f;
    }

    decode(str) {
        let t = this.base64Decode(str);
        if (t[0] != 3) {
            // error
            return 0;
        }
        let u = t[1];
        let rs = [];
        for (let j = 2, i = 0; j < t.length; ) {
            rs[i++] = t[j++] ^ u & 0xff;
            u = ~(u * 131);
        }
        console.log(rs);
        // check rs is OK
        let e = 0;
        for (let i = 0; i < rs.length; i++) {
            e = (e << 5) - e + rs[i];
        }
        e = e & 0xff;
        if (e == t[1]) {
            return rs;
        }
        return 0;
    }
}

class UserParams {
    constructor() {
        this.mouseMove = 0;
        this.mouseClick = 0;
        this.mouseWhell = 0;
        this.keyDown = 0;
    }

    getMouseMove() {
        this.mouseMove += parseInt(Math.random() * 15);
        return this.mouseMove;
    }
    getMouseClick() {
        this.mouseClick += parseInt(Math.random() * 15);
        return this.mouseClick;
    }
    getMouseWhell() {
        this.mouseWhell += parseInt(Math.random() * 15);
        return this.mouseWhell;
    }
    getKeyDown() {
        this.keyDown += parseInt(Math.random() * 10);
        return this.keyDown;
    }
    getClickPosX() {
        return parseInt(Math.random() * 1024);
    }
    getClickPosY() {
        return parseInt(Math.random() * 720);
    }
    serverTimeNow() {
        let diff = this.timeNow() - TOKEN_SERVER_TIME;
        if (diff > 20 * 60) { // 20 minuts
            TOKEN_SERVER_TIME = this.timeNow();
        }
        return parseInt(TOKEN_SERVER_TIME);
    }
    timeNow() {
        return parseInt(Date.now() / 1000);
    }
    ramdom() {
        return parseInt(Math.random() * 4294967295);
    }
}

class Henxin {
    constructor() {
        this.data = [];
        this.base_fileds = [4, 4, 4, 4, 1, 1, 1, 3, 2, 2, 2, 2, 2, 2, 2, 4, 2, 1];
        for (let i = 0; i < this.base_fileds.length; i++) {
            this.data[i] = 0;
        }
        this.uiParams = new UserParams();
        this.base64 = new Base64();
    }

    init() {
        this.data[0] = this.uiParams.ramdom();
        this.data[1] = 1717735760; //this.uiParams.serverTimeNow();
        this.data[3] = 3539863620; // strhash(navigator.userAgent)
        this.data[4] = 1; // getPlatform
        this.data[5] = 10; // getBrowserIndex
        this.data[6] = 5; // getPluginNum
        this.data[13] = 3748; // getBrowserFeature

        this.data[15] = 0;
        this.data[16] = 0;
        this.data[17] = 3;
    }

    update() {
        this.data[1] = this.uiParams.serverTimeNow();
        this.data[2] = this.uiParams.timeNow();

        this.data[7] = this.uiParams.getMouseMove();
        this.data[8] = this.uiParams.getMouseClick();
        this.data[9] = this.uiParams.getMouseWhell();
        this.data[10] = this.uiParams.getKeyDown();
        this.data[11] = this.uiParams.getClickPosX();
        this.data[12] = this.uiParams.getClickPosY();

        this.data[15] = 0;
        this.data[16]++;

        let n = this.toBuffer();
        let rs = this.base64.encode(n);
        // console.log('encode:', rs);
        return rs;
    }

    decodeBuffer(buf) {
        let r = 0;
        for (let bf = this.base_fileds, j = 0, i = 0; i < bf.length; i++) {
            let v = bf[i];
            r = 0;
            do {
                r = (r << 8) + buf[j++];
            } while (--v > 0);
            this.data[i] = r >>> 0;
        }
        return r;
    }

    toBuffer() {
        let c = [];
        for (let s = -1, i = 0, u = this.base_fileds; i < this.base_fileds.length; i++) {
            for (let l = this.data[i], p = u[i], d = s += p; c[d] = l & 0xff, --p != 0; ) {
                --d;
                l >>= 8;
            }
        }
        return c;
    }
}


let hx = new Henxin();
hx.init();
hx.data[0] = 3411707073
hx.data[1] = 1717735760
hx.data[2] = 1720415622
hx.data[3] = 3539863620
hx.data[4] = 1
hx.data[5] = 10
hx.data[6] = 5
hx.data[7] = 904
hx.data[8] = 10
hx.data[9] = 3
hx.data[10] = 21
hx.data[11] = 1155
hx.data[12] = 545
hx.data[13] = 3748
hx.data[14] = 0
hx.data[15] = 0
hx.data[16] = 52
hx.data[17] = 3

let n = hx.toBuffer();
console.log(n.length);
console.log(n);
let rs = hx.base64.encode(n);

//let rs = hx.update();

console.log(rs);
/*
rs = 'http://d.10jqka.com.cn/v6/line/33_002261/01/today.js?hexin-v=' + rs
console.log(rs);

javascript: window.location.href = 'https://s.thsi.cn/js/chameleon/time.1' + (new Date().getTime() / 1200000) + '.js'


*/