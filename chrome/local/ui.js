
/**
 * columns = [{
 *      key: str of data's attr key, or '_index_',
 *      title: str, title of table header
 *      sortable ?: boolean, default is false
 *      cellRender ?: function(h, rowData, column)
 *      sorter? : function(a, b, tag)  tag = 'asc' | 'desc' return -1, 0, 1
 *      
 *  }, ...]
 */

import config from './config.js'

let BasicTable = {
    name: 'BasicTable',
    props: {
        columns: {type: Array, default: () => []},
        datas: {type: Array, default: () => []},
    },
    data() {
        // console.log('BasicTable.data()');
        return {
            tableCss: 'basic-table',
            filterDatas: this.datas.slice(),
            curSelRow: null,
        }
    },
    methods : {
        getDefaultSorter(key, _sort) {
            return function(a, b) {
                a = a[key], b = b[key];
                if (a == undefined) a = null;
                if (b == undefined) b = null;
                if (a == null && b == null)
                    return 0;
                if (a == null) {
                    return -1;
                }
                if (b == null) {
                    return 1;
                }
                if (typeof(a) != typeof(b)) {
                    // TODO:
                }
                if (typeof(a) == 'string') {
                    if (_sort == 'asc')
                        return a.localeCompare(b);
                    return b.localeCompare(a);
                } else if (typeof(a) == 'number' || typeof(a) == 'boolean') {
                    if (_sort == 'asc')
                        return a - b;
                    return b - a;
                }
                return 0;
            }
        },
        changeSort(column) {
            if (! column.sortable)
                return;
            if (! column._sort) column._sort = 'asc';
            else if (column._sort == 'asc') column._sort = 'desc';
            else if (column._sort == 'desc') column._sort = '';
            for (let h of this.columns) {
                if (h != column && h.sortable) h._sort = '';
            }
            if (! column._sort) {
                this.filterDatas = this.datas.slice();
                return;
            }
            let sorter = column.sorter ? function(a, b) {return column.sorter(a, b, column._sort);} : this.getDefaultSorter(column.key, column._sort);
            this.filterDatas.sort(sorter);
        },
        clearSort() {
            for (let h of this.columns) {
                if ( h.sortable) h._sort = '';
            }
        },
        onClickCell(rowData, column) {
            this.$emit('click-cell', rowData, column, this);
        },
        onDblclickCell(rowData, column) {
            this.$emit('dblclick-cell', rowData, column, this);
        },
        onClickRow(rowData) {
            if (this.curSelRow != rowData)
                this.curSelRow = rowData;
            this.$emit('click-row', rowData, this);
        },
        onDblclickRow(rowData) {
            this.$emit('dblclick-row', rowData, this);
            console.log('BasicTable.onDblclickRow', rowData);
        },
        filter(text) {
            if (! this.datas) {
                return;
            }
            let {cond, qrs} = this.getSearchConditions(text);
            let rs = [];
            for (let d of this.datas) {
                if (this.matchData(d, qrs, cond))
                    rs.push(d);
            }
            this.filterDatas = rs;
            this.clearSort();
        },
        getSearchConditions(text) {
            let qs, cond, qrs = new Set();
            if (!text || !text.trim()) {
                return {cond, qrs};
            }
            text = text.trim().toUpperCase();
            if (text.indexOf('|') >= 0) {
                qs = text.split('|')
                cond = 'OR'
            } else {
                qs = text.split(' ')
                cond = 'AND'
            }
            for (let q of qs) {
                q = q.trim();
                if (q && !qrs.has(q))
                    qrs.add(q);
            }
            return {cond, qrs};
        },
        getSearchData(data) {
            let rs = {};
            for (let hd of this.columns) {
                rs[hd.key] = data[hd.key] || '';
            }
            return rs;
        },
        matchData(data, qrs, cond) {
            if (! qrs || !cond)
                return true;
            for (let q of qrs) {
                let fd = false;
                let sd = this.getSearchData(data);
                for (let k in sd) {
                    let v = sd[k];
                    if (typeof(v) == 'string') {
                        if (v.toUpperCase().indexOf(q) >= 0) {
                            fd = true;
                            break;
                        }
                    }
                }
                if (cond == 'AND' && !fd)
                    return false;
                if (cond == 'OR' && fd)
                    return true;
            }
            if (cond == 'AND')
                return true;
            return false;
        },
        matchKey(data, qrs, cond, key) {
            for (let q of qrs) {
                let fd = false;
                let sd = this.getSearchData(data);
                let v = sd[key];
                if (typeof(v) == 'string') {
                    if (v.toUpperCase().indexOf(q) >= 0) {
                        fd = true;
                    }
                }
                if (cond == 'AND' && !fd)
                    return false;
                if (cond == 'OR' && fd)
                    return true;
            }
            if (cond == 'AND')
                return true;
            return false;
        }
    },
    render() {
        // console.log('BaseTable.render');
        const {h} = Vue;
        let hds = [];
        for (let column of this.columns) {
            let hdText = column.title + ' ' + (column.sortable ? (column._sort == 'asc' ? '&#8593;' : column._sort == 'desc' ? '&#8595;' : '&#9830;') : '');
            let a = {onClick: (evt) => {this.changeSort(column);}, innerHTML: hdText};
            for (let k in column) {
                if (typeof(column[k]) != 'function')
                    a[k] = column[k];
            }
            hds.push(h('th', a));
        }
        let theader = h('thead', h('tr', hds));
        let trs = [];
        for (let i = 0; i < this.filterDatas.length; i++) {
            let tds = [];
            let rowData = this.filterDatas[i];
            rowData._index_ = i + 1;
            for (let column of this.columns) {
                let cellVal = null;
                if (column.cellRender) cellVal = column.cellRender(h, rowData, column);
                else cellVal = rowData[column.key];
                tds.push(h('td', {
                    onclick: () => this.onClickCell(rowData, column),
                    ondblclick: () => this.onDblclickCell(rowData, column)
                }, cellVal));
            }
            let tr = h('tr', {
                class: {sel: this.curSelRow == rowData},
                onClick: () => this.onClickRow(rowData),
                ondblclick: () => this.onDblclickRow(rowData),
            }, tds);
            trs.push(tr);
        }
        let tbody = h('tbody', trs);
        return h('table', {class: this.tableCss}, [theader, tbody]); // this.$slots.default()
    },
}

