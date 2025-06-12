import asyncio
import websockets

# 服务端地址和端口
SERVER_ADDRESS = "localhost"
SERVER_PORT = 6789

# 客户端集合，用于存储所有连接的客户端
connected_clients = set()

# 处理客户端连接
async def handle_client(websocket):
    print(f"客户端连接: {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print(f"收到消息: {message}")
            # 向所有客户端广播消息
            await broadcast(message)
    except websockets.ConnectionClosed:
        print(f"客户端断开连接: {websocket.remote_address}")
    finally:
        connected_clients.remove(websocket)

# 广播消息给所有连接的客户端
async def broadcast(message):
    if not connected_clients:
        print("没有连接的客户端")
        return
    tasks = []
    for client in connected_clients:
        try:
            tasks.append(asyncio.create_task(client.send(message)))
        except websockets.ConnectionClosed:
            print(f"客户端 {client.remote_address} 断开连接")
            connected_clients.remove(client)
    
    await asyncio.gather(*tasks, return_exceptions=True)  # 等待所有任务完成

# 启动 WebSocket 服务
async def start_server():
    async with websockets.serve(handle_client, SERVER_ADDRESS, SERVER_PORT):
        print(f"WebSocket 服务已启动，监听地址: ws://{SERVER_ADDRESS}:{SERVER_PORT}")
        await asyncio.Future()  # 运行直到手动停止

# 运行服务端
if __name__ == "__main__":
    asyncio.run(start_server())