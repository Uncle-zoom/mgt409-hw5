"""The dashboard's connection to the shop data: the campus-customs MCP server in --admin mode.

Every database read and write the API makes goes through this client. There is no
database code in backend/.
"""
import json
import sys
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from .config import MCP_SERVER_PATH


class ShopError(RuntimeError):
    pass


class ShopClient:
    def __init__(self) -> None:
        transport = StdioTransport(command=sys.executable, args=[str(MCP_SERVER_PATH), "--admin"])
        self._client = Client(transport)

    async def __aenter__(self) -> "ShopClient":
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.__aexit__(*exc)

    async def call(self, tool: str, **arguments: Any) -> dict[str, Any]:
        result = await self._client.call_tool(tool, arguments, raise_on_error=False)
        text = next((c.text for c in result.content if getattr(c, "text", None) is not None), None)
        if result.is_error or text is None:
            raise ShopError(text or f"MCP tool {tool} failed")
        return json.loads(text)
