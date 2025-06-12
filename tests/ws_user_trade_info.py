import asyncio
from binance import AsyncClient, BinanceSocketManager
from aiohttp import ClientTimeout
async def main():


    # api_key = ""
    # api_secret = ""


    api_key = ''
    api_secret = ''
    timeout = ClientTimeout(total=30)
    # initialise the client
    client = await AsyncClient.create(api_key, api_secret, testnet=True)
    # # 获取监听键
    # listen_key = await client.stream_get_listen_key()
    # print(f"Listen Key: {listen_key}")

    # 初始化 WebSocket 管理器
    bsm = BinanceSocketManager(client)
    us = bsm.user_socket()
    # 连接到用户数据流 WebSocket
    # async with bsm.user_socket() as user_socket:
    #     while True:
    #         msg = await user_socket.recv()
    #         if msg['e'] == 'executionReport':  # 处理订单更新事件
    #             print(f"Order Update: {msg}")
    #         elif msg['e'] == 'outboundAccountInfo':  # 处理账户信息更新事件
    #             print(f"Account Update: {msg}")
    #         elif msg['e'] == 'balanceUpdate':  # 处理余额更新事件
    #             print(f"Balance Update: {msg}")
    #         else:
    #             print(f"Other Event: {msg}")
    async with us as tscm:
            print("成功连接到WebSocket，开始接收交易数据...")
            while True:
                res = await tscm.recv()
                print(res)
    # 关闭客户端连接
    await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())