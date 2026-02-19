class Rect {
    constructor(l, t, r, b) {
        this.left = l;
        this.top = t;
        this.right = r;
        this.bottom = b;
    }
    width() {return this.right - this.left;}
    height() {return this.bottom - this.top;}
    isPointIn(x, y) {
        return x >= this.left && x < this.right && y >= this.top && y < this.bottom;
    }
    move(dx, dy) {
        let w = this.width();
        let h = this.height();
        this.left += dx;
        this.top += dy;
        this.right = this.left + w;
        this.bottom = this.top + h;
    }
    moveTo(x, y) {
        let w = this.width();
        let h = this.height();
        if (typeof(x) == 'number') {
            this.left = x;
            this.right = x + w;
        }
        if (typeof(y) == 'number') {
            this.top = y;
            this.bottom = y + h;
        }
    }

    intersection(rect) {
        let l = Math.max(rect.left, this.left);
        let t = Math.max(rect.top, this.top);
        let r = Math.min(rect.right, this.right);
        let b = Math.min(rect.bottom, this.bottom);
        if (l >= r || t >= b) {
            return 0;
        }
        return (r - l) * (b - t);
    }
}

class AnchrosView {
    constructor(canvas) {
        this.width = canvas.width = canvas.clientWidth;
        this.height = canvas.height = canvas.clientHeight;
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");
        this.anchors = null;
        this.sh000001 = null;
        this.anchorsUI = null; // list of {rect: Rect, data: xx, }
        this.selAnchor = null;
        this.day = null;

        let thiz = this;
        canvas.addEventListener('click', function(e) {
            thiz.onClick(e.offsetX, e.offsetY);
        });
        canvas.addEventListener('dblclick', function(e) {
            thiz.onDbClick(e.offsetX, e.offsetY);
        });
        this.PADDING_X = 100;
        this.maxPrice = 0;
        this.minPrice = 0;
    }

    // day = YYYY-MM-DD
    loadData(day, callback) {
        let thiz = this;
        this.anchors = null;
        this.sh000001 = null;
        this.anchorsUI = null;
        this.selAnchor = null;

        function cbx(rs) {
            thiz.anchors = rs.anchors;
            thiz.sh000001 = rs.sh000001;
            if (callback)
                callback(thiz.anchors);
            thiz.draw();
        }
        self.day = day;
        this._loadData(day, cbx);
    }

    reloadData(callback) {
        if (! this.day) {
            return;
        }
        this.loadData(this.day, callback);
    }

    _loadData(day, cb) {
        let cbNum = 0;
        let rs = {};
        function mcb() {
            cbNum ++;
            if (cbNum == 2) {
                cb(rs);
            }
        }
        if (! day) day = '';
        axios.get(`/hot-anchors?day=${day}&days=10`).then((resp) => {
            rs.anchors = resp.data;
            mcb();
        });
        axios.get(`/get-fenshi/999999?day=${day}`).then((resp) => {
            rs.sh000001 = resp.data;
            if (! resp.data.line || !resp.data.line.length) {
                this._fillEmptyKLine(day, resp.data);
            }
            mcb();
        });
    }

    _fillEmptyKLine(day, data) {
        let kline = [];
        let hour = 9;
        let minites = 30;
        day = parseInt(day.replace(/[-]/g, ""));
        while (true) {
            let time = hour * 100 + minites;
            if (time > 1500) {
                break;
            }
            if ((time >= 930 && time <= 1130) || (time > 1300 && time <= 1500)) {
                let price = time <= 1130 ? 100 : 110;
                kline.push({day: day, time: time, price: price});
            }
            minites ++;
            if (minites >= 60) {
                minites %= 60;
                hour ++;
            }
        }
        data.line = kline;
        data.pre = 100;
    }

    calcMinMax() {
        //算最大值，最小值
        let maxPrice = 0;
        let minPrice = 0;
        for (let i = 0; i < this.sh000001.line.length; i++) {
            let item = this.sh000001.line[i]
            if (! item) {
                continue;
            }
            let price = item.price;
            if (i == 0) {
                maxPrice = minPrice = this.sh000001.pre; // 昨日收盘价
            }
            if (price > maxPrice) {
                maxPrice = price;
            }
            if (price < minPrice) {
                minPrice = price;
            }
        }
        this.maxPrice = maxPrice;
        this.minPrice = minPrice;
    }

