// 要注意，开启fiddler，设置CROS response header

var templateImages = [];

function initTemplateImage() {
    if (templateImages.length != 0) {
        return;
    }
    // 4 template bg images
    for (let i = 0; i < 4; ++i) {
        let elem = document.getElementById('template_bg_img' + i);
        let canvas = document.createElement('canvas');
        let w = $(elem).width() || 340;  // 340;
        let h = $(elem).height() || 195;  // 195
        canvas.width = w;
        canvas.height = h;
        let ctx = canvas.getContext('2d');
        ctx.drawImage(elem, 0, 0, w, h);
        // let url = canvas.toDataURL('image/bmp');
        // console.log('loadImageData:', img.width, img.height, url);
        let imgData = ctx.getImageData(0, 0, w, h);
        let src = elem.src.substring(elem.src.lastIndexOf('/') + 1);
        // console.log('initTemplateImage ', i, imgData.data.length, imgData.width, imgData.height);
        let item = { 'img-idx': i, imgData: imgData, name: src };
        templateImages.push(item);
    }
}

// return 0（完全不等）- 100（完全相等）
function getPixelSimilerBlock(imgData1, imgData2, x, y, w, h, minFZ /*最小阀值 0 - 100 */) {
    let sv = 0;
    for (let i = 0; i < w; i++) {
        for (let j = 0; j < h; j++) {
            if (getPixelSimiler(imgData1, imgData2, x + i, y + j) >= minFZ) {
                ++sv;
            }
        }
    }
    return sv / (w * h) * 100;
}

function searchTemplateImageData() {
    let imgData = imgsInfo.bgImgData;
    const CW = 5, CH = 5;
    let valIdx = -1, similerVal = -1;

    if (!imgData) {
        imgsInfo.matchTemplateImgData = null;
        return null;
    }
    if (imgsInfo.matchTemplateImgData) {
        return;
    }

    for (let i = 0; i < templateImages.length; ++i) {
        let v = getPixelSimilerBlock(imgData, templateImages[i].imgData, 0, 0, CW, CH, 100);
        // console.log('searchTemplateImageData: ', i, templateImages[i].name, 'similerVal=', v);
        if (v > similerVal) {
            valIdx = i;
            similerVal = v;
        }
    }
    // console.log('searchTemplateImageData =', templateImages[valIdx]);
    imgsInfo.matchTemplateImgData = templateImages[valIdx].imgData;
}

function getPixelSimiler(imgData1, imgData2, x, y) {
    let p1 = (x + y * imgData1.width) * 4;
    let p2 = (x + y * imgData2.width) * 4;
    let r = Math.abs(imgData1.data[p1] - imgData2.data[p2]);
    let g = Math.abs(imgData1.data[p1 + 1] - imgData2.data[p2 + 1]);
    let b = Math.abs(imgData1.data[p1 + 2] - imgData2.data[p2 + 2]);
    let similer = 100 - (r + g + b) / 3 / 255 * 100;
    return similer;
}

function matchTemplateImage(fz, blockFZ) {
    if (!imgsInfo.bgImgData || !imgsInfo.matchTemplateImgData) {
        imgsInfo.matchBeginX = 0;
        imgsInfo.matchBeginY = 0;
        return;
    }
    if (imgsInfo.matchBeginX != 0) {
        // 已比较过了
        return;
    }
    const startX = 120, startY = 20;
    const CW = 10, CH = 30; // 比较区域的大小
    const FZ = fz || 50, BLOCK_FZ = blockFZ || 80; // 阀值
    for (let x = startX; x < imgsInfo.bgImgData.width - CW; x++) {
        // 竖向查找
        for (let y = startY; y < imgsInfo.bgImgData.height - CH; y++) {
            let sm = getPixelSimilerBlock(imgsInfo.bgImgData, imgsInfo.matchTemplateImgData, x, y, CW, CH, BLOCK_FZ);
            if (sm < FZ) {
                imgsInfo.matchBeginX = x;
                imgsInfo.matchBeginY = y;
                // console.log('matchTemplateImage: x=', x, 'y=', y);
                return;
            }
        }
    }
}

