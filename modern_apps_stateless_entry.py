from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from modern_apps_widget import apps
from modern_upload_page import MODERN_UPLOAD_ROUTES

AZURE_HOST = "sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net"

mcp = MCPServer("AVOCarbon SharePoint MCP", extensions=[apps])
security = TransportSecuritySettings(
    allowed_hosts=[AZURE_HOST, f"{AZURE_HOST}:*", "localhost", "localhost:*"],
    allowed_origins=["https://chatgpt.com", "https://chat.openai.com"],
)

async def health(_):
    return JSONResponse({
        "status": "ok",
        "version": "1.2.0-stateless",
        "mcp_apps": True,
        "stateless_http": True,
        "endpoint": "/mcp",
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
