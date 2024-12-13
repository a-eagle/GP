top_zt_tips = [
    # {'title': ''}
]

holidays = [
    20250101,
]

top_hot_tips = [
    {'title': '[2024.12.13] 大消费 | 消费 | 零售 | 食品'},
    {'title': '[2024.12.13] 人工智能 | AI'},
    {'title': '[2024.12.13] 机器人 | 人型机器人 | 四足机器人'},

    {'title': '[2024.10.12] | 跨境支付'},
    {'title': '[2024.09.20] | 鸿蒙'},
    {'title': '[2024.08.28] | 折叠屏 | 苹果 | 消费电子'},
    #{'title': '[2024.08.27] | 房屋检测'},
    #{'title': '[2024.08.26] | 西部开发 | 西藏 | 西部大开发'},
    {'title': '[2024.08.26] | 固态电池'},
    {'title': '[2024.08.16] | 华为海思'},
    #{'title': '[2024.08.20] | 猴痘'},
    #{'title': '[2024.08.20] | 黑神话 | 悟空 | 游戏 | 传媒'},
    #{'title': '[2024.08.16] | MR | AI眼镜 | 眼镜'},
    #{'title': '[2024.7.23] | 无人驾使 | 车联网 | 汽车 | 网约车 | 半导体 | 芯片'},
    #{'title': '[2024.6.19] | 印制电路板 | PCB | 消费电子'},
]

if __name__ == '__main__':
    import win32gui, win32con
    hwnd = win32gui.FindWindow('#32770', '短线精灵')
    owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
    print(f'owner = 0x{owner :X}')
    parent = win32gui.GetParent(hwnd)
    print(f'parent = 0x{parent :X}')

    style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    #style &= win32con.WS_POPUP
    style = win32con.WS_OVERLAPPEDWINDOW
    win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

    win32gui.SetWindowLong(hwnd, win32con.GWL_HWNDPARENT, 0)
    #print(f'desktop={win32gui.GetDesktopWindow() :X}')
