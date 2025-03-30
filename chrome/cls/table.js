/**
 *   st = new StockTable(headers);
 *   st.initStyle(); 
 *   st.buildUI();
 */
class StockTable {
    // headers = [ {text: 'xxx', name: 'xx', width: 60, sortable: true,
    //              sortVal?: function(rowData), defined? : true,
    //              cellRender?: function(rowIdx, rowData, header, tdObj) },
    //              headerRender? : function(colIdx, header, thObj),
    //           ...]
    // fix headers : 'zs' 涨速, 'hots': 热度  'zf': 涨幅(根据'fs'列自动生成)  mark_color 标记颜色
    // 必须有列：secu_code(如果有code, 会根据code自动生成), secu_name
    // {name: 'hots', full? : true}
    constructor(headers) {
        this.headers = headers;
        this.lastSortHeader = null;
        this.datas = null;
        this.srcDatas = null;
        this.datasMap = null; // map of this.datas, key = secu_code
        this.day = null;
        this.tradeDays = null;

        this.table = null;
        this.headersTr = null;
        this.trs = {};
        this.tlMgr = new TimeLineUIManager();
        this.config = {elipseNum: 40};
        this.init()
    }

    setTradeDays(days) {
        this.tradeDays = days;
    }

    setDay(day) {
        this.day = day;
    }

    init() {
	    this.initStyle();
        this.table = $('<table class="my-stoks-table" > </table>');;
        this.initHeadersDefault();
        this.buildHeadersUI();
    }

    createTimeLineView(code, width, height) {
        width = width || 300;
        height = height || 60;
        let view = new TimeLineView(width, height);
        this.tlMgr.add(view);
        view.loadData(code, this.day);
        return view;
    }

    _updateAttrUI(rowData, header, val) {
        let key = rowData.key;
        if (! this.trs[key])
            return;
        let td = this.trs[key].find('td:nth-child(' + (header.__colIdx__ + 1) + ')');
        td.empty();
        header.cellRender(rowData.__rowIdx__, rowData, header, td);
    }

    _defineAttr(obj, attr, val) {
        let thiz = this;
        Object.defineProperty(obj, attr.name, {
            get: function() {return val;},
            set: function(newVal) {
                if (val == newVal)
                    return;
                val = newVal;
                thiz._updateAttrUI(obj, attr, newVal);
            }
        });
    }

    _defineProterties() {
        if (! this.headers || !this.datas)
            return;
        let hds = [];
        for (let i = 0; i < this.headers.length; i++) {
            if (this.headers[i].defined)
                hds.push(this.headers[i]);
        }
        if (! hds.length)
            return;
        for (let i = 0; i < this.datas.length; i++) {
            let cur = this.datas[i];
            for (let j = 0; j < hds.length; j++) {
                if (! cur) continue;
                this._defineAttr(cur, hds[j], cur[hds[j].name]);
            }
        }
    }

    // should call setDay before setData
    setData(data) {
        let mdata = {};
        data = data || [];
        for (let i = data.length - 1; i >= 0; i--) {
            let code = data[i].code;
            if (!data[i].secu_code && code) {
                data[i].secu_code = code[0] == '6' ? 'sh' + code : 'sz' + code;
            }
            if (data[i].secu_code) {
                code = this.buildUI_stdCode(data[i].secu_code);
            }
            if (!code || (code[0] != '0' && code[0] != '3' && code[0] != '6')) {
                data.splice(i, 1);
            } else {
                data[i].code = code;
                mdata[data[i].secu_code] = data[i];
            }
        }
        for (let i = 0; i < data.length; i++) {
            data[i].__rowIdx__ = i;
            data[i].key = data[i].secu_code;
        }
        this.lastSortHeader = null;
        this.trs = {};
        this.tlMgr = new TimeLineUIManager();
        this.srcDatas = data;
        this.datas = data.slice();
        this.datasMap = mdata;
        this.loadMarkColors();
        this._defineProterties()
        this.loadCodesInfo();
    }

    buildHeadersUI() {
        if (this.headersTr || !this.headers) {
            return;
        }
        let thiz = this;
        let tr = $('<tr style="vertical-align: middle; "> </tr>');
        for (let i = 0; i < this.headers.length; i++) {
            let hd = this.headers[i];
            let th = $('<th> </th>');
            hd.headerRender(i, hd, th, this);
            if (hd.sortable) {
                th.click(function() {
                    thiz.sortHeader($(this).attr('name'));
                });
            }
            tr.append(th);
        }
        
        this.headersTr = tr;
        this.table.append(tr);
    }

    _headerRender(colIdx, header, thObj, thiz) {
        for (let k in header) {
            if (typeof(header[k]) != 'function')
                thObj.attr(k, header[k]);
        }
        let txt = header.text;
        if (header.__sort__ == 'asc') {
            txt += '&nbsp;&#8593;';
        } else if (header.__sort__ == 'desc') {
            txt += '&nbsp;&#8595;';
        } else if (header.sortable) {
            txt += '&#9830;';
        }
        thObj.html(txt);
        if (header.name == 'fs') {
            thiz._fsHeaderRender(colIdx, header, thObj);
        }
    }

    _fsHeaderRender(colIdx, header, thObj) {
        let btn = $('<button> &nbsp;&nbsp;</button>');
        let thiz = this;
        btn.click(function() {
            if (! window.dpFS) {
                window.dpFS = new TradeDatePicker();
            }
            window.dpFS.removeListener('select');
            window.dpFS.addListener('select', function(evt) {
                let dd = new Date(evt.date);
                let ss = '日一二三四五六';
                btn.text(evt.date.substring(5) + ' ' + ss.charAt(dd.getDay()));
                for (let view of thiz.tlMgr.views) {
                    view.day = evt.date;
                    view.reloadData();
                }
            });
            window.dpFS.openFor(this);
        });
        thObj.append(btn);
    }

