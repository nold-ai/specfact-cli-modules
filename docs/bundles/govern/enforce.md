---
layout: default
title: Govern enforce
nav_order: 3
permalink: /bundles/govern/enforce/
redirect_from:
  - /guides/govern-enforce/
keywords: [govern, enforce, policy, compliance, rules]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Govern enforce

The Govern bundle exposes two enforcement paths: a stage preset for day-to-day quality policy and an SDD validator for bundle- and contract-level release checks.

## Commands

- `specfact govern enforce stage`
- `specfact govern enforce sdd [BUNDLE]`

## `specfact govern enforce stage`

Use the stage command to set the default enforcement preset for the current workspace.

| Option | Purpose |
|--------|---------|
| `--preset <minimal\|balanced\|strict>` | Select the saved enforcement mode |

Examples:

```bash
specfact govern enforce stage --preset balanced
specfact govern enforce stage --preset strict
specfact govern enforce stage --preset minimal
```

## `specfact govern enforce sdd [BUNDLE]`

Use the SDD command to validate bundle state, SDD thresholds, and frozen sections before promotion or release.

| Option | Purpose |
|--------|---------|
| `--sdd <path>` | Point to a non-default SDD manifest |
| `--output-format <yaml\|json\|markdown>` | Choose the report format |
| `--out <path>` | Write the validation report to a specific location |
| `--no-interactive` | Disable interactive prompts for CI/CD |

Examples:

```bash
specfact govern enforce sdd legacy-api
specfact govern enforce sdd auth-module --output-format json --out validation-report.json
specfact govern enforce sdd legacy-api --no-interactive
```

## Bundle-owned resources

Govern presets and any bundled policy packs travel with the installed Govern module version. Treat them as bundle payloads and refresh related IDE exports with `specfact init ide` after upgrades.

## Related

- [Govern patch](/bundles/govern/patch/)
- [Govern bundle overview](/bundles/govern/overview/)