function tryMoveBlock() {
    if (imgsInfo.moveBockX) {
        return;
    }
    if (!imgsInfo.scaleBgWidth || !imgsInfo.realBgWidth) {
        return;
    }
    imgsInfo.moveBockX = imgsInfo.matchBeginX * imgsInfo.scaleBgWidth / imgsInfo.realBgWidth;
    // console.log('tryMoveBlock x=', imgsInfo.moveBockX);
    
    // start moving slider
    imgsInfo.blockMoving = true;
    let slider = document.querySelector('#slider');
    let evt = new MouseEvent('mousedown', { clientX: 10, clientY: 10, buttons: 1, which : 1});
    slider.dispatchEvent(evt); // send event to slider

    let ms = 0;
    for (let x = 0; x < imgsInfo.moveBockX - 10;) {
        let step = 5 + parseInt(Math.random() * 100) % 10;  // step is 5 ~ 15 px
        ms += 200 + parseInt(Math.random() * 100); // wait time 100 ~ 200 ms
        x += step;
        setTimeout(function (mx) {
            let evt = new MouseEvent('mousemove', { clientX: 10 + mx, clientY: 10 });
            document.dispatchEvent(evt); // send event to document
        }, ms, x);
    }
    setTimeout(function () {
        evt = new MouseEvent('mousemove', { clientX: 10 + imgsInfo.moveBockX, clientY: 10 });
        document.dispatchEvent(evt); // send event to document
        evt = new MouseEvent('mouseup', { clientX: 10 + imgsInfo.moveBockX, clientY: 10 });
        document.dispatchEvent(evt); // send event to document
        imgsInfo.blockMoving = false;
    }, ms + 200);
}

function makeBmp(w, h) {
    const BMP_HEADER_LEN = 14;
    const DIB_HEADER_LEN = 108;
    const arr = new Uint8Array(BMP_HEADER_LEN + DIB_HEADER_LEN + w * h * 4);

    // https://en.wikipedia.org/wiki/BMP_file_format#Example_2
    arr[0] = 0x42;      // 'B'
    arr[1] = 0x4D;      // 'M'
    arr[0x0A] = BMP_HEADER_LEN + DIB_HEADER_LEN;
    arr[0x0E] = DIB_HEADER_LEN;
    arr[0x1A] = 1      // Number of color planes being used
    arr[0x1C] = 32;     // Number of bits per pixel
    arr[0x1E] = 3;      // BI_BITFIELDS, no pixel array compression used

    arr[0x36] = 0xFF;   // R channel bit mask
    arr[0x3B] = 0xFF;   // G channel bit mask
    arr[0x40] = 0xFF;   // B channel bit mask
    arr[0x45] = 0xFF;   // A channel bit mask

    const view = new DataView(arr.buffer);
    // view.setUint16(2, DIB_HEADER_LEN + w * h * 4, true) // optional
    view.setInt32(0x12, w, true);
    view.setInt32(0x16, -h, true);  // top-down

    let bits = arr.subarray(BMP_HEADER_LEN + DIB_HEADER_LEN);
    return {bmp: arr, bits : bits};
}

function resetImgsInfo() {
    return {
        bgImgUrl: null,
        blockImgUrl: null,
        bgImgData: null,

        matchTemplateImgData: null,
        matchBeginX: 0, matchBeginY: 0,

        // bg image
        scaleBgWidth: 0, scaleBgHeight: 0,
        realBgWidth: 0, realBgHeight: 0,
        // block image
        scaleBlockWidth: 0, scaleBlockHeight: 0,
        realBlockWidth: 0, realBlockHeight: 0,
        scaleBlockY: 0, realBlockY: 0,

        moveBockX : 0, blockMoving : false,
    };
}

var imgsInfo = resetImgsInfo();

