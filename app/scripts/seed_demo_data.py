"""Seed demo data for HUBEX (M20 Step 4).

Creates demo devices, variables, automations, and a dashboard
so a fresh install immediately looks alive.

Usage:
    python -m app.scripts.seed_demo_data
    python -m app.scripts.seed_demo_data --delete   # remove demo data
"""
import asyncio
import argparse
import json
import os
import random
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, select, func

from app.db.session import AsyncSessionLocal
from app.scripts.wait_for_db import wait_for_db

DEMO_TAG = "__demo__"


async def seed(db) -> dict:
    """Create demo entities. Returns summary dict."""
    from app.db.models.device import Device
    from app.db.models.user import User
    from app.db.models.variables import VariableDefinition, VariableValue
    from app.db.models.automation import AutomationRule
    from app.db.models.dashboard import Dashboard, DashboardWidget
    from app.db.models.entities import Entity

    # Find first user for ownership (order by id to get the primary/seed user)
    res = await db.execute(select(User).order_by(User.id).limit(1))
    user = res.scalar_one_or_none()
    if not user:
        print("ERROR: No user found. Create a user first.")
        return {"error": "no user"}

    # Find or create org_id
    org_id = None
    if hasattr(user, "default_org_id"):
        org_id = user.default_org_id

    summary = {"devices": 0, "variables": 0, "automations": 0, "dashboards": 0, "entities": 0}

    # ── 1. Demo Devices ────────────────────────────────────────────────────
    demo_devices = [
        {"uid": "demo-temp-sensor-01", "name": "Temperature Sensor (Demo)", "device_type": "esp32", "category": "hardware", "meta": {"location": "Lab Room 1", DEMO_TAG: True}},
        {"uid": "demo-weather-api-01", "name": "Weather API Service (Demo)", "device_type": "api_device", "category": "service", "meta": {"provider": "OpenWeather", DEMO_TAG: True}},
        {"uid": "demo-mqtt-bridge-01", "name": "MQTT Bridge (Demo)", "device_type": "mqtt_bridge", "category": "bridge", "meta": {"protocol": "MQTT", DEMO_TAG: True}},
    ]

    created_device_ids = []
    for dd in demo_devices:
        existing = await db.execute(select(Device).where(Device.device_uid == dd["uid"]))
        existing_device = existing.scalar_one_or_none()
        if existing_device:
            # Always refresh last_seen_at and fix metadata so demo devices stay online
            existing_device.last_seen_at = datetime.now(timezone.utc)
            existing_device.is_claimed = True
            existing_device.device_type = dd["device_type"]
            existing_device.category = dd.get("category", "hardware")
            created_device_ids.append(existing_device.id)
            continue
        device = Device(
            device_uid=dd["uid"],
            name=dd["name"],
            device_type=dd["device_type"],
            category=dd.get("category", "hardware"),
            owner_user_id=user.id,
            is_claimed=True,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(device)
        await db.flush()
        created_device_ids.append(device.id)
        summary["devices"] += 1

    # ── 2. Demo Variable Definitions ───────────────────────────────────────
    # These MUST match the variable_keys that the simulators actually produce.
    # Simulator keys: temperature, humidity, pressure, wind_speed, rain_mm,
    #                 motion, luminance, demo.gps (→ auto-splits to demo.gps.lat/lng)
    demo_vars = [
        # Temperature Sensor + Weather Station
        {"key": "temperature", "scope": "device", "value_type": "float", "description": "Temperature reading", "unit": "\u00b0C", "display_hint": "line_chart", "category": "sensor.temperature"},
        {"key": "humidity", "scope": "device", "value_type": "float", "description": "Relative humidity", "unit": "%", "display_hint": "gauge", "category": "sensor.humidity"},
        {"key": "pressure", "scope": "device", "value_type": "float", "description": "Atmospheric pressure", "unit": "hPa", "display_hint": "sparkline", "category": "sensor.pressure"},
        # Weather Station only
        {"key": "wind_speed", "scope": "device", "value_type": "float", "description": "Wind speed", "unit": "km/h", "display_hint": "line_chart", "category": "sensor.speed"},
        {"key": "rain_mm", "scope": "device", "value_type": "float", "description": "Rainfall accumulation", "unit": "mm", "display_hint": "sparkline", "category": "sensor.count"},
        # Motion Sensor
        {"key": "motion", "scope": "device", "value_type": "bool", "description": "PIR motion detected", "display_hint": "toggle", "category": "sensor.boolean"},
        {"key": "luminance", "scope": "device", "value_type": "float", "description": "Ambient light level", "unit": "lux", "display_hint": "gauge", "category": "sensor.brightness"},
        # GPS (the simulator writes demo.gps as JSON, telemetry bridge auto-splits)
        {"key": "demo.gps", "scope": "device", "value_type": "json", "description": "GPS location", "display_hint": "map", "category": "gps"},
        {"key": "demo.gps.lat", "scope": "device", "value_type": "float", "description": "GPS latitude", "unit": "\u00b0", "display_hint": "sparkline", "category": "gps"},
        {"key": "demo.gps.lng", "scope": "device", "value_type": "float", "description": "GPS longitude", "unit": "\u00b0", "display_hint": "sparkline", "category": "gps"},
        # Computed variable example: "feels like" temperature
        {"key": "feels_like", "scope": "device", "value_type": "float", "description": "Feels-like temperature (computed)", "unit": "\u00b0C", "display_hint": "line_chart", "category": "sensor.temperature",
         "formula": "temperature + 0.33 * humidity / 100 * 6 - 4", "compute_trigger": "reactive"},
    ]

    for dv in demo_vars:
        existing = await db.execute(
            select(VariableDefinition).where(VariableDefinition.key == dv["key"])
        )
        if existing.scalar_one_or_none():
            continue
        vdef = VariableDefinition(
            key=dv["key"],
            scope=dv["scope"],
            value_type=dv["value_type"],
            description=dv.get("description"),
            unit=dv.get("unit"),
            display_hint=dv.get("display_hint"),
            category=dv.get("category"),
            formula=dv.get("formula"),
            compute_trigger=dv.get("compute_trigger"),
        )
        db.add(vdef)
        summary["variables"] += 1

    # ── 2b. Demo Variable VALUES — matching simulator output keys ────────
    # Device 0 = Temp Sensor: temperature, humidity, pressure
    # Device 1 = Weather API: temperature, humidity, wind_speed, rain_mm
    # Device 2 = MQTT Bridge: motion, luminance, demo.gps
    device_var_map = [
        # Temp Sensor
        {
            "temperature": 23.5,
            "humidity": 65.0,
            "pressure": 1013.2,
        },
        # Weather Station
        {
            "temperature": 18.2,
            "humidity": 72.3,
            "wind_speed": 12.5,
            "rain_mm": 2.4,
        },
        # Motion Sensor (GPS + PIR)
        {
            "motion": False,
            "luminance": 450.0,
            "demo.gps": {"lat": 50.110, "lng": 8.682},
        },
    ]

    for i, device_id in enumerate(created_device_ids):
        if i >= len(device_var_map):
            break
        for var_key, value in device_var_map[i].items():
            existing_val = await db.execute(
                select(VariableValue).where(
                    VariableValue.variable_key == var_key,
                    VariableValue.device_id == device_id,
                    VariableValue.scope == "device",
                )
            )
            if existing_val.scalar_one_or_none():
                continue
            val = VariableValue(
                variable_key=var_key,
                scope="device",
                device_id=device_id,
                value_json=value,
                version=1,
            )
            db.add(val)

    # Global demo log value
    existing_log = await db.execute(
        select(VariableValue).where(
            VariableValue.variable_key == "demo.log",
            VariableValue.scope == "global",
        )
    )
    if not existing_log.scalar_one_or_none():
        db.add(VariableValue(
            variable_key="demo.log",
            scope="global",
            value_json="System started — demo mode active",
            version=1,
        ))

    await db.flush()

    # ── 3. Demo Automations ────────────────────────────────────────────────
    demo_rules = [
        {
            "name": "High Temperature Alert (Demo)",
            "description": "Alerts when temperature exceeds 35 C",
            "trigger_type": "variable_threshold",
            "trigger_config": {"variable_key": "demo.temperature", "operator": "gt", "value": 35},
            "action_type": "create_alert_event",
            "action_config": {"severity": "warning", "message": "Temperature exceeded 35 C"},
            "cooldown_seconds": 300,
        },
        {
            "name": "Device Offline Webhook (Demo)",
            "description": "Sends webhook when any device goes offline",
            "trigger_type": "device_offline",
            "trigger_config": {},
            "action_type": "call_webhook",
            "action_config": {"url": "https://httpbin.org/post", "method": "POST"},
            "cooldown_seconds": 600,
        },
    ]

    for dr in demo_rules:
        existing = await db.execute(
            select(AutomationRule).where(AutomationRule.name == dr["name"])
        )
        if existing.scalar_one_or_none():
            continue
        rule = AutomationRule(org_id=org_id, **dr)
        db.add(rule)
        summary["automations"] += 1

    # ── 4. Demo Dashboard ──────────────────────────────────────────────────
    dash_name = "Demo Dashboard"
    existing_dash = await db.execute(select(Dashboard).where(Dashboard.name == dash_name))
    if not existing_dash.scalar_one_or_none():
        dash = Dashboard(
            name=dash_name,
            description="Auto-generated demo dashboard with sample widgets",
            is_default=False,
            owner_id=user.id,
            sharing_mode="private",
        )
        db.add(dash)
        await db.flush()

        # All widgets reference the temp sensor device for correct values
        sensor_uid = "demo-temp-sensor-01"
        widgets = [
            {"widget_type": "gauge", "variable_key": "demo.temperature", "device_uid": sensor_uid, "label": "Temperature", "unit": "C", "min_value": -20, "max_value": 60, "grid_col": 1, "grid_row": 1, "grid_span_w": 4, "grid_span_h": 3},
            {"widget_type": "gauge", "variable_key": "demo.humidity", "device_uid": sensor_uid, "label": "Humidity", "unit": "%", "min_value": 0, "max_value": 100, "grid_col": 5, "grid_row": 1, "grid_span_w": 4, "grid_span_h": 3},
            {"widget_type": "sparkline", "variable_key": "demo.pressure", "device_uid": "demo-weather-api-01", "label": "Pressure", "unit": "hPa", "grid_col": 9, "grid_row": 1, "grid_span_w": 4, "grid_span_h": 3},
            {"widget_type": "line_chart", "variable_key": "demo.temperature", "device_uid": sensor_uid, "label": "Temperature History", "unit": "C", "grid_col": 1, "grid_row": 4, "grid_span_w": 8, "grid_span_h": 4},
            {"widget_type": "control_slider", "variable_key": "demo.target_temp", "device_uid": sensor_uid, "label": "Target Temp", "unit": "C", "min_value": 10, "max_value": 40, "grid_col": 9, "grid_row": 4, "grid_span_w": 4, "grid_span_h": 4},
            {"widget_type": "control_toggle", "variable_key": "demo.heater_on", "device_uid": sensor_uid, "label": "Heater", "grid_col": 1, "grid_row": 8, "grid_span_w": 4, "grid_span_h": 2},
        ]
        for i, w in enumerate(widgets):
            dw = DashboardWidget(dashboard_id=dash.id, sort_order=i, **w)
            db.add(dw)
        summary["dashboards"] += 1

    # ── 4b. Synthetic History Data (24h of realistic values) ────────────
    from app.db.models.variables import VariableHistory
    import math

    # Only generate if we don't already have enough history
    existing_hist = await db.execute(
        select(func.count()).select_from(VariableHistory).where(
            VariableHistory.variable_key == "demo.temperature"
        )
    )
    hist_count = existing_hist.scalar_one()
    if hist_count < 50 and created_device_ids:
        sensor_id = created_device_ids[0]  # temp sensor
        weather_id = created_device_ids[1] if len(created_device_ids) > 1 else sensor_id
        now = datetime.now(timezone.utc)

        # Generate 24h of data, one point every 10 minutes (144 points)
        for i in range(144):
            t = now - timedelta(minutes=(143 - i) * 10)
            hour_frac = (t.hour + t.minute / 60) / 24
            # Temperature: sinusoidal 18-28°C with daily cycle
            temp = 23 + 5 * math.sin(2 * math.pi * (hour_frac - 0.25)) + random.uniform(-0.5, 0.5)
            # Humidity: inverse of temp, 50-80%
            hum = 65 - 15 * math.sin(2 * math.pi * (hour_frac - 0.25)) + random.uniform(-2, 2)
            # Pressure: slow drift 1008-1018 hPa
            pres = 1013 + 5 * math.sin(2 * math.pi * hour_frac * 0.3) + random.uniform(-0.5, 0.5)

            db.add(VariableHistory(variable_key="demo.temperature", scope="device", device_id=sensor_id, value_json=round(temp, 1), numeric_value=round(temp, 1), recorded_at=t, source="demo"))
            db.add(VariableHistory(variable_key="demo.humidity", scope="device", device_id=sensor_id, value_json=round(hum, 1), numeric_value=round(hum, 1), recorded_at=t, source="demo"))
            db.add(VariableHistory(variable_key="demo.pressure", scope="device", device_id=weather_id, value_json=round(pres, 1), numeric_value=round(pres, 1), recorded_at=t, source="demo"))

        # Target temp: a few step changes over 24h
        for hours_ago, val in [(20, 20.0), (14, 22.0), (8, 24.0), (4, 22.0), (1, 21.0)]:
            t = now - timedelta(hours=hours_ago)
            db.add(VariableHistory(variable_key="demo.target_temp", scope="device", device_id=sensor_id, value_json=val, numeric_value=val, recorded_at=t, source="demo"))

        await db.flush()

    # ── 5. Demo Entity ─────────────────────────────────────────────────────
    entity_id = "demo-lab-room-01"
    existing_entity = await db.execute(select(Entity).where(Entity.entity_id == entity_id))
    if not existing_entity.scalar_one_or_none():
        entity = Entity(
            entity_id=entity_id,
            type="room",
            name="Lab Room 1 (Demo)",
            tags=[DEMO_TAG],
        )
        db.add(entity)
        summary["entities"] += 1

    await db.commit()
    return summary


async def remove_demo(db) -> dict:
    """Remove all demo data."""
    from app.db.models.device import Device
    from app.db.models.variables import VariableDefinition
    from app.db.models.automation import AutomationRule
    from app.db.models.dashboard import Dashboard
    from app.db.models.entities import Entity

    from app.db.models.variables import VariableValue, VariableHistory
    summary = {}

    # Variable history with demo prefix
    res = await db.execute(delete(VariableHistory).where(VariableHistory.variable_key.like("demo.%")))
    summary["history_deleted"] = res.rowcount

    # Variable values with demo prefix (must delete before definitions due to FK)
    res = await db.execute(delete(VariableValue).where(VariableValue.variable_key.like("demo.%")))
    summary["variable_values_deleted"] = res.rowcount

    # Devices with demo uid prefix
    res = await db.execute(delete(Device).where(Device.device_uid.like("demo-%")))
    summary["devices_deleted"] = res.rowcount

    # Variable definitions with demo prefix
    res = await db.execute(delete(VariableDefinition).where(VariableDefinition.key.like("demo.%")))
    summary["variables_deleted"] = res.rowcount

    # Automations with (Demo) in name
    res = await db.execute(delete(AutomationRule).where(AutomationRule.name.like("%(Demo)%")))
    summary["automations_deleted"] = res.rowcount

    # Demo dashboard
    res = await db.execute(delete(Dashboard).where(Dashboard.name == "Demo Dashboard"))
    summary["dashboards_deleted"] = res.rowcount

    # Demo entity
    res = await db.execute(delete(Entity).where(Entity.entity_id.like("demo-%")))
    summary["entities_deleted"] = res.rowcount

    await db.commit()
    return summary


async def _run(args) -> int:
    db_url = os.getenv("HUBEX_DATABASE_URL", "")
    ok = await wait_for_db(db_url, timeout_seconds=30, interval_seconds=1.0)
    if not ok:
        print("ERROR: database not ready")
        return 1

    async with AsyncSessionLocal() as db:
        if args.delete:
            result = await remove_demo(db)
            print(f"Demo data removed: {json.dumps(result)}")
        else:
            result = await seed(db)
            if "error" in result:
                return 1
            print(f"Demo data seeded: {json.dumps(result)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed or remove HUBEX demo data")
    parser.add_argument("--delete", action="store_true", help="Remove demo data instead of seeding")
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
