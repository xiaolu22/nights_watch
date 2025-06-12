import asyncio
import websockets
import json
from ..config import MAIN_API_KEY, MAIN_API_SECRET, TESTNET, HTTP_PROXY
from ..utils.logger import logger
from binance import BinanceSocketManager
from binance import AsyncClient
from time import time


class WebSocketClient:
    def __init__(self):
        self.websocket = None
        self.binance_socket_manager = None
        self.us = None
        self.running = False
       

    async def _reconnect(self):
        while self.running:
            try:
                self.websocket = await AsyncClient.create(MAIN_API_KEY, MAIN_API_SECRET,testnet=TESTNET, https_proxy=HTTP_PROXY)
                # server_time = await self.websocket.get_server_time()
                # local_time = int(time() * 1000)
                # time_delta = server_time['serverTime'] - local_time
                
                # Apply time delta to client configuration
                # self.websocket.time_offset = time_delta
                self.binance_socket_manager = BinanceSocketManager(self.websocket, user_timeout=60)
                self.us = self.binance_socket_manager.futures_user_socket()
                
            
                logger.info("WebSocket连接成功")
                return True
            except Exception as e:
                logger.error(f'连接失败: {e}, 10秒后重试...')
                await asyncio.sleep(10)
                continue

    # 废弃
    async def connect(self):
        self.websocket = await AsyncClient.create(MAIN_API_KEY, MAIN_API_SECRET,testnet=TESTNET, https_proxy=HTTP_PROXY)
        self.binance_socket_manager = BinanceSocketManager(self.websocket, user_timeout=60)
        self.us = self.binance_socket_manager.futures_user_socket()
        logger.info("WebSocket连接成功")
        # self.us = self.binance_socket_manager.user_socket()

    async def start(self):
        self.running = True
        if not await self._reconnect():
            return

    async def receive_message(self):
        while True:
            try:
                async with self.us as tscm:
                    print("成功连接到WebSocket，开始接收交易数据...")
                    while True:
                        data = await tscm.recv()
                        # print(data)
                        logger.info(f"收到消息: {data}")
                        # todo 需要判断消息类型， 还有订单状态，如果订单状态是FILLED，需要发送订单信息。
                        # for debug
                        # return data
            except Exception as e:
                logger.error(f"WebSocket连接错误: {str(e)}", exc_info=True)
                logger.info("尝试重新连接...")
                await self.connect()
                await asyncio.sleep(5)
    async def shutdown(self):
        self.running = False
        if self.websocket:
            await self.websocket.close_connection()
        logger.info("WebSocket已关闭")
        # while True:
        #     message = await self.binance_socket_manager
        #     data = json.loads(message)
        #     logger.info(f"收到消息: {data}")
        #     return data

    # async def send_message(self, message):
    #     await self.websocket.send(json.dumps(message))
    #     logger.info(f"发送消息: {message}")


class UserDataClient:
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
        self.bm = None
        self.socket = None
        self.running = False
        self.callbacks = {
            'executionReport': self._handle_order_update
        }

    async def _reconnect(self):
        while self.running:
            try:
                self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=TESTNET)
                self.bm = BinanceSocketManager(self.client)
                listen_key = await self.client.stream_get_listen_key()
                self.socket = self.bm.user_socket(listen_key)
                logger.info('用户数据流连接成功')
                return True
            except Exception as e:
                logger.error(f'连接失败: {e}, 10秒后重试...')
                await asyncio.sleep(10)

    async def _start_socket(self):
        async with self.socket as socket_connection:
            while self.running:
                try:
                    msg = await socket_connection.recv()
                    self._dispatch_event(msg)
                except websockets.ConnectionClosed:
                    logger.warning('连接中断，尝试重新连接...')
                    if await self._reconnect():
                        continue
                    else:
                        break

    async def start(self):
        self.running = True
        if not await self._reconnect():
            return

        asyncio.create_task(self._start_socket())

    async def shutdown(self):
        self.running = False
        try:
            if self.socket:
                await self.socket.close()
            if self.client:
                await self.client.close_connection()
            logger.info('连接已安全关闭')
        except Exception as e:
            logger.error(f'关闭连接时出错: {e}')

    def _dispatch_event(self, msg):
        event_type = msg.get('e')
        if handler := self.callbacks.get(event_type):
            handler(msg)

    def _handle_order_update(self, data):
        logger.info(f"订单更新: {data['x']} {data['X']} "
                    f"{data['s']} {data['S']}@{data['p']} "
                    f"数量: {data['q']}")
        
    def add_reconnect_logic(self):
        self.twm._client._reconnect_websocket = \
            lambda ws: self._reconnect_with_retry(ws)

    def _reconnect_with_retry(self, ws, max_retries=5):
        for i in range(max_retries):
            try:
                self.twm._start_socket(ws)
                return
            except Exception as e:
                logger.error(f"重连失败({i+1}/{max_retries}): {str(e)}")
                time.sleep(2**i)