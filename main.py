from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
import aiohttp
import sqlite3
import json
import shlex
<<<<<<< HEAD
=======
import re
>>>>>>> 3d59563 (更新至1.0.2版本)
from pathlib import Path
from typing import Dict, Any, List, Optional


@register(
    "astrbot_plugin_sl_query",
    "DNT_OF",
<<<<<<< HEAD
    "SCP:SL 服务器查询插件 - 兼容实际 API 格式、会话隔离、解绑支持",
    "1.0.1",
=======
    "SCP:SL 服务器查询插件 - 支持官方API + EXILED实时数据双源",
    "1.0.2",
>>>>>>> 3d59563 (更新至1.0.2版本)
    "https://github.com/DNTOF/astrbot_plugin_sl_query"
)
class SLQueryPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        try:
            self.data_dir: Path = StarTools.get_data_dir("astrbot_plugin_sl_query")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path: Path = self.data_dir / "servers.db"

<<<<<<< HEAD
            # 复用 aiohttp session
            self.session = aiohttp.ClientSession()

            logger.info("[SLQuery] 初始化完成 | 数据库: %s | aiohttp session 已创建", self.db_path)
=======
            self.session = aiohttp.ClientSession()

            self._init_db()
            self._migrate_db()

            logger.info("[SLQuery] 插件 1.5.5 初始化完成")
>>>>>>> 3d59563 (更新至1.0.2版本)
        except Exception as e:
            logger.error("[SLQuery] 初始化失败: %s", e)
            self.session = None

    async def close(self):
