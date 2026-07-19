from __future__ import annotations

from app import app
from server import mcp
from widget_prefill import register_prefill_widget

register_prefill_widget(mcp)

__all__ = ["app"]
