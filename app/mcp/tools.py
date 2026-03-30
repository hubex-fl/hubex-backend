"""MCP Tool Definitions for HUBEX (M22 Step 1).

Defines all tools that an AI agent can invoke via the MCP protocol.
Each tool maps to one or more HUBEX API operations.
"""

from typing import Any

# ---------------------------------------------------------------------------
# Tool schema definitions (JSON Schema format for MCP)
# ---------------------------------------------------------------------------

HUBEX_TOOLS: list[dict[str, Any]] = [
    # ── Device Tools ──────────────────────────────────────────────────────
    {
        "name": "hubex_list_devices",
        "description": "List all IoT devices registered in HUBEX. Returns device UID, name, type, online status, and health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "health_filter": {
                    "type": "string",
                    "enum": ["ok", "stale", "dead", ""],
                    "description": "Filter by health status",
                },
                "limit": {
                    "type": "integer",
                    "default": 50,
                    "description": "Max number of devices to return",
                },
            },
        },
    },
    {
        "name": "hubex_get_device",
        "description": "Get detailed information about a specific device by its numeric ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "device_id": {"type": "integer", "description": "Device ID"},
            },
            "required": ["device_id"],
        },
    },

    # ── Variable Tools ────────────────────────────────────────────────────
    {
        "name": "hubex_list_variables",
        "description": "List all variable definitions. Variables are data points that devices send or receive (temperature, humidity, GPS, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["device", "org", "global", ""],
                    "description": "Filter by scope",
                },
                "category": {
                    "type": "string",
                    "description": "Filter by category (e.g. sensor.temperature, gps, config)",
                },
            },
        },
    },
    {
        "name": "hubex_get_variable_value",
        "description": "Get the current value of a specific variable.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Variable key (e.g. demo.temperature)"},
                "scope": {"type": "string", "enum": ["device", "org", "global"], "default": "device"},
                "device_uid": {"type": "string", "description": "Device UID (required for device scope)"},
            },
            "required": ["key", "scope"],
        },
    },
    {
        "name": "hubex_set_variable",
        "description": "Set the value of a writable variable. Use this to control devices (e.g. set target temperature, toggle heater).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Variable key"},
                "value": {"type": "string", "description": "New value to set"},
                "scope": {"type": "string", "enum": ["device", "org", "global"], "default": "device"},
                "device_uid": {"type": "string", "description": "Device UID (required for device scope)"},
            },
            "required": ["key", "value", "scope"],
        },
    },
    {
        "name": "hubex_get_variable_history",
        "description": "Get time-series history for a variable. Returns timestamped values for charting and analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Variable key"},
                "scope": {"type": "string", "enum": ["device", "org", "global"], "default": "device"},
                "device_uid": {"type": "string", "description": "Device UID"},
                "limit": {"type": "integer", "default": 100, "description": "Max data points"},
            },
            "required": ["key", "scope"],
        },
    },

    # ── Alert Tools ───────────────────────────────────────────────────────
    {
        "name": "hubex_list_alerts",
        "description": "List current alert events (firing, acknowledged, resolved). Alerts are triggered when conditions are met (e.g. temperature too high, device offline).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["firing", "acknowledged", "resolved", ""],
                    "description": "Filter by status",
                },
            },
        },
    },
    {
        "name": "hubex_acknowledge_alert",
        "description": "Acknowledge an active alert event to indicate it has been noticed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "Alert event ID to acknowledge"},
            },
            "required": ["event_id"],
        },
    },

    # ── Automation Tools ──────────────────────────────────────────────────
    {
        "name": "hubex_list_automations",
        "description": "List all automation rules. Automations are IF-THEN rules that react to device events and variable changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "description": "Filter by enabled/disabled state",
                },
            },
        },
    },
    {
        "name": "hubex_toggle_automation",
        "description": "Enable or disable an automation rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "integer", "description": "Automation rule ID"},
                "enabled": {"type": "boolean", "description": "True to enable, false to disable"},
            },
            "required": ["rule_id", "enabled"],
        },
    },
    {
        "name": "hubex_test_automation",
        "description": "Test-fire an automation rule immediately, ignoring cooldown. Useful for verifying the action works.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "integer", "description": "Automation rule ID to test"},
            },
            "required": ["rule_id"],
        },
    },

    # ── Metrics & Health Tools ────────────────────────────────────────────
    {
        "name": "hubex_get_metrics",
        "description": "Get system-wide metrics: device counts (online/offline), alert counts, event volume, uptime.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "hubex_get_health",
        "description": "Get system health status: backend API, database, Redis connectivity.",
        "inputSchema": {"type": "object", "properties": {}},
    },

    # ── Dashboard Tools ───────────────────────────────────────────────────
    {
        "name": "hubex_list_dashboards",
        "description": "List all dashboards. Dashboards are customizable visualizations of device data.",
        "inputSchema": {"type": "object", "properties": {}},
    },

    # ── Semantic Type Tools ───────────────────────────────────────────────
    {
        "name": "hubex_list_semantic_types",
        "description": "List all semantic types. Semantic types define what a variable represents (temperature, humidity, GPS, etc.) with units, triggers, and visualization hints.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return all HUBEX MCP tool definitions."""
    return HUBEX_TOOLS
