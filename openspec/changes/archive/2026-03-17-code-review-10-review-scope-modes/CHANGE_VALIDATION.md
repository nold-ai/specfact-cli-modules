## Verification Report: code-review-10-review-scope-modes

### Summary

| Dimension | Status |
| --- | --- |
| Completeness | 4/4 apply-ready artifacts present (`proposal`, `design`, `specs`, `tasks`) |
| Correctness | Scope-mode and path-filter requirements align with upstream `code-review-10-review-scope-modes` |
| Coherence | Proposal, design, and tasks consistently keep changed-only as the default auto-scope |

### Validation Checks

- Reviewed upstream `specfact-cli` proposal, design, and spec delta for `code-review-10-review-scope-modes`.
- Reviewed local artifacts: `proposal.md`, `design.md`, `tasks.md`, and delta specs under `specs/`.
- Checked current modules-repo review-run capabilities from `code-review-08-review-run-integration` to ensure this is a requirement change on an existing command, not a new command surface.

### CRITICAL

None.

### WARNING

- The derived change assumes the bundle command can identify a stable governed
  repository file set for `--scope full`. If existing runtime logic only
  supports changed-file discovery, implementation may need a new helper to keep
  full-review selection deterministic across unit and e2e tests.
  Recommendation: verify current target-resolution boundaries before coding and
  centralize scope resolution rather than duplicating it across command tests
  and runtime entry points.

### SUGGESTION

- Keep cli-val scenarios narrow and representative. One changed-only example,
  one full-review example, one subtree-filter example, and one invalid
  invocation are enough to prove the contract without making scenario YAML noisy.

### Dependency Analysis

- Modified capabilities: `review-run-command`, `review-cli-contracts`
- Primary implementation touchpoint: `packages/specfact-code-review/src/specfact_code_review/run/`
- Primary regression surface: `tests/unit/`, `tests/e2e/`, and `tests/cli-contracts/`
- Upstream source dependency: `nold-ai/specfact-cli` change `code-review-10-review-scope-modes`

### Final Assessment

No critical issues found. The derived change is internally consistent, matches
the upstream intent, and is ready for implementation after strict OpenSpec
validation passes.

### OpenSpec Validation

- **Status**: Pass
- **Command**: `openspec validate code-review-10-review-scope-modes --strict`
- **Issues Found/Fixed**: 0
