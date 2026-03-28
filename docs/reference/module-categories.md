---
layout: default
title: Module Categories
nav_order: 35
permalink: /reference/module-categories/
keywords: [module, categories, classification, types, organization]
audience: [solo, team, enterprise]
expertise_level: [advanced]
---

# Module Categories

SpecFact groups feature modules into workflow-oriented command families.

Core commands remain top-level:

- `specfact init`
- `specfact backlog auth`
- `specfact module`
- `specfact upgrade`

Category command groups:

- `specfact project ...`
- `specfact backlog ...`
- `specfact code ...`
- `specfact project sync ...`
- `specfact code analyze ...`
- `specfact code drift ...`
- `specfact code validate ...`
- `specfact code repro ...`
- `specfact spec ...`
- `specfact govern ...`
- `specfact govern enforce ...`
- `specfact code review ...`

## Canonical Category Assignments

| Module | Category | Bundle | Group Command | Sub-command |
|---|---|---|---|---|
| `init` | `core` | — | — | `init` |
| `auth` | `core` | — | — | `auth` |
| `module_registry` | `core` | — | — | `module` |
| `upgrade` | `core` | — | — | `upgrade` |
| `project` | `project` | `specfact-project` | `project` | `project` |
| `import_cmd` | `project` | `specfact-project` | `project` | `import` |
| `sync` | `project` | `specfact-project` | `project` | `sync` |
| `backlog` | `backlog` | `specfact-backlog` | `backlog` | `backlog` |
| `policy_engine` | `backlog` | `specfact-backlog` | `backlog` | `policy` |
| `analyze` | `codebase` | `specfact-codebase` | `code` | `analyze` |
| `drift` | `codebase` | `specfact-codebase` | `code` | `drift` |
| `validate` | `codebase` | `specfact-codebase` | `code` | `validate` |
| `repro` | `codebase` | `specfact-codebase` | `code` | `repro` |
| `spec` | `spec` | `specfact-spec` | `spec` | `spec` |
| `enforce` | `govern` | `specfact-govern` | `govern` | `enforce` |
| `patch_mode` | `govern` | `specfact-govern` | `govern` | `patch` |
| `review` | `code-review` | `specfact-code-review` | `code` | `review` |

## Bundle Contents by Category

- `specfact-project`: `project`, `sync`
- `specfact-backlog`: `backlog`, `policy`
- `specfact-codebase`: `code import`, `code analyze`, `code drift`, `code validate`, `code repro`
- `specfact-spec`: `spec`
- `specfact-govern`: `enforce`, `patch`
- `specfact-code-review`: `code review`

## Bundle Package Layout and Namespaces

Official bundle packages are published from the dedicated modules repository:

- Repository: `nold-ai/specfact-cli-modules`
- Package roots: `packages/specfact-project/`, `packages/specfact-backlog/`, `packages/specfact-codebase/`, `packages/specfact-spec/`, `packages/specfact-govern/`

Namespace mapping:

- `specfact-project` -> import namespace `specfact_project.*`
- `specfact-backlog` -> import namespace `specfact_backlog.*`
- `specfact-codebase` -> import namespace `specfact_codebase.*`
- `specfact-spec` -> import namespace `specfact_spec.*`
- `specfact-govern` -> import namespace `specfact_govern.*`

Compatibility note:

- In the current CLI release, bundle commands are mounted under the root groups shown by `specfact --help` (for example `specfact code repro` and `specfact govern enforce`).

## First-Run Profiles

`specfact init` supports profile presets and explicit bundle selection:

- `solo-developer` -> `specfact-codebase`
- `backlog-team` -> `specfact-backlog`, `specfact-project`, `specfact-codebase`
- `api-first-team` -> `specfact-spec`, `specfact-codebase` (and `specfact-project` is auto-installed as a dependency)
- `enterprise-full-stack` -> `specfact-project`, `specfact-backlog`, `specfact-codebase`, `specfact-spec`, `specfact-govern`

Examples:

```bash
specfact init --profile solo-developer
specfact init --install backlog,codebase
specfact init --install all
```

## Command Topology: Before and After

Command surface:

- Core top-level commands (`init`, `auth`, `module`, `upgrade`).
- Workflow commands available through mounted groups (for example `specfact project sync`, `specfact code repro`, `specfact govern enforce`).
