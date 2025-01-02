class Listener {
    constructor() {
        this.listeners = {};
    }
    addListener(eventName, listener) {
        let lsts = this.listeners[eventName];
        if (! lsts) {
            lsts = this.listeners[eventName] = [];
        }
        lsts.push(listener);
    }

    // event = {name: '', ..}
    notify(event) {
        let name = event.name;
        let lsts = this.listeners[name];
        if (! lsts) {
            return;
        }
        for (let i in lsts) {
            lsts[i](event);
        }
    }
}

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
}

class KLineView extends Listener {
    constructor(width, height) {
        super();
        this.KLINE_SPACE = 3; // K线之间的间距
        this.KLINE_WIDTH = 4; // K线的宽度
        this.kMaxValue = 0;
        this.kMinValue = 0;
        this.mouseXY = null;

        this.visibleRange = null;
        this.selectPosIdxArr = [];
        this.line = [];
        this.code = null;
        let ZB_HEIGHT = 80;
        this.klineRect = new Rect(10, 20, width - 50, height - ZB_HEIGHT * 2);
        this.rateRect = new Rect(this.klineRect.left, this.klineRect.bottom + 10, this.klineRect.right, this.klineRect.bottom + ZB_HEIGHT);
        this.amountRect = new Rect(this.klineRect.left, this.rateRect.bottom + 10, this.klineRect.right, this.rateRect.bottom + ZB_HEIGHT);
        this.rateRender = new RateRender(this, this.rateRect.width(), this.rateRect.height());
        this.amountRender = new AmountRender(this, this.amountRect.width(), this.amountRect.height());
        
        let canvas = $('<canvas style="width: ' + width + 'px; height: ' + height + 'px; " />');
        this.canvas = canvas.get(0);
        this.canvas.width = this.width  = width;
        this.canvas.height =  this.height = height;
        this.ctx = this.canvas.getContext("2d");
        let thiz = this;
        this.canvas.addEventListener('mousemove', function(e) {
            thiz.mouseMove(e.offsetX, e.offsetY, true);
        });
        this.canvas.addEventListener('click', function(e) {
            thiz.click(e.offsetX, e.offsetY, true);
        });
        this.canvas.addEventListener('contextmenu', function(e) {
            thiz.rightClick(e.offsetX, e.offsetY, true);
            e.preventDefault();
        });
        this.canvas.addEventListener('mouseleave', function(e) {
            thiz.mouseLeave(true);
        });
    }

    // [ {date, open, close, low, high, vol, amount, rate, zf}, ... ]
    setData(data) {
        this.line = data;
    }

    calcMinMaxPrice(fromIdx, endIdx) {
        //算最大值，最小值
        let kMaxValue = 0;
        let kMinValue = 9999999;
        for (let i = fromIdx; i < endIdx; i++) {
            if (! this.line[i]) {
                continue;
            }
            var barVal = this.line[i].high;
            if (barVal > kMaxValue) {
                kMaxValue = barVal;
            }
            var barVal2 = this.line[i].low;
            if (barVal2 < kMinValue) {
                kMinValue = barVal2;
            }
        }
        this.kMaxValue = kMaxValue;
        this.kMinValue = kMinValue;
    }

    priceToKLinePoint(pos, price) {
        let x = pos * (this.KLINE_WIDTH + this.KLINE_SPACE) + this.KLINE_SPACE;
        let y = parseInt(this.klineRect.height() * ( 1 - (price - this.kMinValue) / (this.kMaxValue - this.kMinValue)));
        // y = Math.max(y, 0);
        return { 'x': x + this.klineRect.left, 'y': y + this.klineRect.top };
    }

    getCode() {
        return this.code;
    }

    isZhiSu() { // 是否是指数
        return this.getCode().substring(0, 2) == '88';
    }