let StockTableDefaultRender = {
    codeRender(h, rowData, column) {
        let code = rowData.code;
        let html = `<a href="https://www.cls.cn/stock?code=${code}" target=_blank> 
                    <span style="color:#383838; font-weight:bold;" >${rowData.name}</span> </a> <br/>
                    <span style="color:#666;font-size:12px;"> ${code}</span>`;
        return h('span', {innerHTML: html});
    },
    // 热度
    hotsRender(h, rowData, column) {
        let val = '';
        if (rowData[column.key]) val =  String(rowData[column.key]) + '°';
        return h('span', val);
    },
    // 涨幅
    zfRender(h, rowData, column) {
        let zf = rowData[column.key];
        let val = '';
        let attrs = {};
        if (typeof(zf) == 'number') {
            val = (zf * 100).toFixed(1) + '%';
            if (zf >= 0) attrs.style = 'color: #de0422';
            else attrs.style = 'color: #52C2A3';
        }
        return h('span', attrs, val);
    },
    // 元 -> 亿元
    yRender(h, rowData, column) {
        let z = rowData[column.key];
        if (typeof(z) == 'number') {
            z = parseInt(z / 100000000) + '亿';
        }
        return h('span', z);
    },
    // 亿元 -> 亿元
    y2Render(h, rowData, column) {
        let z = rowData[column.key];
        if (typeof(z) == 'number') {
            if (z < 1) z = z.toFixed(1);
            else z = parseInt(z);
        }
        return h('span', `${z}亿`);
    },
    // 涨停原因
    ztReasonRender(h, rowData, column) {
        const ELIPSE_NUM = 35;
        let val = rowData[column.key] || '';
        let elipse = val;
        if (val && val.length > ELIPSE_NUM) {
            elipse = val.substring(0, ELIPSE_NUM) + '...';
        }
        let idx = elipse.indexOf('|');
        if (idx > 0 && idx < 20) {
            let cur = h('span', {class: 'zt-reason'}, elipse.substring(0, idx));
            let tail = h('span', {title: val.substring(idx + 1)}, ` ${elipse.substring(idx + 1)}`);
            return h('div', {class : 'div-zt-reason'}, [cur, tail]);
        }
        if (val != elipse || val.length > 30) {
            return h('span', {title: val}, elipse);
        }
        return h('span', {class: 'zt-reason'}, val);
    },
    // 涨速
    zsRender(h, rowData, column) {
        let val = rowData[column.key];
        if (typeof(val) == 'number' && val) {
            val = '↑&nbsp;' + val.toFixed(1);
        }
        return h('span', {innerHTML: val});
    },
    // 连板
    lbRender(h, rowData, column) {
        let val = rowData[column.key];
        if (typeof(val) == 'number' && val) {
            val = `${val}板`;
        }
        return h('span', val);
    },
    thsDtReasonRender(h, rowData, column) {
        let val = rowData[column.key];
        return h('span', {class: 'ths-dt-reason'}, val);
    },
    fsRender(h, rowData, column) {
        return h('timeline-view', {code: rowData.code, day: rowData.day, });
    }
}

