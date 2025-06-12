import asyncio
from .exchange.ws_client import WebSocketClient
from .exchange.order_manager import OrderManager
from .utils.logger import logger
from datetime import datetime

# # 配置日志
# logger = setup_logger()



async def app():

    logger.info("\n" + r"""
     ███╗   ██╗██╗ ██████╗ ██╗  ██╗████████╗███████╗    ██╗    ██╗ ██████╗ ███████╗████████╗██╗  ██╗
     ████╗  ██║██║██╔════╝ ██║  ██║╚══██╔══╝██╔════╝    ██║    ██║██╔═══██╗██╔════╝╚══██╔══╝██║  ██║
     ██╔██╗ ██║██║██║  ███╗███████║   ██║   █████╗      ██║ █╗ ██║██║   ██║███████╗   ██║   ███████║
     ██║╚██╗██║██║██║   ██║██╔══██║   ██║   ██╔══╝      ██║███╗██║██║   ██║╚════██║   ██║   ██╔══██║
     ██║ ╚████║██║╚██████╔╝██║  ██║   ██║   ███████╗    ╚███╔███╔╝╚██████╔╝███████║   ██║   ██║  ██║
     ╚═╝  ╚═══╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝     ╚══╝╚══╝  ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝
    """.strip())
    logger.info(f"■ 守夜人系统启动中... 地球日 {datetime.now()} ■")
    logger.info("▶▶ 星舰能源核心预热...")

    # 初始化main_order_map
    main_order_map = {}

    # 初始化WebSocket客户端和订单管理器
    ws_client = WebSocketClient()
    try:
        await ws_client.start()
        logger.info("✔ 量子链路建立成功 | 通讯频率: 7.83Hz (舒曼共振)")
        order_manager = OrderManager(ws_client)
    
        logger.info("▶▶ 加载战术决策矩阵...")

        # 启动心跳检测
        heartbeat_task = asyncio.create_task(heartbeat())
        logger.info("▷ 启动曲速引擎核心 | 心跳脉冲间隔: 600秒")

        # 启动订单管理器
        await order_manager.start_follow_order(main_order_map)
        logger.info("订单管理器已启动")
        logger.info("✔ 战术AI神经元网络激活 | 追踪模式: 德尔塔协议")

    except KeyboardInterrupt as e:
        logger.error("‼ 收到紧急跃迁指令 | 终止代码: %s", e)
        logger.error("收到退出信号，准备关闭 KeyboardInterrupt: %s", e)

    finally:
        # 关闭WebSocket连接
        await ws_client.shutdown()
        heartbeat_task.cancel()
        logger.info("WebSocket连接已关闭")
        logger.info("心跳停止")
        logger.info("程序已退出")
        logger.info("◀ 解除星舰能源核心链接")
        logger.info("▇▇▇ 曲速引擎关闭 ▇▇▇")
        logger.info("■ 守夜人系统离线 ■")

async def heartbeat(interval=600):
    """程序心跳检测, 默认每60秒检测一次"""
    while True:
        logger.info("程序心跳正常 - 运行状态良好")
        logger.info("曲速引擎工作正常 - 运行状态良好")
        await asyncio.sleep(interval)



if __name__ == "__main__":
    asyncio.run(app())


