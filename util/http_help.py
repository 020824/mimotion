import time
from urllib.parse import urlsplit

import requests


def request_with_retry(method, url, **kwargs):
    """对断连、超时和临时服务错误最多请求三次，不输出带凭据的URL。"""
    kwargs.setdefault('timeout', (10, 30))
    for attempt in range(3):
        delay = 2 ** (attempt + 1)
        try:
            response = requests.request(method, url, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as error:
            if attempt == 2:
                raise type(error)(f"{urlsplit(url).hostname} 请求失败，三次尝试均未成功") from None
        else:
            if response.status_code not in (429, 500, 502, 503, 504) or attempt == 2:
                return response
            try:
                delay = max(delay, min(float(response.headers.get('Retry-After', 0)), 60))
            except (TypeError, ValueError):
                pass
        print(f"{urlsplit(url).hostname} 请求暂时失败，{delay}秒后重试（{attempt + 2}/3）")
        time.sleep(delay)
