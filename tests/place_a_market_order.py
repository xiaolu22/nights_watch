from binance.client import Client
from binance.enums import SIDE_BUY, ORDER_TYPE_MARKET



MAIN_API_KEY = ''
MAIN_API_SECRET = ''
HTTP_PROXY = 'http://127.0.0.1:7890'

proxies = {
    'http': HTTP_PROXY,
    'https': HTTP_PROXY
}


if __name__ == "__main__":




    # 初始化客户端
    client = Client(MAIN_API_KEY, MAIN_API_SECRET, testnet=True, requests_params={'proxies': proxies})

    # 交易对和交易方向
    symbol = 'BNBUSDT'  # 交易对
    side = SIDE_BUY  # 交易方向：买入
    order_type = ORDER_TYPE_MARKET  # 订单类型：市价单
    quantity = 3  # 交易数量：100个BNB

    # 创建市价单
    try:
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity
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