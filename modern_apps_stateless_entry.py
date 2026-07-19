from __future__ import annotations

import sys
import types
from contextlib import asynccontextmanager
from typing import Any

_CAPTURED: list[tuple[str, object]] = []

class LegacyFastMCP:
    def __init__(self, *args, **kwargs):
        pass

    def tool(self, *args, **kwargs):
        explicit_name = kwargs.get("name")
        def decorator(fn):
            _