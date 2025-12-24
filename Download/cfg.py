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
