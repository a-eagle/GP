var pageInfo = {
	anchros: null,
	anchrosView: null,
	maxTradeDaysOfAnchors: 10,
	degrees_fs: {}, //分时degree {day: val, ...}
	degrees_n: null, //日期degree
	curDay: null,
	sh000001: null, sz399001: null,
	tradeDays: null, // ['YYYY-MM-DD', ...]
	lastTradeDay: null,
	zdfb: {}, // {day: val, ...} 涨跌分布
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

function formatDay(date) {
	let y = date.getFullYear();
	let m = date.getMonth() + 1;
	let d = date.getDate();
	if (m < 10) m = '0' + m;
	if (d < 10) d = '0' + d;
	return y + '-' + m + '-' + d;
}

function _doHook(response) {
	console.log(response)

	let data = response.response;
	let len = response.headers['content-length'];
	let url = response.config.url;
	if (url.indexOf('/quote/index/up_down_analysis') >= 0) {
		let idx = url.indexOf('type=');
		let type = url.substring(idx + 5, url.indexOf('&', idx + 5));
		if (type == 'up_pool') type = 'ZT';
		else if (type == 'continuous_up_pool') type = 'LB';
		else if (type == 'up_open_pool') type = 'ZB';
		else if (type == 'down_pool') type = 'DT';
		adjustZTInfo(response, type);
		//console.log(response, type);
	}
	if (url.indexOf('/v3/transaction/anchor') >= 0) {
		let idx = url.indexOf('cdate=');
		let cday = url.substring(idx + 6, idx + 6 + 10);
		adjustAnchors(response, cday);
		//loadTimeDegree();
		loadDegrees_n();
		console.log('/v3/transaction/anchor');
	}
	//console.log(response);
}

function adjustZTInfo(response, type) {
	let body = response.response;
	let json = JSON.parse(body);
	//console.log('[Before]', json);
	let rs = [];
	for (i in json.data) {
		let item = json.data[i];
		if (item.is_st != 0)
			continue
		rs.push(item);
	}
	json.data = rs;
	response.response = JSON.stringify(json);
	//console.log('[After]', json);
	//window.postMessage({cmd: 'ZT-INFO', data: rs}, '*');
	window[type + '_Infos'] = rs;
	/*
	if (type == 'ZT') {
		let text = '涨停&nbsp;' + rs.length;
		if ($('#real-zt-div').length == 0) {
			$('.event-querydate-box > div:eq(1)').hide();
			let div = $('<div id="real-zt-div" style="float:left; font-size:20px; color: #ad1078; padding-left:20px;" > ' + text + '</div>');
			$('.event-querydate-box').append(div);
		} else {
			$('#real-zt-div').html(text);
		}
	}
	*/
}

function adjustAnchors(response, cday) {
	//console.log('[adjustAnchors] cday=', cday);
	pageInfo.curDay = cday;
	if (! pageInfo.anchros) {
		return;
	}
	let body = response.response;
	let json = JSON.parse(body);
	//console.log(pageInfo.anchros);
	let anchrosCP = {};
	let anchrosDays = [];
	let lastDay = pageInfo.anchros[0][0].c_time.substring(0, 10);
	if (json.data.length > 0) {
		if (cday > lastDay) {
			pageInfo.anchros.unshift(json.data);
		} else if (cday == lastDay) {
			pageInfo.anchros[0] = json.data;
		}
	}

	for (let i = 0, num = 0; i < pageInfo.anchros.length && num < pageInfo.maxTradeDaysOfAnchors; i++) {
		let day = pageInfo.anchros[i][0].c_time.substring(0, 10);
		if (day > cday)
			continue;
		anchrosDays.push(day);
		++num;
		for (let j = 0; j < pageInfo.anchros[i].length; j++) {
			let an = pageInfo.anchros[i][j];
			let key = an.symbol_code + '#' + an.float;
			if (anchrosCP[key]) {
				anchrosCP[key].items.push(an);
			} else {
				anchrosCP[key] = {name: an.symbol_name, code: an.symbol_code, num: 0, tag: an.float, items: [an]};
			}
			anchrosCP[key].num++;
		}
	}

	for (let i = 0; i < json.data.length; i++) {
		let an = json.data[i];
		let key = an.symbol_code + '#' + an.float;
		let num = anchrosCP[key].num;
		an.symbol_name += '' + num + '';
	}
	anchrosDays.push(cday);
	window.anchrosCP = anchrosCP;
	window.anchrosDays = anchrosDays;
	response.response = JSON.stringify(json);
	sumGroup(anchrosCP);
}

function sumGroup(anchrosCP) {
	let arr = [];
	for (let k in anchrosCP) {
		arr.push(anchrosCP[k]);
	}
	arr.sort(function(a, b) {return b.num - a.num});
	let hots = null;
	if ($('#hots').length == 0) {
		hots = $('<div id="hots" class="p-r m-b-20  b-c-222 b-t-2"></div>');
		hots.insertAfter($('.event-chart-box').parent());
	} else {
		hots = $('#hots');
		hots.empty();
	}
	let table = $("<table> </table>");
	let tr = null;
	let ROW_NUM = 4, COL_NUM = 7;
	let NUM = ROW_NUM * COL_NUM;
	for (let i = 0; i < NUM && i < arr.length; i++) {
		let item = arr[i];
		if (i % COL_NUM == 0) {
			tr = $('<tr> </tr>');
			table.append(tr);
		}
		let a = '<a href="https://www.cls.cn/plate?code=' + item.code + '" target=_blank> ' + item.name + '&nbsp;&nbsp;' + item.num + '&nbsp;&nbsp;</a>';
		let s = '<span class="arrow" code="' + item.code + '">  </span>';
		tr.append($('<td class="' + item.tag + '"> ' + a + s + ' </td>'));
	}
	hots.append(table);
	table.find('.arrow').click(openChart);
}

function getAnchrosByCode(code, maxDay, daysNum) {
	if (!maxDay || !pageInfo.anchros) {
		return null;
	}
	let rs = {up: [], down: [], days: [], allDays: []};
	for (let i = 0, num = 0; i < pageInfo.anchros.length && num < daysNum; i++) {
		let day = pageInfo.anchros[i][0].c_time.substring(0, 10);
		rs.allDays.push(day);
		if (day > maxDay)
			continue;
		++num;
		rs.days.push(day);
		for (let j = 0; j < pageInfo.anchros[i].length; j++) {
			let an = pageInfo.anchros[i][j];
			if (an.symbol_code == code) {
				rs[an.float].push(an);
			}
		}
	}
	return rs;
}

function openPopup() {
	let thiz = $(this);
	let code = thiz.attr('code');
	console.log(code);
	let up = window.anchrosCP[code + '#up'];
	let down = window.anchrosCP[code + '#down'];
	let arr = [];
	for (let i = 0; up && i < up.items.length; i++) {
		arr.push(up.items[i]);
	}
	for (let i = 0; down && i < down.items.length; i++) {
		arr.push(down.items[i]);
	}
	arr.sort(function(a, b) {return b.c_time.localeCompare(a.c_time)});
	let ui = $('<div class="content"> </div>');
	for (let i = 0; i < arr.length; i++) {
		let ctime = arr[i].c_time;
		let day = ctime.substring(0, 10);
		let time = ctime.substring(11);
		let d = new Date(day);
		let week = d.getDay();
		week = '一二三四五'.charAt(week - 1);
		day = '<span width="100px" style="margin-left:10px;" >' + day + '<span>';
		time = '<span style="margin-left:10px;"> ' + time + '</span>';
		let tag = '';
		if (arr[i].float == 'down') {
			tag = '&nbsp;&nbsp;跌';
		}
		ui.append($('<p style="' + arr[i].float + '">' + week + day + time + tag + ' </p>'));
	}
	$('.popup-container').empty();
	$('.popup-container').css('display', 'block');
	$('.popup-container').append(ui);
	let tdRc = thiz.parent().get(0).getBoundingClientRect();
	ui.css({
		left: tdRc.left,
		top: tdRc.bottom
	});
}

function openChart() {
	let thiz = $(this);
	let code = thiz.attr('code');
	console.log(code);
	let rs = getAnchrosByCode(code, pageInfo.curDay, 20);
	if (! rs) {
		return;
	}
	let up = rs.up;
	let down = rs.down;

	function getDays() {
		rs.days.sort();
		return rs.days;
	}
	function simpleDays(days) {
		let rs = [];
		for (let i = 0; i < days.length; i++) {
			rs.push(days[i].substring(5));
		}
		return rs;
	}
	function getDatas(ud) {
		let rs = [];
		let ds = getDays();
		for (let i = 0; i < ds.length; i++) {
			rs.push(0);
		}
		if (! ud) {
			return rs;
		}
		for (let i = 0; i < ds.length; i++) {
			let num = 0;
			for (let j = 0; j < ud.length; ++j) {
				let day = ud[j].c_time.substring(0, 10);
				if (day <= ds[i]) {
					num++;
				}
			}
			rs[i] = num;
		}
		return rs;
	}
	let upset = getDatas(up);
	let downset = getDatas(down);
	function skipped(ctx, set, val) {
		if (set[ctx.p0DataIndex] == set[ctx.p1DataIndex]) {
			return val;
		}
		return undefined;
	}
	function ss(set) {
		let rs = {
			borderColor: ctx => skipped(ctx,  set, 'rgb(0,0,0,0.2)'),
			borderDash: ctx => skipped(ctx, set, [3, 3])
		}
		return rs;
	}
	
	let cdata = {
		labels: simpleDays(getDays()),
		datasets: [
			{label: 'UP', data: upset, fill: false, borderColor: '#FF3333', segment: ss(upset), spanGaps: true},
			{label: 'DOWN', data: downset, fill: false, borderColor: '#33ff33', segment: ss(downset), spanGaps: true},
		],
	};
	let ui = $('<div class="canvas-wrap"> </div>');
	let canvas = $('<canvas> </canvas> ');
	$('.popup-container').empty();
	$('.popup-container').css('display', 'block');
	$('.popup-container').append(ui);
	let tdRc = thiz.parent().get(0).getBoundingClientRect();
	ui.css({left: tdRc.left, top: tdRc.bottom});
	ui.append(canvas);
	canvas.width(ui.width());
	canvas.height(ui.height());
	canvas.attr('day', pageInfo.curDay);
	new Chart(canvas.get(0), {type: 'line', data: cdata, options: {}});
}

function hook_proxy() {
	ah.proxy({
		onRequest:  function(config, handler) {
			// console.log('Hook request ->', config);
			handler.next(config)
		},
		
		onError: function(err, handler) {
			handler.next(err);
		},
		
		onResponse:function(response, handler) {
			_doHook(response);
			handler.next(response);
		},
	});
}

//hook_proxy();

function updateDegree(d) {
	let canvas = $('#hots_canvas');
	if (canvas.length == 0) {
		setTimeout(function() {updateDegree(d);}, 2000);
		return;
	}
	canvas = canvas.get(0);
	let xl = [];
	let xv = [];
	let v50 = [];
	for (let i = 0; d && i < d.length; i++) {
		if (d[i].time.charAt(4) == '0') { // d[i].time <= '10:00' || 
			xl.push(d[i].time);
			xv.push(d[i].degree);
			v50.push(50);
		}
	}
	function ss(set) {
		let rs = {
			borderColor: ctx => {if (set[ctx.p1DataIndex] < 50) return '#8EC8B4'; return undefined; },
			// borderDash: ctx => skipped(ctx, set, [3, 3])
		}
		return rs;
	}
	let cdata = {
		labels: xl,
		datasets: [
			{label: 'Degree', data: xv, fill: false, borderColor: '#FF3333', segment: ss(xv), spanGaps: true},
			//{label: '50', data: v50, fill: false, borderColor: '#505050'},
		],
	};
	if (! window.hotChart) {
		let cc = $('.my-info-item');
		$(canvas).attr('width', cc.width());
		$(canvas).attr('height', cc.height());
		window.hotChart = new Chart(canvas, {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}});
		window.hotChart.resize(cc.width(), cc.height());
	} else {
		window.hotChart.data = cdata;
		window.hotChart.update();
	}
}

