console.log('Load Chrome Extension ..');

function loadHotPageError(tag) {
    let txt = '源代码已发生变更，需要修改代码: ' + tag;
    let info = $("<div style='position:absolute; width: 400px; height:200px; background-color:#ffff00; z-index: 999909999;'> "+ txt + " </div>")
    $(document.body).append(info);
    console.log(txt);
}

function getColumnIndex(heads, colName) {
    for (let i = 0; i < heads.length; i++) {
        let title = heads[i].trim();
        if (colName == title) {
            return i;
        }
        let ts = title.split('\n');
        for (let j = 0; j < ts.length; ++j) {
            if (ts[j].trim() == colName) {
                return i;
            }
        }
    }
    return -1;
}

function loadHotPage() {
    let heads1 = document.querySelectorAll('.iwc-table-content .iwc-table-fixed div.iwc-table-header ul > li');
    let heads2 = document.querySelectorAll('ul.iwc-table-header-ul > li');
    let tb = document.querySelector('.iwc-table-content .iwc-table-scroll table');
    let trs = tb.querySelectorAll('tr');
    let heads = [];

    if (heads1.length == 0 || heads2.length == 0) {
        loadHotPageError('[loadHotPage] 未找到表格列');
        return null;
    }
    for (let i = 0; i < heads1.length; i++) {
        heads.push(heads1[i].innerText.trim());
    }
    for (let i = 0; i < heads2.length; i++) {
        heads.push(heads2[i].innerText.trim());
    }
    let codeIdx = getColumnIndex(heads, '股票代码');
    let nameIdx = getColumnIndex(heads, '股票简称');
    let hotValsIdx = getColumnIndex(heads, '个股热度');
    let hotOrderIdx = getColumnIndex(heads, '个股热度排名');

    if (codeIdx < 0 || nameIdx < 0 || hotValsIdx < 0 || hotOrderIdx < 0) {
        loadHotPageError('[loadHotPage] B 未找到相关列 [股票代码 | 股票简称 | 个股热度 | 个股热度排名]');
        return null;
    }
    let hotVals = heads[hotValsIdx];
    let hotOrders = heads[hotOrderIdx];

    let hotDay = hotVals.split('\n')[1].replaceAll('.', '-').trim();
    let dayRe = /^\d{4}-\d{2}-\d{2}$/;
    if (! dayRe.test(hotDay)) {
        loadHotPageError('[loadHotPage] 未找到日期');
        return null;
    }

    let vals = [];
    for (let i = 0; i < trs.length; ++i) {
        let tds = trs[i].querySelectorAll('td');
        let obj = { code: tds[codeIdx].innerText, name: tds[nameIdx].innerText, hotValue : tds[hotValsIdx].innerText, hotOrder : tds[hotOrderIdx].innerText};
        obj.hotValue = parseInt(obj.hotValue);
        obj.hotOrder = parseInt(obj.hotOrder);
        vals.push(obj);
        console.log(obj);
    }
    pageInfo.hotDay = hotDay;

    return vals;
}

function getPageData(task, resolve) {
    let datas = loadHotPage();

    if (datas[0].hotOrder == task.startOrder) {
        for (let d in datas) {
            pageInfo.hotPageDatas.push(datas[d]);
        }
    }
    
    resolve();
}

function gotoPage(task, resolve) {
    let pageIdx = task.pageIdx;
    let pi = document.querySelectorAll('.pager .page-item > a');
    let a = pi[pageIdx];
    // console.log('gotoPage: ', task, a);
    a.click();
    resolve();
}

function sendPageData(task, resolve) {
    // console.log('sendPageData: ', pageInfo.hotPageDatas);
    let ct = new Date();
    let hotTime = '';
    if (ct.getHours() < 10)
        hotTime += '0';
    hotTime += ct.getHours();
    hotTime += ':';
    if (ct.getMinutes() < 10)
        hotTime += '0';
    hotTime += ct.getMinutes();

    let msg = { cmd: 'SET_HOT_INFO', data: { hotDay: pageInfo.hotDay, hotTime: hotTime, hotInfo: pageInfo.hotPageDatas, isLogined : pageInfo.isLogined } };

    chrome.runtime.sendMessage(msg
        // function(response) {
        // 	console.log('收到来自后台的回复：' + response);
        // }
    );

    // msg = { cmd: 'LOG', data: pageInfo.userInfo, 'name' : 'user info'};
    // chrome.runtime.sendMessage(msg);

    resolve();
}

