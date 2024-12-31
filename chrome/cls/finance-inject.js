var anchros = null;

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
		let div = $('<div id="real-zt-div" style="padding-left:250px; font-size:20px; color: #ad1078;" > ' + text + '</div>');
		$('.event-querydate-box').append(div);
	} else {
		$('#real-zt-div').html(text);
	}
}

function adjustAnchors(response, cday) {
	console.log('[adjustAnchors] cday=', cday);
	if (! anchros) {
		return;
	}
	let MAX_TRACE_DAYS = 5;
	let body = response.response;
	let json = JSON.parse(body);
	console.log(anchros);
	let anchrosCP = {};
	for (let i = 0, num = 0; i < anchros.length && num < MAX_TRACE_DAYS; i++) {
		if (anchros[i][0].c_time.substring(0, 10) >= cday)
			continue;
		++num;
		for (let j = 0; j < anchros[i].length; j++) {
			let an = anchros[i][j];
			let key = an.symbol_code + '#' + an.float;
			if (anchrosCP[key]) anchrosCP[key]++;
			else anchrosCP[key] = 1;
		}
	}

	for (let i = 0; i < json.data.length; i++) {
		let key = json.data[i].symbol_code + '#' + json.data[i].float;
		let num = anchrosCP[key] || 0;
		num += 1;
		json.data[i].symbol_name += '' + num + '';
		anchrosCP[key] = num;
	}
	response.response = JSON.stringify(json);
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