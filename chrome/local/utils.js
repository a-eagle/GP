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

function getLocationParams(name = null) {
    let url = window.location.href;
    let params = {};
    if (url.indexOf('#') > 0)
        url = url.substring(0, url.indexOf('#'));
    let q = url.indexOf('?');
    if (q < 0) return params;
    let ps = url.substring(q + 1);
    for (let it of ps.split('&')) {
        let ks = it.split('=');
        params[ks[0]] = ks[1];
    }
    if (name) {
        return params[name];
    }
    return params;
}