from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any, Literal

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from server import GraphError, enc, mcp, out, path_enc, request, upload_bytes

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv