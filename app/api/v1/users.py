from fastapi import APIRouter, Depends
from app.api.deps_auth import get_current_user
from app.db.models.user import User

router = APIRouter(prefix="/users")

@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email}
