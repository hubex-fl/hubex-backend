HUBEX Phase-1 Enablement (Slice-1) — Capability Enforcement Scaffold

Scope
- Central capability registry (single source of truth)
- Route → capability mapping table
- Auth-free public whitelist (minimal, static)
- Enforcement guard (deny-by-default) behind flag

Env flags
- HUBEX_CAPS_ENFORCE=0 (default): report-only, no behavior change
- HUBEX_CAPS_ENFORCE=1: enforce deny-by-default, missing mapping → 403

Public whitelist (auth-free)
- POST /api/v1/devices/hello
- POST /api/v1/pairing/confirm
- POST /api/v1/devices/pairing/confirm

How to extend mapping
1) Add capability to app/core/capabilities.py CAPABILITY_REGISTRY
2) Add route mapping to CAPABILITY_MAP (method, path_template)
3) For auth-free routes only, add to PUBLIC_WHITELIST

How to enable enforcement
PowerShell:
  $env:HUBEX_CAPS_ENFORCE="1"

Bash:
  export HUBEX_CAPS_ENFORCE=1
