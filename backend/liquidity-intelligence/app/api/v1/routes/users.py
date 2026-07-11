"""
User management endpoints:
  POST   /users              — register a new user
  GET    /users/me           — get current authenticated user profile
  GET    /users/{user_id}    — get user by ID (admin only)
  PATCH  /users/{user_id}    — update user (admin only)
  GET    /users              — list all users (admin only)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import CurrentUser, DBClient
from app.db.repositories.prisma_repositories import PrismaUserRepository
from app.domain.entities import User
from app.domain.value_objects import UserRole
from app.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest

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


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreateRequest, db: DBClient):
    """
    Register a new user in the system.
    Typically called after Firebase sign-up to create the internal user record.
    No auth required — this is the registration endpoint.
    """
    repo = PrismaUserRepository(db)

    # Check if firebase_uid already exists
    existing = await repo.get_by_firebase_uid(body.firebase_uid)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this firebase_uid already exists.",
        )

    user = User(
        id=str(uuid.uuid4()),
        firebase_uid=body.firebase_uid,
        phone=body.phone,
        name=body.name,
        role=UserRole(body.role),
        region=body.region,
        area=body.area,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    await repo.save(user)
    return _to_response(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: CurrentUser):
    """Get the authenticated user's own profile."""
    return _to_response(current_user)


@router.get("", response_model=list[UserResponse])
async def list_users(db: DBClient, current_user: CurrentUser):
    """List all users. Admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can list all users.",
        )
    repo = PrismaUserRepository(db)
    users = await repo.list_all()
    return [_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: DBClient, current_user: CurrentUser):
    """Get a user by ID. Admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view other users.",
        )
    repo = PrismaUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdateRequest,
    db: DBClient,
    current_user: CurrentUser,
):
    """Update a user. Admin only."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update users.",
        )
    repo = PrismaUserRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply partial updates
    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.region is not None:
        user.region = body.region
    if body.area is not None:
        user.area = body.area
    if body.is_active is not None:
        user.is_active = body.is_active

    await repo.save(user)
    return _to_response(user)