    findAnchor(x, y) {
        if (! this.anchorsUI)
            return null;
        for (let i = 0; i < this.anchorsUI.length; i++) {
            let an = this.anchorsUI[i];
            if (an.isPointIn(x, y)) {
                return an;
            }
        }
        return null;
    }

    onClick(x, y) {
        let an = this.findAnchor(x, y);
        if (! an) return;
        if (this.selAnchor == an) {
            return;
        }
        this.selAnchor = an;
        this.drawSelAnchor();
    }

    onDbClick(x, y) {
        let an = this.findAnchor(x, y);
        if (! an) return;
        let code = an.data.code;
        if (code.length == 8 && (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh'))
            window.open('https://www.cls.cn/stock?code=' + code, '_blank');
        else
            window.open('plate.html?code=' + code + '&name=' + an.data.name, '_blank');
    }

    draw() {
        this.drawBackground();
        this.drawFenShi();
        this.drawAnchors();
    }

    drawSelAnchor() {
        if (! this.selAnchor)
            return;
        this.ctx.beginPath();
        let an = this.selAnchor.data;
        let rect = this.selAnchor;
        if (an.up) {
            this.ctx.fillStyle = '#FFD8D8';
            this.ctx.strokeStyle = 'red';
        } else {
            this.ctx.fillStyle = '#A0F1DC';
            this.ctx.strokeStyle = 'green';
        }
        this.ctx.font = 'bold 18px 宋体';
        this.ctx.fillRect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top);
        this.ctx.fillStyle = 'black';
        this.ctx.fillText(an.wName, rect.left + 5, rect.top + 20);
        this.ctx.stroke();
        this.ctx.closePath();
    }

    getAnchorRectAtIdx(idx, w, h, time) {
        let pointsCount = 241; // 画的点数
        let pointsDistance = (this.width - this.PADDING_X * 2) / (pointsCount - 1); // 点之间的距离
        let PADDING_Y = 20;
        let H = this.height - PADDING_Y;
        let midx = this.minuteToIdx(time);
        if (midx < 0) {
            let t = PADDING_Y + (time - 925) * 40;
            return new Rect(5, t, w + 5, t + h);
        } 
        if (!this.zMaxPrice || !this.zMinPrice || idx >= this.sh000001.line.length) {
            return null;
        }
        let x = this.PADDING_X + pointsDistance * midx;
        let item = this.sh000001.line[midx];
        let priceY = H - (item.price - this.zMinPrice) * H / (this.zMaxPrice - this.zMinPrice) + PADDING_Y;
        let y = priceY + 50;
        let rect = new Rect(x, y, x + w, y + h);
        rect.priceY = priceY;
        let rm = []; // trys
        // search down
        while (true) {
            if (rect.bottom > this.height) {
                break;
            }
            let m = this.getIntersection(rect);
            rm.push({m: m, y: rect.top});
            if (m == 0) {
                return rect;
            }
            rect.move(0, 10);
        }
        rect.moveTo(null, priceY - 80);
        while (true) {
            if (rect.top < 0) {
                break;
            }
            let m = this.getIntersection(rect);
            rm.push({m: m, y: rect.top});
            if (m == 0) {
                return rect;
            }
            rect.move(0, -10);
        }
        rm.sort(function(a, b) {return a.m - b.m;});
        rect.moveTo(null, rm[0].y);
        return rect;
    }

    getIntersection(rect) {
        let a = 0;
        for (let i = 0; i < this.anchorsUI.length; i++) {
            let an = this.anchorsUI[i];
            let v = an.intersection(rect);
            a += v;
        }
        return a;
    }

    drawAnchors() {
        this.anchorsUI = [];
        if (! this.anchors) {
            return;
        }
        let IH = 30;
        
        for (let i = 0; i < this.anchors.length; i++) {
            this.ctx.beginPath();
            let an = this.anchors[i];
            let hour = parseInt(an.ctime.substring(0, 2));
            let minute = parseInt(an.ctime.substring(3, 5));
            let time = hour * 100 + minute;
            if (an.up) {
                this.ctx.fillStyle = '#FFD8D8';
                this.ctx.strokeStyle = '#ff0000';
            } else {
                this.ctx.fillStyle = '#A0F1DC';
                this.ctx.strokeStyle = '#00ff00';
            }
            this.ctx.font = 'bold 18px 宋体';
            let tw = this.ctx.measureText(an.wName).width;
            let bw = tw + 10;
            let rc = this.getAnchorRectAtIdx(i, bw, IH, time);
            if (! rc) {
                console.log('Ignore draw', an);
                continue;
            }
            rc.left = parseInt(rc.left);
            rc.top = parseInt(rc.top);
            rc.right = parseInt(rc.right);
            rc.bottom = parseInt(rc.bottom);
            rc.data = an;
            this.anchorsUI.push(rc);
            this.ctx.fillRect(rc.left, rc.top, rc.width(), rc.height());
            if (rc.priceY) {
                this.ctx.moveTo(rc.left, rc.priceY);
                this.ctx.lineTo(rc.left, (rc.priceY <= rc.top ? rc.top : rc.bottom));
                this.ctx.stroke();
            }
            this.ctx.fillStyle = 'black';
            this.ctx.fillText(an.wName, rc.left + 5, rc.top + 20);
            this.ctx.closePath();
        }
    }

    minuteToIdx(ms) {
        if (ms <= 930) {
            return ms - 930
        }
        let hour = parseInt(ms / 100);
        let minute = ms % 100;
        let ds = 0;
        if (hour <= 11) {
            ds = 60 * (hour - 9) + minute - 30
            return ds
        }
        ds = 120
        ds += minute + (hour - 13) * 60
        return ds
    }

    drawFenShi() {
        if (! this.sh000001 || !this.sh000001.line || this.sh000001.line.length == 0) {
            return;
        }
        this.zMaxPrice = this.zMinPrice = 0;
        this.calcMinMax();
        if (this.maxPrice == this.minPrice) {
            return;
        }
        let pre = this.sh000001.pre;
        let zf1 = Math.abs(this.maxPrice - pre) / pre;
        let zf2 = Math.abs(this.minPrice - pre) / pre;
        let zf = zf1 > zf2 ? zf1 : zf2;
        let zMaxPrice = (1 + zf) * pre;
        let zMinPrice = (1 - zf) * pre;
        this.zMaxPrice = zMaxPrice;
        this.zMinPrice = zMinPrice;
        
        let pointsCount = 241; // 画的点数
        let pointsDistance = (this.width - this.PADDING_X * 2) / (pointsCount - 1); // 点之间的距离
        let PADDING_Y = 20;
        let H = this.height - PADDING_Y;
        
        this.ctx.fillStyle = 'rgb(255, 255, 255)';
        this.ctx.lineWidth = 1;
        this.ctx.strokeStyle = 'black';
        this.ctx.beginPath();
        this.ctx.setLineDash([]);
        for (let i = 0; i < this.sh000001.line.length; i++) {
            let item = this.sh000001.line[i];
            let x = i * pointsDistance + this.PADDING_X;
            let y = H - (item.price - zMinPrice) * H / (zMaxPrice - zMinPrice) + PADDING_Y;
            if (i == 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        this.ctx.stroke();
        this.ctx.closePath();
        // 画最高、最低价
        this.ctx.font = 'normal 12px Arial';
        zf *= 100;
        zf = zf.toFixed(2) + '%'
        this.ctx.beginPath();
        this.ctx.fillStyle = 'red';
        let ww = this.ctx.measureText(zf).width;
        this.ctx.fillText(zf, this.width - ww, 10);
        this.ctx.closePath();
        this.ctx.beginPath();
        this.ctx.fillStyle = 'green';
        zf = '-' + zf;
        let ww2 = this.ctx.measureText(zf).width;
        this.ctx.fillText(zf, this.width - ww2, this.height - 10);
        this.ctx.closePath();
    }

    drawBackground() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        // draw background lines
        this.ctx.beginPath();
        this.ctx.strokeStyle = '#ccc';
        //this.ctx.setLineDash([4, 2]);
        this.ctx.lineWidth = 1;
        for (let i = 0; i < 3; i++) {
            let y = parseInt(i * (this.height / 2));
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.width, y);
        }

        for (let i = 0; i < 5; i++) {
            let x = parseInt(i * ((this.width - this.PADDING_X * 2) / 4)) + this.PADDING_X;
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.height);
        }
        this.ctx.stroke();
        this.ctx.closePath();
        //this.ctx.setLineDash([]);
    }
};

export {
    AnchrosView
}