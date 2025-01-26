var GPInfos = {
    FEN_SHI_DATA_ITEM_SIZE: 5,
    codes : [],
    // <code>_FS : { pre: xxx,  data: [ <时间，价格，成交额（元），分时均价，成交量（手）>, ...], canvas: HTMLElement }  分时数据
    // <code>_ELEM : {tr: jquery HTMLElement, fs_td: jquery HTMLElement, fs_canvas: HTMLElement}
};

/* 
    获取带henxin-v的参数地址
    @param url is http://d.10jqka.com.cn/v6/line/33_002261/01/today.js
    @return url is :
    http://d.10jqka.com.cn/v6/time/33_002230/1121.js?hexin-v=A-n8fhdIqX0iIpXJYlQnw1Eq-J5Gtt-XR6QBVoveZtQOxAfA0wbtuNf6EXkY
    http://d.10jqka.com.cn/v6/time/17_601360/last.js?hexin-v=A39quF26J9NEiCPPm5D5nUt4DlgMZNPK7bnX_xFMGQJ0B5EGGTRjVv2IZ1ki 
    http://d.10jqka.com.cn/v6/line/17_601360/01/last1800.js?hexin-v=A5SB-RLzjCIzYRjuRI8iTHwhZdkD7bhb-hFMHi51IJ-iGTrHVv2IZ0ohHLp9 
*/
function getdUrl_henxin(url) {
    let headElem = window['head_clone'];
    if (! headElem) {
        let cl = $(document.head).clone();
        cl.empty();
        headElem = window['head_clone'] = cl.get(0);
    }
    let scriptElem = window['head-script'];
    if (!scriptElem) {
        scriptElem = window['head-script'] = document.createElement("script");
    }
    scriptElem.setAttribute("src", url);
    headElem.appendChild(scriptElem);
    let src = scriptElem.src;
    // console.log(src);
    headElem.removeChild(scriptElem);
    return src;
}

function getCodeSH(code) {
    // 600xxx : 17;  300xxx 000xxx 002xxx : 33  48: 88:xxxx
    if (code[0] == '8') {
        return '48'; // 指数
    }
    let sh = code[0] == '6' ? '17' : '33'; 
    return sh;
}

// 分时线 url
function getFenShiUrl(code) {
    let sh = getCodeSH(code);
    let url = 'http://d.10jqka.com.cn/v6/time/' + sh + '_' + code + '/last.js';
    url = getdUrl_henxin(url);
    return url;
}

// 日线 url
function getKLineUrl(code) {
    let sh = getCodeSH(code);
    let url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/last1800.js';
    url = getdUrl_henxin(url);
    return url;
}

// 今日-日线 url
function getTodayKLineUrl(code) {
    let sh = getCodeSH(code);
    let url = 'http://d.10jqka.com.cn/v6/line/'+ sh + '_' + code + '/01/today.js';
    url = getdUrl_henxin(url);
    return url;
}

function loadFenShiData(code) {
    delete GPInfos[code + '_FS'];
    let url = getFenShiUrl(code);
    $.ajax({
        url: url, type: 'GET', dataType : 'text',
        success: function(data) {
            let idx = data.indexOf(':');
            let eidx = data.indexOf('}})');
            data = data.substring(idx + 1, eidx + 1); 
            data = JSON.parse(data);
            let rs = {};
            rs.pre = data.pre; // 昨日收盘价
            rs.data = data.data.split(/;|,/g);
            // 时间，价格，成交额（元），分时均价，成交量（手）
            for (let i = 0; i < rs.data.length; i += GPInfos.FEN_SHI_DATA_ITEM_SIZE) {
                rs.data[i + 0] = parseInt(rs.data[i]);
                rs.data[i + 1] = parseFloat(rs.data[i + 1]);
                rs.data[i + 2] = parseInt(rs.data[i + 2]);
                rs.data[i + 3] = parseFloat(rs.data[i + 3]);
                rs.data[i + 4] = parseInt(rs.data[i + 4]);
            }
            GPInfos[code + '_FS'] = rs;
            // console.log(rs);
            bindFenShiCanvas(code);
        }
    });
}

function bindFenShiCanvas(code) {
    let fsData = GPInfos[code + '_FS'];
    let fsElem = GPInfos[code + '_ELEM'];
    if (!fsElem || !fsData) {
        return;
    }
    drawFenShiCanvas(fsData, fsElem.fs_canvas.width, fsElem.fs_canvas.height, fsElem.fs_canvas);
    $(fsElem.fs_canvas).show();
}

function loadAllGPElements() {
    for (let i in GPInfos.codes) {
        let code = GPInfos.codes[i];
        if (GPInfos[code + '_ELEM'])
            delete GPInfos[code + '_ELEM'];
    }
    GPInfos.codes.length = 0;
    $('.iwc-table-body table').css('width', '');
    let trs = $('.iwc-table-body table tr');
    for (let i = 0; i < trs.length; i++) {
        let tr = $(trs[i]);
        let fs_td = null, fs_canvas = null;
        if (tr.children().size() > 8) {
            // fen shi <TD> is exitst
            fs_td = tr.children('td:eq(8)');
            fs_canvas = fs_td.children('canvas')[0];
        } else {
            fs_canvas = $('<canvas width="200" height="50" > </canvas>');
            fs_td = $('<td style="padding: 4px 2px 0px 2px;"> </td>');
            fs_td.append(fs_canvas);
            tr.append(fs_td);
            fs_canvas = fs_canvas[0];
        }
        let code = tr.children('td:eq(2)').text();
        GPInfos[code + '_ELEM'] = { tr, fs_td, fs_canvas };
        GPInfos.codes.push(code);
    }
}

