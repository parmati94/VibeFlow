"""Shared FastAPI dependencies."""

from __future__ import annotations

from backend.common.db import get_session  # re-exported for routers

__all__ = ["get_session"]
