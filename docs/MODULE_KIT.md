# Module Kit (MIC v1)

This guide standardizes module creation so new modules are fast, consistent, and capability-gated.
No new public contracts are introduced by this kit.

## Create a New Module
1) Copy `modules/_template` to `modules/<module_key>`.
2) Update `module.json`:
   - `key`, `name`, `version`
   - capabilities in the form `module.<module_key>.<resource>.<action>`
3) Update `config.schema.json` (optional) to reflect configuration needs.

## Example
See `modules/rules_min` for a minimal, MIC-compliant example.

## Required Capabilities
Use the prefix:
```
module.<module_key>.<resource>.<action>
```

## Local Testing
- Ensure capability enforcement is enabled (`HUBEX_CAPS_ENFORCE=1`) in dev.
- Verify the UI remains read-only and capability-gated.

## Forbidden
- No core bypasses.
- No optimistic UI.
- No hidden defaults or side-effect logic.
