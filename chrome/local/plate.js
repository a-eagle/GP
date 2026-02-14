import utils from './components/utils.js'
import init from './components/init.js'
import {DefaultRender} from './components/table.js'

let App = {
    created() {
        // console.log('[App.created]');
    },
    data() {
        return {
            code: null, name: null,
            info: {},
        };
    },
    provide() {
        return {
            curDay: Vue.computed(() => this.curDay)
        };
    },
    methods: {
        formateZf(zf) {
            if (typeof zf == 'number')
                return (zf * 100).toFixed(2) + '%';
            return '';
        },
        onCurDayChanged(val) {
            this.curDay = val;
        },
    },
    created() {
        let code = utils.getLocationParams('code');
        let name = utils.getLocationParams('name');
        this.code = code;
        this.name = decodeURIComponent(name);
        axios.get(`/plate-info/${code}`).then((resp) => {
            // console.log(resp.data.data);
            this.info = resp.data.data;
        });
    },
};

// data.items = [ {name: 'zt-table-view', title: '涨停池'} ]

let TabNaviView = {
    data() {
        return {
            items: [{name: 'news-table-view', title: '新闻'}, {name: 'code-table-view', title: '个股'} ],
            curTabCntView: 'news-table-view',
        }
    },
    methods: {
        changeTab(item) {
            this.curTabCntView = item.name;
        }
    },
    template: `
        <div class="toggle-nav-box">
            <div v-for="item in items" :key="item.title" @click="changeTab(item)" :class="{'toggle-nav-active': item.name == curTabCntView}" > 
                {{item.title}}
            </div>
        </div>
        <keep-alive>  <component :is="curTabCntView">  </component> </keep-alive>
    `,
};

let NewsTabView = {
    data() {
        return {
            articles: null,
        }
    },
    beforeMount() {
        let code = utils.getLocationParams('code');
        let name = utils.getLocationParams('name');
        axios.get(`/subject/${name}?code=${code}`).then((resp) => {
            let data = resp.data.data;
            // console.log(data);
            this.articles = data.articles;
            for (let it of this.articles) {
                let time = new Date(it.article_time * 1000);
                it.day = utils.formatDate(time)
                it.time = utils.formatTime(time);
                it.url = `https://www.cls.cn/detail/${it.article_id}`;
                let title = it.article_title;
                if (title.indexOf('【') == 0 && title.indexOf('】') > 0) {
                    it.title = title.substring(0, title.indexOf('】') + 1);
                    let detail = title.substring(title.indexOf('】') + 1);
                    it.details = [detail];
                } else {
                    it.title = title;
                    it.details = [];
                    let lines = it.article_brief.split('\n');
                    for (let ln of lines)
                        it.details.push(ln);
                }
            }
        });
    },
    template: `
        <div class="subject-item" v-for="item in articles" >
            <div class="small-title"> {{item.day}} &nbsp;&nbsp;  {{item.time}} </div>
            <div class="small-content">
                <a :href="item.url" target="_blank">
                    <strong> {{item.title}}  </strong>
                </a>
                <div v-for="dt in item.details" > {{dt}} </div>
            </div>
            <div class="stock-plate" v-if="item.stock_list.length > 0"> 
                <template v-for="sk in item.stock_list">
                    <a :href="'/openui/kline/' + sk.StockID" target="hideFrame" >
                        <span> {{sk.name}} </span> 
                        <span :class="sk.RiseRange >= 0 ? 'red' : 'green'"> {{sk.RiseRange.toFixed(2)}}%</span>
                    </a> 
                </template>
            </div>
        </div>
    `,
};

let CodeTabView = {
    data() {
        return {
            url: null,
            day: null,
            columns: [
                {title: '', key:  '_index_', width: 50},
                {title: '股票/代码', key: 'code', width: 80},
                {title: '同花顺行业', key: 'ths_hy', width: 120},
                {title: '涨跌幅', key: 'change', width: 70, sortable: true},
                {title: '最高热度', key: 'maxHot', width: 70, sortable: true},
                {title: '热度', key: 'hots', width: 50, sortable: true},
                {title: '成交额', key: 'amount', width: 50, sortable: true},
                {title: '5日最高成交额', key: 'max_5_vol', width: 70, sortable: true, cellRender: DefaultRender.yRender},
                {title: '20日最高成交额', key: 'max_20_vol', width: 70, sortable: true, cellRender: DefaultRender.yRender},
                // {title: '流通市值', key: 'cmc', width: 70, sortable: true},
                {title: '简介', key: 'assoc_desc', width: 250},
                {title: '分时图', key: 'fs', width: 300},
            ],
        }
    },
    async mounted() {
        let day = utils.getLocationParams('day') || '';
        let code = utils.getLocationParams('code');
        if (! day) {
            let resp = await axios.get('/last-trade-day');
            day = resp.data.day;
        }
        this.day = day;
        this.url = `/plate/${code}?day=${day}`;
    },
    template: `
        <stock-table :columns="columns" :url="url" :day="day" > </stock-table>
    `,
};


function registerComponents(app) {
    init.registerComponents(app);
    app.component('tab-navi-view', TabNaviView);
    app.component('news-table-view', NewsTabView);
    app.component('code-table-view', CodeTabView);
}

export default {
    App,
    registerComponents
}