import utils from './components/utils.js'
import {PopupView, PopupWindow} from './components/popup.js'
import {AnchrosView} from './components/anchors-view.js'
import {ZdfbView} from './components/zdfb-view.js'
import {DefaultRender} from './components/table.js'

let App = {
    created() {
        // console.log('[App.created]');
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
            // console.log('[App.onCurDayChanged] curDay', val);
        },
        refresh() {
            this.$notifyListener('cur-day-changed', this.curDay);
        }
    },
    beforeMount() {
        this.getTradeDays();
        // console.log('[App.beforeMount]', this.$data);
    },
    mounted() {
        // console.log('[App.mounted]');
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
            this.$notifyListener('cur-day-changed', this.curDay);
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
        // console.log('[GlobalMgrView.mounted]');
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
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
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
            // console.log('[AmountCompareView.onCurDayChanged] day=', day);
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
        // console.log('[AmountCompareView].mounted');
    }
};

let TimeDegreeView = {
    inject: ['curDay'],
    data() {
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
        return {PCW: 920, PCH: 150, canvasWidth: 960, chartData: null, redo: 1};
    },
    methods: {
        onCurDayChanged(day) {
            // console.log('[TimeDegreeView.onCurDayChanged] day=', day);
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
            
            let cw = parseInt(this.PCW * (this.data.length - 1) / 24) + 40;
            this.canvasWidth = cw;
            this.chartData = {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}};
            this.redo += 1;
        },
        wrapChart() {}, // 保存Chart的实例，因为不能放在data里
    },
    render() {
        if (this.wrapChart.instance) {
            this.wrapChart.instance.destroy(); // 必须，是因为如果Chart已经绑定了canvas，则canvas不能修改大小
        }
        this.$nextTick(() => {
            if (this.wrapChart.instance) {
                this.wrapChart.instance.destroy();
            }
            let canvas = this.$el;
            this.wrapChart.instance = new Chart(canvas, this.chartData);
            this.wrapChart.instance.resize(this.canvasWidth, this.PCH);
        });
        return Vue.h('canvas',
            {width: this.canvasWidth, height: this.PCH, style: {width: `${this.canvasWidth}px`, redo: this.redo }}
        );
    },
    mounted() {
        // console.log('[TimeDegreeView].mounted');
    }
};

let _ZdfbView = {
    inject: ['curDay'],
    data() {
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
        return {
            day: '', degree: '', zdfb: {}, d: 0, degreeTxt: '--',
            degreeStyle: {'text-align': 'center', 'line-height': 1, 'font-size': '30px', 'margin-top': '-35px', color: '#52c2a3'}, // color:${color};
        };
    },
    methods: {
        onCurDayChanged(day) {
            // console.log('[ZdfbView.onCurDayChanged] day=', day);
            axios.get('/zdfb-detail/' + day).then((resp) => {
                // console.log('ZdfbView.data', resp.data);
                for (let k in resp.data) {
                    this[k] = resp.data[k];
                }
                let d = 0;
                if (this.degree) {
                    d = this.degree / 100.0 * 226;
                    this.degreeTxt = String(this.degree) + '°';
                }
                this.d = `${d} 227`;
                if (this.degree && this.degree >= 50)
                    this.degreeStyle.color = 'red';
                this.$nextTick(() => {
                    let canvas = this.$refs.zdfbCanvas;
                    let view = new ZdfbView(canvas);
		            view.draw(this.zdfb);
                });
            });
        },
    },
    template:  `<table class="zdfb"><tbody>
        <tr style="height: 40px;"> <th> 日期 </th> <th style='width: 100px;'>涨停 </th> 
            <td rowspan=4> 
                <div>  <canvas ref="zdfbCanvas" width=700 height=215 style="width: 700px; height:215px;"> </canvas> </div>
            </td> 
        </tr>
        <tr style="height: 40px;"> <th> {{day}} </th> <th style='color:red;'> {{zdfb.zt}} </th> </tr>
        <tr  style="height: 60px;">
            <th style='width:165px; background-color:#fff;' rowspan=2> 
                <div style="width:160px; height: 80px;">
                <svg style="width:100% ;height: 100%;">
                    <defs>
                        <linearGradient id="linear" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" stop-color="#80DCC2"></stop>
                            <stop offset="100%" stop-color="#FF2C49"></stop>
                        </linearGradient>
                    </defs>
                    <circle cx="77.5" cy="76" r="72" stroke="#E2E2E2" stroke-width="8" fill="none" stroke-dasharray="226" stroke-dashoffset="-226" stroke-linecap="round"></circle>
                    <circle cx="77.5" cy="76" r="72" stroke="url(#linear)" stroke-width="8" fill="none" :stroke-dasharray="d" stroke-dashoffset="-226" stroke-linecap="round"></circle>
                </svg>
                <div :style="degreeStyle"> {{degreeTxt}} </div>
            </div>
            </th> <th>跌停</th>
        </tr>
        <tr style="height: 60px;"> <th style='color:green;'> {{zdfb.dt}} </th> </tr>
        </tbody></table>
        `,
};

