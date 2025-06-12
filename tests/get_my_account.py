# 获取我的账户信息



from binance import Client


MAIN_API_KEY = ''
MAIN_API_SECRET = ''
HTTP_PROXY = 'http://127.0.0.1:7890'


proxies = {
    'http': HTTP_PROXY,
    'https': HTTP_PROXY
}


if __name__ == '__main__':
    client =  Client(MAIN_API_KEY, MAIN_API_SECRET, testnet=True,  requests_params={'proxies': proxies})
    account_info = client.get_account()
    print(account_info)







