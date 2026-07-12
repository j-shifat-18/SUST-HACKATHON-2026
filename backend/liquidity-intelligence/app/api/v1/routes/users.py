"""
User registration and lookup endpoints.
GET  /api/v1/users?phone=... — lookup user by phone
POST /api/v1/users          — register a new user
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from prisma import Prisma

from app.api.v1.deps import get_db
from app.db.repositories.prisma_repositories import PrismaUserRepository
from app.domain.entities import User
from app.domain.value_objects import UserRole
from app.schemas.users import UserCreateRequest, UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/users", tags=["Users"])


def _to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        firebase_uid=user.firebase_uid,
        phone=user.phone,
        name=user.name,
        role=user.role.value,
        region=user.region,
        area=user.area,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.get("", response_model=list[UserResponse])
async def list_users_by_phone(
    phone: Optional[str] = Query(default=None),
    db: Prisma = Depends(get_db),
):
    """
    Lookup users by phone number. Returns matching users as a list.
    No auth required — used during login flow before token is available.
    """
    if not phone:
        return []

    user_repo = PrismaUserRepository(db)

    # Try exact match first via Prisma
    try:
        rows = await db.user.find_many(where={"phone": phone})
        if rows:
            return [_to_response(
                User(
                    id=r.id,
                    firebase_uid=r.firebaseUid,
                    phone=r.phone,
                    name=r.name,
                    role=UserRole(r.role),
                    region=r.region,
                    area=r.area,
                    is_active=r.isActive,
                    created_at=r.createdAt,
                )
            ) for r in rows]
    except Exception as e:
        logger.warning("user_lookup_error", error=str(e))

    # Fallback: try matching last 10 digits
    phone_digits = phone.replace("+", "").replace("-", "").replace(" ", "")
    if len(phone_digits) >= 10:
        last10 = phone_digits[-10:]
        try:
            all_users = await db.user.find_many(where={"isActive": True})
            matches = []
            for r in all_users:
                stored_digits = r.phone.replace("+", "").replace("-", "").replace(" ", "")
                if len(stored_digits) >= 10 and stored_digits[-10:] == last10:
                    matches.append(_to_response(
                        User(
                            id=r.id,
                            firebase_uid=r.firebaseUid,
                            phone=r.phone,
                            name=r.name,
                            role=UserRole(r.role),
                            region=r.region,
                            area=r.area,
                            is_active=r.isActive,
                            created_at=r.createdAt,
                        )
                    ))
            return matches
        except Exception as e:
            logger.warning("user_fuzzy_lookup_error", error=str(e))

    return []


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: Request,
    db: Prisma = Depends(get_db),
):
    """
    Register a new user. Extracts firebase_uid from the Authorization token.
    Body: { phone, name, region, area }
    """
    # Parse body manually to handle flexible frontend payload
    body = await request.json()

    phone = body.get("phone", "")
    name = body.get("name", "")
    region = body.get("region")
    area = body.get("area")

    if not phone or not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="phone and name are required",
        )

    # Extract firebase_uid from token if available
    firebase_uid = ""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            import firebase_admin
            from firebase_admin import auth as firebase_auth

            if not firebase_admin._apps:
                from firebase_admin import credentials
                from app.core.config import get_settings
                settings = get_settings()
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
            logger.warning("token_decode_failed_during_registration", error=str(e))
            # Generate a placeholder UID if token verification fails
            firebase_uid = f"unverified_{uuid.uuid4().hex[:12]}"
    else:
        firebase_uid = f"unverified_{uuid.uuid4().hex[:12]}"

    # Check if user already exists with this phone
    try:
        existing = await db.user.find_many(where={"phone": phone})
        if existing:
            # Return existing user instead of error
            r = existing[0]
            return _to_response(
                User(
                    id=r.id,
                    firebase_uid=r.firebaseUid,
                    phone=r.phone,
                    name=r.name,
                    role=UserRole(r.role),
                    region=r.region,
                    area=r.area,
                    is_active=r.isActive,
                    created_at=r.createdAt,
                )
            )
    except Exception:
        pass

    # Create new user
    user = User(
        id=str(uuid.uuid4()),
        firebase_uid=firebase_uid,
        phone=phone,
        name=name,
        role=UserRole.OPERATOR,
        region=region,
        area=area,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    user_repo = PrismaUserRepository(db)
    await user_repo.save(user)

    return _to_response(user)
