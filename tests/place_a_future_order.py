from binance import Client

api_key = ""
api_secret = ''
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET, TIME_IN_FORCE_GTC

HTTP_PROXY = 'http://127.0.0.1:33210'


proxies = {
    'http': HTTP_PROXY,
    'https': HTTP_PROXY
}


# 查询订单状态
def get_order_status(symbol, order_id):
    try:
        order_status = client.futures_get_order(symbol=symbol, orderId=order_id)
        print("订单状态：")
        print(order_status)
    except Exception as e:
        print(f"查询订单状态失败：{e}")


def place_market_order(symbol, side, quantity):
    try:
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print("市价单已成功创建！")
        print(order)
        return order
    except Exception as e:
        print(f"下单失败：{e}")


if __name__ == '__main__':
    client =  Client(api_key, api_secret, testnet=True,  requests_params={'proxies': proxies})
    # account_info = client.futures_account()
    

    symbol = 'BTCUSDT'  # 交易对
    side = SIDE_BUY  # 交易方向：买入
    quantity = 0.01  # 交易数量
    price = 30000  # 限价单价格
    

    print("U订单开启")
    side = SIDE_SELL  # 交易方向：卖出
    # market_order = place_market_order(symbol, side, quantity)
    # # 查询订单状态
    # if market_order:
    #     get_order_status(symbol, market_order['orderId'])
    get_order_status(symbol,4333281946)
    # position_info = client.futures_position_information()
    # print(position_info)