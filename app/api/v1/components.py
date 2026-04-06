"""Component Library API — CRUD + built-in sensor/actuator manifests."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.component import HardwareComponent

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/components", tags=["Components"])

_BUILTINS = [
    {"key": "dht22", "name": "DHT22", "category": "sensor", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "Data"}],
     "libraries_required": ["DHT sensor library"], "default_widget": "line_chart",
     "variables": [{"key": "temperature", "semantic_type": "temperature", "direction": "read", "unit": "°C"},
                   {"key": "humidity", "semantic_type": "humidity", "direction": "read", "unit": "%"}],
     "description": "Digital temperature and humidity sensor. ±0.5°C accuracy, 0-100% RH."},
    {"key": "bme280", "name": "BME280", "category": "sensor", "bus_type": "i2c",
     "pin_requirements": [{"type": "i2c", "count": 2}],
     "libraries_required": ["Adafruit BME280 Library"], "default_widget": "line_chart",
     "variables": [{"key": "temperature", "semantic_type": "temperature", "direction": "read", "unit": "°C"},
                   {"key": "humidity", "semantic_type": "humidity", "direction": "read", "unit": "%"},
                   {"key": "pressure", "semantic_type": "pressure", "direction": "read", "unit": "hPa"}],
     "description": "I2C temperature, humidity, and pressure sensor. High accuracy."},
    {"key": "ds18b20", "name": "DS18B20", "category": "sensor", "bus_type": "onewire",
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "Data"}],
     "libraries_required": ["OneWire", "DallasTemperature"], "default_widget": "line_chart",
     "variables": [{"key": "temperature", "semantic_type": "temperature", "direction": "read", "unit": "°C"}],
     "description": "Waterproof 1-Wire temperature sensor. -55°C to +125°C."},
    {"key": "hcsr04", "name": "HC-SR04", "category": "sensor", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 2, "label": "Trigger+Echo"}],
     "libraries_required": [], "default_widget": "gauge",
     "variables": [{"key": "distance_cm", "semantic_type": "distance", "direction": "read", "unit": "cm"}],
     "description": "Ultrasonic distance sensor. 2cm-400cm range."},
    {"key": "pir", "name": "PIR Motion Sensor", "category": "sensor", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "OUT"}],
     "libraries_required": [], "default_widget": "bool",
     "variables": [{"key": "motion", "semantic_type": "boolean", "direction": "read"}],
     "description": "Passive infrared motion detector."},
    {"key": "bh1750", "name": "BH1750", "category": "sensor", "bus_type": "i2c",
     "pin_requirements": [{"type": "i2c", "count": 2}],
     "libraries_required": ["BH1750"], "default_widget": "gauge",
     "variables": [{"key": "light_lux", "semantic_type": "light", "direction": "read", "unit": "lx"}],
     "description": "Digital ambient light sensor. 1-65535 lux."},
    {"key": "relay", "name": "Relay Module", "category": "actuator", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "IN"}],
     "libraries_required": [], "default_widget": "toggle_control",
     "variables": [{"key": "state", "semantic_type": "boolean", "direction": "write"}],
     "description": "Single-channel relay. Switch AC/DC loads up to 10A."},
    {"key": "servo", "name": "Servo Motor", "category": "actuator", "bus_type": None,
     "pin_requirements": [{"type": "pwm", "count": 1, "label": "Signal"}],
     "libraries_required": ["ESP32Servo"], "default_widget": "slider_control",
     "variables": [{"key": "angle", "semantic_type": "percentage", "direction": "write", "unit": "°"}],
     "description": "Standard servo motor. 0-180° rotation."},
    {"key": "led_pwm", "name": "LED (PWM)", "category": "actuator", "bus_type": None,
     "pin_requirements": [{"type": "pwm", "count": 1, "label": "LED"}],
     "libraries_required": [], "default_widget": "slider_control",
     "variables": [{"key": "brightness", "semantic_type": "percentage", "direction": "write", "unit": "%"}],
     "description": "PWM-controlled LED. Variable brightness 0-100%."},
    {"key": "neopixel", "name": "WS2812B / Neopixel", "category": "actuator", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "Data"}],
     "libraries_required": ["Adafruit NeoPixel"], "default_widget": "json",
     "variables": [{"key": "color", "semantic_type": "color", "direction": "write"}],
     "description": "Addressable RGB LED strip. Individual pixel control."},
    {"key": "buzzer", "name": "Buzzer", "category": "actuator", "bus_type": None,
     "pin_requirements": [{"type": "pwm", "count": 1, "label": "Buzzer"}],
     "libraries_required": [], "default_widget": "toggle_control",
     "variables": [{"key": "tone", "semantic_type": "number", "direction": "write", "unit": "Hz"}],
     "description": "Piezo buzzer for audio feedback."},
    {"key": "ssd1306", "name": "SSD1306 OLED", "category": "display", "bus_type": "i2c",
     "pin_requirements": [{"type": "i2c", "count": 2}],
     "libraries_required": ["Adafruit SSD1306", "Adafruit GFX Library"], "default_widget": None,
     "variables": [],
     "description": "0.96\" OLED display. 128x64 pixels, I2C."},
    {"key": "gps_neo6m", "name": "GPS NEO-6M", "category": "module", "bus_type": "uart",
     "pin_requirements": [{"type": "uart_rx", "count": 1}, {"type": "uart_tx", "count": 1}],
     "libraries_required": ["TinyGPSPlus"], "default_widget": "map",
     "variables": [{"key": "latitude", "semantic_type": "gps_lat", "direction": "read"},
                   {"key": "longitude", "semantic_type": "gps_lng", "direction": "read"},
                   {"key": "speed", "semantic_type": "speed", "direction": "read", "unit": "km/h"}],
     "description": "GPS module with UART. Position, speed, altitude."},
    {"key": "analog_input", "name": "Analog Input", "category": "sensor", "bus_type": None,
     "pin_requirements": [{"type": "adc", "count": 1, "label": "Analog"}],
     "libraries_required": [], "default_widget": "gauge",
     "variables": [{"key": "value", "semantic_type": "number", "direction": "read"}],
     "description": "Generic analog input. Raw ADC value (0-4095 on ESP32)."},
    {"key": "button", "name": "Push Button", "category": "sensor", "bus_type": None,
     "pin_requirements": [{"type": "digital_io", "count": 1, "label": "BTN"}],
     "libraries_required": [], "default_widget": "bool",
     "variables": [{"key": "pressed", "semantic_type": "boolean", "direction": "read"}],
     "description": "Simple push button with pull-up/pull-down."},
]


class ComponentOut(BaseModel):
    id: int; key: str; name: str; category: str
    pin_requirements: list; bus_type: str | None
    libraries_required: list; variables: list
    default_widget: str | None; description: str | None
    datasheet_url: str | None; is_builtin: bool


async def _ensure_builtins(db: AsyncSession) -> None:
    result = await db.execute(select(HardwareComponent).where(HardwareComponent.is_builtin == True).limit(1))
    if result.scalar_one_or_none():
        return
    for c in _BUILTINS:
        db.add(HardwareComponent(**c, is_builtin=True))
    await db.flush()


@router.get("", response_model=list[ComponentOut])
async def list_components(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    await _ensure_builtins(db)
    await db.commit()
    stmt = select(HardwareComponent).order_by(HardwareComponent.category, HardwareComponent.name)
    if category:
        stmt = stmt.where(HardwareComponent.category == category)
    result = await db.execute(stmt)
    return [ComponentOut(
        id=c.id, key=c.key, name=c.name, category=c.category,
        pin_requirements=c.pin_requirements or [], bus_type=c.bus_type,
        libraries_required=c.libraries_required or [], variables=c.variables or [],
        default_widget=c.default_widget, description=c.description,
        datasheet_url=c.datasheet_url, is_builtin=c.is_builtin,
    ) for c in result.scalars().all()]


@router.get("/{component_key}", response_model=ComponentOut)
async def get_component(component_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HardwareComponent).where(HardwareComponent.key == component_key))
    c = result.scalar_one_or_none()
    if not c: raise HTTPException(status_code=404, detail="component not found")
    return ComponentOut(
        id=c.id, key=c.key, name=c.name, category=c.category,
        pin_requirements=c.pin_requirements or [], bus_type=c.bus_type,
        libraries_required=c.libraries_required or [], variables=c.variables or [],
        default_widget=c.default_widget, description=c.description,
        datasheet_url=c.datasheet_url, is_builtin=c.is_builtin,
    )
