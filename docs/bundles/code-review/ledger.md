---
layout: default
title: Code review ledger
nav_order: 4
permalink: /bundles/code-review/ledger/
redirect_from:
  - /guides/code-review-ledger/
keywords: [code-review, ledger, history, tracking, audit]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Code review ledger

The ledger commands persist and inspect the local reward history produced by review runs.

## Commands

- `specfact code review ledger status`
- `specfact code review ledger update`
- `specfact code review ledger reset`

## Subcommands

| Command | Purpose |
|--------|---------|
| `specfact code review ledger status` | Print the current coins, streaks, and last verdict |
| `specfact code review ledger update --from <path>` | Update the ledger from a `ReviewReport` JSON file instead of stdin |
| `specfact code review ledger reset --confirm` | Delete the local fallback ledger |

## Examples

```bash
specfact code review ledger status
specfact code review run --json --out /tmp/review-report.json packages/specfact-code-review/src/specfact_code_review/run/commands.py
specfact code review ledger update --from /tmp/review-report.json
specfact code review ledger reset --confirm
```

## Notes

- `update` requires either stdin JSON or `--from`.
- `reset` refuses to delete the local ledger unless `--confirm` is present.
- `status` also prints the top violations when the ledger has enough history.

## Related

- [Code review run](run/)
- [Code review rules](rules/)
