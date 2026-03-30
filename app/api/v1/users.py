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
    preferences: dict[str, Any] = {}


class PreferencesUpdate(BaseModel):
    """Shallow-merge into existing preferences."""
    preferences: dict[str, Any]


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(
        id=user.id,
        email=user.email,
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
