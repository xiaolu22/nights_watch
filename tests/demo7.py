from binance.client import Client

# 替换为你的API密钥和密钥
API_KEY = ''
API_SECRET = ''

client = Client(api_key=API_KEY, api_secret=API_SECRET)

# 查询 API Key 权限
permissions = client.get_account()
print(permissions)