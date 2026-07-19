from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from modern_apps_widget import apps
from modern_upload_page import MODERN_UPLOAD_ROUTES
from upload_ui import UPLOAD_UI_ROUTES

mcp = MCPServer("AVOCarbon SharePoint MCP", extensions=[apps])

async def health(_: object) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "version": "1.1.0-apps-sdk",
        "mcp_apps": True,
        "extension": "io.modelcontextprotocol/ui",
        "widget": "ui://widget/sharepoint-upload-modern.html",
        "browser_upload": "/upload-modern",
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
        Mount("/", app=mcp.streamable_http_app()),
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