function updateDegree_n_UI() {
	let table = $('#hots_table');
	if (table.length == 0 || !pageInfo.degrees_n) {
		setTimeout(function() {updateDegree_n_UI();}, 2000);
		return;
	}
	table.empty();
	let datas = [];
	for (let i = 0; i < pageInfo.degrees_n.length; i++) {
		let day = pageInfo.degrees_n[i].day;
		pageInfo.degrees_n[i].amount = '';
		if (pageInfo.sh000001 && pageInfo.sz399001) {
			let am = pageInfo.sh000001[day].amount + pageInfo.sz399001[day].amount;
			pageInfo.degrees_n[i].amount = am.toFixed(2);
		}
		datas.push(pageInfo.degrees_n[i]);
	}
	
	let cols = ['sday', 'degree', 'amount'];
	let colsDesc = ['', '热度', '成交额'];
	for (let c = 0; c < cols.length; c++) {
		let tr = $('<tr> </tr>');
		tr.append($('<th>' + colsDesc[c] + '</th>'));
		let lastMonth = '';
		for (let i = 0; i < datas.length; i++) {
			let v = datas[i][cols[c]];
			let clazz = '';
			let title = '';
			if (cols[c] == 'sday') {
				let m = v.substring(0, 2);
				if (m != lastMonth) {
					lastMonth = m;
				} else {
					v = v.substring(2);
				}
			} else if (cols[c] == 'degree') {
				clazz = c == 0 ? '' : (v >= 50 ? 'red' : 'green');
				let fb = datas[i]['fb'];
				if (fb) {
					fb = JSON.parse(fb);
					title = "涨停:  " + fb.zt + "\t上涨:  "+fb.up+"  \t涨幅>8%:  "+(fb.up_8 + fb.up_10)+" \n跌停:  "+fb.dt+"\t下跌:  "+fb.down+"  \t跌幅>8%:  " + (fb.down_8 + fb.down_10);
				}
			} else if (cols[c] == 'amount') {
				title = v + '万亿';
			}
			let tag = c == 0 ? 'th' : 'td';
			let td = $('<' + tag + ' class="' + clazz  + '" title=" ' + title + '" colidx="' + i + '">' + v + '</' + tag + '>');
			td.data('val', datas[i]);
			tr.append(td);
		}
		table.append(tr);
	}
	function inFunction() {
		let idx = $(this).attr('colidx');
		let table = $('.my-info-item > table');
		table.find('td[colidx=' + idx + ']').addClass('selcol');
	}
	function outFunction() {
		let idx = $(this).attr('colidx');
		let table = $('.my-info-item > table');
		table.find('td[colidx=' + idx + ']').removeClass('selcol');
	}
	function onClick() {
		let data = $(this).data('val');
		let tds = $('#zdfb_table td');
		let dayTh = $('#zdfb_table *[v=day]');
		dayTh.text(data.day);
		let udd = {up:'', down:'', up_8: '', up_10: '', zt:'', dt:'', down_8:'', down_10:''};
		if (data.fb)
			udd = JSON.parse(data.fb);
		tds.eq(0).text(udd.up);
		tds.eq(1).text(udd.zt);
		tds.eq(2).text(udd.up_8 + udd.up_10);
		tds.eq(3).text(udd.down);
		tds.eq(4).text(udd.dt);
		tds.eq(5).text(udd.down_8 + udd.down_10);
		loadDegree_fs(data.day);
	}
	table.find('td, th').hover(inFunction, outFunction);
	table.find('td').click(onClick);
}

