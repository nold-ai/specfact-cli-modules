---
layout: default
title: Govern patch apply
nav_order: 4
permalink: /bundles/govern/patch/
redirect_from:
  - /guides/govern-patch/
keywords: [govern, patch, apply, remediation, fix]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Govern patch apply

`specfact govern patch apply` previews or applies a patch file through the Govern bundle’s explicit write controls.

## Command

- `specfact govern patch apply PATCH_FILE`

## Key options

| Option | Purpose |
|--------|---------|
| `--write` | Apply the patch to the upstream target instead of previewing only |
| `--yes`, `-y` | Confirm an upstream write |
| `--dry-run` | Validate the patch without applying it |

## Examples

```bash
specfact govern patch apply changes.patch --dry-run
specfact govern patch apply changes.patch --write --yes
```

## When to use it

- Review a patch before applying it to a working tree
- Gate an upstream write behind an explicit confirmation step
- Pair patch application with an SDD or review workflow

## Related

- [Govern enforce](/bundles/govern/enforce/)
- [Govern bundle overview](/bundles/govern/overview/)
