from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager

# Compatibility shim: server.py only needs the decorator surface to expose its
# Microsoft Graph helper functions. MCP 2.0 removed mcp.server.fastmcp.
try:
    import mcp.server.fastmcp  # type: ignore # noqa: F401
except ModuleNotFoundError:
    compat = types.ModuleType("mcp.server.fastmcp")

    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def