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

class InitMgr {
	constructor(vue) {
		this.initUIEnd = false;
		this.vue = vue;
		this.init();
	}

	isReady() {
		let model = this.vue.data;
		return  model.tradeDays && model.anchros && this.initUIEnd;
	}

	init() {
		this._initRequest();
		this._initUI();
	}

	// load trade days
	_loadTradeDays(async) {
		let thiz = this;
		let model = this.vue.data;
		if (async == undefined)
			async = true;
		$.ajax({url: 'http://localhost:5665/get-trade-days', async: async, success: function(data) {
			model.lastTradeDay = data[data.length - 1];
			model.tradeDays = data;
			model.initMgrReady = thiz.isReady();
		}});
	}

	_initRequest() {
		let thiz = this;
		let model = this.vue.data;
		this._loadTradeDays(false);
		setInterval(function() {thiz._loadTradeDays();}, 1000 * 60 * 30); // 30 minutes
		window.addEventListener("message", function(evt) {
			if (evt.data && evt.data.cmd == 'GET_ANCHORS_CB') {
				model.anchros = evt.data.data;
				model.initMgrReady = thiz.isReady();
			}
		}, false);
		window.postMessage({cmd: 'GET_ANCHORS', data: {lastDay: new Date(), traceDaysNum: 60}}, '*');
	}

