MY_成交额
警戒线_低 0-100 5
警戒线_中 0-100 10
警戒线_高 0-100 20



JE :=  MONEY / 100000000;
成交额 :  JE;

// MA$1:MA(JE,N1);
// MA$2:MA(JE,N2);

W := 9;
a := JE;
// 倍量以上
IF (a >= REF(a, 1) * 2) {
    STICKLINE(OPEN >= CLOSE, 0, a, W, 0), RGB(50, 50, 255);
    STICKLINE(OPEN < CLOSE, 0, a, W, 1), RGB(50, 50, 255);
} ELSE {
    STICKLINE(CLOSE >= OPEN, 0, a, 9, 1), RGB(255, 50, 50);
    STICKLINE(CLOSE < OPEN, 0, a, 9, 0),  RGB(84, 252, 252);
}

// A股
IF (CODETYPE == 1 AND STRLEFT(CODE, 2) != '88' ) {
   MAXBP  = HHV(a, 200);
   HORLINE(MAXBP >= 警戒线_低, 警戒线_低, 0, 1), colorblue, Linethick2; 	
   HORLINE(MAXBP >= 警戒线_中, 警戒线_中, 0, 1), colormagenta, Linethick2; 
	HORLINE(MAXBP >= 警戒线_高, 警戒线_高, 0, 1),  coloryellow, Linethick2; 
}