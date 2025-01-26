proc_info = {
    clsZTWindowId: 0,
    savedDays : {}, // day : True
    timelines : {}, // {code: { loadTime: xxx, data: xxx }, .... }

    anchors:{}, // day : []
    lastLoadAnchorsTime : 0,
    lastLoadDegreeTime: 0,
    degree: {}, // day: [{time:xx, degree:xx}, ...]
    thread: new Thread(),
};

// YYYY-MM-DD
function formatDate(date) {
    let d = date;
    let m = d.getMonth() + 1;
    return '' + d.getFullYear() + '-' + (m > 9 ? m : '0' + m) + '-' + (d.getDate() > 9 ? d.getDate() : '0' + d.getDate());
}

// HH:MM
function formatTime(date) {
    let d = date;
    let h = d.getHours();
    let m = d.getMinutes();
    let v = '';
    v += h > 9 ? h : '0' + h;
    v += ':';
    v += m > 9 ? m : '0' + m;
    return v;
}

function mlog(...args) {
    let ms = formatDate(new Date()) + ' ' + formatTime(new Date());
    console.log('[' + ms + '] ', ...args);
}

// 监听消息
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
	let cmd = request['cmd'];
    let data = request['data'];

    if (cmd == 'GET_ANCHORS') {
        let rs = getAnchors(data.lastDay, data.traceDayNum);
        if (sendResponse) {
            sendResponse(rs);
        }
    } else if (cmd == 'GET_DEGREE') {
        let day = data;
        let rs = proc_info.degree[day];
        //console.log('[GET_DEGREE]', day, rs);
        if (sendResponse) {
            sendResponse(rs);
        }
    }
});

function deepCopy(obj) {
    let _obj = Array.isArray(obj) ? [] : {};
    for (let i in obj) {
        _obj[i] = (typeof obj[i] === 'object') ? deepCopy(obj[i]) : obj[i];
    }
    return _obj;
}

function run_loop() {
    if (Date.now() - proc_info.lastLoadAnchorsTime >= 60 * 60 * 1000) {
        proc_info.lastLoadAnchorsTime = Date.now();
        loadHistoryAnchor();
    }
    let time = formatTime(new Date());
    if ((time >= '09:30' && time <= '11:30') || (time >= '13:00' && time <= '15:00')) {
        let m = new Date().getMinutes();
        if (m % 5 == 0 && Date.now() - proc_info.lastLoadDegreeTime >= 2 * 60 * 1000) {
            proc_info.lastLoadDegreeTime = Date.now();
            loadDegree();
        }
    }
}

function loadDegree() {
    let url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597';
    $.ajax({url : url, success: function(resp) {
        let data = resp.data;
        let day = data.date; // YYYY-MM-DD
        let degree = data.market_degree;
        if (formatDate(new Date()) != day) {
            return;
        }
        let rs = proc_info.degree[day];
        if (! rs) {
            proc_info.degree[day] = rs = [];
        }
        rs.push({time: formatTime(new Date()), degree: parseInt(degree * 100), date: new Date()});
    }});
}

function openZTPage() {
    let url = 'https://www.cls.cn/finance?autoClose=1';
    chrome.windows.create({ url: url, type: 'panel' }, function (window) {
        // callback
        proc_info.clsZTWindowId = window.id;
        proc_info.lastOpenZSPageTime = Date.now();
        let today = formatDate(new Date());
        proc_info.savedDays[today] = true;
    });
}

function loadTimeLine(code) {
    if (! code || code.length != 6) {
        return;
    }
    let obj = proc_info.timelines[code];
    let diff = new Date().getTime() - (obj ? obj.loadTime : 0);
    if (diff <= 3 * 60 * 1000) {
        return;
    }

    let url = 'http://localhost:8071/ths/load-timeline?code=' + code;
    $.ajax({
        type: 'GET',
        url : url,
        success: function(res) {
            //console.log(res);
            if (res.status == 'OK') {
                proc_info.timelines[code] = {loadTime: new Date().getTime(), data: res.data};
            }
        }
    });
}

function getTimeLine(code) {
    let ts = new Date().getTime();
    let obj = proc_info.timelines[code];
    if (! obj) {
        return null;
    }
    let diff = ts - obj.loadTime;
    if (diff >= 10 * 60 * 1000) { // 超过10分钟
        // return null;
    }
    return obj.data;
}

function loadAnchorTask(task, resolve) {
    if (proc_info.anchors[task.day] && formatDate(new Date()) != task.day) {
        resolve();
        return;
    }
    new ClsUrl().loadAnchor(task.day, function(data) {
        if (data.errno == 0)
            proc_info.anchors[task.day] = data.data;
        resolve();
    });
}

// lastDay = yyyy-mm-dd | Date
function getAnchors(lastDay, traceDayNum) {
    if (lastDay instanceof  Date) {
        lastDay = formatDate(lastDay);
    }
    let ks = [];
    for (let k in proc_info.anchors) {
        if (k <= lastDay)
            ks.push(k);
    }
    ks.sort();
    let rs = [];
    for (let i = ks.length - 1, num = 0; i >= 0; i --) {
        let a = proc_info.anchors[ks[i]];
        if (! a || !a.length) {
            continue;
        }
        if (num > traceDayNum)
            break;
        rs.push(a);
        ++num;
    }
    return rs;
}

// 不含当日
function loadHistoryAnchor() {
    let dd = new Date();
    for (let i = 0; i < 90; i++) {
        let dd2 = new Date(new Date().setDate(dd.getDate() - 1 - i));
        let tsk = new Task('LA', 100, loadAnchorTask);
        tsk.day = formatDate(dd2);
        proc_info.thread.addTask(tsk);
    }
    proc_info.thread.start();
}

setInterval(run_loop, 1000 * 10);
loadHistoryAnchor();

// CORS
function updateHeaders(hds, name, value) {
	let sname = name.toLowerCase();
	for (let i = 0; i < hds.length; i++) {
		if (hds[i].name.toLowerCase() == sname) {
			hds[i].value = value;
			return;
		}
	}
	hds.push({'name': name, 'value': value});
}

chrome.webRequest.onHeadersReceived.addListener(function(details) {
		let hds = details.responseHeaders;
        // console.log(details);
		updateHeaders(hds, 'Access-Control-Allow-Origin', '*');
		updateHeaders(hds, 'Access-Control-Allow-Credentials', 'true');
		updateHeaders(hds, 'Access-Control-Allow-Methods', '*');
        let url = details.url;
		return {responseHeaders : hds};
	},
	{urls: ['https://www.cls.cn/*', '*://*/*']},
	['blocking', 'responseHeaders', 'extraHeaders'] // , 
);

/*
chrome.webRequest.onCompleted.addListener(function(details) {
        let url = details.url;
        console.log(url);
        $.get(url, function(data, status) {
            console.log(data);
        });
    },
    {urls : ['https://x-quote.cls.cn/quote/stock/emotion_options*']},
    ['blocking', 'responseHeaders']
);
*/