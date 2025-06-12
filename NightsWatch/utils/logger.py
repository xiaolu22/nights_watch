import logging

def setup_logger():
    logger = logging.getLogger("nights_watch(守夜人)")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()

    handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


# 创建全局logger实例
logger = setup_logger()

# 导出logger
__all__ = ['logger', 'setup_logger']