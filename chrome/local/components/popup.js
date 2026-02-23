import utils from './utils.js'

let PopupWindow = {
    zIndex : 8000,

    // return an Element
    _createPopup(mask, onClose) {
        let popup = document.createElement('div');
        popup.className = `popup-window ${mask ? 'popup-window-mask' : ''}`;
        popup.style.zIndex = this.zIndex ++;
        popup.addEventListener('click', function(evt) {
            evt.stopPropagation();
            let cl = evt.target.classList;
            if (cl.contains('popup-window')) {
                onClose(popup);
                popup.remove();
            }
        });
        popup.addEventListener('wheel', function(evt) {
            // evt.preventDefault();
            // evt.stopPropagation();
        });
        let cnt = document.createElement('div');
        cnt.className = 'content';
        popup.appendChild(cnt);
        popup._contentDiv = cnt;
        return popup;
    },

    // content: is a VNode (Vue.h )
    // config = {hideScrollBar?: false, mask?: false, destoryOnClose? : true, contentStyle?: '', }
    // onClose: function
    open(content, config, onClose) {
        if (! Vue.isVNode(content)) {
            return null;
        }
        let mask = config?.mask;
        let destoryOnClose = config?.destoryOnClose == undefined ? true : config.destoryOnClose;
        let popup = this._createPopup(mask, function() {
            if (destoryOnClose) {
                Vue.render(null, popup._contentDiv); // unmount
            }
            if (config?.hideScrollBar) {
                document.body.classList.remove('no-scroll');
            }
            if (onClose) onClose();
        });
        if (config?.contentStyle) {
            popup._contentDiv.style = config.contentStyle;
        }
        Vue.render(content, popup._contentDiv);
        document.body.appendChild(popup);
        if (config?.hideScrollBar) {
            document.body.classList.add('no-scroll');
        }
        return popup;
    },
};

let PopupView = {
    props: {
        mask: {default: true},
        modal: {default: false},
        hideScrollBar: {default: false},
    },
    emits: ['close'],
    created() {
        // console.log('[PopupView.created]');
    },
    data() {
        return {
            zIndex: PopupWindow.zIndex++,
            className: `popup-window ` + (this.mask ? 'popup-window-mask' : ''),
            visible: false,
            x: 0, y: 0,
        }
    },
    methods: {
        clickMask(evt) {
            evt.stopPropagation();
            if (evt.target.classList.contains('popup-window') && !this.modal) {
                this.close();
            }
        },
        close() {
            this.visible = false;
            if (this.hideScrollBar) {
                document.body.classList.remove('no-scroll');
            }
            this.$emit('close', this);
        },
        show(x, y) {
            this.visible = true;
            if (typeof(x) == 'number') this.x = x;
            if (typeof(y) == 'number') this.y = y;
        },
    },
    beforeMount() {
        if (this.hideScrollBar) {
            document.body.classList.add('no-scroll');
        }
    },
    mounted() {
        // console.log('[PopupView.mounted]');
    },
    template: `
        <teleport to="body">
            <div :class="className" :style="{zIndex: zIndex}" @click="clickMask($event)" v-show="visible">
                <div class="content" v-bind="$attrs" :style="{left: x, top: y}">
                    <slot> </slot>
                </div>
            </div>
        </teleport>
    `
};
/**
 * <trade-date-picker default-date="2026-01-05" >  </trade-date-picker>
 * V.h(TradeDatePicker, {onSelectDayEnd: function, })
 */
