import {BasicTable, StockTable} from './table.js'
import {TimeLineView} from './timeline-view.js'

function registerComponents(app) {
    app.component('basic-table', BasicTable);
    app.component('stock-table', StockTable);
    app.component('timeline-view', TimeLineView);
}

export default {
    registerComponents
}