# Phase-1 Rate Limit Slice (MVP)

Purpose: opt-in, in-memory rate limiting to return 429 under load instead of failing.

Enable:
- PowerShell: `$env:HUBEX_RL_ENABLED="1"`
- Bash: `export HUBEX_RL_ENABLED=1`

Configuration:
- `HUBEX_RL_PER_MIN` (default 60)

Behavior:
- Applies after auth + capability guard.
- Key: `subject_id + method + route_template`.
- When exceeded: HTTP 429 with `{"detail":"rate_limited"}` and `Retry-After` seconds.

Caveats:
- In-memory per-process only (no shared state across instances).
