/**
 *   st = new StockTable(headers);
 *   st.initStyle(); 
 *   st.buildUI();
 */
class StockTable {
    // headers = [ {text: 'xxx', name: 'xx', width: 60, sortable: true,
    //              sortVal?: function(rowData), defined? : true,
    //              formater?: function(rowIdx, rowData, header, tdObj) }, ...]
    // fix headers : 'zs' 涨速, 'hots': 热度  'zf': 涨幅(根据'fs'列自动生成)
    // 必须有列：secu_code(如果有code, 会根据code自动生成), secu_name
    // {name: 'hots', full? : true}
    constructor(headers) {
        this.headers = headers;
        this.lastSortHeader = null;
        this.datas = null;
        this.datasMap = null; // map of this.datas, key = secu_code
        this.hotsZH = null;
        this.day = null;

        this.table = null;
        this.headersTr = null;
        this.trs = {};
        this.tlMgr = new TimeLineUIManager();
        this.config = {elipseNum: 40};
        this.init()
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
        view.loadData(code);
        return view;
    }

    _updateAttrUI(rowData, header, val) {
        let key = rowData.key;
        if (! this.trs[key])
            return;
        let td = this.trs[key].find('td:nth-child(' + (header.__colIdx__ + 1) + ')');
        td.empty();
        header.formater(rowData.__rowIdx__, rowData, header, td);
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
        if (data == this.datas || !data) {
            return;
        }
        let mdata = {};
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
        this.datas = data;
        this.datasMap = mdata;
        this._defineProterties()
        this.loadHotsZH();
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
            hd.headerFormater(i, hd, th);
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

    initHeadersDefault() {
        if (! this.headers) 
            return;
        let proxyHeaders = [];
        let thiz = this;
        function updateAttr(target, attr, op) {
            let th = thiz.headersTr.find('th:nth-child(' + (target.__colIdx__ + 1) +')');
            th.empty()
            if (op == 'del') th.removeAttr(attr);
            target.headerFormater(target.__colIdx__, target, th);
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
            if (cur.headerFormater) {
                continue;
            }
            cur.headerFormater = function(colIdx, header, thObj) {
                for (let k in header) {
                    if (typeof(header[k]) != 'function')
                        thObj.attr(k, header[k]);
                }
                let txt = header.text;
                if (header.__sort__ == 'asc') {
                    txt += '&nbsp;&#8593;';
                } else if (header.__sort__ == 'desc') {
                    txt += '&nbsp;&#8595;';
                }  else if (header.sortable) {
                    txt += '&#9830;';
                }
                thObj.html(txt);
            }
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
            if (! header.formater) {
                this.initFormaterDefault(k, header);
            }
        }
        
        this.headers = proxyHeaders;
    }

    initFormaterDefault(k, header) {
        let thiz = this;
        if (k == '__rowIdx__') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                tdObj.text(rowData.__rowIdx__ + 1);
            }
        } else if (k == 'code') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                tdObj.append($('<span> <a href="https://www.cls.cn/stock?code=' + rowData.secu_code + '" target=_blank> <span style="color:#383838; font-weight:bold;" >' + 
                rowData.secu_name + '</span> </a> <br/> <span style="color:#666;font-size:12px;"> ' + rowData.code + '</span></span> '));
            }
        } else if (k == 'hots') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                let val = '';
                if (rowData.hots) val =  String(rowData.hots) + '°'
                tdObj.text(val);
            }
        } else if (k == 'change') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
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
            header.formater = function(rowIdx, rowData, head, tdObj) {
                let val = parseInt(rowData.cmc / 100000000) + '亿';
                tdObj.text(val);
            }
        } else if (k == 'fundflow') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                let val = parseInt(rowData.fundflow / 10000) + '万';
                tdObj.text(val);
            }
        } else if (k == 'assoc_desc' || k == 'up_reason') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                tdObj.addClass('pl20');
                tdObj.attr('title', rowData[head.name]);
                tdObj.css('font-size', '12px');
                tdObj.html(thiz.buildUI_elipse(rowData[head.name]));
            }
        } else if (k == 'fs') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                tdObj.addClass('fs');
                let view = thiz.createTimeLineView(rowData.secu_code, 300, 60);
                view.key = rowData.key;
                tdObj.append(view.canvas);
                view.addListener('LoadDataEnd', function(evt) {thiz.onLoadFsDataEnd(evt);});
            }
        } else if (k == 'zs') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                let val = '';
                if (typeof(rowData.zs) == 'number' && rowData.zs) {
                    val = '↑&nbsp;' + rowData.zs.toFixed(1) ;
                }
                tdObj.html(val);
            }
        } else if ( k == 'zf') {
            header.formater = function(rowIdx, rowData, head, tdObj) {
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
        } else {
            header.formater = function(rowIdx, rowData, head, tdObj) {
                let val = rowData[head.name];
                tdObj.text(val == undefined ? '' : val);
            }
        }
    }

    buildRowUI(idx, rowData) {
        let tr = $('<tr style="vertical-align: middle;" code="' + rowData.secu_code + '"> </tr>');
        for (let i = 0; i < this.headers.length; i++) {
            let ff = this.headers[i].formater;
            let td = $('<td> </td>');
            tr.append(td);
            ff(idx, rowData, this.headers[i], td);
        }
        return tr;
    }

    buildUI() {
        if (! this.datas) {
            return;
        }
        let thiz = this;
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            let tr = this.buildRowUI(i, sd);
            this.table.append(tr);
            tr.dblclick(function() {thiz.openKLineDialog($(this).attr('code'))});
            this.trs[sd.key] = tr;
        }
    }

    openKLineDialog(code) {
        //console.log('[openKLineDialog]', code);
        if (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh') {
            code = code.substring(2);
        }
        let params = '';
        if (this.day) {
            params = '?day=' + this.day;
        }
        $.get('http://localhost:5665/openui/kline/' + code + params);
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
        this.sortBy(header.name, by == 'asc');
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
            if (list[i][name] == undefined)
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

    sortBy(name, asc) {
        //console.log('[sortNumberBy]', name, asc);
        if (!this.datas || !this.table) {
            return;
        }
        this.datas.sort(this.compare(this.datas, name, asc));
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

    mergeHotsZH() {
        if (!this.hotsZH || !this.datasMap || !this.headers)
            return;
        for (let scode in this.datasMap) {
            let it = this.datasMap[scode];
            let hh = this.hotsZH[it.code];
            if (! hh) {
                it.hots = 0;
                continue;
            }
            it.hots = hh.zhHotOrder;
            for (let k in hh) {
                it[k] = hh[k];
            }
        }
    }

    loadHotsZH() {
        let thiz = this;
        let day = this.day || ''
        let full = null;
        for (let i = 0; i < this.headers.length; i++) {
            if (this.headers[i].name == 'hots') {
                full = this.headers[i].full;
                break;
            }
        }
        full = full ? '&full=true' : ''
        $.ajax({
            url: 'http://localhost:5665/get-hots?day=' + day + full, type: 'GET',
            success: function(resp) {
                thiz.hotsZH = resp;
                thiz.mergeHotsZH();
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
        this.loadHotsZH();
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
                tr.dblclick(function() {thiz.openKLineDialog($(this).attr('code'))});
                this.trs[sdx.key] = tr;
            }
        }
    }

    sortBy(name, asc) {
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
}