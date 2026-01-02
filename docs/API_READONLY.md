# API Read-Only Catalog

This document lists read-only endpoints and required capabilities. It reflects the current codebase and is additive-only.

## Devices
- GET /api/v1/devices - cap: devices.read - list devices
- GET /api/v1/devices/{device_id} - cap: devices.read - device detail
- GET /api/v1/devices/lookup/{device_uid} - cap: devices.read - device lookup
- GET /api/v1/devices/whoami - cap: devices.read - device identity (auth)
- GET /api/v1/devices/{device_id}/telemetry/recent - cap: telemetry.read - recent telemetry
- GET /api/v1/devices/{device_id}/telemetry - cap: telemetry.read - telemetry list (if enabled)
- POST /api/v1/devices/hello - cap: devices.hello - device hello/provision
- POST /api/v1/devices/{device_id}/tasks - cap: tasks.write - enqueue task
- POST /api/v1/devices/{device_id}/tasks/{task_id}/cancel - cap: tasks.write - cancel task

## Tasks (read)
- GET /api/v1/devices/{device_id}/tasks - cap: tasks.read - list tasks
- GET /api/v1/devices/{device_id}/current-task - cap: tasks.read - current task
- GET /api/v1/devices/{device_id}/task-history - cap: tasks.read - task history
- POST /api/v1/tasks/context/heartbeat - cap: tasks.write - client context heartbeat
- POST /api/v1/tasks/poll - cap: tasks.read - client poll
- POST /api/v1/tasks/{task_id}/complete - cap: tasks.write - client complete
- POST /api/v1/tasks/{task_id}/renew - cap: tasks.write - client renew

## Variables (read)
- GET /api/v1/variables/definitions - cap: vars.read - list definitions
- GET /api/v1/variables/defs - cap: vars.read - list definitions (alias)
- GET /api/v1/variables/value - cap: vars.read - get value
- GET /api/v1/variables/device/{device_uid} - cap: vars.read - effective device+global values
- GET /api/v1/variables/effective - cap: vars.read - effective snapshot
- GET /api/v1/variables/snapshot - cap: vars.read - snapshot v3
- GET /api/v1/variables/applied - cap: vars.read - applied ack list
- GET /api/v1/variables/audit - cap: vars.read - audit list
- GET /api/v1/variables/effects - cap: vars.read - variables effect trace
- GET /api/v1/variables/effects/{effect_id} - cap: vars.read - effect trace detail
- POST /api/v1/variables/definitions - cap: vars.write - create definition
- POST /api/v1/variables/defs - cap: vars.write - create definition (alias)
- PUT /api/v1/variables/value - cap: vars.write - set value
- POST /api/v1/variables/set - cap: vars.write - set value (v2)
- POST /api/v1/variables/applied - cap: vars.ack - applied ack
- POST /api/v1/variables/ack - cap: vars.ack - ack (v3)
- POST /api/v1/variables/effects/run-once - cap: vars.write - run effects once (dev)

## Auth
- POST /api/v1/auth/register - cap: core.auth.register - register
- POST /api/v1/auth/login - cap: core.auth.login - login
- GET /api/v1/users/me - cap: users.read - current user

## Entities v1
- GET /api/v1/entities - cap: entities.read - list entities
- GET /api/v1/entities/{entity_id} - cap: entities.read - entity detail
- GET /api/v1/entities/{entity_id}/devices - cap: entities.read - bindings

## Events v1
- GET /api/v1/events - cap: events.read - cursor-based event read
- GET /api/v1/events/{event_id} - cap: events.read - event by id
- POST /api/v1/events/ack - cap: events.ack - cursor ack

## Effects v1
- GET /api/v1/effects - cap: effects.read - effects trace list
- GET /api/v1/effects/{effect_id} - cap: effects.read - effect by id

## Audit v1
- GET /api/v1/audit - cap: audit.read - audit list
- GET /api/v1/audit/{entry_id} - cap: audit.read - audit entry

## Secrets v1 (metadata-only)
- GET /api/v1/secrets - cap: secrets.read - list secrets (metadata only)
- GET /api/v1/secrets/{secret_id} - cap: secrets.read - secret metadata

## Config v1 (metadata-only)
- GET /api/v1/config - cap: config.read - list config (metadata only)
- GET /api/v1/config/{config_id} - cap: config.read - config metadata

## Pairing
- POST /api/v1/pairing/start - cap: pairing.start - start pairing
- POST /api/v1/pairing/confirm - cap: pairing.confirm - confirm pairing
- POST /api/v1/devices/pairing/start - cap: pairing.start - legacy alias
- POST /api/v1/devices/pairing/confirm - cap: pairing.confirm - legacy alias

## Telemetry
- POST /api/v1/telemetry - cap: telemetry.emit - ingest telemetry
- GET /api/v1/telemetry/recent - cap: telemetry.read - recent telemetry

Notes:
- "metadata-only" endpoints never return secret/config values.
- All non-whitelisted routes are capability-gated deny-by-default when HUBEX_CAPS_ENFORCE=1.
