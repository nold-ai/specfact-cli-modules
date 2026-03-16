# Change Validation Report: code-review-04-contract-test-runners

**Validation Date**: 2026-03-13
**Change Proposal**: [proposal.md](./proposal.md)
**Validation Method**: Local repo alignment review against upstream
`specfact-cli` change plus bundle implementation inventory

## Executive Summary

- Breaking Changes: 0 detected
- Target Repo: `nold-ai/specfact-cli-modules`
- Impact Level: Low to medium
- Validation Result: Pass with blocker
- User Decision: Sync the change into `specfact-cli-modules` first

## Validation Findings

### Resolved mismatch

The upstream `specfact-cli` change artifacts for `code-review-04-contract-test-runners`
describe module-package implementation work, but they lived only in the `specfact-cli`
repo. This local change mirrors that scope into the actual implementation repository:
`specfact-cli-modules`.

### Dependency status

`code-review-04` depends on the bundle-local type/governance runners from
`code-review-03-type-governance-runners`.

At validation time:

- `ruff_runner.py` and `radon_runner.py` are present on `dev`
- `basedpyright_runner.py` and `pylint_runner.py` are not present on `dev`
- those files exist only as uncommitted work in a separate worktree

That dependency has since been merged to `origin/dev` and fast-forwarded into the active
`feature/code-review-04-contract-test-runners` worktree.

### Remaining blocker

Release metadata regeneration is still blocked by an encrypted private signing key that
requires an interactive passphrase before module manifest re-signing and detached
artifact-signature generation can complete.

## Impact Assessment

- **Code Impact**: additive bundle changes under
  `packages/specfact-code-review/src/specfact_code_review/`
- **Test Impact**: new unit tests under `tests/unit/specfact_code_review/`
- **Documentation Impact**: update existing `docs/modules/code-review.md`
- **Release Impact**: patch version bump for `specfact-code-review` plus registry update

## OpenSpec Validation

- **Status**: Pass
- **Command**:
  `openspec validate code-review-04-contract-test-runners --strict`