let HotAnchrosView = {
    inject: ['curDay'],
    data() {
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
        return {
            redo: 1,
        };
    },
    methods: {
        onCurDayChanged(day) {
            this.redo += 1;
            this.$nextTick(() => {
                let view = this.$el._view;
                if (! view) {
                    view = this.$el._view = new AnchrosView(this.$el);
                }
                view.loadData(day);
                view.draw();
            });
        },
    },
    render() {
        return Vue.h('canvas',
            {style:'width:100%;height:100%; background-color:#fff;', redo: this.redo }
        );
    },
};

let HotAnchrosGroupView = {
    inject: ['curDay'],
    data() {
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
        return {
            datas: null,
        };
    },
    methods: {
        onCurDayChanged(day) {
            axios.get(`/hot-anchors-group`).then((resp) => {
                let COL_NUM = 7;
                let rs = [];
                for (let i = 0; i < resp.data.length; i += COL_NUM) {
                    let row = resp.data.slice(i, i + COL_NUM);
                    row.vkey = i;
                    rs.push(row);
                }
                this.datas = rs;
            });
        },
        getAnchorUrl(item) {
            return `plate.html?code=${item.code}&name=${item.name}`;
        },
        openChart(code, evt) {
            let pp = evt.target.parentElement;
            let tdRc = pp.getBoundingClientRect();
            let dw = document.documentElement.clientWidth;
            const C_WIDTH = 800;
            let attrs = {left: tdRc.left, top : tdRc.bottom, code: code, day: this.curDay};
            if (dw < tdRc.left + C_WIDTH) {
                attrs.left = dw - C_WIDTH - 30
            }
            attrs.canvasAttrs = {
                width: C_WIDTH - 4,
                height: 280 - 32,
                style: `width: ${C_WIDTH - 4}px; height: ${280 - 32}px;`,
            }
            let vnodes = Vue.h(HotAnchrosChartView, attrs);
            PopupWindow.open(vnodes);
        }
    },
    template: `
        <table class="anchor-list" style="border-collapse: separate;border-spacing: 15px 10px;">
            <tr v-for="row in datas" :key="row.vkey">
                <td v-for="item in row" :class="String(item.up)" :key="item.code" >
                    <a :href="getAnchorUrl(item)" target=_blank> {{item.name}} &nbsp;&nbsp;  {{item.num}}&nbsp;&nbsp;</a>
                    <span class="anchor-arrow" :code="item.code" @click="openChart(item.code, $event)">  </span>
                </td>
            </tr>
        </table>
    `,
};

