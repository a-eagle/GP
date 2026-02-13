
let PopupWindow = {
    zIndex : 8000,

    // return an Element
    _createPopup(onClose) {
        let popup = document.createElement('div');
        popup.className = 'popup-window';
        popup.style.zIndex = this.zIndex ++;
        popup.addEventListener('click', function(evt) {
            evt.stopPropagation();
            let cl = evt.target.classList;
            if (cl.contains('popup-window')) {
                onClose(popup);
                popup.remove();
            }
        });
        popup.addEventListener('wheel', function(evt) {
            // evt.preventDefault();
            // evt.stopPropagation();
        });
        return popup;
    },

    // content: is a VNode (Vue.h )
    // config = {hideScrollBar: true}
    // onClose: function
    open(content, config, onClose) {
        if (! Vue.isVNode(content)) {
            return null;
        }
        let popup = this._createPopup(function() {
            Vue.render(null, popup); // unmount
            if (config?.hideScrollBar)
                document.body.classList.remove('no-scroll');
            if (onClose) onClose();
        });
        Vue.render(content, popup);
        document.body.appendChild(popup);
        if (config?.hideScrollBar)
            document.body.classList.add('no-scroll');
        return popup;
    },
};

export {
    PopupWindow,
}