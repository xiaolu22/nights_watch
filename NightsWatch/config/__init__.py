import os
# 从 settings 模块导入定义
from .settings import Config, TestConfig, ProdConfig, config


# 读取环境变量 ENV，如果未设置则默认为 'test'，并转换为小写
_env_setting = os.getenv('ENV', 'test').lower()
# 使用小写的环境变量值从 config_map 字典获取对应的配置类
# 如果找不到对应的键，则使用默认配置类
_ActiveConfigClass = config.get(_env_setting, config["default"])


# 实例化选定的配置类
_config_instance = _ActiveConfigClass()

# 将配置实例的属性导出到包级别 (NightsWatch.config)
_exported_vars = []
for _key in dir(_config_instance):
    # 过滤掉私有属性和方法
    if not _key.startswith('__'):
        _value = getattr(_config_instance, _key)
        # 检查是否是方法，只导出非方法的属性
        if not callable(_value):
            globals()[_key] = _value
            _exported_vars.append(_key)


__all__ = _exported_vars


# 清理在 __init__.py 执行过程中使用的临时变量
del os, Config, TestConfig, ProdConfig, config
del _env_setting, _ActiveConfigClass, _config_instance, _key, _value, _exported_vars