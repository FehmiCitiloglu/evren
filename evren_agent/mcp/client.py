from __future__ import annotations
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

from evren_agent.mcp.protocol import (
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
    MCPCallToolResult,
    MCPContentItem,
    MCPToolSchema,
)

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Model Context Protocol (MCP) Client.
    Supports:
    - Stdio transport (spawns subprocess and speaks newline-delimited JSON-RPC 2.0)
    - SSE / HTTP transport (queries MCP HTTP endpoints)
    """

    def __init__(
        self,
        name: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
    ):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.url = url
        self.is_stdio = bool(command)

        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id: int = 1
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._is_connected: bool = False
        self._server_info: Dict[str, Any] = {}
        self._tools_cache: List[MCPToolSchema] = []

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self) -> None:
        """Start the process / connection and perform MCP handshake."""
        if self._is_connected:
            return

        if self.is_stdio:
            await self._connect_stdio()
        elif self.url:
            await self._connect_http()
        else:
            raise ValueError(f"MCP client '{self.name}' must have either command or url specified.")

        await self._initialize()
        self._is_connected = True
        logger.info("Connected to MCP server '%s'", self.name)

    async def _connect_stdio(self) -> None:
        cmd_env = os.environ.copy()
        cmd_env.update(self.env)

        logger.info("Launching MCP server '%s': %s %s", self.name, self.command, " ".join(self.args))
        self._process = await asyncio.create_subprocess_exec(
            self.command,  # type: ignore
            *self.args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=cmd_env,
        )

        self._read_task = asyncio.create_task(self._listen_stdout())
        asyncio.create_task(self._listen_stderr())

    async def _connect_http(self) -> None:
        # For HTTP/SSE endpoints, handshake directly via HTTP requests
        self._is_connected = True

    async def _listen_stdout(self) -> None:
        assert self._process and self._process.stdout
        while True:
            line = await self._process.stdout.readline()
            if not line:
                break
            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                msg = json.loads(line_str)
                req_id = msg.get("id")
                if req_id is not None and req_id in self._pending_requests:
                    future = self._pending_requests.pop(req_id)
                    if not future.done():
                        future.set_result(msg)
                else:
                    logger.debug("MCP [%s] notification / unhandled: %s", self.name, line_str)
            except json.JSONDecodeError:
                logger.debug("MCP [%s] non-json line: %s", self.name, line_str)

    async def _listen_stderr(self) -> None:
        assert self._process and self._process.stderr
        while True:
            line = await self._process.stderr.readline()
            if not line:
                break
            logger.debug("MCP [%s stderr]: %s", self.name, line.decode("utf-8").strip())

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        req_id = self._request_id
        self._request_id += 1

        request = JSONRPCRequest(id=req_id, method=method, params=params)

        if self.is_stdio:
            if not self._process or not self._process.stdin:
                raise RuntimeError(f"MCP server '{self.name}' stdio process is not running.")

            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._pending_requests[req_id] = future

            data = (request.model_dump_json() + "\n").encode("utf-8")
            self._process.stdin.write(data)
            await self._process.stdin.drain()

            try:
                raw_resp = await asyncio.wait_for(future, timeout=30.0)
            except asyncio.TimeoutError:
                self._pending_requests.pop(req_id, None)
                raise TimeoutError(f"MCP '{self.name}' timed out waiting for response to '{method}'")

            if "error" in raw_resp and raw_resp["error"]:
                err = raw_resp["error"]
                raise RuntimeError(f"MCP Error ({err.get('code')}): {err.get('message')}")

            return raw_resp.get("result")
        else:
            # HTTP POST
            assert self.url
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.url, json=request.model_dump())
                resp.raise_for_status()
                data = resp.json()
                if "error" in data and data["error"]:
                    err = data["error"]
                    raise RuntimeError(f"MCP Error ({err.get('code')}): {err.get('message')}")
                return data.get("result")

    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        notif = JSONRPCNotification(method=method, params=params)
        if self.is_stdio and self._process and self._process.stdin:
            data = (notif.model_dump_json() + "\n").encode("utf-8")
            self._process.stdin.write(data)
            await self._process.stdin.drain()

    async def _initialize(self) -> None:
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": False},
                "sampling": {},
            },
            "clientInfo": {
                "name": "evren-agent",
                "version": "0.1.0",
            },
        }
        res = await self._send_request("initialize", params)
        self._server_info = res or {}
        await self._send_notification("notifications/initialized")
        logger.info("Initialized MCP server '%s': %s", self.name, self._server_info.get("serverInfo"))

    async def list_tools(self) -> List[MCPToolSchema]:
        """Query tools available from this MCP server."""
        res = await self._send_request("tools/list", {})
        raw_tools = res.get("tools", []) if isinstance(res, dict) else []
        tools = []
        for t in raw_tools:
            tools.append(
                MCPToolSchema(
                    name=t.get("name", ""),
                    description=t.get("description", ""),
                    inputSchema=t.get("inputSchema", {"type": "object"}),
                )
            )
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> MCPCallToolResult:
        """Execute a tool on this MCP server."""
        res = await self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        if not isinstance(res, dict):
            return MCPCallToolResult(content=[MCPContentItem(type="text", text=str(res))])

        content_items = []
        for c in res.get("content", []):
            content_items.append(
                MCPContentItem(
                    type=c.get("type", "text"),
                    text=c.get("text"),
                    data=c.get("data"),
                    mimeType=c.get("mimeType"),
                )
            )

        return MCPCallToolResult(
            content=content_items,
            isError=res.get("isError", False),
        )

    async def disconnect(self) -> None:
        """Shutdown subprocess and clean up."""
        self._is_connected = False
        if self._read_task:
            self._read_task.cancel()
        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=3.0)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
        logger.info("Disconnected MCP server '%s'", self.name)
