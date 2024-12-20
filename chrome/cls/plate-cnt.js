let timelines = {}; // key : {model, ui }
let pageInfo = { tableColNum : 0 };
window['pageInfo'] = pageInfo;
let thread = new Thread();
const ADD_WIDTH = 300;

function updateTimelineUI(code, rowIdx, tr) {
    let item = timelines[code];
    if (! item) {
        item = createTimeLine(code, rowIdx);
        updateTimelineView(code, item);
    }
    if (item.canvas.is(':visible')) {
        return;
    }
    let tds = tr.find('td');
    let td = null;
    if (tds.length < pageInfo.tableColNum) {
        td = $('<td> </td>');
        tr.append(td);
    } else {
        td = tr.find('td:last');
        td.empty();
    }
    td.css('padding', '3px 15px');
    td.append(item.canvas);
}

function createTimeLine(code, rowIdx) {
    let item = {code: code, model: null, view: null, rowIdx: rowIdx, time: 0};
    item.view = new TimeLineView(ADD_WIDTH, 60);
    item.canvas = $(item.view.canvas);
    timelines[code] = item;
    return item;
}

function updateTimelineView(code, item) {
    let cu = new ClsUrl();
    cu.loadHistory5FenShi(code, function(data5) {
        if (! data5 || !data5['date'] || !data5.date.length || !data5['line'] || !data5.line.length)
            return;
        let idx = (data5.date.length - 1) * 241;
        let pre = 0;
        if (idx > 0){
            pre = data5.line[idx - 1].last_px;
        } else {
            pre = data5.line[0].last_px;
        }
        let ds = {date: data5.line[idx].date, pre: pre, line: []};
        for (let i = idx; i < data5.line.length; i++) {
            let ct = data5.line[i];
            ds.line.push({time: ct.minute, price: ct.last_px, money: ct.business_balance, avgPrice: ct.av_px});
        }
        item.time = Date.now();
        item.view.setData(ds);
        item.view.draw();
    });
    return item;
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function getCodeInTd(tr) {
    let txt = tr.find('td:eq(0)').text().trim();
    let code = txt.substring(txt.length - 6)
    if (code && code.length == 6) {
        return code;
    }
    return '';
}

function initTimelineUI() {
    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);
    let trs = $('table.watch-table tr');
    pageInfo.tableColNum = trs.find('th').length + 1;
    let tr0 = $('table.watch-table tr:nth-child(1)');
    if (tr0.children('th').length < pageInfo.tableColNum) {
        tr0.append('<th style="width:' + ADD_WIDTH + 'px">分时</th>');
    }

    function loadAllCodes(tk, resolve) {
        let trs = $('table.watch-table tr');
        for (let i = 1; i < trs.length; i++) {
            trs.eq(i).css('border-top', 'solid 1px #ccc');
            trs.eq(i).css('height', '60px');
            let code = getCodeInTd(trs.eq(i));
            if (code.length != 6) {
                continue;
            }
            updateTimelineUI(code, i, trs.eq(i));
        }
        let task = new Task('LAC', 3000, loadAllCodes);
        thread.addTask(task);
        resolve();
    }

    let task = new Task('LAC', 1000, loadAllCodes);
    thread.addTask(task);
    thread.start();
}

function bindMouseOver() {
    let table = $('table.watch-table');
    
}

function initPlatePage() {
    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let href = 'https://www.cls.cn/stock?code=' + code;
    let obj = $(' <a style="margin-left: 50px; color:#c03030; " href="' + href +'" target="_blank" >  查看K线、分时图 </a>');
    obj.insertAfter('.stock-detail > span:eq(1)');
}

function initTimelineUI_ZT_Num() {
    let trs = $('table.watch-table tr');
    let num = 0;
    let tds = trs.eq(0).find('th');
    let zfCol = -1;
    for (let i = 0; i < tds.length; i++) {
        if (tds.eq(i).text().trim() == '涨跌幅') {
            zfCol = i;
            break;
        }
    }
    if (zfCol < 0) {
        console.log('未找到列：<涨跌幅>');
        return;
    }
    for (let i = 1; i < trs.length; i++) {
        let tds = trs.eq(i).find('td');
        let zf = tds.eq(zfCol).text();
        zf = zf.replace('%', '').replace('+', '');
        zf = parseFloat(zf);
        if (zf > 8) {
            num ++;
        }
    }
    $('.event-querydate-box').append($('<span style="padding-left: 30px; color:red;" >实际涨停：' + num + '</span>'));
}

let url = window.location.href;
if (url.indexOf('https://www.cls.cn/plate?code=') >= 0) {
    setTimeout(() => {
        initPlatePage();
        initTimelineUI();
    }, 2000);
    
}

/*
window.addEventListener("message", function(e)
{
    let data = e.data;
    console.log('get message:', e.data);
    if (data['cmd'] == 'ZT-INFO') {
        window['zt-info'] = data.data;
    }
}, false);
*/