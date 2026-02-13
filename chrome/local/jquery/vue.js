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

    function modelChanged() {
        let target = this;
        let value = target.model;
        if (! target._elem) {
            return true;
        }
        if (target.tag == 'text') {
            target._elem.data = toString(value);
            return true;
        }
        if (! target.render) {
            target._elem.innerHTML = toString(value);
            return true;
        }
        target._elem.innerHTML = '';
        target.render(target, target._elem);
        return true;
    }

    let targetHander = {
        set: function(target, attr, value) {
            if (attr == 'model') {
                target[attr] = value;
                modelChanged.apply(target);
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
            } else if (attr == '_elem') {
                if (target._elem instanceof Text)
                    target.tag = 'text';
                elif (target._elem instanceof Element)
                    target.tag = target._elem.tagName.toLowerCase();
            } else {
                target[attr] = value;
            }
            return true;
        },
        deleteProperty: function(target, attr) {
            if (attr == 'tag' || attr == '_elem' || attr == 'html' || attr == 'text' || attr == 'render')
                return false;
            if (attr == 'attrs')
                removeElemAttrs(target._elem, target[attr]);
            else if (attr == 'events')
                removeElemEvents(target._elem, target[attr]);
            delete target[attr];
            return true;
        },
    };

    // data.tag = 'button' | 'div' |  ... 'text'
    // data.attrs = {width : 100, ..., class: ...};
    //                  class = string | {className: true | false, ..},
    //                  style = string | {}
    // data.events = {click: func, ...} 
    // data.model = any data, inner content data 
    // data.render = func(data, elem),  render element content(childs),
    // auto build attrs:
    //   ._elem  .modelChanged() ._is_proxy
    function createElement(data) {
        if (! isObject(data))
            return null;
        let elem = null;
        if (data.tag == 'text') elem = document.createTextNode('');
        else elem = document.createElement(data.tag);
        return bindElement(data, elem);
    };

    function bindElement(data, elem) {
        if (! isObject(data) || !elem)
            return null;
        if (! data.attrs) data.attrs = {};
        if (! data.events) data.events = {};
        data.modelChanged = modelChanged;
        let tg = new Proxy(data, targetHander);
        tg._elem = elem;
        tg._is_proxy = true;
        notifyObject(tg);
        return tg;
    };

    window.V = {
        c: createElement, b: bindElement
    };
})();