// let StockTable = deepCopy(BasicTable);
// extendObject(StockTable, {
let StockTable = {
    // mixins: [BasicTable],
    extends: BasicTable,
    name: 'StockTable',
    props: {
        day: {type: String, default: () => ''},
        url: {type: String, default: () => ''},
    },
    data() {
        // console.log('StockTable.data()');
        this._initDefaultRenders();
        this._loadData();
        this.$watch('url', this.onUrlChanged);
        return {
            tableCss: ['basic-table', 'stock-table'],
        }
    },
    methods: {
        _loadData() {
            if (! this.url)
                return;
            axios.get(this.url).then(res => {
                this.datas.splice(0, this.datas.length);
                for (let it of res.data) {
                    this.datas.push(it);
                }
                this.filterDatas = this.datas.slice();
                this._adjustStdCode(this.datas);
                this.onLoadDataDone();
                // console.log(this.filterDatas)
            });
        },
        _adjustStdCode(datas) {
            if (! datas) return;
            for (let it of datas) {
                if (it.secu_code && !it.code) {
                    if (it.secu_code[0] == 's') it.code = it.secu_code.substring(2);
                    else if (it.secu_code[0] == 'c') it.code = it.secu_code;
                }
                if (it.secu_name && !it.name) {
                    it.name = it.secu_name;
                }
            }
        },
        _initDefaultRenders() {
            for (let col of this.columns) {
                if (col.cellRender) continue;
                if (col.key == 'code') col.cellRender = StockTableDefaultRender.codeRender;
                else if (col.key == 'hots') col.cellRender = StockTableDefaultRender.hotsRender;
                else if (col.key == 'zf' || col.key == 'change') col.cellRender = StockTableDefaultRender.zfRender;
                else if (col.key == 'cmc' || col.key == 'amount') col.cellRender = StockTableDefaultRender.yRender;
                else if (col.key == 'amountY') col.cellRender = StockTableDefaultRender.y2Render;
                else if (col.key == 'assoc_desc' || col.key == 'up_reason') col.cellRender = StockTableDefaultRender.ztReasonRender;
                else if (col.key == 'cls_ztReason' || col.key == 'ths_ztReason') col.cellRender = StockTableDefaultRender.ztReasonRender;
                else if (col.key == 'zs') col.cellRender = StockTableDefaultRender.zsRender;
                else if (col.key == 'limit_up_days') col.cellRender = StockTableDefaultRender.lbRender;
                else if (col.key == 'ths_dt_reason') col.cellRender = StockTableDefaultRender.thsDtReasonRender;
                else if (col.key == 'fs') col.cellRender = StockTableDefaultRender.fsRender;
            }
        },
        onUrlChanged(newUrl) {
            this._loadData();
        },
        onLoadDataDone() {
            this.$emit('load-data-done', this.filterDatas);
            this.$nextTick(() => this.bindTimeLine());
        },
        getSearchData(data) {
            let rs = {};
            for (let hd of this.columns) {
                rs[hd.key] = data[hd.key] || '';
            }
            rs['code'] = data['code'] || '';
            rs['name'] = data['name'] || '';
            return rs;
        },
        getCodeList() {
            if (! this.filterDatas)
                return [];
            let rs = [];
            for (let k of this.filterDatas) {
                if (k.code)
                    rs.push(k.code);
            }
            return rs;
        },
        openKLineDialog(rowData) {
            let code = rowData.code;
            let rdatas = { codes: this.getCodeList(), day: this.day};
            // this.notify({name: 'BeforeOpenKLine', src: this, data: rdatas, rowData});
            axios.post(`/openui/kline/${code}`, rdatas);
        },
        onDblclickRow(rowData) {
            this.openKLineDialog(rowData);
        },
    },
};

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

}

let _TimeLineView = {
    props:['code', 'day'],
    data() {
        return {
            zf: null,
            amount: null,
        }
    },
    methods: {
        wrapData() {},
    },
    mounted() {
        this.wrapData.view = new TimeLineView(300, 600, this.$el);

    },
    render() {
        return Vue.h('canvas', {style: 'width:300px; height: 60px; background-color: #fafafa;', width: 300, height: 60});
    }
};

function registerComponents(app) {
    app.component('basic-table', BasicTable);
    app.component('stock-table', StockTable);
    app.component('timeline-view', _TimeLineView);
}

export default {
    BasicTable,
    StockTable,
    StockTableDefaultRender,
    PopupWindow,
    TimeLineView,
    registerComponents,
}