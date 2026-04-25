from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
import aiohttp
import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

@register(
    "astrbot_plugin_sl_query",
    "DNT_OF",
    "SCP:SL 服务器查询插件 - 支持官方API + EXILED实时数据双源",
    "1.0.3",
    "https://github.com/DNTOF/astrbot_plugin_sl_query"
)
class SLQueryPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        try:
            self.data_dir: Path = StarTools.get_data_dir("astrbot_plugin_sl_query")
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.db_path: Path = self.data_dir / "servers.db"
            # [修复] ClientSession 不在同步 __init__ 里创建，避免事件循环问题
            self._session: Optional[aiohttp.ClientSession] = None
            self._init_db()
            self._migrate_db()
            logger.info("[SLQuery] 插件 1.0.3 初始化完成")
        except Exception as e:
            logger.error("[SLQuery] 初始化失败: %s", e)

    @property
    def session(self) -> aiohttp.ClientSession:
        """懒初始化 ClientSession，确保在事件循环内创建"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

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

    def _db_execute(self, sql: str, params: tuple = (), fetch: bool = False):
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if fetch:
                return cursor.fetchall()
            conn.commit()

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

    # [修复] 原来分两次连接查 changes() 永远为 0，改为在同一连接内用 cursor.rowcount 判断
    def _remove_server(self, session_id: str, name: str) -> bool:
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM servers WHERE session_id = ? AND name = ?",
                (session_id, name)
            )
            conn.commit()
            return cursor.rowcount > 0

    # [新增] 按 EX 服务器 IP 解绑
    def _remove_exiled_server_by_ip(self, session_id: str, ip: str) -> bool:
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM servers WHERE session_id = ? AND is_exiled = 1 AND exiled_ip = ?",
                (session_id, ip)
            )
            conn.commit()
            return cursor.rowcount > 0

    def _remove_all_servers(self, session_id: str):
        self._db_execute("DELETE FROM servers WHERE session_id = ?", (session_id,))

    # ====================== 清理颜色和大小标签 ======================

    def _clean_name(self, name: str) -> str:
        if not name:
            return "未知服务器"
        name = re.sub(r'<color=[^>]*>', '', name, flags=re.IGNORECASE)
        name = re.sub(r'</color>', '', name, flags=re.IGNORECASE)
        name = re.sub(r'<size=[^>]*>', '', name, flags=re.IGNORECASE)
        name = re.sub(r'</size>', '', name, flags=re.IGNORECASE)
        return name.strip()

    # ====================== EXILED 数据获取 ======================

    async def _fetch_exiled(self, ip: str, key: str) -> Optional[Dict]:
        url = f"http://{ip}:8081/get_sl_data?token={key}"
        logger.info("[SLQuery] [EXILED] 请求: %s", url)
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
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
        async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise Exception(f"HTTP {resp.status}")
            data = json.loads(text)
            if not data.get("Success", False):
                raise Exception("API 返回 Success=false")
            if "Servers" not in data or not data["Servers"]:
                raise Exception("Servers 数组为空")
            server_data = data["Servers"][0]
            server_data["Success"] = data["Success"]
            server_data["Cooldown"] = data.get("Cooldown")
            return server_data

    # ====================== 格式化 ======================

    def _format_exiled(self, name: str, data: Dict) -> str:
        if not data.get("success"):
            return f"名称: {name}[EX]\nEXILED返回失败"

        d = data if "data" not in data else data.get("data", data)

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
        server_id = data.get("ID", "未知")
        port = data.get("Port", "未知")
        players_str = data.get("Players", "未知")

        result = f"名称: {name}\n"
        result += f"【服务器 ID: {server_id} (端口: {port})】\n"

        if players_str == "未知":
            result += "未获取到玩家信息（服务器可能离线）\n"
        else:
            result += f"玩家: {players_str}\n"

        if "ServerName" in data:
            result += f"服务器名: {data['ServerName']}\n"
        if "Version" in data:
            result += f"版本: {data['Version']}\n"
        if "Modded" in data:
            result += f"模组: {'启用' if data['Modded'] else '无'}\n"

        return result

    # ====================== 查询核心 ======================

    @filter.command("sl")
    async def cmd_query(self, event: AstrMessageEvent):
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        target_name = args[1] if len(args) > 1 else None

        servers = self._get_all_servers(session_id)
        if not servers:
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
            yield event.plain_result("用法: /bind <id> <key> [name]\n提示: 绑定 EXILED 服务器请使用 /bindex")
            return

        server_id = args[1]
        api_key = args[2]

        # 官方 API 的 Account ID 是纯数字，若含 '.' 说明填的是 IP，引导去用 /bindex
        if not server_id.isdigit():
            yield event.plain_result(
                f"❌ ID '{server_id}' 格式不正确，官方 API 的 ID 应为纯数字\n"
                "如果你要绑定 EXILED 服务器，请使用:\n/bindex <IP> <Key>"
            )
            return

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
            if s.get("is_exiled"):
                lines.append(f"- {s['name']}[EX]  (IP: {s['exiled_ip']})")
            else:
                lines.append(f"- {s['name']}")
        yield event.plain_result("\n".join(lines))

    @filter.command("unbind")
    async def cmd_unbind(self, event: AstrMessageEvent):
        """
        解绑服务器。
        - /unbind <服务器名>   按名称解绑（官方API服务器 或 EX服务器均可）
        - /unbind <IP>         按 IP 解绑 EX 服务器
        """
        session_id = event.session_id
        args = event.message_str.strip().split(maxsplit=1)
        if len(args) < 2:
            yield event.plain_result("用法:\n/unbind <服务器名>  —— 按名称解绑\n/unbind <IP>        —— 按 IP 解绑 EX 服务器")
            return

        target = args[1].strip()

        # 先尝试按名称解绑（兼容所有类型）
        if self._remove_server(session_id, target):
            yield event.plain_result(f"已解绑: {target}")
            return

        # 名称未命中，再尝试按 EX 服务器 IP 解绑
        if self._remove_exiled_server_by_ip(session_id, target):
            yield event.plain_result(f"已解绑 IP 为 {target} 的 EX 服务器")
            return

        yield event.plain_result(f"未找到名称或 IP 为 '{target}' 的服务器")

    @filter.command("unbindall")
    async def cmd_unbindall(self, event: AstrMessageEvent):
        session_id = event.session_id
        self._remove_all_servers(session_id)
        yield event.plain_result("本会话所有绑定已清空")
