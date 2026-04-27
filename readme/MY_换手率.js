警戒线换手率  0-100 20


BB = 100.0;
a = VOL * BB / SHGZG;
// a = MONEY * BB / DPLTSZ; 


IF (PERIODNAME == '周线') {
    a = a / 5;
} ELSE IF (PERIODNAME == '月线') {
    a = a / 20;
}

STICKLINE(CLOSE >= OPEN, 0, a, 9, 1), Colorff3232; // RGB(255, 50, 50);
STICKLINE(CLOSE < OPEN, 0, a, 9, 0), Color54fcfc; // RGB(84, 252, 252);

IF (a >= REF(a, 1) * 2) {
    STICKLINE(CLOSE >= OPEN, 0, a, 9, 1), Color3232ff; //  RGB(50, 50, 255);
    STICKLINE(CLOSE < OPEN, 0, a, 9, 0), Color3232ff; // RGB(50, 50, 255);
}

// A股
IF (CODETYPE == 1 AND STRLEFT(CODE, 2) != '88' ) {
        // 换手: a;
        换手五 : 5, colorblue, Linethick2;
        换手十 : 10, colormagenta, Linethick2;

        MAXBP  = HHV(a, 120);
        // 警戒线 : 警戒线换手率, coloryellow, Linethick2;

        HORLINE(MAXBP >= 警戒线换手率, 20, 0, 1), coloryellow, Linethick2;
}


STD_WIDTH := 9;
FILL := OPEN < CLOSE;
STICKLINE(a > 20, 20, a, STD_WIDTH,  FILL ),Color7812ff; // RGB(120, 18, 255);
换手 : a;
