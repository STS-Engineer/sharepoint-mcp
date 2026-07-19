from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from modern_apps_widget import apps
from modern_upload_page import MODERN_UPLOAD_ROUTES

AZURE_HOST = "sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net"

