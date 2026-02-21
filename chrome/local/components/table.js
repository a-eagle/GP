import {TimeLineView, TimeLineViewManager} from './timeline-view.js'
import utils from './utils.js';
/**
 * columns = [{
 *      key: str of data's attr key, or '_index_',
 *      title: str, title of table header
 *      sortable ?: boolean, default is false
 *      cellRender ?: function(h, rowData, column, table)
 *      sorter? : function(a, b, key, tag)  tag = 'asc' | 'desc' return -1, 0, 1
 *      
 *  }, ...]
 */
let uniqueKey = 1000000;

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
        getDefaultSorter(key) {
            for (let t of this.datas) {
                if (t[key] == null || t[key] == undefined)
                    continue;
                if (typeof(t[key]) == 'string')
                    return DefaultSorter.stringSorter;
                if (typeof(t[key]) == 'number' || typeof(t[key]) == 'bigint')
                    return DefaultSorter.numberSorter;
                if (typeof(t[key]) == 'boolean')
                    return DefaultSorter.booleanSorter;
            }
            return DefaultSorter.noSorter;
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
            let _sorter = column.sorter ? column.sorter : this.getDefaultSorter(column.key);
            let ws = function(a, b) {return _sorter(a, b, column.key, column._sort);}
            this.filterDatas.sort(ws);
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
            // console.log('BasicTable.onDblclickRow', rowData);
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
        matchAttr(data, qrs, cond, attrName) {
            for (let q of qrs) {
                let fd = false;
                let sd = this.getSearchData(data);
                let v = sd[attrName];
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
        },
        onLoadFsEnd(rowData, tl) {
            rowData.dynamicAmount = tl.amount;
            rowData.dynamicZf = tl.zf;
            rowData.zs = tl.zs;
        },
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
                if (column.cellRender) cellVal = column.cellRender(h, rowData, column, this);
                else cellVal = rowData[column.key];
                tds.push(h('td', {
                    onclick: () => this.onClickCell(rowData, column),
                    ondblclick: () => this.onDblclickCell(rowData, column)
                }, cellVal));
            }
            if (! rowData._rkey) {
                rowData._rkey = uniqueKey++;
            }
            let tr = h('tr', {
                key: rowData._rkey,
                class: {sel: this.curSelRow == rowData},
                onClick: () => this.onClickRow(rowData),
                ondblclick: () => this.onDblclickRow(rowData),
            }, tds);
            trs.push(tr);
        }
        let tbody = h('tbody', trs);
        let table = h('table', {class: this.tableCss}, [theader, tbody]); // this.$slots.default()
        return table;
    },
    mounted() {
        // console.log('[BasicTable].mounted')
    },
}

let DefaultRender = {
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
            if (column.key == 'dynamicZf')
                val = zf.toFixed(1) + '%';
            else
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
    fsRender(h, rowData, column, table) {
        return h(TimeLineView, {code: rowData.code, day:
            rowData.day, onLoadDataEnd: (tl) => table.onLoadFsEnd(rowData, tl) }
        );
    }
}

let DefaultSorter = {
    hotsSorter(a, b, key, _sort) {
        let ak = a[key], bk = b[key];
        if (ak && bk) {
            return _sort == 'asc' ? ak - bk : bk - ak;
        }
        if (ak) return -1;
        if (bk) return 1;
        return 0;
    },
    numberSorter(a, b, key, _sort) {
        let ak = a[key], bk = b[key];
        if (typeof(ak) == 'number' && typeof(bk) == 'number') {
            if (_sort == 'asc')
                return ak - bk;
            return bk - ak;
        }
        if (typeof(ak) == 'number') return -1;
        if (typeof(bk) == 'number') return 1;
        return 0;
    },
    booleanSorter(a, b, key, _sort) {
        let ak = a[key], bk = b[key];
        if (typeof(ak) == 'boolean' && typeof(bk) == 'boolean') {
            if (_sort == 'asc')
                return ak - bk;
            return bk - ak;
        }
        if (typeof(ak) == 'number') return -1;
        if (typeof(bk) == 'number') return 1;
        return 0;
    },
    stringSorter(a, b, key, _sort) {
        let ak = a[key], bk = b[key];
        if (typeof(ak) == 'string' && typeof(bk) == 'string') {
            if (_sort == 'asc')
                return ak.localeCompare(bk);
            return bk.localeCompare(ak);
        }
        if (typeof(ak) == 'string') return -1;
        if (typeof(bk) == 'string') return 1;
        return 0;
    },
    noSorter(a, b, key,  _sort) {
        return 0;
    }
}

