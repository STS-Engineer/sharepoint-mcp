from __future__ import annotations

import base64
import contextlib
import os
from pathlib import Path
from typing import Annotated, Literal

import httpx
import uvicorn
from pydantic import BaseModel, Field
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from server import GraphError, enc, mcp, out, path_enc, request, upload