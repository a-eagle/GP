console.log('[iwencai] load chrome extions...loading zt info');

function loadCodeName() {
    let rs = [];
    let boxs = $('.tab-item > .tab-left > .tab-left-contentBox');
    for (let i = 0; i < boxs.length; i++) {
        let item = boxs.eq(i);
        let name = item.find('.basic-text').text();
        let code = item.find('.tab-left-code').text();
        // console.log(code, name);
        rs.push({code, name})
    }
    return rs;
}

function loadZTReason() {
    let rs = [];
    let boxs = $('.tab-item > .tab-right > .swiper-container > .swiper-wrapper > .swiper-table:eq(2) > .swiper-table-item');
    for (let i = 0; i < boxs.length; i++) {
        let item = boxs.eq(2);
        let ztReason = item.text();
        rs.push(ztReason);
    }
    return rs;
}

setTimeout(function() {
    let cn = loadCodeName();
    let zt = loadZTReason();
    for (let i = 0; i < cn.length; i++) {
        cn[i].ztReason = zt[i];
        console.log(cn[i]);
    }
}, 5000);


