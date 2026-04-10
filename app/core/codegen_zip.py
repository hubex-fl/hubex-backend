"""HubEx ESP Code Generator — full-project ZIP assembly.

Sprint 2: turns a wizard payload (board + framework + components + transport
+ name) into a ready-to-flash ZIP archive containing everything needed to
compile and run the firmware.

Supported frameworks:
    - platformio   → src/main.cpp + platformio.ini + include/config.h + README.md
    - arduino      → HUBEX_<name>.ino + config.h + README.md  (flat sketch)
    - micropython  → main.py + boot.py + config.py + README.md

Entry point: ``build_project_zip(spec)``.

The caller (``app/api/v1/codegen.py``) is responsible for the device / token
/ variable / pin-config creation in the database BEFORE calling this
function. The ZIP builder only reads the pre-computed pin assignments and
assembles file contents — it does no database work.
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from app.core.firmware_templates import (
    ARDUINO_IDE_INO_TEMPLATE,
    CONFIG_H_TEMPLATE,
    GITIGNORE_TEMPLATE,
    MICROPYTHON_BOOT_PY_TEMPLATE,
    MICROPYTHON_CONFIG_PY_TEMPLATE,
    MICROPYTHON_MAIN_PY_TEMPLATE,
    PLATFORMIO_INI_TEMPLATE,
    PLATFORMIO_MAIN_CPP_TEMPLATE,
    README_MD_TEMPLATE,
)

logger = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class CodegenError(Exception):
    """Base for codegen-specific errors raised up to the FastAPI handler."""

    code: str = "CODEGEN_ERROR"

    def __init__(self, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.message = message
        self.extra = extra


class PinConflictError(CodegenError):
    code = "PIN_CONFLICT"


class UnsupportedFrameworkError(CodegenError):
    code = "FRAMEWORK_INVALID"


@dataclass
class ProjectSpec:
    """Resolved spec fed to the ZIP builder.

    Populated by the FastAPI handler after DB lookups and device creation.
    """

    device_id: int
    device_name: str
    device_uid: str
    device_token: str  # plaintext, goes into config.h / config.py
    board_key: str
    board_name: str
    board_chip: str  # "esp32" / "esp32s3" / "esp32c3" / "rp2040"
    framework: str  # "platformio" / "arduino" / "micropython"
    components: list[dict]  # [{key, name, category, libraries, variables, pin_requirements}]
    pin_assignments: dict[int, dict]  # {pin_num: {component, function, variable_key}}
    wifi_ssid: str
    wifi_pass: str
    server_url: str
    read_interval_s: int = 10
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    )


# ---------------------------------------------------------------------------
# Constants: framework mapping, MicroPython drivers, PlatformIO boards
# ---------------------------------------------------------------------------

VALID_FRAMEWORKS = {"platformio", "arduino", "micropython"}

# Board chip → PlatformIO board id + platform
_PIO_BOARDS: dict[str, tuple[str, str, str]] = {
    #  chip      → (platformio board id,            platform,        env_name)
    "esp32":   ("esp32dev",        "espressif32",  "esp32dev"),
    "esp32s3": ("esp32-s3-devkitc-1", "espressif32", "esp32s3"),
    "esp32c3": ("esp32-c3-devkitm-1", "espressif32", "esp32c3"),
    "rp2040":  ("rpipicow",        "raspberrypi",  "rpipicow"),
}

# Arduino library name → PlatformIO lib_deps spec.
# When we find a library string in a component's libraries_required list that's
# not in this map, we fall back to emitting it verbatim (usually works with
# PlatformIO's registry search).
_PIO_LIB_SPEC: dict[str, str] = {
    "DHT sensor library": "adafruit/DHT sensor library@^1.4.6",
    "Adafruit BME280 Library": "adafruit/Adafruit BME280 Library@^2.2.4",
    "Adafruit Unified Sensor": "adafruit/Adafruit Unified Sensor@^1.1.14",
    "OneWire": "paulstoffregen/OneWire@^2.3.8",
    "DallasTemperature": "milesburton/DallasTemperature@^3.11.0",
    "BH1750": "claws/BH1750@^1.3.0",
    "ESP32Servo": "madhephaestus/ESP32Servo@^3.0.5",
    "Adafruit NeoPixel": "adafruit/Adafruit NeoPixel@^1.12.3",
    "Adafruit SSD1306": "adafruit/Adafruit SSD1306@^2.5.12",
    "Adafruit GFX Library": "adafruit/Adafruit GFX Library@^1.11.10",
    "TinyGPSPlus": "mikalhart/TinyGPSPlus@^1.0.3",
    "ArduinoJson": "bblanchon/ArduinoJson@^7.2.0",
}

# ArduinoJson is always needed for the telemetry payload
_MANDATORY_PIO_LIBS = ["bblanchon/ArduinoJson@^7.2.0"]

# MicroPython "drivers" — which components produce working MPY code in v1
# and what their import + init + read snippets look like.
#
# Each entry: { imports, init (per instance), read (emits payload[key] = ...) }
# "unsupported" components fall through to a commented-out TODO placeholder.
_MPY_DRIVERS: dict[str, dict[str, str]] = {
    "dht22": {
        "imports": "import dht",
        "init": "dht22_{i} = dht.DHT22(Pin({pin}))",
        "read": (
            "    try:\n"
            "        dht22_{i}.measure()\n"
            '        payload["temperature"] = dht22_{i}.temperature()\n'
            '        payload["humidity"] = dht22_{i}.humidity()\n'
            "    except Exception as e:\n"
            '        print("dht22 read failed:", e)'
        ),
    },
    "ds18b20": {
        "imports": "import onewire, ds18x20",
        "init": (
            "ow_{i} = onewire.OneWire(Pin({pin}))\n"
            "ds_{i} = ds18x20.DS18X20(ow_{i})\n"
            "ds_roms_{i} = ds_{i}.scan()"
        ),
        "read": (
            "    if ds_roms_{i}:\n"
            "        ds_{i}.convert_temp()\n"
            "        time.sleep_ms(750)\n"
            '        payload["temperature"] = ds_{i}.read_temp(ds_roms_{i}[0])'
        ),
    },
    "analog_input": {
        "imports": "from machine import ADC",
        "init": "adc_{i} = ADC(Pin({pin}))",
        "read": '    payload["analog_{i}"] = adc_{i}.read_u16()',
    },
    "pir": {
        "imports": "",
        "init": "pir_{i} = Pin({pin}, Pin.IN)",
        "read": '    payload["motion_{i}"] = pir_{i}.value()',
    },
    "button": {
        "imports": "",
        "init": "btn_{i} = Pin({pin}, Pin.IN, Pin.PULL_UP)",
        "read": '    payload["button_{i}"] = 1 - btn_{i}.value()',
    },
    "relay": {
        "imports": "",
        "init": "relay_{i} = Pin({pin}, Pin.OUT)",
        "read": '    payload["relay_{i}"] = relay_{i}.value()',
    },
    "led_pwm": {
        "imports": "from machine import PWM",
        "init": "led_pwm_{i} = PWM(Pin({pin}), freq=1000, duty_u16=0)",
        "read": '    payload["led_pwm_{i}"] = led_pwm_{i}.duty_u16()',
    },
    "buzzer": {
        "imports": "from machine import PWM",
        "init": "buzzer_{i} = PWM(Pin({pin}), freq=1000, duty_u16=0)",
        "read": "    # buzzer is output-only",
    },
}

# Component keys that DO NOT have a MicroPython driver in v1.
# The ZIP will still build but the main.py contains a TODO comment.
_MPY_UNSUPPORTED: set[str] = {
    "bme280",
    "bh1750",
    "ssd1306",
    "gps_neo6m",
    "neopixel",
    "servo",
    "hcsr04",
}


# ---------------------------------------------------------------------------
# Pin assignment (greedy allocator)
# ---------------------------------------------------------------------------


def _strictness(comp: dict) -> int:
    """Higher = more constrained, should be placed first."""
    reqs = comp.get("pin_requirements") or []
    strict = 0
    for req in reqs:
        t = req.get("type", "")
        if t in ("i2c_sda", "i2c_scl", "spi_mosi", "spi_miso", "spi_clk", "uart_tx", "uart_rx", "dac", "touch"):
            strict += 3
        elif t in ("adc", "pwm"):
            strict += 2
        else:
            strict += 1
    return strict


def assign_pins(board_pins: list[dict], components: list[dict]) -> dict[int, dict]:
    """Greedy pin assignment. Raises PinConflictError if any component can't be placed.

    ``board_pins`` is the BoardProfile.pins JSON array:
        [{number: 4, label: "GPIO4", capabilities: ["digital_io", "adc", "pwm"]}, ...]

    ``components`` is a list of dicts with at least `key`, `name`, `category`,
    `pin_requirements`, `variables`.

    Returns a dict keyed by pin number (int) with the same shape as
    PinConfiguration.pin_assignments.
    """
    used: set[int] = set()
    i2c_bus_assigned = False
    i2c_sda_pin: int | None = None
    i2c_scl_pin: int | None = None
    assignments: dict[int, dict] = {}

    # Sort components by strictness so I2C/SPI pins get picked before free digital IOs.
    sorted_comps = sorted(
        components,
        key=lambda c: (-_strictness(c), -len(c.get("pin_requirements") or []), c.get("key", "")),
    )

    for comp in sorted_comps:
        reqs = comp.get("pin_requirements") or []
        comp_key = comp.get("key", "unknown")
        comp_name = comp.get("name", comp_key)
        var_key = ((comp.get("variables") or [{}])[0] or {}).get("key", comp_key)
        function = "sensor_input" if comp.get("category") == "sensor" else "actuator_output"

        # Special-case I2C components: they ride on the shared bus.
        if any(r.get("type") == "i2c" for r in reqs):
            if not i2c_bus_assigned:
                # Find a SDA + SCL pair on the board
                sda = next((p for p in board_pins if "i2c_sda" in p.get("capabilities", []) and p["number"] not in used), None)
                scl = next((p for p in board_pins if "i2c_scl" in p.get("capabilities", []) and p["number"] not in used and p["number"] != (sda and sda["number"])), None)
                if not sda or not scl:
                    raise PinConflictError(
                        f"Board has no free I2C bus (SDA+SCL) for {comp_name}",
                        component=comp_key,
                        required="i2c",
                    )
                used.add(sda["number"])
                used.add(scl["number"])
                i2c_sda_pin = sda["number"]
                i2c_scl_pin = scl["number"]
                assignments[sda["number"]] = {
                    "component": "i2c_bus",
                    "function": "bus",
                    "variable_key": "i2c_sda",
                }
                assignments[scl["number"]] = {
                    "component": "i2c_bus",
                    "function": "bus",
                    "variable_key": "i2c_scl",
                }
                i2c_bus_assigned = True
            # Record the component against the SDA pin for the wiring table,
            # but don't mark additional pins used.
            if i2c_sda_pin is not None:
                # Attach the component as a "rider" on the SDA pin via a marker
                assignments.setdefault(i2c_sda_pin, {}).setdefault("i2c_devices", []).append(comp_key)
            continue

        # Non-I2C requirements: allocate one pin per requirement.
        for req in reqs:
            req_type = req.get("type", "digital_io")
            picked: int | None = None
            for pin in board_pins:
                if pin["number"] in used:
                    continue
                if req_type in pin.get("capabilities", []):
                    picked = pin["number"]
                    break
            if picked is None:
                raise PinConflictError(
                    f"No free {req_type} pin available for {comp_name}",
                    component=comp_key,
                    required=req_type,
                )
            used.add(picked)
            assignments[picked] = {
                "component": comp_key,
                "function": function,
                "variable_key": var_key,
            }

    return assignments


# ---------------------------------------------------------------------------
# Helpers for generating C++ snippets from the component list
# ---------------------------------------------------------------------------


def _sanitize_dirname(name: str) -> str:
    """Convert a human-readable device name into a safe folder + filename stem."""
    stem = re.sub(r"[^A-Za-z0-9_\- ]", "", name).strip().replace(" ", "_")
    if not stem:
        stem = "HubExDevice"
    return f"HUBEX_{stem}"


def _collect_libraries(components: list[dict]) -> list[str]:
    """Union of all unique libraries required by the components (order-preserving)."""
    seen: set[str] = set()
    libs: list[str] = []
    for comp in components:
        for lib in comp.get("libraries_required") or []:
            if lib not in seen:
                seen.add(lib)
                libs.append(lib)
    return libs


def _cpp_snippets(spec: ProjectSpec) -> dict[str, str]:
    """Build C++ snippets (pin_defines, sensor_init, etc.) from the pin assignments."""
    pin_defines: list[str] = []
    sensor_inits: list[str] = []
    sensor_reads: list[str] = []
    pin_setup: list[str] = []
    library_includes: list[str] = []
    telemetry_fields: list[str] = []

    libs = _collect_libraries(spec.components)
    for lib in libs:
        guard = lib.replace(" ", "_").replace("-", "_")
        # Very rough include inference. Components with no Arduino header → commented note.
        header = {
            "DHT sensor library": "DHT.h",
            "Adafruit BME280 Library": "Adafruit_BME280.h",
            "Adafruit Unified Sensor": "Adafruit_Sensor.h",
            "OneWire": "OneWire.h",
            "DallasTemperature": "DallasTemperature.h",
            "BH1750": "BH1750.h",
            "ESP32Servo": "ESP32Servo.h",
            "Adafruit NeoPixel": "Adafruit_NeoPixel.h",
            "Adafruit SSD1306": "Adafruit_SSD1306.h",
            "Adafruit GFX Library": "Adafruit_GFX.h",
            "TinyGPSPlus": "TinyGPSPlus.h",
            "ArduinoJson": "ArduinoJson.h",
        }.get(lib)
        if header and header not in ("ArduinoJson.h",):  # ArduinoJson is in the base template
            library_includes.append(f"#include <{header}>  // {lib}")

    # Walk components in a stable order (same as pin_assignments iteration)
    seen_components: set[str] = set()
    for pin_num, assignment in sorted(spec.pin_assignments.items()):
        comp_key = assignment.get("component")
        if not comp_key or comp_key in ("i2c_bus",):
            continue
        if comp_key in seen_components:
            continue
        seen_components.add(comp_key)
        comp = next((c for c in spec.components if c.get("key") == comp_key), None)
        if not comp:
            continue

        up = comp_key.upper().replace("-", "_")
        var_key = assignment.get("variable_key", comp_key)
        pin_defines.append(f"#define PIN_{up} {pin_num}")

        if comp_key == "dht22":
            sensor_inits.append(f"DHT dht_{pin_num}(PIN_{up}, DHT22);")
            pin_setup.append(f"dht_{pin_num}.begin();")
            sensor_reads.append(f"    float t_{pin_num} = dht_{pin_num}.readTemperature();")
            sensor_reads.append(f"    float h_{pin_num} = dht_{pin_num}.readHumidity();")
            telemetry_fields.append(f'    payload["temperature"] = t_{pin_num};')
            telemetry_fields.append(f'    payload["humidity"] = h_{pin_num};')
        elif comp_key == "ds18b20":
            sensor_inits.append(f"OneWire ow_{pin_num}(PIN_{up});")
            sensor_inits.append(f"DallasTemperature ds_{pin_num}(&ow_{pin_num});")
            pin_setup.append(f"ds_{pin_num}.begin();")
            sensor_reads.append(f"    ds_{pin_num}.requestTemperatures();")
            sensor_reads.append(f"    float t_{pin_num} = ds_{pin_num}.getTempCByIndex(0);")
            telemetry_fields.append(f'    payload["temperature"] = t_{pin_num};')
        elif comp_key == "analog_input":
            pin_setup.append(f"pinMode(PIN_{up}, INPUT);")
            sensor_reads.append(f"    int v_{pin_num} = analogRead(PIN_{up});")
            telemetry_fields.append(f'    payload["{var_key}"] = v_{pin_num};')
        elif comp_key in ("pir", "button"):
            pin_setup.append(f"pinMode(PIN_{up}, INPUT);")
            sensor_reads.append(f"    int v_{pin_num} = digitalRead(PIN_{up});")
            telemetry_fields.append(f'    payload["{var_key}"] = v_{pin_num};')
        elif comp_key in ("relay", "led_pwm", "buzzer"):
            pin_setup.append(f"pinMode(PIN_{up}, OUTPUT);")
            telemetry_fields.append(f'    payload["{var_key}"] = digitalRead(PIN_{up});')
        elif comp_key == "bme280":
            sensor_inits.append("Adafruit_BME280 bme;")
            pin_setup.append("if (!bme.begin(0x76)) { Serial.println(\"BME280 not found\"); }")
            sensor_reads.append("    float bmet = bme.readTemperature();")
            sensor_reads.append("    float bmeh = bme.readHumidity();")
            sensor_reads.append("    float bmep = bme.readPressure() / 100.0F;")
            telemetry_fields.append('    payload["temperature"] = bmet;')
            telemetry_fields.append('    payload["humidity"] = bmeh;')
            telemetry_fields.append('    payload["pressure"] = bmep;')
        elif comp_key == "bh1750":
            sensor_inits.append("BH1750 lightMeter;")
            pin_setup.append("lightMeter.begin();")
            sensor_reads.append("    float lux = lightMeter.readLightLevel();")
            telemetry_fields.append('    payload["lux"] = lux;')
        elif comp_key == "hcsr04":
            sensor_reads.append(f'    // HC-SR04 on pin {pin_num}: trigger/echo wiring TBD')
            telemetry_fields.append('    payload["distance_cm"] = 0;')
        elif comp_key == "servo":
            sensor_inits.append(f"Servo servo_{pin_num};")
            pin_setup.append(f"servo_{pin_num}.attach(PIN_{up});")
        elif comp_key == "neopixel":
            sensor_inits.append(f"Adafruit_NeoPixel strip_{pin_num}(8, PIN_{up}, NEO_GRB + NEO_KHZ800);")
            pin_setup.append(f"strip_{pin_num}.begin();")
        else:
            sensor_reads.append(f"    // {comp_key}: TODO (pin {pin_num})")

    return {
        "library_includes": "\n".join(library_includes) or "// no extra libraries",
        "pin_defines": "\n".join(pin_defines) or "// no pins configured",
        "sensor_init": "\n".join(sensor_inits),
        "pin_setup": "\n  ".join(pin_setup) if pin_setup else "// no pinMode calls",
        "sensor_setup": "",
        "sensor_read": "\n".join(sensor_reads) or "    // no sensors configured",
        "telemetry_fields": "\n".join(telemetry_fields) or '    payload["status"] = "ok";',
        "read_interval": str(spec.read_interval_s * 1000),
    }


def _mpy_snippets(spec: ProjectSpec) -> dict[str, str]:
    """MicroPython-specific snippets."""
    imports: set[str] = set()
    inits: list[str] = []
    reads: list[str] = []

    instance_counter = 0
    for pin_num, assignment in sorted(spec.pin_assignments.items()):
        comp_key = assignment.get("component")
        if not comp_key or comp_key == "i2c_bus":
            continue
        driver = _MPY_DRIVERS.get(comp_key)
        if driver is None:
            if comp_key in _MPY_UNSUPPORTED:
                reads.append(f"    # TODO: {comp_key} on pin {pin_num} (no MicroPython driver in v1)")
            else:
                reads.append(f"    # {comp_key}: unknown component")
            continue
        instance_counter += 1
        i = instance_counter
        if driver["imports"]:
            imports.add(driver["imports"])
        inits.append(driver["init"].format(i=i, pin=pin_num))
        reads.append(driver["read"].format(i=i))

    return {
        "mpy_imports": "\n".join(sorted(imports)) if imports else "",
        "mpy_pin_setup": "",  # Pins are inited inline in _mpy_sensor_init
        "mpy_sensor_init": "\n".join(inits) or "# no components",
        "mpy_sensor_read": "\n".join(reads) or '    payload["status"] = "ok"',
        "read_interval_s": str(spec.read_interval_s),
    }


# ---------------------------------------------------------------------------
# Framework-specific ZIP file producers
# ---------------------------------------------------------------------------


def _build_platformio(spec: ProjectSpec) -> dict[str, str]:
    """Return {zip_entry_name: text_content} for a PlatformIO project."""
    if spec.board_chip not in _PIO_BOARDS:
        raise UnsupportedFrameworkError(
            f"Board chip '{spec.board_chip}' has no PlatformIO mapping",
            board_chip=spec.board_chip,
        )
    pio_board, platform, env_name = _PIO_BOARDS[spec.board_chip]

    libs = _collect_libraries(spec.components)
    pio_specs = list(_MANDATORY_PIO_LIBS)
    for lib in libs:
        mapped = _PIO_LIB_SPEC.get(lib, lib)  # fall back to verbatim
        if mapped not in pio_specs:
            pio_specs.append(mapped)
    lib_deps_block = "\n".join(f"    {spec_line}" for spec_line in pio_specs)

    snippets = _cpp_snippets(spec)

    root = _sanitize_dirname(spec.device_name)

    platformio_ini = PLATFORMIO_INI_TEMPLATE.format(
        env_name=env_name,
        platform=platform,
        pio_board=pio_board,
        device_name=spec.device_name,
        lib_deps=lib_deps_block,
    )

    main_cpp = PLATFORMIO_MAIN_CPP_TEMPLATE.format(
        board_name=spec.board_name,
        **snippets,
    )

    config_h = CONFIG_H_TEMPLATE.format(
        wifi_ssid=spec.wifi_ssid,
        wifi_pass=spec.wifi_pass,
        server_url=spec.server_url,
        device_token=spec.device_token,
        device_name=spec.device_name,
    )

    return {
        f"{root}/platformio.ini": platformio_ini,
        f"{root}/src/main.cpp": main_cpp,
        f"{root}/include/config.h": config_h,
        f"{root}/lib/README": (
            "Private libraries for this project go here. See PlatformIO docs for layout.\n"
        ),
        f"{root}/.gitignore": GITIGNORE_TEMPLATE,
        f"{root}/README.md": _build_readme(spec, "platformio"),
    }


def _build_arduino_ide(spec: ProjectSpec) -> dict[str, str]:
    """Return {zip_entry_name: text_content} for an Arduino IDE sketch folder."""
    root = _sanitize_dirname(spec.device_name)
    sketch_name = f"{root}.ino"

    libs = _collect_libraries(spec.components)
    arduino_lib_comment = (
        "\n".join(f"//   - {lib}" for lib in libs) or "//   (none beyond ArduinoJson)"
    )

    snippets = _cpp_snippets(spec)
    sketch = ARDUINO_IDE_INO_TEMPLATE.format(
        board_name=spec.board_name,
        arduino_lib_comment=arduino_lib_comment,
        **snippets,
    )

    config_h = CONFIG_H_TEMPLATE.format(
        wifi_ssid=spec.wifi_ssid,
        wifi_pass=spec.wifi_pass,
        server_url=spec.server_url,
        device_token=spec.device_token,
        device_name=spec.device_name,
    )

    return {
        f"{root}/{sketch_name}": sketch,
        f"{root}/config.h": config_h,
        f"{root}/README.md": _build_readme(spec, "arduino"),
    }


def _build_micropython(spec: ProjectSpec) -> dict[str, str]:
    """Return {zip_entry_name: text_content} for a MicroPython project folder."""
    root = _sanitize_dirname(spec.device_name)

    boot_py = MICROPYTHON_BOOT_PY_TEMPLATE
    main_py = MICROPYTHON_MAIN_PY_TEMPLATE.format(
        board_name=spec.board_name,
        **_mpy_snippets(spec),
    )
    config_py = MICROPYTHON_CONFIG_PY_TEMPLATE.format(
        wifi_ssid=spec.wifi_ssid,
        wifi_pass=spec.wifi_pass,
        server_url=spec.server_url,
        device_token=spec.device_token,
        device_name=spec.device_name,
    )

    return {
        f"{root}/boot.py": boot_py,
        f"{root}/main.py": main_py,
        f"{root}/config.py": config_py,
        f"{root}/README.md": _build_readme(spec, "micropython"),
    }


# ---------------------------------------------------------------------------
# README assembly
# ---------------------------------------------------------------------------


def _build_readme(spec: ProjectSpec, framework: str) -> str:
    # ASCII wiring table
    wiring_rows: list[str] = []
    for pin_num, assignment in sorted(spec.pin_assignments.items()):
        comp_key = assignment.get("component", "-")
        function = assignment.get("function", "-")
        var_key = assignment.get("variable_key", "-")
        comp_name = comp_key
        if comp_key != "i2c_bus":
            comp = next((c for c in spec.components if c.get("key") == comp_key), None)
            if comp:
                comp_name = comp.get("name", comp_key)
        wiring_rows.append(
            f"| {pin_num:<3} | {comp_name:<12} | {function:<11} | {var_key:<14} |"
        )
    wiring_text = "\n".join(wiring_rows) or "| -   | -            | -           | -              |"

    component_list = ", ".join(c.get("name", c.get("key", "?")) for c in spec.components) or "(none)"

    framework_label_map = {
        "platformio": "PlatformIO",
        "arduino": "Arduino IDE",
        "micropython": "MicroPython",
    }
    framework_label = framework_label_map.get(framework, framework)

    config_file_map = {
        "platformio": "include/config.h",
        "arduino": "config.h",
        "micropython": "config.py",
    }
    config_file = config_file_map.get(framework, "config.h")

    flash_instructions = _flash_instructions(framework, spec)

    wifi_display = spec.wifi_ssid if spec.wifi_ssid else "(empty — edit config before flashing)"

    return README_MD_TEMPLATE.format(
        device_name=spec.device_name,
        board_name=spec.board_name,
        framework_label=framework_label,
        device_id=spec.device_id,
        device_token_short=spec.device_token[:8],
        component_list=component_list,
        flash_instructions=flash_instructions,
        wiring_rows=wiring_text,
        config_file=config_file,
        wifi_ssid_display=wifi_display,
        server_url=spec.server_url,
        read_interval_s=spec.read_interval_s,
        generated_at=spec.generated_at,
    )


def _flash_instructions(framework: str, spec: ProjectSpec) -> str:
    if framework == "platformio":
        return (
            "### PlatformIO (recommended)\n\n"
            "1. Install [PlatformIO](https://platformio.org/install) (VSCode extension or CLI).\n"
            "2. `cd` into this project folder.\n"
            "3. Run:\n\n"
            "   ```\n"
            "   pio run -t upload\n"
            "   pio device monitor\n"
            "   ```\n\n"
            "PlatformIO will download all library dependencies automatically from the\n"
            "spec in `platformio.ini`.\n"
        )
    if framework == "arduino":
        libs = _collect_libraries(spec.components)
        lib_lines = "\n".join(f"   - {lib}" for lib in libs) if libs else "   - ArduinoJson"
        return (
            "### Arduino IDE\n\n"
            "1. Open the Arduino IDE.\n"
            "2. Install required libraries via **Tools → Manage Libraries…**:\n\n"
            f"{lib_lines}\n\n"
            f"3. Install the **{spec.board_name}** board support package via\n"
            "   **Tools → Board → Boards Manager** if not already installed.\n"
            "4. Open this folder in the Arduino IDE (double-click the `.ino` file).\n"
            "5. Select your board + port, then press **Upload** (→).\n"
        )
    if framework == "micropython":
        return (
            "### MicroPython\n\n"
            "1. Flash the official MicroPython firmware onto your board (see https://micropython.org/download/).\n"
            "2. Install [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html):\n\n"
            "   ```\n"
            "   pip install mpremote\n"
            "   ```\n\n"
            "3. Copy the project files to the board:\n\n"
            "   ```\n"
            "   mpremote cp boot.py :boot.py\n"
            "   mpremote cp main.py :main.py\n"
            "   mpremote cp config.py :config.py\n"
            "   mpremote reset\n"
            "   ```\n\n"
            "4. Open a REPL to watch the output: `mpremote repl`\n"
        )
    return "TBD"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_project_zip(spec: ProjectSpec) -> tuple[bytes, str]:
    """Assemble the project ZIP and return (bytes, filename).

    Filename is a suggested download name (without path). The caller sets it
    in the HTTP ``Content-Disposition`` header.
    """
    if spec.framework not in VALID_FRAMEWORKS:
        raise UnsupportedFrameworkError(
            f"Framework '{spec.framework}' is not supported. "
            f"Valid: {sorted(VALID_FRAMEWORKS)}",
            framework=spec.framework,
        )

    if spec.framework == "platformio":
        files = _build_platformio(spec)
    elif spec.framework == "arduino":
        files = _build_arduino_ide(spec)
    elif spec.framework == "micropython":
        files = _build_micropython(spec)
    else:  # pragma: no cover
        raise UnsupportedFrameworkError(f"Unknown framework {spec.framework}")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for entry_name, content in files.items():
            zf.writestr(entry_name, content)

    filename = _sanitize_dirname(spec.device_name) + ".zip"
    return buf.getvalue(), filename
