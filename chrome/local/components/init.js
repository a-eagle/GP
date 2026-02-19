import {BasicTable, StockTable} from './table.js'
import {TimeLineView} from './timeline-view.js'
import {TradeDatePicker, PopupView} from './popup.js'

function registerComponents(app) {
    app.component('BasicTable', BasicTable);
    app.component('StockTable', StockTable);
    app.component('TimeLineView', TimeLineView);
    app.component('TradeDatePicker', TradeDatePicker);
    app.component('PopupView', PopupView);
}

export default {
    registerComponents
}