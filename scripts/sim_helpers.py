"""Shared helpers for HUBEX device simulators."""
from __future__ import annotations
from typing import Any

RESET = "\033[0m"; GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; CYAN = "\033[96m"
def _ok(m): print(f"  {GREEN}+ {m}{RESET}")
def _warn(m): print(f"  {YELLOW}! {m}{RESET}")


def robust_pair(requests_mod, server: str, uid: str, jwt: str, *,
                name: str, device_type: str, category: str,
                firmware: str = "sim-1.0",
                capabilities: dict | None = None) -> str | None:
    """Pair a device robustly. If already claimed, unclaim and re-pair.

    Returns device_token or None on failure.
    """
    auth = {"Authorization": f"Bearer {jwt}"}

    # Step 1: Try hello
    r = requests_mod.post(f"{server}/api/v1/devices/pairing/hello",
                          json={"device_uid": uid, "firmware_version": firmware,
                                "capabilities": capabilities or {}}, timeout=15)
    r.raise_for_status()
    data = r.json()

    if data.get("claimed"):
        # Already claimed — unclaim first
        _warn(f"{uid}: already claimed, unclaiming...")
        # Find device ID
        try:
            devices = requests_mod.get(f"{server}/api/v1/devices", headers=auth, timeout=10).json()
            dev = next((d for d in devices if d.get("device_uid") == uid), None)
            if dev:
                requests_mod.post(f"{server}/api/v1/devices/{dev['id']}/unclaim",
                                  headers=auth, timeout=10)
                _ok("Unclaimed. Re-pairing...")
                # Retry hello
                r = requests_mod.post(f"{server}/api/v1/devices/pairing/hello",
                                      json={"device_uid": uid, "firmware_version": firmware,
                                            "capabilities": capabilities or {}}, timeout=15)
                r.raise_for_status()
                data = r.json()
                if data.get("claimed"):
                    _warn("Still claimed after unclaim — skipping")
                    return None
            else:
                _warn("Could not find device to unclaim")
                return None
        except Exception as e:
            _warn(f"Unclaim failed: {e}")
            return None

    code = data["pairing_code"]

    # Step 2: Claim
    r = requests_mod.post(f"{server}/api/v1/devices/pairing/claim",
                          headers=auth, json={"pairing_code": code, "device_uid": uid}, timeout=15)
    r.raise_for_status()

    # Step 3: Confirm
    r = requests_mod.post(f"{server}/api/v1/devices/pairing/confirm",
                          json={"device_uid": uid, "pairing_code": code}, timeout=15)
    r.raise_for_status()
    resp = r.json()
    token = resp["device_token"]

    # Step 4: Set identity
    requests_mod.patch(f"{server}/api/v1/devices/{resp['device_id']}",
                       headers=auth,
                       json={"name": name, "device_type": device_type, "category": category},
                       timeout=10)

    _ok(f"Paired: {name} (token: {token[:12]}...)")
    return token


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
    {"key": "gps_location", "scope": "device", "valueType": "json", "description": "GPS position", "displayHint": "map", "category": "gps"},
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
