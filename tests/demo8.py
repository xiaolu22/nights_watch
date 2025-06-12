import requests
import json
import asyncio
import websockets
import hashlib
import hmac
import time

ws_base_url = "wss://fstream.binance.com/ws/"
base_url = "https://fapi.binance.com"
listen_key_path = "/fapi/v1/listenKey"


API_KEY = ''
API_SECRET = ''



# 请求头
headers = {
    'X-MBX-APIKEY': API_KEY,
    'X-MBX-SECRET-KEY': API_SECRET,
    'Content-Type': 'application/json'
}

# 时间戳
timestamp = int(time.time() * 1000)

# 签名
signature = hmac.new(API_SECRET.encode(), f'timestamp={timestamp}'.encode(), hashlib.sha256).hexdigest()

# 请求参数
params = {
    'timestamp': timestamp,
    'signature': signature
}

def get_listen_key():
    url = base_url + listen_key_path
    response = requests.post(url, headers=headers, params=params)
    print(response.json())
    if response.status_code == 200:
        return response.json()["listenKey"]
    else:
        return None


# def on_message(ws, message):
#     print("Received message:", message)

# def on_error(ws, error):
#     print("Error occurred:", error)

# def on_close(ws, close_status_code, close_msg):
#     print("WebSocket closed")

# def on_open(ws):
#     print("WebSocket opened")
#     # 订阅事件
#     subscribe_message = {
#         "method": "SUBSCRIBE",
#         "params": [
#             "CONDITIONAL_ORDER_TRADE_UPDATE"
#         ],
#         "id": 1
#     }
#     ws.send(json.dumps(subscribe_message))


async def subscribe_to_updates(uri):
    async with websockets.connect(uri) as websocket:
        print("WebSocket connection established")
        
        # 订阅事件
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [
                "CONDITIONAL_ORDER_TRADE_UPDATE"
            ],
            "id": 1
        }
        await websocket.send(json.dumps(subscribe_message))
        print("Subscription message sent")
        
        # 接收消息
        while True:
            message = await websocket.recv()
            print("Received message:", message)

if __name__ == "__main__":
    listen_key = get_listen_key()
    if listen_key:
        uri = ws_base_url + listen_key
        asyncio.run(subscribe_to_updates(uri))