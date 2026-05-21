---
layout: default
title: Code review rules
nav_order: 5
permalink: /bundles/code-review/rules/
redirect_from:
  - /guides/code-review-rules/
keywords: [code-review, rules, configuration, linting, quality]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Code review rules

The rules commands manage the bundled `specfact-code-review` skill. Install it
when Codex CLI, Claude, Vibe, Cursor, or another SKILL.md-compatible AI IDE
needs the Code Review workflow without copying slash prompt templates by hand.
The skill includes CLI self-healing guidance, review run commands,
simplification queue handling, and compact house rules.

## Commands

- `specfact code review rules show`
- `specfact code review rules init`
- `specfact code review rules update`

## Subcommands

| Command | Purpose |
|--------|---------|
| `specfact code review rules show` | Print the current skill content |
| `specfact code review rules init --ide <target>` | Create the default skill file and optionally install it to one IDE target |
| `specfact code review rules update --ide <target>` | Refresh the TOP VIOLATIONS section and sync installed IDE targets |

## Examples

```bash
specfact code review rules show
specfact code review rules init --ide codex
specfact code review rules update --ide cursor
```

## Bundle-owned resources

The skill content is bundled with `nold-ai/specfact-code-review`. Initialize or
refresh it from the installed module version instead of copying prompt templates
or legacy core-owned files by hand.

## Related

- [Code review run](../run/)
- [Code review ledger](../ledger/)