    getZDTag(posIdx) {
        let cur = this.line[posIdx];
        if (posIdx < 0 || !this.line || posIdx >= this.line.length || !cur) {
            return 'E'; // empty k-line
        }
        if (posIdx > 0 && this.line[posIdx - 1].close) {
            let ZRDP = this.line[posIdx - 1].close;
            let is20P = this.getCode().substring(0, 3) == '688' || this.getCode().substring(0, 2) == '30';
            if (cur.date < 20200824) {
                is20P = false;
            }
            let ZT = is20P ? 20 : 10;
            let isZT = (parseInt(ZRDP  * (100 + ZT) + 0.5) <= parseInt(cur.close * 100 + 0.1));
            if (isZT) {
                return 'ZT';
            }
            let isZTZB = (parseInt(ZRDP  * (100 + ZT)+ 0.5) <= parseInt(cur.high * 100))  && (cur.high != cur.close);
            if (isZTZB) {
                return 'ZTZB';
            }
            let isDT = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(cur.close * 100))
            if (isDT) {
                return 'DT';
            }
            let isDTZB = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(cur.low * 100)) && (cur.low != cur.close);
            if (isDTZB) {
                return 'DTZB';
            }
            if (this.isZhiSu()) {
                let zf = (cur.close - ZRDP) / ZRDP * 100;
                let zf2 = Math.abs((Math.max(cur.high, ZRDP) - cur.low) / ZRDP * 100);
                if (zf >= 3.5 || zf2 >= 3.5) {
                    return 'DZDD'; // 指数大涨大跌
                }
            }
        }
        if (cur.open <= cur.close) {
            return 'Z';
        } else {
            return 'D';
        }
    }
    
    getKColor(tag) {
        if (tag == 'ZT' || tag == 'ZTZB')
            return "rgb(0, 0, 255)";
        if (tag == 'DT' || tag == 'DTZB')
            return "#FFC125";
        if (tag == 'DZDD')
            return "rgb(255, 0, 255)";
        if (tag == 'Z')
            return "rgb(253,50,50)";
        // tag is 'D'
        return "rgb(84,252,252)";
    }

    // big = true | false
    zoom(big) {
        if (big) {
            this.KLINE_WIDTH = Math.min(this.KLINE_WIDTH + 2, 10);
            //this.KLINE_SPACE = Math.min(this.KLINE_SPACE + 1, 4);
        } else {
            this.KLINE_WIDTH = Math.max(this.KLINE_WIDTH - 2, 2);
            //this.KLINE_SPACE = Math.max(this.KLINE_SPACE - 1, 1);
        }
    }

    getVisibleRange() {
        if (! this.line) {
            return null;
        }
        let num = parseInt(this.klineRect.width() / (this.KLINE_WIDTH + this.KLINE_SPACE));
        let fromIdx = Math.max(0, this.line.length - num);
        return [fromIdx, this.line.length];
    }

    draw() {
        this.ctx.clearRect(0, 0, this.width, this.height);
        if (! this.line || this.line.length == 0) {
            return;
        }
        let range = this.getVisibleRange();
        this.visibleRange = range;
        if (! range) {
            return;
        }
        this.drawKLine();
        this.rateRender.draw(this.rateRect.left, this.rateRect.top);
        this.amountRender.draw(this.amountRect.left, this.amountRect.top);
    }

    drawKLine() {
        let range = this.visibleRange;
        this.calcMinMaxPrice(range[0], range[1]);
        if (this.mouseXY) {
            let mousePos = this.getPosIdx(this.mouseXY[0]);
            this.drawMouse(mousePos);
        }
        for (let i = range[0], k = 0; i < range[1]; i++, k++) {
            let data = this.line[i];
            if (! data) {
                continue;
            }
            let tag = this.getZDTag(i);
            let color = this.getKColor(tag);
          
            //最高最低的线
            this.ctx.beginPath();
            this.ctx.strokeStyle = color;
            this.ctx.lineWidth = 1;
            let pt1 = this.priceToKLinePoint(k, data.low);
            let pt2 = this.priceToKLinePoint(k, data.high);
            this.ctx.moveTo(pt1.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt1.y);
            this.ctx.lineTo(pt2.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt2.y);
            this.ctx.stroke();
            this.ctx.closePath();
            
            //绘制方块
            this.ctx.beginPath();
            pt1 = this.priceToKLinePoint(k, data.open);
            pt2 = this.priceToKLinePoint(k, data.close);
            this.ctx.rect(pt1.x + 0.5, Math.min(pt1.y, pt2.y) + 0.5, this.KLINE_WIDTH, Math.abs(pt1.y - pt2.y));
            if (data.close >= data.open) {
                this.ctx.fillStyle = 'rgb(0, 0, 0)';
                this.ctx.lineWidth = 1;
                this.ctx.strokeStyle = color;
                this.ctx.fill();
                this.ctx.stroke();
            } else {
                this.ctx.fillStyle = color;
                this.ctx.lineWidth = 0;
                this.ctx.fill();
                this.ctx.stroke();
            }
            this.ctx.closePath();
        }

        // draw ma5 ma10
        this.ctx.beginPath();
        this.ctx.strokeStyle = '#ffff00';
        this.ctx.lineWidth = 1;
        for (let i = range[0], k = 0, st = false; i < range[1]; i++, k++) {
            let data = this.line[i];
            if (! data.ma5) continue;
            let pt1 = this.priceToKLinePoint(k, data.ma5);
            if (! st) {
                this.ctx.moveTo(pt1.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt1.y);
                st = true;
            } else {
                this.ctx.lineTo(pt1.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt1.y);
            }
        }
        this.ctx.stroke();
        this.ctx.closePath();

        this.ctx.beginPath();
        this.ctx.strokeStyle = '#EE00EE';
        this.ctx.lineWidth = 2;
        for (let i = range[0], k = 0, st = false; i < range[1]; i++, k++) {
            let data = this.line[i];
            if (! data.ma10) continue;
            let pt1 = this.priceToKLinePoint(k, data.ma10);
            if (! st) {
                this.ctx.moveTo(pt1.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt1.y);
                st = true;
            } else {
                this.ctx.lineTo(pt1.x + parseInt(this.KLINE_WIDTH / 2) + 0.5, pt1.y);
            }
        }
        this.ctx.stroke();
        this.ctx.closePath();

        // draw split line
        this.ctx.beginPath();
        this.ctx.strokeStyle = '#202020';
        this.ctx.fillStyle = '#202020';
        this.ctx.rect(0, this.klineRect.bottom + 3, this.width, 3);
        this.ctx.fill();
        this.ctx.closePath();
    }

    getPosIdx(x) {
        if (x < this.klineRect.left || x >= this.klineRect.right || !this.visibleRange) {
            return -1;
        }
        let nx = Math.max(x - this.klineRect.left - this.KLINE_SPACE, 0);
        let posIdx = parseInt(nx / (this.KLINE_WIDTH + this.KLINE_SPACE));
        if (posIdx + this.visibleRange[0] < this.visibleRange[1])
            return posIdx;
        return -1;
    }

    getPosIdxByDate(date) {
        for (let i = 0; i < this.line.length; i++) {
            if (this.line[i] && this.line[i].date == date) {
                return i;
            }
        }
        return -1;
    }

    drawMouse(posIdx) {
        if (posIdx < 0) {
            return;
        }
        let nx = posIdx * (this.KLINE_WIDTH + this.KLINE_SPACE) + this.KLINE_SPACE;
        nx += this.klineRect.left;
        this.ctx.beginPath();
        this.ctx.fillStyle = '#505050';
        this.ctx.strokeStyle = '#505050';
        this.ctx.lineWidth = 0;
        this.ctx.rect(nx, 0, this.KLINE_WIDTH, this.height);
        this.ctx.fill();
        this.ctx.stroke();
        this.ctx.closePath();
    }

    mouseMove(x, y, notify) {
        this.mouseXY = [x, y];
        this.draw();
        if (notify) {
            this.notify({name : 'MouseMove', x : x, y : y, source : this});
        }
    }

    click(x, y, notify) {
        return;
        let pos = this.getPosIdx(x);
        if (pos < 0) {
            return;
        }
        this.setSelectMouse(pos);
        this.draw();
        if (notify) {
            this.notify({name : 'Click', pos : pos, x : x, y : y, source : this});
        }
    }

    rightClick(x, y, notify) {
        return;
        let pos = this.getPosIdx(x);
        this.setHilightMouse(pos);
        this.draw();
        if (notify) {
            this.notify({name : 'RightClick', pos : pos, x : x, y : y, source : this});
        }
    }

    mouseLeave(notify) {
        /*
        this.draw();
        if (notify) {
            this.notify({name : 'MouseLeave', source : this});
        }
        */
    }

    limitLoadDataLength(len) {
        let arr = this.line;
        if (arr.length > len) {
            arr.splice(0, arr.length - len);
        }
        while (arr.length < len) {
            arr.unshift({});
        }
    }

    // zq = 'DAY' 'WEEK' 'MONTH'
    loadData(code, zq) {
        let thiz = this;
        code = code.trim();
        if (code.length == 8) {
            code = code.substring(2);
        }
        if (code.length != 6) {
            return;
        }
        this.code = code;
        new ClsUrl().loadKline(code, 800, zq, function(data) {
            let rs = [];
            //console.log(data);
            for (let i = 0; i < data.length; i++) {
                rs.push(thiz.toStdKLine(data[i]));
            }
            thiz.setData(rs);
            thiz.draw();
            thiz.notify({name : 'LoadDataEnd'});
        });
    }

    toStdKLine(item) {
        let obj = new Object();
        obj.date = item.date;
        obj.open = item.open_px;
        obj.close = item.close_px;
        obj.low = item.low_px;
        obj.high = item.high_px;
        obj.vol = parseInt(item.business_amount);
        obj.amount = parseInt(item.business_balance);
        obj.pre = item.preclose_px;
        obj.zf = item.change * 100; // 涨幅 %
        obj.rate = item.tr * 100; // %
        obj.ma5 = item.ma5 || 0;
        obj.ma10 = item.ma10 || 0;
        return obj;
    }
}

