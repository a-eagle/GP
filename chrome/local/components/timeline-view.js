import {Thread, Task} from './thread.js'
import utils from './utils.js'

class TimeLineViewManager {
    constructor() {
        this.viewId = 1;
        this.views = {};
        this.thread = new Thread();
    }
    nextViewId() {
        return this.viewId++;
    }
    add(view) {
        this.views[view.key] = view;
    }
    remove(view) {
        delete this.views[view.key];
    }
    reload(key, day) {
        if (! this.views[key]) {
            return;
        }
        this.runTask(this.views[key], day);
    }

    runTask(view, day) {
        if (! view.checkReload(day)) {
            return;
        }
        let run = (task, resolve) => {
            let visible = utils.isClientVisible(view.$el);
            if (! visible) {
                // console.log('[runTask] Not load', view.key);
                resolve();
            } else {
                // console.log('[runTask] load', view.key);
                view.loadData(day, resolve);
            }
        };
        let task = new Task(view.key, 0, run);
        viewMgr.addUniqueTask(view.key, task);
    }
    addUniqueTask(key, task) {
        this.thread.addUniqueTask(key, task);
    }
};

const viewMgr = new TimeLineViewManager();
viewMgr.thread.start(1000);

let TimeLineView = {
    props:['code'],
    emits: ['load-data-end'],
    data() {
        return {
            width: 300, height: 60, key: viewMgr.nextViewId(),
            day: null,
            data: null,
            zf: null,
            zs: null,
            amount: null,
            zsResults: [], //涨速
            updateTime: null,
            maxPrice: null,
            minPrice: null,
            loaded: false,
        }
    },
    methods: {
        checkReload(day) {
            day = utils.formatDate(day);
            if (this.loaded || day == this.day || !utils.isFormatDate(day)) {
                return false;
            }
            return true;
        },
        loadData(day, finish) {
            day = utils.formatDate(day)
            if (! this.checkReload(day)) {
                if (finish) finish();
                    return;
            }
            this.loaded = true;
            this.day = day;
            axios.get(`/get-fenshi/${this.code}?day=${this.day}`)
                .then((resp) => {
                    let ds = resp.data;
                    if (resp.line) ds.date = resp.line[0].day;
                    else ds.date = null;
                    this.updateTime = Date.now();
                    this.setData(ds);
                    this.draw();
                    this.$emit('load-data-end', this);
                })
                .finally((resp) => {
                    if (finish) finish();
                });
        },
        setData(data) {
            // {code: xx, date:xx, pre: xx, line: [{time, price, amount, avgPrice, vol}, ...] }
            this.data = data;
            this.zf = null;
            this.amount = null;
            this.zsResults.length = 0;
            if (!data || !data['line'] || !data.line.length) {
                return;
            }
            let last = data.line[data.line.length - 1];
            this.zf = (last.price - this.data.pre) * 100 / this.data.pre;
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
            this.fx();
            this.calcAmount();
        },
        calcMinMax() {
            //算最大值，最小值
            let maxPrice = 0;
            let minPrice = 9999999;
            for (let i = 0; i < this.data.line.length; i++) {
                if (! this.data.line[i]) {
                    continue;
                }
                let price = this.data.line[i].price;
                if (price > maxPrice) {
                    maxPrice = price;
                }
                if (price < minPrice) {
                    minPrice = price;
                }
            }
            this.maxPrice = maxPrice;
            this.minPrice = minPrice;
        },
        fx() {
            const SPEED_PEROID = 10; // 时速周期 5 / 10 /15
            const MIN_ZHANG_SU = 5; // 最小涨速 %
            this.zsResults.length = 0;
            let data = this.data.line;
            for (let i = 0; i < data.length - 1; i++) {
                let m = data[i];
                let mm = this._calcMaxPrice(i, Math.min(data.length, i + SPEED_PEROID));
                let maxIdx = mm[0], maxPrice = mm[1];
                if (maxIdx < 0)
                    continue;
                let me = data[maxIdx];
                let pre = data[i].price;
                if (pre <= 0)
                    continue;
                let zf = (maxPrice - pre) / pre * 100;
                if (zf < MIN_ZHANG_SU)
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
            let maxZs = this.getMaxZs();
            if (maxZs) {
                this.zs = maxZs.zf;
            }
        },
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
        },
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
        },
        calcAmount() {
            let a = 0;
            for (let i = 0; i < this.data.line.length; i++) {
                if (! this.data.line[i]) {
                    continue;
                }
                if (typeof(this.data.line[i].amount) == 'number' )
                    a += this.data.line[i].amount;
            }
            this.amount = a;
        },
        getLineColor(tag) {
            if (tag == 'ZT' || tag == 'ZTZB')
                return 'rgb(0, 0, 240)';
            if (tag == 'DT' || tag == 'DTZB')
                //return 'rgb(255, 153, 53)';
                return '#FFA500';
            if (tag == 'Z')
                return 'rgb(255, 0, 0)';
            return 'rgb(0, 204, 0)';
        },
        draw() {
            if (! this.data || !this.data['line'] || this.data.line.length == 0) {
                return;
            }
            let ctx = this.$el.getContext("2d");
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
            ctx.clearRect(0, 0, this.width, this.height);
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
            this.drawZhangFu(ctx, true, this.maxPrice, this.width, 10);
            this.drawZhangFu(ctx, false, this.minPrice, this.width, this.height - 5);
            let close = this.data.line[this.data.line.length - 1].price;
            this.drawZhangFu(ctx, false, close, this.width, this.height / 2 + 3, '#000');
        },
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
        },
        drawZhangFu(ctx, up, price, x, y, color) {
            let zf = (price - this.data.pre) * 100 / this.data.pre;
            let tag = this.getZDTag();
            if (up && (tag == 'ZT' || tag == 'ZTZB')) {
                // pass
            } else if (!up && (tag == 'DT' || tag == 'DTZB')) {
                // pass
            } else {
                tag = zf >= 0 ? 'Z' : 'D';
            }
            ctx.fillStyle = color || this.getLineColor(tag);
            zf = '' + zf;
            let pt = zf.indexOf('.');
            if (pt > 0) {
                zf = zf.substring(0, pt + 2);
            }
            zf += '%';
            let ww = ctx.measureText(zf).width;
            ctx.fillText(zf, x - ww, y);
        },
        drawMouse(x) {
            if (x < 0 || x >= this.width) {
                return;
            }
            let ctx = this.$el.getContext("2d");
            ctx.beginPath();
            ctx.strokeStyle = 'black';
            ctx.setLineDash([4, 2]);
            ctx.lineWidth = 1;
            ctx.moveTo(x + 0.5, 0);
            ctx.lineTo(x + 0.5, this.height);
            ctx.stroke();
            ctx.closePath();
            ctx.setLineDash([]);
        },
    },
    mounted() {
        viewMgr.add(this);
    },
    unmounted() {
        viewMgr.remove(this);
    },
    render() {
        return Vue.h('canvas', {'key-id': this.key, class: 'timeline', style: `width:${this.width}px; height: ${this.height}px; background-color: #fafafa;`, width: this.width, height: this.height});
    }
};


export {
    TimeLineView, viewMgr as TimeLineViewManager
}