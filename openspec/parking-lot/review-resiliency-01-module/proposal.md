# Change: Review Resiliency Module

## Why

The core repo can define resiliency contracts and scoring, but SpecFact still lacks a modules-side bundle that actually runs resiliency-oriented checks against repositories. Without a dedicated bundle, operational-scalability review remains a paper capability instead of a runnable part of the platform.

## What Changes

- **NEW**: Add a `specfact-review-resiliency` bundle scaffold under `packages/` with `review-resiliency` as its primary command.
- **NEW**: Package deterministic resiliency rule packs for retry, timeout, idempotency, backpressure, and graceful-degradation checks that map into the paired core findings contract.
- **OPTIONAL**: Add optional probe adapters for lightweight load-profile validation behind explicit opt-in flags so default review runs stay local-first and safe for CI.
- **NOTE**: Emit findings in the shared review report shape and, when the knowledge bundle is installed, forward evidence metadata to the memory runtime without making that integration mandatory.
- **EXTEND**: Document the new bundle on modules docs and declare manifest, registry, and bundle-dependency expectations for later implementation.

### Adapter Contract

The adapter boundary between resiliency analyzers and the core review contract defines how resiliency findings flow into the core ReviewFinding model:

**Mapping to ReviewFinding Fields:**

- **category**: Set to an existing allowed enum value from the `ReviewFinding` type's `category` field (e.g., `"clean_code"` for general resiliency patterns). New categories must be proposed via a core-spec change rather than in this module
- **severity**: Set to `"error"`, `"warning"`, or `"info"` based on the violation severity
- **tool**: Set to the resiliency analyzer name (e.g., `"resiliency-analyzer"` or specific tool name)
- **rule**: Set to the stable rule identifier in format `resiliency-<category>-<rule-id>` (e.g., `resiliency-retry-001`)
- **file**: Set to the repository-relative file path where the violation occurs
- **line**: Set to the 1-based line number or line range start
- **message**: Set to a human-readable description of the resiliency finding
- **fixable**: Optional boolean indicating whether the finding can be auto-fixed (default: false)

**Field Mapping from Custom Schema to ReviewFinding:**

- `id` → `rule` (or use as tool-specific identifier in extended metadata)
- `title` → Incorporated into `message` as the primary human-readable text
- `description` → Incorporated into `message` as detailed explanation
- `location` → Mapped to `file` and `line` fields
- `timestamp` → Can be preserved as metadata but is not a core ReviewFinding field
- `confidence` → Can be preserved as metadata but is not a core ReviewFinding field
- `evidence_refs` → Can be retained as supplemental references but primary location uses `file`/`line`

**Severity Enum Values:**

- Use canonical severity values: `"error"`, `"warning"`, `"info"`
- Map previous severity ranges to these values as needed

## Capabilities

### New Capabilities

- `review-resiliency-module`: Runtime bundle, command surfaces, packaged rule sets, and evidence adapters for resiliency review.

### Modified Capabilities

_None._

## Impact

- Affected code: future `packages/specfact-review-resiliency/`, bundle loader wiring, and rule resources under `resources/`.
- Affected docs: bundle overview and command-reference pages on modules.specfact.io for resiliency review.
- Dependencies: paired core change `review-resiliency-01-contracts`; optional knowledge integration with `knowledge-01-module-memory-runtime`.
- Release impact: introduces a new signed official bundle with a new `module-package.yaml` and registry entry.
- **Core Compatibility and Dependencies**: The bundle declares `core_compatibility: ">=1.0.0 <2.0.0"` for `review-resiliency-01-contracts` in `module-package.yaml`. Optional integration with `knowledge-01-module-memory-runtime` is declared under `bundle_dependencies` with a feature flag key `knowledge_integration_enabled: false` (default off), allowing evidence forwarding when the knowledge bundle is installed and the flag is explicitly enabled.

---

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Core umbrella (specfact-cli)**: [specfact-cli#511](https://github.com/nold-ai/specfact-cli/issues/511)
- **Modules Epic**: [#216](https://github.com/nold-ai/specfact-cli-modules/issues/216)
- **Parent Feature**: [#217](https://github.com/nold-ai/specfact-cli-modules/issues/217)
- **GitHub Issue**: [#226](https://github.com/nold-ai/specfact-cli-modules/issues/226)
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/226>
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: proposed
- **Sanitized**: false