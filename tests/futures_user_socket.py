from binance import Client

api_key = ""
api_secret = ''
HTTP_PROXY = 'http://127.0.0.1:7890'


proxies = {
    'http': HTTP_PROXY,
    'https': HTTP_PROXY
}


if __name__ == '__main__':
    client =  Client(api_key, api_secret, testnet=True,  requests_params={'proxies': proxies})
    # account_info = client.futures_account()
    position_info = client.futures_position_information()
    print(position_info)