let HotAnchrosChartView = {
    props:{
        left: {type: Number, default: () => 0},
        top: {type: Number, default: () => 0},
        code: {requared: true},
        day: {requared: true},
        canvasAttrs: {requared: true}
    },
    data() {
        return {
            chartOrgData: null, cdata: null,
        }
    },
    mounted() {
        this.loadData(this.code, this.day);
    },
    methods: {
        charWrap() {},
        loadData(code, day) {
            function skipped(ctx, set, val) {
                if (set[ctx.p0DataIndex] == set[ctx.p1DataIndex]) {
                    return val;
                }
                return undefined;
            }
            function ss(set) {
                let rs = {
                    borderColor: ctx => skipped(ctx,  set, 'rgb(0,0,0,0.2)'),
                    borderDash: ctx => skipped(ctx, set, [3, 3])
                }
                return rs;
            }
            axios.get(`/get-hot-tc-by-code?code=${code}&curDay=${day}&days=20`).then((resp) => {
                let data = resp.data;
                this.chartOrgData = data;
                let upset = data.up;
                let downset = data.down;
                let cdata = {
                    labels: data.sdays,
                    datasets: [
                        {label: 'UP', data: upset, fill: false, borderColor: '#FF3333', segment: ss(upset), spanGaps: true},
                        {label: 'DOWN', data: downset, fill: false, borderColor: '#33ff33', segment: ss(downset), spanGaps: true},
                    ],
                };
                function pbc() {
                    let rs = [];
                    rs.push('#0000ff');
                    for (let i = 0; i < 4; i++)
                        rs.push(Chart.defaults.borderColor);
                    return rs;
                }
                this.cdata = {type: 'line', data: cdata, options: {
                    plugins: {legend: {display: false, title: {display: false}}},
                    scales: {x: {grid : {color : pbc()}}}}};
            }).then(() => {
                this.charWrap.chart = new Chart(this.$refs.chart, this.cdata);
            });
        },
    },
    template: `
        <div class="anchors-wrap" :style="{left: left, top: top}">
            <div class="header"> <button class="left"> &lt;&lt; </button>  <button class="right"> &gt;&gt; </button> </div>
            <canvas ref="chart" v-bind="canvasAttrs" > </canvas>
        </div>
    `,

};

let TabNaviView = {
    inject: ['curDay'],
    data() {
        return {
            items: [{name: 'zt-table-view', title: '涨停池'}, {name: 'lb-table-view', title: '连板池'},
                        {name: 'zb-table-view', title: '炸板池'}, {name: 'dt-table-view', title: '跌停池'},
                        {name: 'hots-table-view', title: '热度榜'}, {name: 'amount-table-view', title: '成交额'}, 
                        {name: 'lhb-table-view', title: '龙虎榜'}, ],
            curTabCntView: 'zt-table-view',
        }
    },
    methods: {
        changeTab(item) {
            this.curTabCntView = item.name;
        }
    },
    template: `
        <div class="toggle-nav-box">
            <div v-for="item in items" :key="item.title" @click="changeTab(item)" :class="{'toggle-nav-active': item.name == curTabCntView}" > 
                {{item.title}}
            </div>
        </div>
        <keep-alive>  <component :is="curTabCntView">  </component> </keep-alive>
    `,
};

let BaseTableView = {
    inject: ['curDay'],
    data() {
        // this.$watch('curDay', this.onCurDayChanged);
        this.$addListener('cur-day-changed', (day) => this.onCurDayChanged(day));
        return {pageSize: 0};
    },
    mounted() {
        this.onCurDayChanged();
    },
    methods: {
        doSearch(text) {
            this.$refs.stable.filter(text);
        },
        onLoadDataDone(datas) {
        },
        onClickCell(rowData, column, event, tableView) {
        }
    },
    template: `
        <div style="text-align:center; width:100%; display: flex; justify-content: center;  ">
            <input style="border:solid 1px #999; height:25px;" @keydown.enter="doSearch($event.target.value)" />
        </div>
        <stock-table ref="stable" :columns="columns" 
            :url="url" :day="curDay" style="width:100%;"
            @load-data-done="onLoadDataDone" @click-cell="onClickCell" >
        </stock-table>
    `,
};

