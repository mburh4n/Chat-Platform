"""The backend's side of MCP: connect to the MCP server, list and call its tools.

Every operation opens a short connection (the server is stateless), so there
is no long-lived connection to keep healthy. The chat code is synchronous, so
each async MCP call is run to completion with asyncio.run().
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from app.core.config import settings

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 5
# The tool itself may wait up to ~8 s for the dictionary API
CALL_TIMEOUT_SECONDS = 20


class MCPUnavailableError(Exception):
    """The MCP server could not be reached or failed."""


@dataclass(frozen=True)
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema of the tool's arguments


@dataclass(frozen=True)
class MCPToolResult:
    text: str
    is_error: bool


async def _list_tools_async() -> list[MCPTool]:
    async with streamablehttp_client(settings.mcp_server_url, timeout=CONNECT_TIMEOUT_SECONDS) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()
            return [
                MCPTool(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema,
                )
                for tool in result.tools
            ]


async def _call_tool_async(name: str, arguments: dict[str, Any]) -> MCPToolResult:
    async with streamablehttp_client(settings.mcp_server_url, timeout=CALL_TIMEOUT_SECONDS) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            text = "\n".join(
                block.text for block in result.content if isinstance(block, TextContent)
            )
            return MCPToolResult(text=text or "(the tool returned no text)", is_error=result.isError)


def list_tools() -> list[MCPTool]:
    """Ask the MCP server which tools it offers."""
    try:
        return asyncio.run(_list_tools_async())
    except Exception as exc:  # network errors arrive wrapped in ExceptionGroups
        logger.warning("MCP server unavailable while listing tools: %r", exc)
        raise MCPUnavailableError("The MCP server is not reachable.") from exc


def call_tool(name: str, arguments: dict[str, Any]) -> MCPToolResult:
    """Run one tool on the MCP server and return its text output."""
    logger.info("Calling MCP tool %s with %s", name, arguments)
    try:
        result = asyncio.run(_call_tool_async(name, arguments))
    except Exception as exc:
        logger.warning("MCP tool call %s failed: %r", name, exc)
        raise MCPUnavailableError("The MCP tool call failed.") from exc
    logger.info("MCP tool %s returned (is_error=%s)", name, result.is_error)
    return result
