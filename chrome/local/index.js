class InitMgr {
	constructor(vue) {
		this.vue = vue;
		this.init();
	}

	isReady() {
		let model = this.vue.data;
		return  !!model.tradeDays;
	}

	init() {
		this._loadTradeDays(false);
	}

	// load trade days
	_loadTradeDays(async) {
		let thiz = this;
		let model = this.vue.data;
		if (async == undefined)
			async = true;
		$.ajax({url: '/get-trade-days', async: async, success: function(data) {
			model.lastTradeDay = data[data.length - 1];
			model.tradeDays = data;
			model.initMgrReady = thiz.isReady();
		}});
	}
}

class GlobalMgr {
	constructor(vue) {
		this.vue = vue;
		this.table = null;
		this.zsInfos = {
			sh000001: null, sz399001: null, data: null // data = [{day, sday, amount, degree]
		}
		this.init();
	}

	init() {
		this._loadAmount();
		this._loadDegrees();
		this._initUI();
	}

	isReady() {
		return this.table != null;
	}

	_loadAmount() {
		let thiz = this;
		// 两市成交额
		function cb(data) {
			let rs = {};
			for (let i = 0; i < data.length; i++) {
				let day = String(data[i].day);
				day = day.substring(0, 4) + '-' + day.substring(4, 6) + '-' + day.substring(6);
				data[i].amount = data[i].amount / 1000000000000; // 万亿
				rs[day] = data[i];
			}
			return rs;
		}
		$.get('/load-kline/999999', function(data) {
			thiz.zsInfos.sh000001 = cb(data);
		});
		$.get('/load-kline/399001', function(data) {
			thiz.zsInfos.sz399001 = cb(data);
		});
	}

	_loadDegrees() {
		let thiz = this;
		let eday = this.vue.data.lastTradeDay;
		let date = new Date(eday);
		//let dx = date.setDate(date.getDate() - 45);
		let dx = date.setMonth(date.getMonth() - 1);
		date = new Date(dx);
		let fday = formatDay(date);
		let sql = "select day, 综合强度 as degree, substr(day, 6) as sday, fb from CLS_SCQX where day >= '" + fday + "' and day <= '" + eday + "'";
		$.ajax({
			url: '/query-by-sql/cls',
			data: {'sql': sql},
			success: function(resp) {
				let ds = thiz._getDays(fday, eday);
				thiz._mergeDays(ds, resp);
			}
		});
	}

	_mergeDays(days, resp) {
		let thiz = this;
		let model = this.vue.data;
		if (! model.initMgrReady || !this.zsInfos.sh000001 || !this.zsInfos.sz399001) {
			setTimeout(function() {thiz._mergeDays(days, resp);}, 500);
			return;
		}
		let mp = {};
		let rs = [];
		for (let r of resp) {
			mp[r.day] = r;
		}
		for (let day of days) {
			let item = mp[day] || {day: day, degree: '', fb:{zt:"", dt:"", up:"", down:"", zero:"", up_8:"", up_10:"",down_8:"", down_10:""}, sday: day.substring(5), amount: ''};
			rs.push(item);
			if (item && item.fb && typeof(item.fb) == 'string')
				item.fb = JSON.parse(item.fb);
			if (this.zsInfos.sh000001[day] && this.zsInfos.sz399001[day]) {
				let am = this.zsInfos.sh000001[day].amount + this.zsInfos.sz399001[day].amount;
				item.amount = am.toFixed(2);
			}
		}
		this.zsInfos.data = rs;
	}

	_getDays(fromDay, endDay) {
		let rs = [];
		for (let d of this.vue.data.tradeDays) {
			if (d >= fromDay && d <= endDay)
				rs.push(d);
		}
		return rs;
	}

	changeDay(curDay) {
		let datas = this.zsInfos.data;
		if (! curDay) return;
		if (curDay.length == 8) {
			curDay = curDay.substring(0, 4) + '-' + curDay.substring(4, 6) + '-' + curDay.substring(6, 8);
		}
		let idx = -1;
		for (let i = 0; i < datas.length; i++) {
			if (datas[i].day == curDay) {
				idx = i;
				break;
			}
		}
		if (idx < 0)
			return;
		let td = this.table.find(`tr:eq(1) > td:eq(${idx})`);
		this._inFunction(td);
		this._onClick(td);
	}

