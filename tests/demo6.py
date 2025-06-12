import asyncio
from binance import AsyncClient, BinanceSocketManager






# 替换为你的API密钥和密钥
# API_KEY = ''
# API_SECRET = ''

api_key = ''
api_secret = ''


# proxies = {
#     'http': 'http://127.0.0.1:7890',
#     'https': 'http://127.0.0.1:7890'
# }

# os.environ['HTTP_PROXY'] = "http://127.0.0.1:7890"
# os.environ['HTTPS_PROXY'] = "http://127.0.0.1:7890"

async def main():

    # 设置代理
    # connector = TCPConnector(proxy="http://127.0.0.1:7890")
    # 创建异步客户端
    client = await AsyncClient.create(
        api_key, 
        api_secret,
        testnet=True,
        https_proxy="http://127.0.0.1:7890")
    bm = BinanceSocketManager(client, user_timeout=60)


    us = bm.user_socket()

    async with us as tscm:
        print("成功连接到WebSocket，开始接收交易数据...")
        while True:
            res = await tscm.recv()
            print(res)

    # 防止主线程退出
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # 关闭WebSocket和客户端
        bm.stop_socket(user_data_socket)
        await client.close_connection()

if __name__ == "__main__":
    asyncio.run(main())