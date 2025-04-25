let pageInfo = { tableColNum : 0 , groupsMgr : null};
const ADD_WIDTH = 300;

class ZsRelatedManager {
    constructor() {
        this.groups = [
            ['cls80573 商业零售', '881158 零售', 'cls80032 食品饮料', 'cls80041 乳业奶粉', 'cls80039 休闲食品'], //大消费类 2025.04.18
            ['cls80353 跨境电商', '885642 跨境电商', 'cls80551 跨境支付', '885966 跨境支付'],
            ['cls82542 统一大市场', 'cls80087 东盟自贸区'],
        ];
    }

    isCode(code) {
        if (! code) return false;
        code = code.trim();
        if (code.length == 8 && code.substring(0, 3) == 'cls')
            return true;
        if (code.length == 8 && (code.substring(0, 2) == 'sz' || code.substring(0, 2) == 'sh'))
            return true;
        if (code.length == 6 && (code.charAt(0) == '0' || code.charAt(0) == '3' || code.charAt(0) == '6'))
            return true;
        if (code.length == 6 && code.substring(0, 2) == '88')
            return true;
        return false;
    }

    getCodeInfo(info) {
        info = info.trim();
        if (! info) return null;
        let its = info.split(' ');
        let rs = {code: null, name: null};
        for (let it of its) {
            if (! it) continue;
            if (! rs.code && this.isCode(it)) rs.code = it;
            else rs.name = it;
        }
        if (! rs.code)
            return null;
        return rs;
    }

    getItemUI(code) {
        if (! this.items) return null;
        for (let it of this.items) {
            if (it.code == code)
                return it.ui;
        }
        return it;
    }

    create(code, day) {
        let gps = null;
        for (let gp of this.groups) {
            for (let it of gp) {
                if (it.indexOf(code) >= 0) {
                    gps = gp;
                    break;
                }
            }
        }
        if (! gps) {
            return null;
        }
        this.items = [];
        let thiz = this;
        let div = $('<div style="max-width:750px;"> </div>');
        for (let it of gps) {
            let cc = this.getCodeInfo(it);
            if (! cc) continue;
            let cv = new CodeView(cc.code, cc.name, day);
            div.append(cv.ui);
            cv.ui.css({'margin-left': '10px'});
            if (cc.code == code) {
                cv.ui.css({'border' : 'solid 2px #006633'});
            }
            this.items.push(cv);
            cv.ui.click(function() {thiz.onClick(this);})
        }
        return div;
    }

    onClick(elem) {
        let code = $(elem).attr('code');
        let name = $(elem).attr('name');
        let params = getLocationParams();
        if (code.substring(0, 3) == 'cls') {
            params.code = code;
            delete params.refThsCode;
            delete params.refThsName;
        } else {
            params.refThsCode = code;
            params.refThsName = name;
        }
        window.location.href = paramsToUrl(params);
    }
}

function createTimeLineView(code, params) {
    let view = new TimeLineView(ADD_WIDTH, 60);
    //tlMgr.add(view);
    let day = getLocationParams('day');
    window.myview = view;

    let onLoadEnd = function(evt) {
        let zf = evt.src.zf;
        let span = $('.stock-detail > span:eq(1)');
        span.html('<label style="color:' + (zf > 0 ? 'red' : zf < 0 ? 'green' : '#000') + '">' + zf.toFixed(2) + '%' + '<label>');
    };
    view.addListener('LoadDataEnd', onLoadEnd);
    view.loadData(code, day);

    if (params.refThsCode) {
        loadRefThsCode(view, params);
    }
    return view;
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function loadRefThsCode(view, params) {
    let span = $('.stock-detail > span:eq(0)');
    let title = '【' + params.refThsCode + ' ' + decodeURIComponent(params.refThsName || '') + '】';
    span.text(title);
    document.title = title;
}

function initPlatePage() {
    let params = getLocationParams();
    let code = params.refThsCode || params.code;
    let day = params.day || '';
    let period = params.period;
    if (! period) {
        params.period = 10;
        window.location.href = paramsToUrl(params);
        return;
    }

    let span = $('.stock-detail > span');
    if (span.length < 2) {
        setTimeout(initPlatePage, 1000);
        return;
    }
    let view = createTimeLineView(code, params);
    let ui = $(view.canvas);
    ui.css('margin-left', '50px').css('background-color', '#f8f8f8').css('border', 'solid 1px #a0c0a0');
    let pdiv = $('.stock-detail');
    let btn = $('<button style="margin-left: 30px;"> 打开K线图-Win </button>');
    btn.click(function() {
        $.ajax({
            url: 'http://localhost:5665/openui/kline/' + code, 
            type: 'POST', contentType: 'application/json',
            data: JSON.stringify({day: day}),
        });
    });
    pdiv.append(ui).append(btn);
    pdiv.css('background-color', 'rgb(250, 250, 250)');


    let picker = $('<button style="margin-left:30px;" >选择日期 </button>');
    let fday = null;
    if (day) {
        let mday = day.replaceAll('-', '');
        fday = mday.substring(0, 4) + '-' + mday.substring(4, 6) + '-' + mday.substring(6, 8);
        let dd = new Date(fday);
        let ss = '日一二三四五六';
        picker.text('选择日期 ' + fday.substring(5) + ' 星期' + ss.charAt(dd.getDay()));
    }
    picker.click(function() {
        if (! window.dpFS) {
            window.dpFS = new TradeDatePicker();
        }
        window.dpFS.curSelDate = fday;
        window.dpFS.removeListener('select');
        window.dpFS.addListener('select', function(evt) {
            params.day = evt.date;
            window.location.href = paramsToUrl(params);
        });
        window.dpFS.openFor(this);
    });
    let wrap = $('<div style="height: 80px; background-color: #d0d0d0; margin-bottom: 5px;"> </div>');
    let w1 = $('<div style="float:left; border-right: solid 2px #999; height: 100%; padding-right:10px;"> </div>');
    w1.append(picker);
    let w2 = $('<div style="float:left; height: 100%; border-right: solid 2px #999; padding: 0 5px;"> </div>');
    let ps = $('<button val="5" name="period">活跃周期(5&nbsp;&nbsp;日) </button> <button val="10" name="period">活跃周期(10日) </button> <br/> <button val="20" name="period">活跃周期(20日) </button> <button val="30" name="period">活跃周期(30日) </button>');
    w2.append(ps);
    w2.children('button').css('margin-left', '10px');
    w2.children('button').click(function() {
        let period = $(this).attr('val');
        params.period = period;
        window.location.href = paramsToUrl(params);
    });
    w2.find(`button[val=${period}]`).css({'color-': '#f00', 'border-color': 'green'});

    pageInfo.groupsMgr = new ZsRelatedManager();
    let w3 = pageInfo.groupsMgr.create(code, day);
    if (w3) w3.css({'float': 'left'});
    wrap.insertAfter('.plate-up-list');
    wrap.append(w1).append(w2).append(w3);

    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);
    $('.top-ad').remove();
}

