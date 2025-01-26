
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
temp.src = chrome.extension.getURL('chart.js');
//temp.src = 'https://cdn.jsdelivr.net/npm/chart.js';
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('finance-inject.js');
temp.async = false;
document.documentElement.appendChild(temp);

window.addEventListener("message", function(evt) {
	if (evt.data && evt.data.cmd == 'GET_ANCHORS') {
		chrome.runtime.sendMessage(evt.data, function(resp) {
			window.postMessage({cmd: 'GET_ANCHORS_CB', data: resp});
		});
	} else if (evt.data && evt.data.cmd == 'GET_DEGREE') {
		chrome.runtime.sendMessage(evt.data, function(resp) {
			window.postMessage({cmd: 'GET_DEGREE_CB', data: resp});
		});
	}
}, false);