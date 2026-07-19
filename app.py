from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import unquote, urlparse

import httpx
import uvicorn
from pydantic import Field
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Mount,