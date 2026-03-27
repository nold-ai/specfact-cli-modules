---
layout: default
title: Spec validate and backward compatibility
nav_order: 3
permalink: /bundles/spec/validate/
redirect_from:
  - /guides/spec-validate/
  - /guides/spec-backward-compat/
---

# Spec validate and backward compatibility

Use the Spec bundle to validate OpenAPI or AsyncAPI contracts with Specmatic and to compare two contract revisions before release.

## Commands

- `specfact spec validate [SPEC_PATH]`
- `specfact spec backward-compat OLD_SPEC NEW_SPEC`

## What `specfact spec validate` does

- Validates one contract file or every contract in a selected bundle.
- Uses Specmatic for schema checks and example validation.
- Supports bundle-driven validation with the active plan from `specfact plan select`.
- Caches validation results in `.specfact/cache/specmatic-validation.json` unless you pass `--force`.

## Key options for `specfact spec validate`

| Option | Purpose |
|--------|---------|
| `--bundle <name>` | Validate all bundle contracts instead of a single file |
| `--no-interactive` | Disable contract selection prompts for CI/CD |
| `--force` | Re-run validation even when the cache says nothing changed |

## What `specfact spec backward-compat` does

- Compares an older and newer contract version.
- Flags breaking changes before they reach consumers.
- Works best in release checks or pre-merge validation.

## Examples

```bash
specfact spec validate api/openapi.yaml
specfact spec validate api/openapi.yaml --previous api/openapi.v1.yaml
specfact spec validate --bundle legacy-api
specfact spec validate --bundle legacy-api --force
specfact spec backward-compat api/openapi.v1.yaml api/openapi.v2.yaml
```

## Bundle-owned resources

Validation itself does not depend on exported IDE prompts, but the contract workflows around the Spec bundle still ship from the installed module version. Refresh IDE assets with `specfact init ide` after upgrading the bundle so surrounding prompt-driven flows stay aligned with the command behavior.

## Related

- [Spec bundle overview](overview/)
- [Generate Specmatic tests](generate-tests/)
- [Run a mock server](mock/)
