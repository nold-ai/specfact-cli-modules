# Change: Reusable Requirements Evidence Command and Local Enforcement

## Why

`requirements-05-dogfood-evidence-gate` proved the CI evaluator, but it is a
repository script with a branch-diff interface. The same deterministic evidence
cannot be consumed safely by local pre-commit hooks or by the paired CLI repo:
the current script has no public command contract and cannot inspect staged
index content. As a result, agents can receive code-review feedback while
missing a broken requirement import or evidence sidecar.

## What Changes

- **NEW**: `specfact requirements evidence`, a module-owned command that
  evaluates selected native OpenSpec sources in disposable bundles and emits
  the existing JSON/Markdown verdict schema.
- **NEW**: explicit mutually exclusive source-selection modes for a PR base
  reference and the current Git index, with index-snapshot isolation for local
  use.
- **NEW**: deterministic local report and remediation rendering suitable for
  pre-commit consumers and AI coding agents.
- **CHANGED**: the existing modules CI workflow and pre-commit invoke the
  module-owned evaluator through a thin compatibility adapter until the paired
  core CLI exposes module command routing.
- **CHANGED**: modules pre-commit Block 2 invokes the evaluator before code
  review and contract tests when staged active OpenSpec sources exist.

The command continues to validate imports, profile gates, and declared
test-link coverage. It does not execute tests or claim behavioral requirement
satisfaction.

## Capabilities

### New Capabilities

- `requirements-evidence-command`: A reusable, source-safe Requirements
  evidence command for local hooks and immutable CI consumers.

## Impact

- Affected package: `packages/specfact-requirements`, including the Typer app,
  runtime boundary, command documentation, module manifest/version, registry
  artifact, checksum, and signature.
- Affected tooling: `scripts/requirements_evidence_gate.py` becomes a thin
  compatibility wrapper or is retired after callers migrate; pre-commit Block
  2 gains an evidence stage.
- Affected CI: requirements-evidence keeps always-uploaded artifacts and uses
  the module-owned evaluator through its compatibility adapter until core
  command routing is released.
- Affected paired repository: `specfact-cli` consumes only the released command
  through an immutable fixture SHA.
- Rollback: retain the current script-compatible CI entrypoint until the
  command is released and consumed; revert hook/workflow wiring without
  altering OpenSpec source files.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#361](https://github.com/nold-ai/specfact-cli-modules/issues/361)
- **GitHub Type**: User Story
- **Parent Feature**: [#161](https://github.com/nold-ai/specfact-cli-modules/issues/161)
- **Parent Epic**: [#144](https://github.com/nold-ai/specfact-cli-modules/issues/144)
- **Project**: SpecFact CLI (`Todo`)
- **Depends On Change**: `requirements-05-dogfood-evidence-gate`
- **Blocked By**: [#352](https://github.com/nold-ai/specfact-cli-modules/issues/352) (native GitHub dependency)
- **Paired CLI Change**: `requirements-06-evidence-enforcement`
- **Paired CLI Issue**: [nold-ai/specfact-cli#657](https://github.com/nold-ai/specfact-cli/issues/657)
- **Blocks**: nold-ai/specfact-cli#657 (native GitHub dependency)
- **Repository**: nold-ai/specfact-cli-modules
- **Last Synced Status**: open / Todo (aligned 2026-07-26)
- **Sanitized**: false
