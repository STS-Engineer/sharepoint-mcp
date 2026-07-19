from __future__ import annotations

import os
from typing import Literal

from mcp.server.apps import Apps, ResourceCsp

WIDGET_URI = "ui://widget/sharepoint-upload-modern.html"
BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://sharepoint-mcp-hqhfgeauhufbe5cv.francecentral-01.azurewebsites.net").rstrip("/")
apps = Apps()

HTML = f"""<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><style>
*{{box-sizing:border-box}}body{{margin:0;padding:14px;font-family:Arial,sans-serif;background:#f4f6f9;color