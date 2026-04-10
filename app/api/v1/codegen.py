"""Code Generator — produces deployment-ready Arduino/ESP sketches from UI config.

Two endpoints:
    * ``POST /codegen/generate`` — legacy single-file generator, requires an
      existing device with a PinConfiguration. Returns JSON with the code
      string.
    * ``POST /codegen/project`` — Sprint 2 wizard-mode generator. Creates the
      device + token + variables + pin config in the backend, then assembles
      a ready-to-flash ZIP and streams it back to the caller.
"""

import io
import logging
import re
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.user import User
from app.core.codegen_zip import (
    CodegenError,
    PinConflictError,
    ProjectSpec,
    UnsupportedFrameworkError,
    assign_pins,
    build_project_zip,
)
from app.core.firmware_templates import (
    ARDUINO_CLIENT_TEMPLATE,
    DIRECT_ESP32_TEMPLATE,
    ESP32_BRIDGE_TEMPLATE,
)
from app.core.security import hash_device_token
from app.db.models.component import HardwareComponent
from app.db.models.device import Device
from app.db.models.hardware import BoardProfile, PinConfiguration
from app.db.models.pairing import DeviceToken
from app.db.models.variables import VariableDefinition

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


# =============================================================================
# Sprint 2: wizard-mode project ZIP generator
# =============================================================================


class CodegenProjectRequest(BaseModel):
    """Wizard payload for ``POST /codegen/project``."""

    device_name: str = Field(..., min_length=1, max_length=128)
    board_key: str = Field(..., description="Board chip key: esp32 / esp32s3 / esp32c3 / rp2040")
    framework: str = Field(..., description="platformio | arduino | micropython")
    component_keys: list[str] = Field(default_factory=list)
    wifi_ssid: str = ""
    wifi_pass: str = ""
    server_url: str = "http://your-hubex:8000"
    read_interval_s: int = Field(default=10, ge=1, le=3600)


def _error(code: str, message: str, status: int = 400, **extra):
    detail = {"code": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status, detail=detail)


def _unique_device_uid() -> str:
    return f"esp-{secrets.token_hex(6)}"


@router.post("/project")
async def generate_project(
    data: CodegenProjectRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new device + API key + pin config, then stream a ZIP project.

    This is the Sprint 2 'killer-demo' endpoint: the user picks a board and
    sensors in the wizard, and gets back a ready-to-flash project archive
    with the device already registered in HubEx.
    """
    if data.framework not in {"platformio", "arduino", "micropython"}:
        raise _error(
            "FRAMEWORK_INVALID",
            f"Unknown framework '{data.framework}'. Use platformio, arduino or micropython.",
        )

    # --- 1. Resolve board by chip key -------------------------------------
    board_res = await db.execute(
        select(BoardProfile).where(BoardProfile.chip == data.board_key).limit(1)
    )
    board = board_res.scalar_one_or_none()
    if board is None:
        raise _error("BOARD_UNKNOWN", f"No board profile found for chip '{data.board_key}'", status=404)

    # --- 2. Resolve components --------------------------------------------
    if not data.component_keys:
        raise _error("NO_COMPONENTS", "Pick at least one sensor or actuator.")
    comp_res = await db.execute(
        select(HardwareComponent).where(HardwareComponent.key.in_(data.component_keys))
    )
    component_rows = list(comp_res.scalars().all())
    found_keys = {c.key for c in component_rows}
    missing = [k for k in data.component_keys if k not in found_keys]
    if missing:
        raise _error(
            "COMPONENT_UNKNOWN",
            f"Unknown component key(s): {', '.join(missing)}",
            status=404,
            missing=missing,
        )

    # Convert to plain dicts for the codegen module (no DB objects leaking out)
    components_data = [
        {
            "key": c.key,
            "name": c.name,
            "category": c.category,
            "pin_requirements": c.pin_requirements or [],
            "libraries_required": c.libraries_required or [],
            "variables": c.variables or [],
            "bus_type": c.bus_type,
        }
        for c in component_rows
    ]

    # --- 3. Auto-assign pins ----------------------------------------------
    try:
        pin_assignments = assign_pins(board.pins or [], components_data)
    except PinConflictError as e:
        raise _error("PIN_CONFLICT", e.message, status=400, **e.extra)

    # --- 4. Create Device + token + variables + pin config ----------------
    # Wizard-created devices are owned by the requesting user. Org id is left
    # NULL in v1 — the normal devices endpoint can move them into an org later.
    user_id = current_user.id
    org_id = None

    device_uid = _unique_device_uid()
    now = datetime.now(timezone.utc)

    device = Device(
        device_uid=device_uid,
        name=data.device_name.strip(),
        device_type=board.chip,
        category="hardware",
        owner_user_id=user_id,
        org_id=org_id,
        is_claimed=user_id is not None,
        last_seen_at=None,
        firmware_version=f"hubex-wizard/{data.framework}",
        capabilities={
            "board": board.chip,
            "framework": data.framework,
            "wizard": True,
            "components": [c["key"] for c in components_data],
        },
    )
    db.add(device)
    await db.flush()  # populate device.id before FK inserts

    # Issue a device token
    plain_token = secrets.token_urlsafe(32)
    token_hash = hash_device_token(plain_token)
    db.add(DeviceToken(device_id=device.id, token_hash=token_hash, is_active=True))

    # Create variable definitions (upsert: skip existing keys)
    for comp in components_data:
        for var in comp.get("variables") or []:
            vkey = var.get("key")
            if not vkey:
                continue
            existing = await db.get(VariableDefinition, vkey)
            if existing is not None:
                continue
            db.add(
                VariableDefinition(
                    key=vkey,
                    scope="device",
                    value_type=var.get("value_type") or "float",
                    unit=var.get("unit"),
                    description=f"{comp.get('name')} ({comp.get('key')})",
                    direction=var.get("direction") or "read_write",
                    category=comp.get("category"),
                )
            )

    # Pin configuration — convert pin keys to strings (JSON dict keys)
    db.add(
        PinConfiguration(
            device_id=device.id,
            board_profile_id=board.id,
            shield_profile_id=None,
            pin_assignments={str(k): v for k, v in pin_assignments.items()},
        )
    )

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.exception("codegen/project commit failed")
        raise _error("DEVICE_CREATE_FAILED", f"Failed to create device: {e}", status=500)

    # --- 5. Assemble the ZIP ----------------------------------------------
    spec = ProjectSpec(
        device_id=device.id,
        device_name=device.name or "HubEx Device",
        device_uid=device_uid,
        device_token=plain_token,
        board_key=board.chip,
        board_name=board.name,
        board_chip=board.chip,
        framework=data.framework,
        components=components_data,
        pin_assignments=pin_assignments,
        wifi_ssid=data.wifi_ssid,
        wifi_pass=data.wifi_pass,
        server_url=data.server_url,
        read_interval_s=data.read_interval_s,
    )

    try:
        zip_bytes, suggested_name = build_project_zip(spec)
    except UnsupportedFrameworkError as e:
        # Device was already committed; still return the error so the user
        # can just retry the wizard with a different framework.
        raise _error("FRAMEWORK_INVALID", e.message, status=400, **e.extra)
    except CodegenError as e:
        raise _error(e.code, e.message, status=400, **e.extra)

    headers = {
        "Content-Disposition": f'attachment; filename="{suggested_name}"',
        "X-HubEx-Device-Id": str(device.id),
        "X-HubEx-Device-Uid": device_uid,
        "X-HubEx-Device-Name": device.name or "",
    }
    return StreamingResponse(
        io.BytesIO(zip_bytes),
        media_type="application/zip",
        headers=headers,
    )
