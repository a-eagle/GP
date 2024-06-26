"""
同花顺 个股行业概念信息

https://www.iwencai.com/unifiedwap/result?w=%E4%B8%AA%E8%82%A1%E5%8F%8A%E8%A1%8C%E4%B8%9A%E6%9D%BF%E5%9D%97&querytype=stock

function nextPage() {
	let np = $('ul.pcwencai-pagination > li:last');
	np.find('a').get(0).click();
}

function loadPageData() {
	trs = $('.iwc-table-body.scroll-style2.big-mark > table tr');
	for (let i = 0; i < trs.length; i++) {
		let tds = trs.eq(i).find('td');
		let code = tds.eq(2).text();
		let name = tds.eq(3).text();
		let gn = tds.eq(7).text().trim();
        let hy = tds.eq(6).text().trim();
		console.log(code + '\t' + name + '\t' +  hy + '\t' +  gn);
	}
}

var lp = 0;
_lpID = setInterval(function() {
    loadPageData(); nextPage();
    lp++;
    if (lp > 53) {
        clearInterval(_lpID);
    }
}, 3000);


"""
import sys

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from db import ths_orm

def modify_hygn(obj : ths_orm.THS_GNTC, zsInfos):
    gn_code = []
    for g in obj.gn.split(';'):
        gcode = zsInfos.get(g, '')
        gn_code.append(gcode)
    gn_code = ';'.join(gn_code)
    hys = obj.hy.split('-')
    hy_2_code = zsInfos.get(hys[1], '')
    hy_3_code = zsInfos.get(hys[2], '')
    obj.gn_code = gn_code
    obj.hy_2_code = hy_2_code
    obj.hy_3_code = hy_3_code
    obj.hy_2_name = hys[1]
    obj.hy_3_name = hys[2]

def run_行业概念():
    def trim(s): return s.replace('【', '').replace('】', '').strip()

    f = open('D:/a.txt', 'r', encoding='utf8')
    lines = f.readlines()
    f.close()
    zsInfos = {}
    qr = ths_orm.THS_ZS.select().dicts()
    for q in qr:
        zsInfos[q.name] = q.code

    for line in lines:
        line = line.strip()
        if not line:
            continue
        code, name, hy, gn = line.split('\t', 3)
        hy = hy.strip()
        gn = gn.strip()
        if ' ' in gn:
            gn = gn.replace(' ', '')
        gns = list(map(trim, gn.split(';')))
        gn = ';'.join(gns)
        obj = ths_orm.THS_GNTC.get_or_none(ths_orm.THS_GNTC.code == code)
        if obj:
            if obj.hy != hy or obj.gn != gn:
                obj.hy = hy
                obj.name = name
                obj.gn = gn
                print('update ', code, name, hy, gn)
                modify_hygn(obj, zsInfos)
                obj.save()
        else:
            obj = ths_orm.THS_GNTC(code = code, name = name, gn = gn, hy = hy)
            modify_hygn(obj, zsInfos)
            obj.save()
            print('insert ', code, name,hy, gn)

    