function wrapAnchor(name) {
	if (! pageInfo.anchros) {
		return name;
	}
	let num = pageInfo.anchros[name + '#up'];
	if (! num) {
		return name;
	}
	return name + num;
}

function initUI() {
	if (!pageInfo.degrees_n || !pageInfo.sh000001 || !pageInfo.sz399001 || !pageInfo.tradeDays || $('.watch-content-left > div').length < 7) {
		setTimeout(initUI, 1000);
		return;
	}
	let style = document.createElement('style');
	let css = "#change-trade-days .sel {color: #ff00ff;  border: 1px solid #ff00ff;} \n\
			 #hots .up {background-color: #FFD8D8;} \n\
			 #hots .down {background-color: #A0F1DC;} \n\
			 #hots table {border-collapse: separate; border-spacing: 15px 10px;} \n\
			 .popup-container {z-index: 81100; display: none;  position: fixed; padding: 0; outline: 0; left:0px; top: 0px;width:100%;height:100%;}\n\
			 .popup-container .content {position:absolute; background-color: #fcfcfc; border: solid 1px #d0d0d0;} \n\
			 .popup-container p {padding: 0 20px 0 10px; } \n\
			 .popup-container p:hover {background-color: #f0f0f0; } \n\
			 .popup-container .canvas-wrap {position:absolute; width: 800px; height: 250px; background-color: #fcfcfc; border: solid 1px #aaa;} \n\
			 #hots .arrow {float:right; width:15px; text-align:center; border-left:1px solid #c0c0c0; background-color:#c0c0c0; width:15px; height:25px;} \n\
			 .my-info-item {border-bottom: solid 1px #222; padding-bottom: 10px; padding-top: 5px;} \n\
			 #hots_canvas {height: 130px; width: 100%;} \n\
			 .my-info-item > table { border-collapse: collapse; border: 1px solid #ddd; width:100%; text-align: center; cursor:hander; } \n\
			 .my-info-item > table th {border: 1px solid #ddd; background-color: #ECECEC; height: 30px; font-weight: normal; color: #6A6B70;} \n\
			 .my-info-item > table td {border: 1px solid #ddd;} \n\
			 .my-info-item .red {color: #990000;} \n\
			 .my-info-item .green {color: #009900;} \n\
			 .my-info-item .selcol {background-color: #EEE9E9;} \n\
			 #zdfb_table td {width:120px;} \n\
			 .w-1200 {width: 1400px;} \n\
			 .watch-content-left {width: 1090px;} \n\
			";
	style.appendChild(document.createTextNode(css));
	document.head.appendChild(style);
	let popup = $('<div class="popup-container"> </div>');
	$(document.body).append(popup);
	popup.click(function() {$(this).css('display', 'none')});
	popup.on('mousewheel', function(event) {event.preventDefault();});
	$('.top-ad').remove();
	let group = $('<div> </div>');
	let md1 = $('<div class="my-info-item p-r b-c-222" > <table id="hots_table"> </table> </div>');
	let md2 = $('<div class="my-info-item p-r b-c-222" > <canvas id="hots_canvas"> </canvas> </div>');
	let md3 = $('<div class="my-info-item p-r b-c-222" style="height: 70px;"  > <table id="zdfb_table">'+
				"<tr class='red'> <th> 日期 </th> <th> 上涨数 </th> <td> </td>  <th> 涨停 </th> <td> </td> <th> 涨幅>8% </th> <td> </td> </tr>" +
				"<tr class='green'> <th v='day'> </th>  <th> 下跌数 </th> <td> </td>  <th> 跌停 </th> <td> </td> <th> 跌幅>8% </th> <td> </td> </tr>" +
				' </table>  </div>');
	let md4 = $('<div class="my-info-item p-r b-c-222" style="height: 400px;"> <canvas id="fs_canvas" > </canvas> </div>');
	group.append(md1).append(md2).append(md3).append(md4);
	$('.watch-content-left > div:gt(1)').hide();
	group.insertAfter($('.watch-chart-box'));
	pageInfo.anchrosView = new AnchrosView($('#fs_canvas').get(0));
	pageInfo.anchrosView.loadData(pageInfo.lastTradeDay);
}