function loadUI() {
	let tag = $('.toggle-nav-box > .toggle-nav-active').text().trim();
	if (tag == '股票池') tag = 'Stock';
	else if (tag == '产业链') tag = 'Industry';
	let data = window[tag + 'Data'];
	if (! data || !tag) {
		return;
	}
	$('.list-more-button').remove();
	let cnt = $('.toggle-nav-box').next();
	if (cnt.attr('name') == tag) {
		return;
	}
	if (! window[tag + '_StockTable']) {
        let hyzsRender = function(rowIdx, rowData, head, tdObj) {
            let val = rowData[head.name] || 0;
            if (val) val += ' C';
            else val = '';
            tdObj.text(val);
        }
        let hd = [
            {text: '标记', 'name': 'mark_color', width: 40, defined: true, sortable: true},
            {text: '股票/代码', 'name': 'code', width: 80},
            {text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
            {text: '活跃指数', 'name': '_snum_', width: 70, sortable: true, cellRender: hyzsRender},
            {text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
            {text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
            {text: '成交额', 'name': 'amount', width: 50, sortable: true, defined: true},
            {text: '流通市值', 'name': 'cmc', width: 70, sortable: true},
        ];
        if (getLocationParams('refThsCode')) {
            hd.push({text: '行业', 'name': 'hy', width: 250, sortable: true});
        } else {
            hd.push({text: '领涨次数', 'name': 'head_num', width: 70, sortable: true});
            // hd.append({text: '资金流向', 'name': 'fundflow', width: 90, sortable: true});
            hd.push({text: '简介', 'name': 'assoc_desc', width: 250});
        }
        hd.push({text: '分时图', 'name': 'fs', width: 300});
		let st = window[tag + '_StockTable'] = tag == 'Stock' ? new StockTable(hd) : new IndustryTable(hd);
		st.initStyle();
        let ps = getLocationParams();
        if (ps.day) st.setDay(ps.day);
		st.setData(data);
		st.buildUI();
	}
	let st = window[tag + '_StockTable'];
    cnt.empty();
    cnt.append(st.table);
    // cnt.find('.watch-table').replaceWith(st.table);
    cnt.attr('name', tag);
    window.st = st;
}

function getLocationParams(name = null) {
    let url = window.location.href;
    let params = {};
    if (url.indexOf('#') > 0)
        url = url.substring(0, url.indexOf('#'));
    let q = url.indexOf('?');
    if (q < 0) return params;
    let ps = url.substring(q + 1);
    for (let it of ps.split('&')) {
        let ks = it.split('=');
        params[ks[0]] = ks[1];
    }
    if (name) {
        return params[name];
    }
    return params;
}

function paramsToUrl(params) {
    let url = 'https://www.cls.cn/plate?'; //code=cls80079&day=&period=10
    let p = '';
    for (let k in params) {
        if (p) p += '&';
        p += k + '=' + params[k];
    }
    return url + p;
}

function loadStoks() {
    let params = getLocationParams();
    let code = params.refThsCode || params.code;
    let day = params.day || '';
    let period = params.period;
    if (! period) {
        return;
    }
    let url = `http://localhost:5665/plate/${code}?day=${day}&period=${period}`;
    $.ajax({
        url: url, type: 'GET',
        success: function(resp) {
            let sd = resp;
            window['StockData'] = sd;
        }
    });
    url = `http://localhost:5665/industry/${code}?day=${day}&period=${period}`;
    $.ajax({
        url: url, type: 'GET',
        success: function(resp) {
            let sd = resp;
            window['IndustryData'] = sd;
        }
    });
}

initPlatePage();
// loadStoksData();
// loadIndustryData();
loadStoks();
setInterval(function() {
	loadUI();
}, 1 * 1000);
