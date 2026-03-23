from fastapi import APIRouter, Depends

from app.api.deps_caps import capability_guard
from app.api.deps_rate_limit import rate_limit_guard

from .auth import router as auth_router
from .users import router as users_router
from .devices import router as devices_router
from .pairing import router as pairing_router, legacy_router as pairing_legacy_router
from .telemetry import router as telemetry_router
from .tasks import router as tasks_router
from .variables import router as variables_router
from .entities import router as entities_router
from .events import router as events_router
from .audit import router as audit_router
from .secrets import router as secrets_router
from .config import router as config_router
from .effects import router as effects_router
from .signals import router as signals_router
from .executions import router as executions_router
from .modules import router as modules_router
from .webhooks import router as webhooks_router
from .groups import router as groups_router
from .alerts import router as alerts_router
from .metrics import router as metrics_router
from .orgs import router as orgs_router
from .ota import router as ota_router
from .edge import router as edge_router

router = APIRouter(dependencies=[Depends(capability_guard), Depends(rate_limit_guard)])

router.include_router(auth_router, tags=["auth"])
router.include_router(users_router, tags=["users"])
router.include_router(devices_router, tags=["devices"])
router.include_router(pairing_router)
# Legacy alias for /api/v1/pairing/*
router.include_router(pairing_legacy_router)
router.include_router(telemetry_router, tags=["telemetry"])
router.include_router(tasks_router, tags=["tasks"])
router.include_router(variables_router, tags=["variables"])
router.include_router(entities_router, tags=["entities"])
router.include_router(events_router, tags=["events"])
router.include_router(audit_router, tags=["audit"])
router.include_router(secrets_router, tags=["secrets"])
router.include_router(config_router, tags=["config"])
router.include_router(effects_router, tags=["effects"])
router.include_router(signals_router, tags=["signals"])
router.include_router(executions_router, tags=["executions"])
router.include_router(modules_router, tags=["modules"])
router.include_router(webhooks_router, tags=["webhooks"])
router.include_router(groups_router, tags=["groups"])
router.include_router(alerts_router, tags=["alerts"])
router.include_router(metrics_router, tags=["metrics"])
router.include_router(orgs_router, tags=["orgs"])
router.include_router(ota_router, tags=["ota"])
router.include_router(edge_router, tags=["edge"])
