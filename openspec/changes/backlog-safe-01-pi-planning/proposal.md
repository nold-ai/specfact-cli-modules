# Change: Backlog SAFe — PI Planning and WSJF Support

## Why


SAFe teams operate at PI/iteration/ART level. Today backlog-core-01 (E4) includes ROAM list seed and backlog-scrum-02 mentions SAFe usage, but there is no PI-level first-class support: no `backlog pi-summary`, no WSJF workflow, no PI readiness policy. Without a dedicated `backlog-safe` module providing `.specfact/safe.yaml` and PI artifacts, SAFe is an afterthought, not a supported framework.

This change establishes the **`backlog-safe` module** — the SAFe-framework module that provides PI planning, WSJF assistance, and PI readiness policies.

## Ownership Alignment (2026-04-08)

- Authoritative implementation owner: `nold-ai/specfact-cli-modules`, backlog bundle story [#154](https://github.com/nold-ai/specfact-cli-modules/issues/154)
- Target hierarchy: modules Epic [#145](https://github.com/nold-ai/specfact-cli-modules/issues/145) -> Feature [#146](https://github.com/nold-ai/specfact-cli-modules/issues/146) -> Story `#154`
- This modules-repo proposal is the authoritative implementation change for the transferred issue.
- Implementation MUST NOT proceed in `specfact-cli` core from the legacy `modules/backlog-safe/...` paths below.

## Module Package Structure

```
modules/backlog-safe/
  module-package.yaml          # name: backlog-safe; commands: backlog pi-summary
  src/backlog_safe/
    __init__.py
    main.py                    # typer.Typer app — backlog pi-summary command group
    commands/
      pi_summary.py            # specfact backlog pi-summary
    planning/
      wsjf.py                  # WSJF calculation + AI-assisted field proposals
      pi_artifacts.py          # PI scope, team commitments, ROAM seed, dependency contracts
    config/
      safe_config.py           # .specfact/safe.yaml loader (PI/iteration/ART settings)
    integrations/
      policy_hook.py           # PI readiness policy hook (policy-engine-01)
      dependency_hook.py       # cross-team dependency contracts from backlog-core-01
```

**`module-package.yaml` declares:**
- `name: backlog-safe`
- `version: 0.1.0`
- `commands: [backlog pi-summary]`
- `dependencies: [backlog-core]`
- `optional_dependencies: [policy-engine]`
- `publisher:` + `integrity:` — arch-06 marketplace readiness

**Config**: `.specfact/safe.yaml` — PI/iteration/ART settings (PI number, iteration length, ART name, team names). Separate from `.specfact/scrum.yaml` and `.specfact/kanban.yaml`.

## Module Package Structure

```
modules/backlog-safe/
  module-package.yaml          # name: backlog-safe; commands: backlog pi-summary
  src/backlog_safe/
    __init__.py
    main.py                    # typer.Typer app — backlog pi-summary command group
    commands/
      pi_summary.py            # specfact backlog pi-summary
    planning/
      wsjf.py                  # WSJF calculation + AI-assisted field proposals
      pi_artifacts.py          # PI scope, team commitments, ROAM seed, dependency contracts
    config/
      safe_config.py           # .specfact/safe.yaml loader (PI/iteration/ART settings)
    integrations/
      policy_hook.py           # PI readiness policy hook (policy-engine-01)
      dependency_hook.py       # cross-team dependency contracts from backlog-core-01
```

**`module-package.yaml` declares:**
- `name: backlog-safe`
- `version: 0.1.0`
- `commands: [backlog pi-summary]`
- `dependencies: [backlog-core]`
- `optional_dependencies: [policy-engine]`
- `publisher:` + `integrity:` — arch-06 marketplace readiness

**Config**: `.specfact/safe.yaml` — PI/iteration/ART settings (PI number, iteration length, ART name, team names). Separate from `.specfact/scrum.yaml` and `.specfact/kanban.yaml`.

## What Changes


- **NEW**: CLI command `specfact backlog pi-summary` in `modules/backlog-safe/src/backlog_safe/commands/pi_summary.py`: PI scope, team commitments, cross-team dependency contracts, ROAM items (from backlog-core-01 E4 when available). Declared in `module-package.yaml`; no changes to `cli.py`.
- **NEW**: Config `.specfact/safe.yaml` for PI/iteration/ART settings; loaded by `modules/backlog-safe/src/backlog_safe/config/safe_config.py`.
- **NEW**: WSJF assistance in `modules/backlog-safe/src/backlog_safe/planning/wsjf.py`: calculation with AI-assisted missing-field proposals and confirmation; output as JSON and Markdown.
- **EXTEND** (policy-engine-01): When policy-engine-01 is present, register PI readiness policy hooks; evaluated when safe config exists. Graceful no-op if policy-engine-01 not installed.
- **EXTEND** (backlog-core-01): Cross-team dependency contracts and ROAM seed from backlog-core-01 E4 feed PI summary when available.
- **EXTEND** (arch-07 schema extensions): Register `backlog_safe.pi_metadata` extension on `BacklogItem` via `module-package.yaml` — stores PI number, ART assignment, WSJF score for SAFe items.

## Capabilities
- **backlog-safe** (PI planning): `backlog pi-summary` command; `.specfact/safe.yaml` (PI/iteration/ART); WSJF assistance (calculation + AI-assisted fields + confirmation); PI readiness in policy-engine-01; cross-team dependency contracts from backlog-core-01.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Original GitHub Issue**: nold-ai/specfact-cli#184 (transferred 2026-04-08)
- **GitHub Issue**: #154
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/154>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
