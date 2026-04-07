# Changelog

All notable changes to HubEx will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-04-07

### Added
- **Core Platform**: Device Management (4 types), Variable System (20+ semantic types), Dashboard Builder (9 widget types)
- **Automation Engine**: 7 triggers, 7 actions, AND/OR condition groups, cron schedules, email templates
- **Security**: RBAC (6 roles), JWT auth, 2FA (TOTP), API keys (scoped), session management
- **Dashboard Features**: Public embed (token + PIN), Kiosk mode, White-Label branding
- **Data Management**: Export/Import (JSON), Reports (HTML), Variable history with retention
- **Monitoring**: System Health, Trace Timeline, Anomaly Detection (z-score), Audit Log
- **Hardware Concepts**: Board profiles (ESP32/S3/C3/Pico), Shield definitions, Component library (15 sensors/actuators), Code generator templates
- **Integrations**: Webhooks, Custom API Builder, Plugin framework, MCP server
- **UI**: 25+ pages, Dark/Light mode, i18n (EN/DE), PWA manifest, responsive sidebar
- **Scaling**: Partitioning, Redis Streams (optional), configurable pool sizes

### Security
- CORS configurable via environment variable
- XSS mitigated (sandboxed iframes for user-generated HTML)
- SQL injection protected (parameterized queries + regex validation)
- Security headers (HSTS, X-Frame-Options, X-Content-Type-Options)

### API Versioning Policy
- API v1 (`/api/v1/`) is stable
- Breaking changes only in major versions (v2)
- Deprecation warnings 6 months before removal

### Semantic Versioning
- MAJOR: Breaking API changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, security patches
