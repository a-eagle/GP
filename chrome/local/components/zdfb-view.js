class ZdfbView {
    constructor(canvas) {
        this.width = canvas.width;
        this.height = canvas.height;
        this.canvas = canvas;
        this.ctx = canvas.getContext("2d");

        this.BOTTOM_H = 35, this.DESC_H = 35, this.BOX_TITLE = 20;
        this.BOX_HEIGHT = this.height - this.BOTTOM_H - this.DESC_H - this.BOX_TITLE;
        this.ITEM_WIDTH = 35, this.ITEM_SPACE = 20;
    }

    getValue(attrs, data) {
        let val = 0;
        for (let a of attrs.split(',')) {
            val += data[a.trim()];
        }
        return val;
    }

    getMaxVal(infos, data) {
        let mv = 0;
        for (let info of infos) {
            mv = Math.max(mv, this.getValue(info.a, data));
        }
        return mv;
    }

    draw(data) {
        // console.log('[ZdfwView]', data)
        if (! data || !data.total) {
            return;
        }
        this.ctx.clearRect(0, 0, this.width, this.height);
        this.ctx.font = 'normal 12px Arial';
        let infos = [{t: '涨停', a:'11', color: '#f00', descColor: '#f00'}, {t: '>7%', a:'10,9,8', descColor: '#555'}, {t: '7~5%', a:'7,6'}, 
                     {t: '5~2%', a:'5,4,3'}, {t: '2~0%', a:'2,1'}, 
                     {t: '平', a:'0', color:'#555', descColor: '#555'}, 
                     {t: '0~2%', a:'-1,-2', color: '#25990E'},{t: '2~5%', a:'-3,-4,-5'}, {t: '5~7%', a:'-6,-7'}, 
                     {t: '7%<', a:'-8,-9,-10'}, {t: '跌停', a:'-11', descColor: '#25990E'}];
        let maxVal = this.getMaxVal(infos, data.zdfb);
        for (let i = 0; i < infos.length; i++) {
            this.ctx.beginPath();
            this.ctx.lineWidth = 0;
            if (infos[i].color) {
                this.ctx.strokeStyle = infos[i].color;
                this.ctx.fillStyle = infos[i].color;
            }
            let x = i * (this.ITEM_WIDTH + this.ITEM_SPACE);
            let val = this.getValue(infos[i].a, data.zdfb);
            let boxH = Math.max(val / maxVal * this.BOX_HEIGHT, 2);
            let sy = this.height - this.BOTTOM_H - this.DESC_H - boxH;
            this.ctx.rect(x, sy, this.ITEM_WIDTH, boxH);
            sy -= this.BOX_TITLE;
            let dx = (this.ITEM_WIDTH - this.ctx.measureText(String(val)).width) / 2;
            this.ctx.fillText(String(val), x + dx, sy + 15);
            this.ctx.stroke();
            this.ctx.fill();
            this.ctx.closePath();
        }

        for (let i = 0; i < infos.length; i++) {
            this.ctx.beginPath();
            this.ctx.lineWidth = 0;
            let x = i * (this.ITEM_WIDTH + this.ITEM_SPACE);
            let sy = this.height - this.BOTTOM_H - this.DESC_H;
            if (infos[i].descColor) {
                // this.ctx.strokeStyle = infos[i].descColor;
                this.ctx.fillStyle = infos[i].descColor;
            }
            let dx = (this.ITEM_WIDTH - this.ctx.measureText(infos[i].t).width) / 2;
            this.ctx.fillText(infos[i].t, x + dx, sy + 15);
            this.ctx.stroke();
            this.ctx.closePath();
        }

        // draw bottom rect
        // red
        let WIDTH = 11 * this.ITEM_WIDTH + 10 * this.ITEM_SPACE;
        let sx = 0;
        let ex = data.up / data.total * WIDTH;
        let sy = this.height - this.BOTTOM_H;
        let CH = 10, SP = 6;
        this.ctx.beginPath();
        this.ctx.moveTo(sx, sy);
        this.ctx.lineTo(ex, sy);
        this.ctx.lineTo(ex - SP, sy + CH);
        this.ctx.lineTo(sx, sy + CH);
        this.ctx.closePath();
        this.ctx.fillStyle = '#f00';
        this.ctx.fill();
        // gray
        sx = ex;
        ex = (data.up + data.zero) / data.total * WIDTH;
        this.ctx.beginPath();
        this.ctx.moveTo(sx + SP, sy);
        this.ctx.lineTo(ex, sy);
        this.ctx.lineTo(ex - SP, sy + CH);
        this.ctx.lineTo(sx, sy + CH);
        this.ctx.closePath();
        this.ctx.fillStyle = '#555';
        this.ctx.fill();
        // green
        sx = ex;
        ex = WIDTH;
        this.ctx.beginPath();
        this.ctx.moveTo(sx + SP, sy);
        this.ctx.lineTo(ex, sy);
        this.ctx.lineTo(ex, sy + CH);
        this.ctx.lineTo(sx, sy + CH);
        this.ctx.closePath();
        this.ctx.fillStyle = '#25990E';
        this.ctx.fill();

        // bottom text
        this.ctx.font = 'normal 16px Arial';
        sy = this.height - 8;
        this.ctx.fillStyle = '#f00';
        this.ctx.fillText('涨 ' + data.up, 5, sy);
        this.ctx.fillStyle = '#25990E';
        let text = '跌 ' + data.down;
        sx = WIDTH - this.ctx.measureText(text).width - 5;
        this.ctx.fillText(text, sx, sy);
    }
}

export {
    ZdfbView
}