import {BasicTable, StockTable} from './table.js'
import {TimeLineView} from './timeline-view.js'
import {TradeDatePicker} from './popup.js'

function registerComponents(app) {
    app.component('basic-table', BasicTable);
    app.component('stock-table', StockTable);
    app.component('timeline-view', TimeLineView);
    app.component('trade-date-picker', TradeDatePicker);
}

export default {
    registerComponents
}