    initHeadersDefault() {
        if (! this.headers) 
            return;
        let proxyHeaders = [];
        let thiz = this;
        function updateAttr(target, attr, op) {
            let th = thiz.headersTr.find('th:nth-child(' + (target.__colIdx__ + 1) +')');
            th.empty()
            if (op == 'del') th.removeAttr(attr);
            target.headerRender(target.__colIdx__, target, th);
        }
        let hander = {
            set: function(target, attr, value) {
                target[attr] = value;
                updateAttr(target, attr, 'set');
                return true;
            },
            deleteProperty: function(target, attr) {
                delete target[attr];
                updateAttr(target, attr, 'del');
                return true;
            },
        };
        this.headers.splice(0, 0, {name: '__rowIdx__', text: '', width:50, defined : true});
        for (let i = 0; i < this.headers.length; i++) {
            let cur = this.headers[i];
            cur.__colIdx__ = i;
            if (cur.headerRender) {
                continue;
            }
            cur.headerRender = this._headerRender;
            proxyHeaders.push(new Proxy(cur, hander));
        }
        
        for (let i = 0; i < this.headers.length; i++) {
            let k = this.headers[i].name;
            let header = this.headers[i];

            if (k == 'hots' || k == 'zs' || k == 'zf') {
                header.defined = true;
            }
            if (k == 'hots' && !header.sortVal) {
                header.sortVal = function(rowData) {
                    return rowData.hots && rowData.hots > 0 ? 1000 - rowData.hots : 0
                }
            }
            if (! header.cellRender) {
                this.initCellRender(k, header);
            }
        }
        
        this.headers = proxyHeaders;
    }

    filter(text) {
        if (! this.srcDatas) {
            return;
        }
        for (let k in this.trs) {
            this.trs[k].hide();
        }
        let rs = this._searchText(text);
        this.datas = rs;
        for (let i = 0; i < rs.length; i++) {
            let d = rs[i];
            d.__rowIdx__ = i;
            this.trs[d.secu_code].show();
        }
    }

