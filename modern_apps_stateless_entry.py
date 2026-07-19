from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager

_CAPTURED: list[tuple[str, object]] = []

class LegacyFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self, *args, **kwargs):
        explicit_name = kwargs.get("name")
        def decorator(fn):
            _CAPTURED.append((explicit_name or fn.__name__, fn))
            return fn
        return decorator

    def run(self, *args, **kwargs):
        return None

compat = types.ModuleType("mcp.server.fastmcp")
compat.FastMCP = LegacyFastMCP
sys.modules["mcp.server.fastmcp"] = compat

import server as legacy

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from modern_apps_widget import apps
from modern_upload_page import MODERN_UPLOAD_ROUTES
from upload_ui import UPLOAD_UI_ROUTES

AZURE_HOST = "sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net"

mcp = MCPServer("AVOCarbon SharePoint MCP", extensions=[apps])
for tool_name, tool_fn in _CAPTURED:
    mcp.add_tool(tool_fn, name=tool_name)

security = TransportSecuritySettings(
    allowed_hosts=[AZURE_HOST, f"{AZURE_HOST}:*", "localhost", "localhost:*"],
    allowed_origins=["https://chatgpt.com", "https://chat.openai.com"],
)

async def health(_):
    return JSONResponse({
        "status": "ok",
        "version": "1.3.0-complete",
        "mcp_apps": True,
        "stateless_http": True,
        "endpoint": "/mcp",
        "legacy_tools": len(_CAPTURED),
        "total_tools": len(_CAPTURED) + 1,
    })

@asynccontextmanager
async def lifespan(_):
    async with mcp.session_manager.run():
        yield

mcp_app = mcp.streamable_http_app(
    transport_security=security,
    stateless_http=True,
    json_response=True,
)

starlette_app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        *MODERN_UPLOAD_ROUTES,
        *UPLOAD_UI_ROUTES,
        Mount("/", app=mcp_app),
    ],
    lifespan=lifespan,
)

app = CORSMiddleware(
    app=starlette_app,
    allow_origins=["https://chatgpt.com", "https://chat.openai.com"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
    allow_credentials=False,
)
