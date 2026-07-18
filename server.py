from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

GRAPH_BASE = os.getenv("GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").rstrip("/")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
STATIC_ACCESS_TOKEN = os.getenv("GRAPH_ACCESS_TOKEN", "")
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS