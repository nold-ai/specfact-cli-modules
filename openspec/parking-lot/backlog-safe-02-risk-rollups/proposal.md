# Change: Backlog SAFe — Explainable Risk Rollups

## Why


Every ceremony (standup, refinement, sprint summary, PI planning, release readiness) needs a consistent risk model with explainable inputs. Today risk is mentioned piecemeal in extensions but not modeled or wired. A single risk rollup mechanism — dependency criticality, policy failures, complexity flags, capacity overage, aging/WIP violations — makes all commands "exceptions-first" by default and gives teams one place to see "what might blow up."

Risk rollups are part of the **`backlog-safe` module** — they live here because risk is cross-ceremony (standup, refinement, sprint, PI) and the SAFe framework explicitly requires explainable risk tracking (ROAM, risk metrics). Scrum and Kanban teams benefit from risk rollups through integration hooks.

## Ownership Alignment (2026-04-08)

- Authoritative implementation owner: `nold-ai/specfact-cli-modules`, backlog bundle story [#156](https://github.com/nold-ai/specfact-cli-modules/issues/156)
- Target hierarchy: modules Epic [#145](https://github.com/nold-ai/specfact-cli-modules/issues/145) -> Feature [#146](https://github.com/nold-ai/specfact-cli-modules/issues/146) -> Story `#156`
- This modules-repo proposal is the authoritative implementation change for the transferred issue.
- Implementation MUST NOT proceed in `specfact-cli` core from the legacy `modules/backlog-safe/...` paths below.

## Module Package Structure

```
modules/backlog-safe/
  module-package.yaml          # updated: risk model available as cross-ceremony capability
  src/backlog_safe/
    risk/
      model.py                 # Risk model (inputs, scoring, contributions)
      rollup.py                # Risk aggregation (low/medium/high) with traceable inputs
      integrations.py          # hooks into standup, refinement, sprint-summary, pi-summary, verify-readiness
```

**Risk is a shared capability within `backlog-safe` module** — other modules (backlog-scrum, backlog-kanban) access risk rollups via the bridge registry by resolving the risk capability from backlog-safe.

## Module Package Structure

```
modules/backlog-safe/
  module-package.yaml          # updated: risk model available as cross-ceremony capability
  src/backlog_safe/
    risk/
      model.py                 # Risk model (inputs, scoring, contributions)
      rollup.py                # Risk aggregation (low/medium/high) with traceable inputs
      integrations.py          # hooks into standup, refinement, sprint-summary, pi-summary, verify-readiness
```

**Risk is a shared capability within `backlog-safe` module** — other modules (backlog-scrum, backlog-kanban) access risk rollups via the bridge registry by resolving the risk capability from backlog-safe.

## What Changes


- **NEW**: Risk model in `modules/backlog-safe/src/backlog_safe/risk/model.py` with inputs: dependency criticality (from backlog-core-01), policy failures (from policy-engine-01), complexity flags (from backlog-scrum-03), capacity overage (from backlog-scrum-02), aging/WIP violations (from backlog-kanban-01).
- **NEW**: Risk aggregation in `modules/backlog-safe/src/backlog_safe/risk/rollup.py`: single rollup score (low/medium/high); JSON output with input contributions, reasons, and evidence pointers; optional configurable weights.
- **NEW**: Integrate risk rollup into standup, refinement, sprint-summary, PI summary, and `backlog verify-readiness` (release) via `modules/backlog-safe/src/backlog_safe/risk/integrations.py` — each command surfaces a risk section when `backlog-safe` is installed.
- **EXTEND** (arch-07 schema extensions): Register `backlog_safe.risk_score` extension on `BacklogItem` via `module-package.yaml` — stores computed risk level (low/medium/high) and contributing factors for each item.

## Risk Input Contract (arch-05 bridge registry)
Risk inputs are consumed via the bridge registry — each contributing module exposes a protocol that the risk model queries:
- `BacklogCoreDependencyProtocol` → dependency criticality
- `PolicyEngineProtocol` → policy failures
- `BacklogScrumComplexityProtocol` → complexity flags
- `BacklogScrumCapacityProtocol` → capacity overage
- `BacklogKanbanFlowProtocol` → aging/WIP violations

All inputs are optional; risk model degrades gracefully with available data.

## Capabilities
- **backlog-safe** (risk rollups): Risk model with configurable inputs; single rollup score (low/medium/high); JSON output with input contributions, reasons, evidence pointers; integration with standup, refinement, sprint-summary, pi-summary, verify-readiness.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Original GitHub Issue**: nold-ai/specfact-cli#182 (transferred 2026-04-08)
- **GitHub Issue**: #156
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/156>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false
