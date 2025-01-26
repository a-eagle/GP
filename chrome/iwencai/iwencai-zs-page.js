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

class HeadNames {
	constructor() {
		this.day = '';
		this.heads = [];
		this.errors = [];
		this.saveColumns = {};
	}
	
	init() {
		let headNames = [];
		let tabCnt = $('.iwc-table-content.isTwoLine');
		let titles = $(tabCnt.children('.iwc-table-fixed')).find('ul > li');
		for (let i = 0; i < titles.length; i++) {
			let it = titles.eq(i);
			let n = it.text().trim();
			headNames.push(n);
		}
		titles = tabCnt.find('.iwc-table-scroll > .iwc-table-header > ul > li');
		for (let i = 0; i < titles.length; i++) {
			let it = titles.eq(i);
			let n = it.text().trim();
			headNames.push(n);
		}
		let rs = [];
		for (let i = 0; i < headNames.length; i++) {
			let it = headNames[i];
			it = it.split(/\s+/);
			// console.log(it)
			let name = it[0], day = '';
			if (it.length == 2) {
				if (/\d{4}[.]\d{2}[.]\d{2}/.test(it[1])) {
					day = it[1];
					if (! this.day) {
						this.day = day;
					} else if (this.day != day) {
						console.log(day, 'error date');
                        throw '[HeadNames].init fail, ' + day + ' is error date'
					}
				}
			}
			name = name.replace(/\(.*?\)/, '');
			this.heads.push(name);
		}
		if (this.day) {
			this.day = this.day.replace(/[.]/g, '-');
		}
		console.log(this.heads);
		console.log('Current day is ', this.day);

		
		let ts = ['指数代码', '指数简称', '收盘价', '涨跌幅', '开盘价', '最高价' ,'换手率', '成交额', '成交量'];
		let ets = ['code', 'name', 'close', 'zdf', 'open', 'high', 'rate', 'money', 'vol'];
		for (let i = 0; i < ts.length; i++) {
			this.saveColumns[ets[i]] = this.getColumnIdx(ts[i]);
			if (this.saveColumns[ets[i]] < 0 ) {
				this.errors.push('Not find column: ' + ts[i]);
			}
		}
	}
	
	getColumnIdx(name) {
		return this.heads.indexOf(name);
	}
}

function parseCell(colName, val) {
    if (colName == 'money' || colName == 'vol') {
        if (val.indexOf('亿') > 0) {
            val = val.replace('亿', '');
            val = parseInt(val);
        } else {
            val = 0;
        }
    } else if (colName == 'close' || colName == 'zdf' || colName == 'open' || colName == 'high' || colName == 'rate') {
        val = parseFloat(val);
    }
	return val;
}

function loadTableData() {
	let trs = $('.iwc-table-content.isTwoLine > .iwc-table-scroll > .iwc-table-body > table tr');
    //if (trs.length != zsPageInfo['pageSize']) {
    //    let msg = '[loadTableData] error, load data length = ' + rs.length + ', but page-size is ' + zsPageInfo['pageSize'];
    //    console.log(msg);
    //    throw msg;
    //}

	for (let i = 0; i < trs.length; i++) {
		let tds = trs.eq(i).children('td');
		let item = {};
        item['day'] = headInstance.day;
		for (let k in headInstance.saveColumns) {
			let idx = headInstance.saveColumns[k];
			let val = tds.eq(idx).text().replace(',', '');
			item[k] = parseCell(k, val);
		}
		zsPageInfo['data'].push(item);
	}
    console.log('[loadTableData] load data num: ' + trs.length);
}

function clickNextPage() {
    let pages = $('ul.pcwencai-pagination > li');
    let next = pages.eq(pages.length - 1);
    if (next.hasClass('disabled')) {
        console.log('[clickNextPage] is end to last page');
        return false; // finished
    }
    next.find('a').get(0).click();
    return true;
}

function getPageSize() {
    let span = $('.pcwencai-pagination-wrap > .drop-down-box > span');
    let txt = span.text().trim();
    if (/显示\d+条[/]页/.test(txt)) {
        let num = txt.match(/(\d+)/);
        return parseInt(num);
    }
    let msg = 'getPageSize() Not find 显示xx条/页';
    console.log(msg);
    throw msg;
}

function getPageNum() {
    let li = $('ul.pcwencai-pagination > li');
    for (let i = li.length - 1; i >= 0; --i) {
        let txt = li.eq(i).text().trim();
        if (txt.match(/^\d+$/)) {
            return parseInt(txt);
        }
    }
    let msg = 'getPageNum() Not find page num info';
    console.log(msg);
    throw msg;
}

function loadFinished() {
    console.log('[loadFinished] load data length: ', zsPageInfo['data'].length);
    data = zsPageInfo['data'];
    data50 = [];
    for (let i = 0; i < data.length; i++) {
        let dt = data[i];
        if (dt['money'] >= 50) {
            data50.push(dt);
        }
        if (i <= data.length / 2) {
            dt['zdf_PM'] = i + 1;
        } else {
            dt['zdf_PM'] = i - data.length;
        }
    }
    for (let i = 0; i < data50.length; i++) {
        let dt = data50[i];
        if (i <= data50.length / 2) {
            dt['zdf_50PM'] = i + 1;
        } else {
            dt['zdf_50PM'] = i - data50.length;
        }
    }

    let msg = { cmd: 'SET_ZS_INFO', data:  zsPageInfo['data']};
    chrome.runtime.sendMessage(msg
        // function(response) {
        // 	console.log('收到来自后台的回复：' + response);
        // }
    );
}


zsPageInfo = {};
thread = new Thread();
headInstance = new HeadNames();

function initPage() {
    headInstance.init();
    zsPageInfo['pageSize'] = getPageSize();
    zsPageInfo['pageNum'] = getPageNum();
    console.log(headInstance);

    for (let i = 0; i < zsPageInfo['pageNum']; i++) {
        if (i != 0) {
            let task2 = new Task('Click Page ' + (i + 1), 5 * 1000, function(task, resolve) {clickNextPage(); resolve();  } );
            thread.addTask(task2);
        }
        let task = new Task('Load Page ' + i, 10 * 1000, function(task, resolve) { loadTableData(); resolve(); } );
        thread.addTask(task);
    }
    thread.addTask(new Task('Load Finished', 1000, function(task, resolve) { loadFinished(); resolve(); }));
    thread.addTask(new Task('CloseWindow', 3000, function(task, resolve) { window.close(); resolve(); }));
}


function beginLoadPageData() {
    zsPageInfo['data'] = [];
    thread.addTask(new Task('HeadNames.init', 10 * 1000, function(task, resolve) {initPage();  resolve(); }));
    thread.start();
}


console.log(decodeURI(window.location.href));

// http://www.iwencai.com/unifiedwap/result?w=同花顺概念指数或同花顺行业指数按涨跌幅排序&querytype=zhishu
if (decodeURI(window.location.href).indexOf('w=同花顺概念指数或同花顺行业指数按涨跌幅排序') > 0) {
    let lv = getRequestParams();
    console.log('openReason=', lv);
    if (lv['openReason'] == 'FOR-SAVE') {
        beginLoadPageData();
    }
}