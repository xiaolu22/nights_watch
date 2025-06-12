import asyncio

from websockets import ConnectionClosedError
from ..utils.logger import logger
from ..config import SUB_API_KEY, SUB_API_SECRET, TESTNET, HTTP_PROXY, SUB_ORDER_TRADE_RATIO
from binance import AsyncClient, BinanceWebsocketClosed
from concurrent.futures import ThreadPoolExecutor
from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_LIMIT, ORDER_TYPE_MARKET, TIME_IN_FORCE_GTC
from enum import Enum
import random
import time
# from binance.enums import TIME_IN_FORCE_GTC





class OrderAction(Enum):
    """
    定义交易订单的开仓平仓操作类型。
    包含开多仓、开空仓、平多仓、平空仓四种操作。
    """
    OPEN_LONG = 'OPEN_LONG' # 开多仓
    OPEN_SHORT = 'OPEN_SHORT' # 开空仓
    CLOSE_LONG = 'CLOSE_LONG' # 平多仓
    CLOSE_SHORT = 'CLOSE_SHORT' # 平空仓



class OrderManager:
    def __init__(self, ws_client):
        self.main_client = ws_client
        self.sub_client = None
        # self._prepare_sub_account()
        asyncio.create_task(self._prepare_sub_account())
        # self._initialize_thread_pool()
        self.compensate_queue = asyncio.Queue()
        self.need_close_symbols = set()
        self.main_positions = {'LONG': 0.0, 'SHORT': 0.0}
        self.sub_positions = {'LONG': 0.0, 'SHORT': 0.0}
        # self.lock = asyncio.Lock()
        asyncio.create_task(self.init_positions())  # 初始化时异步加载仓位信息
        
        for _ in range(5):
            asyncio.create_task(self.compensate_consumer())

    async def init_positions(self):
        """
        初始化主账户和子账户的持仓信息， 双向持仓模式
        {
            "symbol": {
                "position_side": "position_quantity",
                "LONG": 50.0
            }
        } 
        """
        try:
            # 初始化主账户持仓
            main_positions = await self.main_client.websocket.futures_position_information()
            for pos in main_positions:
                symbol = pos['symbol']
                position_side = pos['positionSide']
                if symbol not in self.main_positions:
                    self.main_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                if position_side == 'LONG':
                    self.main_positions[symbol]['LONG'] = float(pos['positionAmt'])
                elif position_side == 'SHORT':
                    self.main_positions[symbol]['SHORT'] = float(pos['positionAmt'])
                else:
                    logger.warning(f"未知的仓位方向: {position_side}")
            # 初始化子账户持仓（如果已配置API）
            if self.sub_client:
                sub_positions = await self.sub_client.futures_position_information()
                for pos in sub_positions:
                    symbol = pos['symbol']
                    position_side = pos['positionSide']
                    if symbol not in self.sub_positions:
                        self.sub_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                    if position_side == 'LONG':
                        self.sub_positions[symbol]['LONG'] = float(pos['positionAmt'])
                    elif position_side == 'SHORT':
                        self.sub_positions[symbol]['SHORT'] = float(pos['positionAmt'])
                    else:
                        logger.warning(f"未知的仓位方向: {position_side}")
            logger.info(f"主账户和子账户持仓初始化完成, 主账户当前仓位: {self.main_positions}, 子账户当前仓位: {self.sub_positions}")
        except Exception as e:
            logger.error(f"初始化持仓信息失败: {str(e)}", exc_info=True)

    def _initialize_thread_pool(self):
        self.thread_pool = ThreadPoolExecutor(max_workers=5)

    async def _prepare_sub_account(self):

        try:
            if SUB_API_KEY and SUB_API_SECRET:
                self.sub_client = AsyncClient(SUB_API_KEY, SUB_API_SECRET, testnet=TESTNET, https_proxy=HTTP_PROXY)
                server_time = await self.sub_client.get_server_time()
                local_time = int(time.time() * 1000)
                time_delta = server_time['serverTime'] - local_time
                
                # Apply time delta to client configuration
        
                self.sub_client.time_offset = time_delta

            else:
                logger.warning('未配置副账户API密钥，跟单功能不可用')
        except Exception as e:
            logger.error(f"初始化副账户失败: {str(e)}")
    # def __init__(self, ws_client):
    #     self.ws_client = ws_client

    async def compensate_consumer(self):
        while True:
            try:
                order_id, message, main_order_map = await self.compensate_queue.get()
                retry_count = 0
                max_notify = 15
                max_discard = 30
                while retry_count < max_notify:
                    try:
                        await self.compensate_close_position(order_id, message, main_order_map, from_queue=True)
                        break
                    except Exception as e:
                        logger.error(f"补偿队列消费异常: {str(e)}，第{retry_count}次重试", exc_info=True)
                        if retry_count == max_notify:
                            # todo 添加app通知逻辑
                            # 发送飞书请求人工介入
                            # 这里请替换为你自己的飞书通知实现
                            logger.warning(f"补偿平仓连续{max_notify}次失败，发送飞书请求人工介入，订单ID: {order_id}")
                        if retry_count >= max_discard:
                            logger.error(f"补偿平仓连续{max_discard}次失败，丢弃该消息，订单ID: {order_id}")
                            break
                    finally:
                         retry_count += 1
            except Exception as e:
                logger.error(f"补偿队列消费异常: {str(e)}", exc_info=True)
            await asyncio.sleep(1)

    # 未验证
    def get_order_action(self, msg):
        """
        根据订单消息判断订单操作类型（开仓或平仓）。
        :param msg: 订单消息
        :return: OrderAction 枚举类型的操作类型，若无法判断则返回 None
        """

        order_status = msg.get('o', {}).get('X', '')  # 订单状态
        reduce_only = msg.get('o', {}).get('R', False)  # 是否为只减仓模式
        order_side = msg.get('o', {}).get('S', '')  # 订单方向
        position_side = msg.get('o', {}).get('ps', '')  # 仓位方向

     # 部分情况下可能没有 ps 字段，默认 BOTH

        if reduce_only:
                if order_side == 'SELL' and position_side in ['LONG', 'BOTH']:
                    return OrderAction.CLOSE_LONG
                elif order_side == 'BUY' and position_side in ['SHORT', 'BOTH']:
                    return OrderAction.CLOSE_SHORT
        else:
            if order_side == 'BUY' and position_side in ['LONG', 'BOTH']:
                return OrderAction.OPEN_LONG
            elif order_side == 'SELL' and position_side in ['SHORT', 'BOTH']:
                return OrderAction.OPEN_SHORT


        return None
    # untest
    def _update_position(self, position_dict: dict, symbol: str, order_action: OrderAction, last_filled_quantity: float):
        """
         更新指定仓位字典的持仓
        :param position_dict: 仓位字典 (main_positions/sub_positions)
        :param symbol: 交易对
        :param order_action: 订单操作类型
        :param last_filled_quantity: 成交数量
        """
        if symbol not in position_dict:
            position_dict[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
            
        if order_action == OrderAction.OPEN_LONG:
            position_dict[symbol]['LONG'] += last_filled_quantity
        elif order_action == OrderAction.OPEN_SHORT:
            position_dict[symbol]['SHORT'] -= last_filled_quantity
        elif order_action == OrderAction.CLOSE_LONG:
            position_dict[symbol]['LONG'] -= last_filled_quantity
        elif order_action == OrderAction.CLOSE_SHORT:
            position_dict[symbol]['SHORT'] += last_filled_quantity

    async def start_follow_order(self, main_order_map):
        async with self.main_client.us as tscm:
            while self.main_client.running:
                try:
                    msg = await tscm.recv()
                    # todo 处理重连
                    if msg['e'] == 'error':
                        logger.error(f"接收到错误消息: {msg}")
                        await self._handle_error(msg)
                        continue


                    # open_long open_short close_long close_short  开仓 开仓 平仓 平仓
                    ORDER_EVENT_TYPE = msg['e']
                    # partially_filled_count 聚合PARTIALLY_FILLED事件，每5次聚合成1次。
                    partially_filled_count = 0
                    
                    # 如果x=NEW X=NEW 则为新订单， 创建子订单状态
                    if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['x'] == 'NEW' and msg['o']['X'] == 'NEW' :  # 处理订单更新事件
                        
                        order_id = msg['o']['i']
                        main_order_map[str(order_id)] ={}
                        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
                        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
                        main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
                        main_order_map[str(order_id)]['sub_orders'] = []
                        main_order_map[str(order_id)]['filled_quantity'] = 0
                        # 初始化子订单需要开仓或者平仓的数量  bug , 当子账户钱不够的话，需要处理这个问题。
                        main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO 
                        main_order_map[str(order_id)]['sub_filled_quantity'] = 0
                        main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
                        logger.info(f"NEW 监测到主账户有新的订单: ID={msg['o']['i']}, 状态={msg['o']['X']}, 数量={msg['o']['q']}, 价格={msg['o']['p']}, 时间={msg['o']['T']}, 类型={msg['o']['ot']}, 方向={msg['o']['S']}")
                    # todo 部分成交可能要取消
                    if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['x'] == 'TRADE' and msg['o']['X'] == 'PARTIALLY_FILLED' : 
                        partially_filled_count += 1
                        order_id = msg['o']['i']
                        last_filled_quantity = float(msg['o']['l'])
                        if str(order_id) not in main_order_map:
                            main_order_map[str(order_id)] ={}
                            main_order_map[str(order_id)]['sub_orders'] = []
                            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
                            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
                            main_order_map[str(order_id)]['filled_quantity']=0
                            # 初始化子订单需要开仓或者平仓的数量
                            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO 
                            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
                        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
                        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
                        main_order_map[str(order_id)]['filled_quantity']+= last_filled_quantity
                        order_id = msg['o']['i']
                        quantity = msg['o']['q']
                        price = msg['o']['p']
                        symbol = msg['o']['s']
                        order_type = msg['o']['ot']
                        side = msg['o']['S']
                        logger.info(f"PARTIALLY_FILLED 检测到主账户订单部分成交: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
                        # todo 更新主账号仓位
                        if partially_filled_count >=5:
                            partially_filled_count = 0
                            asyncio.create_task(self.handle_order_update(msg, main_order_map))

                    # 订单已经完全成交
                    if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['x'] == 'TRADE' and msg['o']['X'] == 'FILLED' :  # 处理订单更新事件

                        position_side = msg['o']['ps']
                        symbol = msg['o']['s']
                        last_filled_quantity = float(msg['o']['l'])
                        if symbol not in self.main_positions:
                            self.main_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                        order_action = self.get_order_action(msg)
                        # 更新主账号仓位
                        self._update_position(self.main_positions, symbol, order_action, float(msg['o']['z']))
                        
                        order_id = msg['o']['i']
                        if str(order_id) not in main_order_map:
                            main_order_map[str(order_id)] ={}
                            main_order_map[str(order_id)]['sub_orders'] = []
                            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
                            main_order_map[str(order_id)]['filled_quantity']=0
                            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
                            # 初始化子订单需要开仓或者平仓的数量
                            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO 
                            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
                        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
                        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
                        main_order_map[str(order_id)]['filled_quantity']+= last_filled_quantity
                        order_id = msg['o']['i']
                        quantity = msg['o']['q']
                        price = msg['o']['p']
                        symbol = msg['o']['s']
                        order_type = msg['o']['ot']
                        side = msg['o']['S']
                        logger.info(f"FILLED-收到主账户订单完全成交: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
                        # loop = asyncio.get_running_loop()
                        # loop.run_in_executor(self.thread_pool, lambda: asyncio.run(self.handle_order_update(msg)))
                        asyncio.create_task(self.handle_order_update(msg, main_order_map))

                    # 订单过期
                    # 订单已经完全成交
                    if msg['e'] == 'ORDER_TRADE_UPDATE' and msg['o']['x'] == 'EXPIRED' and msg['o']['X'] == 'EXPIRED' :  # 处理订单更新事件
                        # 订单累计成交量
                        total_filled_quantity = float(msg['o']['z'])
                        # 计算主仓位变化量
                        if symbol not in self.main_positions:
                            self.main_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                        # self.main_positions[symbol][position_side] = abs(self.main_positions[symbol][position_side] - last_filled_quantity )
                        order_action = self.get_order_action(msg)
                         # 更新主账号仓位
                        self._update_position(self.main_positions, symbol, order_action, float(msg['o']['z']))
                        order_id = msg['o']['i']
                        if str(order_id) not in main_order_map:
                            main_order_map[str(order_id)] ={}
                            main_order_map[str(order_id)]['sub_orders'] = []
                            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
                            main_order_map[str(order_id)]['filled_quantity']=0
                            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
                            # 初始化子订单需要开仓或者平仓的数量
                            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO 
                            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
                        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
                        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
                        main_order_map[str(order_id)]['filled_quantity']= total_filled_quantity
                        order_id = msg['o']['i']
                        quantity = msg['o']['q']
                        price = msg['o']['p']
                        symbol = msg['o']['s']
                        order_type = msg['o']['ot']
                        side = msg['o']['S']
                        logger.info(f"EXPIRED-收到主账户订单失效: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
                        # loop = asyncio.get_running_loop()
                        # loop.run_in_executor(self.thread_pool, lambda: asyncio.run(self.handle_order_update(msg)))
                        # todo 更新主账号仓位
                        asyncio.create_task(self.handle_order_update(msg, main_order_map))
                
                except (ConnectionClosedError, BinanceWebsocketClosed) as e:
                    logger.error(f"WebSocket连接错误: {str(e)}", exc_info=True)
                    logger.info("尝试重新连接...")
                    if await self.main_client._reconnect():
                        continue
                    else:
                        break

                except Exception as e :
                    # 其他异常的处理
                    logger.error(f"处理消息时发生错误: {str(e)}", exc_info=True)
                    continue  # 继续
            # 关闭WebSocket连接
            # self.main_client.running = False
            # self.main_client.close_connection()
            logger.info("WebSocket连接已关闭")

    def _handle_filled(self, msg, main_order_map):
        last_filled_quantity = float(msg['o']['l'])
        order_id = msg['o']['i']
        if str(order_id) not in main_order_map:
            main_order_map[str(order_id)] = {}
            main_order_map[str(order_id)]['sub_orders'] = []
            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
            main_order_map[str(order_id)]['filled_quantity'] = 0
            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO
            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
        main_order_map[str(order_id)]['filled_quantity'] += last_filled_quantity
        quantity = msg['o']['q']
        price = msg['o']['p']
        symbol = msg['o']['s']
        order_type = msg['o']['ot']
        side = msg['o']['S']
        logger.info(f"FILLED-收到主账户订单完全成交: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
        asyncio.create_task(self.handle_order_update(msg, main_order_map))
    def _handle_partially_filled(self, msg, main_order_map, partially_filled_count):
        partially_filled_count += 1
        order_id = msg['o']['i']
        last_filled_quantity = float(msg['o']['l'])
        if str(order_id) not in main_order_map:
            main_order_map[str(order_id)] = {}
            main_order_map[str(order_id)]['sub_orders'] = []
            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
            main_order_map[str(order_id)]['filled_quantity'] = 0
            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO
            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
        main_order_map[str(order_id)]['filled_quantity'] += last_filled_quantity
        quantity = msg['o']['q']
        price = msg['o']['p']
        symbol = msg['o']['s']
        order_type = msg['o']['ot']
        side = msg['o']['S']
        logger.info(f"PARTIALLY_FILLED 检测到主账户订单部分成交: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
        if partially_filled_count >= 5:
            partially_filled_count = 0
            asyncio.create_task(self.handle_order_update(msg, main_order_map))
        return partially_filled_count

    # 处理过期下单事件
    def _handle_expired(self, msg, main_order_map):
        last_filled_quantity = float(msg['o']['l'])
        if last_filled_quantity == 0:
            return
        order_id = msg['o']['i']
        if str(order_id) not in main_order_map:
            main_order_map[str(order_id)] = {}
            main_order_map[str(order_id)]['sub_orders'] = []
            main_order_map[str(order_id)]['orgin_quantity'] = msg['o']['q']
            main_order_map[str(order_id)]['orderAction'] = self.get_order_action(msg)
            main_order_map[str(order_id)]['filled_quantity'] = 0
            main_order_map[str(order_id)]['sub_orgin_quantity'] = float(main_order_map[str(order_id)]['orgin_quantity']) * SUB_ORDER_TRADE_RATIO
            main_order_map[str(order_id)]['sub_filled_quantity'] = 0
        main_order_map[str(order_id)]['order_type'] = msg['o']['x']
        main_order_map[str(order_id)]['order_status'] = msg['o']['X']
        main_order_map[str(order_id)]['filled_quantity'] += last_filled_quantity
        quantity = msg['o']['q']
        price = msg['o']['p']
        symbol = msg['o']['s']
        order_type = msg['o']['ot']
        side = msg['o']['S']
        logger.info(f"PARTIALLY_FILLED 检测到主账户订单部分成交: ID={order_id}, 状态={msg['o']['X']}, 数量={quantity}, 价格={price}, 时间={msg['o']['T']}, 类型={order_type}, 方向={side}")
        
        asyncio.create_task(self.handle_order_update(msg, main_order_map))
        
    async def handle_order_update(self, message, main_order_map):
        try:
            order_id = message['o']['i']
            new_status = message['o']['X']
            logger.info(f"订单更新: ID={order_id}, 状态={new_status}")
            # 在这里添加跟单逻辑

            # 根据main_order_map 获取子账号要进行的订单数量， 然后根据数量进行下单。
            
            await self.follow_order(order_id, new_status, message, main_order_map)

            # 后置操作， 判断main_order_map 中的订单是否已经完全成交，如果完全成交， 则删除main_order_map 中的订单
            # 检查订单是否完全成交 todo 未完成
            # if main_order_map[str(order_id)]['order_status'] == 'FILLED':
            #     # 检查子订单是否完全成交
            #     if main_order_map[str(order_id)]['sub_filled_quantity'] >= main_order_map[str(order_id)]['sub_orgin_quantity']:
            #         # 删除主订单
            #         del main_order_map[str(order_id)]
            # 补偿机制
            order_action = self.get_order_action(message)
            is_close_position = order_action in [OrderAction.CLOSE_LONG, OrderAction.CLOSE_SHORT]
            if is_close_position:
                await self.compensate_close_position(order_id, message, main_order_map)
            logger.info(f"订单更新处理完成: 主号仓位={self.main_positions}, 子号仓位={self.sub_positions}")
        except Exception as e:
            logger.error(f"处理订单更新时发生错误: {str(e)}", exc_info=True)

    # GTC(Good Till Cancelled) 模式下跟单
    # gtc模式，不用循环去请求下单
    async def follow_order_gtc(self, order_id, status, message, main_order_map):
        if status in {'FILLED', 'PARTIALLY_FILLED'} and self.sub_client:
            try:
                main_order = main_order_map[str(order_id)]
                logger.info(f"开始 GTC 模式跟单逻辑，主账户订单 ID: {order_id}")

                # 获取本次需要交易的总数量并按照配置的比例计算
                total_quantity = float(message['o']['l']) * SUB_ORDER_TRADE_RATIO
                # 处理精度，保留与原订单相同的小数位数
                qty_precision, price_precision = await self.get_symbol_precision(message['o']['s'])
                total_quantity =  round(total_quantity, qty_precision)
               
                max_retries = 5  # 最大重试次数
                retry_count = 0
                logger.info(f"计划 GTC 模式跟单数量: {total_quantity} (原始数量: {message['o']['l']}, 跟单比例: {SUB_ORDER_TRADE_RATIO})")

                while  retry_count < max_retries:
                    try:
                        # 构建 GTC 模式副账户订单参数
                        sub_order = {
                            'symbol': message['o']['s'],
                            'side': message['o']['S'],
                            'type': message['o']['ot'],
                            'timeInForce': TIME_IN_FORCE_GTC,  # 设置订单有效期为 GTC
                            'quantity': str(total_quantity)  # Binance API 需要字符串格式的数量
                        }

                        # 如果是限价单，设置价格
                        if message['o']['ot'] == 'LIMIT':
                            sub_order['price'] = message['o']['p']

                        # 执行副账户交易
                        response = await self.sub_client.futures_create_order(**sub_order)

                        # 获取实际成交数量
                        filled_quantity = float(response.get('executedQty', 0))
                        

                        logger.info(f"副账户 GTC 模式跟单进度 - 订单 ID: {response['orderId']}, "
                                  f"本次成交: {filled_quantity}, "
                                  f"订单状态: {response['status']}")

                        # 如果还有剩余数量，等待一小段时间再继续
                        if response['status'] in ['FILLED', 'PARTIALLY_FILLED', 'NEW']:
                            return
                        else:
                            await asyncio.sleep(0.5)
                            retry_count += 1

                    except Exception as e:
                        logger.error(f"GTC 模式下单失败，重试中... 错误: {str(e)}")
                        retry_count += 1
                        await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"GTC 模式跟单失败: {str(e)}", exc_info=True)


    async def follow_order(self, order_id, status, message, main_order_map):
        # 实际成交量
        executed_quantity = 0
        main_order = main_order_map[str(order_id)]
        # 如果order_continue 为True，可以继续下单
        order_continue = True
        symbol = message['o']['s']
        position_side = message['o']['ps']
        if not order_continue:
            return 
        # 订单末次成交量
        main_order_last_filled_quantity = float(message['o']['l'])
        #订单累计成交量
        mian_order_filled_quantity = float(message['o']['z'])

        # if (status == 'FILLED' or status == 'PARTIALLY_FILLED') and self.sub_client:
        # if (status == 'FILLED' or status == 'EXPIRED') and self.sub_client:
        if (status == 'FILLED' or status == 'EXPIRED ' ) and self.sub_client:    
            try:
                
                # todo 根据订单数量，多次下单，知道订单完全卖出，或者完全买入。
                # main_order = await self.main_client.futures_get_order(symbol=message['o']['s'], orderId=order_id)
                # todo 查看副账号账户余额， 如果余额不足， 则不执行
                # 构建副账户订单参数
                # sub_order = {
                #     'symbol':message['o']['s'],
                #     'side': message['o']['S'],
                #     'type': message['o']['ot'],
                #     # l为末次成交量
                #     'quantity': message['o']['l']
                # }
                # 根据主账户订单类型设置副账户订单参数, 如果是限价单，需要设置价格， 暂时不需要
                # if message['o']['ot'] == 'LIMIT':
                #     sub_order['price'] = message['o']['p']

                #---------------for debug for todo--------------------------------
                logger.info(f"开始执行跟单逻辑， 主账户订单ID:{order_id}")
                
                # 获取本次需要交易的总数量
                # 获取本次需要交易的总数量并按照配置的比例计算
                # total_quantity = float(message['o']['l']) * SUB_ORDER_TRADE_RATIO
                total_quantity = float(message['o']['z']) * SUB_ORDER_TRADE_RATIO
            
                # 处理精度，保留与原订单相同的小数位数
               
                qty_precision, price_precision = await self.get_symbol_precision(message['o']['s'])
                total_quantity = round(total_quantity, qty_precision)
                # total_quantity = float(message['o']['l'])
                remaining_quantity = total_quantity
                
                max_retries = 5  # 最大重试次数
                retry_count = 0
                logger.info(f"计划跟单数量: {total_quantity} (原始数量: {message['o']['z']}, 跟单比例: {SUB_ORDER_TRADE_RATIO})")
                # 判断是否为平仓操作
                order_action = self.get_order_action(message)
                if not order_action:
                    logger.error(f"获取订单操作类型失败，跟单失败， 订单ID:{order_id}")
                    return
                is_close_position = order_action in [OrderAction.CLOSE_LONG, OrderAction.CLOSE_SHORT]
                while remaining_quantity > 0 and retry_count < max_retries:
                  
                    try:
                        # 目前只支持双向持仓
                        # 构建副账户订单参数
                        remaining_quantity = round(remaining_quantity, qty_precision)
                        sub_order = {
                            'symbol': symbol,
                            'side': message['o']['S'],
                            'type': message['o']['ot'],
                            'quantity': str(remaining_quantity),  # Binance API需要字符串格式的数量
                            'positionSide':message['o']['ps']
                            # 'quantity': str(round(remaining_quantity, decimal_places))
                        }
                        # 双向持仓， long多头持仓量、short空头持仓量
                        # 如果是平仓操作，添加 reduceOnly 参数, 平仓前检查持仓量
                        if is_close_position:
                            try:
                                # 获取当前持仓量
                                position_side = None
                                if order_action == OrderAction.CLOSE_LONG:
                                    position_side = 'LONG'
                                elif order_action == OrderAction.CLOSE_SHORT:
                                    position_side = 'SHORT'
                                position_amt = await self.get_position_quantity(symbol, position_side)
                                #如果持仓量小于要平仓的数量，调整数量
                                if position_amt < remaining_quantity:
                                    remaining_quantity = position_amt
                                    if remaining_quantity <= 0:
                                        logger.info("没有可平仓的持仓量，跳过下单")
                                        break

                                # 处理精度
                                # qty_precision, price_precision = await self.get_symbol_precision(symbol)
                                sub_order['quantity'] =  round(remaining_quantity, qty_precision)
                            except Exception as e:
                                logger.error(f"获取持仓信息失败: {str(e)}", exc_info=True)
                                retry_count += 1
                                continue
                        # 执行副账户交易
                        response = await self.sub_client.futures_create_order(**sub_order)
                        logger.info(f"副账户跟单状态 订单返回:{response} ")
                        # ------------------debug---------------

                        # 根据response获取订单状态
                        sub_order_id = response['orderId']
                        await asyncio.sleep(1)  
                        # 获取订单状态
                        check_response = await self.check_order_status(message['o']['s'], sub_order_id)
                        print("Order status:", check_response)
                        # 获取订单状态失败，不知道是否下单成功， 后续则不下单。 请求人工介入。
                        if check_response == {}:
                            logger.error(f"获取订单状态失败，订单ID:{sub_order_id}")
                            retry_count += 1
                            await asyncio.sleep(1)
                            # todo 发送飞书消息。
                            # break,后续不在下单
                            break
                        
                        # 获取实际成交数量
                        filled_quantity = float(check_response.get('executedQty', 0))

                        # 更新副账户持仓量  
                        self._update_position(self.sub_positions, symbol, order_action, filled_quantity)

                        
                        # if symbol not in self.sub_positions:
                        #     self.sub_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}

                        # self.sub_positions[symbol][position_side] = abs(self.sub_positions[symbol][position_side] - filled_quantity )
                        
                        executed_quantity += filled_quantity
                        remaining_quantity = total_quantity - executed_quantity

                        logger.info(f"副账户跟单进度 - 订单ID:{response['orderId']}, "
                                  f"本次成交:{filled_quantity}, "
                                  f"总计成交:{executed_quantity}, "
                                  f"剩余数量:{remaining_quantity}")
                        sub_order['filled_quantity'] = filled_quantity
                        # 如果订单完全成交，更新main_order_map
                        if check_response['status'] in {'FILLED', 'PARTIALLY_FILLED'}:
                            if 'sub_orders' not in main_order:
                                main_order['sub_orders'] = []
                            main_order['sub_orders'].append({
                                'order_id': response['orderId'],
                                'quantity': filled_quantity,
                                'price': response['price'],
                                'order_status': check_response['status'],
                                'origin_quantity': remaining_quantity,
                                'filled_quantity': filled_quantity,
                            })
                            mian_order_sub_filled_quantity = main_order_map[str(order_id)]['sub_filled_quantity']
                            mian_order_sub_filled_quantity += filled_quantity
                        if check_response['status'] == 'EXPIRED':
                            if 'sub_orders' not in main_order:
                                main_order['sub_orders'] = []
                            main_order['sub_orders'].append({
                                'order_id': response['orderId'],
                                'quantity': filled_quantity,
                                'price': response['price'],
                                'order_status': check_response['status'],
                                'origin_quantity': remaining_quantity,
                                'filled_quantity': filled_quantity,
                            })
                            mian_order_sub_filled_quantity = main_order_map[str(order_id)]['sub_filled_quantity']
                            mian_order_sub_filled_quantity += filled_quantity
                                    
                        # 子订单状态为Filled, 不需要下单，结束循环
                        if check_response['status'] == 'FILLED':
                            logger.info(f"订单 {sub_order_id} 状态为 FILLED，无需下单")
                            break

                        if check_response['status'] == 'PARTIALLY_FILLED':
                            logger.info(f"订单 {sub_order_id} 状态为 PARTIALLY_FILLED, 结束下单 ")
                            break

                        # 如果还有剩余数量，等待一小段时间再继续
                        if remaining_quantity > 0:
                            await asyncio.sleep(0.5)
                            retry_count += 1

                    except Exception as e:
                        logger.error(f"下单失败，重试中... 错误: {str(e)}", exc_info=True)
                        if hasattr(e, 'code') and e.code == -4164:
                            logger.error("持仓数量超过限制，停止后续下单")
                            order_continue = False
                            break
                        retry_count += 1
                        await asyncio.sleep(1)

                if remaining_quantity > 0:
                    logger.warning(f"未能完成全部数量的跟单，剩余数量: {remaining_quantity}")
                else:
                    logger.info(f"跟单完成，总成交数量: {executed_quantity}")
               
                #-----------------------------end--------------------------------
                # 执行副账户交易
                # response = await self.sub_client.futures_create_order(**sub_order)
                # logger.info(f"副账户跟单成功 订单ID:{response['orderId']} "
                #            f"{response['symbol']} {response['side']}@{response['price']}")
                # logger.info(f"副账户跟单信息: {response}")
            except Exception as e:
                logger.error(f"跟单失败: {str(e)}", exc_info=True)
            
    async def check_order_status(self, symbol: str, order_id: int, max_retries: int = 10) -> dict:
        """
        检查订单状态
        :param symbol: 交易对
        :param order_id: 订单ID
        :param max_retries: 最大重试次数
        :return: 订单信息
        """
        retry_count = 0
        order_info = {}
        status = 'None'
        while retry_count < max_retries:
            try:
                # 查询订单状态
                if self.sub_client:
                    order_info = await self.sub_client.futures_get_order(
                        symbol=symbol,
                        orderId=order_id)
                else:
                    logger.error("副账户客户端未初始化，无法查询订单状态")
                    return {}
                
                status = order_info['status']
                logger.info(f"订单 {order_id} 当前状态: {status}")
                
                # 如果是终态，直接返回
                if status in {'FILLED', 'CANCELED', 'REJECTED', 'EXPIRED', 'EXPIRED_IN_MATCH'}:
                    return order_info
                
                # 如果是NEW或PARTIALLY_FILLED状态，继续查询
                if status in {'NEW', 'PARTIALLY_FILLED'}:
                    await asyncio.sleep(1)  # 等待1秒后再次查询
                    retry_count += 1
                    continue
                
            except Exception as e:
                logger.error(f"查询订单状态失败: {str(e)}", exc_info=True)
                retry_count += 1
                await asyncio.sleep(0.5)
                
        logger.warning(f"达到最大重试次数 {max_retries}，最后一次查询状态: {status}")
        return order_info

    # 平单补偿 count 用来判断子账户要不要去请求查询接口。 
    async def compensate_close_position(self, order_id, message, main_order_map, from_queue=False, count=0):

        count += 1
        symbol=message['o']['s']
        position_side = message['o']['ps']
        qty_precision, price_precision = await self.get_symbol_precision(symbol)
        if not self.sub_client:
            logger.warning('未配置副账户API密钥，无法执行补偿平仓操作')
            return

        try:
            symbol = message['o']['s']
            
            if not from_queue:
                # 从主账号获取仓位信息
                main_position_info = await self.main_client.websocket.futures_position_information(symbol=symbol)
                # 修正用户持仓量
                if symbol not in self.main_positions:
                    self.main_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                # 遍历主账号仓位信息，修正仓位信息
                for position in main_position_info:
                    main_position_side = position['positionSide']
                    if main_position_side in {'LONG', 'SHORT'}:
                        self.main_positions[symbol][main_position_side] = float(position['positionAmt'])
                    else:
                        logger.warning(f"未知的仓位方向: {position['positionSide']}")
                # 从子账号获取仓位信息
                sub_position_info = await self.sub_client.futures_position_information(symbol=symbol)
                if symbol not in self.sub_positions:
                    self.sub_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                # 遍历子账号仓位信息，修正仓位信息
                for position in sub_position_info:
                    sub_position_side = position['positionSide']
                    if sub_position_side in {'LONG', 'SHORT'}:
                        self.sub_positions[symbol][sub_position_side] = float(position['positionAmt'])
                    else:
                        logger.warning(f"未知的仓位方向: {position['positionSide']}")
            # 主账号仓位
            main_position = self.main_positions[symbol][position_side]
            sub_position = self.sub_positions[symbol][position_side] 

            main_order = main_order_map[str(order_id)]
            # 根据仓位比例计算子账号应该的仓位数量, 如果main_position为0，子账户全平
            sub_needed_quantity =  SUB_ORDER_TRADE_RATIO * abs(float(main_position))

            if sub_needed_quantity == 0 :
                logger.info(f"主账户仓位为0，子账户需全部平仓，数量为：{sub_position}")
                
            if count % 3 == 0:
                sub_position = await self.get_position_quantity(symbol, position_side)
                # 修正用户持仓量
                if symbol not in self.sub_positions:
                    self.sub_positions[symbol] = {'LONG': 0.0, 'SHORT': 0.0}
                self.sub_positions[symbol][position_side] = sub_position

            # 计算还需要平仓的数量 = 子账户当前数量-子账户应该有的数量
            remaining_quantity = abs(sub_position) - sub_needed_quantity

            order_action = None
            if position_side == 'LONG':
                # remaining_quantity = abs(sub_position) - sub_needed_quantity
                order_action = OrderAction.CLOSE_LONG
            elif position_side == 'SHORT':
                # remaining_quantity = abs(sub_position) - sub_needed_quantity
                order_action = OrderAction.CLOSE_SHORT
            else:
                logger.error(f"未知的仓位方向: {position_side}")
                return
            

            if remaining_quantity <= 0:
                logger.info("子账户仓位已满足要求，无需平仓")
                return

            # 如果没有持仓，直接返回
            if sub_position == 0:
                logger.info("子账户没有持仓，无需补偿平仓")
                return
            # 确定最终平仓数量
            final_close_quantity = remaining_quantity
            if final_close_quantity <= 0:
                logger.info("最终平仓数量小于等于0，跳过补偿平仓")
                return

            # 处理精度问题
            final_close_quantity = round(final_close_quantity, qty_precision)

            if final_close_quantity <= 0:
                logger.info("最终平仓数量小于等于0，跳过补偿平仓")
                return
            logger.info(f"开始执行补偿平仓操作，还需平仓数量: {final_close_quantity}")
            # 构建平仓订单参数
            sub_order = {
                'symbol': message['o']['s'],
                'side': message['o']['S'],
                'type': message['o']['ot'],
                'quantity': str(final_close_quantity),
                'positionSide':position_side
            }

                # 执行副账户平仓操作
            response = await self.sub_client.futures_create_order(**sub_order)
            await asyncio.sleep(1)
            check_response = await self.check_order_status(message['o']['s'], response['orderId'], max_retries=1)
            filled_quantity = float(check_response.get('executedQty', 0))
            logger.info(f"副账户补偿平仓操作 - 订单 ID: {response['orderId']}, 本次成交: {filled_quantity}")
            # 更新main_positon sub_positon
            
            # 更新子账户持仓信息
            self._update_position(self.sub_positions, symbol, order_action, filled_quantity)
            logger.info(f"子账户仓位已更新，当前仓位: {self.sub_positions[symbol][position_side]}")
            # 更新 main_order_map
            if 'sub_orders' not in main_order:
                main_order['sub_orders'] = []
            main_order['sub_orders'].append({
                'order_id': response['orderId'],
                'quantity': filled_quantity,
                'price': response['price'],
                'order_status': response['status']
            })

            main_order['sub_filled_quantity'] += filled_quantity
            # sub_filled_quantity += filled_quantity
            # remaining_quantity = remaining_quantity - filled_quantity
            still_close_quantity = final_close_quantity - filled_quantity
            # 更新子账户仓位 非原子性，后期考虑加上异步锁
            # self.sub_positions[symbol] = sub_position - filled_quantity
            # self.sub_positions[symbol][position_side] -= filled_quantity
            # if self.sub_positions[symbol][position_side] < 0:
            #     self.sub_positions[symbol][position_side] = 0.0
            logger.info(f"主账户当前持仓数量: {main_position}, 子账户当前持仓： {self.sub_positions[symbol]} 子账户需要平仓的数量: {sub_needed_quantity}, 已平仓数量: {filled_quantity}, 还需平仓数量: {still_close_quantity}")
            
            if still_close_quantity > 0:
                logger.warning(f"补偿平仓未完成，剩余持仓: {sub_position}，加入补偿队列")
                await asyncio.sleep(random.randint(1, 5))
                await self.compensate_queue.put((order_id, message, main_order_map))

        except Exception as e:
            logger.error(f"补偿平仓操作失败: {str(e)}", exc_info=True)
            # 如果失败，可能是持仓方向不一样。
            logger.warning(f"补偿平仓未完成，剩余持仓: {sub_position}，加入补偿队列")
            await asyncio.sleep(random.randint(1, 5))
            await self.compensate_queue.put((order_id, message, main_order_map))

    async def get_position_quantity(self, symbol, position_side):
        """
        根据交易对符号和持仓方向获取仓位数量。

        :param symbol: 交易对符号，例如 'BTCUSDT'
        :param position_side: 持仓方向，'LONG' 表示多头，'SHORT' 表示空头
        :return: 对应持仓方向的仓位数量，如果获取失败则返回 0
        """
        if not self.sub_client:
            logger.warning('未配置副账户API密钥，无法获取持仓信息')
            return 0

        try:
            # 获取当前持仓
            position = await self.sub_client.futures_position_information(symbol=symbol)
            # 查找指定持仓方向的持仓
            for pos in position:
                if pos['positionSide'] == position_side:
                    return abs(float(pos['positionAmt']))  # 返回绝对值
            logger.warning(f'未找到 {position_side} 方向的持仓信息')
            return 0
        except Exception as e:
            logger.error(f"获取 {symbol} 的 {position_side} 持仓信息失败: {str(e)}", exc_info=True)
            return 0


    async def get_symbol_precision(self, symbol):
        """
        获取币种的数量和价格精度
        """
        info = await self.sub_client.futures_exchange_info()
        for symbol_info in info['symbols']:
            if symbol_info['symbol'] == symbol:
                return symbol_info['quantityPrecision'], symbol_info['pricePrecision']
        return 0, 0  # 默认


    async def _handle_error(self, msg):
        """
        处理错误信息，目前是只有重连错误
        """
        if msg['type'] == 'BinanceWebsocketUnableToConnect':
            logger.error(f"WebSocket连接错误: {msg['m']}")
            logger.info("尝试重新连接...")
            await self.main_client._reconnect()
        else:
            logger.error(f"未知的WebSocket错误: {msg}")
