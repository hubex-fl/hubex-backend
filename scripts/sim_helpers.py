"""Shared helpers for HUBEX device simulators."""
from __future__ import annotations
from typing import Any


def ensure_variable_definitions(requests_mod, server: str, jwt: str, var_defs: list[dict[str, Any]]) -> int:
    """Create VariableDefinitions via API if they don't exist.

    Each var_def should have: key, scope, valueType, description
    Optional: unit, displayHint, category

    Returns number of newly created definitions.
    """
    auth = {"Authorization": f"Bearer {jwt}"}
    created = 0
    for vd in var_defs:
        try:
            r = requests_mod.post(
                f"{server}/api/v1/variables/definitions",
                headers=auth,
                json=vd,
                timeout=10,
            )
            if r.status_code in (200, 201):
                created += 1
            # 409 = already exists, that's fine
        except Exception:
            pass
    return created


# Pre-defined variable sets per device type
ESP32_VARIABLES = [
    {"key": "temperature", "scope": "device", "valueType": "float", "description": "Temperature", "unit": "°C", "displayHint": "line_chart", "category": "sensor.temperature"},
    {"key": "humidity", "scope": "device", "valueType": "float", "description": "Relative humidity", "unit": "%", "displayHint": "gauge", "category": "sensor.humidity"},
    {"key": "pressure", "scope": "device", "valueType": "float", "description": "Atmospheric pressure", "unit": "hPa", "displayHint": "sparkline", "category": "sensor.pressure"},
    {"key": "battery", "scope": "device", "valueType": "float", "description": "Battery level", "unit": "%", "displayHint": "gauge", "category": "power"},
    {"key": "rssi", "scope": "device", "valueType": "float", "description": "WiFi signal strength", "unit": "dBm", "displayHint": "sparkline", "category": "connectivity"},
]

WEATHER_API_VARIABLES = [
    {"key": "temperature_2m", "scope": "device", "valueType": "float", "description": "Temperature at 2m", "unit": "°C", "displayHint": "line_chart", "category": "weather"},
    {"key": "wind_speed_10m", "scope": "device", "valueType": "float", "description": "Wind speed at 10m", "unit": "km/h", "displayHint": "sparkline", "category": "weather"},
    {"key": "relative_humidity_2m", "scope": "device", "valueType": "float", "description": "Relative humidity at 2m", "unit": "%", "displayHint": "gauge", "category": "weather"},
]

MQTT_BRIDGE_VARIABLES = [
    {"key": "value", "scope": "device", "valueType": "float", "description": "MQTT sensor value", "displayHint": "line_chart", "category": "mqtt"},
]

AGENT_VARIABLES = [
    {"key": "cpu_percent", "scope": "device", "valueType": "float", "description": "CPU usage", "unit": "%", "displayHint": "gauge", "category": "system"},
    {"key": "memory_percent", "scope": "device", "valueType": "float", "description": "Memory usage", "unit": "%", "displayHint": "gauge", "category": "system"},
    {"key": "disk_percent", "scope": "device", "valueType": "float", "description": "Disk usage", "unit": "%", "displayHint": "gauge", "category": "system"},
]