let ZT_TableView = {
    name: 'ZT_TableView',
    extends: BaseTableView,
    data() {
        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true}, // 
                {title: '连板', key: 'limit_up_days', width: 50, sortable: true},
                {title: '涨速', key: 'zs', width: 50, sortable: true, },
                {title: '热度', key: 'hots', width: 50, sortable: true,},
                {title: '动因', key: 'up_reason', width: 250, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true, },
                {title: '分时图', key: 'fs', width: 300},],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/query-cls-updown/ZT/${this.curDay}?_t=${new Date().getTime()}`;
        },
    }
};

let LB_TableView = {
    name: 'LB_TableView',
    extends: BaseTableView,
    data() {
        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true}, // 
                {title: '连板', key: 'limit_up_days', width: 50, sortable: true},
                {title: '涨速', key: 'zs', width: 50, sortable: true, },
                {title: '热度', key: 'hots', width: 50, sortable: true,},
                {title: '动因', key: 'up_reason', width: 250, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true, },
                {title: '分时图', key: 'fs', width: 300},],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/query-cls-updown/LB/${this.curDay}?_t=${new Date().getTime()}`;
        },
    }
};

let ZB_TableView = {
    name: 'ZB_TableView',
    extends: BaseTableView,
    data() {
        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '行业', key: 'ths_hy', width: 100, sortable: true},
				{title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true},
				{title: 'CLS-ZT', key: 'cls_ztReason', width: 100, sortable: true},
				{title: '热度', key: 'hots', width: 50, sortable: true},
				{title: '涨跌幅', key: 'change', width: 70, sortable: true},
				{title: '涨速', key: 'zs', width: 50, sortable: true},
				{title: '分时图', key: 'fs', width: 300},],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/query-cls-updown/ZB/${this.curDay}?_t=${new Date().getTime()}`;
        },
    }
};

let DT_TableView = {
    name: 'DT_TableView',
    extends: BaseTableView,
    data() {
        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '行业', key: 'ths_hy', width: 100, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true},
                {title: 'CLS-ZT', key: 'cls_ztReason', width: 100, sortable: true},
                {title: 'THS-DT', key: 'ths_dt_reason', width: 100, sortable: true},
                {title: '热度', key: 'hots', width: 50, sortable: true},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true},
                {title: '涨速', key: 'zs', width: 50, sortable: true},
                {title: '分时图', key: 'fs', width: 300},],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/query-cls-updown/DT/${this.curDay}?_t=${new Date().getTime()}`;
        },
        onLoadDataDone(datas) {
            let day = this.curDay.replaceAll('-', '');
            // ths_dtReason
            axios.get(`/iwencai?q=${day} 跌停,非st,成交额,收盘价,涨跌幅`).then((resp) => {
                // console.log('[iwencai]', resp);
                if (! resp.data) return;
                let ds = {};
                for (let r of resp.data) {
                    let reason = '';
                    for (let m in r) if (m.indexOf('跌停原因类型[') >= 0) { reason = r[m]; break; }
                    // let scode = r.code.charAt(0) == '6' ? 'sh' : 'sz';
                    // if (fd) fd.up_reason = reason;
                    ds[r.code] = reason;
                }
                for (let it of datas) {
                    let reason = ds[it.code];
                    it.ths_dt_reason = reason;
                }
            })
        },
    }
};

