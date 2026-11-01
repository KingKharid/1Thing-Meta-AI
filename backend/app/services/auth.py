"""Admin authentication for the control room and other operator surfaces.

``X-Admin-Key`` must match ``ADMIN_API_KEY``. The check fails closed: an
unset key returns 503 rather than opening the surface to the world, so a
misconfigured deploy is loud instead of silently public.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException


def configured_admin_key() -> str:
    return (os.getenv("ADMIN_API_KEY") or "").strip()


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    expected = configured_admin_key()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_KEY is not configured on this server",
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid admin key")