class TimeLineView extends Listener {
    
    constructor(width, height) {
        super();
        this.data = null;
        let thiz = this;
        let canvas = $('<canvas style="width: ' + width + 'px; height: ' + height + 'px; " />'); //border-right: solid 1px #ccc;
        canvas = canvas.get(0);
        canvas.addEventListener('mousemove', function(e) {
            thiz.mouseMove(e.offsetX, e.offsetY, true);
        });
        canvas.addEventListener('mouseleave', function(e) {
            thiz.mouseLeave(true);
        });
        this.canvas = canvas;
        canvas.width = this.width  = width;
        canvas.height =  this.height = height;
        this.ctx = canvas.getContext("2d");
        this.updateTime = 0; // load timeline data time mili-seconds
        this.code = null; // 股票代码

        this.SPEED_PEROID = 10; //  时速周期 5 / 10 /15
        this.MIN_ZHANG_SU = 5; // 最小涨速
        this.zsResults = []; //涨速
    }

    setData(data) {
        // {code: xx, date:xx, pre: xx, line: [{time, price, amount, avgPrice, vol}, ...] }
        this.data = data;
        if (!data || !data['line'] || !data.line.length) {
            return;
        }
        // calc low, high price
        let low = 0, high = 0;
        let ln = data.line;
        for (let i = 0; i < ln.length; i++) {
            let price = ln[i].price;
            if (low == 0 || high == 0) {
                low = high = price;
            } else {
                low = price < low ? price : low;
                high = price > high ? price : high;
            }
        }
        // append attr: low, high, close
        data.low = low;
        data.high = high;
        data.close = ln[ln.length - 1].price;
        this.code = data.code;
        this.fx();
    }

