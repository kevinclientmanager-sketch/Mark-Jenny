"""
MCP Client — Manages Model Context Protocol servers.
Connects to MCP servers, discovers tools, and invokes them.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.core.config import get_settings

settings = get_settings()

MCP_CONFIG_DIR = Path(os.environ.get("MARK_IMTI_DATA", ".")) / "mcp"
MCP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

MCP_CONFIG_FILE = MCP_CONFIG_DIR / "servers.json"


class MCPClient:
    def __init__(self):
        self.servers: Dict[str, Dict] = {}
        self.active_connections: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        # Persisted in the database so connected servers survive a deploy.
        # Falls back to the on-disk file for local/desktop use.
        try:
            from app.db.base import SessionLocal
            from app.models.system_kv import SystemKV
            db = SessionLocal()
            try:
                row = db.query(SystemKV).filter(SystemKV.key == "mcp_servers").first()
                if row and isinstance(row.value, dict):
                    self.servers = row.value.get("servers", {}) or {}
                    return
            finally:
                db.close()
        except Exception:
            pass
        if MCP_CONFIG_FILE.exists():
            try:
                with open(MCP_CONFIG_FILE) as f:
                    self.servers = json.load(f).get("servers", {})
            except Exception:
                self.servers = {}
        else:
            self.servers = {}

    def _save_config(self):
        payload = {"servers": self.servers, "updated_at": datetime.utcnow().isoformat()}
        try:
            from app.db.base import SessionLocal
            from app.models.system_kv import SystemKV
            db = SessionLocal()
            try:
                row = db.query(SystemKV).filter(SystemKV.key == "mcp_servers").first()
                if not row:
                    row = SystemKV(key="mcp_servers", value=payload)
                    db.add(row)
                else:
                    row.value = payload
                db.commit()
                return
            finally:
                db.close()
        except Exception:
            pass
        try:
            with open(MCP_CONFIG_FILE, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            pass

    def list_servers(self) -> List[Dict]:
        return [{"id": k, **v} for k, v in self.servers.items()]

    def get_server(self, server_id: str) -> Optional[Dict]:
        return self.servers.get(server_id)

    def add_server(self, server_id: str, config: Dict[str, Any]) -> Dict:
        # Keep any tools already discovered for this server so re-saving a
        # credential does not wipe the browsable tool list.
        existing_tools = (self.servers.get(server_id) or {}).get("tools", [])
        self.servers[server_id] = {
            "name": config.get("name", server_id),
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "env": config.get("env", {}),
            "type": config.get("type", "stdio"),
            "url": config.get("url", ""),
            "enabled": config.get("enabled", True),
            "auto_start": config.get("auto_start", False),
            "tools": existing_tools,
            "added_at": datetime.utcnow().isoformat(),
        }
        self._save_config()
        return {"success": True, "server_id": server_id}

    def update_server(self, server_id: str, config: Dict[str, Any]) -> Dict:
        if server_id not in self.servers:
            return {"success": False, "error": f"Server {server_id} not found"}
        self.servers[server_id].update(config)
        self._save_config()
        return {"success": True}

    def remove_server(self, server_id: str) -> Dict:
        if server_id not in self.servers:
            return {"success": False, "error": f"Server {server_id} not found"}
        del self.servers[server_id]
        self._save_config()
        return {"success": True}

    async def start_server(self, server_id: str) -> Dict:
        config = self.servers.get(server_id)
        if not config:
            return {"success": False, "error": f"Server {server_id} not found"}

        if server_id in self.active_connections:
            return {"success": True, "message": "Already running"}

        try:
            cmd = config.get("command", "")
            args = config.get("args", [])
            env = {**os.environ, **config.get("env", {})}

            if not cmd:
                return {"success": False, "error": "No command specified"}

            proc = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            self.active_connections[server_id] = {
                "process": proc,
                "started_at": datetime.utcnow(),
                "tools": [],
            }

            # Send initialize request
            init_msg = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "MARK-IMTI", "version": "1.0.0"},
                },
            }

            await self._send_message(server_id, init_msg)
            response = await self._read_response_for(server_id, 1, timeout=30)

            if response and "result" in response:
                # Proper MCP handshake: acknowledge before asking for tools.
                try:
                    await self._send_message(server_id, {
                        "jsonrpc": "2.0", "method": "notifications/initialized",
                    })
                except Exception:
                    pass
                tools_msg = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {},
                }
                await self._send_message(server_id, tools_msg)
                tools_response = await self._read_response_for(server_id, 2, timeout=30)

                if tools_response and "result" in tools_response:
                    tools = tools_response["result"].get("tools", []) or []
                    self.servers[server_id]["tools"] = [
                        {"name": t.get("name"),
                         "description": t.get("description", ""),
                         "inputSchema": t.get("inputSchema") or t.get("input_schema") or {}}
                        for t in tools if isinstance(t, dict) and t.get("name")
                    ]
                    self.active_connections[server_id]["tools"] = tools
                    self._save_config()

            return {
                "success": True,
                "message": f"Server {server_id} started",
                "tools": len(self.servers[server_id].get("tools", [])),
                # The actual tool definitions, so callers can browse them.
                "tool_list": self.servers[server_id].get("tools", []),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def stop_server(self, server_id: str) -> Dict:
        conn = self.active_connections.pop(server_id, None)
        if conn and conn.get("process"):
            conn["process"].terminate()
            try:
                await asyncio.wait_for(conn["process"].wait(), timeout=5)
            except asyncio.TimeoutError:
                conn["process"].kill()
        return {"success": True}

    async def _read_response_for(self, server_id: str, msg_id: int, timeout: float = 20) -> Optional[Dict]:
        """Read until the JSON-RPC response with this id arrives.

        MCP servers interleave notifications (e.g. notifications/initialized)
        between request/response pairs, so reading a single line can easily
        consume a notification and miss the actual result.
        """
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while loop.time() < deadline:
            remaining = max(0.5, deadline - loop.time())
            msg = await self._read_message(server_id, timeout=remaining)
            if msg is None:
                break
            if msg.get("id") == msg_id:
                return msg
            # notifications / server-initiated requests carry no matching id
        return None

    async def call_tool(self, server_id: str, tool_name: str, arguments: Dict = None) -> Dict:
        conn = self.active_connections.get(server_id)
        if not conn:
            return {"success": False, "error": f"Server {server_id} not running (it may have stopped - start it again)"}

        try:
            msg = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {},
                },
            }
            await self._send_message(server_id, msg)
            response = await self._read_response_for(server_id, 3, timeout=120)

            if response and "result" in response:
                return {"success": True, "result": response["result"]}
            elif response and "error" in response:
                return {"success": False, "error": response["error"]}
            return {"success": False, "error": "No response from server"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _send_message(self, server_id: str, msg: Dict):
        conn = self.active_connections.get(server_id)
        if conn and conn.get("process") and conn["process"].stdin:
            data = json.dumps(msg) + "\n"
            conn["process"].stdin.write(data.encode())
            await conn["process"].stdin.drain()

    async def _read_message(self, server_id: str, timeout: float = 10) -> Optional[Dict]:
        conn = self.active_connections.get(server_id)
        if not conn or not conn.get("process"):
            return None

        try:
            proc = conn["process"]
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if line:
                return json.loads(line.decode().strip())
        except (asyncio.TimeoutError, json.JSONDecodeError):
            pass
        return None

    def get_all_tools(self) -> List[Dict]:
        tools = []
        for server_id, server in self.servers.items():
            for tool in server.get("tools", []):
                tools.append({
                    "server": server_id,
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                })
        return tools

    async def start_all_enabled(self):
        for server_id, config in self.servers.items():
            if config.get("enabled") and config.get("auto_start"):
                await self.start_server(server_id)

    def get_stats(self) -> Dict:
        return {
            "total_servers": len(self.servers),
            "active": len(self.active_connections),
            "total_tools": sum(len(s.get("tools", [])) for s in self.servers.values()),
        }


# Singleton
mcp_client = MCPClient()
