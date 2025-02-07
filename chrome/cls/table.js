/**
 *   st = new StockTable(headers);
 *   st.initStyle(); 
 *   st.buildUI();
 */
class StockTable {
    // headers = [ {text: 'xxx', name: 'xx', width: 60, sortable: true, sortVal: function(rowData) }, ...]
    // fix headers : 'zs' 涨速, 'hots': 热度
    constructor(headers) {
        this.headers = headers;
        this.lastSortHeader = null;
        this.datas = null;
        this.datasMap = null;
        this.hotsZH = null;
        this.table = null;
        this.trs = {};
        this.tlMgr = new TimeLineUIManager();
        this.config = {elipseNum: 40};
    }

    createTimeLineView(code, width, height) {
        width = width || 300;
        height = height || 60;
        let view = new TimeLineView(width, height);
        this.tlMgr.add(view);
        view.loadData(code);
        return view;
    }

    setData(data) {
        if (data == this.datas || !data) {
            return;
        }
        let mdata = {};
        for (let i = data.length - 1; i >= 0; i--) {
            let code = this.buildUI_stdCode(data[i].secu_code);
            if (! code) {
                data.splice(i, 1);
            } else {
                data[i].code = code;
                mdata[data[i].secu_code] = data[i];
            }
        }
        this.datas = data;
        this.datasMap = mdata;
        this.loadHotsZH();
    }

    buildHeadersUI() {
        let tr = $('<tr style="vertical-align: middle;"> </tr>');
        tr.append($('<th width=50> </th>')); // row no column
        for (let i = 0; i < this.headers.length; i++) {
            let cur = this.headers[i];
            let hd = $('<th> ' + cur.text + ' </th>');
            for (let k in cur) {
                hd.attr(k, cur[k]);
            }
            tr.append(hd);
        }
        let tds = tr.find('th[sortable]');
        let thiz = this;
        for (let i = 0; i < tds.length; i++) {
            let td = tds.eq(i);
            td.append('&#9830;');
            td.click(function() {
                thiz.onSortHead($(this));
            });
        }
        return tr;
    }

    buildRowUI(idx, rowData) {
        let tr = $('<tr style="vertical-align: middle;" code="' + rowData.secu_code + '"> </tr>');
        tr.append($('<td style="text-align:center;">' + (idx + 1) + ' </td> '));
        for (let i = 0; i < this.headers.length; i++) {
            let hd = '';
            let k = this.headers[i].name;
            if (k == 'code') {
                hd = $('<td> <a href="https://www.cls.cn/stock?code=' + rowData.secu_code + '" target=_blank> <span style="color:#383838; font-weight:bold;" >' + 
                rowData.secu_name + '</span> </a> <br/> <span style="color:#666;font-size:12px;"> ' + rowData.code + '</span></td> ');
            } else if (k == 'hots') {
                hd = $(this.buildUI_hotsZH(rowData));
            } else if (k == 'change') {
                hd = $(this.buildUI_zf(rowData));
            } else if (k == 'cmc') {
                hd = $('<td>' + parseInt(rowData.cmc / 100000000) + '亿 </td>');
            } else if (k == 'fundflow') {
                hd = $('<td>' + parseInt(rowData.fundflow / 10000) + '万 </td>');
            } else if (k == 'assoc_desc' || k == 'up_reason') {
                hd = $('<td class="pl20" title="' + rowData[k] + '" style="font-size:12px;">' + this.buildUI_elipse(rowData[k]) + '</td>');
            } else if (k == 'fs') {
                hd = $('<td class="fs" > </td>');
                let view = this.createTimeLineView(rowData.secu_code, 300, 60);
                view.key = rowData.key;
                hd.append(view.canvas);
                let thiz = this;
                view.addListener('LoadDataEnd', function(evt) {thiz.onLoadFsDataEnd(evt);});
            } else if (k == 'zs') {
                let v = !rowData['zs'] ? '' : rowData['zs'];
                hd = $('<td class="zs" > ' + v + ' </td>');
            } else {
                let d = rowData[k];
                hd = $('<td> ' + (d == undefined ? '' : d) + ' </td>');
            }
            tr.append(hd);
        }
        return tr;
    }

