---
layout: default
title: Spec generate-tests
nav_order: 4
permalink: /bundles/spec/generate-tests/
redirect_from:
  - /guides/spec-generate-tests/
---

# Spec generate-tests

`specfact spec generate-tests` turns one contract or an entire bundle into runnable Specmatic test suites for downstream API validation.

## Command

- `specfact spec generate-tests [SPEC_PATH]`

## Key options

| Option | Purpose |
|--------|---------|
| `--bundle <name>` | Generate tests for every contract in a bundle |
| `--output`, `--out` | Choose the output directory instead of `.specfact/specmatic-tests/` |
| `--force` | Rebuild generated tests even when the cache says inputs are unchanged |

## Typical flow

1. Validate the contract first.
2. Generate the test suite into a repo-local directory.
3. Run the generated tests in CI or against a staging environment.

## Examples

```bash
specfact spec generate-tests api/openapi.yaml
specfact spec generate-tests api/openapi.yaml --output tests/specmatic/
specfact spec generate-tests --bundle legacy-api --output tests/contract/
specfact spec generate-tests --bundle legacy-api --force
```

## Bundle-owned resources

Generated tests come from the installed Spec bundle version. Keep the bundle version and any IDE exports in sync with `specfact init ide` when your team relies on prompt-assisted contract workflows.

## Related

- [Spec validate and backward compatibility](validate/)
- [Spec bundle overview](overview/)
