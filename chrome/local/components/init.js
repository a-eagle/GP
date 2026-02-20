import {BasicTable, StockTable, PageniteView} from './table.js'
import {TimeLineView} from './timeline-view.js'
import {TradeDatePicker, PopupView} from './popup.js'
import {Plugin} from './plugins.js'

function registerComponents(app) {
    app.use(Plugin);
    
    app.component('BasicTable', BasicTable);
    app.component('StockTable', StockTable);
    app.component('PageniteView', PageniteView);
    app.component('TimeLineView', TimeLineView);
    app.component('TradeDatePicker', TradeDatePicker);
    app.component('PopupView', PopupView);
}

export default {
    registerComponents
}