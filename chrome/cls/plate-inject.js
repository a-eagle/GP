let pageInfo = { tableColNum : 0 };
let thread = new Thread();
const ADD_WIDTH = 300;
var zsView = null;

function createTimeLineView(code, width, height) {
    width = width || ADD_WIDTH;
    height = height || 60;
    let view = new TimeLineView(width, height);
    //tlMgr.add(view);
    let day = getLocationParams('day');
    view.loadData(code, day);
    window.myview = view;
    return view;
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}

function loadRefThsCode(view, params) {
    let onLoadEnd = function(evt) {
        let zf = evt.src.zf;
        let span = $('.stock-detail > span:eq(1)');
        span.html('<label style="color:' + (zf > 0 ? 'red' : zf < 0 ? 'green' : '#000') + '">' + zf.toFixed(2) + '%' + '<label>');
    };
    view.addListener('LoadDataEnd', onLoadEnd);
    let span = $('.stock-detail > span:eq(0)');
    span.text('【' + params.refThsCode + ' ' + decodeURIComponent(params.refThsName || '') + '】');
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
    let view = createTimeLineView(code);
    if (params.refThsCode) {
        loadRefThsCode(view, params);
    }
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

    let picker = $('<button style="margin-left:30px;" >选择日期 </button>');
    if (day) {
        let mday = day.replaceAll('-', '');
        let fday = mday.substring(0, 4) + '-' + mday.substring(4, 6) + '-' + mday.substring(6, 8);
        let dd = new Date(fday);
        let ss = '日一二三四五六';
        picker.text('选择日期 ' + fday.substring(5) + ' 星期' + ss.charAt(dd.getDay()));
    }
    picker.click(function() {
        if (! window.dpFS) {
            window.dpFS = new TradeDatePicker();
        }
        window.dpFS.removeListener('select');
        window.dpFS.addListener('select', function(evt) {
            params.day = evt.date;
            window.location.href = paramsToUrl(params);
        });
        window.dpFS.openFor(this);
    });
    pdiv.append(ui).append(btn);
    pdiv.css('background-color', 'rgb(250, 250, 250)');
    let wrap = $('<div style="height: 50px; background-color: #d0d0d0; padding-top: 10px;"> </div>');
    let wp = $('<button val="5" name="period">活跃周期(5日) </button> <button val="10" name="period">活跃周期(10日) </button>  <button val="20" name="period">活跃周期(20日) </button> <button val="30" name="period">活跃周期(30日) </button>');
    wrap.append(picker).append(wp);
    wrap.insertAfter('.plate-up-list');
    wrap.children('button:gt(0)').css('margin-left', '10px').css('height', '25px');
    wrap.children('button[name=period]').click(function() {
        let period = $(this).attr('val');
        params.period = period;
        window.location.href = paramsToUrl(params);
    });
    wrap.find(`button[val=${period}]`).css({'color-': '#f00', 'border-color': 'green'})

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
