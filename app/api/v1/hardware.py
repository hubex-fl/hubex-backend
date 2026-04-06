"""Hardware Abstraction Layer API — board profiles, shields, pin configurations."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.hardware import BoardProfile, ShieldProfile, PinConfiguration

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/hardware", tags=["Hardware"])

# ── Built-in Board Profiles ──────────────────────────────────────────────────

_BUILTIN_BOARDS = [
    {
        "name": "ESP32 DevKit V1",
        "chip": "esp32",
        "flash_size_kb": 4096,
        "ram_size_kb": 520,
        "wifi_capable": True,
        "bluetooth_capable": True,
        "description": "Most common ESP32 development board. 30-pin layout, USB-C or Micro-USB.",
        "pins": [
            {"number": 2, "label": "D2/LED", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 4, "label": "D4", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 5, "label": "D5/SS", "capabilities": ["digital_io", "pwm", "spi"]},
            {"number": 12, "label": "D12/MISO", "capabilities": ["digital_io", "adc", "pwm", "spi", "touch"]},
            {"number": 13, "label": "D13/MOSI", "capabilities": ["digital_io", "adc", "pwm", "spi", "touch"]},
            {"number": 14, "label": "D14/SCK", "capabilities": ["digital_io", "adc", "pwm", "spi", "touch"]},
            {"number": 15, "label": "D15", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 16, "label": "D16/RX2", "capabilities": ["digital_io", "pwm", "uart_rx"]},
            {"number": 17, "label": "D17/TX2", "capabilities": ["digital_io", "pwm", "uart_tx"]},
            {"number": 18, "label": "D18/SCK", "capabilities": ["digital_io", "pwm", "spi"]},
            {"number": 19, "label": "D19/MISO", "capabilities": ["digital_io", "pwm", "spi"]},
            {"number": 21, "label": "D21/SDA", "capabilities": ["digital_io", "pwm", "i2c_sda"]},
            {"number": 22, "label": "D22/SCL", "capabilities": ["digital_io", "pwm", "i2c_scl"]},
            {"number": 23, "label": "D23/MOSI", "capabilities": ["digital_io", "pwm", "spi"]},
            {"number": 25, "label": "D25/DAC1", "capabilities": ["digital_io", "adc", "pwm", "dac"]},
            {"number": 26, "label": "D26/DAC2", "capabilities": ["digital_io", "adc", "pwm", "dac"]},
            {"number": 27, "label": "D27", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 32, "label": "D32", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 33, "label": "D33", "capabilities": ["digital_io", "adc", "pwm", "touch"]},
            {"number": 34, "label": "D34", "capabilities": ["adc"]},
            {"number": 35, "label": "D35", "capabilities": ["adc"]},
            {"number": 36, "label": "VP/D36", "capabilities": ["adc"]},
            {"number": 39, "label": "VN/D39", "capabilities": ["adc"]},
        ],
    },
    {
        "name": "ESP32-S3 DevKit",
        "chip": "esp32s3",
        "flash_size_kb": 8192,
        "ram_size_kb": 512,
        "wifi_capable": True,
        "bluetooth_capable": True,
        "description": "ESP32-S3 with USB-OTG, AI acceleration. 44-pin layout.",
        "pins": [
            {"number": i, "label": f"GPIO{i}", "capabilities": ["digital_io", "pwm"]}
            for i in range(0, 21)
        ],
    },
    {
        "name": "ESP32-C3 Mini",
        "chip": "esp32c3",
        "flash_size_kb": 4096,
        "ram_size_kb": 400,
        "wifi_capable": True,
        "bluetooth_capable": True,
        "description": "Ultra-low-power RISC-V ESP32-C3. Compact, WiFi+BLE.",
        "pins": [
            {"number": i, "label": f"GPIO{i}", "capabilities": ["digital_io", "pwm"]}
            for i in range(0, 11)
        ],
    },
    {
        "name": "Raspberry Pi Pico W",
        "chip": "rp2040",
        "flash_size_kb": 2048,
        "ram_size_kb": 264,
        "wifi_capable": True,
        "bluetooth_capable": True,
        "description": "RP2040 dual-core with CYW43 WiFi/BLE. 40-pin layout.",
        "pins": [
            {"number": i, "label": f"GP{i}", "capabilities": ["digital_io", "pwm"]}
            for i in range(0, 29)
        ],
    },
]

_BUILTIN_SHIELDS = [
    {
        "name": "HubEx Arduino Bridge Shield",
        "target_chip": None,
        "occupied_pins": [16, 17],
        "exposed_pins": [],
        "bus_type": "serial",
        "description": "Serial bridge shield — connects Arduino to ESP32 via UART. Enables remote programming.",
        "components": [{"type": "bridge", "protocol": "hubex_serial"}],
    },
    {
        "name": "HubEx RS485 Gateway Module",
        "target_chip": "esp32",
        "occupied_pins": [16, 17, 4],
        "exposed_pins": [],
        "bus_type": "serial",
        "description": "RS485/Modbus gateway module. MAX485 transceiver with DE/RE on GPIO4.",
        "components": [{"type": "transceiver", "protocol": "modbus_rtu"}],
    },
    {
        "name": "Sensor Shield (DHT22 + BMP280 + Light)",
        "target_chip": "esp32",
        "occupied_pins": [4, 21, 22, 34],
        "exposed_pins": [],
        "bus_type": "i2c",
        "description": "Multi-sensor shield: DHT22 (GPIO4), BMP280 (I2C), LDR (ADC GPIO34).",
        "components": [
            {"type": "sensor", "model": "DHT22", "pin": 4, "variables": ["temperature", "humidity"]},
            {"type": "sensor", "model": "BMP280", "bus": "i2c", "variables": ["pressure", "altitude"]},
            {"type": "sensor", "model": "LDR", "pin": 34, "variables": ["light_level"]},
        ],
    },
]


# ── Schemas ──────────────────────────────────────────────────────────────────

class BoardOut(BaseModel):
    id: int; name: str; chip: str; pins: list
    flash_size_kb: int; ram_size_kb: int
    wifi_capable: bool; bluetooth_capable: bool
    is_builtin: bool; description: str | None
    image_url: str | None


class ShieldOut(BaseModel):
    id: int; name: str; target_chip: str | None
    occupied_pins: list; exposed_pins: list
    bus_type: str | None; components: list | None
    description: str | None; is_builtin: bool


class PinConfigOut(BaseModel):
    id: int; device_id: int
    board_profile_id: int | None
    shield_profile_id: int | None
    pin_assignments: dict


class PinConfigUpdateIn(BaseModel):
    board_profile_id: int | None = None
    shield_profile_id: int | None = None
    pin_assignments: dict = {}


# ── Seed Builtins ────────────────────────────────────────────────────────────

async def _ensure_builtins(db: AsyncSession) -> None:
    result = await db.execute(select(BoardProfile).where(BoardProfile.is_builtin == True).limit(1))
    if result.scalar_one_or_none():
        return
    for b in _BUILTIN_BOARDS:
        db.add(BoardProfile(**b, is_builtin=True))
    for s in _BUILTIN_SHIELDS:
        db.add(ShieldProfile(**s, is_builtin=True))
    await db.flush()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/boards", response_model=list[BoardOut])
async def list_boards(db: AsyncSession = Depends(get_db)):
    await _ensure_builtins(db)
    await db.commit()
    result = await db.execute(select(BoardProfile).order_by(BoardProfile.name))
    return [BoardOut(
        id=b.id, name=b.name, chip=b.chip, pins=b.pins or [],
        flash_size_kb=b.flash_size_kb, ram_size_kb=b.ram_size_kb,
        wifi_capable=b.wifi_capable, bluetooth_capable=b.bluetooth_capable,
        is_builtin=b.is_builtin, description=b.description, image_url=b.image_url,
    ) for b in result.scalars().all()]


@router.get("/boards/{board_id}", response_model=BoardOut)
async def get_board(board_id: int, db: AsyncSession = Depends(get_db)):
    b = await db.get(BoardProfile, board_id)
    if not b: raise HTTPException(status_code=404, detail="board not found")
    return BoardOut(
        id=b.id, name=b.name, chip=b.chip, pins=b.pins or [],
        flash_size_kb=b.flash_size_kb, ram_size_kb=b.ram_size_kb,
        wifi_capable=b.wifi_capable, bluetooth_capable=b.bluetooth_capable,
        is_builtin=b.is_builtin, description=b.description, image_url=b.image_url,
    )


@router.get("/shields", response_model=list[ShieldOut])
async def list_shields(db: AsyncSession = Depends(get_db)):
    await _ensure_builtins(db)
    await db.commit()
    result = await db.execute(select(ShieldProfile).order_by(ShieldProfile.name))
    return [ShieldOut(
        id=s.id, name=s.name, target_chip=s.target_chip,
        occupied_pins=s.occupied_pins or [], exposed_pins=s.exposed_pins or [],
        bus_type=s.bus_type, components=s.components,
        description=s.description, is_builtin=s.is_builtin,
    ) for s in result.scalars().all()]


@router.get("/devices/{device_id}/pins", response_model=PinConfigOut | None)
async def get_pin_config(device_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PinConfiguration).where(PinConfiguration.device_id == device_id)
    )
    pc = result.scalar_one_or_none()
    if not pc: return None
    return PinConfigOut(
        id=pc.id, device_id=pc.device_id,
        board_profile_id=pc.board_profile_id,
        shield_profile_id=pc.shield_profile_id,
        pin_assignments=pc.pin_assignments or {},
    )


@router.put("/devices/{device_id}/pins", response_model=PinConfigOut)
async def update_pin_config(
    device_id: int,
    data: PinConfigUpdateIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PinConfiguration).where(PinConfiguration.device_id == device_id)
    )
    pc = result.scalar_one_or_none()
    if pc:
        pc.board_profile_id = data.board_profile_id
        pc.shield_profile_id = data.shield_profile_id
        pc.pin_assignments = data.pin_assignments
    else:
        pc = PinConfiguration(
            device_id=device_id,
            board_profile_id=data.board_profile_id,
            shield_profile_id=data.shield_profile_id,
            pin_assignments=data.pin_assignments,
        )
        db.add(pc)
    await db.commit()
    await db.refresh(pc)
    return PinConfigOut(
        id=pc.id, device_id=pc.device_id,
        board_profile_id=pc.board_profile_id,
        shield_profile_id=pc.shield_profile_id,
        pin_assignments=pc.pin_assignments or {},
    )
