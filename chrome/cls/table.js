class StockTable {
    // headers = [ {text: xxx, width: xx, sortable: true, name: xx, }  ]
    constructor(headers) {
        this.headers = headers;
        this.lastSortHeader = null;
        this.datas = null;
        this.datasMap = null;
        this.table = null;
        this.trs = {};
    }

    createTimeLineView(code, width, height) {
        width = width || 300;
        height = height || 60;
        let view = new TimeLineView(width, height);
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
    }

    onSortHead(thiz, td) {
        console.log('[onSortHead]', this);
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
        thiz.lastSortHeader = td;
        if (old != thiz.lastSortHeader && old) {
            old.html(old.attr('v') + '&#9830;');
            old.attr('sv', '');
        }
        td.html(td.attr('text') + tag);
        thiz.sortNumberBy(td.attr('a'), v == 'asc');
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
                thiz.onSortHead(thiz, $(this));
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
                hd.append(view.canvas);
                let thiz = this;
                view.addListener('LoadDataEnd', function(evt) {thiz.onLoadFsDataEnd(evt)});
            } else {
                let d = rowData[k];
                hd = $('<td> ' + (d == undefined ? '' : d) + ' </td>');
            }
            tr.append(hd);
        }
        return tr;
    }

    buildUI() {
        if (! this.datas) {
            return;
        }
        /*if ($('.toggle-nav-active').text() != '股票池')
            return;
        if (this.table) {
            if (! this.table.is(':visible')) {
                $('table.watch-table').replaceWith(this.table);
            }
            return;
        }
        */
    
        let tab = $('<table class="my-stoks-table" > </table>');
        let hds = this.buildHeadersUI(); // $('<tr style="vertical-align: middle;"> <th width=50></th> <th width=90>股票</th> <th width=70 class="s" a="sortHots">热度</th> <th width=70 class="s" a="change">涨幅</th>  <th width=70 class="s" a="zs">涨速</th> <th width=70 class="s" a="head_num">领涨次数</th> <th width=70 class="s" a="cmc" >流通市值</th> <th width=90 class="s" a="fundflow">资金流向</th>  <th width=300>简介</th> <th width=300 >分时图</th> </tr>');
        tab.append(hds);
        for (let i = 0; i < this.datas.length; i++) {
            let sd = this.datas[i];
            let tr = this.buildRowUI(i, sd);
            tab.append(tr);
            tr.dblclick(function() {this.openKLineDialog($(this).attr('code'))});
            //tr.click(function() {if (selTr) selTr.removeClass('sel'); selTr = $(this); selTr.addClass('sel'); });
            this.trs[sd.secu_code] = tr;
        }
        this.table = tab;
        //$('table.watch-table').replaceWith(this.table);
        return tab;
    }

    openKLineDialog(code) {
        if (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh') {
            code = code.substring(2);
        }
        $.get('http://localhost:5665/openui/kline/' + code);
    }

    onLoadFsDataEnd(evt) {
        console.log('[onLoadFsDataEnd]', this.prototype);
        let view = evt.src;
        let maxZs = view.getMaxZs();
        if (! maxZs) {
            return;
        }
        let zf = maxZs.zf;
        let td = $(view.canvas).parent().parent().find('td.zs');
        let sd = this.datasMap[view.code];
        sd.zs = zf;
        td.text('' + zf.toFixed(1) + '%');
    }

    sortNumberBy(name, asc) {
        if (!this.datas || !this.table) {
            return;
        }
        this.datas.sort(function(a, b) {let v = a[name] - b[name]; return asc ? v : -v;});
        for (let k in this.trs) {
            this.trs[k].detach();
        }
        let no = 1;
        for (let i = 0; i < this.datas.length; i++) {
            let code = this.datas[i].secu_code;
            if (this.trs[code]) {
                this.table.append(stocksTrs[code]);
                this.trs[code].find('td:first').text(String(no ++));
            }
        }
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
        if (s && s.length > 40) {
            s = s.substring(0, 40) + '...';
        }
        return s;
    }

}