from binance.cm_futures import CMFutures




API_KEY = ''
API_SECRET = ''




cm_futures_client = CMFutures()

# get server time
print(cm_futures_client.time())

cm_futures_client = CMFutures(key=API_KEY, secret=API_SECRET)

# Get account information
print(cm_futures_client.account())