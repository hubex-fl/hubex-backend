---
marp: true
theme: uncover
class: invert
paginate: true
---

# HUBEX

## The Universal IoT Device Hub

Open-Source | Self-Hosted | API-First

<!-- notes
Opening slide. Emphasize: "universal" — not just ESP32, not just smart home.
HUBEX handles everything from microcontrollers to cloud agents, all through one unified platform.
-->

---

## The Problem

Every IoT startup rebuilds the same device backend from scratch.

- **$50K+ engineering cost** just for device management basics
- **3-6 months** before the first device sends data reliably
- **Vendor lock-in**: AWS IoT Core = cloud-only, pay-per-message
- **Fragmented stack**: separate tools for devices, telemetry, alerts, OTA, dashboards
- **No standard**: every team invents their own pairing, auth, and update protocol

> 80% of IoT backend work is commodity infrastructure, not product differentiation.

<!-- notes
Pain point: talk to any IoT startup founder. They all say the same thing —
"We spent 6 months building device management before we could work on our actual product."
This is wasted engineering. HUBEX eliminates it.
-->

---

## The Solution

**HUBEX** — plug-and-play IoT backend. From zero to first device in under 1 hour.

| What you get | How long it takes |
|---|---|
| Device pairing + authentication | 5 minutes |
| Real-time telemetry ingestion | 10 minutes |
| Variable streams + visualization | 15 minutes |
| Alerts + automation rules | 20 minutes |
| OTA firmware updates | 30 minutes |
| Full production deployment (Docker + SSL) | 1 hour |

**One platform. Every device type. Self-hosted.**

<!-- notes
Key message: HUBEX is not a prototype — it's a production-grade platform
that replaces 5-6 separate tools. The 1-hour claim is real:
Docker Compose up, pair a device, see data flowing.
-->

---

## What HUBEX Can Do

**Dashboard** — Mission Control with live metrics, device health ring, event streams

**Variable Streams** — Grafana-style real-time monitoring with sparklines, gauges, charts

**Automations** — Native If-Then rules: variable thresholds, geofence, device offline triggers

**OTA Updates** — Staged rollouts (immediate, canary, percentage-based) with rollback

**Multi-Tenancy** — Organizations, capability-based security, plan limits

**n8n Integration** — Connect to 1000+ services via custom n8n nodes

<!-- notes
Walk through each feature briefly. Mention that all of these are built-in,
not plugins. The n8n integration is a separate npm package that ships with HUBEX.
Variable Streams are the "wow moment" — Grafana-quality visualization built in.
-->

---

## How It Works

```
1. DEPLOY     Docker Compose up (5 min)
      |
2. PAIR       Device sends hello -> gets token (QR or API)
      |
3. TELEMETRY  Device pushes data -> auto-bridges to variables
      |
4. VISUALIZE  Variable Streams show real-time charts
      |
5. AUTOMATE   If temperature > 40C -> send webhook -> n8n -> email
      |
6. SCALE      Add orgs, devices, users — capability-gated
```

**Works with:** ESP32, Raspberry Pi, Linux agents, Windows services, REST APIs, MQTT bridges

<!-- notes
The flow is simple and linear. No complex setup wizards.
Emphasize the Telemetry Bridge — data flows automatically from device
telemetry into typed variables. No manual mapping needed.
-->

---

## Architecture

```
                    +------------------+
                    |    Vue 3 SPA     |  Tailwind + Mission Control UI
                    +--------+---------+
                             |
                    +--------+---------+
                    |    FastAPI        |  Async Python, 150+ endpoints
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
     +--------+--+   +------+-----+  +-----+------+
     | PostgreSQL |   |   Redis    |  |   Workers   |
     | (Data)     |   | (Cache,    |  | (Alerts,    |
     |            |   |  Rate Lim) |  |  OTA, Health)|
     +------------+   +------------+  +-------------+
```

**Stack:** Python 3.11+ | FastAPI | SQLAlchemy async | PostgreSQL | Redis | Vue 3 | Tailwind CSS

<!-- notes
Architecture is intentionally simple. No Kafka, no Kubernetes required.
PostgreSQL + Redis handle everything. Workers run as async background tasks.
This makes HUBEX deployable on a $5/month VPS — not just on AWS.
-->

---

## Market Opportunity

**IoT Platform Market: $15B+ by 2027** (Growing 25% CAGR)

| Segment | Size | HUBEX Fit |
|---------|------|-----------|
| Industrial IoT startups | $4B | Direct replacement for custom backends |
| Smart building / facility | $3B | Multi-tenant, multi-device |
| Agricultural IoT | $2B | Self-hosted, offline-capable |
| Maker / prototyping | $1B | Free tier, instant setup |
| Edge computing | $5B | Agent SDK + Bridge framework |

**Target customers:** IoT startups (Series A/B), system integrators, hardware companies adding software, R&D labs

<!-- notes
The market is massive and fragmented. Most IoT startups use either
AWS IoT (expensive, complex) or build from scratch (slow, risky).
HUBEX sits in the sweet spot: production-grade but accessible.
-->

---

## Competitive Landscape

