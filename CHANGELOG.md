## [1.0.0] - 2026-02-25
### Added
- 初始版本：支持 /sl 查询 SCP:SL 服务器基本信息（使用官方 API）
- 命令：/sl [服务器名]
- 使用 requests → 后续换 aiohttp
- 支持多服务器绑定（默认第一个或指定名称查询）
- 使用 SQLite 存储
- 支持会话隔离（每个 QQ 群/私聊独立绑定，不串台)

### Changed
- 命令分离：
  - /bind → 绑定
  - /unbind / unbindall → 解绑（后续添加）
  - /sllist → 查看列表
  - /sl → 查询

## [1.0.1] - 2026-02-28
### Fixed
- 修复了一些问题:
  - 移除 __del__ 方法，数据库操作全部使用 with 上下文管理器（自动关闭连接）
  - 每次数据库操作独立连接，避免长连接导致的 database is locked 风险
  - aiohttp.ClientSession 在初始化时创建一次复用，并在 close 方法中关闭
  - cmd_bind 参数解析使用 shlex.split，支持引号包裹的 name（如 name="My Server Name" 不会被截断）
  - 修复 API 返回结构解析问题（顶层有 "Success" 和 "Servers" 数组）
  - _fetch_server_info 现在正确提取 Servers[0] 数据
  - 兼容 Players 为字符串格式（如 "0/30"）

## [1.0.2] - 2026-04-02

### 新增
- 支持 EXILED 实时数据源（通过 `/bindex <IP> <Key>` 绑定）
- `/sl` 命令现在会同时显示所有绑定的官方 API 和 EXILED 服务器
- EXILED 数据显示时自动添加 `[EX]` 标识
- 优先使用 EXILED 返回的真实服务器名称，并自动清理 `<color>` 和 `<size>` 等标签
- EXILED 和官方 API 数据之间使用 `===============` 分隔
- 数据库自动升级，支持同时存储官方和 EXILED 绑定
- 优化了错误处理和日志输出

### 改进
- `/bind` 命令改为简洁格式：`/bind <id> <key> [name]`