function getFenShiDataMinMax(fsData, pointNN, itemIdx) {
    let minVal = 99999999999, maxVal = -minVal;
    let datas = fsData.data;
    for (let i = 0; i < datas.length; i += GPInfos.FEN_SHI_DATA_ITEM_SIZE) {
        if (i % pointNN != 0) {
            continue;
        }
        if (minVal > datas[i + itemIdx])
            minVal = datas[i + itemIdx];
        if (maxVal < datas[i + itemIdx])
            maxVal = datas[i + itemIdx];
    }
    return { minVal, maxVal };
}


// return a canvas HTMLElement
function drawFenShiCanvas(fsData, width, height, canvas) {
    let ctx = canvas.getContext('2d');
    const POINT_NN = 1;// 每几分钟选一个点
    const PRICE_IDX = 1; // 价格
    const PADDING_Y = 2; // 上下留点空间
    const PADDING_X = 25; // 右边留点空间
    let mm = getFenShiDataMinMax(fsData, POINT_NN, PRICE_IDX);
    if (mm.minVal > fsData.pre)
        mm.minVal = fsData.pre;
    if (mm.maxVal < fsData.pre)
        mm.maxVal = fsData.pre;
    
    let pointsCount = parseInt(4 * 60 / POINT_NN); // 画的点数
    let pointsDistance = (width - PADDING_X) / (pointsCount - 1); // 点之间的距离
    
    ctx.fillStyle = 'rgb(255, 255, 255)';
    ctx.lineWidth = 1;
    ctx.fillRect(0, 0, width, height);
    if (fsData.data[fsData.data.length - GPInfos.FEN_SHI_DATA_ITEM_SIZE + PRICE_IDX] >= fsData.pre)
        ctx.strokeStyle = 'rgb(255, 0, 0)';
    else
        ctx.strokeStyle = 'rgb(0, 204, 0)';
    ctx.beginPath();
    ctx.setLineDash([]);
    for (let i = 0, pts = 0; i < fsData.data.length; i += GPInfos.FEN_SHI_DATA_ITEM_SIZE) {
        if (i % POINT_NN != 0) {
            continue;
        }
        let x = pts * pointsDistance;
        let y = (height - PADDING_Y * 2) - (fsData.data[i + PRICE_IDX] - mm.minVal) * (height - PADDING_Y * 2) / (mm.maxVal - mm.minVal) + PADDING_Y;
        if (pts == 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
        ++pts;
    }
    ctx.stroke();

    // 画开盘价线
    ctx.strokeStyle = 'rgb(150, 150, 150)';
    ctx.beginPath();
    ctx.setLineDash([2, 4]);
    let y = (height - PADDING_Y * 2) - (fsData.pre - mm.minVal) * (height - PADDING_Y * 2) / (mm.maxVal - mm.minVal) + PADDING_Y;
    ctx.moveTo(0, y);
    ctx.lineTo(width - PADDING_X, y);
    ctx.stroke();
    // 画最高、最低价
    drawZhangFu(ctx, (mm.maxVal - fsData.pre) * 100 / fsData.pre, width, 10);
    drawZhangFu(ctx, (mm.minVal - fsData.pre) * 100 / fsData.pre, width, height - 5);
}

function drawZhangFu(ctx, zf, x, y) {
    if (zf >= 0) {
        ctx.fillStyle = 'rgb(255, 0, 0)';
    } else {
        ctx.fillStyle = 'rgb(0, 204, 0)';
    }
    zf = '' + zf;
    let pt = zf.indexOf('.');
    if (pt > 0) {
        zf = zf.substring(0, pt + 2);
    }
    zf += '%';
    let ww = ctx.measureText(zf).width;
    ctx.fillText(zf, x - ww, y);
}

function beautyfulUI() {
    $('.left-bar-wrapper').hide();
    $('.apps-bar').hide();
    $('.iwc-table-body table').css('width', '');
    $('.iwc-table-body').find('tr > td:nth-child(6)').each(function () {
        let txt = $(this).find('div').text();
        if (txt.indexOf('%') < 0) {
            $(this).find('div').text($(this).text() + '%');
        }
    });
    $('.iwc-table-body td').css('border-bottom', 'solid 1px #fa3');
    setTimeout(beautyfulUI, 500);
}

function buildFenShiTitleUI() {
    let titleBar = $('ul.iwc-table-header-ul');
    let tmp = '<li class="jsc-list-item" fmp_c="0" style="width: 180px;"> 分时图 </li>';
    titleBar.append(tmp);
    $('.iwc-table-fixed').hide();
    $('.iwc-table-body tr').height(50);
}

function loadAllFenShiData() {
    for (let i in GPInfos.codes) {
        let code = GPInfos.codes[i];
        if (!GPInfos[code + '_FS'])
            loadFenShiData(code);
        else
            bindFenShiCanvas(code);
    }
}

function pageChanged() {
    $('.iwc-table-body canvas').hide();
    setTimeout(function () {
        loadAllGPElements();
        loadAllFenShiData();
    }, 1500);
}

function listenChangePage() {
    $('.pcwencai-pagination-wrap > .pager a').on('click', pageChanged);
    $('.pcwencai-pagination-wrap > .drop-down-box li').on('click', pageChanged);
}

setTimeout(function () {
    buildFenShiTitleUI();
    beautyfulUI();
    listenChangePage();
    loadAllGPElements();
    loadAllFenShiData();
}, 4000);



