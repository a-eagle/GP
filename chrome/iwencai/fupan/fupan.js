var klineUIMgr = new KLineUIManager();
var timeLineUIMgr = new TimeLineUIManager();
var volMgr = new VolUIManager();

//--------------------------K 线-------------------------------------------------
function buildCodeUI(code, config, parent) {
    if (! code || !code.trim()) {
        return;
    }
    const KLINE_VIEW_WIDTH = 750;
    const KLINE_VIEW_HEIGHT = 120;
    const VOL_HEIGHT = 0;
    const ROW_HEIGHT = KLINE_VIEW_HEIGHT + VOL_HEIGHT;
    let p = $('<p style="width: 100%; border-bottom: solid 1px #ccc; padding-left: 20px; height: ' + ROW_HEIGHT + 'px; " />');
    if (code.toLowerCase().indexOf('empty') >= 0) {
        parent.append(p);
        p.css({height: '4px', backgroundColor : '#abc'});
        return;
    }

    let infoDiv = $('<div style="float: left; width: 100px; height: ' + (ROW_HEIGHT + 1) + 'px; border-right: solid 1px #ccc; " /> ');
    let selInfoDiv = $('<div style="float: left; width: 150px; height: ' + (ROW_HEIGHT + 1) + 'px; border-right: solid 1px #ccc; " /> ');
   
    let klineUI = new KLineView(KLINE_VIEW_WIDTH, KLINE_VIEW_HEIGHT);
    klineUIMgr.add(klineUI);
    let timelineUI = new TimeLineView(300, KLINE_VIEW_HEIGHT);
    timeLineUIMgr.add(timelineUI);
    // let volUI = new VolView(klineUI, KLINE_VIEW_WIDTH, VOL_HEIGHT);
    // volMgr.add(volUI);

    p.append(infoDiv);
    p.append(selInfoDiv);
    let kv = $('<div style="float: left; width: ' + KLINE_VIEW_WIDTH + 'px; height: ' + ROW_HEIGHT + 'px" > </div>');
    $(klineUI.canvas).css('display', 'block');
    $(klineUI.canvas).css('border-bottom', 'solid 1px #ddd');
    kv.append(klineUI.canvas);
    // kv.append(volUI.canvas);
    p.append(kv);
    p.append(timelineUI.canvas);
    parent.append(p);

    klineUI.addListener('LoadDataEnd', function(event) {
        let info = klineUI.baseInfo;
        infoDiv.append(info.code + '<br/>' + info.name);
    });

    klineUI.addListener('VirtualMouseMove', function(event) {
        let dataArr = klineUI.dataArr;
        if (event.pos < 0 || !dataArr  ||  event.pos >= dataArr.length) {
            return;
        }
        let info = dataArr[event.pos];
        let txt = '' ;
        txt += '' + info.date + ' <br/><br/>';
        txt += '涨幅：';
        if (event.pos > 0) {
            let preInfo = dataArr[event.pos - 1];
            let zf = '' + ((info.close - preInfo.close) / preInfo.close * 100);
            zf = zf.substring(0, zf.indexOf('.') + 2);
            txt += '' + zf + '% <br/>';
        } else {
            txt += '- <br/>';
        }
        let money = '' + (info.money / 100000000);
        money = money.substring(0, money.indexOf('.') + 2);
        txt += '成交额：' + money + '亿<br/>';
        let rate = '' + parseInt(info.rate);
        txt += '换手率：' + rate + '%';
        selInfoDiv.html(txt);
    });

    klineUI.loadData(code, config);
    timelineUI.loadData(code);
}


