"""
Pydantic schemas for User endpoints.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    firebase_uid: str
    phone: str = Field(..., min_length=6, max_length=20)
    name: str
    role: str = "operator"
    region: Optional[str] = None
    area: Optional[str] = None


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    area: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    firebase_uid: str
    phone: str
    name: str
    role: str
    region: Optional[str] = None
    area: Optional[str] = None
    is_active: bool
    created_at: datetime
