var anchros = null;
var maxTradeDays = 10;
var degrees = null;

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

function _doHook(response) {
	let data = response.response;
	let len = response.headers['content-length'];
	let url = response.config.url;
	if (url.indexOf('/quote/index/up_down_analysis') >= 0) {
		adjustZTInfo(response);
	}
	if (url.indexOf('/v3/transaction/anchor') >= 0) {
		let idx = url.indexOf('cdate=');
		let cday = url.substring(idx + 6, idx + 6 + 10);
		adjustAnchors(response, cday);
		loadDegree();
	}
}

function adjustZTInfo(response) {
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
	window['zt-info'] = rs;

	let text = '涨停&nbsp;' + rs.length;
	if ($('#real-zt-div').length == 0) {
		let div = $('<div id="real-zt-div" style="float:left; font-size:20px; color: #ad1078; padding-left:20px;" > ' + text + '</div>');
		$('.event-querydate-box').append(div);
	} else {
		$('#real-zt-div').html(text);
	}
}

function adjustAnchors(response, cday) {
	//console.log('[adjustAnchors] cday=', cday);
	if (! anchros) {
		return;
	}
	let body = response.response;
	let json = JSON.parse(body);
	//console.log(anchros);
	let anchrosCP = {};
	let anchrosDays = [];
	for (let i = 0, num = 0; i < anchros.length && num < maxTradeDays - 1; i++) {
		let day = anchros[i][0].c_time.substring(0, 10);
		if (day >= cday)
			continue;
		anchrosDays.push(day);
		++num;
		for (let j = 0; j < anchros[i].length; j++) {
			let an = anchros[i][j];
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
		if (! anchrosCP[key]) {
			anchrosCP[key] = {name: an.symbol_name, code: an.symbol_code, num: 0, tag: an.float, items: [an]};
		} else {
			anchrosCP[key].items.push(an);
		}
		let num = anchrosCP[key].num;
		num += 1;
		an.symbol_name += '' + num + '';
		anchrosCP[key].num = num;
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
	let ROW_NUM = 3, COL_NUM = 6;
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
	let up = window.anchrosCP[code + '#up'];
	let down = window.anchrosCP[code + '#down'];
	let arr = [];
	for (let i = 0; up && i < up.items.length; i++) {
		arr.push(up.items[i]);
	}
	for (let i = 0; down && i < down.items.length; i++) {
		arr.push(down.items[i]);
	}
	arr.sort(function(a, b) {return a.c_time.localeCompare(b.c_time)});
	
	function getDays() {
		window.anchrosDays.sort();
		return window.anchrosDays;
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
		ud = ud.items;
		
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

hook_proxy();

window.postMessage({cmd: 'GET_ANCHORS', data: {lastDay: new Date(), traceDaysNum: 30}}, '*');
window.addEventListener("message", function(evt) {
	if (evt.data && evt.data.cmd == 'GET_ANCHORS_CB') {
		anchros = evt.data.data;
		//console.log(anchros);
	} else if (evt.data && evt.data.cmd == 'GET_DEGREE_CB') {
		let dg = evt.data.data;
		updateDegree(dg);
	}
}, false);

function updateDegree(d) {
	let canvas = $('.my-degree > canvas').get(0);
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
	if (! window.chart) {
		window.chart = new Chart(canvas, {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}});
		let cc = $('.my-degree');
		window.chart.resize(cc.width(), cc.height());
	} else {
		window.chart.data = cdata;
		window.chart.update();
	}
}

function wrapAnchor(name) {
	if (! anchros) {
		return name;
	}
	let num = anchros[name + '#up'];
	if (! num) {
		return name;
	}
	return name + num;
}

function initUI() {
	if ($('#real-zt-div').length == 0) {
		setTimeout(initUI, 500);
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
			 .popup-container .canvas-wrap {position:absolute; width: 400px; height: 200px; background-color: #fcfcfc; border: solid 1px #aaa;} \n\
			 #hots .arrow {float:right; width:15px; text-align:center; border-left:1px solid #c0c0c0; background-color:#c0c0c0; width:15px; height:25px;} \n\
			 .my-degree {height: 130px; border-bottom: solid 1px #222; margin-bottom: 10px;} \n\
			 .my-degree > canvasx {height: 130px; width: 890px;} \n\
			";
	style.appendChild(document.createTextNode(css));
	document.head.appendChild(style);
	let div = $('<div id="change-trade-days" style="padding-left:30px; font-size:15px; float:left; "> 交易日期：<button  val="5" >5日</button> <button class="sel" val="10">10日</button> </div>');
	$('.event-querydate-box').append(div);
	div.find('button').click(function() {
		div.find('button').removeClass('sel');
		$(this).addClass('sel');
		maxTradeDays = parseInt($(this).attr('val'));
	});
	let popup = $('<div class="popup-container"> </div>');
	$(document.body).append(popup);
	popup.click(function() {$(this).css('display', 'none')});
	popup.on('mousewheel', function(event) {event.preventDefault();});
	$('.top-ad').remove();
	let md = $('<div class="my-degree p-r b-c-222" > <canvas width="890" height="130"> </canvas> </div>');
	md.insertAfter($('.watch-chart-box'));
	loadDegree();
}

function loadDegree() {
	let day = $('.event-querydate-selected').text().trim();
	day = day.replaceAll('/', '-');
	window.postMessage({cmd: 'GET_DEGREE', data: day}, '*');
}

setTimeout(initUI, 500);

setInterval(function() {
	loadDegree();
}, 60 * 1000);
/*
var _can2DProto = CanvasRenderingContext2D.prototype;
var _old_can2d_ft = _can2DProto.fillText;
var ens = /^[-+.0-9%/:]+$/;
_can2DProto.fillText = function(txt, x, y) {
	//if (! ens.test(txt))
	//	txt = wrapAnchor(txt);
	_old_can2d_ft.call(this, txt, x, y);
}

*/