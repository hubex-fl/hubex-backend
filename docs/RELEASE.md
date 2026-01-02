# RELEASE

Phase-1 is feature-frozen. This file defines release hygiene only.

## What feature-frozen means
- No new APIs or contracts.
- No semantic changes.
- Only docs/hygiene/gates and bugfixes allowed.

## Tagging (phase1-YYYYMMDD)
1) Ensure the repo is clean.
2) Run Phase-1 gates locally (runner must be green).
3) Verify OpenAPI snapshot is unchanged.
4) Verify alembic has a single head.
5) Tag:
   - `git tag phase1-YYYYMMDD`
   - `git push --tags`

## Pre-tag checklist
- Phase-1 gates pass (local or CI).
- `scripts/check_feature_frozen_marker.py` passes.
- OpenAPI snapshot check passes.
- Alembic single head check passes.
