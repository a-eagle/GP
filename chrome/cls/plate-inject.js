let timelines = {}; // code : TimeLineView
let pageInfo = { tableColNum : 0 };
let thread = new Thread();
let tlMgr = new TimeLineUIManager();
const ADD_WIDTH = 300;
var stockDatas = null;
var stocksTable = null;
var stocksTrs = {};
var lastSortHeader = null;

function updateTimelineUI(code, tr) {
    let view = timelines[code];
    if (! view) {
        view = createTimeLineView(code);
    }
    if ($(view.canvas).is(':visible')) {
        return;
    }
    let tdLast = tr.find('td:last');
    let td = null;
    if (tdLast.text() == '分时图') {
        td = tdLast;
        td.empty();
    } else {
        td = $('<td> </td>');
        tr.append(td);
    }
    td.css('padding', '3px 15px');
    td.append(view.canvas);
}

function createTimeLineView(code, width, height) {
    width = width || ADD_WIDTH;
    height = height || 60;
    let view = new TimeLineView(width, height);
    timelines[code] = view;
    tlMgr.add(view);
    view.loadData(code);
    return view;
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function getCodeInTd(tr) {
    let txt = tr.find('td:eq(0)').text().trim();
    txt = txt.substring(txt.length - 8);
    let tag = txt.substring(0, 2);
    if (tag == 'sh' || tag == 'sz') {
        let code = txt.substring(2);
        return code;
    }
    tag = txt.substring(0, 3);
    if (tag == 'cls') {
        return txt;
    }
    return '';
}

function loadAllCodes(tk, resolve) {
    let trs = $('table.watch-table tr');
    let tr0 = $('table.watch-table tr:nth-child(1)');
    let lastHead = tr0.find('th:last');
    if (lastHead.text().trim() != '分时图') {
        tr0.append('<th style="width:' + ADD_WIDTH + 'px">分时图</th>');
        pageInfo.tableColNum = trs.find('th').length;
    }
    let firstHead = tr0.find('th:first');
    if (firstHead.text().trim() != '#') {
        $('<th width="50px">#</th>').insertBefore(firstHead);
    }
    for (let i = 1; i < trs.length; i++) {
        trs.eq(i).css('border-top', 'solid 1px #ccc');
        trs.eq(i).css('height', '60px');
        let code = getCodeInTd(trs.eq(i));
        if (! code) {
            continue;
        }
        let tdFirst = trs.eq(i).find('td:first');
        let clz = tdFirst.attr('class') || '';
        if (clz.indexOf('IDX') < 0) {
            $('<td class="IDX" width="50px">' + i + '</td>').insertBefore(tdFirst);
        }
        updateTimelineUI(code, trs.eq(i));
    }
    let task = new Task('LAC', 3000, loadAllCodes);
    thread.addTask(task);
    resolve();
}

function sortHead() {
    let old = lastSortHeader;
    let td = $(this);
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
    lastSortHeader = td;
    if (old != lastSortHeader && old) {
        old.html(td.attr('v') + '&#9830;');
    }
    td.html(td.attr('v') + tag);
    sortNumberBy(td.attr('a'), v == 'asc');
}

function buildNewUI() {
    if (! stockDatas) {
        return;
    }
    if (stocksTable) {
        if (! stocksTable.is(':visible')) {
            $('table.watch-table').replaceWith(stocksTable);
        }
        return;
    }

    function elipse(s) {
        if (s && s.length > 40) {
            s = s.substring(0, 40) + '...';
        }
        return s;
    }

    function price(row) {
        if (row.change >= 0)
            return '<td style="color:#de0422;">' + row.last_px + '</td>';
        return '<td style="color:#52C2A3;">' + row.last_px + '</td>';
    }

    function zf(row) {
        let val = row.change;
        val = (val * 100).toFixed(2);
        if (row.change >= 0)
            return '<td style="color:#de0422;">' + val + '%</td>';
        return '<td style="color:#52C2A3;">' + val + '%</td>';
    }

    let tab = $('<table id="my-stoks-table"> </table>');
    let hds = $('<tr style="vertical-align: middle;"> <th width=50></th> <th width=100>股票</th> <th width=80>价格</th> <th width=80 class="s" a="change">涨幅</th> <th width=80 class="s" a="head_num">领涨次数</th> <th width=80 class="s" a="cmc" >流通市值</th> <th width=100 class="s" a="fundflow">资金流向</th>  <th width=300>简介</th> <th width=300 >分时图</th> </tr>');
    let tds = hds.find('th.s');
    for (let i = 0; i < tds.length; i++) {
        let td = tds.eq(i);
        td.attr('v', td.text());
        td.append('&#9830;');
        td.click(sortHead);
    }
    tab.append(hds);
    for (let i = 0; i < stockDatas.length; i++) {
        let sd = stockDatas[i];
        let tr = $('<tr> <td style="text-align:center;">' + (i + 1) + ' </td> <td> <span style="color:#383838; font-weight:bold;" >' + sd.secu_name +
                '</span><br/> <span style="color:#666;font-size:12px;"> ' + sd.secu_code + '</span> </td> ' + price(sd) +
                zf(sd) + ' <td>' + sd.head_num + ' </td> <td>' + parseInt(sd.cmc / 100000000)+ '亿 </td> <td>' +
                parseInt(sd.fundflow / 10000) + '万 </td>  <td class="pl20" title="' + sd.assoc_desc + '" style="font-size:12px;">' + 
                elipse(sd.assoc_desc) + ' </td>  <td class="fs"> </td>  </tr>');
        let view = createTimeLineView(sd.secu_code, 300, 60);
        tr.find('td.fs').append(view.canvas);
        tab.append(tr);
        stocksTrs[sd.secu_code] = tr;
    }
    stocksTable = tab;
    $('table.watch-table').replaceWith(stocksTable);
}

function sortNumberBy(name, asc) {
    if (!stockDatas || !stocksTable) {
        return;
    }
    stockDatas.sort(function(a, b) {let v = a[name] - b[name]; return asc ? v : -v;});
    for (k in stocksTrs) {
        stocksTrs[k].detach();
    }
    for (let i = 0; i < stockDatas.length; i++) {
        let code = stockDatas[i].secu_code;
        stocksTable.append(stocksTrs[code]);
        stocksTrs[code].find('td:first').text(String(i + 1));
    }
}

function startBuildUI() {
    //let task = new Task('LAC', 1000, buildNewUI);
    //thread.addTask(task);
    //thread.start();
    setInterval(buildNewUI, 1000);
}

function initTimelineUI() {
    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);
}

