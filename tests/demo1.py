import asyncio
from binance import AsyncClient
import json



async def main():
    api_key = ""
    api_secret = ""
    # initialise the client
    client = await AsyncClient.create(api_key, api_secret, testnet=True)

    

    # res = await client.get_exchange_info()
    res = await client.get_all_tickers()
    # print(json.dumps(res, indent=2))
    print(res)
    await client.close_connection()
if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())