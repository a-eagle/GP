import platform

SYNC_DB_SERVER_BASE_URL = 'http://113.44.136.221:8090'

def getProxyUrl(url):
    return url
    if platform.node() != 'DESKTOP-P6GAAMF':
        return url
    url = urllib.parse.urlencode({'url': url})
    return 'http://113.44.136.221:8090/cls-proxy?' + url

def isServerMachine():
    REMOTE_NODE = 'hcss-ecs-3865'
    return platform.node() == REMOTE_NODE

if __name__ == '__main__':
    import requests
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
    }
    resp = requests.get('https://www.cls.cn/v3/transaction/anchor?app=CailianpressWeb&cdate=2025-12-25&os=web&sv=7.7.5&sign=6362bfb303fe8eedceca1c8d35760590', headers=headers)
    a = resp.content.decode()
    print(a)
    pass
