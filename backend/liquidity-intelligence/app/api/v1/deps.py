"""
FastAPI dependency injection.
Provides DB client, current user (Firebase-verified), and RBAC helpers.
"""
from __future__ import annotations

from typing import Annotated

import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, Header, HTTPException, Request, status
from prisma import Prisma

from app.core.config import get_settings
from app.db.session import get_db
from app.db.repositories.prisma_repositories import PrismaUserRepository
from app.domain.entities import User
from app.domain.value_objects import UserRole

_settings = get_settings()
_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    global _firebase_app
    if _firebase_app is None:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": _settings.firebase_project_id,
            "client_email": _settings.firebase_client_email,
            "private_key": _settings.firebase_private_key.replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Prisma = Depends(get_db),
) -> User:
    """
    Verifies Firebase ID token, maps to internal User entity.
    Raises 401 if token is missing/invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.split(" ", 1)[1]

    try:
        app = _get_firebase_app()
        decoded = firebase_auth.verify_id_token(token, app=app)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase token: {exc}",
        )

    uid = decoded.get("uid")
    repo = PrismaUserRepository(db)
    user = await repo.get_by_firebase_uid(uid)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not registered in the system.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated.",
        )
    return user


def require_role(*roles: UserRole):
    """Dependency factory — raises 403 if user doesn't have one of the required roles."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}",
            )
        return current_user
    return _check


def get_request_id(request: Request) -> str:
    return request.state.request_id


# Type aliases for cleaner route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DBClient = Annotated[Prisma, Depends(get_db)]
RequestId = Annotated[str, Depends(get_request_id)]
