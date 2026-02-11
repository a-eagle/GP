import utils from './utils.js'

let App = {
    created() {
        console.log('[App.created]');
    },
    data() {
        return {
            tradeDays: null,
            lastTradeDay: null,
            curDay: null,
        };
    },
    provide() {
        return {
            curDay: Vue.computed(() => this.curDay)
        };
    },
    methods: {
        async getTradeDays() {
            const resp = await axios.get('/get-trade-days');
            let dd = resp.data;
            this.tradeDays = dd;
            this.lastTradeDay = dd[dd.length - 1];
        },
        onCurDayChanged(val) {
            this.curDay = val;
            console.log('[App.onCurDayChanged] curDay', val);
        },
    },
    beforeMount() {
        this.getTradeDays();
        console.log('[App.beforeMount]', this.$data);
    },
    mounted() {
        console.log('[App.mounted]');
    },
};

let GlobalView = {
    name: 'GlobalMgrView',
    data() {
        return {
            pageData: null,
            datas: null,
            curDay: null,
            curHoverDay: null,
        }
    },
    emits: ['cur-day-changed'],
    methods: {
        onCurDayChanged(newVal) {
            this.pageData = this.getPageDate(newVal);
            this.$emit('cur-day-changed', this.curDay);
        },
        getPageDate(curDay) {
            if (! this.datas || !curDay)
                return null;
            let fidx = this.datas.length - 1;
            for (let i = this.datas.length - 1; i >= 0; i--) {
                if (this.datas[i].day == utils.formatDate(curDay)) {
                    fidx = i;
                    break;
                }
            }
            const PAGE_SIZE = 22;
            let rightNum = Math.min(this.datas.length - fidx, parseInt(PAGE_SIZE / 2));
		    let leftNum = PAGE_SIZE - rightNum;
            return this.datas.slice(fidx - leftNum, fidx + rightNum);
        },
        initCurDay() {
            let lp = utils.formatDate(utils.getLocationParams('day'));
            let last = this.datas[this.datas.length - 1].day;
            this.curDay = lp || last;
        },
        onSelDay(item) {
            this.curDay = item.day;
        },
        onHoverIn(item) {
            this.curHoverDay = item.day;
        },
        onHoverOut(item) {
            this.curHoverDay = null;
        },
    },
    mounted() { // beforeMount
        console.log('[GlobalMgrView.mounted]');
        this.$watch('curDay', (newVal, oldVal) => {
            this.onCurDayChanged(newVal);
        });
        axios.get('/ls-amounts').then((resp => {
            this.datas = resp.data;
            this.initCurDay();
        }));
    },
    render() {
        let {h} = Vue;
        let trs = [];
        if (! this.pageData) {
            return h('table', null, trs);
        }
        let HD = ['', '热度', '成交额'];
        for (let i = 0; i < 3; i++) {
            let tds = [];
            tds.push(h('th', null, HD[i]));
            let month = '';
            for (let it of this.pageData) {
                let csn = (i == 1) ? (it.degree > 50 ? 'red' : 'green') : '';
                let attrs = {onclick: ()=> this.onSelDay(it), 
                             onmouseover: () => this.onHoverIn(it),
                             onmouseout: () => this.onHoverOut(it),
                             class: [{selcol: it.day == this.curHoverDay || it.day == this.curDay}, csn],
                    };
                if (i == 0) {
                    if (month != it.sday.substring(0, 2)) it.fday = it.sday;
                    else it.fday = it.sday.substring(3);
                    month = it.sday.substring(0, 2);
                    tds.push(h('th', {innerHTML: `${it.fday}<br/>${it.week}`}, null));
                } else if (i == 1) {
                    tds.push(h('td', attrs, it.degree));
                } else {
                    let w = (it.amount / 10000).toFixed(2);
                    tds.push(h('td', Object.assign({}, {title: `${w}万亿`, }, attrs), w));
                }
            }
            let tr = h('tr', null, tds);
            trs.push(tr);
        }
        return h('table', null, trs);
    },
    
};