<<<<<<< HEAD
        """插件卸载时关闭 aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("[SLQuery] aiohttp session 已关闭")

    # 数据库操作：每次使用独立连接 + 上下文管理器
=======
        if self.session and not self.session.closed:
            await self.session.close()

    def _init_db(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    session_id TEXT,
                    name TEXT,
                    server_id TEXT,
                    api_key TEXT,
                    is_exiled INTEGER DEFAULT 0,
                    exiled_ip TEXT,
                    exiled_key TEXT,
                    PRIMARY KEY (session_id, name)
                )
            ''')
            conn.commit()

    def _migrate_db(self):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(servers)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "is_exiled" not in columns:
                logger.info("[SLQuery] 正在升级数据库...")
                conn.execute("ALTER TABLE servers ADD COLUMN is_exiled INTEGER DEFAULT 0")
                conn.execute("ALTER TABLE servers ADD COLUMN exiled_ip TEXT")
                conn.execute("ALTER TABLE servers ADD COLUMN exiled_key TEXT")
                conn.commit()
                logger.info("[SLQuery] 数据库升级完成")

>>>>>>> 3d59563 (更新至1.0.2版本)
    def _db_execute(self, sql: str, params: tuple = (), fetch: bool = False):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()

<<<<<<< HEAD
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
=======
    def _get_all_servers(self, session_id: str) -> List[Dict[str, Any]]:
        rows = self._db_execute(
            "SELECT name, server_id, api_key, is_exiled, exiled_ip, exiled_key FROM servers WHERE session_id = ?",
            (session_id,),
            fetch=True
        )
        return [
            {
                "name": r[0],
                "id": r[1],
                "key": r[2],
                "is_exiled": r[3],
                "exiled_ip": r[4],
                "exiled_key": r[5]
            }
            for r in rows
        ]

    def _add_official_server(self, session_id: str, name: str, server_id: str, api_key: str):
        self._db_execute(
            "INSERT OR REPLACE INTO servers (session_id, name, server_id, api_key, is_exiled) VALUES (?, ?, ?, ?, 0)",
            (session_id, name, server_id, api_key)
        )

    def _add_exiled_server(self, session_id: str, name: str, ip: str, key: str):
        self._db_execute(
            "INSERT OR REPLACE INTO servers (session_id, name, server_id, api_key, is_exiled, exiled_ip, exiled_key) VALUES (?, ?, '', '', 1, ?, ?)",
            (session_id, name, ip, key)
        )

    def _remove_server(self, session_id: str, name: str) -> bool:
        self._db_execute("DELETE FROM servers WHERE session_id = ? AND name = ?", (session_id, name))
        return self._db_execute("SELECT changes()", fetch=True)[0][0] > 0

    def _remove_all_servers(self, session_id: str):
        self._db_execute("DELETE FROM servers WHERE session_id = ?", (session_id,))

    # ====================== 清理颜色和大小标签 ======================
    def _clean_name(self, name: str) -> str:
        if not name:
            return "未知服务器"
        # 彻底清理颜色和大小标签
        name = re.sub(r'<color=[^>]*>', ' ', name, flags=re.IGNORECASE)
        name = re.sub(r'</color>', '', name, flags=re.IGNORECASE)
        name = re.sub(r'<size=[^>]*>', '', name, flags=re.IGNORECASE)
        name = re.sub(r'</size>', '', name, flags=re.IGNORECASE)
        return name.strip()

    # ====================== EXILED 数据获取 ======================
    async def _fetch_exiled(self, ip: str, key: str) -> Optional[Dict]:
        url = f"http://{ip}:8081/get_sl_data?token={key}"
        logger.info("[SLQuery] [EXILED] 请求: %s", url)
        
        try:
            async with self.session.get(url, timeout=10) as resp:
                text = await resp.text()
                if resp.status != 200:
                    return {"success": False, "message": f"HTTP {resp.status}"}
                data = json.loads(text)
                return data
        except Exception as e:
            logger.error("[SLQuery] [EXILED] 请求异常: %s", e)
            return {"success": False, "message": str(e)}

    # ====================== 官方 API 获取 ======================
    async def _fetch_official(self, server_id: str, api_key: str) -> Dict[str, Any]:
        url = f"https://api.scpslgame.com/serverinfo.php?id={server_id}&key={api_key}&players=true&extended=true"
        async with self.session.get(url, timeout=10) as resp:
            text = await resp.text()
>>>>>>> 3d59563 (更新至1.0.2版本)
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            data = json.loads(text)
            if not data.get("Success", False):
                raise Exception("API 返回 Success=false")
            if "Servers" not in data or not data["Servers"]:
<<<<<<< HEAD
                raise Exception("Servers 数组为空或不存在")
=======
                raise Exception("Servers 数组为空")
>>>>>>> 3d59563 (更新至1.0.2版本)
            server_data = data["Servers"][0]
            server_data["Success"] = data["Success"]
            server_data["Cooldown"] = data.get("Cooldown")
            return server_data

<<<<<<< HEAD
    def _format_result(self, data: Dict[str, Any]) -> str:
        logger.info("[SLQuery] 解析数据: %s", json.dumps(data, ensure_ascii=False, indent=2))

=======
    # ====================== 格式化 ======================
    def _format_exiled(self, name: str, data: Dict) -> str:
        if not data.get("success"):
            return f"名称: {name}[EX]\nEXILED返回失败"

        d = data if "data" not in data else data.get("data", data)

        # 使用 EXILED 返回的 server_name，并清理标签
        raw_name = d.get("server_name", name)
        clean_name = self._clean_name(raw_name)

        players_list = [f"{p.get('nickname', '未知')}[{p.get('role', '未知')}]" for p in d.get("players", [])]
        player_str = "、".join(players_list) if players_list else "无"

        round_str = f"已开始 {round(d.get('round_duration', 0)/60, 1)} 分钟" if d.get("round_started") else "等待开始"

        return f"""名称: {clean_name}[EX]
