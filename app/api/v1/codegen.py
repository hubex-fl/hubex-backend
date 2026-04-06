"""Code Generator — produces deployment-ready Arduino/ESP sketches from UI config."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.hardware import BoardProfile, PinConfiguration
from app.db.models.component import HardwareComponent
from app.core.firmware_templates import DIRECT_ESP32_TEMPLATE, ESP32_BRIDGE_TEMPLATE, ARDUINO_CLIENT_TEMPLATE

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/codegen", tags=["Code Generator"])


class CodegenRequest(BaseModel):
    device_id: int
    mode: str = "direct"  # direct | bridge
    wifi_ssid: str = "YOUR_WIFI"
    wifi_pass: str = "YOUR_PASSWORD"
    server_url: str = "http://your-hubex:8000"
    device_token: str = "YOUR_DEVICE_TOKEN"


class CodegenResult(BaseModel):
    filename: str
    code: str
    libraries: list[str]
    board_name: str
    mode: str


@router.post("/generate", response_model=CodegenResult)
async def generate_code(
    data: CodegenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate firmware code for a device based on its pin configuration."""

    # Load pin configuration
    result = await db.execute(
        select(PinConfiguration).where(PinConfiguration.device_id == data.device_id)
    )
    pin_config = result.scalar_one_or_none()

    board_name = "ESP32 DevKit V1"
    if pin_config and pin_config.board_profile_id:
        board = await db.get(BoardProfile, pin_config.board_profile_id)
        if board:
            board_name = board.name

    # Collect components from pin assignments
    components: list[HardwareComponent] = []
    pin_defines = []
    sensor_inits = []
    sensor_reads = []
    actuator_handlers = []
    libraries = set()
    telemetry_fields = []

    if pin_config and pin_config.pin_assignments:
        for pin_str, assignment in pin_config.pin_assignments.items():
            pin_num = int(pin_str)
            comp_key = assignment.get("component")
            if comp_key:
                comp_res = await db.execute(
                    select(HardwareComponent).where(HardwareComponent.key == comp_key)
                )
                comp = comp_res.scalar_one_or_none()
                if comp:
                    components.append(comp)
                    for lib in (comp.libraries_required or []):
                        libraries.add(lib)

                    func = assignment.get("function", "sensor_input")
                    var_key = assignment.get("variable_key", comp.key)

                    pin_defines.append(f"#define PIN_{comp.key.upper()} {pin_num}")

                    if comp.category == "sensor":
                        sensor_reads.append(f'  // Read {comp.name} on pin {pin_num}')
                        sensor_reads.append(f'  Serial.println("VAR {var_key} " + String(analogRead(PIN_{comp.key.upper()})));')
                        telemetry_fields.append(f'    payload["{var_key}"] = analogRead(PIN_{comp.key.upper()});')
                    elif comp.category == "actuator":
                        actuator_handlers.append(f'  if (key == "{var_key}") {{ digitalWrite(PIN_{comp.key.upper()}, value.toInt()); }}')

    lib_includes = "\n".join([f'#include <{lib}.h>' for lib in sorted(libraries)]) if libraries else "// No additional libraries"

    if data.mode == "bridge":
        code = ARDUINO_CLIENT_TEMPLATE.format(
            board_name=board_name,
            baud_rate=115200,
            device_name=f"HubEx Device #{data.device_id}",
            library_includes=lib_includes,
            pin_defines="\n".join(pin_defines) or "// No pins configured",
            sensor_init="",
            pin_setup="\n  ".join([f"pinMode(PIN_{c.key.upper()}, {'INPUT' if c.category == 'sensor' else 'OUTPUT'});" for c in components]) or "// No pins",
            sensor_setup="",
            sensor_read="\n".join(sensor_reads) or "  // No sensors configured",
            read_interval=10000,
            actuator_handlers="\n".join(actuator_handlers) or "  // No actuators configured",
        )
        filename = f"hubex_client_{data.device_id}.ino"
    else:
        code = DIRECT_ESP32_TEMPLATE.format(
            board_name=board_name,
            wifi_ssid=data.wifi_ssid,
            wifi_pass=data.wifi_pass,
            server_url=data.server_url,
            device_token=data.device_token,
            library_includes=lib_includes,
            pin_defines="\n".join(pin_defines) or "// No pins configured",
            sensor_init="",
            pin_setup="\n  ".join([f"pinMode(PIN_{c.key.upper()}, {'INPUT' if c.category == 'sensor' else 'OUTPUT'});" for c in components]) or "// No pins",
            sensor_setup="",
            sensor_read="\n".join(sensor_reads) or "  // No sensors configured",
            telemetry_fields="\n".join(telemetry_fields) or '    payload["status"] = "ok";',
            read_interval=10000,
        )
        filename = f"hubex_device_{data.device_id}.ino"

    return CodegenResult(
        filename=filename,
        code=code,
        libraries=sorted(libraries),
        board_name=board_name,
        mode=data.mode,
    )


@router.get("/preview/{device_id}")
async def preview_code(
    device_id: int,
    mode: str = Query("direct"),
    db: AsyncSession = Depends(get_db),
):
    """Quick preview of generated code for a device."""
    result = await generate_code(
        CodegenRequest(device_id=device_id, mode=mode),
        db=db,
    )
    return PlainTextResponse(content=result.code, media_type="text/plain")