function initPageInfo(task, resolve) {
    let ops = document.querySelectorAll('.drop-down-box > span');
    let txt = ops[0].innerText;
    pageInfo.perpage = parseInt(txt.substring(2));
    pageInfo.pageCount = document.querySelectorAll('.pager .page-item').length;

    getLoginInfo();
    // console.log('initPageInfo: ', pageInfo);
    if (! pageInfo.isLogined) {
        // wait 120 secods , for user login
        let we = new Task('wait', 120 * 1000, function (task, resolve) { resolve(); });
        workThread.addTask(we);
    }
    for (let i = 1; i < pageInfo.pageCount && pageInfo.isLogined; ++i) {
        let w2 = new Task('Goto Page', 1000, gotoPage);
        w2.pageIdx = i;
        workThread.addTask(w2);
        
        let w1 = new Task('Get Page Data', 8000, getPageData);
        w1.startOrder = i * pageInfo.perpage + 1;
        workThread.addTask(w1);
    }

    let wx = new Task('Send Page Data', 0, sendPageData);
    workThread.addTask(wx);

    resolve();
}

function getLoginInfo() {
    console.log(typeof(document.cookie), document.cookie);

    let items = document.cookie.split(';');
    let cookies = {};
    for (i in items) {
        let vt = items[i].split('=', 2);
        let name = vt[0].trim();
        cookies[name] = vt[1].trim();
    }
    pageInfo.userInfo.userid = cookies['userid'];
    pageInfo.userInfo.u_name = cookies['u_name'];
    pageInfo.isLogined = !!pageInfo.userInfo.userid;
}

var workThread = new Thread();
var pageInfo = {
    pageCount: 0,
    perpage: 0,
    hotPageDatas: [],
    isLogined: false,
    userInfo: {},

    klineCode: '',
    klineSelectDay : '',
    klineHotInfo: null, // server hot data of select code
};

function forSave() {
    let w1 = new Task('Init Page Info', 8000, initPageInfo);
    workThread.addTask(w1);

    // first page
    let w2 = new Task('Get Page Data', 1000, getPageData);
    w2.startOrder = 1;
    workThread.addTask(w2);

    workThread.start();
}

function openLoginPanel() {
    // console.log('openLoginPanel');
    let btn = document.querySelector('.login-box .login_btn.nav_word');
    if (btn) {
        btn.click();
    } else {
        setTimeout(openLoginPanel, 200);
    }
}

function sendLoginData(task, resolve) {
    let msg = { cmd: 'SET_LOGIN_INFO', data: { isLogined: pageInfo.isLogined, userInfo: pageInfo.userInfo } };
    chrome.runtime.sendMessage(msg);

    // console.log('sendLoginData: ', msg);
    resolve();
}

function forLogin() {
    getLoginInfo();
    // console.log('forLogin: ', pageInfo);
    // if (pageInfo.isLogined) {
    //     sendPageData(null, function () { });
    //     return;
    // }
    // wait 120 secods , for user login
    let ws = pageInfo.isLogined ? 5 : 100;
    let we = new Task('wait', ws * 1000, function (task, resolve) { resolve(); });
    workThread.addTask(we);
    let wx = new Task('Send Login Data', 0, sendLoginData);
    workThread.addTask(wx);
    workThread.start();

    // open login panel
    if (! pageInfo.isLogined) {
        openLoginPanel();
    }
}

function getRequestParams() {
    let url = window.location.href;
    let idx = url.indexOf('?');
    if (idx < 0) {
        return {};
    }
    let vals = {};
    url = url.substring(idx + 1);
    let params = url.split('&');
    for (let i in params) {
        let item = params[i].split('=');
        vals[item[0]] = decodeURIComponent(item[1]);
    }
    return vals;
}

//---------------------------------------------------------
function buildKlineUI() {
    document.querySelector('.condition-list').style.display = 'none';
    // '#xuangu-table-popup > .popup_main_box'
    let kline = $('#klinePopup');
    kline.css('float', 'left');
    let hots = $('<div id = "kline_hots_info" style="float: left; width: 260px; height: 590px; border: solid 1px #000; overflow: auto;" > </div>');
    kline.after(hots);
    kline.after('<div id="kline_hots_tip" style="float: left; width: 80px; height:590px; background-color: #ccc;" > </div>');

    setInterval(listenKlineDOM, 300);
}

