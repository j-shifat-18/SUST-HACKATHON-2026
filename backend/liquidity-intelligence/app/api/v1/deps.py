"""
FastAPI dependencies for authentication, authorization, and DB access.
"""
from __future__ import annotations

from typing import Optional

import structlog
from fastapi import Depends, Header, HTTPException, status
from prisma import Prisma

from app.core.config import get_settings
from app.db.session import get_client
from app.db.repositories.prisma_repositories import PrismaUserRepository
from app.domain.entities import User
from app.domain.value_objects import UserRole

logger = structlog.get_logger(__name__)
settings = get_settings()


def get_db() -> Prisma:
    """Return the connected Prisma client singleton."""
    return get_client()


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Prisma = Depends(get_db),
) -> User:
    """
    Verify Firebase ID token and resolve to an internal User entity.
    In development mode, allows X-Dev-User-Id header as a bypass for testing.
    """
    # Dev bypass: allow direct user ID for local testing
    if settings.app_env == "development" and authorization and authorization.startswith("Bearer dev_"):
        dev_user_id = authorization.removeprefix("Bearer dev_").strip()
        user_repo = PrismaUserRepository(db)
        user = await user_repo.get_by_id(dev_user_id)
        if user:
            return user

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # --- Firebase token verification ---
    try:
        import firebase_admin
        from firebase_admin import auth as firebase_auth

        # Initialize Firebase app if not already done
        if not firebase_admin._apps:
            from firebase_admin import credentials
            cred = credentials.Certificate({
                "type": "service_account",
                "project_id": settings.firebase_project_id,
                "client_email": settings.firebase_client_email,
                "private_key": settings.firebase_private_key.replace("\\n", "\n"),
                "token_uri": "https://oauth2.googleapis.com/token",
            })
            firebase_admin.initialize_app(cred)

        decoded = firebase_auth.verify_id_token(token)
        firebase_uid = decoded["uid"]
    except Exception as e:
        logger.warning("firebase_auth_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Resolve to internal user
    user_repo = PrismaUserRepository(db)
    user = await user_repo.get_by_firebase_uid(firebase_uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not registered in the system",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return user


def require_role(*roles: UserRole):
    """Dependency factory — ensures the authenticated user has one of the allowed roles."""

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[r.value for r in roles]}",
            )
        return user

    return _check
