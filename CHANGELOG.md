# Changelog

All notable changes to HUBEX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-04-08

### Added

**Core Platform**
- Device Management with 4 device types: Hardware, Service, Bridge, Agent
- Variable System with 20+ semantic types, type icons, units, and direction (read/write/read-write)
- Auto-Discovery: telemetry payloads automatically create typed variable definitions
- Entity/Group system with hierarchical bindings and health aggregation
- Multi-Tenancy: Organizations, members, plan limits, tenant hierarchy

**Automation Engine**
- Visual If/Then automation builder with 7 triggers and 7 actions
- Triggers: threshold, variable_change, device_online, device_offline, schedule (cron), geofence, event
- Actions: set_variable, webhook, send_notification, log_to_audit, send_email, device_command, log
- AND/OR condition groups with nested conditions
- Cooldown, cron scheduling, test-run capability
- Computed Variables with formula evaluation (safe-eval, reactive + cron modes)

**Dashboard System**
- Dashboard Builder with 9 widget types: line_chart, sparkline, gauge, boolean, toggle, slider, log, map, text
- Drag-and-drop widget reordering with 12-column grid layout
- Dashboard sharing: public links, PIN-protected, token-authenticated
- Dashboard sets, cloning, embed mode, kiosk slideshow, homepage override
- HTML widget for custom content (sandboxed iframe)
- Widget auto-suggest based on variable semantic type

**Security**
- RBAC with 6 roles: owner, admin, operator, viewer, device, api_key
- JWT authentication with refresh tokens
- 2FA/MFA via TOTP with recovery codes
- Scoped API key management (hbx_ prefix)
- Session management with user-agent/IP tracking
- Security headers: HSTS, X-Frame-Options, X-Content-Type-Options
- CORS configurable via environment variable
- XSS mitigation (sandboxed iframes for user-generated HTML)

**Observability**
- System Health dashboard (DB, Redis, devices, alerts)
- Trace Timeline with correlated events, audit, alerts, automations
- Anomaly Detection (z-score based on variable history)
- Incident Summary (active alerts, offline devices, errors)
- Support Bundle export (JSON diagnostic snapshot)
- Audit Log with full CRUD tracking and CSV/JSON export

**Data & Analytics**
- Variable History with time-series storage and SQL downsampling
- History retention policies (configurable days)
- Data export: Variables, Events, Audit as CSV/JSON
- Variable Snapshots for point-in-time state capture
- Report Generator with HTML output, scheduling, email delivery

**Integrations**
- Webhook system with HMAC signatures, retry logic, delivery history
- Custom API Builder: visual endpoint configuration with rate limiting
- MCP Server: 15 tools for device, variable, alert, automation, dashboard operations
- Plugin Framework with sandboxed execution and capability gating
- n8n integration: custom node with device, variable, automation, dashboard resources
- Agent SDK (Python): heartbeat, telemetry, collectors (CPU, memory, disk, network)
- Bridge/Gateway framework with Serial, Modbus, BLE plugin stubs

**System Map & Flow Editor**
- Node-graph visualization: Device > Variables > Alerts/Automations
- Editable Flow Editor (n8n-style): 6 node types, drag-to-connect, inspector panel
- Auto-load from API with initial graph layout

**Tour Engine**
- Guided camera tours with spotlight overlay and autoplay
- Custom tour builder for admin-created walkthroughs

**Email & Notifications**
- Email Template Editor with HTML preview and variable placeholders
- 4 built-in templates: Alert Notification, Daily Report, Welcome, Device Offline
- SMTP configuration via environment variables

**Admin & Management**
- Admin Console with module lifecycle, status overview, system info
- Config Export/Import (dashboards, automations, variables, alerts, semantic types)
- White-Label branding (product name, logo, colors configurable)
- Feedback Widget (in-app bug/feature reporting)

**UI & UX**
- 25+ pages with consistent "Warm Depth" design system
- Dark/Light mode with theme persistence
- i18n with English and German translations (complete coverage)
- Progressive Disclosure throughout (collapsible panels, tooltips, contextual hints)
- Command Palette (Cmd+K) for global search and navigation
- Add Device Wizard with 4 guided flows (Hardware, Service, Bridge, Agent)
- Getting Started onboarding guide (5-step, dismissible)
- PWA manifest with responsive layout (sidebar hamburger on mobile)
- Contextual navigation: from any element to related alerts, automations, devices

**Hardware Concepts** (models and APIs, implementation in Phase 11)
- Board Profiles (ESP32, ESP32-S3, ESP32-C3, Pico W)
- Shield definitions and pin configurations
- Component Library with 15 sensor/actuator/module manifests
- Code Generator templates for firmware scaffolding
- Retrofit Profiles and Edge Logic definitions

**Device Simulators**
- ESP32, API-Poll, MQTT-Bridge, and Agent simulators
- Fleet launcher (all 4 in parallel)
- Advanced simulator with task execution, alert triggering, geofence movement, burst mode

**Production Deployment**
- Docker Compose for production (PostgreSQL + Redis + Backend + Frontend)
- Full-stack Compose with n8n + Portainer companion
- One-line install script with .env generator
- Backup/restore scripts (pg_dump, 30-day retention)
- Alembic migration system (48 migrations)
- Health/Ready endpoints with Docker HEALTHCHECK

**Documentation**
- Quick-Start Guide, User Guide, Operator Runbook, API Guide, FAQ
- Scaling Guide, Bridge Protocol spec, Release Process
- CE/EE Feature Matrix with pricing model
- Video tutorial plan (10 scripts)
- Community guide, Contributing guide, Code of Conduct

**Legal & Licensing**
- AGPL v3 license for Community Edition
- Commercial license option documented

### Fixed
- Dashboard widget edit bug (widget config not loading in edit modal)
- Telemetry bridge device_writable filter blocking variable values
- Semantic Types page broken after route changes
- Modal scrolling issues (max-height with overflow)
- Variable slider scroll-to-top bug
- Gauge widget SVG viewBox cutoff
- nginx proxy missing /ready, /docs, /redoc, /openapi.json routes
- Dockerfile COPY with invalid shell redirect
- vue-i18n downgraded from v12-alpha to v11.3.1 (stable)
- Register IntegrityError handling and variable type mismatch
- Auto-create all DB tables on startup (Base.metadata.create_all)
- Device list online status showing incorrectly
- Sidebar default state flash on page load
- Devices page Error+Empty state overlap
- Alert acknowledge backend logic (409 on non-firing status)
- GPS/Map widget: Leaflet CSS import, marker icon paths, container sizing, resize handling, null coordinate graceful fallback

### Changed
- Sidebar restructured into 3 collapsible groups (Top, Data & Logic, System)
- Design system migrated to "Warm Depth" tokens (Amber/Gold primary, Teal accent)
- All entity reference fields now use selectors instead of ID text inputs
- Flow Editor renamed from "System Map" for clarity
- Dashboard Builder rebuilt with proper drag-and-drop and sharing UI

### Security
- OWASP Top 10 audit completed (SQL injection, XSS, CSRF, auth bypass, input validation)
- Self-hosting tested on real VPS (hubextest.tech)
- .env removed from git repository

### API Versioning Policy
- API v1 (`/api/v1/`) is stable
- Breaking changes only in major versions (v2)
- Deprecation warnings 6 months before removal

### Semantic Versioning
- MAJOR: Breaking API changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, security patches
