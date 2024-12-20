let timelines = {}; // code : TimeLineView
let pageInfo = { tableColNum : 0 };
window['pageInfo'] = pageInfo;
let thread = new Thread();
const ADD_WIDTH = 300;

function updateTimelineUI(code, rowIdx, tr) {
    let view = timelines[code];
    if (! view) {
        view = createTimeLineView(code);
    }
    if ($(view.canvas).is(':visible')) {
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
    td.append(view.canvas);
}

function createTimeLineView(code, width, height) {
    width = width || ADD_WIDTH;
    height = height || 60;
    let view = new TimeLineView(width, height);
    timelines[code] = view;
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
    let view = createTimeLineView(code, 600, 80);
    let ui = $(view.canvas);
    ui.css('margin-left', '50px').css('background-color', '#f8f8f8');
    ui.insertAfter('.stock-detail > span:eq(1)');
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