    buildUI() {
        if (! this.datas || !this.headers) {
            return;
        }
        let tab = $('<table class="my-stoks-table" > </table>');
        let hds = this.buildHeadersUI(); //  <th width=300>简介</th> <th width=300 >分时图</th> </tr>');
        tab.append(hds);
        let thiz = this;
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            sd.key = sd.secu_code;
            let tr = this.buildRowUI(i, sd);
            tab.append(tr);
            tr.dblclick(function() {thiz.openKLineDialog($(this).attr('code'))});
            //tr.click(function() {if (selTr) selTr.removeClass('sel'); selTr = $(this); selTr.addClass('sel'); });
            this.trs[sd.key] = tr;
        }
        this.table = tab;
        return tab;
    }

    openKLineDialog(code) {
        //console.log('[openKLineDialog]', code);
        if (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh') {
            code = code.substring(2);
        }
        $.get('http://localhost:5665/openui/kline/' + code);
    }

    onSortHead(td) {
        //console.log('[onSortHead]', td);
        let old = this.lastSortHeader;
        //let td = $(this);
        let v = td.attr('sv');
        let tag = '';
        if (!v || v == 'asc') {
            v = 'desc';
            tag = '&nbsp;&#8595;';
        } else {
            v = 'asc';
            tag = '&nbsp;&#8593;';
        }
        td.attr('sv', v);
        this.lastSortHeader = td;
        if (old != this.lastSortHeader && old) {
            old.html(old.attr('text') + '&#9830;');
            old.attr('sv', '');
        }
        td.html(td.attr('text') + tag);
        this.sortBy(td.attr('name'), v == 'asc');
    }

    onLoadFsDataEnd(evt) {
        let view = evt.src;
        let maxZs = view.getMaxZs();
        let sd = this.datasMap[view.key];
        if (! maxZs) {
            sd.zs = 0;
            return;
        }
        let zf = maxZs.zf;
        let td = $(view.canvas).parent().parent().find('td.zs');
        sd.zs = zf;
        td.text('' + zf.toFixed(1) + '%');
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
        let no = 1;
        for (let i = 0; i < this.datas.length; i++) {
            let code = this.datas[i].secu_code;
            if (this.trs[code]) {
                this.table.append(this.trs[code]);
                this.trs[code].find('td:first').text(String(no ++));
            }
        }
    }

    mergeHotsZH() {
        if (!this.hotsZH || !this.datasMap || !this.headers)
            return;
        let hotIdx = -1;
        for (let i = 0; i < this.headers.length; i++) {
            if (this.headers[i].name == 'hots') {
                hotIdx = i;
            }
        }
        if (hotIdx < 0)
            return;
        if (! this.headers[hotIdx].sortVal) {
            this.headers[hotIdx].sortVal = function(rowData) {
                return rowData.hots > 0 ? 1000 - rowData.hots : 0
            }
        }
        hotIdx += 1; // first is row no
        for (let scode in this.datasMap) {
            let it = this.datasMap[scode];
            let hots = this.hotsZH[it.code] ? this.hotsZH[it.code].zhHotOrder : 0;
            it.hots = hots;
            //it.sortHots = hots > 0 ? 1000 - hots : 0;
            if (hots > 0 && this.trs[it.key]) {
                this.trs[it.key].find('td:nth-child(' + (hotIdx + 1) + ')').text(hots);
            }
        }
    }

    loadHotsZH() {
        let thiz = this;
        $.ajax({
            url: 'http://localhost:5665/get-hots', type: 'GET',
            success: function(resp) {
                thiz.hotsZH = resp;
                thiz.mergeHotsZH();
            }
        });
    }

    buildUI_stdCode(code) {
        let tag = code.substring(0, 2);
        if (tag == 'sz' || tag == 'sh') {
            return code.substring(2);
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
        let css = ".my-stoks-table {color: #383838; font-size: 14px; } \n\
                   .my-stoks-table th {height: 40px; font-size:12px; color: #999; vertical-align: middle;font-weight: normal; text-align:left;} \n\
                   .my-stoks-table tr:nth-child(even) { background-color: #f9fafc;} \n \
                   .my-stoks-table tr:hover {background-color: #ECEFF9;} \n\
                   .my-stoks-table td, th { vertical-align: middle; height: 66px;} \n\
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
        }
        this.datas = data;
        this.datasMap = mdata;
        this.loadHotsZH();
    }

    buildUI() {
        if (! this.datas || !this.headers) {
            return;
        }
        let tab = $('<table class="my-stoks-table" > </table>');
        let hds = this.buildHeadersUI();
        tab.append(hds);
        let thiz = this;
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            let ftr = $('<tr> <td colspan="' + (this.headers.length + 1) + '" class="industry" > ' + sd.industry_name + '&nbsp;&nbsp;' + sd.stocks.length + ' </td> </tr>');
            tab.append(ftr);
            this.trs[sd.industry_name] = ftr;
            
            for (let j = 0; j < sd.stocks.length; j++) {
                let sdx = sd.stocks[j];
                sdx.key = sdx.secu_code + ':' + sd.industry_name;
                let tr = this.buildRowUI(j, sdx);
                tab.append(tr);
                tr.dblclick(function() {thiz.openKLineDialog($(this).attr('code'))});
                //tr.click(function() {if (selTr) selTr.removeClass('sel'); selTr = $(this); selTr.addClass('sel'); });
                this.trs[sdx.key] = tr;
            }
        }
        this.table = tab;
        return tab;
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
            let no = 1;
            for (let j = 0; j < ids.stocks.length; j++) {
                let it = ids.stocks[j];
                let tr = this.trs[it.key];
                if (! tr)
                    continue
                this.table.append(tr);
                tr.find('td:first').text(String(no ++));
            }
        }
    }
}