let TradeDatePicker = {
    props: ['defaultDate'], // set default day
    emits: ['select-day-end'],
    data() {
        return {
            curSelDate : this.defaultDate, // String YYYY-mm-dd
            tradeDays: {},
            curPageDays: null,
            curPageYear: null,
            curPageMonth: null,
        }
    },
    methods: {
        init() {
            let d = this.curSelDate || new Date();
            if (typeof(d) == 'string') {
                d = new Date(d);
            }
            let y = d.getFullYear();
            let m = d.getMonth() + 1;
            this.changeMonth(y, m);
        },
        changeMonth(year, month) {
            year = parseInt(year);
            month = parseInt(month);
            if (month == 0) {
                year -= 1;
                month = 12;
            } else if (month == 13) {
                month = 1;
                year += 1;
            }
            this.curPageYear = year;
            this.curPageMonth = month;
            let ds = this.getDays(year, month);
            this.curPageDays = ds;
        },
        getDays(year, month) {
            year = parseInt(year);
            month = parseInt(month) - 1;
            let firstDate = new Date(year, month, 1);
            let sweek = (firstDate.getDay() + 6) % 7; // 0 ~ 6, 一 ~ 日
            let days = [];
            for (let i = 0; i < 31; i++) {
                let d = new Date(year, month, i + 1);
                if (d.getFullYear() == year && d.getMonth() == month) {
                    days.push(d);
                } else {
                    break;
                }
            }
            for (let i = sweek - 1, j = 0; i >= 0; i--, j ++) {
                let d = new Date(year, month, - j);
                days.unshift('');
            }
            let lastDate = days[days.length - 1];
            let eweek = (lastDate.getDay() + 6) % 7;
            for (let i = eweek + 1, j = 0; i < 7; i++, j++) {
                let d = new Date(year, month + 1, 1 + j);
                days.push('');
            }
            return days;
        },
        getWeek(date) {
            let sweek = (date.getDay() + 6) % 7; // 0 ~ 6, 一 ~ 日
            return sweek;
        },
        onSelectDay(day, able) {
            if (! able || !day) return;
            this.curSelDate = day;
            this.$emit('select-day-end', day);
        },
        onChangeMonth(num) {
            this.changeMonth(this.curPageYear, this.curPageMonth + num);
        },
    },
    beforeMount() {
        this.init();
        axios.get('/get-trade-days').then((resp) => {
            for (let d of resp.data) {
                if (d.length == 8) {
                    d = d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
                }
                this.tradeDays[d] = true;
            }
        });
    },
    render() {
        const {h} = Vue;
        let ym = `${this.curPageYear}-${this.curPageMonth}`;
        let today = utils.formatDate(new Date());
        let tds = [];
        let days = this.curPageDays;
        for (let i = 0; i < days.length; i++) {
            let cday = utils.formatDate(days[i]) || '';
            let able = cday ? this.tradeDays[cday] : false;
            let sday = cday ? parseInt(cday.substring(8)) : '';
            tds.push(h('td', {val: cday, able: !!able, class: {'no-able': !able,
                        sel: cday && cday == this.curSelDate, today: cday == today},
                        onClick: () => this.onSelectDay(cday, able) }, sday));
        }
        let trs = [];
        for (let i = 0; i < days.length; i += 7) {
            let tr = h('tr', null, tds.slice(i, i + 7));
            trs.push(tr);
        }
        let table = h('table', null, [
            h('tr', null, [h('td', {colspan: 5}, ym),
                           h('td', {onclick: () => this.onChangeMonth(-1), innerHTML: '&lt;'}),
                           h('td', {onclick: () => this.onChangeMonth(1), innerHTML: '&gt;'})]),
            h('tr', {innerHTML: `<th>一</th><th>二</th><th>三</th><th>四</th><th>五</th><th>六</th><th>日</th>`}),
            ...trs
        ]);
        return h('div', {class: 'datepicker'}, [table]);
    },
};

// opener = { elem?: HtmlElement, x?: Number, y?:Number, defaultDate?: 'YYYY-MM-DD' }
// onSelDay = function(selDay) callback function
function openTradeDatePicker(opener, onSelDay) {
    const DW = window.innerWidth;
    let rect = opener.elem?.getBoundingClientRect();
    let x = 0, y = 0;
    if (rect) {
        x = rect.left;
        y = rect.bottom;
    } else {
        if (opener.x || opener.left) x = opener.x || opener.left;
        if (opener.y || opener.top) x = opener.y || opener.top;
    }
    let popup = null;
    let nodes = Vue.h(TradeDatePicker, {
        defaultDate: opener?.defaultDate,
        onSelectDayEnd: (selDay) => {
            popup.remove();
            if (onSelDay) onSelDay(selDay);
        }
    });
    popup = PopupWindow.open(nodes, {contentStyle: `left:${x}px; top: ${y}px;`});
}

export {
    PopupWindow,TradeDatePicker, openTradeDatePicker, PopupView
}