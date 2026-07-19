from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager

try:
    import mcp.server.fastmcp  # type: ignore # noqa: F401
except ModuleNotFoundError:
    compat = types.ModuleType("mcp.server.fastmcp")

    class FastMCP:
        def __init__(self, *args, **kwargs):
            pass

        def tool(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator

        def run(self, *args, **kwargs):
            return None

    compat.FastMCP = FastMCP
    sys.modules["mcp.server.fastmcp"] = compat

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

security = TransportSecuritySettings(
    allowed_hosts=[AZURE_HOST, f"{AZURE_HOST}:*", "localhost", "localhost:*", "127.0.0.1", "127.0.0.1:*"],
    allowed_origins=["https://chatgpt.com", "https://chat.openai.com"],
)

async def health(_: object) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": "1.1.4-apps-sdk",
        "mcp_apps": True,
        "extension": "io.modelcontextprotocol/ui",
        "widget": "ui://widget/sharepoint-upload-modern.html",
        "browser_upload": "/upload-modern",
        "graph_backend": "legacy-helpers-via-shim",
        "allowed_host": AZURE_HOST,
    })

@asynccontextmanager
async def lifespan(_: Starlette):
    async with mcp.session_manager.run():
        yield

starlette_app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        *MODERN_UPLOAD_ROUTES,
        *UPLOAD_UI_ROUTES,
        Mount("/", app=mcp.streamable_http_app(transport_security=security)),
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