let AmountCompareView = {
    inject: ['curDay'],
    data() {
        this.$watch('curDay', this.onCurDayChanged);
        return {
            data : null,
		    result : null,
            selTime: null,
            PAD_LEFT: 80,
            PAD_RIGHT: 200,
            PAD_TOP: 5, 
            PAD_BOTTOM: 30,
        };
    },
    methods: {
        onCurDayChanged(day) {
            console.log('[AmountCompareView.onCurDayChanged] day=', day);
            axios.get('/compare-amount/' + day).then((resp) => {
                this.data = resp.data;
                this.calc();
                this.draw();
            });
        },
        calc() {
            this.result = {data: [], time: this.data.time, curSum: 0, preSum: 0, preAllSum: this.data.presum};
            let maxRate = 0, minRate = 0;
            for (let i = 0; i < this.data.cur.length; i++) {
                let cur = this.data.cur[i];
                let pre = this.data.pre[i];
                if (i != 0) {
                    cur += this.result.data[i - 1].cur;
                    pre += this.result.data[i - 1].pre;
                }
                let rate = pre ? (cur - pre) / pre * 100 : 1;
                let obj = {cur, pre, rate};
                this.result.data.push(obj);
                if (i == 0) {
                    maxRate = minRate = rate;
                } else {
                    maxRate = rate > maxRate ? rate : maxRate;
                    minRate = rate < minRate ? rate : minRate;
                }
                this.result.curSum = cur;
                this.result.preSum = pre;
            }
            if (maxRate <= 0) {
                maxRate = 0;
            } else if (minRate >= 0) {
                minRate = 0;
            } else {
                let m1 = maxRate; // maxRate > 0
                let m2 = -minRate; // minRate < 0
                if (m1 >= m2) {
                    let mm = m1 / m2;
                    if (mm >= 3) minRate = - maxRate / 3;
                    else minRate = - maxRate;
                } else {
                    let mm = m2 / m1;
                    if (mm >= 3) maxRate = - minRate / 3;
                    else maxRate = - minRate;
                }
            }
            this.result.maxRate = maxRate;
            this.result.minRate = minRate;
        },
        getCurTime() {
            if (this.selTime == null)
                return '';
            let time = String(this.result.time[this.selTime]);
            if (time.length < 4) time = '0' + time;
            time = time.substring(0, 2) + ':' + time.substring(2);
            return '时间 ' + time;
        },
        getRealAmount() {
            if (this.selTime == null)
                return parseInt(this.result.curSum / 100000000);
            return parseInt(this.result.data[this.selTime].cur / 100000000);
        },
        getYestodayRate() {
            if (this.selTime == null)
                return this.result.curSum / this.result.preAllSum * 100;
            let amount = this.result.data[this.selTime].cur;
            return amount / this.result.preAllSum * 100;
        },
        getDiffSum() {
            let idx = this.selTime == null ? this.result.data.length - 1 : this.selTime;
            let curSumAmount = this.result.data[idx].cur;
            let preSumAmount = this.result.data[idx].pre;
            let diff = curSumAmount - preSumAmount;
            let rate = diff / preSumAmount * 100;
            return {diff, rate};
        },
        draw() {
            // console.log(this)
            let thiz = this;
            let canvas = this.$el;
            if (! canvas)
                return;
            let ctx = canvas.getContext("2d");
            let width = canvas.width;
            let height = canvas.height;
            ctx.clearRect(0, 0, width, height);
            if (! this.result || !this.result.data.length)
                return;
            const AW = width - this.PAD_LEFT - this.PAD_RIGHT;
            const AH = height - this.PAD_TOP - this.PAD_BOTTOM;
            const PX = AW / 240;
            const MM = this.result.maxRate - this.result.minRate;
            function getRateY(result, rate) {
                let r = rate - result.minRate;
                let rr = r / MM;
                return AH - rr * AH + thiz.PAD_TOP;
            }
    
            // draw line
            ctx.beginPath();
            ctx.strokeStyle = '#FC9938';
            ctx.font = 'normal 12px Arial';
            ctx.lineWidth = 2;
            for (let i = 0; i < this.result.data.length; i++) {
                let x = this.PAD_LEFT + i * PX;
                let y = getRateY(this.result, this.result.data[i].rate);
                if (i == 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.stroke();
            ctx.closePath();
    
            // fill line area
            ctx.beginPath();
            ctx.fillStyle = '#FFF2E5';
            // console.log(this.result);
            for (let i = 0; i < this.result.data.length; i++) {
                let x = this.PAD_LEFT + i * PX;
                let y = getRateY(this.result, this.result.data[i].rate);
                if (i == 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.lineTo(this.result.data.length * PX + this.PAD_LEFT, getRateY(this.result, this.result.minRate) - 1);
            ctx.lineTo(this.PAD_LEFT, getRateY(this.result, this.result.minRate) - 1);
            ctx.fill();
            ctx.closePath();
    
            // draw bg
            let rpx = (this.result.maxRate - this.result.minRate) / 4;
            for (let i = 0; i < 5; i++) {
                let v = this.result.maxRate - i * rpx;
                ctx.beginPath();
                ctx.font = 'normal 12px Arial';
                if (v == 0) ctx.fillStyle = '#555';
                else if (v > 0) ctx.fillStyle = '#f55';
                else ctx.fillStyle = '#5c5';
                let text = v != 0 ? v.toFixed(1) + '%' : String(v);
                let ww = ctx.measureText(text).width;
                let y = getRateY(this.result, v);
                ctx.fillText(text, this.PAD_LEFT - ww - 5, y + 5);
                ctx.moveTo(this.PAD_LEFT, y)
                ctx.lineTo(width - this.PAD_RIGHT, y);
                ctx.strokeStyle = '#ddd';
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 4]);
                ctx.stroke();
                ctx.closePath();
                ctx.setLineDash([]);
            }
    
            // zero line bule
            ctx.beginPath();
            ctx.strokeStyle = '#9F79EE';
            ctx.lineWidth = 2;
            ctx.moveTo(this.PAD_LEFT, getRateY(this.result, 0))
            ctx.lineTo(width - this.PAD_RIGHT, getRateY(this.result, 0));
            ctx.stroke();
            ctx.closePath();
            
            ctx.beginPath();
            // right tip text
            ctx.fillStyle = '#000';
            ctx.font = 'normal 16px Arial';
            ctx.fillText(this.getCurTime(), width - this.PAD_RIGHT + 10, this.PAD_TOP + 20);
    
            let text = '实际量能  ' +  this.getRealAmount() + '亿';
            ctx.fillText(text, width - this.PAD_RIGHT + 10, this.PAD_TOP + 50);
    
            let zb = this.getYestodayRate();
            text = '昨日占比  ' + zb.toFixed(0) + '%';
            ctx.fillStyle = '#000';
            ctx.fillText(text, width - this.PAD_RIGHT + 10, this.PAD_TOP + 80);
    
            let {diff, rate} = this.getDiffSum();
            let flag = diff >= 0 ? '增量 ' : '缩量 ';
            text = flag + parseInt(diff / 100000000) + '亿';
            let zr = rate.toFixed(1);
            text += '   ' + zr + '%';
            if (diff > 0) ctx.fillStyle = '#c00';
            else if (diff < 0) ctx.fillStyle = '#0c0';
            else ctx.fillStyle = '#000';
            ctx.fillText(text, width - this.PAD_RIGHT + 10, this.PAD_TOP + 110);
    
            let diffAll = parseInt(this.result.preAllSum * rate / 100 / 100000000);
            text = '预计' + flag + diffAll + '亿';
            if (diffAll > 0) ctx.fillStyle = '#c00';
            else if (diffAll < 0) ctx.fillStyle = '#0c0';
            else ctx.fillStyle = '#000';
            ctx.fillText(text, width - this.PAD_RIGHT + 10, this.PAD_TOP + 140);
    
            ctx.fillStyle = '#aaa';
            ctx.strokeStyle = '#aaa';
            ctx.font = 'normal 12px Arial';
            let time = ['09:30', '10:00', '10:30', '11:00', '11:30','13:30', '14:00', '14:30', '15:00'];
            for (let i = 0; i < time.length; i++) {
                let cx = this.PAD_LEFT + i * AW / (time.length - 1);
                let ww = ctx.measureText(time[i]).width;
                let tx = cx;
                if (i == 0)
                    tx = this.PAD_LEFT;
                else if (i == time.length - 1)
                    tx -= ww;
                else
                    tx -= ww / 2;
                ctx.moveTo(cx, height - this.PAD_BOTTOM - 3);
                ctx.lineTo(cx, height - this.PAD_BOTTOM);
                ctx.stroke();
                ctx.fillText(time[i], tx, height - this.PAD_BOTTOM + 15);
            }
            ctx.closePath();
    
            // draw sel time
            if (this.selTime != null) {
                ctx.beginPath();
                ctx.strokeStyle = '#7B68EE';
                ctx.lineWidth = 1;
                let cx = this.PAD_LEFT + this.selTime * PX;
                ctx.moveTo(cx, this.PAD_TOP);
                ctx.lineTo(cx, height - this.PAD_BOTTOM);
                ctx.stroke();
                ctx.closePath();
            }
        },
        onClick(evt) {
            let canvas = this.$el;
            let width = canvas.width;
            let x = evt.offsetX;
            let isOut = x < this.PAD_LEFT || x > width - this.PAD_RIGHT;
            if (this.selTime || isOut) {
                this.selTime = null;
                this.draw();
                return;
            }
            if (! this.result || !this.result.data.length) {
                this.selTime = null;
                this.draw();
                return;
            }
            this.selTime = null;
            const AW = width - this.PAD_LEFT - this.PAD_RIGHT;
            const PX = AW / 240;
            for (let i = 0; i < this.result.data.length; i++) {
                let bx = this.PAD_LEFT + i * PX - PX / 2;
                let ex = this.PAD_LEFT + i * PX + PX / 2;
                if (x >= bx && x <= ex) {
                    this.selTime = i;
                    break;
                }
            }
            this.draw();
        }
    },
    render() {
        return Vue.h('canvas', {width: 1200, height: 200, onclick: this.onClick });
    },
    mounted() {
        console.log('[AmountCompareView].mounted');
    }
};

let TimeDegreeView = {
    inject: ['curDay'],
    data() {
        this.$watch('curDay', this.onCurDayChanged);
        return {PCW: 920, PCH: 150, canvasWidth: 960, chart: null};
    },
    methods: {
        onCurDayChanged(day) {
            console.log('[TimeDegreeView.onCurDayChanged] day=', day);
            axios.get('/get-time-degree?day=' + day).then((resp) => {
                this.data = resp.data;
                this.calc();
            });
        },
        calc() {
            let xl = [];
            let xv = [];
            let v50 = [];
            let lastTime = null;
            for (let i = 0; this.data && i < this.data.length; i++) {
                if (this.data[i].time.charAt(4) == '0') {
                    let ctime = this.data[i].time;
                    let mtime = ctime;
                    if (lastTime && lastTime.substring(0, 2) == ctime.substring(0, 2)) {
                        mtime = ctime.substring(3);
                    }
                    lastTime = ctime;
                    xl.push(mtime);
                    xv.push(this.data[i].degree);
                    v50.push(50);
                }
            }
            function ss(set) {
                let rs = {
                    borderColor: ctx => {if (set[ctx.p1DataIndex] < 50) return '#8EC8B4'; return undefined; },
                    // borderDash: ctx => skipped(ctx, set, [3, 3])
                }
                return rs;
            }
            let cdata = {
                labels: xl,
                datasets: [
                    {label: 'Degree', data: xv, fill: false, borderColor: '#FF3333', segment: ss(xv), spanGaps: true},
                    //{label: '50', data: v50, fill: false, borderColor: '#505050'},
                ],
            };
            let canvas = this.$el;
            let cw = parseInt(this.PCW * (this.data.length - 1) / 24) + 40;
            this.canvasWidth = cw;
            canvas.width = cw;
            canvas.style.width = `${cw}px`;
            this.chart = new Chart(canvas, {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}});
            this.chart.resize(cw, this.PCH);
        }
    },
    render() {
        return Vue.h('canvas', {width: this.PCW, height: this.PCH});
    },
    mounted() {
        console.log('[TimeDegreeView].mounted');
    }
};

let ZdfbView = {
    inject: ['curDay'],
    data() {
        this.$watch('curDay', this.onCurDayChanged);
        return {data: null};
    },
    methods: {
        onCurDayChanged(day) {
            console.log('[ZdfbView.onCurDayChanged] day=', day);
            axios.get('/zdfb-detail/' + day).then((resp) => {
                console.log('ZdfbView.data', resp.data);
                this.data = resp.data;
            });
        },
    },
    template: `
        <div class="zdfb-item">
            <table class="zdfb">
                <tr class='red'> <th> 日期 </th> <th style=''>涨停 </th> </tr>
                <tr class='green'> <th> {{data.day}} </th> <th style='color:red;'> {{data.zt}} </th> </tr>
                <tr> <th style='width:165px; background-color:#fff;' rowspan=2>  </th> <th>跌停</th>  </tr>
                <tr> <th style='color:green;'> {{data.dt}} </th> </tr>
            </table>
            <div style='width: 700px; height:215px; float:left; margin-left:120px;' :bind='zdfb.czd' :render='zdfb.czdFunc'> </div>
        </div>
    `
};


function registerComponents(app) {
    app.component('global-view', GlobalView);
    app.component('amount-compare-view', AmountCompareView);
    app.component('time-degree-view', TimeDegreeView);
    app.component('zdfb-view', ZdfbView);
}

export default {
    App,
    registerComponents,
}