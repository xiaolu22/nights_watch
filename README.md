# 守夜人(nights_watch)

#### 介绍
币安交易跟随机器人(只支持U本位合约)。

#### 软件架构
项目采用异步架构

```
nights_watch/
├── README.md
├── README_en.md
├── README_zh.md
├── doc
├── NightsWatch.py
├── __init__.py
├── main.py
├── config.py
├── exchange/
│   ├── __init__.py
│   ├── ws_client.py       # 交易所 WebSocket 客户端，用于实时数据交互
│   ├── order_manager.py   # 处理交易所订单相关操作
├── utils/
│   ├── __init__.py
│   ├── logger.py          # 日志记录工具
├── tests
├── requirements.txt
```

#### 安装教程

1.  启动
在nights_watch目录下执行
```
python main.py
```
2.  配置
在nights_watch/config/settings.py中配置
```
2.  xxxx
3.  xxxx

#### 使用说明

1.  xxxx
2.  xxxx
3.  xxxx

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request


#### 交流群
QQ群：1051968388





