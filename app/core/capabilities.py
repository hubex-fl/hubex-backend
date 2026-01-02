import os
import logging
from typing import Iterable

logger = logging.getLogger("uvicorn.error")

# Central registry (single source of truth). Append-only.
CAPABILITY_REGISTRY: set[str] = {
    "cap.admin",
    "config.write",
    "config.read",
    "secrets.write",
    "secrets.read",
    "audit.read",
    "audit.write",
    "mic.admin",
    "vars.read",
    "vars.write",
    "vars.ack",
    "devices.read",
    "devices.write",
    "pairing.start",
    "pairing.confirm",
    "devices.hello",
    "telemetry.emit",
    "telemetry.read",
    "tasks.read",
    "tasks.write",
    "users.read",
    "core.auth.login",
    "core.auth.register",
    "entities.read",
    "events.read",
    "events.emit",
    "events.ack",
    "effects.read",
}

# Route -> capability mapping (method, path_template)
CAPABILITY_MAP: dict[tuple[str, str], list[str]] = {
    ("POST", "/api/v1/auth/register"): ["core.auth.register"],
    ("POST", "/api/v1/auth/login"): ["core.auth.login"],
    ("GET", "/api/v1/users/me"): ["users.read"],
    ("POST", "/api/v1/devices/hello"): ["devices.hello"],
    ("GET", "/api/v1/devices/whoami"): ["devices.read"],
    ("GET", "/api/v1/devices/lookup/{device_uid}"): ["devices.read"],
    ("GET", "/api/v1/devices"): ["devices.read"],
    ("GET", "/api/v1/devices/{device_id}"): ["devices.read"],
    ("GET", "/api/v1/devices/{device_id}/telemetry/recent"): ["telemetry.read"],
    ("GET", "/api/v1/devices/{device_id}/telemetry"): ["telemetry.read"],
    ("POST", "/api/v1/devices/{device_id}/tasks"): ["tasks.write"],
    ("GET", "/api/v1/devices/{device_id}/tasks"): ["tasks.read"],
    ("GET", "/api/v1/devices/{device_id}/current-task"): ["tasks.read"],
    ("GET", "/api/v1/devices/{device_id}/task-history"): ["tasks.read"],
    ("POST", "/api/v1/devices/{device_id}/tasks/{task_id}/cancel"): ["tasks.write"],
    ("POST", "/api/v1/pairing/start"): ["pairing.start"],
    ("POST", "/api/v1/pairing/confirm"): ["pairing.confirm"],
    ("POST", "/api/v1/devices/pairing/start"): ["pairing.start"],
    ("POST", "/api/v1/devices/pairing/confirm"): ["pairing.confirm"],
    ("POST", "/api/v1/telemetry"): ["telemetry.emit"],
    ("GET", "/api/v1/telemetry/recent"): ["telemetry.read"],
    ("POST", "/api/v1/tasks/context/heartbeat"): ["tasks.write"],
    ("POST", "/api/v1/tasks/poll"): ["tasks.read"],
    ("POST", "/api/v1/tasks/{task_id}/complete"): ["tasks.write"],
    ("POST", "/api/v1/tasks/{task_id}/renew"): ["tasks.write"],
    ("GET", "/api/v1/variables/definitions"): ["vars.read"],
    ("GET", "/api/v1/variables/defs"): ["vars.read"],
    ("POST", "/api/v1/variables/definitions"): ["vars.write"],
    ("POST", "/api/v1/variables/defs"): ["vars.write"],
    ("GET", "/api/v1/variables/value"): ["vars.read"],
    ("PUT", "/api/v1/variables/value"): ["vars.write"],
    ("POST", "/api/v1/variables/set"): ["vars.write"],
    ("GET", "/api/v1/variables/device/{device_uid}"): ["vars.read"],
    ("GET", "/api/v1/variables/effective"): ["vars.read"],
    ("GET", "/api/v1/variables/snapshot"): ["vars.read"],
    ("POST", "/api/v1/variables/applied"): ["vars.ack"],
    ("POST", "/api/v1/variables/ack"): ["vars.ack"],
    ("GET", "/api/v1/variables/applied"): ["vars.read"],
    ("GET", "/api/v1/variables/audit"): ["vars.read"],
    ("GET", "/api/v1/variables/effects"): ["vars.read"],
    ("GET", "/api/v1/variables/effects/{effect_id}"): ["vars.read"],
    ("POST", "/api/v1/variables/effects/run-once"): ["vars.write"],
    ("GET", "/api/v1/entities"): ["entities.read"],
    ("GET", "/api/v1/entities/{entity_id}"): ["entities.read"],
    ("GET", "/api/v1/entities/{entity_id}/devices"): ["entities.read"],
    ("GET", "/api/v1/events"): ["events.read"],
    ("POST", "/api/v1/events/ack"): ["events.ack"],
    ("GET", "/api/v1/audit"): ["audit.read"],
    ("GET", "/api/v1/audit/{entry_id}"): ["audit.read"],
    ("GET", "/api/v1/secrets"): ["secrets.read"],
    ("GET", "/api/v1/secrets/{secret_id}"): ["secrets.read"],
    ("GET", "/api/v1/config"): ["config.read"],
    ("GET", "/api/v1/config/{config_id}"): ["config.read"],
    ("GET", "/api/v1/effects"): ["effects.read"],
    ("GET", "/api/v1/effects/{effect_id}"): ["effects.read"],
}

# Public whitelist (auth-free, minimal, static).
PUBLIC_WHITELIST: set[tuple[str, str]] = {
    ("POST", "/api/v1/devices/hello"),
    ("POST", "/api/v1/pairing/confirm"),
    ("POST", "/api/v1/devices/pairing/confirm"),
}

def enforcement_enabled() -> bool:
    return os.getenv("HUBEX_CAPS_ENFORCE", "0") == "1"

def validate_caps(caps: Iterable[str]) -> list[str]:
    unknown = [cap for cap in caps if cap not in CAPABILITY_REGISTRY]
    return unknown

def resolve_required_caps(method: str, path: str) -> list[str] | None:
    return CAPABILITY_MAP.get((method.upper(), path))

def is_public_route(method: str, path: str) -> bool:
    return (method.upper(), path) in PUBLIC_WHITELIST
