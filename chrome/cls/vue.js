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
                if (className[k]) rs +=  k + ' ';
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
                if (style[k] != null && style[k] != undefined) 
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
            obj[k] = obj[k];
        }
    }

    let classNameHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            attrsObj[attr] = value;
            if (! el) return;
            el.setAttribute('class', classNameToString(attrsObj));
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            delete attrsObj[attr];
            el.setAttribute('class', classNameToString(attrsObj));
            return true;
        }
    };

    let styleHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            attrsObj[attr] = value;
            if (! el) return;
            el.setAttribute('class', styleToString(attrsObj));
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            delete attrsObj[attr];
            el.setAttribute('class', styleToString(attrsObj));
            return true;
        }
    };

    let attrsHandler = {
        set: function(attrsObj, attr, value) {
            let el = attrsObj._target._elem;
            let aValue = value;
            if (attr == 'className' || attr == 'style') {
                if (value == null || value == undefined) {
                    aValue = null;
                    attrsObj[attr] = null;
                } else if (isObject(value)) {
                    value._target = attrsObj._target;
                    if (attr == 'className')
                        attrsObj[attr] = new Proxy(value, classNameHandler);
                    else
                        attrsObj[attr] = new Proxy(value, styleHandler);
                } else {
                    attrsObj[attr] = value;
                }
                if (attr == 'className')
                    aValue = classNameToString(value);
                else
                    aValue = styleToString(value);
            }
            if (el) {
                if (aValue == null || aValue == undefined) 
                    el.removeAttribute(attr);
                else
                    el.setAttribute(attr, aValue);
            }
        },
        deleteProperty: function(attrsObj, attr) {
            let el = attrsObj._target._elem;
            if (el) {
                if (attr == 'className')
                    el.removeAttribute('class');
                else
                    el.removeAttribute(attr);
            }
            delete attrsObj[attr];
            return true;
        }
    };

    function removeElemAttrs(elem, attrs) {
        if (! elem || !attrs) return;
        for (let k in attrs) {
            elem.removeAttribute(k);
        }
    };
    function updateElemAttrs(elem, attrs) {
        if (! elem || !attrs) return;
        for (let k in attrs) {
            if (k == 'className')
               elem.setAttribute('class', classNameToString(attrs[j]));
            else if (k == 'style')
                elem.setAttribute('style', styleToString(attrs[j]));
            else
                elem.setAttribute(k, attrs[j]);
        }
    }
    function removeElemEvents(elem, events) {
        if (! elem || !events) return;
        for (let k in events) {
            elem.removeEventListener(k, events[k]);
        }
    };
    function updateElemEvents(elem, events) {
        if (! elem || !events) return;
        for (let k in events) {
            elem.addEventListener(k, events[k]);
        }
    }

    let targetHander = {
        set: function(target, attr, value) {
            if (attr == 'html' || attr == 'text') {
                target[attr] = toString(value);
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
                target[attr]._target = target;
                if (isObject(value)) {
                    target[attr] = new Proxy(value, attrsHandler);
                    notifyObject(target[attr]);
                }
            } else if (attr == 'events') {
                removeElemEvents(target._elem, target[attr]);
                target[attr]._target = target;
                if (isObject(value)) {
                    target[attr] = new Proxy(value, eventsHandler);
                    notifyObject(target[attr]);
                }
            }
            target[attr] = value;
            return true;
        },
        deleteProperty: function(target, attr) {
            if (attr == 'tag' || attr == 'attrs' || attr == 'events' || attr == '_elem' || attr == 'html' || attr == 'text')
                return false;
            delete target[attr];
            return true;
        },
    };

    // target.tag = 'button' | .. | 'text'
    // target.attrs = {width : 100, ..., className: ...};
    //                  className = string | {class: true | false, ..},
    //                  style = string | {}
    // target.events = {click: func, ...} 
    // target.html = inner html | target.text = inner text
    // target._elem
    createElement = function(target) {
        if (! isObject(target))
            return null;
        let elem = null;
        if (! target.attrs) target.attrs = {};
        if (! target.events) target.events = {};
        if (target.tag == 'text') {
            elem = document.createTextNode(target.text | target.html);
        } else {
            elem = document.createElement(target.tag);
        }
        target._elem = elem;
        let tg = new Proxy(target, targetHander);
        notifyObject(tg);
        return tg;
    };

})();