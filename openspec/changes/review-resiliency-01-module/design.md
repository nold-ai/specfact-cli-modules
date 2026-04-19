## Context

`specfact-cli` owns the resiliency finding model, scorer, and CLI contracts, but `specfact-cli-modules` owns the executable bundle that packages third-party analyzers and rule resources. This change needs a new bundle instead of extending `specfact-code-review` so resiliency policy can evolve independently, ship its own dependencies, and remain optional for users who only want source-quality review.

## Goals / Non-Goals

**Goals:**

- Define the package layout, manifest fields, and command ownership for `specfact-review-resiliency`.
- Keep the bundle local-first by default while still allowing explicit opt-in probes for higher-cost runtime checks.
- Reuse the paired core review contracts so downstream evidence, reporting, and future policy gates stay uniform.
- Make bundle dependencies and registry/signing expectations explicit before implementation starts.

**Non-Goals:**

- Implement the core scoring model or findings schema; those remain in `specfact-cli`.
- Add always-on chaos or load testing against live systems.
- Introduce mandatory enterprise connectivity or telemetry requirements.

## Decisions

### 1. Ship resiliency as a standalone official bundle

- **Decision**: Create `packages/specfact-review-resiliency/` with its own `module-package.yaml`, versioning, and signing lifecycle.
- **Why**: Resiliency checks have different dependencies, rollout cadence, and operator expectations than static code review. A standalone bundle keeps install footprint optional and avoids overloading `specfact-code-review`.
- **Alternative considered**: Extend `specfact-code-review`. Rejected because it would conflate source hygiene with runtime robustness and would force unrelated dependencies onto all code-review users.

### 2. Separate static rule packs from optional active probes

- **Decision**: Make static analyzers and deterministic rule packs the default path, and gate active probe adapters behind explicit flags and profile settings.
- **Why**: The repo’s offline-first discipline and CI safety expectations do not permit surprise load generation or environment mutation.
- **Alternative considered**: Enable probe execution automatically when configuration is present. Rejected because it increases blast radius and complicates repeatable CI.

### 3. Depend on core contracts, not duplicate schemas

- **Decision**: Bundle code imports the paired core resiliency findings/report models from `specfact_cli`, and the manifest raises `core_compatibility` when those contracts change.
- **Why**: Shared scoring, rendering, and downstream knowledge ingestion belong in one canonical place.
- **Alternative considered**: Define bundle-local pydantic models. Rejected because it invites drift across core and module surfaces.

## Risks / Trade-offs

- **Risk**: Probe tooling can introduce flaky tests or platform-specific behavior. → **Mitigation**: keep probes opt-in and specify deterministic fixture-based tests as the default contract.
- **Risk**: A new bundle increases registry and signing overhead. → **Mitigation**: make manifest, registry, and version-bump tasks explicit in the implementation checklist.
- **Risk**: Rule overlap with `specfact-code-review` could confuse users. → **Mitigation**: document category boundaries and keep resiliency findings scoped to runtime robustness concerns.

## Migration Plan

1. Land the paired core change so bundle development targets a stable findings contract.
2. Implement the new package and command surface in a dedicated worktree.
3. Add registry metadata, docs, signatures, and compatibility declarations together before publishing.

## Open Questions

- Which optional probe runner provides the best cross-platform baseline with minimal dependency weight?
- Should retry/idempotency rules ship only as Semgrep-style resources, or also expose AST-native Python checks in the first release?