	_initUI() {
		let thiz = this;
		if ($('.watch-content-left > div').length < 7) {
			setTimeout(function() {thiz._initUI()}, 500);
			return;
		}
		let style = document.createElement('style');
		let css = ".my-info-item {border-bottom: solid 1px #222; padding-bottom: 10px; padding-top: 5px; width: 100%; } \n\
				.my-info-item table { border-collapse: collapse; border: 1px solid #ddd; width:100%; text-align: center; cursor:hander; } \n\
				.my-info-item table th {border: 1px solid #ddd; background-color: #ECECEC; height: 30px; font-weight: normal; color: #6A6B70;} \n\
				.my-info-item table td {border: 1px solid #ddd;} \n\
				.my-info-item .red {color: #990000;} \n\
				.my-info-item .green {color: #009900;} \n\
				.my-info-item .selcol {background-color: #EEE9E9;} \n\
				.w-1200 {width: 1400px;} \n\
				.watch-content-left {width: 1090px;} \n\
				";
		style.appendChild(document.createTextNode(css));
		document.head.appendChild(style);
		$('.top-ad').remove();
		let group = $('<div id="my-group-items"> </div>');
		let md1 = $('<div class="my-info-item p-r b-c-222" name="global-item"></div>');
		let md2 = $('<div class="my-info-item p-r b-c-222" name="time-degree-item" > </div>');
		let md3 = $('<div class="my-info-item p-r b-c-222" style="height: 70px;" name="zdfb-item"> </div>');
		let md4 = $('<div class="my-info-item p-r b-c-222" style="height: 400px;" name="anchor-fs-item" > </div>');
		let md5 = $('<div class="my-info-item p-r m-b-20  b-c-222" name="anchor-list-item" ></div>');
		let md6 = $('<div class="clearfix w-100p f-s-14 c-747474 toggle-nav-box finance-toggle-nav" name="tab-nav-item"> </div>');
		let md7 = $('<div class="my-info-item p-r b-c-222" style="" name="tab-nav-cnt-item">  </div>');
		group.append(md1).append(md2).append(md3).append(md4).append(md5).append(md6).append(md7);
		$('.watch-content-left > div:gt(1)').hide();
		// group.insertAfter($('.watch-chart-box'));
		$('.watch-content-left').append(group);
		this.initUIEnd = true;
		this.vue.data.initMgrReady = this.isReady();
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

	_loadAmount() {
		let thiz = this;
		// 两市成交额
		function cb(data) {
			let rs = {};
			for (let i = 0; i < data.length; i++) {
				let day = String(data[i].date);
				day = day.substring(0, 4) + '-' + day.substring(4, 6) + '-' + day.substring(6);
				data[i].amount = data[i].business_balance / 1000000000000; // 万亿
				rs[day] = data[i];
			}
			return rs;
		}
		let cu = new ClsUrl();
		cu.loadKline('sh000001', 100, 'DAY', function(data) {
			thiz.zsInfos.sh000001 = cb(data);
		});
		cu.loadKline('sz399001', 100, 'DAY', function(data) {
			thiz.zsInfos.sz399001 = cb(data);; // business_balance
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
			url: 'http://localhost:5665/query-by-sql/cls',
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

	_initUI() {
		let thiz = this;
		let model = this.vue.data;
		if (!this.zsInfos.data) {
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
		this.table = table;
		$('div[name="global-item"]').append(table);
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
			url: 'http://localhost:5665/get-time-degree?day=' + day,
			success: function(resp) {
				thiz._buildUI(resp);
			}
		});
	}

	_buildUI(d) {
		if (! this.canvas) {
			this.canvas = $('<canvas> </canvas>');
			$('div[name="time-degree-item"]').append(this.canvas);
		}
		let canvas = this.canvas;
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
		if (! this.chart) {
			let cc = this.canvas.parent();
			canvas.attr('width', cc.width());
			canvas.attr('height', cc.height());
			this.chart = new Chart(canvas.get(0), {type: 'line', data: cdata, options: {plugins: {legend: {display: false}}}});
			this.chart.resize(cc.width(), cc.height());
		} else {
			this.chart.data = cdata;
			this.chart.update();
		}
	}
}

class ZdfbMgr {
	constructor(vue) {
		this.vue = vue;
		this.table = null;
		let thiz = this;
		let r = function(elem, bindName, obj, attrName) {
			thiz._render(elem, bindName, obj, attrName);
		}
		this.vue.data.zdfb = {day: null, zt:'', dt:'', up:'', down:'', up_8: '', down_8:'', degree:'', r: r}; // 涨跌分布
		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
	}

	_onChangeDay(newVal, oldVal) {
		let thiz = this;
		if (! this.table) {
			this._buildUI();
		}
		if (newVal == this.vue.data.lastTradeDay) {
			this.loadNewestData(function(data) {
				thiz.updateData(data);
			});
		} else {
			this.loadHistoryData(newVal);
		}
	}

	_buildUI() {
		this.table = $('<table>'+
			"<tr class='red'> <th> 日期 </th> <th> 热度</th>  <th> 上涨数 </th> <td :bind='zdfb.up'> </td>  <th> 涨停 </th> " +
			"<td :bind='zdfb.zt'> </td> <th> 涨幅>8% </th> <td :bind='zdfb.up_8'> </td> </tr>" +
			"<tr class='green'> <th :bind='zdfb.day'> </th> <td :bind='zdfb.degree' :render='zdfb.r'> </td>  <th> 下跌数 </th> " +
			"<td :bind='zdfb.down'> </td>  <th> 跌停 </th> <td :bind='zdfb.dt'> </td> <th> 跌幅>8% </th>" +
			"<td :bind='zdfb.down_8'> </td> </tr> </table> ");
		this.table.find('td').css('width', '120px');
		$('div[name="zdfb-item"]').append(this.table);
		this.vue.mount(this.table);

		// 实时动态更新
		let model = this.vue.data;
		let thiz = this;
		setInterval(function() {
			let today = formatDay(new Date());
			if (today != model.lastTradeDay || model.lastTradeDay != model.curDay) {
				return;
			}
			let curTime = formatTime(new Date());
			if (curTime < '09:25' || curTime > '15:05') {
				return;
			}
			thiz.loadNewestData(function(data) {
				if (model.curDay != model.lastTradeDay)
					return;
				thiz.updateData(data);
			});
		}, 1000 * 30);
	}

	_render(elem, bindName, data, attrName) {
		elem = $(elem);
		if (attrName == 'degree') {
			if (data.degree && data.degree >= 50) {
				elem.removeClass('green');
				elem.addClass('red');
				elem.text(String(data.degree) + '°');
			} else if (data.degree) {
				elem.removeClass('red');
				elem.addClass('green');
				elem.text(String(data.degree) + '°');
			} else {
				elem.text('');
			}
		}
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
				udd.zt = udd.up_num;
				udd.dt = udd.down_num;
				udd.day = thiz.vue.data.lastTradeDay;
				cb(udd);
			}
		});
	}

	loadHistoryData(day) {
		let thiz =  this;
		let sql = `select day, 综合强度 as degree, substr(day, 6) as sday, fb from CLS_SCQX where day = '${day}'`;
		$.ajax({
			url: 'http://localhost:5665/query-by-sql/cls',
			data: {'sql': sql},
			success: function(resp) {
				let ds = JSON.parse(resp[0].fb);
				ds.day = day;
				ds.degree = resp[0].degree;
				thiz.updateData(ds);
			}
		});
	}

	updateData(data) {
		let a = ['day', 'zt', 'dt', 'up', 'down', 'up_8', 'down_8', 'degree'];
		let model = this.vue.data.zdfb;
		for (let k of a) {
			if (k == 'up_8') model[k] = data[k] + data['up_10'];
			else if (k == 'down_8') model[k] = data[k] + data['down_10'];
			else model[k] = data[k];
		}
	}
}

