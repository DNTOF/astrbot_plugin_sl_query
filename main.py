from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
import aiohttp
import sqlite3
import json
import shlex
from pathlib import Path
from typing import Dict, Any, List, Optional


@register(
    "astrbot_plugin_sl_query",
    "DNT_OF",
    "SCP:SL 服务器查询插件 - 兼容实际 API 格式、会话隔离、解绑支持",
    "1.0.1",
    "https://github.com/DNTOF/astrbot_plugin_sl_query"
)
class SLQueryPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        try:
            self.data_dir: Path = StarTools.get_data_dir("astrbot_plugin_sl_query")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path: Path = self.data_dir / "servers.db"

            # 复用 aiohttp session
            self.session = aiohttp.ClientSession()

            logger.info("[SLQuery] 初始化完成 | 数据库: %s | aiohttp session 已创建", self.db_path)
        except Exception as e:
            logger.error("[SLQuery] 初始化失败: %s", e)
            self.session = None

    async def close(self):
        """插件卸载时关闭 aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[SLQuery] aiohttp session 已关闭")

    # 数据库操作：每次使用独立连接 + 上下文管理器
    def _db_execute(self, sql: str, params: tuple = (), fetch: bool = False):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()

    def _get_all_servers(self, session_id: str) -> List[Dict[str, str]]:
        rows = self._db_execute(
            "SELECT name, server_id, api_key FROM servers WHERE session_id = ?",
            (session_id,),
            fetch=True
        )
        return [{"name": r[0], "id": r[1], "key": r[2]} for r in rows]

    def _get_server(self, session_id: str, name: str) -> Optional[Dict[str, str]]:
        rows = self._db_execute(
            "SELECT server_id, api_key FROM servers WHERE session_id = ? AND name = ?",
            (session_id, name),
            fetch=True
        )
        if rows:
            return {"id": rows[0][0], "key": rows[0][1], "name": name}
        return None

    def _add_or_update_server(self, session_id: str, name: str, server_id: str, api_key: str):
        self._db_execute(
            """
            INSERT OR REPLACE INTO servers (session_id, name, server_id, api_key)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, name, server_id, api_key)
        )
        logger.info("[SLQuery] 绑定/更新 | 会话: %s | 名称: %s | ID: %s", session_id, name, server_id)

    def _remove_server(self, session_id: str, name: str) -> bool:
        self._db_execute(
            "DELETE FROM servers WHERE session_id = ? AND name = ?",
            (session_id, name)
        )
        changes = self._db_execute("SELECT changes()", fetch=True)[0][0]
        deleted = changes > 0
        if deleted:
            logger.info("[SLQuery] 解绑成功 | 会话: %s | 名称: %s", session_id, name)
        return deleted

    def _remove_all_servers(self, session_id: str):
        self._db_execute("DELETE FROM servers WHERE session_id = ?", (session_id,))
        deleted_count = self._db_execute("SELECT changes()", fetch=True)[0][0]
        if deleted_count > 0:
            logger.info("[SLQuery] 清空绑定 | 会话: %s | 数量: %d", session_id, deleted_count)

    async def _fetch_server_info(self, server_id: str, api_key: str) -> Dict[str, Any]:
        url = f"https://api.scpslgame.com/serverinfo.php?id={server_id}&key={api_key}&players=true&extended=true"
        async with self.session.get(url, timeout=10) as resp:
            text = await resp.text()
            logger.debug("[SLQuery] API 请求 | 状态: %d | 响应: %s", resp.status, text[:500])
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            data = json.loads(text)
            if not data.get("Success", False):
                raise Exception("API 返回 Success=false")
            if "Servers" not in data or not data["Servers"]:
                raise Exception("Servers 数组为空或不存在")
            server_data = data["Servers"][0]
            server_data["Success"] = data["Success"]
            server_data["Cooldown"] = data.get("Cooldown")
            return server_data

    def _format_result(self, data: Dict[str, Any]) -> str:
        logger.info("[SLQuery] 解析数据: %s", json.dumps(data, ensure_ascii=False, indent=2))

        server_id = data.get("ID", "未知")
        port = data.get("Port", "未知")
        players_str = data.get("Players", "未知")

        result = f"【服务器 ID: {server_id} (端口: {port})】\n"

        if players_str == "未知":
            result += "未获取到玩家信息（服务器可能离线或未返回完整数据）\n"
        else:
            result += f"玩家: {players_str}\n"

        # 在线状态判断
        if "Online" in data:
            online = data["Online"]
            result += f"状态: {'在线' if online else '离线'}\n"
        elif players_str != "未知" and players_str != "0/0":
            result += "状态: 在线\n"
        else:
            result += "状态: 未明确返回（可能离线或加载中）\n"

        if "ServerName" in data:
            result += f"服务器名: {data['ServerName']}\n"
        if "Version" in data:
            result += f"版本: {data['Version']}\n"
        if "Modded" in data:
            result += f"模组: {'启用' if data['Modded'] else '无'}\n"
        if "Cooldown" in data:
            result += f"查询冷却: {data['Cooldown']} 秒\n"

        return result

    @filter.command("bind")
    async def cmd_bind(self, event: AstrMessageEvent):
        logger.info("[SLQuery] /bind 被触发")
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        if len(args) < 2:
            yield event.plain_result("用法: /bind id=xxxx key=yyyy [name=\"zzz\"]")
            return

        # 使用 shlex 支持引号包裹的 name（支持空格）
        try:
            params_list = shlex.split(args[1])
        except ValueError:
            yield event.plain_result("参数解析失败，请检查引号是否匹配")
            return

        params = {}
        for part in params_list:
            if '=' in part:
                k, v = part.split('=', 1)
                params[k.lower()] = v.strip()

        sid = params.get("id")
        key = params.get("key") or params.get("token") or params.get("apikey")
        name = params.get("name") or f"服务器{len(self._get_all_servers(session_id)) + 1}"

        if not sid or not key:
            yield event.plain_result("缺少 id 或 key\n示例: /bind id=123456 key=abcdef123 name=\"主服\"")
            return

        self._add_or_update_server(session_id, name, sid, key)
        yield event.plain_result(f"绑定成功（本会话）\n名称: {name}\nID: {sid}")

    @filter.command("unbind")
    async def cmd_unbind(self, event: AstrMessageEvent):
        logger.info("[SLQuery] /unbind 被触发")
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        if len(args) < 2:
            yield event.plain_result("用法: /unbind 服务器名\n示例: /unbind 主服")
            return

        name = args[1].strip()
        if self._remove_server(session_id, name):
            yield event.plain_result(f"已解绑: {name}")
        else:
            yield event.plain_result(f"未找到绑定: {name}")

    @filter.command("unbindall")
    async def cmd_unbindall(self, event: AstrMessageEvent):
        logger.info("[SLQuery] /unbindall 被触发")
        session_id = event.session_id
        self._remove_all_servers(session_id)
        yield event.plain_result("本会话所有绑定已清空")

    @filter.command("sllist")
    async def cmd_list(self, event: AstrMessageEvent):
        logger.info("[SLQuery] /sllist 被触发")
        session_id = event.session_id
        servers = self._get_all_servers(session_id)
        if not servers:
            yield event.plain_result("本会话暂无绑定服务器\n使用 /bind 添加")
            return

        lines = ["本会话绑定列表："]
        for s in servers:
            lines.append(f"- {s['name']} (ID: {s['id']})")
        yield event.plain_result("\n".join(lines))

    @filter.command("sl")
    async def cmd_query(self, event: AstrMessageEvent):
        logger.info("[SLQuery] /sl 被触发")
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        target_name = args[1] if len(args) > 1 else None

        servers = self._get_all_servers(session_id)
        if not servers:
            yield event.plain_result("本会话无绑定服务器\n请先使用 /bind 添加")
            return

        if not target_name:
            target = servers[0]
            target_name = target["name"]
        else:
            matched = [s for s in servers if target_name.lower() in s["name"].lower()]
            if not matched:
                names = ", ".join(s["name"] for s in servers) or "无"
                yield event.plain_result(f"未找到 '{target_name}'\n已绑定: {names}")
                return
            target = matched[0]
            target_name = target["name"]

        try:
            data = await self._fetch_server_info(target["id"], target["key"])
            yield event.plain_result(self._format_result(data))
        except Exception as e:
            yield event.plain_result(f"查询失败 ({target_name}): {str(e)}\n请检查服务器是否在线，或 token/ID 是否正确")