
import time
import hashlib
import hmac
import websockets
import asyncio
import json


API_KEY = ''
API_SECRET = ''




ws_url = "wss://testnet.binancefuture.com/ws-fapi/v1"





async def connect_to_server():
    async with websockets.connect(ws_url, open_timeout=60, close_timeout=60) as websocket:
        print(f"连接到服务端: {ws_url}")
        try:
           
        
            # 订阅事件
            # subscribe_message = {
            #     "method": "SUBSCRIBE",
            #     "params": [
            #         "CONDITIONAL_ORDER_TRADE_UPDATE"
            #     ],
            #     "id": 1
            # }
            # await websocket.send(json.dumps(subscribe_message))
            # print("Subscription message sent")

            # account_message = {
            #     "method": "account.balance",
            #     "id":2
            # }

            

            # 时间戳
            timestamp = int(time.time() * 1000)
            # 签名
            signature = hmac.new(API_SECRET.encode(), f'timestamp={timestamp}'.encode(), hashlib.sha256).hexdigest()

            params = {
                "id": 1,
                "method": "account.balance",
                "params": {
                    "apiKey": API_KEY,
                    "timestamp": timestamp,
                    "signature": signature
                }
            }

            await websocket.send(json.dumps(params))
            print("account message sent")
            # 接收消息
            while True:
                message = await websocket.recv()
                print("Received message:", message)

            # # 向服务端发送消息
            # await websocket.send("客户端已连接")
            # # 接收服务端推送的消息
            # async for message in websocket:
            #     print(f"收到服务端消息: {message}")
        except websockets.ConnectionClosed:
            print("连接到服务端失败或已断开")

# 运行客户端
if __name__ == "__main__":
    asyncio.run(connect_to_server())

