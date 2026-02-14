# Module Template (MIC v1)

Use this folder as the starting point for new MIC modules.
Do not add new public contracts without an SSOT update.

## Lifecycle
install → configure → enable → disable → revoke → uninstall

## Capability naming (recommended)
`module.<module_key>.<resource>.<action>`

Examples:
- `module.rules_min.read`
- `module.rules_min.write`

## Files
- `module.json`: metadata (key/name/version/caps)
- `config.schema.json`: example config schema stub
- Optional code package (keep internal-only unless SSOT updated)