function updateKlineUI() {
    $('#kline_hots_info').empty();
    let tab = $('<table style="text-align:center; " > </table>');
    tab.append('<tr> <th style="width:70px;" >日期 </th>  <th style="width:50px;">时间 </th> <th  style="width:70px;"> 热度值(万) </th> <th style="width:70px;"> 热度排名 </th> </tr>');
    let lastDay = '';
    for (let d in pageInfo.klineHotInfo) {
        let tr = $('<tr />');
        let v = pageInfo.klineHotInfo[d];
        if (v.day != lastDay) {
            tr.append('<td>' + v.day + '</td>');
            tr.css('border-top', 'solid #ccc 1px');
        } else {
            tr.append('<td> </td>');
        }
        lastDay = v.day;
        tr.append('<td>' + v.time + '</td>');
        tr.append('<td>' + v.hotValue + '&nbsp;万</td>');
        tr.append('<td>' + v.hotOrder + '</td>');
        tab.append(tr);
    }
    $('#kline_hots_info').append(tab);
}

function markKlineHotDay(oldDay, newDay) {
    if (!pageInfo.klineHotInfo) {
        return;
    }
    let newIdx = -1, oldIdx = -1, lastNewIdx = -1;
    for (let i = 0; i < pageInfo.klineHotInfo.length; i++) {
        let d = pageInfo.klineHotInfo[i];
        if (d.day == newDay && newIdx == -1) {
            newIdx = i;
        } else if (d.day == oldDay && oldIdx == -1) {
            oldIdx = i;
        }
        if (d.day == newDay) {
            lastNewIdx = i;
        }
    }
    if (oldIdx >= 0) {
        let dx = $('#kline_hots_info tr:eq(' + (oldIdx + 1) + ') td:eq(0)');
        dx.css('color', '#000');
    }
    if (newIdx >= 0) {
        let dx = $('#kline_hots_info tr:eq(' + (newIdx + 1) + ') td:eq(0)');
        dx.css('color', 'red');
    }

    if (newIdx < 0 || lastNewIdx < 0) {
        return;
    }

    // scroll to visible
    let visibleHeight = $('#kline_hots_info').height();
    if (visibleHeight <= 0) {
        return;
    }

    let startElem = $('#kline_hots_info tr:eq(' + (newIdx + 1) + ')');
    let lastElem = $('#kline_hots_info tr:eq(' + (lastNewIdx + 1) + ')');
    let ROW_HEIGHT = startElem.height();
    let startY = startElem.position().top;
    let endY = lastElem.position().top + ROW_HEIGHT;

    let se = document.querySelector('#kline_hots_info');
    if (startY < se.scrollTop) {
        se.scrollTo({ top: startY, behavior: 'smooth' });
        return;
    }
    if (endY - se.scrollTop > visibleHeight) {
        se.scrollTo({ top: endY - visibleHeight, behavior: 'smooth' });
        return;
    }
}

function listenKlineDOM() {
    let code = $('#klinePopup .code').text();
    if (code != '' && code != pageInfo.klineCode) {
        pageInfo.klineCode = code;
        $('#kline_hots_info').empty();
        pageInfo.klineHotInfo = null;
        // download
        $.get('http://localhost:8071/getHot/' + code, function (result) {
            pageInfo.klineHotInfo = result;
            console.log('Get Server Hot: ', result);
            updateKlineUI();
        });
        return;
    }

    let selectDay = $('#klinePopup .d3charts-tooltip').text().substring(0, 10); // yyyy-MM-dd
    if (selectDay != pageInfo.klineSelectDay) {
        let oldDay = pageInfo.klineSelectDay;
        pageInfo.klineSelectDay = selectDay;
        markKlineHotDay(oldDay, selectDay);
    }
}

//---------------------------------------------------------

function createScript(url) {
    let sc = document.createElement('script');
    sc.setAttribute('type', 'text/javascript');
    sc.src = chrome.extension.getURL(url);
    sc.async = false;
    document.documentElement.appendChild(sc);
}

// 热股排名页面
if (decodeURI(window.location.href).indexOf('个股热度排名') > 0) {
    let reqParams = getRequestParams();
    let openReason = reqParams['openReason'];
    console.log('openReason=', openReason);

    // open from bg extention
    if (openReason == 'FOR-SAVE') {
        forSave();
    } else if (openReason == 'FOR-KEEP-ALIVE' || openReason == 'FOR-LOGIN') {
        forLogin();
    } else if (openReason == 'FuPan') {
        // 复盘
        createScript('iwencai-hot-page-inject.js');
        createScript('fupan/kline.js');
        createScript('fupan/fupan.js');
    } else {
        setTimeout(buildKlineUI, 4000);
        createScript('iwencai-hot-page-inject.js');
    }
}



console.log('Extension-Hot-Page: ', window.location.href);