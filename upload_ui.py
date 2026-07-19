from __future__ import annotations

import html
import os
from typing import Any, Literal

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse
from starlette.routing import Route

from server import GraphError, enc, out, path_enc, request, upload_bytes

MAX_UPLOAD_BYTES = int(os.getenv("MAX_BROWSER_UPLOAD_MB", "50")) * 1024 * 1024


def _same_name(left: str, right: str) -> bool:
    return " ".join(left.split()).casefold() == "