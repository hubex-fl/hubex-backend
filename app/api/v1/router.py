from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .devices import router as devices_router
from .pairing import router as pairing_router

router = APIRouter()

router.include_router(auth_router, tags=["auth"])
router.include_router(users_router, tags=["users"])
router.include_router(devices_router, tags=["devices"])
router.include_router(pairing_router, tags=["pairing"])
