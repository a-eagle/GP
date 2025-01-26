import threading, sys
import flask, flask_cors
import win32con, win32gui

sys.path.append(__file__[0 : __file__.upper().index('GP') + 2])
from Common import base_win

class Server:
    def __init__(self) -> None:
        self.app = flask.Flask(__name__)
        flask_cors.CORS(self.app)
        self.workThread = None

    def start(self):
        th = threading.Thread(target = self.runner, daemon = True)
        th.start()
        self.workThread = base_win.Thread()
        self.workThread.start()

    def runner(self):
        base_win.ThreadPool.instance().start()
        self.app.add_url_rule('/openui/<type_>/<code>', view_func = self.openUI)
        self.app.add_url_rule('/get-hots', view_func = self.getHots)
        self.app.run('localhost', 5665, use_reloader = False, debug = False)

    def openUI_Timeline(self, code, day):
        from Tck import timeline
        win = timeline.TimelinePanKouWindow()
        win.createWindow(None, (0, 0, 1200, 600), win32con.WS_OVERLAPPEDWINDOW)
        win32gui.ShowWindow(win.hwnd, win32con.SW_SHOW)
        win.load(code, day)
        win32gui.PumpMessages()

    def openUI_Kline(self, code, day):
        from Tck import kline_utils
        win = kline_utils.createKLineWindow(None)
        win.changeCode(code)
        win.klineWin.setMarkDay(day)
        win.klineWin.makeVisible(-1)
        win32gui.PumpMessages()

    def openUI(self, type_, code):
        if type_ == 'timeline':
            day = flask.request.args.get('day', None)
            self.workThread.addTask(code, self.openUI_Timeline, code, day)
        elif type_ == 'kline':
            day = flask.request.args.get('day', None)
            self.workThread.addTask(code, self.openUI_Kline, code, day)
        else:
            return {'code': 2, 'msg': f'Type Error: {type_}'}
        return {'code': 0, 'msg': 'OK'}
    
    def getHots(self):
        day = flask.request.args.get('day', None)
        from THS import hot_utils
        hz = hot_utils.DynamicHotZH.instance()
        if day and len(day) >= 8:
            rs = hz.getHotsZH(day)
        else:
            rs = hz.getNewestHotZH()
        m = {}
        for k in rs:
            fk = f'{k :06d}'
            m[fk] = rs[k]
        return m

if __name__ == '__main__':
    s = Server()
    s.runner()