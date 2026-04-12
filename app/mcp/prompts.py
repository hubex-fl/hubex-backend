"""Sprint 9 Step 3C: MCP prompt templates.

Pre-built prompt templates that MCP clients can discover via prompts/list
and invoke via prompts/get. Each template generates a multi-step prompt
that orchestrates multiple HubEx tools to complete a common workflow.
"""

from typing import Any

PROMPT_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "check-device-status",
        "description": "Check the health and current values of a device",
        "arguments": [
            {
                "name": "device_name",
                "description": "Device name or UID to check (leave empty for fleet overview)",
                "required": False,
            },
        ],
    },
    {
        "name": "investigate-alert",
        "description": "Find firing alerts and trace them back to the root cause",
        "arguments": [
            {
                "name": "severity",
                "description": "Filter by severity: info, warning, critical (leave empty for all)",
                "required": False,
            },
        ],
    },
    {
        "name": "dashboard-overview",
        "description": "List all dashboards and summarize what each one visualizes",
        "arguments": [],
    },
    {
        "name": "control-device",
        "description": "Set a variable on a device to control it (e.g. toggle a relay, set a setpoint)",
        "arguments": [
            {
                "name": "device_uid",
                "description": "The device UID (e.g. demo-temp-sensor-01)",
                "required": True,
            },
            {
                "name": "variable_key",
                "description": "The variable key to set (e.g. target_temperature, relay_state)",
                "required": True,
            },
            {
                "name": "value",
                "description": "The new value to set",
                "required": True,
            },
        ],
    },
]


def get_prompt_messages(name: str, arguments: dict[str, str]) -> list[dict[str, Any]]:
    """Generate the messages array for a prompt template invocation."""

    if name == "check-device-status":
        device = arguments.get("device_name", "").strip()
        if device:
            text = (
                f"Check the status of device '{device}'. "
                "First list all devices to find it, then get its current variable values "
                "and report on health, online status, last seen, and any anomalies."
            )
        else:
            text = (
                "Give me a fleet overview. List all devices with their online/offline "
                "status and health. Highlight any devices that are offline or in bad health."
            )
        return [{"role": "user", "content": {"type": "text", "text": text}}]

    if name == "investigate-alert":
        severity = arguments.get("severity", "").strip()
        if severity:
            text = (
                f"Find all firing alerts with severity '{severity}'. "
                "For each alert, identify the device and variable that triggered it, "
                "show the current value, and suggest what might be wrong."
            )
        else:
            text = (
                "Check for any firing alerts. List them with their severity, "
                "trace each one to the triggering device and variable, "
                "and summarize the situation."
            )
        return [{"role": "user", "content": {"type": "text", "text": text}}]

    if name == "dashboard-overview":
        text = (
            "List all dashboards and describe what each one shows. "
            "Include the widget count and any notable data sources."
        )
        return [{"role": "user", "content": {"type": "text", "text": text}}]

    if name == "control-device":
        uid = arguments.get("device_uid", "")
        key = arguments.get("variable_key", "")
        value = arguments.get("value", "")
        text = (
            f"Set variable '{key}' on device '{uid}' to '{value}'. "
            "After setting, read back the value to confirm it was applied. "
            "Show the before and after values."
        )
        return [{"role": "user", "content": {"type": "text", "text": text}}]

    return [{"role": "user", "content": {"type": "text", "text": f"Unknown prompt template: {name}"}}]