    fx() {
        let data = this.data.line;
        for (let i = 0; i < data.length - 1; i++) {
            let m = data[i];
            let mm = this._calcMaxPrice(i, Math.min(data.length, i + this.SPEED_PEROID));
            let maxIdx = mm[0], maxPrice = mm[1];
            if (maxIdx < 0)
                continue;
            let me = data[maxIdx];
            let pre = data[i].price;
            if (pre <= 0)
                continue;
            let zf = (maxPrice - pre) / pre * 100;
            if (zf < this.MIN_ZHANG_SU)
                continue;
            if (this.zsResults.length > 0) {
                let last = this.zsResults[this.zsResults.length - 1];
                if (last['zf'] <= zf)
                    this.zsResults.pop();  // remove last, replace it
                else
                    continue // skip
            }
            let curJg = {'fromMinute': m.time, 'endMinute': me.time, 'minuts': maxIdx - i + 1, 'fromIdx' : i, 'endIdx': maxIdx, 'zf': zf};
            this.zsResults.push(curJg);
        }
    }

    // 最大涨速 {fromMinute: , endMinute, minuts, fromIdx, endIdx, zf}
    getMaxZs() {
        let maxVal = null;
        for (let i = 0; i < this.zsResults.length; i++) {
            let it = this.zsResults[i];
            if (!maxVal) 
                maxVal = it;
            else if (maxVal.zf < it.zf)
                maxVal = it;
        }
        return maxVal;
    }