	_initUI() {
		let thiz = this;
		let model = this.vue.data;
		if (!this.zsInfos.data || !this.zsInfos.sh000001 || !this.zsInfos.sz399001) {
			setTimeout(function() {thiz._initUI();}, 500);
			return;
		}
		let table = $('<table> </table>');
		let datas = this.zsInfos.data;
		let cols = ['sday', 'degree', 'amount'];
		let colsDesc = ['', '热度', '成交额'];
		let WW = ['一', '二', '三', '四', '五'];
		for (let c = 0; c < cols.length; c++) {
			let tr = $('<tr> </tr>');
			tr.append($('<th>' + colsDesc[c] + '</th>'));
			let lastMonth = '';
			for (let i = 0; i < datas.length; i++) {
				let v = datas[i][cols[c]] || '';
				let clazz = '';
				let title = '';
				if (cols[c] == 'sday') {
					let m = v.substring(0, 2);
					if (m != lastMonth) {
						lastMonth = m;
					} else {
						v = v.substring(3);
					}
					let dx = new Date(datas[i].day);
					v += '<br/>' + WW[dx.getDay() - 1];
				} else if (cols[c] == 'degree') {
					clazz = c == 0 ? '' : (v >= 50 ? 'red' : 'green');
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
		table.find('td, th').hover(function(){thiz._inFunction(this);}, function(){thiz._outFunction(this);});
		table.find('td').click(function(){thiz._onClick(this);});
		$('div[name="global-item"]').append(table);
		this.table = table;
	}

	_inFunction(elem) {
		let idx = $(elem).attr('colidx');
		this.table.find('td[colidx=' + idx + ']').addClass('selcol');
	}

	_outFunction(elem) {
		let idx = $(elem).attr('colidx');
		let curSel = this.table.find('th[sel=true]');
		if (curSel.attr('colidx') != idx) {
			this.table.find('td[colidx=' + idx + ']').removeClass('selcol');
		}
	}

	_onClick(elem) {
		let colidx = $(elem).attr('colidx');
		let oldSel = this.table.find('th[sel=true]');
		let oldSelIdx = oldSel.attr('colidx');
		let newSel = this.table.find('th[colidx=' + colidx + ']');
		if (oldSelIdx != colidx) {
			oldSel.removeAttr('sel');
			newSel.attr('sel', 'true');
			this.table.find('td[colidx=' + oldSelIdx + ']').removeClass('selcol');
		}
		let data = $(elem).data('val');
		// window.location.hash = data.day;
		this.vue.data.curDay = data.day;
	}
}

class TimeDegreeMgr {
	constructor(vue) {
		this.vue = vue;
		this.canvas = null;
		this.chart = null;
		this.init();
	}

	init() {
		let thiz = this;
		this.vue.addWatch('curDay', function(n, o) {thiz._onChangeDay(n, o);});
	}

	_onChangeDay(newDay, oldDay) {
		this._loadData(newDay);
	}

	// day = YYYY-mm-dd
	_loadData(day) {
		let thiz = this;
		$.ajax({
			url: '/get-time-degree?day=' + day,
			success: function(resp) {
				thiz._buildUI(resp);
			}
		});
	}

	_buildUI(d) {
		if (this.canvas) {
			this.canvas.remove();
		}
		this.canvas = $('<canvas> </canvas>');
		$('div[name="time-degree-item"]').append(this.canvas);
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
		let cc = this.canvas.parent();
		if (! this.PCW) this.PCW = cc.width();
		if (! this.PCH) this.PCH = cc.height();

		if (this.chart)
			this.chart.destroy();
		let cw = parseInt(this.PCW * d.length / 26);
		this.canvas.width(cw);
		this.canvas.height(this.PCH);
		this.chart = new Chart(this.canvas.get(0), {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}});
		this.chart.resize(cw, this.PCH);
	}
}

class ZdfbMgr {
	constructor(vue) {
		this.vue = vue;
		this.ui = null;
		let thiz = this;
		let r = function(elem, bindName, obj, attrName) {
			thiz._renderDegree(elem, bindName, obj, attrName);
		}
		let czdFunc = function(elem, bindName, obj, attrName) {
			thiz._render_czd(elem, bindName, obj, attrName);
		}
		this.vue.data.zdfb = {day: null, zt:'', dt:'', up:'', down:'', up_8: '', down_8:'', degree:'', zero: '', czd: '', r: r, czdFunc: czdFunc}; // 涨跌分布
		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
	}

	_onChangeDay(newVal, oldVal) {
		let thiz = this;
		if (! this.ui) {
			this._buildUI();
		}
		let model = this.vue.data;
		if (newVal == this.vue.data.lastTradeDay) {
			// this.loadNewestData(function(data) {
			// 	thiz.updateData(data);
			// });
			this.loadNewestData_EC(function(data) {
				thiz.loadNewestDegree(function(day, degree) {
					// console.log(day, degree);
					if (day == newVal)
						thiz.updateData_EC(newVal, degree, data);
				});
			});
		} else {
			this.loadHistoryData(newVal);
		}
	}

	loadNewestDegree(cb) {
		let thiz =  this;
		let url = 'https://x-quote.cls.cn/quote/stock/emotion_options?app=CailianpressWeb&fields=up_performance&os=web&sv=7.7.5&sign=5f473c4d9440e4722f5dc29950aa3597';
		$.ajax({
			url: '/cls-proxy?url=' + encodeURIComponent(url),
			success: function(resp) {
				let day = resp.data.date;
				let degree = resp.data.market_degree;
				degree = parseInt(parseFloat(degree) * 100);
				cb(day, degree);
			}
		});
	}

	_buildUI() {
		this.ui = $('<div style="height:220px;">' +
					'<table class="zdfb" style="float:left; width:300px; height:215px;">' +
						"<tr class='red'> <th> 日期 </th> <th style=''>涨停 </th> </tr>" + 
						"<tr class='green'> <th :bind='zdfb.day'> </th> <th :bind='zdfb.zt' style='color:red;'> </th> </tr>" + 
						"<tr> <th :bind='zdfb.degree' :render='zdfb.r' style='width:165px; background-color:#fff;' rowspan=2>  </th> <th>跌停</th>  </tr>  " +
						"<tr> <th :bind='zdfb.dt' style='color:green;'> </th> </tr>" +
					"</table>" +
					"<div name='' style='width: 700px; height:215px; float:left; margin-left:120px;' :bind='zdfb.czd' :render='zdfb.czdFunc'> "+
					"</div>");
		// this.table.find('td').css('width', '120px');
		$('div[name="zdfb-item"]').append(this.ui);
		let style = document.createElement('style');
		let css = `.zdfb th {width: 110px;} \n\
				`;
		style.appendChild(document.createTextNode(css));
		document.head.appendChild(style);
		this.vue.mount(this.ui);
	}

	_renderDegree(elem, bindName, data, attrName) {
		elem = $(elem);
		elem.empty();
		let d = 0;
		if (data.degree) {
			d = data.degree / 100.0 * 226;
		}
		let wrap = $(`<div style="width:160px; height: 80px;"><svg style="width:100% ;height: 100%;">\
						<defs>\
						    <linearGradient id="linear" x1="0%" y1="0%" x2="100%" y2="0%">\
								<stop offset="0%" stop-color="#80DCC2"></stop>\
								<stop offset="100%" stop-color="#FF2C49"></stop>\
							</linearGradient>\
						</defs>\
						<circle cx="77.5" cy="76" r="72" stroke="#E2E2E2" stroke-width="8" fill="none" stroke-dasharray="226" stroke-dashoffset="-226" stroke-linecap="round"></circle>\
						<circle cx="77.5" cy="76" r="72" stroke="url(#linear)" stroke-width="8" fill="none" stroke-dasharray="${d} 227" stroke-dashoffset="-226" stroke-linecap="round"></circle>\
					</svg></div>`);
		elem.append(wrap);
		let dg = '--';
		if (data.degree) {
			dg = String(data.degree) + '°';
		}
		let color = '#52c2a3';
		if (data.degree && data.degree >= 50) color = 'red';
		let title = $(`<div style="text-align: center; line-height: 1; font-size: 30px; margin-top:-35px; color:${color};">${dg}</div>`);
		wrap.append(title);
	}

	_render_czd(elem, bindName, data, attrName) {
		elem = $(elem);
		elem.empty();
		if (typeof(data.up) != 'number' || typeof(data.zero) != 'number' || typeof(data.down) != 'number')
			return;
		let total = data.up + data.down + data.zero;
		data.total = total;
		let canvas = $('<canvas> </canvas>');
		elem.append(canvas);
		let view = new ZdfbView(canvas.get(0));
		view.draw(data);
	}

	// 涨跌分布
	loadNewestData(cb) {
		let thiz =  this;
		$.ajax({
			url: 'https://x-quote.cls.cn/quote/index/home?app=CailianpressWeb&os=web&sv=8.4.6&sign=9f8797a1f4de66c2370f7a03990d2737',
			success: function(resp) {
				if (resp.code != 200 || !resp.data.up_down_dis.status)
					return;
				let udd = resp.data.up_down_dis;
				udd.up = udd.rise_num;
				udd.down = udd.fall_num;
				// udd.zt = udd.up_num;
				// udd.dt = udd.down_num;
				udd.zero = udd.flat_num;
				udd.day = thiz.vue.data.lastTradeDay;
				cb(udd);
			}
		});
	}

	// 东财的数据
	loadNewestData_EC(cb) {
		$.ajax({
			url: 'https://push2ex.eastmoney.com/getTopicZDFenBu?cb=callbackdata838226&ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt',
			success: function(text) {
				text = text.substring(text.indexOf('(') + 1, text.indexOf(')'));
				let fb = {};
				let rs = JSON.parse(text);
				if (rs) {
					let fenbu = rs['data']['fenbu']
					for (let it of fenbu) {
						for (let k in it) fb[k] = it[k];
					}
				}
				cb(fb);
			}
		});
	}

	loadHistoryData(day) {
		let thiz =  this;
		let sql = `select day, 综合强度 as degree, substr(day, 6) as sday, fb, zdfb from CLS_SCQX where day = '${day}'`;
		$.ajax({
			url: '/query-by-sql/cls',
			data: {'sql': sql},
			success: function(resp) {
				let zdfb = resp[0].zdfb ? JSON.parse(resp[0].zdfb) : null;
				let degree = resp[0].degree || '';
				thiz.updateData_EC(day, degree, zdfb);
			}
		});
	}

	updateData(data) {
		let a = ['day', 'zero', 'down', 'up', 'up_8', 'down_8', 'degree']; // 'zt', 'dt'
		let model = this.vue.data.zdfb;
		for (let k of a) {
			if (k == 'up_8') model[k] = data[k] + data['up_10'];
			else if (k == 'down_8') model[k] = data[k] + data['down_10'];
			else model[k] = data[k];
		}
		model.czd = data.up *100 + data.down * 10 + data.zero;
	}

	updateData_EC(day, degree, zdfb) {
		let model = this.vue.data.zdfb;
		function numToStr(n) {if (typeof(n) == undefined) return ''; return n;}
		model.day = day;
		model.degree = degree;
		zdfb = zdfb || {}
		model.zt = numToStr(zdfb['11']);
		model.dt = numToStr(zdfb['-11']);
		let up = 0, down = 0;
		for (let k in zdfb) {
			if (k.indexOf('-') >= 0) down += zdfb[k];
			else if (k != '0') up += zdfb[k];
		}
		model.zdfb = zdfb;
		model.up = numToStr(up);
		model.down = numToStr(down);
		model.zero = numToStr(zdfb['0']);
		model.up_8 = numToStr(zdfb['9']) + numToStr(zdfb['10']); // zdfb['10'] means > 9%
		model.down_8 = numToStr(zdfb['-9']) + numToStr(zdfb['-10']); // zdfb['10'] means > 9%
		model.czd = Math.random(); // update it view
	}
}

class AnchorsMgr {
	constructor(vue) {
		this.vue = vue;
		this.anchorView = null; // fenshi anchor 
		this.table = null; // list table
		let thiz = this;
		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
		this.vue.addWatch('dayAnchor', function(a, b) {thiz.onDayAnchorUpdate(a, b);});
		this.vue.addWatch('anchorGroup', function(a, b) {thiz.onAnchorGroupUpdate(a, b);});
	}

	_initUI() {
		let canvas = $('<canvas> </canvas>');
		$('div[name=anchor-fs-item]').append(canvas);
		let table = $('<table class="anchor-list" style="border-collapse: separate;border-spacing: 15px 10px;"> </table>');
		$('div[name=anchor-list-item]').append(table);
		this.table = table;
		let popup = $('<div class="popup-container"> </div>');
		$(document.body).append(popup);
		popup.click(function() {$(this).css('display', 'none')});
		popup.on('mousewheel', function(event) {event.preventDefault();});

		this.anchorView = new AnchrosView(canvas.get(0));
		this.chart = null;
		this.chartOrgData = null;
	}

	_onChangeDay(newVal, oldVal) {
		let thiz = this;
		let model = this.vue.data;
		if (! this.anchorView) {
			this._initUI();
		}
		if (newVal == this.vue.data.lastTradeDay) {
		}
		$.ajax({url: `/get-all-hot-tc?days=20&curDay=${newVal}`, async: true, success: function(data) {
			model.anchros = data;
			model.anchorGroup = thiz.calcGroups(newVal);
			thiz.loadAnchorOfDay(newVal);
		}});
	}

	updateAnchorName(data) {
		if (! data) return;
		let anchrosCP = this.vue.data.anchorGroup;
		for (let i = 0; i < data.length; i++) {
			let an = data[i];
			let key = an.code + '#' + an.up;
			let num = anchrosCP[key]?.num || 1;
			an.wName = an.name + num;
		}
	}

	loadAnchorOfDay(day) {
		let model = this.vue.data;
		let thiz = this;
		this.anchorView.loadData(day, function(data) {
			if (! data)
				return;
			if (! model.dayAnchor || model.dayAnchor.length != data.length) {
				model.dayAnchor = data;
			}
			thiz.updateAnchorName(data);
		});
	}

	onDayAnchorUpdate(newVal, oldVal) {
		if (newVal == oldVal || !newVal || newVal.length == 0) {
			return;
		}
		let model = this.vue.data;
		let lastDay = model.anchros[0][0].day;
		let cday = newVal[0].day;
		if (cday > lastDay) {
			model.anchros.unshift(newVal);
		} else if (cday == lastDay) {
			model.anchros[0] = newVal;
		}
		if (model.curDay >= cday) {
			model.anchorGroup = this.calcGroups(model.curDay);
		}
	}

	onAnchorGroupUpdate(anchrosCP, oldVal) {
		let arr = [];
		for (let k in anchrosCP) {
			if (k.indexOf('#true') > 0)
				arr.push(anchrosCP[k]);
		}
		arr.sort(function(a, b) {return b.num - a.num});
		this.table.empty();
		let tr = null;
		let COL_NUM = 7;
		for (let i = 0; i < arr.length; i++) {
			let item = arr[i];
			if (item.num < 2)
				break;
			if (i % COL_NUM == 0) {
				tr = $('<tr> </tr>');
				this.table.append(tr);
			}
			let a = '<a href="plate.html?code=' + item.code + '&name=' + item.name + '" target=_blank> ' + item.name + '&nbsp;&nbsp;' + item.num + '&nbsp;&nbsp;</a>';
			let s = '<span class="anchor-arrow" code="' + item.code + '">  </span>';
			tr.append($('<td class="' + item.tag + '"> ' + a + s + ' </td>'));
		}
		let thiz = this;
		this.table.find('.anchor-arrow').click(function() {thiz.openChart(this);});
	}

	calcGroups(cday) {
		let model = this.vue.data;
		let anchrosCP = {};
		for (let i = 0, num = 0; i < model.anchros.length && num < 10; i++) { // 10 days
			let day = model.anchros[i][0].day;
			if (day > cday)
				continue;
			num++;
			for (let j = 0; j < model.anchros[i].length; j++) {
				let an = model.anchros[i][j];
				let key = an.code + '#' + an.up;
				if (anchrosCP[key]) {
					anchrosCP[key].items.push(an);
				} else {
					anchrosCP[key] = {name: an. name, code: an.code, num: 0, tag: an.up, items: [an]};
				}
				anchrosCP[key].num++;
			}
		}
		// console.log(anchrosDays);
		return anchrosCP;
	}

	getAnchrosByCode(code, maxDay, daysNum) {
		let model = this.vue.data;
		if (!maxDay || !model.anchros) {
			return null;
		}
		let rs = {up: [], down: [], days: [], allDays: []};
		for (let i = 0, num = 0; i < model.anchros.length && num < daysNum; i++) {
			let day = model.anchros[i][0].day;
			rs.allDays.push(day);
			if (day > maxDay)
				continue;
			++num;
			rs.days.push(day);
			for (let j = 0; j < model.anchros[i].length; j++) {
				let an = model.anchros[i][j];
				if (an.code == code) {
					rs[an.up ? 'up' : 'down'].push(an);
				}
			}
		}
		return rs;
	}

	openChart(elem) {
		let thiz = this;
		elem = $(elem);
		let code = elem.attr('code');
		let model = this.vue.data;
		this._loadChartData(code, model.curDay, function(cdata) {
			thiz._openChartUI(elem, cdata);
		});
	}

	_loadChartData(code, day, cb) {
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
		let thiz = this;
		$.get(`/get-hot-tc-by-code?code=${code}&curDay=${day}&days=20`, function(data) {
			thiz.chartOrgData = data;
			let upset = data.up;
			let downset = data.down;
			let cdata = {
				labels: data.sdays,
				datasets: [
					{label: 'UP', data: upset, fill: false, borderColor: '#FF3333', segment: ss(upset), spanGaps: true},
					{label: 'DOWN', data: downset, fill: false, borderColor: '#33ff33', segment: ss(downset), spanGaps: true},
				],
			};
			cb(cdata);
		});
	}

	_openChartUI(elem, cdata) {
		let thiz = this;
		elem = $(elem);
		let ui = $('<div class="anchors-wrap"> </div>');
		let btns = $('<div class="header"> <button class="left"> &lt;&lt; </button>  <button class="right"> &gt;&gt; </button> </div>');
		btns.find('button').click(function() {
			thiz.onClickChart($(this).attr('class'));
		});
		ui.append(btns);
		let canvas = $('<canvas> </canvas> ');
		$('.popup-container').empty();
		$('.popup-container').css('display', 'block');
		$('.popup-container').append(ui);
		ui.click(function(event) {  event.stopPropagation(); return false; });
		let tdRc = elem.parent().get(0).getBoundingClientRect();
		let dw = $(window.document).width();
		if (dw < tdRc.left + ui.width()) {
			ui.css({left: dw - ui.width() - 10, top: tdRc.bottom});
		} else {
			ui.css({left: tdRc.left, top: tdRc.bottom});
		}
		ui.append(canvas);
		canvas.width(ui.width());
		canvas.height(ui.height() - btns.height() - 10);
		// canvas.attr('day', day);
		function pbc() {
			let rs = [];
			rs.push('#0000ff');
			for (let i = 0; i < 4; i++)
				rs.push(Chart.defaults.borderColor);
			return rs;
		}
		this.chart = new Chart(canvas.get(0), {type: 'line', data: cdata, options: {
			plugins: {legend: {display: false, title: {display: false}}},
			scales: {x: {grid : {color : pbc()}}}
		}});
	}

	onClickChart(name) {
		let thiz = this;
		let day = name == 'left' ? this.chartOrgData.preDay : this.chartOrgData.nextDay;
		if (! day) return;
		this._loadChartData(this.chartOrgData.code, day, function(cdata) {
			thiz.chart.data.labels = cdata.labels;
			thiz.chart.data.datasets = cdata.datasets;
			thiz.chart.update();
		});
	}
}

class TabNaviMgr {
	constructor(vue) {
		this.vue = vue;
		this.navi = null;
		this.curTabName = null;
		let thiz = this;

		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
	}

	_onChangeDay(newVal, oldVal) {
		let thiz = this;
		if (! this.navi) {
			this._initUI();
		}
		let wrap = $(`div[name=tab-nav-cnt-item]`);
		wrap.empty();
		this.loadTabNavi(this.curTabName || '涨停池');
	}

	_initUI() {
		let thiz = this;
		this.navi = $('<div class="toggle-nav-active">涨停池</div> <div >连板池</div>  <div >炸板池</div> <div >跌停池</div> <div >热度榜</div> <div >成交额</div> <div >指数</div> <div>笔记</div> <div>标记</div> </div>');
		$('div[name="tab-nav-item"]').append(this.navi);
		$('div[name="tab-nav-item"] > div').click(function() {
			if (! $(this).hasClass('toggle-nav-active')) {
				$('div[name="tab-nav-item"] > .toggle-nav-active').removeClass('toggle-nav-active');
				$(this).addClass('toggle-nav-active');
			}
			thiz.loadTabNavi($(this).text().trim());
		});
	}

	loadTabNavi(name) {
		this.curTabName = name;
		if (name == '热度榜') {
			this.loadTopHotsNavi(name);
			return;
		}
		if (name == '笔记') {
			this.loadNoteNavi(name);
			return;
		}
		if (name == '标记') {
			this.loadMarkNavi(name);
			return;
		}
		if (name == '成交额') {
			this.loadAmountNavi(name);
			return;
		}
		if (name == '指数') {
			this.loadZSNavi();
			return;
		}
		if (name.indexOf('池') > 0) {
			this.loadPoolNavi(name);
			return;
		}
	}

	loadPoolNavi(name) {
		let model = this.vue.data;
		let thiz = this;
		if (model.curDay == model.lastTradeDay) {
			let ks = {'涨停池': 'up_pool', '连板池': 'continuous_up_pool', '炸板池': 'up_open_pool', '跌停池': 'down_pool'};
			let url = 'https://x-quote.cls.cn/quote/index/up_down_analysis?'
			let params = 'app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=' + ks[name] + '&way=last_px';
			params = new ClsUrl().signParams(params);
			url += params;
			$.ajax({
				url: '/cls-proxy?url=' + encodeURIComponent(url),
				success: function(resp) {
					for (let i = resp.data.length - 1; i >= 0; i--) {
						if (resp.data[i].is_st) resp.data.splice(i, 1);
					}
					thiz.updateTabContentUI(name, resp.data);
				}
			});
		} else {
			let sql = 'select * from cls_updown where day = "' + model.curDay + '" ';
			if (name == '涨停池') sql += ' and limit_up_days > 0';
			else if (name == '连板池') sql += ' and limit_up_days > 1';
			else if (name == '炸板池') sql += ' and limit_up_days = 0 and is_down = 0';
			else sql += ' and is_down = 1';
			$.ajax({
				url : ' /query-by-sql/cls',
				data: {'sql': sql},
				success: function(resp) {
					thiz.updateTabContentUI(name, resp);
				}
			});
		}
	}

	loadMarkNavi(name) {
		let thiz = this;
		$.ajax({
			url: ' /mark-color',
			contentType: 'application/json',
			type: 'POST',
			data: JSON.stringify({op: 'get'}),
			success: function(resp) {
				thiz.updateTabContentUI(name, resp);
			}
		});
	}

	loadAmountNavi(name) {
		let thiz = this;
		let day = this.vue.data.curDay;
		$.ajax({
			url: ` /top100-vol?day=${day}`,
			contentType: 'application/json',
			type: 'GET',
			// data: JSON.stringify({op: 'get'}),
			success: function(resp) {
				thiz.updateTabContentUI(name, resp);
			}
		});
	}

	loadTopHotsNavi(name) {
		let thiz = this;
		let day = this.vue.data.curDay;
		$.ajax({
			url: ' /get-hots?day=' + day, type: 'GET',
			success: function(resp) {
				let rs = [];
				for (let k in resp) {
					resp[k].secu_name = resp[k].name;
					rs.push(resp[k]);
				}
				rs.sort(function(a, b) {return a.hots - b.hots});
				rs.splice(100, rs.length - 100);
				thiz.updateTabContentUI(name, rs);
				thiz.loadTopAmounts(name, rs, false);
			}
		});
	}

	loadTopAmounts(name, rs, setAmount) {
		let thiz = this;
		let day = this.vue.data.curDay;
		day = day.replaceAll('-', '');
		$.ajax({
			url: ' /iwencai', type: 'GET',
			data: {q: '个股成交额排名, ' + day, maxPage : 2},
			success: function(resp) {
				let amountAttrName = 'amount';
				if (resp && resp.length > 0) {
					for (let k in resp[0]) {
						if (k.indexOf('成交额[') >= 0) amountAttrName = k;
					}
				}
				let map = {};
				for (let k = 0; k < resp.length; k++) {
					resp[k].secu_name = resp[k].股票简称;
					resp[k].change = resp[k].最新涨跌幅;
					resp[k].amount = parseFloat(resp[k][amountAttrName]) / 100000000;
					resp[k].amountIdx = k + 1;
					map[resp[k].code] = resp[k];
				}
				for (let i = 0; i < rs.length; i++) {
					let code = rs[i].code;
					if (map[code]) {
						if (setAmount)
							rs[i].amount = map[code].amount;
						rs[i].amountIdx = map[code].amountIdx;
					} else {
						if (setAmount)
							rs[i].amount = 0;
						rs[i].amountIdx = 0;
					}
				}
			}
		});
	}

	loadZSNavi(name) {
		let thiz = this;
		let day = this.vue.data.curDay;
		let db = '';
		let sql = '';
		let headers = null;
		function amountRender(idx, rowData, header, tdObj) {
			if (! rowData[header.name]) {
				tdObj.text('');
				return;
			}
			let v = String(parseInt(rowData[header.name])) + ' 亿';
			tdObj.html(v);
		}
		function topPmRender(idx, rowData, header, tdObj) {
			if (! rowData[header.name]) {
				tdObj.text('');
				return;
			}
			tdObj.text(rowData[header.name]);
		}
		function codeRender(idx, rowData, header, tdObj) {
			if (! rowData[header.name]) {
				tdObj.text('');
				return;
			}
			let params = '';
			if (rowData.secu_code.substring(0, 3) == 'cls') {
				params = `code=${rowData.secu_code}`;
			} else {
				params = `code=0&refThsCode=${rowData.secu_code}&refThsName=${rowData.name}`;
			}
			let a = $(`<span><a href="https://www.cls.cn/plate?${params}&period=10&day=${rowData.day}" target=_blank> ${rowData.name} </a></span>`);
			let b = $(`<span style="color:#666;font-size:12px;"> ${rowData.secu_code} </span>`);
			tdObj.append(a).append('<br/>').append(b);
		}
		
		if (name == 'cls') {
			db = 'cls';
			sql = `select * from CLS_ZS_ZD where day = '${day}' and abs(pm) <= 50`;
			headers = [{name: 'day', text: '日期'}, {name: 'code', text: '代码', cellRender: codeRender},
					{name: 'type_', text: '类型', sortable: true,}, {name: 'zf', text: '涨幅', sortable: true},
					{name: 'fund', text: '净流入(亿)', sortable: true, cellRender : amountRender}, {name: 'pm', text:'全市排名', sortable: true}];
		} else {
			db = 'ths_zs';
			sql = `select * from 同花顺指数涨跌信息 where day = '${day}' and abs(zdf_PM) <= 50`;
			headers = [{name: 'day', text: '日期'}, {name: 'code', text: '代码', cellRender: codeRender},
					{name: 'money', text: '成交额(亿)', sortable: true, cellRender : amountRender}, {name: 'zf', text: '涨幅', sortable: true},
					{name: 'zdf_topLevelPM', text: '一级排名', sortable: true, cellRender: topPmRender}, {name: 'zdf_PM', text: '全市排名', sortable: true}];
		}
		let opts = $('<button name="ths"> 同花顺指数 </button>  &nbsp; &nbsp; <button name="cls">财联社指数 </button>');
		$.ajax({
			url: ' /query-by-sql/' + db,
			data: {'sql': sql},
			success: function(resp) {
				for (let d of resp) {
					d.secu_code = d.code;
					if (d.zdf != undefined) d.zf = d.zdf;
				}
				thiz.updateTabContentUI('指数', {data: resp, header: headers, ops : opts});
			}
		});
		opts.click(function() {
			thiz.loadZSNavi($(this).attr('name'));
		})
	}

	updateTabContentUI(name, data) {
		let wrap = $(`div[name=tab-nav-cnt-item]`);
		let cnt = wrap.find(`div[name=${name}]`);
		$(`div[name=tab-nav-cnt-item] > div`).hide();
		if (cnt.length != 0) {
			cnt.show();
			return;
		}
		cnt = $(`<div  name=${name} > </div>`);
		wrap.append(cnt);
		let model = this.vue.data;
		if (! data) {
			return;
		}
		let hd = null, ops = null, exOps = null;
		function amountRender(idx, rowData, header, tdObj) {
			if (! rowData[header.name]) {
				tdObj.text('');
				return;
			}
			let v = String(parseInt(rowData[header.name])) + ' 亿';
			tdObj.html(v);
		}
		function amountIdxRender(idx, rowData, header, tdObj) {
			if (! rowData.amountIdx) {
				tdObj.text('');
				return;
			}
			tdObj.html(rowData.amountIdx);
		}
		if (name == '涨停池' || name == '连板池') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true}, // change
				{text: '连板', 'name': 'limit_up_days', width: 50, sortable: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
				{text: '动因', 'name': 'up_reason', width: 250, sortable: true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if (name == '炸板池') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '行业', 'name': 'ths_hy', width: 100, sortable: true, defined:true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: 'CLS-ZT', 'name': 'cls_ztReason', width: 100, sortable: true, defined: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if (name == '跌停池') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '行业', 'name': 'ths_hy', width: 100, sortable: true, defined:true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: 'CLS-ZT', 'name': 'cls_ztReason', width: 100, sortable: true, defined: true},
				{text: 'THS-DT', 'name': 'up_reason', width: 100, sortable: true, defined: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if (name == '热度榜') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '行业', 'name': 'ths_hy', width: 100, sortable: true, defined:true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: 'CLS-ZT', 'name': 'cls_ztReason', width: 100, sortable: true, defined: true},
				{text: '成交额', 'name': 'amount', width: 50, sortable: true, defined: true},
				{text: '成交额<br/>排名', 'name': 'amountIdx', width: 50, sortable: false, cellRender : amountIdxRender, defined: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if ( name == '成交额') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '行业', 'name': 'ths_hy', width: 100, sortable: true, defined:true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: 'CLS-ZT', 'name': 'cls_ztReason', width: 100, sortable: true, defined: true},
				{text: '成交额', 'name': 'vol', width: 50, sortable: true, cellRender : amountRender},
				{text: '成交额<br/>排名', 'name': 'pm', width: 50, sortable: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true, defined:true},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if ( name == '标记') {
			hd = [
				{text: ' ', 'name': 'mark_color', width: 40, sortable: true, defined: true},
				{text: '股票/代码', 'name': 'code', width: 80},
				{text: '行业', 'name': 'ths_hy', width: 100, sortable: true, defined:true},
				{text: 'THS-ZT', 'name': 'ths_ztReason', width: 100, sortable: true, defined: true},
				{text: 'CLS-ZT', 'name': 'cls_ztReason', width: 100, sortable: true, defined: true},
				{text: '标记日期', 'name': 'day', width: 80, sortable: true},
				{text: '热度', 'name': 'hots', width: 50, sortable: true, defined: true},
				{text: '涨跌幅', 'name': 'zf', width: 70, sortable: true, defined: true},
				{text: '涨速', 'name': 'zs', width: 50, sortable: true, defined: true},
				{text: '分时图', 'name': 'fs', width: 300},
			];
		} else if (name == '指数') {
			exOps = data.ops;
			hd = data.header;
			data = data.data;
		}
		if (name == '涨停池') {
			for (let i = data.length - 1; i >= 0; i--) {
				if (data[i].limit_up_days != 1)
					data.splice(i, 1);
			}
			data.sort((a, b) => a.time.localeCompare(b.time));
		}

		let st = new StockTable(hd);
		// window.st = st;
		st.setDay(model.curDay);
		st.setTradeDays(model.tradeDays);
		st.setData(data);
		if (name == '涨停池') {
			//st.sortHeader('limit_up_days', 'asc');
		} else if (name == '连板池') {
			st.sortHeader('limit_up_days', 'desc');
		} else if (name == '标记') {
			st.addListener('BeforeOpenKLine', function(evt) {
				let cs = evt.data.codes;
				cs.length = 0;
				for (let d of evt.src.datas) {
					cs.push({code: d.code, day: d.day});
				}
				evt.data.day = evt.rowData.day;
			});
		}
		st.buildUI();
		ops = $('<div style="text-align:center; "> \
			<input name="searchText" placeHolder = "" style="border:solid 1px #999;"/>  \
			</div>');
		ops.find('input').bind('keydown', function(event) {
			if(event.keyCode == 13) {
				window.st.filter($(this).val().trim());
			}
		});
		ops.append(exOps);
		cnt.append(ops);
		cnt.append(st.table);
		if (name == '跌停池' && model.curDay == model.lastTradeDay) {
			this.loadDTInfo(st, model.curDay);
		}
	}

	loadDTInfo(st, day) {
		day = day || '';
		day = day.replaceAll('-', '');
		// ths_dtReason
		$.ajax({
			url: `/iwencai?q=${day} 跌停,非st,成交额,收盘价,涨跌幅`,
			success: function(resp) {
				if (! resp) return;
				for (let r of resp) {
					let reason = '';
					for (let m in r) if (m.indexOf('跌停原因类型[') >= 0) { reason = r[m]; break; }
					let scode = r.code.charAt(0) == '6' ? 'sh' : 'sz';
					let fd = st.datasMap[scode + r.code];
					if (fd) fd.up_reason = reason;
				}
			}
		});
	}

	loadNoteNavi(name) {
		let wrap = $(`div[name=tab-nav-cnt-item]`);
		let cnt = wrap.find(`div[name=${name}]`);
		$(`div[name=tab-nav-cnt-item] > div`).hide();
		if (cnt.length != 0) {
			cnt.show();
			return;
		}
		cnt = $(`<div name=${name} > </div>`);
		wrap.append(cnt);
		let re = new RichEditor('my-note');
		re.buildUI();
		cnt.append(re.ui);
	}
}

function changeCurDay(initMgr, globalMgr) {
	let curDay = getLocationParams('day');
	if (!initMgr.isReady() || !globalMgr.isReady()) {
		setTimeout(() => {
			changeCurDay(initMgr, globalMgr);
		}, 500);
		return;
	}
	globalMgr.changeDay(curDay || window.vue.data.lastTradeDay);
}

class AmountCompare {
	constructor(vue) {
		this.vue = vue;
		this.data = null;
		this.result = null;
		let thiz = this;
		this.canvas = null;
		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
	}

	_onChangeDay(newVal, oldVal) {
		this._loadAmount(newVal);
	}

	_loadAmount(day) {
		let thiz = this;
		$.get('/compare-amount/'+day, function(data) {
			thiz.data = data;
			thiz.calc();
			thiz._buildUI();
		});
	}

	_buildUI() {
		if (! this.canvas) {
			let c = $('<canvas> </canvas>');
			this.canvas = c.get(0);
			$('div[name="amount-item"]').append(c);
			let p = c.parent();
			this.canvas.width = p.width() * 0.8;
			this.canvas.height = p.height();
		}
		this.draw();
	}

	calc() {
		this.result = {data: [], time: this.data.time, curSum: 0, preSum: 0};
		let maxRate = 0, minRate = 0;
		for (let i = 0; i < this.data.cur.length; i++) {
			let cur = this.data.cur[i];
			let pre = this.data.pre[i];
			if (i != 0) {
				cur += this.result.data[i - 1].cur;
				pre += this.result.data[i - 1].pre;
			}
			let rate = pre ? (cur - pre) / pre * 100 : 1;
			let obj = {cur, pre, rate};
			this.result.data.push(obj);
			if (i == 0) {
				maxRate = minRate = rate;
			} else {
				maxRate = rate > maxRate ? rate : maxRate;
				minRate = rate < minRate ? rate : minRate;
			}
			this.result.curSum = cur;
			this.result.preSum = pre;
		}
		if (maxRate <= 0) {
			maxRate = 0;
		} else if (minRate >= 0) {
			minRate = 0;
		} else {
			let m = Math.abs(maxRate) > Math.abs(minRate);
			if (m) minRate = - Math.abs(maxRate);
			else maxRate = Math.abs(minRate);
		}
		this.result.maxRate = maxRate;
		this.result.minRate = minRate;
	}

	draw() {
		if (! this.result || !this.result.data.length)
			return;
        let ctx = this.canvas.getContext("2d");
		let width = this.canvas.width;
		let height = this.canvas.height;
		const PAD_LEFT = 80;
		const PAD_RIGHT = 200;
		const PAD_TOP = 5;
		const PAD_BOTTOM = 30;
		const AW = width - PAD_LEFT - PAD_RIGHT;
		const AH = height - PAD_TOP - PAD_BOTTOM;
		const PX = AW / 240;
		const MM = this.result.maxRate - this.result.minRate;
		function getRateY(result, rate) {
			let r = rate - result.minRate;
			let rr = r / MM;
			return AH - rr * AH + PAD_TOP;
		}
		
		ctx.clearRect(0, 0, width, height);

		ctx.beginPath();
		ctx.strokeStyle = '#FC9938';
		ctx.font = 'normal 12px Arial';
		ctx.lineWidth = 2;
		for (let i = 0; i < this.result.data.length; i++) {
			let x = PAD_LEFT + i * PX;
			let y = getRateY(this.result, this.result.data[i].rate);
			if (i == 0) ctx.moveTo(x, y);
			else ctx.lineTo(x, y);
		}
		ctx.stroke();
		ctx.closePath();

		ctx.beginPath();
		ctx.fillStyle = '#FFF2E5';
		for (let i = 0; i < this.result.data.length; i++) {
			let x = PAD_LEFT + i * PX;
			let y = getRateY(this.result, this.result.data[i].rate);
			if (i == 0) ctx.moveTo(x, y);
			else ctx.lineTo(x, y);
		}
		ctx.lineTo(this.result.data.length * PX + PAD_LEFT, getRateY(this.result, this.result.minRate) - 1);
		ctx.lineTo(PAD_LEFT, getRateY(this.result, this.result.minRate) - 1);
		ctx.fill();
		ctx.closePath();

		// draw bg
		let rpx = (this.result.maxRate - this.result.minRate) / 4;
		for (let i = 0; i < 5; i++) {
			let v = this.result.maxRate - i * rpx;
			ctx.beginPath();
			ctx.font = 'normal 12px Arial';
			if (v == 0) ctx.fillStyle = '#555';
			else if (v > 0) ctx.fillStyle = '#f55';
			else ctx.fillStyle = '#5c5';
			let text = v != 0 ? v.toFixed(1) + '%' : String(v);
			let ww = ctx.measureText(text).width;
			let y = getRateY(this.result, v);
			ctx.fillText(text, PAD_LEFT - ww - 5, y + 5);
			ctx.moveTo(PAD_LEFT, y)
			ctx.lineTo(width - PAD_RIGHT, y);
			ctx.strokeStyle = '#ddd';
			ctx.lineWidth = 1;
			ctx.setLineDash([4, 4]);
			ctx.stroke();
			ctx.closePath();
		}
		ctx.setLineDash([]);

		// zero line bule
		ctx.beginPath();
		ctx.strokeStyle = '#00c';
		// ctx.lineWidth = 2;
		ctx.moveTo(PAD_LEFT, getRateY(this.result, 0))
		ctx.lineTo(width - PAD_RIGHT, getRateY(this.result, 0));
		ctx.stroke();
		ctx.closePath();

		// right tip text
		ctx.fillStyle = '#000';
		ctx.font = 'normal 20px Arial';
		let text = '实际量能  ' +  parseInt(this.result.curSum / 100000000) + '亿';
		ctx.fillText(text, width - PAD_RIGHT + 10, PAD_TOP + 40);
		let z = (this.result.curSum - this.result.preSum);
		let flag = this.result.curSum >= this.result.preSum ? '增量 ' : '缩量 ';
		text = flag + parseInt(z / 100000000) + '亿';
		let zr = (z / this.result.preSum * 100).toFixed(1);
		text += '   ' + zr + '%';
		if (z > 0) ctx.fillStyle = '#c00';
		else if (z < 0) ctx.fillStyle = '#0c0';
		else ctx.fillStyle = '#000';
		ctx.fillText(text, width - PAD_RIGHT + 10, PAD_TOP + 80);

		ctx.fillStyle = '#aaa';
		ctx.font = 'normal 12px Arial';
		let time = ['09:30', '10:30', '11:30', '14:00', '15:00'];
		for (let i = 0; i < time.length; i++) {
			let x = PAD_LEFT + i * AW / 4;
			if (i == time.length - 1)
				x -= ctx.measureText(time[i]).width;
			ctx.fillText(time[i], x, height - PAD_BOTTOM + 15);
		}
	}
}

(function() {
	let model = {
		initMgrReady: false,
		anchros: null,
		dayAnchor: null,
		anchorGroup: null, //当前
		tradeDays: null, // ['YYYY-MM-DD', ...]
		lastTradeDay: null, //最新交易日期
		curDay: null, //当前选择的日期
		compareAmountData: null, // 今昨日成交对比
	};
	let vue = new Vuex(model);
	let initMgr = new InitMgr(vue);
	let globalMgr = new GlobalMgr(vue);
	new TimeDegreeMgr(vue);
	new ZdfbMgr(vue);
	new AnchorsMgr(vue);
	new TabNaviMgr(vue);
	new AmountCompare(vue);
	window.vue = vue;
	setTimeout(function() {changeCurDay(initMgr, globalMgr);}, 500);
})();
