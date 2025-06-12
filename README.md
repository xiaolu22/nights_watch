# 守夜人(nights_watch)

#### 介绍
币安交易跟随机器人

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


#### 特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)

#### todo
- [ ] 增加多线程
- [ ] 增加多交易所
- [ ] 增加多策略
- [ ] 增加账户信息管理，管理仓位
- [ ] 集成数据库
- [ ] 缺一个仓位管理，缺一个修正持仓
- [ ] 增加主账号跟子账号持仓信息, 并且每30分钟做一次修正
- [ ]   我感觉后面有界面了， 有一个列表可以操作所有的跟单账号。 如果机器处理有问题了，还能人工接入。 
- [ ] 比如说最开始主号下单 副号只执行比例的百分之30  然后每亏损2%执行比例10%  当主号亏损到14%副号比例的全部追加完
