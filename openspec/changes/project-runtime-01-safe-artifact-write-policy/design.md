## Context

Many bundle commands in `specfact-cli-modules` write directly into user repositories using local `write_text` or bespoke write logic. Even where behavior is currently harmless, the repo lacks a consistent contract for ownership, merge strategy, preview, and recovery when bundle commands materialize artifacts. If only core init/setup adopts safer semantics, runtime package commands can still recreate the same trust failure elsewhere.

The paired core change defines the authoritative policy language. This modules-side design focuses on adopting that policy in runtime packages without introducing a competing abstraction.

## Goals / Non-Goals

**Goals:**
- Reuse the core safe-write contract from `specfact-cli` in bundle runtime code.
- Standardize how bundle commands declare file ownership and write intent.
- Add adoption for first-runner package commands that materialize or mutate local project artifacts.
- Add tests ensuring bundle commands preserve unrelated user content when they touch partially owned artifacts.

**Non-Goals:**
- Refactor every single `write_text` call in the repo regardless of target ownership.
- Move ownership policy definition into modules; core remains authoritative.
- Turn all bundle writers into interactive review workflows in this change.

## Decisions

### 1. Runtime packages will depend on the core safe-write helper instead of creating a duplicate modules-side helper

Bundle code already imports `specfact_cli` surfaces where needed. This change will reuse the core helper and ownership model so both repos speak the same semantics.

Rationale:
- One contract, one enforcement surface.
- Avoids drift between “core-safe” and “runtime-safe” behavior.

Alternative considered:
- Create a modules-local wrapper and later reconcile. Rejected because it duplicates the core design immediately.

### 2. Adoption scope will prioritize commands that write into user repos, not internal generated temp artifacts

The first slice should cover commands that write persistent user-facing artifacts in target repositories. Internal temp files, caches, or package-build outputs are not the same risk class.

Rationale:
- Keeps scope manageable while addressing the highest-risk trust boundary.

### 3. Runtime commands must declare artifact ownership at the call site

Each adopting command will explicitly state whether the target artifact is:
- fully owned by SpecFact
- partially owned by SpecFact-managed keys/blocks
- create-only

Rationale:
- Bundle authors know command intent best.
- CI can verify helper usage but needs call-site ownership declarations to be meaningful.

### 4. Modules CI should add behavior fixtures rather than a second independent static scanner

The static “unsafe write” rule belongs in core because it defines the helper boundary. Modules-side CI will focus on adoption tests for selected commands and package flows.

Rationale:
- Keeps enforcement non-duplicative.
- Core owns the API and static contract; modules own runtime usage proof.

## Risks / Trade-offs

- `[Risk]` Bundle packages may need a raised `core_compatibility` floor to consume the new helper. → Mitigation: stage versioning and compatibility updates as part of adoption tasks.
- `[Risk]` Adoption can stall if too many commands are targeted at once. → Mitigation: identify first adopters in proposal/tasks and defer remaining paths with explicit follow-up inventory.
- `[Risk]` Some runtime artifact types may not support structured merge yet. → Mitigation: use create-only or explicit-replace with backup semantics until a sanctioned merge strategy exists.

## Migration Plan

1. Wait for the core helper contract to land or stabilize in the paired core change.
2. Update selected runtime package commands to call the helper with ownership metadata.
3. Add tests proving preservation/backup/conflict behavior for those package flows.
4. Document adoption guidance for future bundle authors.

Rollback strategy:
- If a specific runtime adoption proves unstable, the command should fail-safe or skip existing-file mutation instead of restoring raw overwrite behavior.

## Open Questions

- Which bundle commands should be first adopters in this change versus a later follow-up inventory?
- Should bundle manifests or docs carry artifact ownership metadata, or is code-level declaration sufficient for now?