    _searchText(text) {
        let qs, cond, qrs = new Set();
        if (!text || !text.trim()) {
            return this.srcDatas.slice();
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
        let rs = [];
        for (let d of this.srcDatas) {
            if (this.match(d, qrs, cond))
                rs.push(d)
        }
        return rs;
    }

    match(data, qrs, cond) {
        for (let q of qrs) {
            let fd = false;
            for (let hd of this.headers) {
                let v = data[hd.name] || '';
                if (typeof(v) == 'string') {
                    if (hd.name == 'up_reason' && v.indexOf('|') > 0) 
                        v = v.substring(0, v.indexOf('|'));
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
    }

    initCellRender(k, header) {
        let thiz = this;
        if (k == '__rowIdx__') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                tdObj.text(rowData.__rowIdx__ + 1);
            }
        } else if (k == 'code') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                tdObj.append($('<span> <a href="https://www.cls.cn/stock?code=' + rowData.secu_code + '" target=_blank> <span style="color:#383838; font-weight:bold;" >' + 
                rowData.secu_name + '</span> </a> <br/> <span style="color:#666;font-size:12px;"> ' + rowData.code + '</span></span> '));
            }
        } else if (k == 'hots') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = '';
                if (rowData.hots) val =  String(rowData.hots) + '°'
                tdObj.text(val);
            }
        } else if (k == 'change') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                if (typeof(rowData.change) != 'number') {
                    tdObj.text('');
                    return;
                }
                let val = rowData.change;
                val = (val * 100).toFixed(1) + '%';
                if (rowData.change >= 0)
                    tdObj.css('color', '#de0422');
                else
                    tdObj.css('color', '#52C2A3');
                tdObj.text(val);
            }
        } else if (k == 'cmc') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = parseInt(rowData.cmc / 100000000) + '亿';
                tdObj.text(val);
            }
        } else if (k == 'fundflow') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = parseInt(rowData.fundflow / 10000) + '万';
                tdObj.text(val);
            }
        } else if (k == 'assoc_desc' || k == 'up_reason') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                tdObj.addClass('pl20');
                tdObj.attr('title', rowData[head.name]);
                tdObj.css('font-size', '12px');
                tdObj.html(thiz.buildUI_elipse(rowData[head.name]));
            }
        } else if (k == 'cls_ztReason' || (k == 'ths_ztReason')) {
            header.cellRender = function (idx, rowData, header, tdObj) {
                if (header.name.indexOf('cls') >= 0)
                    tdObj.addClass('cls-zt-reason');
                else
                    tdObj.addClass('ths-zt-reason');
                tdObj.text(rowData[header.name] || '');
            }
        } else if (k == 'fs') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                tdObj.addClass('fs');
                let view = thiz.createTimeLineView(rowData.secu_code, 300, 60);
                view.key = rowData.key;
                tdObj.append(view.canvas);
                view.addListener('LoadDataEnd', function(evt) {thiz.onLoadFsDataEnd(evt);});
            }
        } else if (k == 'zs') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = '';
                if (typeof(rowData.zs) == 'number' && rowData.zs) {
                    val = '↑&nbsp;' + rowData.zs.toFixed(1) ;
                }
                tdObj.html(val);
            }
        } else if ( k == 'zf') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                if (typeof(rowData.zf) != 'number') {
                    tdObj.text('');
                    return;
                }
                let val = rowData.zf.toFixed(1) + '%';
                if (rowData.zf >= 0)
                    tdObj.css('color', '#de0422');
                else
                    tdObj.css('color', '#52C2A3');
                tdObj.text(val);
            }
        } else if (k == 'limit_up_days') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                tdObj.text(String(rowData.limit_up_days) + '板');
            }
        } else if (k == 'head_num') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = rowData[head.name];
                tdObj.text(!val ? '' : String(val) + '次');
            }
        } else if (k == 'mark_color') {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = rowData[head.name];
                if (val) tdObj.append($(`<span style="width: 20px; height: 20px; display: inline-block; background-color:${val}; vertical-align: middle; "> </span>`));
            }
        } else {
            header.cellRender = function(rowIdx, rowData, head, tdObj) {
                let val = rowData[head.name];
                tdObj.text(val == undefined ? '' : val);
            }
        }
    }

    buildRowUI(idx, rowData) {
        let thiz = this;
        let tr = $('<tr style="vertical-align: middle;" code="' + rowData.secu_code + '"> </tr>');
        for (let i = 0; i < this.headers.length; i++) {
            let ff = this.headers[i].cellRender;
            let td = $('<td> </td>');
            tr.append(td);
            ff(idx, rowData, this.headers[i], td);
        }
        tr.dblclick(function() {thiz.openKLineDialog($(this).attr('code'))});
        tr.on('contextmenu', function(event) {
            event.preventDefault();
            const x = event.clientX;
            const y = event.clientY;
            thiz.onContextMenu(event, x, y);
            return false;
        });
        return tr;
    }

    onContextMenu(event, x, y) {
        let thiz = this;
        let tr = event.currentTarget;
        function onselect(evt) {
            thiz.onMenuItem(tr, evt);
        }
        if (! this.__menu__) {
            this.__menu__ = new PopupMenu();
        }
        this.__menu__.removeListener('select-item');
        this.__menu__.addListener('select-item', onselect);
        let menu = this.__menu__;
        let model = [
                    {title: '标记', sub: [
                        {name: 'mark-color', title: ' <span style="border:solid 1px #999; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: ''},
                        {name: 'mark-color', title: ' <span style="background-color: #f00; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: '#f00'}, 
                        {name: 'mark-color', title: ' <span style="background-color: #0f0; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: '#0f0'}, 
                        {name: 'mark-color', title: ' <span style="background-color: #00f; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: '#00f'}, 
                        {name: 'mark-color', title: ' <span style="background-color: #FF1493; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: '#FF1493'}, 
                        {name: 'mark-color', title: ' <span style="background-color: #9A32CD; width: 50px; height:15px; display: inline-block; vertical-align: middle;"> &nbsp; </span>', color: '#9A32CD'}, 
                    ]},
                ];
        menu.setModel(model);
        menu.show(x, y);
    }

    onMenuItem(tr, evt) {
        let code = tr.getAttribute('code');
        // console.log(code, evt);
        if (evt.item.name == 'add-my-sel-list') {
            this.addToMySelList(code);
        } else if (evt.item.name == 'mark-color') {
            this.markColor(code, evt.item.color);
        } 
    }

    addToMySelList(code) {
        const TAG = '[GP]:my-sel-list';
        let rs = this.getLocalObject(TAG) || [];
        for (let k of rs) {
            if (k.code == code)
                return;
        }
        let date = new Date();
        let y = date.getFullYear();
        let m = String(date.getMonth() + 1);
        let d = String(date.getDate());
        let day = `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
        rs.push({code, day});
        this.saveLocalObject(TAG, rs);
    }

    getLocalObject(key) {
        let rs = localStorage.getItem(key);
        if (! rs) return null;
        rs = JSON.parse(rs);
        return rs;
    }

    saveLocalObject(key, data) {
        if (! data) {
            localStorage.setItem(key, null);
        } else {
            localStorage.setItem(key, JSON.stringify(data));
        }
    }

    formatDay (date) {
        let y = date.getFullYear();
        let m = date.getMonth() + 1;
        let d = date.getDate();
        if (m < 10) m = '0' + m;
        if (d < 10) d = '0' + d;
        return y + '-' + m + '-' + d;
    }

    // color: null(取消) | rgb
    markColor(code, color) {
        const TAG = '[GP]:mark-color';
        let rs = this.getLocalObject(TAG) || [];
        let find = false;
        for (let i = 0; i < rs.length; i++) {
            let k = rs[i];
            if (k.code == code) {
                find = true;
                if (! color) rs.splice(i, 1);
                else k.color = color;
            }
        }
        if (! find) {
            rs.push({code, color, day: this.formatDay(new Date())});
        }
        this.saveLocalObject(TAG, rs);
        let ds = this.findInDatasMap(code);
        if (! ds) return;
        if (Array.isArray(ds)) {
            ds.forEach(function(it) {it.mark_color = color;});
        } else {
            ds.mark_color = color;
        }
    }

    loadMarkColors() {
        const TAG = '[GP]:mark-color';
        let rs = this.getLocalObject(TAG);
        if (! rs) return;
        let thiz = this;
        rs.forEach(function(it) {
            let color = it.color;
            let ds = thiz.findInDatasMap(it.code);
            if (! ds) return;
            if (Array.isArray(ds)) {
                ds.forEach(function(itx) {itx.mark_color = color;});
            } else {
                ds.mark_color = color;
            }
        });
    }

    findInDatasMap(code) {
        return this.datasMap[code];
    }

    buildUI() {
        if (! this.datas) {
            return;
        }
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            let tr = this.buildRowUI(i, sd);
            this.table.append(tr);
            this.trs[sd.key] = tr;
        }
    }

    getCodeList() {
        if (! this.datas)
            return [];
        let rs = [];
        for (let k of this.datas) {
            if (k.secu_code.length == 8)
                rs.push(k.secu_code.substring(2));
        }
        return rs;
    }

    openKLineDialog(code) {
        //console.log('[openKLineDialog]', code);
        if (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh') {
            code = code.substring(2);
        }
        let data = JSON.stringify({ codes: this.getCodeList(), day: this.day});
        $.post({
            url: 'http://localhost:5665/openui/kline/' + code,
            contentType: "application/json",
            data: data
        });
    }

    // header = header obj | header.name
    // by = null | undefined | 'asc' | 'desc'
    sortHeader(header, by) {
        if (typeof(header) == 'string') {
            for (let i in this.headers) {
                if (this.headers[i].name == header) {
                    header = this.headers[i];
                    break;
                }
            }
        }
        let old = this.lastSortHeader;
        if (! by) {
            if (! header.__sort__) by = 'desc';
            else by = header.__sort__ == 'asc' ? 'desc' : 'asc';
        }
        header.__sort__ = by;
        this.lastSortHeader = header;
        if (old && old != header) {
            delete old.__sort__;
        }
        this._sortBy(header.name, by == 'asc');
    }

    onLoadFsDataEnd(evt) {
        let view = evt.src;
        let maxZs = view.getMaxZs();
        let sd = this.datasMap[view.key];
        sd.zf = view.zf;
        sd.zs = maxZs ? maxZs.zf : 0;
    }

    getAttrType(list, name) {
        for (let i = 0; i < list.length; i++) {
            if (list[i][name] == undefined || list[i][name] == null)
                continue;
            return typeof(list[i][name]);
        }
        return 'undefined';
    }

    compare(list, name, asc) {
        let type = this.getAttrType(list, name);
        let get_val = function(a) {return a[name];}
        for (let i = 0; i < this.headers.length; i++) {
            if (this.headers[i].name == name && this.headers[i].sortVal) {
                get_val = this.headers[i].sortVal;
                break;
            }
        }
        if (type == "number") {
            return function(a, b) {
                let an = get_val(a) || 0;
                let bn = get_val(b) || 0;
                let v = an - bn; 
                return asc ? v : -v;
            };
        }
        if (type == "string") {
            return function(a, b) {
                let an = get_val(a) || '';
                let bn = get_val(b) || '';
                let v = an.localeCompare(bn); 
                return asc ? v : -v;
            };
        }
        return function(a, b) {return 0;};
    }

    _sortBy(name, asc) {
        //console.log('[sortNumberBy]', name, asc);
        if (!this.datas || !this.table) {
            return;
        }
        this.datas.sort(this.compare(this.datas, name, asc));
        this.srcDatas.sort(this.compare(this.srcDatas, name, asc));
        for (let k in this.trs) {
            this.trs[k].detach();
        }
        for (let i = 0; i < this.datas.length; i++) {
            let it = this.datas[i];
            it.__rowIdx__ = i;
            if (this.trs[it.key]) {
                this.table.append(this.trs[it.key]);
            }
        }
    }

    mergeCodesInfo(infos) {
        if (!infos|| !this.datasMap || !this.headers)
            return;
        for (let scode in this.datasMap) {
            let it = this.datasMap[scode];
            let hh = infos[scode];
            if (! hh) {
                it.hots = 0;
                continue;
            }
            for (let k in hh) {
                if (! it[k]) it[k] = hh[k];
            }
        }
    }

    loadCodesInfo() {
        let thiz = this;
        let day = this.day || ''
        let full = null;
        let cols = [];
        for (let i = 0; i < this.headers.length; i++) {
            if (this.headers[i].name == 'hots' && this.headers[i].defined) {
                cols.push('hots:' + day);
            }
            if (this.headers[i].name.indexOf('_ztReason') > 0 && this.headers[i].defined) {
                cols.push('ztReason');
            }
        }
        $.ajax({
            url: 'http://localhost:5665/query-codes-info',
            type: 'POST',
            contentType: "application/json",
            data: JSON.stringify({cols: cols, codes: this.getCodeList()}),
            success: function(resp) {
                thiz.mergeCodesInfo(resp);
            }
        });
    }

    buildUI_stdCode(code) {
        let tag = code.substring(0, 2);
        if (tag == 'sz' || tag == 'sh') {
            code = code.substring(2);
            if (code[0] == '0' || code[0] == '6' || code[0] == '3')
                return code;
            return null;
        }
        tag = code.substring(0, 3);
        if (tag == 'cls') {
            return code;
        }
        return null;
    }

    buildUI_hotsZH(row) {
        let val = row.hots ? row.hots : '';
        return '<td>' + val + '</td>';
    }

    buildUI_zf(row) {
        let val = row.change;
        val = (val * 100).toFixed(2);
        if (row.change >= 0)
            return '<td style="color:#de0422;">' + val + '%</td>';
        return '<td style="color:#52C2A3;">' + val + '%</td>';
    }

    buildUI_elipse(s) {
        if (s && s.length > this.config.elipseNum) {
            s = s.substring(0, this.config.elipseNum) + '...';
        }
        let idx = s.indexOf('|');
        if (idx > 0 && idx < 20) {
            s = '<span class="elipse" >' + s.substring(0, idx) + '</span> &nbsp;&nbsp;' + s.substring(idx + 1);
        }
        return s;
    }

    initStyle() {
        if (window['StockTable_style']) {
            return;
        }
        window['StockTable_style'] = true;
        let style = document.createElement('style');
        let css = ".my-stoks-table {color: #383838; font-size: 14px; border-collapse: collapse; border: 1px solid #ddd; text-align: center; } \n\
                   .my-stoks-table th {height: 30px; font-size:12px; color: #6A6B70; vertical-align: middle;font-weight: normal; border: 1px solid #ddd; background-color: #ECECEC; } \n\
                   .my-stoks-table tr:nth-child(even) { background-color: #f9fafc;} \n \
                   .my-stoks-table tr:hover {background-color: #ECEFF9;} \n\
                   .my-stoks-table td { vertical-align: middle; height: 66px; border: 1px solid #ddd;} \n\
                   .my-stoks-table .fs {padding: 3px 3px;} \n\
                   .my-stoks-table .pl20 {padding-right:20px;} \n\
                   .my-stoks-table .sel {background-color: #ECEFF9;}\n\
                   .my-stoks-table .elipse {color: #66B2FF; }\n\
                   .my-stoks-table .cls-zt-reason {color: #6495ED; font-size: 12px;}\n\
                   .my-stoks-table .ths-zt-reason {color: #5CACEE; font-size: 12px;}\n\
                   .my-stoks-table .industry {background-color: #8C92A6; height: 26px; vertical-align: middle; color: #fff; }\n\
                   .my-stoks-table .industry:before {content:'\\20'; width: 6px; height:16px; background-color: #8d1f1f; margin: 0 5px 0 10px; display: inline-block; vertical-align: middle;} \n\
                ";
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
    }
}

class IndustryTable extends StockTable {
    constructor(headers) {
        super(headers);
    }

    setData(data) {
        if (data == this.datas || !data) {
            return;
        }
        let mdata = {};
        for (let k = 0; k < data.length; k++) {
            let items = data[k].stocks;
            let industry = data[k].industry_name;
            for (let i = items.length - 1; i >= 0; i--) {
                let code = this.buildUI_stdCode(items[i].secu_code);
                if (! code) {
                    items.splice(i, 1);
                } else {
                    let key = items[i].secu_code + ':' + industry;
                    items[i].code = code;
                    items[i].key = key;
                    mdata[key] = items[i];
                }
            }
            for (let i = 0; i < items.length; i++) {
                items[i].__rowIdx__ = i;
            }
        }
        this.datas = data;
        this.datasMap = mdata;
        this._defineProterties()
        this.loadCodesInfo();
    }

    buildUI() {
        if (! this.datas) {
            return;
        }
        let thiz = this;
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            let ftr = $('<tr> <td colspan="' + this.headers.length + '" class="industry" style="text-align:left;"> ' + sd.industry_name + '&nbsp;&nbsp;' + sd.stocks.length + ' </td> </tr>');
            this.table.append(ftr);
            this.trs[sd.industry_name] = ftr;
            
            for (let j = 0; j < sd.stocks.length; j++) {
                let sdx = sd.stocks[j];
                let tr = this.buildRowUI(j, sdx);
                this.table.append(tr);
                this.trs[sdx.key] = tr;
            }
        }
    }

    _sortBy(name, asc) {
        //console.log('[sortNumberBy]', name, asc);
        if (!this.datas || !this.table) {
            return;
        }
        for (let i = 0; i < this.datas.length; i++) {
            this.datas[i].stocks.sort(this.compare(this.datas[i].stocks, name, asc));
        }
        for (let k in this.trs) {
            this.trs[k].detach();
        }
        
        for (let i = 0; i < this.datas.length; i++) {
            let ids = this.datas[i];
            this.table.append(this.trs[ids.industry_name]);
            for (let j = 0; j < ids.stocks.length; j++) {
                let it = ids.stocks[j];
                let tr = this.trs[it.key];
                if (! tr)
                    continue
                it.__rowIdx__ = j;
                this.table.append(tr);
            }
        }
    }

    findInDatasMap(code) {
        let rs = [];
        for (let k in this.datasMap) {
            if (k.indexOf(code) >= 0) rs.push(this.datasMap[k]);
        }
        return rs;
    }
}

class UIListener {
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

    removeListener(eventName) {
        delete this.listeners[eventName];
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

class TradeDatePicker extends UIListener {
    constructor() {
        super();
        this.table = null;
        this.curSelDate = null; // String YYYY-mm-dd
        this.popup = null;
        this.tradeDays = {};
        this.changeInfo = {};
        this.loadTradeDays();
    }

    openFor(targetElem) {
        this.reset();
        if (! targetElem.tagName) targetElem = targetElem.get(0);
        let tdRc = targetElem.getBoundingClientRect();
        let dw = $(window.document).width();
        if (dw < tdRc.left + this.table.width()) {
            this.table.css({left: dw - this.table.width() - 10, top: tdRc.bottom});
        } else {
            this.table.css({left: tdRc.left, top: tdRc.bottom});
        }
	    this.popup.css('display', 'block');
    }

    loadTradeDays() {
        let thiz = this;
        $.ajax({url: 'http://localhost:5665/get-trade-days', async: false, success: function(data) {
            for (let d of data) {
                if (d.length == 8) {
                    d = d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
                }
                thiz.tradeDays[d] = true;
            }
        }});
    }

    reset() {
        let d = this.curSelDate || new Date();
        if (typeof(d) == 'string')
            d = new Date(d);
        let y = d.getFullYear();
        let m = d.getMonth() + 1;
        this.changeMonth(y, m);
    }

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
        this.buildUI(ds);
    }

    formatDate(date) {
        if (! date) {
            return '';
        }
        if (typeof(date) == 'string') {
            if (date.length == 8) {
                return date.substring(0, 4) + '-' + date.substring(4, 6) + '-' + date.substring(6, 8);
            }
        }
        let y = date.getFullYear();
        let m = String(date.getMonth() + 1);
        let d = String(date.getDate());
        return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

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
    }

    getWeek(date) {
        let sweek = (date.getDay() + 6) % 7; // 0 ~ 6, 一 ~ 日
        return sweek;
    }

    buildUI(days) {
        this.initStyle();
        this.table.empty();
        let tr = $('<tr> </tr>');
        let ym = `${this.changeInfo.year}-${this.changeInfo.month}`;
        let today = this.formatDate(new Date());
        tr.append($(`<td colspan=5> ${ym} </td> <td val="prev" able=true> &lt; </td> <td val="next" able=true> &gt; </td> `));
        this.table.append(tr);
        tr = $('<tr> </tr>');
        for (let k of '一二三四五六日') {
            tr.append($(`<th> ${k} </th>`));
        }
        this.table.append(tr);
        tr = null;
        for (let i = 0; i < days.length; i++) {
            if (i % 7 == 0) {
                tr = $('<tr> </tr>');
                this.table.append(tr);
            }
            let sday = this.formatDate(days[i]);
            let td = $(`<td val=${sday}> ${sday ? parseInt(sday.substring(8)) : ''} </td>`);
            let able = this.tradeDays[sday];
            td.attr('able', able);
            if (! able) td.addClass('no-able');
            if (sday == today) td.html(`<span class="today"> ${td.text()} </span>`);
            if (sday == this.curSelDate) td.addClass('sel');
            tr.append(td);
        }
        let thiz = this;
        this.table.find('td').click(function() { thiz.onSel($(this)); return false;});
    }
    
    onSel(elem) {
        let val = elem.attr('val');
        if (! elem.attr('able'))
            return;
        if (val.length == 10) {
            this.curSelDate = val;
            this.popup.css('display', 'none');
            this.notify({name: 'select', date: this.curSelDate});
        } else if (val == 'prev' || val == 'next') {
            let v = val == 'prev' ? -1 : 1;
            this.changeMonth(this.changeInfo.year, this.changeInfo.month + v);
        }
    }

    initStyle() {
        if (window['DatePicker-InitStyle'])
            return;
        window['DatePicker-InitStyle'] = true;
        let style = document.createElement('style');
        let css = " \
            .datepicker-popup {z-index: 81100; display: none;  position: fixed; padding: 0; outline: 0; left:0px; top: 0px;width:100%;height:100%;}\n\
            .datepicker-popup tr {width: 300px; height: 25px;} \n\
            .datepicker-popup table {position:absolute; color: #383838; font-size: 14px; border-collapse: collapse; border: 1px solid #aaa; text-align: center; background-color: #fcfcfc; } \n\
            .datepicker-popup th {width: 30px; height: 30px; border: solid 1px #ddd; background-color:#ECECEC;vertical-align: middle;} \n\
            .datepicker-popup td {height: 30px; border: solid 1px #ddd;vertical-align: middle;} \n\
            .datepicker-popup .no-able {background-color:#f0f0f0; } \n\
            .datepicker-popup .today {color: #0a0; } \n\
            .datepicker-popup .sel {background-color: #FF66FF; } \n\
        ";
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
        this.popup = $('<div class="datepicker-popup" > </div>');
        this.popup.click(function() {$(this).css('display', 'none')});
        this.popup.on('mousewheel', function(event) {event.preventDefault(); return false;});
        $(document.body).append(this.popup);
        this.table = $('<table> </table>');
        this.popup.append(this.table);
        this.table.click(function() {return false;});
    }
}

class PopupMenu extends UIListener {
    constructor() {
        super();
        this.menus = []; // menu manager list
        this.popup = null;
        this.menu = null;
        this.model = null;
        this.config = {maxVisibleItemNum: 10};
    }

    // model = [{title: string, name?: string, style?: string, sub?: model}, ...]
    // model-item = null, means split line
    setModel(model) {
        this.menus.length = 0;
        this.model = model;
        if (this.popup) this.popup.empty();
        this.initStyle();
        this.menu = this._buildMenu(this.model, 0);
    }

    show(x, y) {
        this.popup.append(this.menu);
        this.menu.css({left: String(x) + 'px', top: String(y) + 'px'});
        this.menu.show();
        this.popup.show();
    }

    hide() {
        if (this.popup) {
            this.popup.empty();
            this.popup.hide();
        }
    }

    _closeMenuLevel(level) {
        for (let i = this.menus.length - 1; i >= 0;  --i) {
            let cur = this.menus[i];
            if (cur.data('level') >= level) {
                cur.hide();
                this.menus.splice(i, 1);
            }
        }
    }

    _buildMenu(model, level) {
        let thiz = this;
        let menu = $('<div class="menu"> </div>');
        menu.data('level', level);
        menu.css('max-height', `${this.config.maxVisibleItemNum * 25 + 20}px`);
        menu.click(function() {return false;});
        let m = 0;
        menu.on('mousewheel', function(event) {
            let dy = event.originalEvent.deltaY;
            let curElem = event.originalEvent.currentTarget;
            let cntHeight = curElem.scrollHeight;
            let h = $(curElem).height();
            let moveableH = cntHeight - h;
            if (dy > 0) {
                let mmy = moveableH - curElem.scrollTop;
                dy = Math.min(mmy, dy);
                curElem.scrollTo(0, curElem.scrollTop + dy);
            } else {
                let mmy = curElem.scrollTop;
                dy = Math.min(mmy, -dy);
                curElem.scrollTo(0, curElem.scrollTop - dy);
            }
            return false;
        });
        menu.hide();
        this.popup.append(menu);
        for (let k of model) {
            if (! k) {
                menu.append($('<hr style="padding: 0; margin: 0;"/>'));
                continue;
            }
            let item = $(`<p class="menu-item"> <span class="menu-item-prefix"> </span> ${k.title} <span class="menu-item-suffix"> ${k.sub && k.sub.length ? ">" : ""} </span> </p>`);
            item.data('__model__', k);
            menu.append(item);
            item.click(function(evt) {let mi = $(this).data('__model__');  thiz.hide(); thiz.notify({name: 'select-item', item: mi, menu: thiz});});
            if (k.style) {
                k.style.split(';').forEach(function(it) {let s = it.split(':'); item.css[s[0].trim()] = s[1];});
            }
            
            item.on('mouseenter', function() {
                let it = $(this);
                let itModel = it.data('__model__');
                if (!k.sub || !k.sub.length) {
                    thiz._closeMenuLevel(level + 1);
                    return;
                }
                if (! itModel.__submenu__) {
                    itModel.__submenu__ = thiz._buildMenu(itModel.sub, level + 1);
                    thiz.popup.append(itModel.__submenu__);
                }
                let bb = it.get(0).getBoundingClientRect();
                itModel.__submenu__.css({left: bb.right, top: bb.top});
                thiz._closeMenuLevel(itModel.__submenu__.data('level'));
                thiz.menus.push(itModel.__submenu__);
                itModel.__submenu__.show();
            });
            item.on('mouseleave', function(event) {
                let it = $(this);
                let itModel = it.data('__model__');
                if (! itModel.__submenu__) return;
                if (! itModel.__submenu__.is(':visible')) return;
                let bb = itModel.__submenu__.get(0).getBoundingClientRect();
                let isIn = event.clientX >= bb.left && event.clientX <= bb.right && event.clientY >= bb.top && event.clientY <= bb.bottom;
                if (! isIn) itModel.__submenu__.hide();
            });
        }
        return menu;
    }

    initStyle() {
        if (window['PopupMenu-InitStyle']) {
            if (! this.popup )
                this.popup = $('.popupmenu-popup');
            return;
        }
        window['PopupMenu-InitStyle'] = true;
        let style = document.createElement('style');
        let css = " \
            .popupmenu-popup {z-index: 99900; display: none;  position: fixed; padding: 0; outline: 0; left:0px; top: 0px;width:100%;height:100%;}\n\
            .popupmenu-popup .menu {position:absolute; color: #383838; font-size: 14px; border: 1px solid #888; padding: 10px 0;  \n\
                background-color:#fcfcfc;vertical-align: middle; overflow-x: hidden; overflow-y: scroll;-ms-overflow-style: none; } \n\
            .popupmenu-popup .menu::-webkit-scrollbar {display: none;} \n\
            .popupmenu-popup .menu-item {min-width: 100px; min-height: 25px; display: block; vertical-align: middle; user-select: none; -webkit-user-select: none;} \n\
            .popupmenu-popup .menu-item-prefix {width: 30px; height: 25px; float: left;} \n\
            .popupmenu-popup .menu-item-suffix {width: 30px; height: 25px; float:right; margin-left: 10px; text-align:center;} \n\
            .popupmenu-popup .menu-item:hover {background-color:#ECECEC;} \n\
            .popupmenu-popup .menu-item-updown {min-width: 100px; height: 15px; display: block; vertical-align: middle; user-select: none; -webkit-user-select: none;} \n\
        ";
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
        this.popup = $('<div class="popupmenu-popup" > </div>');
        this.popup.click(function() {$(this).css('display', 'none'); $(this).empty();});
        this.popup.on('mousewheel', function(event) { return false;}); //  event.stopPropagation();event.preventDefault();
        $(document.body).append(this.popup); 
    }

}

class RichEditor extends UIListener {
    constructor(name) {
        super();
        this.name = name;
        this.ui = null;
    }

    buildUI() {
        this.initStyle();
        if (this.ui) {
            this.loadData();
            return;
        }
        this.ui = $('<div class="richeditor" contenteditable="true" > </div>');
        let thiz = this;
        this.ui.keydown(function(evt) {return thiz.onKeyDown(evt);});
        this.ui.on('contextmenu', function(event) {
            event.preventDefault();
            const x = event.clientX;
            const y = event.clientY;
            thiz.onContextMenu(x, y);
            return false;
        });
        this.loadData();
    }

    onContextMenu(x, y) {
        let thiz = this;
        let menu = this.__menu__ = new PopupMenu();
        const onselect = function(evt) {
            thiz.onMenuItem(evt);
        }
        menu.addListener('select-item', onselect);
        const makeColorItem = function(name, color) {
            if (! color)
                return {name: name, title: ' <span style="border:solid 1px #999; width: 50px; height:15px; display: inline-block; vertical-align: middle;">  </span>', value: ''};
            return {name: name, title: ` <span style="background-color: ${color};width: 50px; height:15px; display: inline-block; vertical-align: middle;">  </span>`, value: color};
        }
        const makeColorItems = function(name, colors) {
            let rs = [];
            if (typeof(colors) == 'string') {
                colors = colors.split(';');
            }
            for (let c of colors) {
                rs.push(makeColorItem(name, c.trim()));
            }
            return rs;
        }
        const simpleItems = function(name, vals) {
            let rs = [];
            vals.split(';').forEach(function(item) {
                let ss = item.split(':');
                let m = {name: name, title: ss[0].trim()};
                if (ss.length == 1) m.value = ss[0].trim();
                else  m.value = ss[1].trim();
                rs.push(m);
            });
            return rs;

        }
        let colors = ' ;#DCDCDC; #FFDEAD; #2F4F4F; #696969; #000080; #6A5ACD; #00CED1; #006400; #556B2F; #CD5C5C; #CD853F; #FF1493; #9932CC;  #FF7F00; #8B008B';
        let model = [{ title: '前景色', sub: makeColorItems('setColor', colors)},
                    {title: '背景色', sub: makeColorItems('setBgColor', colors)},
                    {title: '字体', sub: [{name: 'bold', title: '粗体'}, {name: 'italic', title: '斜体'},
                        {name: 'strikeThrough', title: '删除线'}, {name: 'underline', title: '下划线'},
                        {name: 'superScript', title: '上标'}, {name: 'subScript', title: '下标'}]},
                    {title: '字体大小', sub: simpleItems('setFontSize', '小-x:1;  小:2;  中:3;   大:4;   大-x:5;   大-xx:6;   大-xxx:7')},
                    {title: '对齐', sub: simpleItems('textAlign', '左对齐:left; 居中对齐:center; 右对齐:right; 两端齐:full')},
                    null,
                    {title: '插入/删除', sub: [{name: 'insertHorizontalRule', title: '插入水平线'},
                        {name: 'insertHtml', title: '插入Html', input: true},
                        {name: 'insertText', title: '插入Text', input: true},
                        {name: 'createLink', title: '插入Link', input: true},
                        {name: 'unlink', title: '删除Link'},]},
                    null,
                    {name: 'removeFormat', title: '清除格式'},
                    {name: 'redo', title: '重做'},
                    {name: 'undo', title: '撤消'},
                    null,
                    {name: 'save', title: '保存'},
                ];
        menu.setModel(model);
        menu.show(x, y);
    }

    onMenuItem(evt) {
        let name = evt.item.name;
        if (! name) return;
        let func = this[name];
        if (evt.item.input) {
            let val = prompt(evt.item.title);
            func.call(this, val);
        } else if (evt.item.value) {
            func.call(this, evt.item.value);
        } else {
            func.call(this);
        }
    }

    loadData() {
        this.ui.html(localStorage.getItem(this.name));
    }

    onKeyDown(event) {
        // console.log(event);
        if (event.keyCode == 83 && event.ctrlKey) {
            // ctrl + S
            this.save();
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
    }

    initStyle() {
        if (window['RichEditor-InitStyle'])
            return;
        window['RichEditor-InitStyle'] = true;
        let style = document.createElement('style');
        let css = " \
            .richeditor  {border:solid 1px #aaa; min-height: 400px; padding: 10px; } \n\
        ";
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
    }

    setBgColor(color) { // 修改文档的背景颜色
        document.execCommand('backColor', false, color); 
    }
    setBgColor2(color) { // 更改选择或插入点的背景颜色
        document.execCommand('hiliteColor', false, color);
    }
    bold() { // 开启或关闭
        document.execCommand('bold');
    }
    italic() { // 在光标插入点开启或关闭斜体字
        document.execCommand('italic');
    }
    setFontName(fontName) { // 在插入点或者选中文字部分修改字体名称
        document.execCommand('fontName', false, fontName);
    }
    // fontSize = 1 ~ 7
    setFontSize(fontSize) {
        document.execCommand('fontSize', false, fontSize);
    }
    setColor(foreColor) { // 在插入点或者选中文字部分修改字体颜色。
        document.execCommand('foreColor', false, foreColor);
    }
    insertHorizontalRule() { // 在插入点插入一个水平线（删除选中的部分）
        document.execCommand('insertHorizontalRule');
    }
    insertHtml(html) { // 在插入点插入一个 HTML 字符串（删除选中的部分）
        document.execCommand('insertHtml', false, html);
    }
    insertText(text) { // 在插入点插入一个 Text 字符串（删除选中的部分）
        document.execCommand('insertText', false, text);
    }
    insertImage(url) { // 在插入点插入一张图片（删除选中的部分）
        document.execCommand('insertImage', false, url);
    }
    enableObjectResizing() { // 启用或禁用图像和其他对象的大小可调整大小手柄。
        document.execCommand('enableObjectResizing');
    }
    createLink(url) { // 将选中内容创建为一个锚链接
        document.execCommand('createLink', false, url || ' ');
    }
    unlink() { // 去除所选的锚链接的<a>标签
        document.execCommand('unlink');
    }
    // align: center, full, left, right
    textAlign(align) { // 对光标插入位置或者所选内容进行文字对齐
        align = align.toLowerCase();
        let first = align.substring(0, 1).toUpperCase();
        let cmd = 'justify' + first + align.substring(1);
        document.execCommand(cmd);
    }
    redo() { // 重做被撤销的操作。
        document.execCommand('redo');
    }
    undo() { // 撤销最近执行的命令。
        document.execCommand('undo');
    }
    removeFormat() { // 对所选内容去除所有格式
        document.execCommand('removeFormat');
    }
    strikeThrough() { // 在光标插入点开启或关闭删除线。
        document.execCommand('strikeThrough');
    }
    underline() { // 在光标插入点开启或关闭下划线。
        document.execCommand('underline');
    }
    subScript() { // 在光标插入点开启或关闭下角标。
        document.execCommand('subscript');
    }
    superScript() { // 在光标插入点开启或关闭上角标。
        document.execCommand('superscript');
    }
    formatBlock(tagName) { // 添加一个 HTML 块式标签在包含当前选择的"行"
        document.execCommand('formatBlock', false, tagName);
    }
    useCss(flag) {
        document.execCommand('styleWithCSS', false, flag);
    }
    save() {
        localStorage.setItem(this.name, this.ui.html());
    }

}