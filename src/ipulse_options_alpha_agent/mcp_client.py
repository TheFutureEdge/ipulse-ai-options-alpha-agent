"""Small asynchronous client for Alpaca's official MCP server."""

from __future__ import annotations

import json
import os
import shlex
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class AlpacaMcpClient:
    """Connect to an externally configured Alpaca MCP stdio command."""

    def __init__(self, command: str | None = None, args: list[str] | None = None) -> None:
        """Load a command without embedding credentials in the application."""

        self.command = command or os.environ.get("ALPACA_MCP_COMMAND", "uvx")
        configured_args = os.environ.get("ALPACA_MCP_ARGS", "alpaca-mcp-server")
        self.args = args if args is not None else shlex.split(configured_args)
        self._stack: AsyncExitStack | None = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "AlpacaMcpClient":
        """Start the MCP process and initialize the protocol session."""

        self._stack = AsyncExitStack()
        parameters = StdioServerParameters(command=self.command, args=self.args)
        streams = await self._stack.enter_async_context(stdio_client(parameters))
        self._session = await self._stack.enter_async_context(ClientSession(*streams))
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        """Close the MCP session and its child process."""

        if self._stack is not None:
            await self._stack.aclose()
        self._session = None
        self._stack = None

    def _require_session(self) -> ClientSession:
        """Return the initialized session or fail with a clear error."""

        if self._session is None:
            raise RuntimeError("Alpaca MCP client is not connected.")
        return self._session

    async def list_tool_names(self) -> list[str]:
        """Return tool names advertised by the configured server."""

        result = await self._require_session().list_tools()
        return sorted(tool.name for tool in result.tools)

    async def call_json_value(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any] | list[Any]:
        """Call one MCP tool and decode its first JSON object or array response."""

        result = await self._require_session().call_tool(tool_name, arguments)
        is_error = getattr(result, "is_error", getattr(result, "isError", False))
        if is_error:
            raise RuntimeError(f"Alpaca MCP tool failed: {tool_name}")
        for item in result.content:
            if getattr(item, "type", None) != "text":
                continue
            try:
                payload = json.loads(item.text)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, (dict, list)):
                return payload
        raise RuntimeError(f"Alpaca MCP tool returned no JSON value: {tool_name}")

    async def call_json(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call one MCP tool and require a JSON object response."""

        payload = await self.call_json_value(tool_name, arguments)
        if isinstance(payload, dict):
            return payload
        raise RuntimeError(f"Alpaca MCP tool returned a JSON array: {tool_name}")
