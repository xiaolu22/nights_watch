import asyncio
import json
import websockets

# 替换为你需要订阅的市场对，例如 "btcusdt"
SYMBOL = "btcusdt"
# 替换为你需要订阅的数据类型，例如 "kline"（K线数据）或 "depth"（深度数据）
STREAM_TYPE = "kline"

# 构造 WebSocket URL
websocket_url = f"wss://stream.binance.com:9443/ws/{SYMBOL}@{STREAM_TYPE}"

async def binance_websocket():
    async with websockets.connect(websocket_url) as websocket:
        print(f"Connected to Binance WebSocket: {websocket_url}")
        
        while True:
            try:
                # 接收服务器发送的消息
                message = await websocket.recv()
                data = json.loads(message)
                
                # 处理接收到的数据
                print(data)
                
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed. Reconnecting...")
                break

# 运行 WebSocket 客户端
asyncio.run(binance_websocket())