// 涨跌分布
function loadNewestZdfb() {
	$.ajax({
	 	url: 'https://x-quote.cls.cn/quote/index/home?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737',
	 	success: function(resp) {
			if (resp.code != 200 || !resp.data.up_down_dis.status)
				return;
			let udd = resp.data.up_down_dis;
			let lastDay = pageInfo.lastTradeDay;
			udd.up = udd.rise_num;
			udd.down = udd.fall_num;
			udd.zt = udd.up_num;
			udd.dt = udd.down_num;
			pageInfo.zdfb[lastDay] = udd;
	 	}
	});
}

// day = YYYY-MM-DD
function loadDegree_fs(day) {
	$.ajax({
		url: 'http://localhost:5665/get-time-degree?day=' + day,
		success: function(resp) {
			pageInfo.degrees_fs[day] = resp;
			updateDegree(resp);
		}
	});
}

// load trade days
function loadTradeDays(async) {
	if (async == undefined)
		async = true;
	$.ajax({url: 'http://localhost:5665/get-trade-days', async: async, success: function(data) {
		pageInfo.lastTradeDay = data[data.length - 1];
		if (! pageInfo.curDay) {
			pageInfo.curDay = pageInfo.lastTradeDay;
		}
		pageInfo.tradeDays = data;
	}});
}

