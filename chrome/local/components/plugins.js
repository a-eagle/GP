const Listener = {
    listeners : {},

    // listener = function(event, args)
    addListener(name, listener, args) {
        if (!name || !listener) {
            return;
        }
        let curs = this.listeners[name];
        if (! curs) {
            this.listeners[name] = curs = [];
        }
        curs.push({func: listener, args: args});
    },

    notifyListener(name, event) {
        let curs = this.listeners[name];
        if (! curs) {
            return;
        }
        for (let t of curs) {
            t.func(event, t.args);
        }
    }
};

const Store = {
    stores: {},
    getVal(name) {
        return this.stores[name];
    },
    setVal(name, val) {
        this.stores[name] = val;
    },
    wrap(name, val) {
        if (val == undefined) return this.getVal(name);
        else this.setVal(name, val);
    }
}

const Plugin = {
    install(app, options) {
        app.config.globalProperties.$addListener = function(name, listener, arg) {
            Listener.addListener(name, listener, arg);
        };
        app.config.globalProperties.$notifyListener = (name, event) => Listener.notify(name, event);
        app.config.globalProperties.$store = function(name, val) {
            return Store.wrap(name, val);
        }
    }
};

export {
    Plugin
}