class AnchorsMgr {
	constructor(vue) {
		this.vue = vue;
		this.anchorView = null; // fenshi anchor 
		this.table = null; // list table
		let thiz = this;
		this.vue.addWatch('curDay', function(a, b) {thiz._onChangeDay(a, b);});
		this.vue.addWatch('newestAnchor', function(a, b) {thiz.onNewestAnchorUpdate(a, b);});
		this.vue.addWatch('curAnchorGroup', function(a, b) {thiz.onCurAnchorUpdate(a, b);});
	}

	_initUI() {
		let canvas = $('<canvas> </canvas>');
		$('div[name=anchor-fs-item]').append(canvas);
		let table = $('<table class="anchor-list" style="border-collapse: separate;border-spacing: 15px 10px;"> </table>');
		$('div[name=anchor-list-item]').append(table);
		this.table = table;

		let style = document.createElement('style');
		let css = "\
				.popup-container {z-index: 81100; display: none;  position: fixed; padding: 0; outline: 0; left:0px; top: 0px;width:100%;height:100%;}\n\
				.popup-container .content {position:absolute; background-color: #fcfcfc; border: solid 1px #d0d0d0;} \n\
				.popup-container p {padding: 0 20px 0 10px; } \n\
				.popup-container p:hover {background-color: #f0f0f0; } \n\
				.popup-container .anchors-wrap {position:absolute; width: 800px; height: 250px; background-color: #fcfcfc; border: solid 1px #aaa;} \n\
				.anchor-list .anchor-arrow {float:right; width:15px; text-align:center; border-left:1px solid #c0c0c0; background-color:#c0c0c0; width:15px; height:25px;} \n\
				.anchor-list .up {background-color: #FFD8D8;} \n\
				.anchor-list .down {background-color: #A0F1DC;} \n\
				";
		style.appendChild(document.createTextNode(css));
		document.head.appendChild(style);
		let popup = $('<div class="popup-container"> </div>');
		$(document.body).append(popup);
		popup.click(function() {$(this).css('display', 'none')});
		popup.on('mousewheel', function(event) {event.preventDefault();});

		this.anchorView = new AnchrosView(canvas.get(0));
		this.loadNewestAnchor();
	}

	_onChangeDay(newVal, oldVal) {
		let thiz = this;
		if (! this.anchorView) {
			this._initUI();
		}
		if (newVal == this.vue.data.lastTradeDay) {
		}
		this.vue.data.curAnchorGroup = this.calcGroups(newVal);
		this.anchorView.loadData(newVal, function( d) {thiz.updateAnchorName(d);});
	}

	updateAnchorName(data) {
		if (! data) return;
		let anchrosCP = this.vue.data.curAnchorGroup;
		for (let i = 0; i < data.length; i++) {
			let an = data[i];
			let key = an.symbol_code + '#' + an.float;
			let num = anchrosCP[key]?.num || 1;
			an.symbol_name += '' + num + '';
		}
	}

	loadNewestAnchor() {
		// 实时动态更新
		let model = this.vue.data;
		let thiz = this;
		this._loadNewestAnchor();
		setInterval(function() {
			let curTime = formatTime(new Date());
			if (curTime < '09:25' || curTime > '15:05' || model.curDay != model.lastTradeDay) {
				return;
			}
			thiz._loadNewestAnchor();
		}, 1000 * 30);
	}

	_loadNewestAnchor() {
		let model = this.vue.data;
		let thiz = this;
		if (model.curDay != model.lastTradeDay)
			return;
		this.anchorView.loadData(model.lastTradeDay, function(data) {
			if (! data)
				return;
			if (! model.newestAnchor || model.newestAnchor.length != data.length) {
				model.newestAnchor = data;
			}
			if (model.lastTradeDay == model.curDay)
				thiz.updateAnchorName(data);
		});
	}

	onNewestAnchorUpdate(newVal, oldVal) {
		if (newVal == oldVal || !newVal || newVal.length == 0) {
			return;
		}
		let model = this.vue.data;
		let lastDay = model.anchros[0][0].c_time.substring(0, 10);
		let cday = newVal[0].c_time.substring(0, 10);
		if (cday > lastDay) {
			model.anchros.unshift(newVal);
		} else if (cday == lastDay) {
			model.anchros[0] = newVal;
		}
		if (model.curDay >= cday) {
			model.curAnchorGroup = this.calcGroups(model.curDay);
		}
	}

