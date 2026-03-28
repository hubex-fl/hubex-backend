"""Device type detection and constants."""

VALID_DEVICE_TYPES = frozenset({
    "esp32",
    "api_device",
    "mqtt_bridge",
    "software_agent",
    "standard_device",
    "unknown",
})

DEVICE_TYPE_LABELS = {
    "esp32": "ESP32",
    "api_device": "API Device",
    "mqtt_bridge": "MQTT Bridge",
    "software_agent": "Software Agent",
    "standard_device": "Standard Device",
    "unknown": "Unknown",
}


def detect_device_type(firmware_version: str | None) -> str:
    """Infer device type from the firmware_version string.

    Called during pairing hello; only overwrites if current type is
    unknown/None so manual overrides are preserved.
    """
    if not firmware_version:
        return "unknown"
    fw = firmware_version.lower()

    if "api-device" in fw or "api_device" in fw:
        return "api_device"
    if "mqtt-bridge" in fw or "mqtt_bridge" in fw:
        return "mqtt_bridge"
    if "esp" in fw or "esp32" in fw or "esp-idf" in fw:
        return "esp32"
    if "agent" in fw or "software-agent" in fw:
        return "software_agent"
    if "shelly" in fw or "tasmota" in fw:
        return "standard_device"
    return "unknown"
