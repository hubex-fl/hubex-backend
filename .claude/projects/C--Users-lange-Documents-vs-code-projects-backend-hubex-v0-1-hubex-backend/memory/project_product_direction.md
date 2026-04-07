---
name: HUBEX Product Direction
description: Strategic product direction - Hardware-Software Interface Hub, n8n delegation, connector architecture
type: project
---

HUBEX positioning: "Open-Source Device Hub for Product Builders" — not a Home Assistant clone, not an AWS IoT competitor. It's the device backend stack that every IoT startup builds from scratch, delivered as a ready-made platform.

**Why:** User wants to build a specific tool for product building, not copy existing solutions. Key differentiators: self-hosted, API-first, protocol-agnostic connectors, deterministic state management, capability-based security.

**How to apply:**
- Automation engine stays basic (IF/THEN rules + cron) — complex automation delegated to n8n/Node-RED via webhooks
- Connector architecture is the next big architectural step (MQTT, WebSocket, BLE, Serial)
- Device Twins (reported/desired/effective state) replace the current Variables system
- Existing Provider/Signal scaffolding becomes the Connector adapter layer
- Events v1 becomes the central message bus for webhooks and integrations
- Roadmap documented in docs/PRODUCT_VISION.md
- Business pitch in docs/PITCH.md
