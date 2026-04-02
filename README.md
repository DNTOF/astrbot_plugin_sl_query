<<<<<<< HEAD
# astrbot_plugin_sl_query

SCP:SL 服务器查询插件

## 命令
/bind id=xxxx key=yyyy name=zzz      → 绑定  
/unbind 服务器名                       → 解绑指定  
/unbindall                             → 清空本会话  
/sllist                                → 查看列表  
/sl [服务器名]                         → 查询（默认第一个）
=======
# SCP:SL 查询插件（astrbot_plugin_sl_query）

一个功能强大的 SCP:SL 服务器查询插件，支持**官方 API** + **EXILED 实时数据** 双源查询。

### 功能特点

- 支持官方 API 查询（传统方式）
- 支持 EXILED 插件实时数据（玩家列表、回合时间、核弹状态、阵营人数等）
- 一个群聊可同时绑定多个官方服务器 + 多个 EXILED 服务器
- EXILED 数据会显示 `[EX]` 标识，并使用服务器返回的真实名称
- 数据按群聊/私聊会话隔离
- 支持绑定、解绑、列表、查询等完整命令

### 命令列表

| 命令 | 说明 |
|------|------|
| `/bind <id> <key> [name]` | 绑定官方 API 服务器 |
| `/bindex <IP> <Key>` | 绑定 EXILED 服务器 |
| `/sl [服务器名]` | 查询服务器信息（同时显示所有绑定） |
| `/sllist` | 显示本会话所有绑定服务器 |
| `/unbind <服务器名>` | 解绑指定服务器 |
| `/unbindall` | 解绑本会话所有服务器 |
>>>>>>> 3d59563 (更新至1.0.2版本)

## 安装
1. 放入 plugins/astrbot_plugin_sl_query/
2. 重启 AstrBot
3. 用 /bind 绑定（id 必须是 !id 返回的Account ID）
<<<<<<< HEAD

## 日志查看
WebUI 或 docker logs 搜 [SLQuery]，可看到 API 原始响应和解析数据

## 后续计划
- [ ] 优化插件性能
- [ ] 开发Exiled插件服务端，实现查看更多数据

作者：DNT_OF
版本：1.0.1
=======
4. 或者使用/bindex绑定（ip为游戏服务器ip，key详见exiled端配置文件）

## 后续计划
- [x] 优化插件性能
- [x] 开发Exiled插件服务端，实现查看更多数据

作者：DNT_OF
版本：1.0.2
>>>>>>> 3d59563 (更新至1.0.2版本)

欢迎使用Issue提交更多改进想法
