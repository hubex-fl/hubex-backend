---
name: HUBEX Product Direction
description: Strategic product direction — universal device hub, Sprint Track focus, plugin ecosystem
type: project
---

HUBEX positioning: "Open-Source Device Hub for Product Builders" — not a Home Assistant clone,
not an AWS IoT competitor. It's the device backend stack that every IoT startup builds from
scratch, delivered as a ready-made platform.

**Why:** User wants to build a product-builder tool, not copy existing solutions. Differentiators:
self-hosted, API-first, protocol-agnostic, deterministic state, capability-based security,
lightweight-by-default but extensible via feature-flag-gated "heavy" modules.

**Current direction (post Sprint 3):**
- Core platform is shipped (Phases 1-9). Now iterating via numbered Sprint Track.
- **Lightweight default, opt-in heavy features**: new feature flags (`orchestrator`, soon
  `firmware_builder`) gate anything that requires extra infrastructure (Docker, PlatformIO).
  Users who don't need it pay zero install cost.
- **Plugin ecosystem via Portainer, not docker.sock**: HubEx never touches the Docker socket
  directly. Sprint 3 added a generic `portainer_client.py` that all future "spawn a container"
  features (firmware build, sandboxed agents, etc.) reuse.
- **Two plugin kinds**: Service (Docker container, embedded via iframe) and Connector (API
  credentials only, consumed by other subsystems like AI Coop, automation actions).
- Automation engine stays IF/THEN + cron — complex automation still delegated to n8n via
  webhooks. n8n ships as the v1 service plugin (adopted, not duplicated).
- Events v1 is the central message bus for webhooks and integrations.

**Upcoming directional decisions:**
- Sprint 4: firmware_builder follows the Sprint 3 pattern (feature-flag + portainer sidecar)
- Phase 10: Commercialization — License system (Ed25519 per docs/EDITIONS.md), CE/EE gating
- Marketplace (post Phase 10): remote plugin catalog replacing the hardcoded `plugin_catalog.py`