| Feature | HUBEX | AWS IoT | ThingsBoard | Home Assistant | Datacake |
|---------|-------|---------|-------------|----------------|----------|
| Self-hosted | Yes | No | Complex | Yes | No |
| API-first | REST + MCP | SDK-heavy | REST (legacy) | YAML | Limited |
| Device types | All (MCU+Agent+API+Bridge) | MCU/Gateway | MQTT/HTTP | Consumer | LoRa/NB-IoT |
| Automations | Native + n8n | Lambda | Rule Chains | YAML | Webhooks |
| Setup time | 1 hour | Days | Hours | Hours | Minutes |
| Pricing | Free/Open Source | Pay-per-msg | Free/Expensive PE | Free | Per-device |
| Multi-tenant | Built-in | IAM | Yes | No | Yes |
| OTA updates | Built-in | Partial | No | No | No |

<!-- notes
Key differentiators to emphasize:
1. Only platform that supports ALL device types natively
2. Self-hosted AND production-grade (ThingsBoard is self-hosted but Java/heavy)
3. Native automation engine — no Lambda/external tools needed
4. MCP-ready — first IoT platform with AI agent support
-->

---

## Business Model: Open Core

| | Free | Pro ($29/mo) | Enterprise |
|---|---|---|---|
| Devices | 5 | 50 | Unlimited |
| Organizations | 1 | 3 | Unlimited |
| Variable history | 7 days | 90 days | 1 year+ |
| Automations | 5 rules | Unlimited | Unlimited |
| Support | Community | Priority | Dedicated + SLA |
| Features | All core | + Geofence, n8n templates | + SSO, white-label |

**Revenue streams:** SaaS subscriptions, managed hosting, enterprise support, marketplace (future)

<!-- notes
The Free tier is generous enough to build a real product.
Pro is priced for startups — cheaper than one AWS IoT bill.
Enterprise is custom-priced for companies that need SLA and SSO.
All tiers can self-host. Pro/Enterprise add features, not paywalls on core.
-->

---

## Traction & Status

**Built and working today:**

- 150+ API endpoints (fully documented, OpenAPI spec)
- 17 custom UI components (Mission Control design system)
- 69 granular capabilities (security model)
- 4 integration demos (ESP32, API device, MQTT bridge, n8n)
- Full CI/CD pipeline (GitHub Actions, Docker production compose)
- Developer documentation (Getting Started, SDK, Integration Guide)

**Phases completed:** Core Platform, UI Mission Control, Variable Data Hub, Integration & Demo

**Code quality:** TypeScript frontend, async Python backend, structured logging, rate limiting, caching

<!-- notes
This is not a prototype. 4 of 6 phases are complete.
The platform is functional and can demo end-to-end:
device pairing -> telemetry -> variables -> alerts -> webhooks -> n8n.
-->

---

## Roadmap: Next 6 Months

| Quarter | Milestone | Impact |
|---------|-----------|--------|
| **Q2 2026** | WebSocket real-time layer | Live variable streams without polling |
| **Q2 2026** | MCP Server integration | AI agents control devices natively |
| **Q3 2026** | Provider/Signal system | Plugin-based data ingestion |
| **Q3 2026** | Rules Engine v2 | Signal-driven automations with versioning |
| **Q4 2026** | Universal Agent SDK | Python/Node.js agents for RPi, Linux, Windows |
| **Q4 2026** | Dashboard Builder | Drag-and-drop custom interfaces |

**Phase 5 (Platform Extension)** and **Phase 6 (Enterprise)** are fully planned with 15 milestones.

<!-- notes
The roadmap is concrete — every milestone has defined steps with time estimates.
MCP integration is the next big differentiator: "AI agents that control your IoT devices."
The Dashboard Builder reuses the existing VizWidget system from Variable Streams.
-->

---

## Team & Opportunity

**Current:** Solo founder / full-stack developer

**Looking for:**
- **Technical co-founder / CTO** — Backend scaling, DevOps, security
- **Early adopters** — IoT startups willing to beta-test with real hardware
- **Partners** — System integrators, hardware manufacturers
- **Investment** — Pre-seed to accelerate Phase 5-6 development

**Open Source advantage:** Community contributions, trust, adoption velocity

<!-- notes
Be transparent about being solo. The codebase quality speaks for itself —
150+ endpoints, 17 UI components, 4 phases complete.
The ask is specific: co-founder, early adopters, or pre-seed funding.
-->

---

## The Ask

### What we need

1. **Early Adopters** — 5-10 IoT teams to deploy HUBEX in production
2. **Technical Partners** — Hardware companies that need a device backend
3. **Pre-Seed Investment** — EUR 150K to hire 2 engineers, accelerate roadmap

### What you get

- **Early adopters:** Free Enterprise tier for 12 months + direct feature input
- **Partners:** Co-development, white-label option, joint go-to-market
- **Investors:** Ground floor of a platform play in a $15B+ market

**Contact:** [GitHub] | [Email] | [Demo Instance]

<!-- notes
Close with clear, specific asks. Not vague "we need help" but concrete:
5-10 beta teams, hardware partners, 150K pre-seed.
Offer real value in return: free Enterprise, co-development, early equity.
-->

---

## Thank You

### HUBEX — The Universal IoT Device Hub

> From ESP32 to enterprise server — one protocol, one platform, one hour to deploy.

**GitHub:** github.com/hubex-iot/hubex
**Docs:** docs.hubex.io
**Demo:** demo.hubex.io

<!-- notes
End with the tagline. Leave URLs on screen.
Offer live demo if there's time — show device pairing flow.
-->
