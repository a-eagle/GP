proc_info = {
    hotWindowId: 0,
    lastOpenHotPageTime: 0,
    lastOpenHotPageTimeForSave: 0,
    lastOpenZSPageTime : 0,
    needSave: false,
    hotInfos: [],
    isLogined: false,

    topVols : {},
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
    let cl = false;

    if (cmd == 'SET_HOT_INFO') {
        cl = true;
        // console.log('sender=', sender);
        if (sender && sender.tab && sender.tab.windowId == proc_info.hotWindowId) {
            setHotInfo(data);
        }
    } else if (cmd == 'LOG') {
        cl = true;
        // console.log('Log', request);
        mlog('Log', request);
    } else if (cmd == 'SET_LOGIN_INFO') {
        if (sender && sender.tab && sender.tab.windowId == proc_info.hotWindowId) {
            cl = true;
            setLoginInfo(data);
        }
    } else if (cmd == 'SET_ZS_INFO') {
        cl = true;
        sendZSToServer(data);
    }
	
	if (cl && sendResponse) {
		sendResponse('OK');
	}
});

function sendZSToServer(data) {
    $.ajax({
        url: 'http://localhost:8071/saveZS',
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(data),
        success: function (res) {
            mlog('Success: Send ZS info to server success ', res, data);
        },
        error: function (res) {
            mlog('Fail: Send ZS info to server fail ', data);
        }
    });
}

function setHotInfo(data) {
    if (! proc_info.hotWindowId) {
        return;
    }
    try {
        chrome.windows.remove(proc_info.hotWindowId);
    } catch (e) { }
    
    proc_info.hotWindowId = 0;
    proc_info.isLogined = data.isLogined;
    delete data.isLogined;
    let curDate = formatDate(new Date());
    let needSaveToServer = (curDate == data.hotDay && proc_info.needSave);
    proc_info.needSave = false;
    if (needSaveToServer) {
        proc_info.hotInfos.push(data);
        sendHotInfoToServer(data);
    }
}

function setLoginInfo(data) {
    if (!proc_info.hotWindowId) {
        return;
    }
    try {
        chrome.windows.remove(proc_info.hotWindowId);
    } catch (e) { }

    proc_info.hotWindowId = 0;
    proc_info.isLogined = data.isLogined;
    mlog('setLoginInfo', data);
}

function deepCopy(obj) {
    let _obj = Array.isArray(obj) ? [] : {};
    for (let i in obj) {
        _obj[i] = (typeof obj[i] === 'object') ? deepCopy(obj[i]) : obj[i];
    }
    return _obj;
}

function sendHotInfoToServer(data) {
    // save to server http://localhost:8071/saveHot
    // data = deepCopy(data);
    $.ajax({
        url: 'http://localhost:8071/saveHot',
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(data),
        success: function (res) {
            mlog('Success: Send hot info to server success ', res, data);
        },
        error: function (res) {
            mlog('Fail: Send hot info to server fail ', data);
        }
    });
}

function checkWindowAlive() {
    let bt = (Date.now() - proc_info.lastOpenHotPageTime) / 1000 >= 60 * 2; // 2 minuts
    if (! bt) {
        return;
    }
    // 超时，强制关闭
    mlog('checkWindowAlive Out time, fore close window');
    chrome.windows.remove(proc_info.hotWindowId, function () {
            proc_info.hotWindowId = 0; // reset window id
        }
    );
}

// 热股排名
function hot_run() {
    if (proc_info.hotWindowId) {
        checkWindowAlive();
        return;
    }
    let ft = formatTime(new Date());
    let jtTime = (ft >= '09:30' && ft < '11:35') || (ft >= '13:00' && ft < '15:05');
    let jtTime2 = (ft >= '08:00' && ft < '15:20');
    let jtTime3 = (ft >= '15:05' && ft < '15:30'); // 下载指数数据时间
    let day = new Date();
    let jtDay = day.getDay() != 0 && day.getDay() != 6; // not 周六周日
    let holidays = ['2023-05-01', '2023-05-02', '2023-05-03', '2023-06-22', '2023-06-23', '2023-09-29', '2023-10-02', '2023-10-03', '2023-10-04', '2023-10-05', '2023-10-06'];
    jtDay = jtDay && (holidays.indexOf(formatDate(new Date())) < 0); // 不是节假日

    if (! jtDay) {
        return;
    }
    if (jtTime) {
        if ((Date.now() - proc_info.lastOpenHotPageTimeForSave) / 1000 / 60 >= 5) { // 10 minutes
            let mm = new Date().getMinutes();
            if (mm % 10 == 0) { // 10 minutes
                openHotPage('FOR-SAVE');
            }
            return;
        }
    }
    if (jtTime2) {
        if (proc_info.isLogined) {
            if ((Date.now() - proc_info.lastOpenHotPageTime) / 1000 / 60 >= 30) { // 30 minutes, used for keep logined state
                openHotPage('FOR-KEEP-ALIVE');
            }
        } else {
            if ((Date.now() - proc_info.lastOpenHotPageTime) / 1000 / 60 >= 5) { // 5 minutes, used for login
                openHotPage('FOR-LOGIN');
            }
        }
    }
    if (jtTime3) {
        if ((Date.now() - proc_info.lastOpenZSPageTime) / 1000 / 60 >= 90) { // 90 minutes, used for save ZS
            openZSPage('FOR-SAVE');
        }
    }
}

function openHotPage(openReason) {
    let url = 'http://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E6%8E%92%E5%90%8D%3C%3D200%E4%B8%94%E4%B8%AA%E8%82%A1%E7%83%AD%E5%BA%A6%E4%BB%8E%E5%A4%A7%E5%88%B0%E5%B0%8F%E6%8E%92%E5%90%8D&querytype=stock&openReason=' + openReason;
    needSave = openReason == 'FOR-SAVE';
    
    chrome.windows.create({ url: url, type: 'panel' }, function (window) {
        // callback
        proc_info.hotWindowId = window.id;
        proc_info.needSave = needSave;
        proc_info.lastOpenHotPageTime = Date.now();
        if (needSave) {
            proc_info.lastOpenHotPageTimeForSave = Date.now();
        }
    });
}

function openZSPage(openReason) {
    let url = 'https://www.iwencai.com/unifiedwap/result?w=%E5%90%8C%E8%8A%B1%E9%A1%BA%E6%A6%82%E5%BF%B5%E6%8C%87%E6%95%B0%E6%88%96%E5%90%8C%E8%8A%B1%E9%A1%BA%E8%A1%8C%E4%B8%9A%E6%8C%87%E6%95%B0%E6%8C%89%E6%B6%A8%E8%B7%8C%E5%B9%85%E6%8E%92%E5%BA%8F&querytype=zhishu&openReason=' + openReason;
    needSave = openReason == 'FOR-SAVE';
    
    chrome.windows.create({ url: url, type: 'panel' }, function (window) {
        // callback
        if (needSave) {
            proc_info.lastOpenZSPageTime = Date.now();
        }
    });
}

setInterval(hot_run, 1000 * 20); // 20 seconds


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
		updateHeaders(hds, 'Access-Control-Allow-Origin', '*');
		updateHeaders(hds, 'Access-Control-Allow-Credentials', 'true');
		updateHeaders(hds, 'Access-Control-Allow-Methods', '*');
		return {responseHeaders : hds};
	},
	{urls: ['http://captcha.10jqka.com.cn/*', '*://*/*']},
	['responseHeaders','blocking', 'extraHeaders']
);