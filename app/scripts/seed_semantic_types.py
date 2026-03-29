"""Seed 20 built-in semantic types, trigger templates, and unit conversions."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TYPES = [
    ("temperature", "Temperature", "float", "°C", "°C", -50, 100, "gauge", "🌡️", "#EF4444"),
    ("humidity", "Humidity", "float", "%", "%", 0, 100, "gauge", "💧", "#3B82F6"),
    ("pressure", "Pressure", "float", "hPa", "hPa", 800, 1200, "line_chart", "🔽", "#8B5CF6"),
    ("voltage", "Voltage", "float", "V", "V", 0, 500, "line_chart", "⚡", "#F59E0B"),
    ("current", "Current", "float", "A", "A", 0, 100, "line_chart", "⚡", "#F97316"),
    ("power", "Power", "float", "W", "W", 0, 10000, "line_chart", "🔌", "#EAB308"),
    ("energy", "Energy", "float", "kWh", "kWh", 0, None, "line_chart", "📊", "#22C55E"),
    ("percent", "Percent", "float", "%", "%", 0, 100, "gauge", "📈", "#6366F1"),
    ("battery", "Battery Level", "float", "%", "%", 0, 100, "gauge", "🔋", "#22C55E"),
    ("speed", "Speed", "float", "km/h", "km/h", 0, 300, "line_chart", "🏎️", "#06B6D4"),
    ("brightness", "Brightness", "float", "lux", "lux", 0, 100000, "gauge", "☀️", "#FACC15"),
    ("volume_db", "Volume", "float", "dB", "dB", 0, 140, "gauge", "🔊", "#A855F7"),
    ("angle", "Angle", "float", "°", "°", 0, 360, "gauge", "📐", "#64748B"),
    ("gps_position", "GPS Position", "json", None, None, None, None, "map", "📍", "#EF4444"),
    ("color_hex", "Color", "string", None, None, None, None, None, "🎨", "#EC4899"),
    ("boolean_switch", "Boolean Switch", "bool", None, None, None, None, "bool", "🔘", "#22C55E"),
    ("counter", "Counter", "int", None, None, 0, None, "line_chart", "🔢", "#F59E0B"),
    ("status_string", "Status Text", "string", None, None, None, None, "log", "📝", "#64748B"),
    ("image_url", "Image URL", "string", None, None, None, None, "image", "🖼️", "#8B5CF6"),
    ("generic_number", "Generic Number", "float", None, None, None, None, "sparkline", "📊", "#6366F1"),
]

NUMERIC_TYPES = {
    "temperature", "humidity", "pressure", "voltage", "current", "power",
    "energy", "percent", "battery", "speed", "brightness", "volume_db",
    "angle", "generic_number",
}

NUMERIC_TRIGGERS = [
    ("gt", "Greater than", "Value exceeds threshold", {"type": "object", "properties": {"value": {"type": "number"}}}, "📈"),
    ("gte", "Greater or equal", "Value reaches or exceeds threshold", None, "📈"),
    ("lt", "Less than", "Value drops below threshold", None, "📉"),
    ("lte", "Less or equal", "Value at or below threshold", None, "📉"),
    ("eq", "Equal to", "Value equals target", None, "🎯"),
    ("ne", "Not equal to", "Value differs from target", None, "↔️"),
    ("range_exit", "Range exit", "Value leaves defined range", {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}}}, "🚪"),
]

CONVERSIONS = [
    ("temperature", "°C", "°F", "value * 9/5 + 32"),
    ("temperature", "°C", "K", "value + 273.15"),
    ("pressure", "hPa", "mmHg", "value * 0.750062"),
    ("pressure", "hPa", "inHg", "value * 0.02953"),
    ("speed", "km/h", "mph", "value * 0.621371"),
    ("speed", "km/h", "m/s", "value / 3.6"),
    ("speed", "km/h", "knots", "value * 0.539957"),
    ("brightness", "lux", "fc", "value * 0.0929"),
    ("energy", "kWh", "Wh", "value * 1000"),
    ("energy", "kWh", "MJ", "value * 3.6"),
    ("power", "W", "kW", "value / 1000"),
    ("power", "W", "hp", "value / 745.7"),
    ("voltage", "V", "mV", "value * 1000"),
    ("current", "A", "mA", "value * 1000"),
]


async def main():
    from app.db.session import AsyncSessionLocal as async_session_factory
    from app.db.models.semantic_type import SemanticType, TriggerTemplate, UnitConversion
    from sqlalchemy import select

    async with async_session_factory() as db:
        created_types = 0
        skipped_types = 0
        type_map: dict[str, int] = {}

        # 1. Seed types
        for name, display, base, unit, sym, mn, mx, viz, icon, color in TYPES:
            existing = (await db.execute(
                select(SemanticType).where(SemanticType.name == name)
            )).scalar_one_or_none()
            if existing:
                type_map[name] = existing.id
                skipped_types += 1
                continue
            obj = SemanticType(
                name=name, display_name=display, base_type=base,
                unit=unit, unit_symbol=sym, min_value=mn, max_value=mx,
                default_viz_type=viz, icon=icon, color=color, is_builtin=True,
                value_schema=(
                    {"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}, "alt": {"type": "number"}}}
                    if name == "gps_position" else None
                ),
            )
            db.add(obj)
            await db.flush()
            type_map[name] = obj.id
            created_types += 1

        logger.info(f"Types: {created_types} created, {skipped_types} skipped")

        # 2. Seed trigger templates
        created_triggers = 0
        for type_name in NUMERIC_TYPES:
            tid = type_map.get(type_name)
            if not tid:
                continue
            existing = (await db.execute(
                select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == tid)
            )).scalars().all()
            if existing:
                continue
            for tname, dname, desc, schema, icon in NUMERIC_TRIGGERS:
                db.add(TriggerTemplate(
                    semantic_type_id=tid, trigger_name=tname, display_name=dname,
                    description=desc, config_schema=schema, icon=icon,
                ))
                created_triggers += 1
            # Extra for temperature
            if type_name == "temperature":
                db.add(TriggerTemplate(
                    semantic_type_id=tid, trigger_name="rate_of_change",
                    display_name="Rate of change", description="Temperature changes faster than threshold",
                    config_schema={"type": "object", "properties": {"rate": {"type": "number"}, "period_minutes": {"type": "number"}}},
                    icon="📈",
                ))
                created_triggers += 1

        # Boolean triggers
        tid = type_map.get("boolean_switch")
        if tid:
            existing = (await db.execute(
                select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == tid)
            )).scalars().all()
            if not existing:
                for tname, dname, desc, icon in [
                    ("changed_to_true", "Switched ON", "Value changed to true", "✅"),
                    ("changed_to_false", "Switched OFF", "Value changed to false", "❌"),
                    ("toggled", "Toggled", "Any value change", "🔄"),
                ]:
                    db.add(TriggerTemplate(
                        semantic_type_id=tid, trigger_name=tname, display_name=dname,
                        description=desc, icon=icon,
                    ))
                    created_triggers += 1

        # GPS triggers
        tid = type_map.get("gps_position")
        if tid:
            existing = (await db.execute(
                select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == tid)
            )).scalars().all()
            if not existing:
                for tname, dname, desc, schema, icon in [
                    ("entered_geofence", "Entered geofence", "Position entered defined area",
                     {"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}, "radius_m": {"type": "number"}}}, "📍"),
                    ("exited_geofence", "Exited geofence", "Position left defined area", None, "🚪"),
                    ("speed_exceeded", "Speed exceeded", "Movement speed exceeds threshold",
                     {"type": "object", "properties": {"max_speed": {"type": "number"}}}, "🏎️"),
                    ("distance_from_point", "Distance from point", "Distance exceeds threshold",
                     {"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}, "max_distance_m": {"type": "number"}}}, "📏"),
                ]:
                    db.add(TriggerTemplate(
                        semantic_type_id=tid, trigger_name=tname, display_name=dname,
                        description=desc, config_schema=schema, icon=icon,
                    ))
                    created_triggers += 1

        # Counter triggers (numeric + increment_exceeded)
        tid = type_map.get("counter")
        if tid:
            existing = (await db.execute(
                select(TriggerTemplate).where(TriggerTemplate.semantic_type_id == tid)
            )).scalars().all()
            if not existing:
                for tname, dname, desc, schema, icon in NUMERIC_TRIGGERS:
                    db.add(TriggerTemplate(
                        semantic_type_id=tid, trigger_name=tname, display_name=dname,
                        description=desc, config_schema=schema, icon=icon,
                    ))
                    created_triggers += 1
                db.add(TriggerTemplate(
                    semantic_type_id=tid, trigger_name="increment_exceeded",
                    display_name="Increment exceeded", description="Counter increased by more than X in Y minutes",
                    config_schema={"type": "object", "properties": {"increment": {"type": "number"}, "period_minutes": {"type": "number"}}},
                    icon="📈",
                ))
                created_triggers += 1

        logger.info(f"Triggers: {created_triggers} created")

        # 3. Seed unit conversions
        created_convs = 0
        for type_name, from_u, to_u, formula in CONVERSIONS:
            tid = type_map.get(type_name)
            if not tid:
                continue
            existing = (await db.execute(
                select(UnitConversion).where(
                    UnitConversion.semantic_type_id == tid,
                    UnitConversion.from_unit == from_u,
                    UnitConversion.to_unit == to_u,
                )
            )).scalar_one_or_none()
            if existing:
                continue
            db.add(UnitConversion(
                semantic_type_id=tid, from_unit=from_u, to_unit=to_u,
                formula=formula, is_default=False,
            ))
            created_convs += 1

        logger.info(f"Conversions: {created_convs} created")

        await db.commit()
        logger.info("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
