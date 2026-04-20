## Context

`specfact code import` currently computes work by calling `Path.rglob()` in several separate phases and only filters many paths after discovery. That means virtual environments, build outputs, hidden tool directories, and other heavy trees still contribute traversal cost and often distort progress totals. In parallel, `specfact-project` generators load Jinja2 templates from `resources/templates`, but the referenced template files are absent from the bundle payload and the loader logic is less resilient than the prompt/resource patterns already used elsewhere in the repo.

This change spans multiple runtime surfaces in `specfact-project` and affects the `specfact-codebase` import entrypoint behavior, so it benefits from an explicit design before implementation.

## Goals / Non-Goals

**Goals:**
- Define one reusable import traversal policy that can prune hidden and heavyweight directories before file enumeration.
- Ensure import progress and ETA reflect the filtered work set, not the raw repository size.
- Add repo-local `.specfact/.specfactignore` support that future commands can also reuse.
- Package and resolve required generator Jinja2 templates from the module artifact with regression tests.
- Surface large-artifact warnings without aborting the import.

**Non-Goals:**
- Implement full `.gitignore` parsing or arbitrary nested ignore-file semantics.
- Redesign the entire AI analyzer pipeline beyond replacing the most expensive unpruned scans with the shared runtime policy.
- Introduce a new external dependency for ignore-file parsing if a lightweight in-repo parser is sufficient.
- Change the core CLI contract outside the module-owned bundle behavior in this repository.

## Decisions

### Decision 1: Introduce a shared import path policy helper
Create a small shared helper in `specfact_project` that evaluates:
- built-in excluded directory names and artifact patterns,
- hidden dot-prefixed names by default,
- `.specfact/.specfactignore` patterns relative to the repo root,
- optional allow-list exceptions for explicitly targeted entry points.

Why:
- Current ignore logic is duplicated and inconsistent across `_count_python_files`, `CodeAnalyzer.analyze`, relationship extraction, and AI context loading.
- A single helper allows pruning during traversal rather than post-filtering after `rglob()`.

Alternative considered:
- Keep per-callsite substring filters and just add more names. Rejected because it still pays the full traversal cost and keeps totals inconsistent.

### Decision 2: Switch the relevant scans to pruned traversal
Replace raw `rglob()` use in the import runtime hot paths with a helper that walks directories while mutating `dirnames` to skip ignored trees early.

Why:
- Early pruning addresses the primary performance problem directly.
- It gives one canonical file list that can drive counts, warnings, and ETA totals.

Alternative considered:
- Keep `rglob()` and filter after discovery. Rejected because it does not solve the filesystem overhead that triggered the user report.

### Decision 3: Derive ETA from live filtered work
Progress reporting should use the filtered candidate count as the total work and update ETA from processed-versus-discovered progress. Large-artifact warnings should appear when ignored or scanned directories cross configurable thresholds so users understand why the import is slow.

Why:
- Current totals include skipped files and make Rich's remaining-time estimate misleading.
- Warning users about heavyweight artifacts is more actionable than promising a fixed duration.

Alternative considered:
- Only change the user-facing wording from “about 5 minutes.” Rejected because runtime feedback would still remain low-signal on large repos.

### Decision 4: Package generator templates as first-class bundle resources
Add the required `.j2` files under `packages/specfact-project/resources/templates/` and resolve them via a helper that checks packaged resource roots first and development roots second. Mirror the resilience pattern already used in `persona_exporter.py`, but centralize it to avoid more one-off path math.

Why:
- The runtime failure is caused first by missing files and second by fragile single-path resolution.
- Resource packaging is already a governed capability in this repo, so the fix should align with existing bundle payload tests and docs.

Alternative considered:
- Embed the templates as inline Python strings. Rejected because it makes templates harder to maintain and diverges from the resource-payload pattern used elsewhere.

## Risks / Trade-offs

- [Ignore policy is too broad and skips legitimate source] -> Mitigation: support explicit entry-point anchoring, add focused tests for hidden but intentional source paths, and keep the built-in pattern set conservative.
- [Shared traversal helper changes multiple code paths at once] -> Mitigation: add targeted failing-first tests per phase and keep the helper API narrow.
- [Template packaging requires manifest/signature churn] -> Mitigation: treat manifest/resource updates as one release surface, then run signature and registry verification in the required gate order.
- [Warning thresholds create noisy output on medium repos] -> Mitigation: warn only for clearly unusual artifact sizes and keep messages advisory rather than repetitive.

## Migration Plan

1. Add OpenSpec spec deltas and tasks.
2. Write failing tests that prove ignored trees are pruned, ETA totals match filtered work, warnings surface for heavy artifacts, and required templates exist/resolution works.
3. Implement the shared traversal and template-resolution helpers, then update the import runtime and generators to use them.
4. Bump affected bundle versions, regenerate signed artifacts if required, update registry metadata, and document the new behavior.
5. Run the required quality gates and full SpecFact code review before merge.

Rollback is low risk: revert the helper adoption and packaged resources together so traversal and runtime resource behavior return to the previous implementation.

## Open Questions

- None for implementation start; warning thresholds can be tuned in-code if test evidence shows the initial defaults are too noisy.