let Hots_TableView = {
    extends: BaseTableView,
    data() {
        return {
            pageSize: 100,
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '行业', key: 'ths_hy', width: 100, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true},
                {title: 'CLS-ZT', key: 'cls_ztReason', width: 100, sortable: true},
                {title: '热度', key: 'hots', width: 50, sortable: true},
                {title: '成交额', key: 'dynamicAmount', width: 50, sortable: true},
                {title: '涨跌幅', key: 'dynamicZf', width: 70, sortable: true},
                {title: '涨速', key: 'zs', width: 50, sortable: true},
                {title: '分时图', key: 'fs', width: 300}],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/top-hots/${this.curDay}?_t=${new Date().getTime()}`;
        },
    }
};

let Amount_TableView = {
    extends: BaseTableView,
    data() {
        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '行业', key: 'ths_hy', width: 100, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true},
                {title: 'CLS-ZT', key: 'cls_ztReason', width: 100, sortable: true},
                {title: '成交额', key: 'amount', width: 50, sortable: true},
                {title: '成交额<br/>排名', key: 'pm', width: 50, sortable: true},
                {title: '热度', key: 'hots', width: 50, sortable: true},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true},
                {title: '涨速', key: 'zs', width: 50, sortable: true},
                {title: '分时图', key: 'fs', width: 300}],
            datas: null,
            url: null,
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/top-amounts/${this.curDay}?_t=${new Date().getTime()}`;
        },
    }
};

const LHB_DetailView = {
    props: ['rowData'],
    created() {
        console.log('[LHB_DetailView.created]')
    },
    data() {
        console.log('LHB_DetailView.data()');
        return {
        }
    },
    computed: {
        buys() {
            let dd = [];
            if (this.rowData?.detail) {
                let detail = JSON.parse(this.rowData?.detail);
                detail.sort((a, b) => b.mrje - a.mrje);
                for (let i = 0; i < 5; i++) dd.push(detail[i]);
            }
            return dd;
        },
        sells() {
            let dd = [];
            if (this.rowData?.detail) {
                let detail = JSON.parse(this.rowData?.detail);
                detail.sort((a, b) => b.mcje - a.mcje);
                for (let i = 0; i < 5; i++) dd.push(detail[i]);
            }
            return dd;
        },
    },
    methods: {
        getYzName(it) {
			if (it.yz)
				return ' (' + it['yz'] + ')'
			let yyb = it.yyb || '';
			if (yyb.indexOf('分公司') >= 0)
				yyb = yyb.substring(0, yyb.indexOf('公司') + 2);
			if (yyb.indexOf('公司') >= 0) {
				let i = yyb.indexOf('公司');
				if (i != yyb.length - 2)
					yyb = yyb.substring(i + 2);
			}
			yyb = yyb.replace('有限责任公司', '')
			yyb = yyb.replace('股份有限公司', '')
			yyb = yyb.replace('有限公司', '')
			yyb = yyb.replace('证券营业部', '')
        	return yyb
		},
        formatMoney(money) {
			if (Math.abs(money) < 1000)
				return '';
			return (money / 10000).toFixed(1) + '亿';
		},
        show(x, y) {
            this.$refs.popupView.show(x, y);
        },
    },
    mounted() {
        // console.log('[LHB_DetailView.mounted]')
    },
    template:`
    <PopupView ref="popupView" :mask="false">
        <table class="basic-table" style="font-size: 12px">
            <thead>
                <tr> <th width=130> 席位名称 </th>  <th width=60> 买入 </th>  <th width=60> 卖出 </th> <th width=60> 净额 </th> </tr>
            </thead>
            <tbody>
                <tr v-for="(row, idx) in buys">
                    <td style="height:25px;"> {{ getYzName(row) }} </td>
                    <td style="height:25px;"> {{ formatMoney(row.mrje) }} </td>
                    <td style="height:25px;"> -{{ formatMoney(row.mcje) }} </td>
                    <td style="height:25px;"> {{ formatMoney(row.jme) }} </td>
                </tr>
                <tr> <td style="height:3px;background-color: #666;" colspan=4> </td> </tr>
                <tr v-for="(row, idx) in sells">
                    <td style="height:25px;"> {{ getYzName(row) }} </td>
                    <td style="height:25px;"> {{ formatMoney(row.mrje) }} </td>
                    <td style="height:25px;"> -{{ formatMoney(row.mcje) }} </td>
                    <td style="height:25px;"> {{ formatMoney(row.jme) }} </td>
                </tr>
                <tr style="background-color: #aaa;" v-if="rowData">
                    <td style="height:25px;"> 汇总 </td>
                    <td style="height:25px;"> {{ rowData.mrje.toFixed(1) }} 亿</td>
                    <td style="height:25px;"> -{{ rowData.mcje.toFixed(1) }} 亿 </td>
                    <td style="height:25px;"> {{ rowData.jme.toFixed(1) }} 亿 </td>
                </tr>
            </tbody>
        </table>
    </PopupView>
    `
};

