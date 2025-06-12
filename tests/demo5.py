import asyncio
import websockets
from binance import AsyncClient, BinanceSocketManager

api_key = '2'
api_secret = '1'

async def main():
    client = None
    reconnect_interval = 5
    
    while True:
        try:
            client = await AsyncClient.create(api_key, api_secret, testnet=True)
            bm = BinanceSocketManager(client)
            ts = bm.trade_socket('BNBBTC')
            
            async with ts as tscm:
                print("成功连接到WebSocket，开始接收交易数据...")
                while True:
                    res = await tscm.recv()
                    print(res)
                    
        except (websockets.ConnectionClosed, ConnectionResetError) as e:
            print(f"连接异常: {e}, {reconnect_interval}秒后重试...")
            await asyncio.sleep(reconnect_interval)
            reconnect_interval = min(reconnect_interval * 2, 60)
        except Exception as e:
            print(f"意外错误: {e}")
            break
        finally:
            if client:
                await client.close_connection()
                print("客户端连接已安全关闭")

if __name__ == "__main__":

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已安全退出")