function initRequest() {
	// 两市成交额
	function cb(data) {
		let rs = {'days': []};
		for (let i = 0; i < data.length; i++) {
			let day = String(data[i].date);
			day = day.substring(0, 4) + '-' + day.substring(4, 6) + '-' + day.substring(6);
			data[i].amount = data[i].business_balance / 1000000000000; // 万亿
			rs[day] = data[i];
			rs['days'].push(day);
		}
		rs['days'].sort();
		return rs;
	}
	let cu = new ClsUrl();
	cu.loadKline('sh000001', 200, 'DAY', function(data) {
		pageInfo.sh000001 = cb(data);
	});
	cu.loadKline('sz399001', 200, 'DAY', function(data) {
		pageInfo.sz399001 = cb(data);; // business_balance
	});
	loadTradeDays(false);
	loadDegree_fs(pageInfo.lastTradeDay);
	loadNewestZdfb();
	loadDegrees_n();
	setInterval(loadTradeDays, 1000 * 60 * 30); // 30 minutes
	setInterval(function() {
		loadDegree_fs(pageInfo.lastTradeDay);
		loadNewestZdfb();
	}, 60 * 1000);
	window.addEventListener("message", function(evt) {
		if (evt.data && evt.data.cmd == 'GET_ANCHORS_CB') {
			pageInfo.anchros = evt.data.data;
		}
	}, false);
	window.postMessage({cmd: 'GET_ANCHORS', data: {lastDay: new Date(), traceDaysNum: 60}}, '*');
}

