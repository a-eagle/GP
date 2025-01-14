function initStyle() {
    let style = document.createElement('style');
    let css = "\
               .stock-detail button {color: #d838d8; margin-left: 20px; } \n\
            ";
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);
}

function clickBtn() {
    console.log('click button');
    let name = $(this).attr('name');
    let url = window.location.href;
    let idx = url.indexOf('code=');
    if (idx < 0)
        return;
    let code = url.substring(idx + 5);
    if (code.indexOf('sz') >= 0 || code.indexOf('sh') >= 0) {
        code = code.substring(2, 8);
    } else if (code.indexOf('cls') >= 0) {
        code = code.substring(0, 8);
    }
    $.get('http://localhost:5665/openui/kline/' + code);
}

function loadUI() {
    if ($('.stock-detail > div').length < 1) {
        return;
    }
    if ($('.stock-detail > span').length <= 1) {
        return;
    }
    if ($('.stock-detail > button').length > 0) {
        return;
    }
    var btn2 = $('<button name="Win_K"> 打开K线图-Win </button>');
    btn2.insertAfter($('.stock-detail > span:last'));
    //btn.click(clickBtn);
    btn2.click(clickBtn);
}

setInterval(loadUI, 500);
initStyle();
