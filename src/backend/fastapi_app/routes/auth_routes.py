from __future__ import annotations

from fastapi import APIRouter
from fastapi_users.schemas import BaseUser, BaseUserCreate, BaseUserUpdate
from pydantic import EmailStr

from fastapi_app.auth.auth_config import auth_backend, fastapi_users
from fastapi_app.auth.auth_models import User


class UserRead(BaseUser):
    display_name: str | None = None
    is_admin: bool = False


class UserCreate(BaseUserCreate):
    display_name: str | None = None


class UserUpdate(BaseUserUpdate):
    display_name: str | None = None


router = APIRouter()

# /auth/login, /auth/logout
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)

# /auth/register
router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# /auth/me, /auth/me (PATCH)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/auth/users",
    tags=["auth"],
)
