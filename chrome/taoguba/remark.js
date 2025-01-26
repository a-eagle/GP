// 显示收藏内容面
var vTaoGuBaRemarks = [];
var remarkBtn = null;
var infosUI = null;

// model = {id?: xx, info: {url: xx, subject: xx, author:xxx }, ui:xxx }
function bindItemUI(model) {
    for (let i in vTaoGuBaRemarks) {
        if (vTaoGuBaRemarks[i].id == model['id']) {
            // exists
            return;
        }
    }

    let item = $('<div style="width:100%; border-bottom: solid 1px #fa9;"> </div>');
    item.append($('<p> <b> ' + model.info.author + '</b> </p>'));
    item.append($('<p> <a href="' + model.info.url + '" target="_blank" > ' + model.info.subject + '</a> </p>'));
    model.ui = item;
    infosUI.append(item);
    vTaoGuBaRemarks.push(model);
}

function findExists(url) {
    let pos = url.indexOf('/Article/');
    if (pos > 0) {
        let epos = url.indexOf('/', pos + '/Article/'.length);
        let surl = url.substring(0, epos + 1);
        if (surl) {
            for (let i = 0; i < vTaoGuBaRemarks.length; i++) {
                let v = vTaoGuBaRemarks[i];
                if (v.info.url.indexOf(surl) == 0) {
                    // find it
                    return v;
                }
            }
        }
    }

    return null;
}

function beautyCurRemarkUI() {
    let model = findExists(window.location.href);
    if (model && model.ui) {
        model.ui.css('background-color', '#8a8');
    }
}

function remark() {
    let url = window.location.href;
    let emodel = findExists(url);
    if (emodel) {
        emodel.info.url = url;
        sendRemarkToServer(emodel);
        return;
    }
    // let author = $('.right-data-user > p').text().trim();
    let subject = $('#gioMsg').attr('subject');
    let author = $('#gioMsg').attr('username');
    let info = {author, subject, url};
    let model = {info : info};
    sendRemarkToServer(model);
}

function sendRemarkToServer(model) {
    // save to server 
    let mm = {};
    $.extend(true, mm, model);
    mm.info = JSON.stringify(mm.info);
    $.ajax({
        url: 'http://localhost:8071/save_taoguba_remark',
        method: 'POST',
        dataType: 'json',
        contentType : 'application/json',
        data: JSON.stringify(mm),
        success: function (res) {
            console.log('Success:  ', res);
            if (res.status == 'success') {
                model.id = res.id;
                bindItemUI(model);
                beautyCurRemarkUI();
                alert('Success: ' + res.msg);
            } else {
                alert('Respones Fail: ' + res.msg);
            }
        },
        error: function (xhr) {
            console.log('Net Error: ', model);
            alert('Net Error');
        }
    });
}

function loadUI() {
    let WIDTH = 300;
    let x = $(document).width() - WIDTH;
    let cnt = $('<div style="width: ' + WIDTH + 'px; height: 100%; left: ' + x + 'px; top: 50px; position:fixed; z-index: 999999; background-color: #ccc; " > </div>');
    infosUI = $('<div style="width: 100%; " />');
    let opts = $('<div style="width : 100%; margin-top: 20px;" >  </div>');
    remarkBtn = $('<button> Remark </button>');
    remarkBtn.click(function() {
        remark();
    });
    opts.append(remarkBtn);
    cnt.append(infosUI);
    cnt.append(opts);
    $(document.body).append(cnt);

    $.get('http://localhost:8071/query_taoguba_remark', function(rs) {
        for (i in rs) {
            rs[i].info = JSON.parse(rs[i].info);
            bindItemUI(rs[i]);
        }
        console.log(rs);
        beautyCurRemarkUI();
    });

    
}

function checkLogined() {
    if ($('.header-user').text().indexOf('登录/注册') < 0) {
        // 已登录
        return;
    }
    $('.header-user > a')[0].click();
    $('#userPanelName').val('18879269788');
    $('#userPanelPwd').val('gaoyan2012');
    $('#loginBtn').click();

    /*
    let thread = new Thread();
    let loginTask = new Task('login-task', 200, function(task, resolve) {
        console.log('login -1', $('.header-user > a')[0]);
        $('.header-user > a')[0].click();
        resolve();
    });
    thread.addTask(loginTask);
    
    let loginTask2 = new Task('login-task2', 500, function(task, resolve) {
        console.log('login -2');
        $('#userPanelName').val('18879269788');
        $('#userPanelPwd').val('gaoyan2012');
        $('#loginBtn').click();
        resolve();
    });
    thread.addTask(loginTask2);
    thread.addTask(new Task('stop', 1000, function(task, resolve) {
        console.log('login -3');
        thread.stop();
        resolve();
    }));
    thread.start();
    */
    console.log('auto login start');
}

loadUI();
checkLogined();