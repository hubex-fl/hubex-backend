HUBEX Phase-1 Enablement (Slice-2) — Token Revoke (jti denylist)

What it is
- Tokens carry a jti claim.
- Revoked jti values are persisted server-side.
- Revocation is effective immediately (no restart).

Compatibility
- Tokens without jti remain valid and are not revokable.

How to revoke (dev script)
PowerShell:
  $env:HUBEX_TOKEN="<JWT>"
  .\scripts\revoke-token.ps1

Bash:
  export HUBEX_TOKEN="<JWT>"
  ./scripts/revoke-token.sh

Smoke
PowerShell:
  $env:HUBEX_BASE="http://127.0.0.1:8000"
  $env:HUBEX_TOKEN="<JWT>"
  .\scripts\smoke-token-revoke.ps1

Bash:
  export HUBEX_BASE="http://127.0.0.1:8000"
  export HUBEX_TOKEN="<JWT>"
  ./scripts/smoke-token-revoke.sh
