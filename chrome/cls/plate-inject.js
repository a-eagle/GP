let timelines = {}; // code : TimeLineView
let pageInfo = { tableColNum : 0 };
let thread = new Thread();
let tlMgr = new TimeLineUIManager();
const ADD_WIDTH = 300;

function updateTimelineUI(code, tr) {
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
    for (let i = 1; i < trs.length; i++) {
        trs.eq(i).css('border-top', 'solid 1px #ccc');
        trs.eq(i).css('height', '60px');
        let code = getCodeInTd(trs.eq(i));
        if (! code) {
            continue;
        }
        updateTimelineUI(code, trs.eq(i));
    }
    let task = new Task('LAC', 3000, loadAllCodes);
    thread.addTask(task);
    resolve();
}

function initTimelineUI() {
    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);
    
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