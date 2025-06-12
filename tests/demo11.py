# WebSocket Stream Client
from socket import timeout
import time
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
import logging
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def message_handler(_, message):
    logging.info(message)

my_client = UMFuturesWebsocketClient(on_message=message_handler)

# Subscribe to a single symbol stream
my_client.agg_trade(symbol="bnbusdt")
time.sleep(5)
logging.info("closing ws connection")
my_client.stop()