from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager

# Compatibility shim used only while importing server.py for its Microsoft Graph
# helper functions. MCP 2.0 no longer exposes mcp.server.fastmcp.
try:
    import mcp.server.fastmcp  # type: ignore # noqa: F401
except ModuleNotFoundError:
    compat = types.ModuleType("mcp.server.fastmcp