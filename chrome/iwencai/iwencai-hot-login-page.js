/*
let temp = document.createElement('script');
temp.setAttribute('type', 'text/javascript');
temp.src = chrome.extension.getURL('ajax-hook.js');
temp.async = false;
document.documentElement.appendChild(temp);
*/

temp = document.createElement('script');
temp.setAttribute('type', 'text/javascript');
temp.src = chrome.extension.getURL('iwencai-hot-login-inject.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type', 'text/javascript');
temp.src = chrome.extension.getURL("canvas2image.js");
temp.async = false;
document.documentElement.appendChild(temp);

tmpArr = ["capatcha/a0.dib.bmp", "capatcha/b0.dib.bmp", "capatcha/c0.dib.bmp", "capatcha/d0.dib.bmp"];
for (i in tmpArr) {
    temp = document.createElement('img');
    temp.async = false;
    temp.style.display = 'hide';
    temp.setAttribute('id', 'template_bg_img' + i);
    temp.src = chrome.extension.getURL(tmpArr[i]);
    document.documentElement.appendChild(temp);
}

window.addEventListener("message", function (evt) {
    let msg = evt.data;
    console.log('Recevie Message(login-page[CNT]): ', msg);
    chrome.runtime.sendMessage(msg);
}, false);

/*
let norBtn = document.querySelector('#to_normal_login');
norBtn.click();

let accBtn = document.querySelector('#to_account_login');
accBtn.click();

let unameInput = document.querySelector('#uname');
unameInput.value = 'mx_642978864';

let passwdInput = document.querySelector('#passwd');
passwdInput.value = 'gaoyan2012';

unameInput.focus();
*/