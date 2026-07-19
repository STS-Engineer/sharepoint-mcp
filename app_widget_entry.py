from __future__ import annotations

from app import app
from server import mcp
from widget_sdk import register_widget

register_widget(mcp)

__all__ = ["app"]
