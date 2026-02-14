import utils from './utils.js'

let PopupWindow = {
    zIndex : 8000,

    // return an Element
    _createPopup(onClose) {
        let popup = document.createElement('div');
        popup.className = 'popup-window';
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
        return popup;
    },

    // content: is a VNode (Vue.h )
    // config = {hideScrollBar: true}
    // onClose: function
    open(content, config, onClose) {
        if (! Vue.isVNode(content)) {
            return null;
        }
        let popup = this._createPopup(function() {
            Vue.render(null, popup); // unmount
            if (config?.hideScrollBar)
                document.body.classList.remove('no-scroll');
            if (onClose) onClose();
        });
        Vue.render(content, popup);
        document.body.appendChild(popup);
        if (config?.hideScrollBar)
            document.body.classList.add('no-scroll');
        return popup;
    },
};

let TradeDatePicker = {
    data() {
        return {
            curSelDate : null, // String YYYY-mm-dd
            tradeDays: {},
            changeInfo: {},
            curPageDays: null,
        }
    },
    methods: {
        reset() {
            let d = this.curSelDate || new Date();
            if (typeof(d) == 'string')
                d = new Date(d);
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
            this.changeInfo.year = year;
            this.changeInfo.month = month;
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
        onSel(day, able) {
            if (! able) return;
            this.curSelDate = day;
        },
        onChangeMonth(num) {
            this.changeMonth(this.changeInfo.year, this.changeInfo.month + num);
        },
    },
    beforeMount() {
        this.reset();
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
        let ym = `${this.changeInfo.year}-${this.changeInfo.month}`;
        let today = utils.formatDate(new Date());
        let tds = [];
        let days = this.curPageDays;
        for (let i = 0; i < days.length; i++) {
            let cday = utils.formatDate(days[i]) || '';
            let able = cday ? this.tradeDays[cday] : false;
            let sday = cday.substring(8);
            tds.push(h('td', {val: cday, able: !!able, class: {'no-able': !able,
                        sel: cday == this.curSelDate, today: cday == today},
                        onClick: () => this.onSel(cday, able) }, sday));
        }
        let trs = [];
        for (let i = 0; i < days.length; i += 7) {
            let tr = h('tr', null, tds.slice(i, i + 7));
            trs.push(tr);
        }
        return h('table', {class: 'content datepicker'}, [
            h('tr', null, [h('td', {colspan: 5}, ym), 
                           h('td', {onclick: () => this.onChangeMonth(-1), innerHTML: '&lt;'}), 
                           h('td', {onclick: () => this.onChangeMonth(1), innerHTML: '&gt;'})]),
            h('tr', {innerHTML: `<th>一</th><th>二</th><th>三</th><th>四</th><th>五</th><th>六</th><th>日</th>`}),
            ...trs
        ]);
    },
};

export {
    PopupWindow,TradeDatePicker
}