人数: {d.get("players_count", 0)}/{d.get("max_players", 0)}
玩家列表: {player_str}
回合: {round_str}
核弹状态: {d.get("nuke_status", "未知")}
D级人员阵营: {d.get("d_count", 0)}
基金会阵营: {d.get("foundation_count", 0)}
SCP阵营: {d.get("scp_count", 0)}
观察者: {d.get("spectator_count", 0)}
延迟: {d.get("ping", "未知")}ms"""

    def _format_official(self, name: str, data: Dict) -> str:
>>>>>>> 3d59563 (更新至1.0.2版本)
        server_id = data.get("ID", "未知")
        port = data.get("Port", "未知")
        players_str = data.get("Players", "未知")

<<<<<<< HEAD
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

=======
        result = f"名称: {name}\n"
        result += f"【服务器 ID: {server_id} (端口: {port})】\n"

        if players_str == "未知":
            result += "未获取到玩家信息（服务器可能离线）\n"
        else:
            result += f"玩家: {players_str}\n"

>>>>>>> 3d59563 (更新至1.0.2版本)
        if "ServerName" in data:
            result += f"服务器名: {data['ServerName']}\n"
        if "Version" in data:
            result += f"版本: {data['Version']}\n"
        if "Modded" in data:
            result += f"模组: {'启用' if data['Modded'] else '无'}\n"
<<<<<<< HEAD
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
=======

        return result

    # ====================== 查询核心 ======================
    @filter.command("sl")
    async def cmd_query(self, event: AstrMessageEvent):
>>>>>>> 3d59563 (更新至1.0.2版本)
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        target_name = args[1] if len(args) > 1 else None

        servers = self._get_all_servers(session_id)
        if not servers:
<<<<<<< HEAD
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
=======
            yield event.plain_result("当前会话未绑定任何服务器\n使用 /bind 或 /bindex 添加")
            return

        if target_name:
            matched = [s for s in servers if target_name.lower() in s["name"].lower()]
            if not matched:
                yield event.plain_result(f"未找到 '{target_name}'")
                return
            targets = matched
        else:
            targets = servers

        lines = []

        for target in targets:
            name = target["name"]
            is_exiled = target.get("is_exiled", 0) == 1

            if is_exiled:
                ex_data = await self._fetch_exiled(target["exiled_ip"], target["exiled_key"])
                lines.append(self._format_exiled(name, ex_data or {"success": False}))
            else:
                try:
                    official_data = await self._fetch_official(target["id"], target["key"])
                    lines.append(self._format_official(name, official_data))
                except Exception as e:
                    lines.append(f"名称: {name}\n官方API查询失败: {str(e)}")

            # 添加分隔线（除了最后一个）
            if target != targets[-1]:
                lines.append("===============")

        result = "\n".join(lines)
        yield event.plain_result(result)

    # ====================== 其他命令 ======================
    @filter.command("bind")
    async def cmd_bind(self, event: AstrMessageEvent):
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=3)
        if len(args) < 3:
            yield event.plain_result("用法: /bind <id> <key> [name]")
            return

        server_id = args[1]
        api_key = args[2]
        name = args[3] if len(args) > 3 else f"服务器_{server_id}"

        self._add_official_server(session_id, name, server_id, api_key)
        yield event.plain_result(f"绑定成功\n名称: {name}\nID: {server_id}")

    @filter.command("bindex")
    async def cmd_bindex(self, event: AstrMessageEvent):
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=2)
        if len(args) < 3:
            yield event.plain_result("用法: /bindex <IP> <Key>")
            return

        ip = args[1]
        key = args[2]
        name = f"EX服务器_{ip}"

        self._add_exiled_server(session_id, name, ip, key)
        yield event.plain_result(f"EXILED 绑定成功\n名称: {name}\nIP: {ip}")

    @filter.command("sllist")
    async def cmd_list(self, event: AstrMessageEvent):
        session_id = event.session_id
        servers = self._get_all_servers(session_id)
        if not servers:
            yield event.plain_result("本会话暂无绑定服务器")
            return

        lines = ["已绑定服务器列表："]
        for s in servers:
            tag = "[EX]" if s.get("is_exiled") else ""
            lines.append(f"- {s['name']}{tag}")
        yield event.plain_result("\n".join(lines))

    @filter.command("unbind")
    async def cmd_unbind(self, event: AstrMessageEvent):
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        if len(args) < 2:
            yield event.plain_result("用法: /unbind 服务器名")
            return
        name = args[1].strip()
        if self._remove_server(session_id, name):
            yield event.plain_result(f"已解绑: {name}")
        else:
            yield event.plain_result(f"未找到: {name}")

    @filter.command("unbindall")
    async def cmd_unbindall(self, event: AstrMessageEvent):
        session_id = event.session_id
        self._remove_all_servers(session_id)
        yield event.plain_result("本会话所有绑定已清空")
>>>>>>> 3d59563 (更新至1.0.2版本)