	onCurAnchorUpdate(anchrosCP, oldVal) {
		let arr = [];
		for (let k in anchrosCP) {
			arr.push(anchrosCP[k]);
		}
		arr.sort(function(a, b) {return b.num - a.num});
		this.table.empty();
		let tr = null;
		let ROW_NUM = 4, COL_NUM = 7;
		let NUM = ROW_NUM * COL_NUM;
		for (let i = 0; i < NUM && i < arr.length; i++) {
			let item = arr[i];
			if (i % COL_NUM == 0) {
				if (item.num <= 2)
					break;
				tr = $('<tr> </tr>');
				this.table.append(tr);
			}
			let a = '<a href="https://www.cls.cn/plate?code=' + item.code + '" target=_blank> ' + item.name + '&nbsp;&nbsp;' + item.num + '&nbsp;&nbsp;</a>';
			let s = '<span class="anchor-arrow" code="' + item.code + '">  </span>';
			tr.append($('<td class="' + item.tag + '"> ' + a + s + ' </td>'));
		}
		let thiz = this;
		this.table.find('.anchor-arrow').click(function() {thiz.openChart(this);});
	}

	calcGroups(cday) {
		let model = this.vue.data;
		let anchrosDays = [];
		let anchrosCP = {};
		for (let i = 0, num = 0; i < model.anchros.length && num < 10; i++) { // 10 days
			let day = model.anchros[i][0].c_time.substring(0, 10);
			if (day > cday)
				continue;
			anchrosDays.push(day);
			++num;
			for (let j = 0; j < model.anchros[i].length; j++) {
				let an = model.anchros[i][j];
				let key = an.symbol_code + '#' + an.float;
				if (anchrosCP[key]) {
					anchrosCP[key].items.push(an);
				} else {
					anchrosCP[key] = {name: an.symbol_name, code: an.symbol_code, num: 0, tag: an.float, items: [an]};
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
			let day = model.anchros[i][0].c_time.substring(0, 10);
			rs.allDays.push(day);
			if (day > maxDay)
				continue;
			++num;
			rs.days.push(day);
			for (let j = 0; j < model.anchros[i].length; j++) {
				let an = model.anchros[i][j];
				if (an.symbol_code == code) {
					rs[an.float].push(an);
				}
			}
		}
		return rs;
	}

	openChart(elem) {
		elem = $(elem);
		let code = elem.attr('code');
		let model = this.vue.data;
		// console.log(code);
		let rs = this.getAnchrosByCode(code, model.curDay, 20);
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
		let ui = $('<div class="anchors-wrap"> </div>');
		let canvas = $('<canvas> </canvas> ');
		$('.popup-container').empty();
		$('.popup-container').css('display', 'block');
		$('.popup-container').append(ui);
		let tdRc = elem.parent().get(0).getBoundingClientRect();
		let dw = $(window.document).width();
		if (dw < tdRc.left + ui.width()) {
			ui.css({left: dw - ui.width() - 10, top: tdRc.bottom});
		} else {
			ui.css({left: tdRc.left, top: tdRc.bottom});
		}
		ui.append(canvas);
		canvas.width(ui.width());
		canvas.height(ui.height());
		canvas.attr('day', model.curDay);
		new Chart(canvas.get(0), {type: 'line', data: cdata, options: {}});
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
		this.loadTabNavi(this.curTabName || '涨停池');
	}

	_initUI() {
		let thiz = this;
		this.navi = $('<div class="toggle-nav-active">涨停池</div> <div >连板池</div>  <div >炸板池</div> <div >跌停池</div> <div >热度榜</div> <div >成交额</div> <div>笔记</div> <div>标记</div> </div>');
		$('div[name="tab-nav-item"]').append(this.navi);
		this.navi.width('110px');
		$('div[name="tab-nav-item"] > div').click(function() {
			if (! $(this).hasClass('toggle-nav-active')) {
				$('div[name="tab-nav-item"] > .toggle-nav-active').removeClass('toggle-nav-active');
				$(this).addClass('toggle-nav-active');
			}
			thiz.loadTabNavi($(this).text().trim());
		});
	}

	loadTabNavi(name) {
		let model = this.vue.data;
		this.curTabName = name;
		let thiz = this;
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
		if (model.curDay == model.lastTradeDay) {
			let ks = {'涨停池': 'up_pool', '连板池': 'continuous_up_pool', '炸板池': 'up_open_pool', '跌停池': 'down_pool'};
			let url = 'https://x-quote.cls.cn/quote/index/up_down_analysis?'
			let params = 'app=CailianpressWeb&os=web&rever=1&sv=8.4.6&type=' + ks[name] + '&way=last_px';
			params = new ClsUrl().signParams(params);
			url += params;
			$.ajax({
				url: url, 
				success: function(resp) {
					for (let i = resp.data.length - 1; i >= 0; i--) {
						if (resp.data[i].is_st) resp.data.splice(i, 1);
					}
					thiz.updateTabNavi(name, resp.data);
				}
			});
		} else {
			let sql = 'select * from cls_updown where day = "' + model.curDay + '" ';
			if (name == '涨停池') sql += ' and limit_up_days > 0';
			else if (name == '连板池') sql += ' and limit_up_days > 1';
			else if (name == '炸板池') sql += ' and limit_up_days = 0 and is_down = 0';
			else sql += ' and is_down = 1';
			$.ajax({
				url : 'http://localhost:5665/query-by-sql/cls',
				data: {'sql': sql},
				success: function(resp) {
					thiz.updateTabNavi(name, resp);
				}
			});
		}
	}

	loadMarkNavi(name) {
		let thiz = this;
		$.ajax({
			url: 'http://localhost:5665/mark-color',
			contentType: 'application/json',
			type: 'POST',
			data: JSON.stringify({op: 'get'}),
			success: function(resp) {
				thiz.updateTabNavi(name, resp);
			}
		});
	}

	loadAmountNavi(name) {
		let thiz = this;
		let day = this.vue.data.curDay;
		$.ajax({
			url: `http://localhost:5665/top100-vol?day=${day}`,
			contentType: 'application/json',
			type: 'GET',
			data: JSON.stringify({op: 'get'}),
			success: function(resp) {
				thiz.updateTabNavi(name, resp);
			}
		});
	}

	loadTopHotsNavi(name) {
		let thiz = this;
		let day = this.vue.data.curDay;
		$.ajax({
			url: 'http://localhost:5665/get-hots?day=' + day, type: 'GET',
			success: function(resp) {
				let rs = [];
				for (let k in resp) {
					resp[k].secu_name = resp[k].name;
					rs.push(resp[k]);
				}
				rs.sort(function(a, b) {return a.hots - b.hots});
				rs.splice(100, rs.length - 100);
				thiz.updateTabNavi(name, rs);
				thiz.loadTopAmounts(name, rs);
			}
		});
	}

	loadTopAmounts(name, rs) {
		let thiz = this;
		let day = this.vue.data.curDay;
		day = day.replaceAll('-', '');
		$.ajax({
			url: 'http://localhost:5665/iwencai', type: 'GET',
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
						rs[i].amount = map[code].amount;
						rs[i].amountIdx = map[code].amountIdx;
					} else {
						rs[i].amount = 0;
						rs[i].amountIdx = 0;
					}
				}
			}
		});
	}

	updateTabNavi(name, data) {
		let wrap = $('div[name=tab-nav-cnt-item]');
		wrap.empty();
		let model = this.vue.data;
		if (! data) {
			return;
		}
		let hd = null, ops = null;
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
				{text: '成交额', 'name': 'amount', width: 50, sortable: true, cellRender : amountRender, defined: true},
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
				{text: '热度', 'name': 'hots', width: 50, sortable: true},
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
		}

		let st = new StockTable(hd);
		window.st = st;
		st.setDay(model.curDay);
		st.setTradeDays(model.tradeDays);
		st.setData(data);
		if (name == '涨停池') {
			st.sortHeader('limit_up_days', 'asc');
		} else if (name == '连板池') {
			st.sortHeader('limit_up_days', 'desc');
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
		wrap.append(ops);
		wrap.append(st.table);
		if (name == '跌停池' && model.curDay == model.lastTradeDay) {
			this.loadDTInfo(st, window.st.day);
		}
	}

	loadDTInfo(st, day) {
		day = day || '';
		day = day.replaceAll('-', '');
		// ths_dtReason
		$.ajax({
			url: `http://localhost:5665/iwencai?q=${day} 跌停,非st,成交额,收盘价,涨跌幅`,
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
		let wrap = $('div[name=tab-nav-cnt-item]');
		wrap.empty();
		let re = new RichEditor('my-note');
		re.buildUI();
		wrap.append(re.ui);
	}
}


(function() {
	let model = {
		initMgrReady: false,
		anchros: null,
		newestAnchor: null,
		curAnchorGroup: null, //当前
		tradeDays: null, // ['YYYY-MM-DD', ...]
		lastTradeDay: null, //最新交易日期
		curDay: null, //当前选择的日期
	};
	let vue = new Vuex(model);
	new InitMgr(vue);
	new GlobalMgr(vue);
	new TimeDegreeMgr(vue);
	new ZdfbMgr(vue);
	new AnchorsMgr(vue);
	new TabNaviMgr(vue);
	window.vue = vue;
})();
