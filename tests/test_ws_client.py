import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from exchange.ws_client import WebSocketClient
from binance import AsyncClient

class TestWebSocketClient(unittest.TestCase):
    @patch('exchange.ws_client.AsyncClient')
    async def test_connection_flow(self, mock_client):
        # 测试完整的连接生命周期
        mock_async_client = AsyncMock()
        mock_client.return_value = mock_async_client
        
        ws = WebSocketClient()
        ws._reconnect = AsyncMock(return_value=True)

        # 测试正常启动流程
        await ws.start()
        mock_async_client.start.assert_awaited_once()

        # 测试消息接收
        test_msg = {'e': 'test_event'}
        ws._receive_message = AsyncMock(return_value=test_msg)
        msg = await ws.receive_message()
        self.assertEqual(msg, test_msg)

        # 测试异常重连
        ws.running = True
        ws._receive_message.side_effect = Exception('mock error')
        await ws.listen()
        ws._reconnect.assert_awaited()

    @patch('exchange.ws_client.logger')
    async def test_reconnect_mechanism(self, mock_logger):
        # 测试重连逻辑
        ws = WebSocketClient()
        ws._connect = AsyncMock(side_effect=[Exception('connect error'), None])
        
        result = await ws._reconnect()
        self.assertTrue(result)
        mock_logger.error.assert_called_with("WebSocket连接错误: connect error")

    async def test_message_parsing(self):
        # 测试消息解析逻辑
        ws = WebSocketClient()
        raw_message = '{"e":"ORDER_TRADE_UPDATE","o":{"i":1001}}'
        parsed = await ws._parse_message(raw_message)
        self.assertEqual(parsed['e'], 'ORDER_TRADE_UPDATE')

if __name__ == '__main__':
    unittest.main()