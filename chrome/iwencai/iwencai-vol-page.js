
function showTop100() {
    let box = $('.pcwencai-pagination-wrap > .drop-down-box');
    let showNum = box.children('span').text();
    if (showNum == '显示100条/页') {
        return 0;
    }
    box.click();
    box.find('li').eq(2).click();
    return 10;
}

function getDataOfDay() {
    let hd = $('.iwc-table-content > .iwc-table-scroll > .iwc-table-header > ul.iwc-table-header-ul');
    let li = hd.children('li');
    let day = li.eq(li.length - 1).text().trim();
    if (day.indexOf('成交额(元) ') >= 0) {
        day = day.substring(6, day.length);
        day = day.replace('.', '-');
        console.log(day);
        return day;
    }
    console.log('[getDataOfDay] 未取得日期, 请检查代码')
    return '';
}

function getTime() {
    let dd = new Date();
    let hm = dd.getHours().toString().padStart(2, '0') + ':' + dd.getMinutes().toString().padStart(2, '0');
    return hm;
}

function isTradeTime() {
    let dd = new Date();
    let hm = dd.getHours().toString().padStart(2, '0') + ':' + dd.getMinutes().toString().padStart(2, '0');
    if (hm < '09:30' || hm > '15:00' || (hm > '11:30' && hm < '13:00')) {
        return false;
    }
    let day = getDataOfDay();
    let cday = dd.getFullYear() + '-' + (dd.getMonth() + 1).toString().padStart(2, '0') +
            '-' + dd.getDate().toString().padStart(2, '0');
    return day == cday;
}

function getDataOfDay(day) {
    console.log(chrome.extension);
    // return chrome.extension.getBackgroundPage().getTopVol(day);
}

function sendData(data) {
    if (! isTradeTime()) {
        return;
    }
    let tradeDay = getDataOfDay();
    if (! tradeDay) {
        return;
    }
    let hm = dd.getHours().toString().padStart(2, '0') + ':' + dd.getMinutes().toString().padStart(2, '0');
    data.tradeDay = tradeDay;
    data.time = hm;
    let msg = { cmd: 'SET_TOP_VOL', data: data};
    chrome.runtime.sendMessage(msg);

    chrome.extension.storage.local.get(data.tradeDay, function(dd) {
        if (! dd) dd = [];
        dd.push(data);
        chrome.extension.storage.local.set(data.tradeDay, dd);
    });
}

var _hasError = false;
var _reloadTime = new Date().getTime();
var _lastLoadDataTime = 0;

function loadTopVolData() {
    let sumVol = 0, avgZF = 0;
    let tb = $('.iwc-table-content > .iwc-table-scroll > .iwc-table-body > table');
    let trs = tb.find('tr');
    for (let i = 0; i < trs.length; i++) {
        let tr = trs.eq(i);
        let tds = tr.children('td');
        let zf = tds.eq(5).text();
        let vol = tds.eq(7).text();
        if (vol.indexOf('亿') < 0) {
            console.log('[loadTopVolData] 表格列发生的变更, 请修改代码');
            _hasError = true;
            return;
        }
        // console.log(i + 1, tds.eq(3).text(), zf, vol);
        zf = parseFloat(zf);
        vol = parseFloat(vol.replace('亿', ''))
        sumVol += vol;
        avgZF += zf;
    }
    avgZF = avgZF / trs.length;

    let result = {avgZF : avgZF * 100 / 100, sumVol : parseInt(sumVol)};
    console.log('[loadTopVolData] result=', result);
    sendData(result);
    _hasError = false;
}

function check() {
    if (! isTradeTime()) {
        return;
    }
    let lds = ['09:30', '09:45', '10:00', '10:15', "10:30", "10:45", '11:00', '11:15', '11:30',
                '13:15', '13:30', '13:45', '14:00', '14:15', '14:30', '14:45', '15:00'];
    if (lds.indexOf(getTime()) >= 0) {
        let diff = (new Date().getTime() - _reloadTime) / 1000;
        if (diff > 30) {
            window.location.reload();
        } else {
            diff = Math.max(8 - diff, 0);
            setTimeout(loadTopVolData, diff * 1000);
        }
        
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

function createRequestUrl(params) {
    oldParams = getRequestParams();
    reqs = '';
    for (k in params) {
        oldParams[k] = params[k];
    }
    for (k in oldParams) {
        reqs += '&' + k + '=' + oldParams[k];
    }
    if (reqs.length > 0) {
        reqs = reqs.substring(1, reqs.length); // strip &
    }
    let url = window.location.href;
    let idx = url.indexOf('?');
    if (idx > 0) {
        url = url.substring(0, idx);
    }
    url += '?' + reqs;
    return url;
}

// 个股成交额排名
if (decodeURI(window.location.href).indexOf('w=个股成交额') > 0) {
    let lv = getRequestParams('lastLoadDataTime');
    if (lv) _lastLoadDataTime = parseInt(lv);
    let ws = showTop100();

    setInterval(function() {
        check();
    }, 10 * 1000);

    // test
    // getDataOfDay('2023-11-18');
}