function buildUI(codeArr, config) {
    let cntDiv = $('<div style="position: absolute; left: 0; top :0; width: calc(100% - 16px); height: 100%; overflow: auto; z-index: 9999999; background-color: #fff; border: solid 8px #aaa; padding-bottom: 10px;" />');
    $(document.body).append(cntDiv);

    codeArr.unshift('1A0001');
    codeArr.push('Empty');
    for (let i in codeArr) {
        let cur = codeArr[i];
        cur = cur.substring(0, 6);
        buildCodeUI(cur, config, cntDiv);
    }
    klineUIMgr.addListener('LoadAllDataEnd', function(evt) {
        if (config['hilightDate']) {
            for (let i = 0; i < klineUIMgr.klineUIArr.length; i++) {
                let klineUI = klineUIMgr.klineUIArr[i];
                let pos = klineUI.getPosIdxByDate(config['hilightDate']);
                klineUI.setHilightMouse(pos);
                klineUI.draw();
            }
        }
        volMgr.onLoadAllDataEnd();
    });
}

//--------------------------------------------------------------------------------------
政券 = ['881157', '885456', 'Empty','601099', '601136', '601059', '600906', '301315', '300380', '000712', '600095', '002670', '600621'];
// buildUI(政券, {beginDate : 20230713, endDate: 202301031});

数据要素 = ['886041', 'Empty', '603000', '605398', '301159', '301169',  '601858', '300807', '301299', '003007', '002235', '002777', '600602', '600633', '002095'];
// buildUI(数据要素, {beginDate : 20230713, endDate: 202301031} );

医药商业 = ['881143', 'Empty','603716', '301281', '600272', '603122', '301509', '301408', '000705', '300937', '600829', '301370'];
// buildUI(医药商业, {beginDate : 20230713, endDate: 202301031} );

环保 = ['881181', '000826', '605069', 'Empty', '301203', '002310', '688671', '605081', '603291', '600796', '600292', '301372', '301288', '301148', '301049', '300958', '300172' , '002887', '002778'];
// buildUI(环保, {beginDate : 20230713, endDate: 202301031} );

机器人 = ['', '600336', '301137', '002833', '603728', '603662', '002553', '002031', '002896', '300503', '002527', '300885', '', '', '', '', '', '', ];
减速器 = ['', '603767', '000678', '002833', '002031', '002553', '002472', '300904', '002896', '300503', '002527', '301255', '', ];
// buildUI(机器人, {beginDate : 20230713, endDate: 202301031} );

零售 = ['881158', '605188 国光连锁', '600280 中央商场', '002336 人人乐', '000715 中兴商业', '601086 国芳集团'];
// buildUI(零售, {beginDate : 20230801, endDate: 202301031} );


// 2023.08.30日启动
华为概念 = [ '885806', 'Empty', '002855 捷荣技术', '000536 华映科技', '300045 华力创通',
        '002654 万润科技','002642 荣联科技', '600895 张江高科', '601127 赛力斯', '002456 欧菲光', '603496 恒为科技',
         '603178 圣龙股份', '002771 真视通',  '603266 天龙股份', '002682 龙洲股份', '002457 青龙管业'  , '603985 恒润股份', '',
        'Empty ',
       '605588 冠石科技',  '002261 拓维信息', '000158 常山北明',
         '001268 联合精密', '000851 高鸿股份','300293 蓝英装备'  ];
//buildUI(华为概念, {beginDate : 20230815, endDate: 202301031, hilightDate : 20230830} );

// 2023.09.06日启动
光刻胶 = ['885864', 'Empty', '600895 张江高科', '300293 蓝英装备', '300537 广信材料', '603005 晶方科技', '300576 容大感光', '301421 波长光电', '', '', ];
 // buildUI(光刻胶, {beginDate : 20230801, endDate: 202301031} );

// 2023.09.18 日启动（涨停16， 大爆发）  次日直接就结束了， 一日游
// 实际上是 “ 华为汽车 ” 概念  （9个涨停）
汽车零部件 = ['881126', 'Empty', '601127 赛力斯', '', '', '', '', '', '', '', '', '', ''];
// buildUI(汽车零部件, {beginDate : 20230815, endDate: 202301031, hilightDate : 20230918} );

指数 = ['881164 传媒']
buildUI(指数, {beginDate : 20230815, endDate: 202301031, hilightDate : 20230918} );


