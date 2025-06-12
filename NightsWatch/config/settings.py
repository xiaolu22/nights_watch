import os

class Config:
    """基础配置类，包含所有环境通用的配置"""
    # 通用配置
    SUB_ORDER_TRADE_RATIO = 0.3
    PROXY_PORT = 33210
     # 或者根据需要设为 None 或从环境变量读取

    # 默认值，子类可以覆盖
    TESTNET = True
    WEBSOCKET_URL = ''
    MAIN_API_KEY = ''
    MAIN_API_SECRET = ''
    SUB_API_KEY = ''
    SUB_API_SECRET = ''
    SUB_NAME = ''

class TestConfig(Config):
    """测试环境配置"""
    TESTNET = True
    WEBSOCKET_URL = 'wss://testnet.binance.vision/ws'
    HTTP_PROXY = 'http://127.0.0.1:7890'

    # 从环境变量获取，如果未设置则使用默认的测试密钥
    MAIN_API_KEY = os.getenv('MAIN_API_KEY', '')
    MAIN_API_SECRET = os.getenv('MAIN_API_SECRET', '')

    # 测试环境子账户信息 (如果需要，可以从环境变量读取)
    SUB_API_KEY = os.getenv('SUB_API_KEY', '')
    SUB_API_SECRET = os.getenv('SUB_API_SECRET', '')
    SUB_NAME = "wf_test" # 或者根据需要设置


class ProdConfig(Config):
    """生产环境配置"""
    TESTNET = False
    HTTP_PROXY = ''
    WEBSOCKET_URL = 'wss://stream.binance.com:9443/ws' # 生产环境 WebSocket URL

    # 从环境变量获取，如果未设置则使用默认的生产密钥
    MAIN_API_KEY = os.getenv('MAIN_API_KEY', '')
    MAIN_API_SECRET = os.getenv('MAIN_API_SECRET', '')

    # 生产环境子账户信息 (从环境变量读取，强烈建议不要硬编码生产密钥)
    SUB_API_KEY = os.getenv('SUB_API_KEY', '')
    SUB_API_SECRET = os.getenv('SUB_API_SECRET', '')
    SUB_NAME = os.getenv('SUB_NAME', "xx0.3_prod")

# 配置映射字典
config = {
    "test": TestConfig,
    "prod": ProdConfig,
    "default": TestConfig  # 默认使用测试环境配置
}