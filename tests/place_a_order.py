from binance.enums import *
from binance import Client


MAIN_API_KEY = ''
MAIN_API_SECRET = ''
HTTP_PROXY = 'http://127.0.0.1:7890'

proxies = {
    'http': HTTP_PROXY,
    'https': HTTP_PROXY
}


if __name__ == "__main__":

    client =  Client(MAIN_API_KEY, MAIN_API_SECRET, testnet=True,  requests_params={'proxies': proxies})

    symbol = 'BNBBTC'  # 交易对
    side = SIDE_BUY  # 交易方向：买入
    order_type = ORDER_TYPE_LIMIT  # 订单类型：限价单
    time_in_force = TIME_IN_FORCE_GTC  # 有效时间：直到取消
    quantity = 100  # 交易数量：100个BNB

    ticker_price = client.get_symbol_ticker(symbol='BNBBTC')
    current_price = float(ticker_price['price'])
    print(f"当前BNBBTC价格: {current_price}")

    # 设置限价单价格
    # 假设我们希望以低于当前市场价格5%的价格买入
    # 获取交易对的过滤器信息
    symbol_info = client.get_symbol_info(symbol)
    filters = symbol_info['filters']
    price_filter = next(filter(lambda f: f['filterType'] == 'PRICE_FILTER', filters), None)
    min_price = float(price_filter['minPrice'])
    max_price = float(price_filter['maxPrice'])
    tick_size = float(price_filter['tickSize'])

    # 设置限价单价格
    # 确保价格在允许范围内，并且符合价格步长
    limit_price = current_price * 0.95  # 假设以低于当前市场价格5%的价格买入
    limit_price = round(limit_price / tick_size) * tick_size  # 调整价格以符合tickSize
    limit_price = max(min_price, min(limit_price, max_price))  # 确保价格在允许范围内
    limit_price = round(limit_price, 8)  # 根据交易对的精度调整小数位数
    print(f"设置的限价单价格: {limit_price}")

    # 创建限价单
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            timeInForce=time_in_force,
            quantity=quantity,
            price=str(limit_price)  # 价格必须是字符串类型
        )
        print("订单已成功创建！")
        print(order)
            # 检查订单状态（可选）
        order_id = order['orderId']
        order_status = client.get_order(symbol=symbol, orderId=order_id)
        print("订单状态：")
        print(order_status)
    except Exception as e:
        print(f"下单失败：{e}")



