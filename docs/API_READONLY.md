# API Read-Only Catalog

This document lists read-only endpoints and required capabilities. It reflects the current codebase and is additive-only.

## Devices
- GET /api/v1/devices — cap: devices.read — list devices
- GET /api/v1/devices/{device_id} — cap: devices.read — device detail
- GET /api/v1/devices/lookup/{device_uid} — cap: devices.read — device lookup
- GET /api/v1/devices/whoami — cap: devices.read — device identity (auth)
- GET /api/v1/devices/{device_id}/telemetry/recent — cap: telemetry.read — recent telemetry
- GET /api/v1/devices/{device_id}/telemetry — cap: telemetry.read — telemetry list (if enabled)

## Tasks (read)
- GET /api/v1/devices/{device_id}/tasks — cap: tasks.read — list tasks
- GET /api/v1/devices/{device_id}/current-task — cap: tasks.read — current task
- GET /api/v1/devices/{device_id}/task-history — cap: tasks.read — task history

## Variables (read)
- GET /api/v1/variables/definitions — cap: vars.read — list definitions
- GET /api/v1/variables/defs — cap: vars.read — list definitions (alias)
- GET /api/v1/variables/value — cap: vars.read — get value
- GET /api/v1/variables/device/{device_uid} — cap: vars.read — effective device+global values
- GET /api/v1/variables/effective — cap: vars.read — effective snapshot
- GET /api/v1/variables/snapshot — cap: vars.read — snapshot v3
- GET /api/v1/variables/applied — cap: vars.read — applied ack list
- GET /api/v1/variables/audit — cap: vars.read — audit list
- GET /api/v1/variables/effects — cap: vars.read — variables effect trace
- GET /api/v1/variables/effects/{effect_id} — cap: vars.read — effect trace detail

## Entities v1
- GET /api/v1/entities — cap: entities.read — list entities
- GET /api/v1/entities/{entity_id} — cap: entities.read — entity detail
- GET /api/v1/entities/{entity_id}/devices — cap: entities.read — bindings

## Events v1
- GET /api/v1/events — cap: events.read — cursor-based event read
- GET /api/v1/events/{event_id} — cap: events.read — event by id

## Effects v1
- GET /api/v1/effects — cap: effects.read — effects trace list
- GET /api/v1/effects/{effect_id} — cap: effects.read — effect by id

## Audit v1
- GET /api/v1/audit — cap: audit.read — audit list
- GET /api/v1/audit/{entry_id} — cap: audit.read — audit entry

## Secrets v1 (metadata-only)
- GET /api/v1/secrets — cap: secrets.read — list secrets (metadata only)
- GET /api/v1/secrets/{secret_id} — cap: secrets.read — secret metadata

## Config v1 (metadata-only)
- GET /api/v1/config — cap: config.read — list config (metadata only)
- GET /api/v1/config/{config_id} — cap: config.read — config metadata

Notes:
- “metadata-only” endpoints never return secret/config values.
- All non-whitelisted routes are capability-gated deny-by-default when HUBEX_CAPS_ENFORCE=1.
