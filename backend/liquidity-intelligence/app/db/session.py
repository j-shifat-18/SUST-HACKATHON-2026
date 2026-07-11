"""
Prisma client singleton.
Replaces the previous SQLAlchemy engine + session factory.

Usage (FastAPI dependency):
    from app.db.session import get_prisma
    prisma: Prisma = Depends(get_prisma)
"""
from __future__ import annotations

from prisma import Prisma

# Module-level singleton — connected once at startup, disconnected at shutdown.
_prisma: Prisma | None = None


def get_client() -> Prisma:
    """Return the connected Prisma client. Raises if not yet initialised."""
    if _prisma is None:
        raise RuntimeError(
            "Prisma client is not initialised. "
            "Call connect_prisma() during application startup."
        )
    return _prisma


async def connect_prisma() -> Prisma:
    """Create and connect the Prisma client. Call once from lifespan startup."""
    global _prisma
    if _prisma is None:
        _prisma = Prisma()
    if not _prisma.is_connected():
        await _prisma.connect()
    return _prisma


async def disconnect_prisma() -> None:
    """Disconnect the Prisma client. Call once from lifespan shutdown."""
    global _prisma
    if _prisma is not None and _prisma.is_connected():
        await _prisma.disconnect()


async def get_db() -> Prisma:  # type: ignore[return]
    """
    FastAPI dependency — yields the connected Prisma client.
    The client is a singleton; no per-request lifecycle needed.
    """
    yield get_client()