// let StockTable = deepCopy(BasicTable);
// extendObject(StockTable, {
// 如果有分时图，则需要设置day属性，否则无法显示分时图
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
        this._initDefaults();
        this._loadData();
        this.$watch('url', this.onUrlChanged);
        return {
            timerId: 0,
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
                    this._adjustItemData(it);
                }
                this.filterDatas = this.datas.slice();
                this.onLoadDataDone();
                // console.log(this.filterDatas)
            });
        },
        _adjustItemData(it) {
            if (! it) return;
            if (it.secu_code && !it.code) {
                if (it.secu_code[0] == 's') it.code = it.secu_code.substring(2);
                else if (it.secu_code[0] == 'c') it.code = it.secu_code;
            }
            if (it.secu_name && !it.name) {
                it.name = it.secu_name;
            }
        },
        _initDefaults() {
            for (let col of this.columns) {
                if (col.cellRender) continue;
                if (col.key == 'code') col.cellRender = DefaultRender.codeRender;
                else if (col.key == 'hots') {
                    col.cellRender = DefaultRender.hotsRender;
                    col.sorter = DefaultSorter.hotsSorter;
                }
                else if (col.key == 'zf' || col.key == 'change' || col.key == 'dynamicZf') col.cellRender = DefaultRender.zfRender;
                else if (col.key == 'cmc' || col.key == 'amount' || col.key == 'dynamicAmount') col.cellRender = DefaultRender.yRender;
                else if (col.key == 'amountY') col.cellRender = DefaultRender.y2Render;
                else if (col.key == 'assoc_desc' || col.key == 'up_reason') col.cellRender = DefaultRender.ztReasonRender;
                else if (col.key == 'cls_ztReason' || col.key == 'ths_ztReason') col.cellRender = DefaultRender.ztReasonRender;
                else if (col.key == 'zs') col.cellRender = DefaultRender.zsRender;
                else if (col.key == 'limit_up_days') col.cellRender = DefaultRender.lbRender;
                else if (col.key == 'ths_dt_reason') col.cellRender = DefaultRender.thsDtReasonRender;
                else if (col.key == 'fs') col.cellRender = DefaultRender.fsRender;
            }
        },
        onUrlChanged(newUrl) {
            this._loadData();
        },
        onLoadDataDone() {
            this.$emit('load-data-done', this.filterDatas);
            // this.$nextTick(() => this.bindTimeLine());
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
                    rs.push({code: k.code, day: this.day});
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
        checkVisbileTimeline() {
            let elem = this.$el;
            let visible = utils.isClientVisible(elem);
            if (! visible)
                return;
            let tls = document.querySelectorAll('canvas.timeline');
            let rect = elem.getBoundingClientRect();
            let HEIGHT = Math.min(window.innerHeight, rect.bottom);
            for (let i = 0; i < tls.length; i++) {
                let irect = tls[i].getBoundingClientRect();
                if (irect.top < 0) continue;
                if (irect.top >= HEIGHT) break;
                let key = tls[i].getAttribute('key-id');
                TimeLineViewManager.reload(key, this.day);
            }
        },
    },
    mounted() {
        // console.log('[StockTable].mounted', this.$el)
        this.timerId = setInterval(() => {
            this.checkVisbileTimeline();
        }, 1000);
    },
    unmounted() {
        console.log('[StockTable].unmounted', this.$el)
        clearInterval(this.timerId);
        this.timerId = 0;
    }
};

let PageniteView = {
    emits: ['url-changed'],
    props: {
        baseUrl: {required: true, type: String},
        curPage: {type: Number, default: 1},
        pageSize: {type: Number, default: 50},
        total: {type: Number, default: 0},
    },
    data() {
        return {
            _total : this.total,
            _curPage : this.curPage,
        };
    },
    methods: {
        getUrl() {
            let url = this.baseUrl;
            if (url.indexOf('?') < 0) url += '?';
            else url += '&';
            return `${url}curPage=${this._curPage}&pageSize=${this.pageSize}`;
        },
        onChangePage(page) {
            this._curPage = page;
        },
    },
    // call before created()
    watch: {
        _curPage: {
            handler() {
                this.$emit('url-changed', this.getUrl());
            },
            immediate: true
        },
    },
    created() {
    },
    beforeMount() {
    },
    render() {
        const {h} = Vue;
        let items = [];
        const maxPage = parseInt((this._total + this.pageSize - 1) / this.pageSize);
        for (let i = 1; i <= maxPage; i++) {
            items.push(h('span',
                {class: {'page-item': true, 'page-item-select': i == this._curPage},
                 onClick: () => this.onChangePage(i)
                }, 
                i));
        }
        return h('div', {class: 'pagenite'}, items);
    },
    
};

export {
    BasicTable,
    StockTable,
    DefaultRender,
    PageniteView,
}