    _calcMaxPrice(fromIdx, endIdx) {
        let maxIdx = -1;
        let maxPrice = 0;
        for (let i = fromIdx; i < endIdx; i++) {
            let m = this.data.line[i];
            if (m.price > maxPrice) {
                maxPrice = m.price;
                maxIdx = i;
            }
        }
        return [maxIdx, maxPrice]
    }

    calcMinMax() {
        //算最大值，最小值
        let maxPrice = 0;
        let minPrice = 9999999;
        for (var i = 0; i < this.data.line.length; i++) {
            if (! this.data.line[i]) {
                continue;
            }
            var price = this.data.line[i].price;
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

    getLineColor(tag) {
        if (tag == 'ZT' || tag == 'ZTZB')
            return 'rgb(0, 0, 240)';
        if (tag == 'DT' || tag == 'DTZB')
            //return 'rgb(255, 153, 53)';
            return '#FFA500';
        if (tag == 'Z')
            return 'rgb(255, 0, 0)';
        return 'rgb(0, 204, 0)';
    }

    draw() {
        if (! this.data || !this.data['line'] || this.data.line.length == 0) {
            return;
        }
        let ctx = this.ctx;
        const POINT_NN = 1;// 每几分钟选一个点
        const PADDING_X = 30; // 右边留点空间
        
        this.calcMinMax();
        if (this.minPrice > this.data.pre)
            this.minPrice = this.data.pre;
        if (this.maxPrice < this.data.pre)
            this.maxPrice = this.data.pre;

        let pointsCount = parseInt(4 * 60 / POINT_NN); // 画的点数
        let pointsDistance = (this.width - PADDING_X) / (pointsCount - 1); // 点之间的距离
        
        ctx.fillStyle = 'rgb(255, 255, 255)';
        ctx.lineWidth = 1;
        this.ctx.clearRect(0, 0, this.width, this.height);
        let tag = this.getZDTag();
        ctx.strokeStyle = this.getLineColor(tag);
        ctx.beginPath();
        ctx.setLineDash([]);

        for (let i = 0; i < this.zsResults.length; i++) {
            let zs = this.zsResults[i];
            let x = zs.fromIdx * pointsDistance;
            let ex = zs.endIdx * pointsDistance;
            ctx.fillStyle = '#d0d0d0';
            ctx.fillRect(x, 0, ex - x, this.height);
        }
        
        ctx.fillStyle = 'rgb(255, 255, 255)';
        for (let i = 0, pts = 0; i < this.data.line.length; i++) {
            if (i % POINT_NN != 0) {
                continue;
            }
            let x = pts * pointsDistance;
            let y = this.height - (this.data.line[i].price - this.minPrice) * this.height / (this.maxPrice - this.minPrice);
            if (pts == 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
            ++pts;
        }
        ctx.stroke();
    
        // 画开盘价线
        ctx.strokeStyle = 'rgb(150, 150, 150)';
        ctx.beginPath();
        ctx.setLineDash([2, 4]);
        let y = this.height - (this.data.pre - this.minPrice) * this.height / (this.maxPrice - this.minPrice);
        ctx.moveTo(0, y);
        ctx.lineTo(this.width - PADDING_X, y);
        ctx.stroke();
        // 画最高、最低价
        this.drawZhangFu(true, this.maxPrice, this.width, 10);
        this.drawZhangFu(false, this.minPrice, this.width, this.height - 5);
    }

    getZDTag() {
        if (! this.data) {
            return 'E';
        }
        let ZRDP = this.data.pre;
        let cur = this.data;
        let price = cur.close;
        let code = this.data.code;
        if (code.substring(0, 2) == 'sh' || code.substring(0, 2) == 'sz') {
            code = code.substring(2);
        }
        let is20P = code.substring(0, 3) == '688' || code.substring(0, 2) == '30';
        let ZT = is20P ? 20 : 10;
        let isZT = (parseInt(ZRDP  * (100 + ZT) + 0.5) <= parseInt(price * 100 + 0.5));
        if (isZT) {
            return 'ZT';
        }
        let isZTZB = (parseInt(ZRDP  * (100 + ZT)+ 0.5) <= parseInt(cur.high * 100 + 0.5))  && (cur.high != price);
        if (isZTZB) {
            return 'ZTZB';
        }
        let isDT = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(price * 100 + 0.5));
        if (isDT) {
            return 'DT';
        }
        let isDTZB = (parseInt(ZRDP * (100 - ZT) + 0.5) >= parseInt(cur.low * 100 + 0.5)) && (cur.low != price);
        if (isDTZB) {
            return 'DTZB';
        }
        if (ZRDP <= price) {
            return 'Z';
        } else {
            return 'D';
        }
    }
    
    drawZhangFu(up, price, x, y) {
        let zf = (price - this.data.pre) * 100 / this.data.pre;
        let tag = this.getZDTag();
        if (up && (tag == 'ZT' || tag == 'ZTZB')) {
            // pass
        } else if (!up && (tag == 'DT' || tag == 'DTZB')) {
            // pass
        } else {
            tag = zf >= 0 ? 'Z' : 'D';
        }
        this.ctx.fillStyle = this.getLineColor(tag);
        zf = '' + zf;
        let pt = zf.indexOf('.');
        if (pt > 0) {
            zf = zf.substring(0, pt + 2);
        }
        zf += '%';
        let ww = this.ctx.measureText(zf).width;
        this.ctx.fillText(zf, x - ww, y);
    }

    drawMouse(x) {
        if (x < 0 || x >= this.width) {
            return;
        }
        this.ctx.beginPath();
        this.ctx.strokeStyle = 'black';
        this.ctx.setLineDash([4, 2]);
        this.ctx.lineWidth = 1;
        this.ctx.moveTo(x + 0.5, 0);
        this.ctx.lineTo(x + 0.5, this.height);
        this.ctx.stroke();
        this.ctx.closePath();
        this.ctx.setLineDash([]);
    }

    mouseMove(x, y, notify) {
        this.draw();
        this.drawMouse(x);
        if (notify) {
            this.notify({name : 'MouseMove', x : x, y : y, source : this});
        }
    }

    mouseLeave(notify) {
        /*
        this.draw();
        if (notify) {
            this.notify({name : 'MouseLeave', source : this});
        }
        */
    }

    // cb(code, TimeLineView)
    loadData(code, cb) {
        let thiz = this;
        this.code = code;
        this.loadData_(code, function(rs) {
            thiz.setData(rs);
            thiz.draw();
            thiz.notify({name: 'LoadDataEnd', src: thiz});
            if (cb) cb(code, this);
        });
    }

    reloadData() {
        this.loadData(this.code);
    }

    loadData_(code, callback) {
        this.code = code;
        let cu = new ClsUrl();
        let thiz = this;
        cu.loadHistory5FenShi(code, function(data5) {
            if (! data5 || !data5['date'] || !data5.date.length || !data5['line'] || !data5.line.length)
                return;
            let idx = (data5.date.length - 1) * 241;
            let pre = 0;
            if (idx > 0){
                pre = data5.line[idx - 1].last_px;
            } else {
                pre = data5.line[0].last_px;
            }
            let ds = {code: code, date: data5.line[idx].date, pre: pre, line: []};
            for (let i = idx; i < data5.line.length; i++) {
                let ct = data5.line[i];
                ds.line.push({time: ct.minute, price: ct.last_px, amount: ct.business_balance, avgPrice: ct.av_px});
            }
            thiz.updateTime = Date.now();
            callback(ds);
        });
    }
}

class AttrRender {
    constructor(klineView, width, height, attrName) {
        this.klineView = klineView;
        this.width  = width;
        this.height = height;
        this.maxGlobalVal = 0;
        this.attrName = attrName;
        this.tipLines = null; // [{val: xx, color: xxx}]
    }

    getMinMaxVal() {
        let min = 0, max = 0;
        if (! this.klineView.line || !this.klineView.visibleRange)
            return null;
        let range = this.klineView.visibleRange;
        for (let i = range[0]; i < range[1]; i++) {
            let cur = this.klineView.line[i];
            if (min == 0 || min > cur[this.attrName]) {
                min = cur[this.attrName];
            }
            if (max == 0 || max < cur[this.attrName]) {
                max = cur[this.attrName];
            }
        }
        return {maxVal : Math.max(max, this.maxGlobalVal), minVal : min};
    }

    draw(rx, ry) {
        let mm = this.getMinMaxVal();
        if (mm.maxVal <= 0) {
            return;
        }
        let ctx = this.klineView.ctx;
        let range = this.klineView.visibleRange;
        for (let i = range[0], k = 0; i < range[1]; i++, k++) {
            let data = this.klineView.line[i];
            if (! data) {
                continue;
            }
            //绘制方块
            ctx.beginPath();
            let y = (1 - data[this.attrName] / mm.maxVal) * this.height;
            let x = k * (this.klineView.KLINE_WIDTH + this.klineView.KLINE_SPACE) + this.klineView.KLINE_SPACE;
            ctx.rect(rx + x + 0.5, ry + y + 0.5, this.klineView.KLINE_WIDTH, this.height - y);
            if (data.close >= data.open) {
                ctx.fillStyle = 'rgb(253,50,50)';
                ctx.lineWidth = 1;
                ctx.strokeStyle = "rgb(253,50,50)";
                ctx.fill();
                ctx.stroke();
            } else {
                ctx.fillStyle = "rgb(84,252,252)";
                ctx.strokeStyle = "rgb(84,252,252)";
                ctx.lineWidth = 0;
                ctx.fill();
                ctx.stroke();
            }
            ctx.closePath();
        }
        this.drawTipLines(rx, ry);
        ctx.beginPath();
        ctx.font = '16px';
        ctx.strokeStyle = "#A0A0A0";
        ctx.fillText(this.getMaxTip(), rx + this.width, ry + 10);
        ctx.closePath();
    }

    drawTipLines(rx, ry) {
        if (! this.tipLines) {
            return;
        }
        let mm = this.getMinMaxVal();
        let ctx = this.klineView.ctx;
        for (let i = 0; i < this.tipLines.length; i++) {
            if (mm.maxVal >= this.tipLines[i].val) {
                ctx.beginPath();
                ctx.lineWidth = 1;
                ctx.strokeStyle = this.tipLines[i].color;
                let y = (1 - this.tipLines[i].val / mm.maxVal) * this.height;
                ctx.moveTo(rx,  ry + y);
                ctx.lineTo(rx + this.width, ry + y);
                ctx.stroke();
                ctx.closePath();
            }
        }
    }

    getMaxTip() {
        return '';
    }
}

class RateRender extends AttrRender {
    constructor(klineView, width, height) {
        super(klineView, width, height, 'rate');
        this.maxGlobalVal = 5;
        this.tipLines = [{val: 5, color:'#2222ff'}, {val: 10, color:'#ee00ee'}, {val: 20, color: '#ffff00'}];
    }

    getMaxTip() {
        let mm = this.getMinMaxVal();
        return '' + parseInt(mm.maxVal) + '%';
    }
}

class AmountRender extends AttrRender {
    constructor(klineView, width, height) {
        super(klineView, width, height, 'amount');
        this.maxGlobalVal = 500000000;
        let R = 100000000; //亿
        this.tipLines = [{val: 5 * R, color:'#2222ff'}, {val: 10 * R, color:'#ee00ee'}, {val: 20 * R, color: '#ffff00'}];
    }

    getMaxTip() {
        let mm = this.getMinMaxVal();
        return '' + parseInt(mm.maxVal / 100000000) + '亿';
    }
}

class KLineUIManager extends Listener {
    constructor() {
        super();
        this.klineUIArr = [];
        this.loadDataEndNum = 0;
    }

    add(klineUI) {
        let thiz = this;
        this.klineUIArr.push(klineUI);
        klineUI.addListener('LoadDataEnd', function() {
            thiz.loadDataEndNum++;
            if (thiz.loadDataEndNum == thiz.klineUIArr.length) {
                thiz.onAllLoadDataEnd();
            }
        });
        klineUI.addListener('MouseMove', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('Click', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('RightClick', function(event) {thiz.onUserEvent(event);});
        klineUI.addListener('MouseLeave', function(event) {thiz.onUserEvent(event);});
    }

    onUserEvent(event) {
        let newEvent = $.extend({}, event);
        newEvent.name = 'Virtual' + event.name;
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            if (event.source != cur) {
                if (event.name == 'MouseMove') cur.mouseMove(event.x, event.y, false);
                else if (event.name == 'Click') cur.click(event.x, event.y, false);
                else if (event.name == 'RightClick') cur.rightClick(event.x, event.y, false);
                else if (event.name == 'MouseLeave') cur.mouseLeave(false);
            }
            cur.notify(newEvent);
        }
    }

    onAllLoadDataEnd() {
        let maxLen = 0;
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            if (maxLen < cur.dataArr.length) {
                maxLen = cur.dataArr.length;
            }
        }
        for (let i in this.klineUIArr) {
            let cur = this.klineUIArr[i];
            cur.limitLoadDataLength(maxLen);
        }
        this.notify({name: 'LoadAllDataEnd'})
    }
}

class TimeLineUIManager extends Listener {
    constructor() {
        super();
        this.views = [];
    }

    // view = TimeLineView
    add(view) {
        let thiz = this;
        this.views.push(view);
        view.addListener('MouseMove', function(event) {thiz.onUserEvent(event);});
        //view.addListener('Click', function(event) {thiz.onUserEvent(event);});
        view.addListener('MouseLeave', function(event) {thiz.onUserEvent(event);});
    }

    onUserEvent(event) {
        let newEvent = $.extend({}, event);
        newEvent.name = 'Virtual' + event.name;
        for (let i in this.views) {
            let cur = this.views[i];
            if (event.source != cur) {
                if (event.name == 'MouseMove') cur.mouseMove(event.x, event.y, false);
                // else if (event.name == 'Click') cur.click(event.x, event.y, false);
                else if (event.name == 'MouseLeave') cur.mouseLeave(false);
            }
            cur.notify(newEvent);
        }
    }

}

class VolUIManager extends Listener {
    constructor() {
        super();
        this.volUIArr = [];
    }

    add(volView) {
        this.volUIArr.push(volView);
    }

    onLoadAllDataEnd() {
        let max = 0;
        for (let i = 0; i < this.volUIArr.length; i++) {
            let cur = this.volUIArr[i];
            let code = cur.klineView.baseInfo.code;
            let bc = code.substring(0, 2);
            if (bc == '1A' || bc == '88') {
                // 指数
                continue;
            }
            let mm = cur.getMinMaxVal();
            if (max == 0 || max < mm.maxVal) {
                max = mm.maxVal;
            }
        }
        for (let i = 0; i < this.volUIArr.length; i++) {
            let cur = this.volUIArr[i];
            cur.setGlobalMaxVal(max);
            cur.draw();
        }
    }
}