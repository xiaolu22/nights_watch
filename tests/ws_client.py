import asyncio
from socket import timeout
import websockets
import json
# 服务端地址和端口
SERVER_ADDRESS = "wss://fstream.binance.com/ws/w31geYFK5Pe9ggOJy3mJdnpZK9mK1FblGgHtN67Y64YLL4NuxQYlCfPEDo3eBKPP"

# 客户端连接到服务端
async def connect_to_server():
    async with websockets.connect(SERVER_ADDRESS, open_timeout=60, close_timeout=60) as websocket:
        print(f"连接到服务端: {SERVER_ADDRESS}")
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

            account_message = {
                "method": "account.balance",
                "id":2
            }
            await websocket.send(json.dumps(account_message))
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