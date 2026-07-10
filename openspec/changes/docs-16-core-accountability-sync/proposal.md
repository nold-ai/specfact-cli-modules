# docs-16: Core documentation accountability sync

## Why

A modules-only manifest, registry, command, resource, or bundle-docs change can
make core catalogue and ownership documentation stale. Core change
`cli-val-05-ci-integration` supplies the authoritative, fail-closed
documentation-accountability checker, but modules currently does not invoke it
reciprocally. Local pre-commit also regenerates `llms.txt` only for selected
docs and prompt paths, so a module or registry change can bypass the generated
command-artifact update path.

## What Changes

- **ADD** a thin modules-side wrapper that resolves a paired core checkout and
  invokes its authoritative documentation-accountability checker against the
  current modules checkout; the wrapper owns no duplicate official-module
  inventory or core catalogue rules.
- **MODIFY** local pre-commit and Docs Review routing so package, registry,
  command, resource, docs, generated-artifact, dependency, and gate changes run
  the same fail-closed documentation validation before any docs-only safe
  bypass.
- **MODIFY** generated command-overview validation so every `packages/**` or
  `registry/**` change regenerates and verifies `llms.txt` and both generated
  command-reference artifacts; CI remains read-only and rejects drift.
- **MODIFY** command-overview inventory validation so an official manifest or
  grouped-root change cannot silently remain absent from generated module
  command artifacts.
- **MODIFY** non-main module-signature pre-commit remediation so an unrelated
  docs or workflow commit cannot rewrite module manifests; checksum repair is
  limited to staged module payloads and unavailable optional public keys do not
  trigger destructive local repair.

## Impact

- **Affected specs**: `documentation-accountability`,
  `module-command-overview`, `modules-pre-commit-quality-parity`, and
  `modules-docs-publishing`.
- **Affected surfaces**: modules pre-commit helper, Docs Review workflow,
  command-overview generator/checks, paired-checkout resolution, module
  signature verification/remediation, and their focused regression tests.
- **No public CLI or module-runtime API changes**: this is validation and
  generated-documentation hardening only.

## Source Tracking

- **GitHub Issue**: [#339](https://github.com/nold-ai/specfact-cli-modules/issues/339)
- **Parent Epic**: [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162)
- **Project**: SpecFact CLI (`Todo`)
- **Labels**: `bug`, `documentation`, `change-proposal`
- **Prerequisite**: core [#643](https://github.com/nold-ai/specfact-cli/issues/643),
  implemented by `specfact-cli/cli-val-05-ci-integration`; it owns the
  authoritative checker and is closed as of 2026-07-10 Europe/Berlin.
- **Blockers / blocked-by**: no native GitHub dependency is currently recorded;
  implementation readiness must recheck and reconcile the relationship before
  production edits.
- **Last Synced Status**: #339 open, assigned, Todo; #643 closed, Done