let LHB_TableView = {
    extends: BaseTableView,
    components: {
        'LHB_DetailView': LHB_DetailView
    },
    data() {
        function yzRender(h, rowData, column) {
            let ds = JSON.parse(rowData['detail']);
            let yz = '';
            for (let d of ds) {
                if (d.yz && yz.indexOf(d.yz) < 0)
                    yz += d.yz + '&nbsp;&nbsp;';
            }
            return h('span', {innerHTML: yz});
        }

        return {
            columns: [{title: '', key: '_index_', width: 60},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '行业', key: 'ths_hy', width: 100, sortable: true},
                {title: 'THS-ZT', key: 'ths_ztReason', width: 100, sortable: true},
                {title: 'CLS-ZT', key: 'cls_ztReason', width: 100, sortable: true},
                {title: '热度', key: 'hots', width: 50, sortable: true},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true},
                {title: '成交额', key: 'amountY', width: 70, sortable: true},
                {title: '买入', key: 'mrje', width: 70, sortable: true, cellRender: DefaultRender.y2Render},
                {title: '净买入', key: 'jme', width: 70, sortable: true, cellRender: DefaultRender.y2Render},
                {title: '上榜类型', key: 'title', width: 100, cellRender: yzRender},
                {title: '分时图', key: 'fs', width: 300}],
            datas: null,
            url: null,

            rowData: null,// detail view data
        }
    },
    methods: {
        onCurDayChanged() {
            this.url = `/query-lhb/${this.curDay}`;
        },
        onClickCell(rowData, column, event, tableView) {
            if (column.key != 'title') return;
            if ( ! rowData.detail) return;
            let td = event.target.closest('td');
            let rr = td.getBoundingClientRect();
            this.rowData = rowData;
            this.$refs.detailView.show(rr.left, rr.top);
        }
    },
    template: `
        <div style="text-align:center; width:100%;display: flex; justify-content: center; ">
            <input style="border:solid 1px #999; height:25px;" @keydown.enter="doSearch($event.target.value)" />
        </div>
        <stock-table ref="stable" :columns="columns"
            :url="url" :day="curDay" style="width:100%;"
            @load-data-done="onLoadDataDone" @click-cell="onClickCell" >
        </stock-table>
        <LHB_DetailView ref='detailView' :rowData="rowData"> </LHB_DetailView>
    `,
};

function registerComponents(app) {
    app.component('GlobalView', GlobalView);
    app.component('AmountCompareView', AmountCompareView);
    app.component('TimeDegreeView', TimeDegreeView);
    app.component('ZdfbView', _ZdfbView);
    app.component('HotAnchorsView', HotAnchrosView);
    app.component('HotAnchorsGroupView', HotAnchrosGroupView);
    app.component('TabNaviView', TabNaviView);
    app.component('ZtTableView', ZT_TableView);
    app.component('LbTableView', LB_TableView);
    app.component('ZbTableView', ZB_TableView);
    app.component('DtTableView', DT_TableView);
    app.component('HotsTableView', Hots_TableView);
    app.component('AmountTableView', Amount_TableView);
    app.component('LhbTableView', LHB_TableView);
}

export default {
    App,
    registerComponents,
}