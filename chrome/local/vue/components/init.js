import {BasicTable, StockTable} from './table.js'

function registerComponents(app) {
    app.component('basic-table', BasicTable);
    app.component('stock-table', StockTable);
}

export default {
    registerComponents
}