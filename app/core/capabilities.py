import logging
import os
from typing import Iterable

from app.core.config import settings

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
    "devices.token.reissue",
    "devices.unclaim",
    "devices.purge",
    "pairing.start",
    "pairing.claim",
    "pairing.confirm",
    "pairing.status",
    "modules.read",
    "modules.write",
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
    "providers.read",
    "providers.write",
    "signals.read",
    "signals.ingest",
    "executions.read",
    "executions.write",
    "webhooks.read",
    "webhooks.write",
    "entities.write",
    "groups.read",
    "groups.write",
    "alerts.read",
    "alerts.write",
    "metrics.read",
    "org.read",
    "org.write",
    "org.admin",
    "org.members.read",
    "org.members.write",
    "ota.read",
    "ota.write",
    "ota.admin",
    "edge.config",
    "automations.read",
    "automations.write",
    "types.read",
    "types.write",
    "dashboards.read",
    "dashboards.write",
    "notifications.read",
    "notifications.write",
    "mcp.read",
    "mcp.execute",
    "apikeys.read",
    "apikeys.write",
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
    ("PATCH", "/api/v1/devices/{device_id}/type"): ["devices.write"],
    ("PATCH", "/api/v1/devices/{device_id}"): ["devices.write"],
    ("POST", "/api/v1/devices/{device_id}/token/reissue"): ["devices.token.reissue"],
    ("POST", "/api/v1/devices/{device_id}/unclaim"): ["devices.unclaim"],
    ("POST", "/api/v1/devices/{device_id}/purge"): ["devices.purge"],
    ("POST", "/api/v1/devices/purge"): ["devices.purge"],
    ("POST", "/api/v1/devices/purge-bulk"): ["devices.purge"],
    ("POST", "/api/v1/devices/pairing/hello"): ["pairing.start"],
    ("POST", "/api/v1/pairing/hello"): ["pairing.start"],
    ("POST", "/api/v1/pairing/start"): ["pairing.start"],
    ("POST", "/api/v1/pairing/claim"): ["pairing.claim"],
    ("POST", "/api/v1/pairing/confirm"): ["pairing.confirm"],
    ("GET", "/api/v1/pairing/status"): ["pairing.status"],
    ("POST", "/api/v1/devices/pairing/start"): ["pairing.start"],
    ("POST", "/api/v1/devices/pairing/claim"): ["pairing.claim"],
    ("POST", "/api/v1/devices/pairing/confirm"): ["pairing.confirm"],
    ("GET", "/api/v1/devices/pairing/status"): ["pairing.status"],
    ("GET", "/api/v1/devices/pairing/{pairing_code}/qr"): ["pairing.status"],
    ("GET", "/api/v1/modules"): ["modules.read"],
    ("GET", "/api/v1/modules/{key}"): ["modules.read"],
    ("POST", "/api/v1/modules/{key}/enable"): ["modules.write"],
    ("POST", "/api/v1/modules/{key}/disable"): ["modules.write"],
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
    ("PATCH", "/api/v1/variables/definitions/{key}"): ["vars.write"],
    ("DELETE", "/api/v1/variables/definitions/{key}"): ["vars.write"],
    ("GET", "/api/v1/variables/history"): ["vars.read"],
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
    ("GET", "/api/v1/variables/history/export"): ["vars.read"],
    ("POST", "/api/v1/variables/effects/run-once"): ["vars.write"],
    ("GET", "/api/v1/entities"): ["entities.read"],
    ("GET", "/api/v1/entities/{entity_id}"): ["entities.read"],
    ("GET", "/api/v1/entities/{entity_id}/devices"): ["entities.read"],
    ("GET", "/api/v1/events"): ["events.read"],
    ("GET", "/api/v1/events/{event_id}"): ["events.read"],
    ("POST", "/api/v1/events/ack"): ["events.ack"],
    ("POST", "/api/v1/events/emit"): ["events.emit"],
    ("GET", "/api/v1/events/export"): ["events.read"],
    ("GET", "/api/v1/audit"): ["audit.read"],
    ("GET", "/api/v1/audit/{entry_id}"): ["audit.read"],
    ("GET", "/api/v1/audit/export/download"): ["audit.read"],
    ("GET", "/api/v1/secrets"): ["secrets.read"],
    ("GET", "/api/v1/secrets/{secret_id}"): ["secrets.read"],
    ("GET", "/api/v1/config"): ["config.read"],
    ("GET", "/api/v1/config/{config_id}"): ["config.read"],
    ("GET", "/api/v1/effects"): ["effects.read"],
    ("GET", "/api/v1/effects/{effect_id}"): ["effects.read"],
    ("GET", "/api/v1/signals"): ["signals.read"],
    ("GET", "/api/v1/executions/runs"): ["executions.read"],
    ("POST", "/api/v1/executions/definitions"): ["executions.write"],
    ("POST", "/api/v1/executions/runs"): ["executions.write"],
    ("POST", "/api/v1/executions/runs/{run_id}/finalize"): ["executions.write"],
    ("POST", "/api/v1/executions/runs/{run_id}/claim"): ["executions.write"],
    ("POST", "/api/v1/executions/runs/{run_id}/lease"): ["executions.write"],
    ("POST", "/api/v1/executions/runs/{run_id}/release"): ["executions.write"],
    ("POST", "/api/v1/executions/runs/claim-next"): ["executions.write"],
    ("POST", "/api/v1/executions/workers/heartbeat"): ["executions.write"],
    ("POST", "/api/v1/executions/workers/{worker_id}/definitions"): ["executions.write"],
    ("GET", "/api/v1/executions/workers"): ["executions.read"],
    ("GET", "/api/v1/executions/workers/{worker_id}/definitions"): ["executions.read"],
    ("GET", "/api/v1/executions/definitions/{definition_key}/workers"): ["executions.read"],
    ("GET", "/api/v1/executions/definitions"): ["executions.read"],
    ("GET", "/api/v1/executions/runs/{run_id}"): ["executions.read"],
    ("GET", "/api/v1/executions/definitions/{definition_key}"): ["executions.read"],
    ("POST", "/api/v1/webhooks"): ["webhooks.write"],
    ("GET", "/api/v1/webhooks"): ["webhooks.read"],
    ("GET", "/api/v1/webhooks/{webhook_id}"): ["webhooks.read"],
    ("DELETE", "/api/v1/webhooks/{webhook_id}"): ["webhooks.write"],
    ("GET", "/api/v1/webhooks/{webhook_id}/deliveries"): ["webhooks.read"],
    ("POST", "/api/v1/entities"): ["entities.write"],
    ("PUT", "/api/v1/entities/{entity_id}"): ["entities.write"],
    ("DELETE", "/api/v1/entities/{entity_id}"): ["entities.write"],
    ("POST", "/api/v1/entities/{entity_id}/devices"): ["entities.write"],
    ("DELETE", "/api/v1/entities/{entity_id}/devices/{device_id}"): ["entities.write"],
    ("PUT", "/api/v1/entities/{entity_id}/devices/{device_id}"): ["entities.write"],
    ("POST", "/api/v1/entities/{entity_id}/devices/bulk-bind"): ["entities.write"],
    ("POST", "/api/v1/entities/{entity_id}/devices/bulk-unbind"): ["entities.write"],
    ("GET", "/api/v1/entities/{entity_id}/health"): ["entities.read"],
    ("GET", "/api/v1/groups"): ["groups.read"],
    ("POST", "/api/v1/groups"): ["groups.write"],
    ("GET", "/api/v1/groups/{group_id}/devices"): ["groups.read"],
    ("POST", "/api/v1/alerts/rules"): ["alerts.write"],
    ("GET", "/api/v1/alerts/rules"): ["alerts.read"],
    ("GET", "/api/v1/alerts/rules/{rule_id}"): ["alerts.read"],
    ("PUT", "/api/v1/alerts/rules/{rule_id}"): ["alerts.write"],
    ("DELETE", "/api/v1/alerts/rules/{rule_id}"): ["alerts.write"],
    ("GET", "/api/v1/alerts"): ["alerts.read"],
    ("GET", "/api/v1/alerts/{event_id}"): ["alerts.read"],
    ("POST", "/api/v1/alerts/{event_id}/ack"): ["alerts.write"],
    ("POST", "/api/v1/alerts/{event_id}/resolve"): ["alerts.write"],
    ("GET", "/api/v1/metrics"): [],  # no cap required — device counts are user-scoped
    ("POST", "/api/v1/auth/switch-org"): ["core.auth.login"],
    ("POST", "/api/v1/auth/refresh"): ["core.auth.login"],
    ("GET", "/api/v1/auth/roles"): [],  # public info
    # API Keys
    ("POST", "/api/v1/api-keys"): ["apikeys.write"],
    ("GET", "/api/v1/api-keys"): ["apikeys.read"],
    ("DELETE", "/api/v1/api-keys/{key_id}"): ["apikeys.write"],
    # Sessions (self-service — no cap required)
    ("GET", "/api/v1/auth/sessions"): [],
    ("DELETE", "/api/v1/auth/sessions/{session_id}"): [],
    ("DELETE", "/api/v1/auth/sessions"): [],
    # MFA (self-service — no cap required)
    ("POST", "/api/v1/auth/mfa/totp/setup"): [],
    ("POST", "/api/v1/auth/mfa/totp/confirm"): [],
    ("DELETE", "/api/v1/auth/mfa/totp"): [],
    ("GET", "/api/v1/auth/mfa/status"): [],
    ("POST", "/api/v1/auth/mfa/verify"): [],
    # Export/Import
    ("GET", "/api/v1/export"): ["config.read"],
    ("POST", "/api/v1/export/import"): ["config.write"],
    # Email Templates
    ("GET", "/api/v1/email-templates"): ["config.read"],
    ("POST", "/api/v1/email-templates"): ["config.write"],
    ("PATCH", "/api/v1/email-templates/{template_id}"): ["config.write"],
    ("DELETE", "/api/v1/email-templates/{template_id}"): ["config.write"],
    ("POST", "/api/v1/email-templates/preview"): ["config.read"],
    # Custom API Builder
    ("GET", "/api/v1/custom-api/endpoints"): ["config.read"],
    ("POST", "/api/v1/custom-api/endpoints"): ["config.write"],
    ("GET", "/api/v1/custom-api/endpoints/{endpoint_id}"): ["config.read"],
    ("PUT", "/api/v1/custom-api/endpoints/{endpoint_id}"): ["config.write"],
    ("DELETE", "/api/v1/custom-api/endpoints/{endpoint_id}"): ["config.write"],
    ("POST", "/api/v1/custom-api/endpoints/{endpoint_id}/regenerate-key"): ["config.write"],
    ("GET", "/api/v1/custom-api/endpoints/{endpoint_id}/preview"): ["config.read"],
    ("GET", "/api/v1/custom-api/traffic"): ["config.read"],
    # Custom API runtime handler (uses its own per-endpoint auth)
    ("GET", "/api/v1/custom-api/call/{path:path}"): [],
    ("POST", "/api/v1/custom-api/call/{path:path}"): [],
    # Observability
    ("GET", "/api/v1/observability/traces"): ["events.read"],
    ("GET", "/api/v1/observability/incidents"): ["alerts.read"],
    ("GET", "/api/v1/observability/support-bundle"): ["config.read"],
    ("GET", "/api/v1/observability/anomalies"): ["vars.read"],
    # Reports
    ("GET", "/api/v1/reports/templates"): ["config.read"],
    ("POST", "/api/v1/reports/templates"): ["config.write"],
    ("DELETE", "/api/v1/reports/templates/{template_id}"): ["config.write"],
    ("POST", "/api/v1/reports/generate/{template_id}"): ["config.write"],
    ("GET", "/api/v1/reports/history"): ["config.read"],
    ("GET", "/api/v1/reports/download/{report_id}"): ["config.read"],
    # Plugins
    ("GET", "/api/v1/plugins"): ["modules.read"],
    ("POST", "/api/v1/plugins"): ["modules.write"],
    ("GET", "/api/v1/plugins/{plugin_key}"): ["modules.read"],
    ("PATCH", "/api/v1/plugins/{plugin_key}"): ["modules.write"],
    ("DELETE", "/api/v1/plugins/{plugin_key}"): ["modules.write"],
    ("POST", "/api/v1/plugins/{plugin_key}/execute"): ["modules.write"],
    ("POST", "/api/v1/orgs"): ["org.write"],
    ("GET", "/api/v1/orgs"): ["org.read"],
    ("GET", "/api/v1/orgs/{org_id}"): ["org.read"],
    ("PUT", "/api/v1/orgs/{org_id}"): ["org.write"],
    ("DELETE", "/api/v1/orgs/{org_id}"): ["org.admin"],
    ("GET", "/api/v1/orgs/{org_id}/members"): ["org.members.read"],
    ("POST", "/api/v1/orgs/{org_id}/members"): ["org.members.write"],
    ("PUT", "/api/v1/orgs/{org_id}/members/{target_user_id}"): ["org.members.write"],
    ("DELETE", "/api/v1/orgs/{org_id}/members/{target_user_id}"): ["org.members.write"],
    ("GET", "/api/v1/orgs/{org_id}/activity"): ["org.read"],
    ("GET", "/api/v1/orgs/{org_id}/tenants"): ["org.read"],
    ("POST", "/api/v1/orgs/{org_id}/tenants"): ["org.admin"],
    ("DELETE", "/api/v1/orgs/{org_id}/tenants/{node_id}"): ["org.admin"],
    # Branding
    ("GET", "/api/v1/orgs/{org_id}/branding"): ["org.read"],
    ("PUT", "/api/v1/orgs/{org_id}/branding"): ["org.write"],
    # Hardware
    ("GET", "/api/v1/hardware/boards"): ["devices.read"],
    ("GET", "/api/v1/hardware/boards/{board_id}"): ["devices.read"],
    ("GET", "/api/v1/hardware/shields"): ["devices.read"],
    ("GET", "/api/v1/hardware/devices/{device_id}/pins"): ["devices.read"],
    ("PUT", "/api/v1/hardware/devices/{device_id}/pins"): ["devices.write"],
    # Components
    ("GET", "/api/v1/components"): ["devices.read"],
    ("GET", "/api/v1/components/{component_key}"): ["devices.read"],
    # Code Generator
    ("POST", "/api/v1/codegen/generate"): ["devices.write"],
    ("GET", "/api/v1/codegen/preview/{device_id}"): ["devices.read"],
    # OTA Firmware
    ("POST", "/api/v1/ota/firmware"): ["ota.write"],
    ("GET", "/api/v1/ota/firmware"): ["ota.read"],
    ("GET", "/api/v1/ota/firmware/{firmware_id}"): ["ota.read"],
    ("PUT", "/api/v1/ota/firmware/{firmware_id}"): ["ota.write"],
    ("DELETE", "/api/v1/ota/firmware/{firmware_id}"): ["ota.admin"],
    # OTA Rollouts
    ("POST", "/api/v1/ota/rollouts"): ["ota.write"],
    ("GET", "/api/v1/ota/rollouts"): ["ota.read"],
    ("GET", "/api/v1/ota/rollouts/{rollout_id}"): ["ota.read"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/start"): ["ota.write"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/pause"): ["ota.write"],
    ("POST", "/api/v1/ota/rollouts/{rollout_id}/cancel"): ["ota.write"],
    # OTA device-facing
    ("GET", "/api/v1/ota/check"): ["edge.config"],
    ("GET", "/api/v1/ota/status"): ["edge.config"],
    ("POST", "/api/v1/ota/status/{rollout_id}/ack"): ["edge.config"],
    # Edge
    ("GET", "/api/v1/edge/config"): ["edge.config"],
    ("POST", "/api/v1/edge/heartbeat"): ["edge.config"],
    # Automations
    ("GET", "/api/v1/automations"): ["automations.read"],
    ("POST", "/api/v1/automations"): ["automations.write"],
    ("GET", "/api/v1/automations/{rule_id}"): ["automations.read"],
    ("PATCH", "/api/v1/automations/{rule_id}"): ["automations.write"],
    ("DELETE", "/api/v1/automations/{rule_id}"): ["automations.write"],
    ("POST", "/api/v1/automations/{rule_id}/test"): ["automations.write"],
    ("GET", "/api/v1/automations/{rule_id}/history"): ["automations.read"],
    ("GET", "/api/v1/automations/{rule_id}/steps"): ["automations.read"],
    ("POST", "/api/v1/automations/{rule_id}/steps"): ["automations.write"],
    ("PUT", "/api/v1/automations/{rule_id}/steps/{step_id}"): ["automations.write"],
    ("DELETE", "/api/v1/automations/{rule_id}/steps/{step_id}"): ["automations.write"],
    ("GET", "/api/v1/automations/trigger-templates"): ["automations.read"],
    ("GET", "/api/v1/automations/templates"): ["automations.read"],
    # Variables bulk-set
    ("POST", "/api/v1/variables/bulk-set"): ["vars.write"],
    # Semantic Types
    ("GET", "/api/v1/types/semantic"): ["types.read"],
    ("POST", "/api/v1/types/semantic"): ["types.write"],
    ("GET", "/api/v1/types/semantic/{type_id}"): ["types.read"],
    ("PATCH", "/api/v1/types/semantic/{type_id}"): ["types.write"],
    ("DELETE", "/api/v1/types/semantic/{type_id}"): ["types.write"],
    ("GET", "/api/v1/types/semantic/{type_id}/triggers"): ["types.read"],
    ("GET", "/api/v1/types/semantic/{type_id}/conversions"): ["types.read"],
    # Dashboards
    ("GET", "/api/v1/dashboards"): ["dashboards.read"],
    ("POST", "/api/v1/dashboards"): ["dashboards.write"],
    ("GET", "/api/v1/dashboards/default"): ["dashboards.read"],
    ("GET", "/api/v1/dashboards/{dashboard_id}"): ["dashboards.read"],
    ("PUT", "/api/v1/dashboards/{dashboard_id}"): ["dashboards.write"],
    ("DELETE", "/api/v1/dashboards/{dashboard_id}"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/widgets"): ["dashboards.write"],
    ("PUT", "/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}"): ["dashboards.write"],
    ("DELETE", "/api/v1/dashboards/{dashboard_id}/widgets/{widget_id}"): ["dashboards.write"],
    ("PUT", "/api/v1/dashboards/{dashboard_id}/layout"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/share"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/share/pin"): ["dashboards.write"],
    ("DELETE", "/api/v1/dashboards/{dashboard_id}/share/pin"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/unshare"): ["dashboards.write"],
    ("PUT", "/api/v1/dashboards/{dashboard_id}/embed-config"): ["dashboards.write"],
    ("PUT", "/api/v1/dashboards/{dashboard_id}/kiosk-config"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/clone"): ["dashboards.write"],
    ("POST", "/api/v1/dashboards/{dashboard_id}/generate-set"): ["dashboards.write"],
    ("GET", "/api/v1/dashboards/public/{token}"): [],  # public — no auth required
    # Notifications — no cap required, user-scoped
    ("GET", "/api/v1/notifications"): [],
    ("GET", "/api/v1/notifications/unread-count"): [],
    ("PATCH", "/api/v1/notifications/{notification_id}/read"): [],
    ("PATCH", "/api/v1/notifications/read-all"): [],
    ("DELETE", "/api/v1/notifications/{notification_id}"): [],
    # MCP
    ("POST", "/api/v1/mcp/tools/list"): ["mcp.read"],
    ("POST", "/api/v1/mcp/tools/call"): ["mcp.execute"],
    ("GET", "/api/v1/mcp/sse"): ["mcp.read"],
    ("POST", "/api/v1/mcp/messages"): ["mcp.execute"],
    ("GET", "/api/v1/mcp/status"): ["mcp.read"],
    ("GET", "/api/v1/mcp/log"): ["mcp.read"],
    # Search
    ("GET", "/api/v1/search"): ["devices.read"],
    # System / Demo Data
    ("POST", "/api/v1/system/demo-data"): ["devices.write"],
    ("DELETE", "/api/v1/system/demo-data"): ["devices.write"],
    # User preferences
    ("PATCH", "/api/v1/users/me/preferences"): ["users.read"],
    # Tours — user-scoped, no special capability required
    ("GET", "/api/v1/tours"): [],
    ("POST", "/api/v1/tours"): [],
    ("GET", "/api/v1/tours/public/{token}"): [],
    ("GET", "/api/v1/tours/{tour_id}"): [],
    ("PUT", "/api/v1/tours/{tour_id}"): [],
    ("DELETE", "/api/v1/tours/{tour_id}"): [],
    ("POST", "/api/v1/tours/{tour_id}/share"): [],
    # Simulator — user-scoped, no special capability required
    ("GET", "/api/v1/simulator/templates"): [],
    ("GET", "/api/v1/simulator/configs"): [],
    ("POST", "/api/v1/simulator/configs"): [],
    ("GET", "/api/v1/simulator/configs/{sim_id}"): [],
    ("PUT", "/api/v1/simulator/configs/{sim_id}"): [],
    ("DELETE", "/api/v1/simulator/configs/{sim_id}"): [],
    ("POST", "/api/v1/simulator/configs/{sim_id}/start"): [],
    ("POST", "/api/v1/simulator/configs/{sim_id}/stop"): [],
    ("POST", "/api/v1/simulator/configs/{sim_id}/pulse"): [],
    ("POST", "/api/v1/simulator/quick-pulse"): [],
}

# Public whitelist (auth-free, minimal, static).
PUBLIC_WHITELIST: set[tuple[str, str]] = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/devices/hello"),
    ("POST", "/api/v1/devices/pairing/hello"),
    ("POST", "/api/v1/pairing/hello"),
    ("POST", "/api/v1/pairing/confirm"),
    ("POST", "/api/v1/devices/pairing/confirm"),
    ("GET", "/api/v1/pairing/status"),
    ("GET", "/api/v1/devices/pairing/status"),
    ("GET", "/api/v1/dashboards/public/{token}"),
    ("GET", "/api/v1/dashboards/public/{token}/history"),
    ("GET", "/api/v1/dashboards/embed/{token}"),
    ("POST", "/api/v1/auth/refresh"),
    ("GET", "/api/v1/auth/roles"),
    ("POST", "/api/v1/auth/mfa/verify"),
    # Custom API runtime handler (uses per-endpoint auth, not bearer)
    ("GET", "/api/v1/custom-api/call/{path:path}"),
    ("POST", "/api/v1/custom-api/call/{path:path}"),
    # MCP SSE transport (handles own auth via query param / bearer)
    ("GET", "/api/v1/mcp/sse"),
    ("POST", "/api/v1/mcp/messages"),
}

# ── RBAC: Role → Capability Mapping ──────────────────────────────────────────

# Read-only capabilities (viewer role)
_VIEWER_CAPS: list[str] = [
    "devices.read", "telemetry.read", "vars.read", "entities.read",
    "events.read", "alerts.read", "automations.read", "dashboards.read",
    "metrics.read", "types.read", "webhooks.read", "tasks.read",
    "groups.read", "effects.read", "signals.read", "executions.read",
    "providers.read", "org.read", "org.members.read", "users.read",
    "audit.read", "ota.read", "mcp.read", "notifications.read",
    "pairing.status", "config.read", "secrets.read",
]

# Read + write capabilities (operator role)
_OPERATOR_CAPS: list[str] = _VIEWER_CAPS + [
    "devices.write", "devices.token.reissue", "devices.unclaim",
    "vars.write", "vars.ack", "telemetry.emit",
    "entities.write", "events.emit", "events.ack",
    "alerts.write", "automations.write", "dashboards.write",
    "types.write", "webhooks.write", "tasks.write",
    "groups.write", "executions.write",
    "pairing.start", "pairing.claim", "pairing.confirm",
    "ota.write", "mcp.execute", "notifications.write",
    "modules.read", "modules.write",
    "apikeys.read", "apikeys.write",
    "core.auth.login", "core.auth.register",
]

# Admin capabilities (all except cap.admin superuser flag)
_ADMIN_CAPS: list[str] = _OPERATOR_CAPS + [
    "config.write", "secrets.write", "audit.write",
    "devices.purge", "devices.hello",
    "org.write", "org.members.write",
    "ota.admin", "providers.write", "signals.ingest",
    "mic.admin",
]

# Owner has everything
_OWNER_CAPS: list[str] = _ADMIN_CAPS + ["cap.admin", "org.admin"]

# Kiosk: dashboard-only, no navigation
_KIOSK_CAPS: list[str] = ["dashboards.read", "metrics.read"]

ROLE_CAPS: dict[str, list[str]] = {
    "owner": _OWNER_CAPS,
    "admin": _ADMIN_CAPS,
    "operator": _OPERATOR_CAPS,
    "member": _OPERATOR_CAPS,  # backward compat alias
    "viewer": _VIEWER_CAPS,
    "kiosk": _KIOSK_CAPS,
}

VALID_ROLES: set[str] = set(ROLE_CAPS.keys())


def resolve_caps_for_role(
    role: str,
    user_caps: list[str] | None = None,
    custom_role_caps: list[str] | None = None,
) -> list[str]:
    """Resolve effective capabilities from role + optional overrides.

    Priority: custom_role_caps > ROLE_CAPS[role], then union with user_caps.
    """
    if custom_role_caps is not None:
        base = list(custom_role_caps)
    else:
        base = list(ROLE_CAPS.get(role, []))

    # Union with per-user caps (legacy field)
    if user_caps:
        cap_set = set(base)
        for cap in user_caps:
            if cap not in cap_set and cap in CAPABILITY_REGISTRY:
                base.append(cap)

    # Filter out unknown caps
    return [cap for cap in base if cap in CAPABILITY_REGISTRY]


def enforcement_enabled() -> bool:
    # Env override takes precedence (for tests), otherwise use settings.
    env = os.getenv("HUBEX_CAPS_ENFORCE")
    if env is not None:
        return env == "1"
    return settings.caps_enforce

def validate_caps(caps: Iterable[str]) -> list[str]:
    unknown = [cap for cap in caps if cap not in CAPABILITY_REGISTRY]
    return unknown

def resolve_required_caps(method: str, path: str) -> list[str] | None:
    return CAPABILITY_MAP.get((method.upper(), path))

def is_public_route(method: str, path: str) -> bool:
    return (method.upper(), path) in PUBLIC_WHITELIST
