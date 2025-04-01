let pageInfo = { tableColNum : 0 };
let thread = new Thread();
const ADD_WIDTH = 300;
var zsView = null;

function createTimeLineView(code, width, height) {
    width = width || ADD_WIDTH;
    height = height || 60;
    let view = new TimeLineView(width, height);
    //tlMgr.add(view);
    view.loadData(code);
    return view;
}

function extendWidth(obj, aw) {
    let w = obj.width();
    w += aw;
    obj.css('width', '' + w + 'px');
}


function openKLineDialog_chrome(code) {
    if (! klineDialog) {
        klineDialog = $('<dialog class="kline">  </dialog>');
        $(document.body).append(klineDialog);
        klineDialog.get(0).onclick = function(event) {
            if (event.target.tagName.toLowerCase() == "dialog") this.close();
        };
        klineDialog.get(0).ondblclick = function(event) {
            this.close();
        };
    } else {
        klineDialog.empty();
    }
    let btns = $('<p style="height:30px;"> <button z="DAY">日线</button> <button z="WEEK">周线</button> <button z="MONTH">月线</button>');
    klineDialog.append(btns);
    btns.find('button').click(function() {
        let n = $(this).attr('z');
        let canvas = klineDialog.find('canvas');
        for (let i = 0; i < canvas.length; i++) {
            if (canvas.eq(i).attr('z') == n) {
                canvas.eq(i).show();
            } else {
                canvas.eq(i).hide();
            }
        }
    });

    let ks = ['DAY', 'WEEK', 'MONTH'];
    for (let i = 0; i < ks.length; i++) {
        let kline = new KLineView(1500, 650);
        kline.loadData(code, ks[i]);
        if (i != 0)
            $(kline.canvas).hide();
        $(kline.canvas).attr('z', ks[i]);
        klineDialog.append(kline.canvas);
    }
    klineDialog.get(0).showModal();
}

function initPlatePage() {
    let span = $('.stock-detail span:first');
    if (span.length == 0) {
        setTimeout(initPlatePage, 1000);
        return;
    }

    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let view = createTimeLineView(code);
    let ui = $(view.canvas);
    ui.css('margin-left', '50px').css('background-color', '#f8f8f8');
    ui.insertAfter('.stock-detail > span:eq(1)');
    let btn = $('<button > 打开链接 </button>');
    btn.click(function() {
        let url = "https://www.cls.cn/stock?code=" + code;
        window.open(url, '_blank');
    });
    btn.insertAfter(ui);
    //let txt = span.text();
    //span.html('<a href="https://www.cls.cn/stock?code=' + code + '" target=_blank>' + txt + ' </a> ');

    extendWidth($('div.w-1200'), ADD_WIDTH);
    extendWidth($('div.content-main-box div.watch-content-left'), ADD_WIDTH);
    $('.top-ad').remove();
}

function loadStoksData() {
    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let params = 'app=CailianpressWeb&os=web&rever=1&secu_code=' + code + '&sv=8.4.6&way=last_px';
    params = new ClsUrl().signParams(params);
    let url = 'https://x-quote.cls.cn/web_quote/plate/stocks?' + params;
    $.ajax({
        url: url, type: 'GET',
        success: function(resp) {
            let sd = resp.data.stocks;
            window['StockData'] = sd;
        }
    });
}

function loadIndustryData() {
    let lh = window.location.href;
    let TAG = 'https://www.cls.cn/plate?code=';
    let code = lh.substring(TAG.length);
    let params = 'app=CailianpressWeb&os=web&rever=1&secu_code=' + code + '&sv=8.4.6&way=last_px';
    params = new ClsUrl().signParams(params);
    let url = 'https://x-quote.cls.cn/web_quote/plate/industry?' + params;
    $.ajax({
        url: url, type: 'GET',
        success: function(resp) {
            let sd = resp.data;
            window['IndustryData'] = sd;
        }
    });
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
        let hd = [
            {text: '股票/代码', 'name': 'code', width: 80},
            {text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
            {text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
            {text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
            {text: '领涨次数', 'name': 'head_num', width: 70, sortable: true},
            {text: '流通市值', 'name': 'cmc', width: 70, sortable: true},
            {text: '资金流向', 'name': 'fundflow', width: 90, sortable: true},
            {text: '简介', 'name': 'assoc_desc', width: 250},
            {text: '分时图', 'name': 'fs', width: 300},
        ];
		let st = window[tag + '_StockTable'] = tag == 'Stock' ? new StockTable(hd) : new IndustryTable(hd);
		st.initStyle();
		st.setData(data);
		st.buildUI();
	}
	let st = window[tag + '_StockTable'];
    cnt.find('.watch-table').replaceWith(st.table);
    cnt.attr('name', tag);
    window.st = st;
}

initPlatePage();
loadStoksData();
loadIndustryData();
setInterval(function() {
	loadUI();
}, 1 * 1000);