function bindMouseOver() {
    let table = $('table.watch-table');
    
}

function initPlatePage() {
    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let view = createTimeLineView(code);
    let ui = $(view.canvas);
    ui.css('margin-left', '50px').css('background-color', '#f8f8f8');
    ui.insertAfter('.stock-detail > span:eq(1)');
    let span = $('.stock-detail span:first');
    let txt = span.text();
    span.html('<a href="https://www.cls.cn/stock?code=' + code + '" target=_blank>' + txt + ' </a> ');
}

let url = window.location.href;
if (url.indexOf('https://www.cls.cn/plate?code=') >= 0) {
    $(function() {
        initPlatePage();
        initTimelineUI();
    });
}

function loadStoksData() {
    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let params = 'app=CailianpressWeb&os=web&rever=1&secu_code=' + code + '&sv=8.4.6&way=last_px';
    params = new ClsUrl().signParams(params);
    let url = 'https://x-quote.cls.cn/web_quote/plate/stocks?' + params;
    $.ajax({
        url: url, type: 'GET',
        success: function(resp) {
            stockDatas = resp.data.stocks;
        }
    });
}

function initStyle() {
    let style = document.createElement('style');
    let css = "#my-stoks-table {color: #383838; font-size: 14px; } \n\
               #my-stoks-table th {height: 40px; font-size:12px; color: #999; vertical-align: middle;font-weight: normal; text-align:left;} \n\
               #my-stoks-table tr:hover {background-color: #ECEFF9;} \n\
               #my-stoks-table tr:nth-child(even) { background-color: #f9fafc;} \n \
               #my-stoks-table td, th { vertical-align: middle; height: 66px;} \n\
               #my-stoks-table .fs {padding: 3px 3px;} \n\
               #my-stoks-table .pl20 {padding-right:20px;} \n\
            ";
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);
}

initStyle();
loadStoksData();
startBuildUI();