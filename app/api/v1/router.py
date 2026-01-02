from fastapi import APIRouter, Depends

from app.api.deps_caps import capability_guard

from .auth import router as auth_router
from .users import router as users_router
from .devices import router as devices_router
from .pairing import router as pairing_router
from .telemetry import router as telemetry_router
from .tasks import router as tasks_router
from .variables import router as variables_router
from .entities import router as entities_router
from .events import router as events_router
from .audit import router as audit_router
from .secrets import router as secrets_router
from .config import router as config_router

router = APIRouter(dependencies=[Depends(capability_guard)])

router.include_router(auth_router, tags=["auth"])
router.include_router(users_router, tags=["users"])
router.include_router(devices_router, tags=["devices"])
router.include_router(pairing_router)
# Legacy alias for /api/v1/devices/pairing/*
router.include_router(pairing_router, prefix="/devices")
router.include_router(telemetry_router, tags=["telemetry"])
router.include_router(tasks_router, tags=["tasks"])
router.include_router(variables_router, tags=["variables"])
router.include_router(entities_router, tags=["entities"])
router.include_router(events_router, tags=["events"])
router.include_router(audit_router, tags=["audit"])
router.include_router(secrets_router, tags=["secrets"])
router.include_router(config_router, tags=["config"])

