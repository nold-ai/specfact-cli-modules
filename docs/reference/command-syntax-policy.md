---
layout: default
title: Command Syntax Policy
permalink: /reference/command-syntax-policy/
description: Source-of-truth policy for documenting SpecFact CLI command argument syntax.
keywords: [command-syntax, policy, documentation, arguments, conventions]
audience: [solo, team, enterprise]
expertise_level: [advanced]
---

# Command Syntax Policy

This policy defines how command examples must be documented so docs stay consistent with actual CLI behavior.

## Core Rule

Always document commands exactly as implemented by the relevant current help entrypoint in the current release, such as `specfact project --help` or `specfact backlog --help`.

- Do not assume all commands use the same bundle argument style.
- Do not convert positional bundle arguments to `--bundle` unless the command explicitly supports it.

## Bundle Argument Conventions

- Positional bundle argument:
  - `specfact code import [BUNDLE]`
- `--bundle` option:
  - Supported by commands such as `specfact sync bridge --bundle <bundle>`
  - Not universally supported across all commands, so always verify with `--help`

For callback-style commands such as `specfact code import`, keep options before the positional bundle argument in examples, for example `specfact code import --repo . legacy-api`.

## IDE Init Syntax

- Preferred explicit form: `specfact init ide --ide <cursor|vscode|copilot|...>`
- `specfact init` is valid for auto-detection/bootstrap, but docs should be explicit when IDE-specific behavior is intended.

## Docs Author Checklist

Before merging command docs updates:

1. Verify syntax with `hatch run specfact <command> --help`.
2. Verify at least one real invocation for changed commands.
3. Keep examples aligned with current argument model (positional vs option).
4. Prefer one canonical example style per command in each page.

## Quick Verification Commands

```bash
hatch run specfact code import --help
hatch run specfact sync bridge --help
hatch run specfact code validate sidecar --help
hatch run specfact govern enforce --help
```
