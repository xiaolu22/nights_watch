import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
from exchange.order_manager import OrderManager
from exchange.ws_client import WebSocketClient

class TestOrderManager(unittest.TestCase):
    def setUp(self):
        self.mock_ws = MagicMock(spec=WebSocketClient)
        self.mock_ws.running = True
        self.manager = OrderManager(self.mock_ws)
        
    @patch('exchange.order_manager.AsyncClient')
    def test_sub_account_initialization(self, mock_client):
        # 测试副账户初始化逻辑
        self.manager._prepare_sub_account()
        if hasattr(self.manager, 'sub_client'):
            mock_client.assert_called_once()

    @patch('exchange.order_manager.logger')
    async def test_new_order_handling(self, mock_logger):
        # 模拟NEW状态订单消息
        test_msg = {
            'e': 'ORDER_TRADE_UPDATE',
            'o': {
                'x': 'NEW',
                'X': 'NEW',
                'i': 12345,
                's': 'BTCUSDT',
                'q': '0.1',
                'p': '50000',
                'T': 1620000000000,
                'ot': 'MARKET',
                'S': 'BUY'
            }
        }
        
        async def mock_recv():
            return test_msg
        
        self.mock_ws.us.recv = mock_recv
        
        task = asyncio.create_task(self.manager.start_fllow_order())
        await asyncio.sleep(0.1)
        task.cancel()
        
        mock_logger.info.assert_called_with("NEW 监测到主账户有新的订单: ID=12345, 状态=NEW, 数量=0.1, 价格=50000, 时间=1620000000000, 类型=MARKET, 方向=BUY")

    @patch('exchange.order_manager.AsyncClient')
    async def test_order_filled_flow(self, mock_client):
        # 测试完整订单成交流程
        mock_sub = AsyncMock()
        mock_sub.futures_create_order.return_value = {
            'orderId': 54321,
            'status': 'FILLED',
            'executedQty': '0.1'
        }
        self.manager.sub_client = mock_sub
        
        test_msg = {
            'e': 'ORDER_TRADE_UPDATE',
            'o': {
                'x': 'TRADE',
                'X': 'FILLED',
                'i': 12345,
                's': 'BTCUSDT',
                'l': '0.1',
                'T': 1620000000000,
                'ot': 'MARKET',
                'S': 'BUY'
            }
        }
        
        await self.manager.handle_order_update(test_msg)
        mock_sub.futures_create_order.assert_called_once()

if __name__ == '__main__':
    unittest.main()