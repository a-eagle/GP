var rsIdx = 0;

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('ajax-hook.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('mybase64.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('jquery-3.6.min.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('link');
temp.setAttribute('type','text/css');
temp.setAttribute('rel','stylesheet');
temp.href = '//cdn.datatables.net/1.10.21/css/jquery.dataTables.min.css'
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = '//cdn.datatables.net/1.10.21/js/jquery.dataTables.min.js'
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('clsurl.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('kline.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('thread.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('table.js');
temp.async = false;
document.documentElement.appendChild(temp);

temp = document.createElement('script');
temp.setAttribute('type','text/javascript');
temp.src = chrome.extension.getURL('plate-inject.js');
temp.async = false;
document.documentElement.appendChild(temp);
//document.head.insertBefore(temp, document.head.children[rsIdx++]);

