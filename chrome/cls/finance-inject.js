var anchros = null;
var maxTradeDays = 10;

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
	for (let i = 0, num = 0; i < anchros.length && num < maxTradeDays; i++) {
		if (anchros[i][0].c_time.substring(0, 10) >= cday)
			continue;
		++num;
		for (let j = 0; j < anchros[i].length; j++) {
			let an = anchros[i][j];
			let key = an.symbol_code + '#' + an.float;
			if (anchrosCP[key]) anchrosCP[key].num++;
			else anchrosCP[key] = {name: an.symbol_name, code: an.symbol_code, num: 1, 'tag': an.float};
		}
	}

	for (let i = 0; i < json.data.length; i++) {
		let key = json.data[i].symbol_code + '#' + json.data[i].float;
		if (! anchrosCP[key])
			anchrosCP[key] = {name: json.data[i].symbol_name, code: json.data[i].symbol_code, num: 1, 'tag': json.data[i].float};
		let num = anchrosCP[key].num;
		num += 1;
		json.data[i].symbol_name += '' + num + '';
		anchrosCP[key].num = num;
	}
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
	let NUM = 12;
	for (let i = 0; i < NUM; i++) {
		let item = arr[i];
		if (i % (NUM / 2) == 0) {
			tr = $('<tr> </tr>');
			table.append(tr);
		}
		let a = '<a href="https://www.cls.cn/plate?code=' + item.code + '" target=_blank> ' + item.name + '&nbsp;&nbsp;' + item.num + '</a>';
		tr.append($('<td class="' + item.tag + '"> ' + a + ' </td>'));
	}
	hots.append(table);
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
		console.log(anchros);
	}
}, false);

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
}

setTimeout(initUI, 500);

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