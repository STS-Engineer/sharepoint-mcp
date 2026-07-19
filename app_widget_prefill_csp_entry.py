from __future__ import annotations

from app import app
from server import mcp
from widget_prefill_csp import register_prefill_csp_widget

register_prefill_csp_widget(mcp)

__all__ = ["app"]
