from exchange.ws_client import UserDataClient
import time

client = UserDataClient()
client.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("停止监听")