(function() {
    function toString(obj) {
        if (obj == null || obj == undefined)
            return '';
        if (typeof(obj) == 'string')
            return obj;
        return obj.toString();
    };
    function isObject(obj) {
        return obj && obj.constructor && obj.constructor.name == 'Object';
    }
    function classNameToString(className) {
        if (className == null || className == undefined)
            return '';
        if (isObject(className)) {
            let rs = '';
            for (let k in className) {
                if (k != '_target' && className[k]) rs +=  k + ' ';
            }
            return rs;
        }
        return toString(className);
    };
    function styleToString(style) {
        if (style == null || style == undefined)
            return '';
        if (isObject(style)) {
            let rs = '';
            for (let k in style) {
                if (style[k] != null && style[k] != undefined && k != '_target')
                    rs +=  k + ':' + style[k] + '; ';
            }
            return rs;
        }
        return toString(style);
    };
    function notifyObject(obj) {
        if (! isObject(obj))
            return;
        for (let k in obj) {
            if (k != '_target')
                obj[k] = obj[k];
        }
    }

    let classNameHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            attrsObj[attr] = value;
            if (el) el.setAttribute('class', classNameToString(attrsObj));
            return true;
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            delete attrsObj[attr];
            if (el) el.setAttribute('class', classNameToString(attrsObj));
            return true;
        }
    };

    let styleHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            attrsObj[attr] = value;
            if (! el) return true;
            el.setAttribute('style', styleToString(attrsObj));
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            delete attrsObj[attr];
            if (! el) return true;
            el.setAttribute('style', styleToString(attrsObj));
            return true;
        }
    };

    let attrsHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            let aValue = value;
            if (attr == 'class' || attr == 'style') {
                if (value == null || value == undefined) {
                    aValue = null;
                    attrsObj[attr] = null;
                } else if (isObject(value)) {
                    value._target = attrsObj._target;
                    if (attr == 'class')
                        attrsObj[attr] = new Proxy(value, classNameHandler);
                    else
                        attrsObj[attr] = new Proxy(value, styleHandler);
                } else {
                    attrsObj[attr] = value;
                }
                if (attr == 'class')
                    aValue = classNameToString(value);
                else
                    aValue = styleToString(value);
            }
            if (el && attr != '_target') {
                if (aValue == null || aValue == undefined) 
                    el.removeAttribute(attr);
                else
                    el.setAttribute(attr, aValue);
            }
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            if (el) {
                el.removeAttribute(attr);
            }
            delete attrsObj[attr];
            return true;
        }
    };

    let eventsHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            if (el) {
                el.removeEventListener(attr, attrsObj[attr]);
                if (typeof(value) == 'function')
                    el.addEventListener(attr, value);
            }
            return true;
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            if (el) {
                el.removeEventListener(attr, attrsObj[attr]);
            }
            return true;
        }
    }

    function removeElemAttrs(elem, attrs) {
        if (! elem || !attrs) return;
        for (let k in attrs) {
            elem.removeAttribute(k);
        }
    };
    function removeElemEvents(elem, events) {
        if (! elem || !events) return;
        for (let k in events) {
            elem.removeEventListener(k, events[k]);
        }
    };

    let targetHander = {
        set: function(target, attr, value) {
            if (attr == 'html' || attr == 'text') {
                target['html'] = target['text'] = toString(value);
                if (! target._elem) {
                    return true;
                }
                if (target.tag == 'text') {
                    target._elem.data = target[attr];
                    return true;
                }
                if (attr == 'html') target._elem.innerHTML = target[attr];
                else target._elem.innerText = target[attr];
            } else if (attr == 'attrs' ) {
                removeElemAttrs(target._elem, target[attr]);
                if (isObject(value)) {
                    value._target = target;
                    target[attr] = new Proxy(value, attrsHandler);
                    notifyObject(target[attr]);
                }
            } else if (attr == 'events') {
                removeElemEvents(target._elem, target[attr]);
                if (isObject(value)) {
                    value._target = target;
                    target[attr] = new Proxy(value, eventsHandler);
                    notifyObject(target[attr]);
                }
            } else {
                target[attr] = value;
            }
            return true;
        },
        deleteProperty: function(target, attr) {
            if (attr == 'tag' || attr == '_elem' || attr == 'html' || attr == 'text')
                return false;
            if (attr == 'attrs')
                removeElemAttrs(target._elem, target[attr]);
            else if (attr == 'events')
                removeElemEvents(target._elem, target[attr]);
            delete target[attr];
            return true;
        },
    };

    // target.tag = 'button' | 'div' |  ... 
    // target.attrs = {width : 100, ..., class: ...};
    //                  class = string | {className: true | false, ..},
    //                  style = string | {}
    // target.events = {click: func, ...} 
    // target.html = inner html | target.text = inner text
    // target._elem
    window.createElement = function(target) {
        if (! isObject(target))
            return null;
        if (! target.attrs) target.attrs = {};
        if (! target.events) target.events = {};
        target._elem = document.createElement(target.tag);
        let tg = new Proxy(target, targetHander);
        notifyObject(tg);
        return tg;
    };

})();