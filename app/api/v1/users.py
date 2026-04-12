from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/users")


class UserOut(BaseModel):
    id: int
    email: str
    display_name: str | None = None  # Sprint 10 F9
    preferences: dict[str, Any] = {}


class DisplayNameUpdate(BaseModel):
    display_name: str | None = None


class PreferencesUpdate(BaseModel):
    """Shallow-merge into existing preferences."""
    preferences: dict[str, Any]


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        preferences=user.preferences or {},
    )


@router.patch("/me/display-name", response_model=UserOut)
async def update_display_name(
    body: DisplayNameUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update the user's display name."""
    user.display_name = body.display_name.strip() if body.display_name else None
    await db.commit()
    await db.refresh(user)
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        preferences=user.preferences or {},
    )


@router.patch("/me/preferences", response_model=dict[str, Any])
async def update_preferences(
    body: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Shallow-merge new preferences into existing ones."""
    current = dict(user.preferences or {})
    current.update(body.preferences)
    user.preferences = current
    await db.commit()
    return current
