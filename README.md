# astrbot_plugin_sl_query

SCP:SL 服务器查询插件

## 命令
/bind id=xxxx key=yyyy [name=zzz]      → 绑定  
/unbind 服务器名                       → 解绑指定  
/unbindall                             → 清空本会话  
/sllist                                → 查看列表  
/sl [服务器名]                         → 查询（默认第一个）

## 安装
1. 放入 plugins/astrbot_plugin_sl_query/
2. 重启 AstrBot
3. 用 /bind 绑定（id 必须是 !id 返回的Account ID）

## 日志查看
WebUI 或 docker logs 搜 [SLQuery]，可看到 API 原始响应和解析数据

## 后续计划
- [ ] 优化插件性能
- [ ] 开发Exiled插件服务端，实现查看更多数据

作者：DNT_OF
版本：1.0.1

欢迎使用Issue提交更多改进想法