function loadImageData(img) {
    imgsInfo.realBgWidth = img.width;
    imgsInfo.realBgHeight = img.height;

    let canvas = document.createElement('canvas');
    canvas.width = img.width;
    canvas.height = img.height;
    let ctx = canvas.getContext('2d');
    ctx.drawImage(img, 0, 0, img.width, img.height);
    // let url = canvas.toDataURL('image/bmp');
    // console.log('loadImageData:', img.width, img.height, url);
    let imgData = ctx.getImageData(0, 0, img.width, img.height);
    imgsInfo.bgImgData = imgData;

    // download image
    // let bmp = makeBmp(img.width, img.height);
    // bmp.bits.set(imgData.data);
    // let blob = new Blob([bmp.bits.buffer], { type: 'image/bmp' });
    // let url = URL.createObjectURL(blob);
    // window.open(url, "_blank");

    setTimeout(checkImages, 300);
}

function downloadImage(src) {
    let img = new Image();
    img.setAttribute('crossOrigin', 'anonymous');
    img.onload = function () {
        loadImageData(img);
    };
    img.src = src;
    return img;
}

function checkImages() {
    let imgBG = document.querySelector('#slicaptcha-img');
    let imgBlock = document.querySelector('#slicaptcha-block');

    if (!imgBG || !imgBlock || !imgBG.complete || !imgBlock.complete || !imgBG.src || !imgBlock.src) {
        // image not load complete
        setTimeout(checkImages, 300);
        return;
    }
    if (imgsInfo.blockMoving) {
        setTimeout(checkImages, 300);
        return;
    }
    
    if (imgsInfo.bgImgUrl != imgBG.src) {
        imgsInfo = resetImgsInfo();
        imgsInfo.bgImgUrl = imgBG.src;
        imgsInfo.scaleBgHeight = parseInt(imgBG.style.height);
        imgsInfo.scaleBgWidth = parseInt(imgBG.style.width);
        bg = downloadImage(imgBG.src);
        return;
    }

    if (imgsInfo.blockImgUrl != imgBlock.src) {
        imgsInfo.blockImgUrl = imgBlock.src;
        // block = downloadImage(imgBlock.src);
        imgsInfo.realBlockHeight = 0;
        imgsInfo.realBlockWidth = 0;
        imgsInfo.scaleBlockY = 0;
        imgsInfo.realBlockY = 0;
    }

    // adjust block image size
    if (imgsInfo.realBlockWidth == 0) {
        // let ovW = imgBlock.style.width;
        // let ovH = imgBlock.style.height;

        imgsInfo.scaleBlockHeight = parseInt(imgBlock.style.height);
        imgsInfo.scaleBlockWidth = parseInt(imgBlock.style.width);
        // imgBlock.style.width = 'auto';
        // imgBlock.style.height = 'auto';
        // imgsInfo.realBlockHeight = $(imgBlock).height();
        // imgsInfo.realBlockWidth = $(imgBlock).width();
        // imgBlock.style.width = ovW;
        // imgBlock.style.height = ovH;
        let topY = parseInt(imgBlock.style.top) - $('#slicaptcha-title').height();
        imgsInfo.scaleBlockY = parseInt(topY);
    }
    // if (! imgsInfo.realBlockY) {
    //     imgsInfo.realBlockY = parseInt(imgsInfo.scaleBlockY * imgsInfo.realBgHeight / imgsInfo.scaleBgHeight);
    // }

    initTemplateImage();
    searchTemplateImageData();
    matchTemplateImage();
    tryMoveBlock();

    setTimeout(checkImages, 500);
}



window.addEventListener("message", function (evt) {
    console.log('Recevie Message(login-page[Inject]): ', evt.data);
}, false);

function initUserInfoUI() {
    let accBtn = document.querySelector('#to_account_login');
    accBtn.click();
    let unameInput = document.querySelector('#uname');
    unameInput.value = 'mx_642978864';
    let passwdInput = document.querySelector('#passwd');
    passwdInput.value = 'gaoyan2012';
    unameInput.focus();

    let loginBtn = document.querySelector("#account_pannel .submit_btn");
    loginBtn.click();
}

setTimeout(initUserInfoUI, 2500);
setTimeout(checkImages, 5000);

console.log('inject hot login ');