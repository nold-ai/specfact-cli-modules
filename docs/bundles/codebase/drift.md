---
layout: default
title: Code drift detect
nav_order: 4
permalink: /bundles/codebase/drift/
redirect_from:
  - /guides/code-drift-detect/
---

# Code drift detect

`specfact code drift detect` scans a repository and bundle pair for implementation drift, orphaned specs, and missing test coverage.

## Command

- `specfact code drift detect [BUNDLE]`

## Key options

| Option | Purpose |
|--------|---------|
| `--repo <path>` | Select the repository to scan |
| `--format <table\|json\|yaml>` | Choose the report format |
| `--out <path>` | Write JSON or YAML output to a file |

## What it checks

- Added or removed implementation files
- Modified implementation hashes
- Orphaned specs
- Missing tests or contract alignment gaps

## Examples

```bash
specfact code drift detect legacy-api --repo .
specfact code drift detect my-bundle --repo . --format json --out drift-report.json
```

## Related

- [Code analyze contracts](analyze/)
- [Code repro](repro/)
