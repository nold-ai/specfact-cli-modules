# Change: Pre-Implementation Assurance Runtime and Bundled Workflow

## Why

Core contracts alone cannot stop an agent from implementing a stale or internally inconsistent change. SpecFact needs an official modules-owned runtime that deterministically assembles change inputs, evaluates them, exposes unresolved findings for human refinement, and records approval against the exact reviewed contract before implementation starts.

## What Changes

- **NEW**: A future official `specfact-preflight` module with Python validators for artifact completeness, source freshness, role-classified scope, component ownership, approved influence mappings or justified no-impact dispositions for every non-excluded sealed input, risk-dimension disposition, Requirements-plan references, dependency readiness, interface ownership, acceptance-testability, and conflicting active work.
- **NEW**: A future `specfact preflight run <change-id>` CLI that renders human and JSON results, supports read-only review by default, can persist local working copies of the normalized validation result, approved contract, and seal, and atomically advances canonical approval state only in a policy-authorized tracked or independently attested shared source after explicit user approval.
- **NEW**: A modules-owned bundled skill contract exposed as the harness-neutral `specfact-preflight` workflow and installable slash-command equivalent, such as `/specfact-preflight <change-id>` where the harness supports slash commands.
- **NEW**: A deterministic loop: discover -> snapshot -> validate -> review -> user-approved refine/re-run -> approve -> seal -> verify-before-implementation.
- **CLARIFY**: The skill orchestrates the CLI and presents evidence. It does not duplicate validator logic, silently edit ambiguous change artifacts, approve on behalf of a user, or implement production code.
- **EXCLUDE**: Stable publication, external ECC/hatch3r/Codex adapters, and seal-bound implementation checkpoint/conformance execution are separate downstream changes.

## Capabilities

### New Capabilities

- `preflight-assurance-runtime`: Executable pre-implementation validation, rendering, persistence, and approval-loop behavior.
- `preflight-assurance-workflow`: Module-owned canonical skill/slash-command workflow that delegates deterministic decisions to the runtime.

### Modified Capabilities

(none)

## Impact

- Planning artifacts only in this phase. No package, source, tests, manifest, registry entry, signature, version, skill file, command export, plugin, adapter, workflow, or dependency is created.
- Future implementation is modules-owned and consumes the released core preflight contracts without redefining them.
- Publication is explicitly deferred to `preflight-03-dogfood-hardening-and-release` after core C14 dogfood evidence.

## Dependencies

- Parent Feature: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162).
- Blocked by core `preflight-01-design-contract-core`.
- Blocks core C14 adoption issue [nold-ai/specfact-cli#680](https://github.com/nold-ai/specfact-cli/issues/680).
- Consumes, without duplicating, architecture, governance evidence, traceability, and native OpenSpec/Spec Kit import inputs.

## Explicit Non-Goals

- No stable module publication, compatibility promotion, signing, external harness packaging, checkpoint execution, or final implementation comparison.
- No AGENTS.md/OpenSpec/Spec Kit instruction generation; core `ai-integration-03-instruction-files` owns generated instruction surfaces.
- No generic skill discovery or export; core `ai-integration-01-agent-skill` owns that distribution mechanism.
- No proof that an LLM, design, or future implementation is correct.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #431
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/431>
- **Last Synced Status**: proposed
- **Sanitized**: true