function loadDegrees_n() {
	let day = pageInfo.lastTradeDay;
	let date = new Date(day);
	//let dx = date.setDate(date.getDate() - 45);
	let dx = date.setMonth(date.getMonth() - 1);
	date = new Date(dx);
	let fday = formatDay(date);
	let sql = "select day, 综合强度 as degree, substr(day, 6) as sday, fb from CLS_SCQX where day >= '" + fday + "' and day <= '" + day + "'";
	$.ajax({
		url: 'http://localhost:5665/query-by-sql/tck',
		data: {'sql': sql},
		success: function(resp) {
			pageInfo.degrees_n = resp;
			updateDegree_n_UI();
		}
	});
}

function loadZTUI() {
	let tag = $('.toggle-nav-box > .toggle-nav-active').text().trim();
	let data = null;
	if (tag == '涨停池') tag = 'ZT';
	else if (tag == '连板池') tag = 'LB';
	else if (tag == '炸板池') tag = 'ZB';
	else if (tag == '跌停池') tag = 'DT';
	data = window[tag + '_Infos'];
	if (! data || !tag) {
		return;
	}
	$('.list-more-button').remove();
	let cnt = $('.toggle-nav-box').next();
	if (cnt.attr('name') == tag) {
		return;
	}
	let newCnt = $('<div class="" name="' + tag + '"> </div>');
	if (! window[tag + '_StockTable']) {
		let hd = null;
		if (tag == 'ZT' || tag == 'LB') {
			hd = [
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '涨跌幅', 'name': 'change', width: 70, sortable: true},
				{text: '连板', 'name': 'limit_up_days', width: 50, sortable: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true},
				{text: '动因', 'name': 'up_reason', width: 250, sortable: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else {
			hd = [
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '涨跌幅', 'name': 'change', width: 70, sortable: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		}
		let st = window[tag + '_StockTable'] = new StockTable(hd);
		st.initStyle();
		st.setData(data);
		st.buildUI();
	}
	let st = window[tag + '_StockTable'];
	newCnt.append(st.table);
	cnt.replaceWith(newCnt);
}

initRequest();
setTimeout(initUI, 3000);
