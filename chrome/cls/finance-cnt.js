
temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('ajax-hook.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('jquery-3.6.min.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('mybase64.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('finance-inject.js');
temp.async = false;
document.documentElement.appendChild(temp);

window.addEventListener("message", function(evt) {
	if (evt.data.cmd == 'GET_DOC_VIDEO_URLS') {
		chrome.runtime.sendMessage({cmd: 'GET_DOC_VIDEO_URLS', data: evt.data.data});
	} else if (evt.data.cmd == 'GET_WEEKLY_ZUOTI') {
		chrome.runtime.sendMessage({cmd: 'GET_WEEKLY_ZUOTI', data: evt.data.data});
	} else if (evt.data.cmd == 'GET_SPECIAL_ZUOTI') {
		chrome.runtime.sendMessage({cmd: 'GET_SPECIAL_ZUOTI', data: evt.data.data});
	}
	
}, false);