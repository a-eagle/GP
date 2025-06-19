class PlateMgr {
    constructor() {
        this.data = null;
        this.detailUI = null;
        this.zfUI = null;
    }

    loadData() {
        this.detailUI = $('<div class="stock-detail"> </div>');
        this.columnUI = $(`<div class="plate-column-box"> </div>`);
        this.zfUI = $(`<div class="plate-column-box" style="font-size:16px;"> </div>`);
        $('#main').append(this.detailUI).append(this.columnUI).append(this.zfUI);
        let thiz = this;
        let code = getLocationParams('code');
        $.get(`/plate-info/${code}`, function(data) {
            console.log('[PlateMgr]', data);
            thiz.data = data;
            if (data.code != 200)
                return;
            thiz.buildUI(data.data);
        });
    }

    buildUI(data) {
        let title = $(`<span> ${data.secu_code} &nbsp; &nbsp; ${data.secu_name} </span>`);
        this.detailUI.append(title);
        let color = data.change >= 0 ? 'red' : 'green';
        let zf = $(`<span class="${color}"> ${(data.change * 100).toFixed(2)}% </span>`);
        this.detailUI.append(zf);
        
        let p1 = $(`<span class="plate-up-and-down" style="border-color: #f9d5d5; background-color: #fff1f1; color:#de0422;"> <img class="plate-up-and-down-icon" src="https://cdnjs.cls.cn/www/20200601/image/plate-up.png">  </img> <span style="float: right;"> 上涨${data.up_num}家 </span> </span>`);
        let p2 = $(`<span class="plate-up-and-down" style="border-color: ##e6e7ea; background-color: #f4f5fa; color:#666;"> <img class="plate-up-and-down-icon" src="https://cdnjs.cls.cn/www/20200601/image/plate-fair.png">  </img> <span style="float: right;">平盘${data.flat_num}家 </span> </span>`);
        let p3 = $(`<span class="plate-up-and-down" style="border-color: ##cae9e1; background-color: #e5fff8; color:#52c2a3;"> <img class="plate-up-and-down-icon" src="https://cdnjs.cls.cn/www/20200601/image/plate-down.png">  </img> <span style="float: right;">下跌${data.down_num}家 </span> </span>`);
        let pzt = $(`<span class="plate-up-and-down" style="order-color: #f9d5d5; background-color: #fff1f1;">涨停 ${data.limit_up_num}</span>`);
        let pdt = $(`<span class="plate-up-and-down" style="order-color: #cae9e1; background-color: #e5fff8;">跌停 ${data.limit_down_num}</span>`);
        this.columnUI.append(p1).append(p2).append(p3).append(pzt).append(pdt);
        
        let wc = data.week_change > 0 ? 'red' : 'green';
        let zfx1 = $(`<span> 近一周涨幅 </span> <span class="${wc}"> ${(data.week_change * 100).toFixed(2)}% </span> <span> &nbsp;&nbsp;| &nbsp;&nbsp;</span>`);
        let mc = data.month_change > 0 ? 'red' : 'green';
        let zfx2 = $(`<span> 近一月涨幅 </span> <span class="${mc}"> ${(data.month_change * 100).toFixed(2)}% </span> <span> &nbsp;&nbsp;| &nbsp;&nbsp;</span>`);
        let yc = data.year_change > 0 ? 'red' : 'green';
        let zfx3 = $(`<span> 近一年涨幅 </span> <span class="${yc}"> ${(data.year_change * 100).toFixed(2)}% </span> <span> &nbsp;&nbsp;| &nbsp;&nbsp;</span>`);
        this.zfUI.append(zfx1).append(zfx2).append(zfx3);
    }
}

class SubjectMgr {
    constructor() {
        this.ui = null;
        this.data = null;
    }

    loadData() {
        let thiz = this;
        let title = getLocationParams('name');
        $.get(`/subject/${title}`, function(data) {
            console.log('[SubjectMgr]', data);
            thiz.data = data;
            thiz.buildUI(data.data);
        });
    }

    buildUI(data) {
        this.ui = $('<div> </div>');
        for (let it of data.articles) {
            let sb = this.createSubject(it);
            this.ui.append(sb);
        }
        $('#main').append(this.ui);
    }

    createSubject(data) {
        let item = $('<div class="subject-item"> </div>');
        let time = new Date(data.article_time * 1000);
        time = formatDay(time) + '&nbsp;&nbsp;' + formatTime(time);
        item.append($(`<div class="small-title"> ${time} &nbsp; &nbsp; ${data.article_author}</div>`));
        let title = data.article_title;
        let wcnt = $('<div class="small-content"> </div>');
        let cnt = $(`<a href="https://www.cls.cn/detail/${data.article_id}" target=_blank>  </a>`);
        wcnt.append(cnt);
        if (title.indexOf('【') == 0 && title.indexOf('】') > 0) {
            let stitle = title.substring(0, title.indexOf('】') + 1);
            let detail = title.substring(title.indexOf('】') + 1);
            cnt.append($(`<strong> ${stitle} </strong>`));
            cnt.append($(`<span> ${detail} </span>`));
        } else {
            cnt.append($(`<strong> ${title} </strong><br/>`));
            let lines = data.article_brief.split('\n');
            for (let ln of lines)
                cnt.append($(`<span> ${ln} </span>`)).append('<br/>');
        }
        item.append(wcnt);
        let stocks = $(`<div class="stock-plate"> </div>`);
        for (let sk of data.stock_list) {
            let color = sk.RiseRange >= 0 ? 'red' : 'green';
            let a = $(`<a href="/stock?code=${sk.StockID}" target=_blank > <span> ${sk.name}</span> <span class="${color}"> ${sk.RiseRange.toFixed(2)}%</span> </a> `);
            stocks.append(a);
        }
        item.append(stocks);
        return item;
    }
}

$(document).ready(function() {
    let pm = new PlateMgr();
    pm.loadData();
    let sm = new SubjectMgr();
    sm.loadData();
});

    


