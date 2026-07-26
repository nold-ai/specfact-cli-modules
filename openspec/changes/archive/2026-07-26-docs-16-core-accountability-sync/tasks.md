# docs-16: Tasks — core documentation accountability sync

## 1. Governance And Readiness

- [x] 1.1 Refresh and consult GitHub hierarchy state; verify #339 parent,
  labels, project, blockers, blocked-by, and concurrency status before
  production edits.
- [x] 1.2 Verify core #643 / `cli-val-05-ci-integration` remains available on
  the selected core branch and owns the authoritative checker.
- [x] 1.3 Validate this change with `openspec validate
  docs-16-core-accountability-sync --strict` before implementation.

## 2. Failing-First Regression Coverage

- [x] 2.1 Add failing wrapper tests for explicit, sibling, paired-worktree,
  missing-core, and missing-checker resolution paths.
- [x] 2.2 Add failing tests that stale core catalogues and ownership handoffs
  fail when a modules manifest or grouped root changes.
- [x] 2.3 Add failing generator/checker tests for manifest/registry
  disagreement, an unrepresented official package, renamed package, and
  remapped grouped root.
- [x] 2.4 Add failing pre-commit and workflow-policy tests proving every
  `packages/**` and `registry/**` change runs generated-artifact freshness and
  core accountability before safe bypass.
- [x] 2.5 Record failing-before commands and output in `TDD_EVIDENCE.md` before
  production edits.
- [x] 2.6 Add failing tests proving non-main optional-signature verification
  does not mutate docs-only commits and staged-only repair cannot fall back to
  all failed manifests.

## 3. Fail-Closed Gate Implementation

- [x] 3.1 Implement the thin modules-side core-accountability wrapper and Hatch
  command; do not duplicate the core inventory or catalogue checks.
- [x] 3.2 Expand pre-commit routing for manifest, registry, package command,
  resource, docs, dependency, generated-artifact, and gate changes; refuse
  auto-staging when relevant inputs are unstaged.
- [x] 3.3 Make generated overview validation reject authoritative inventory and
  command-mount disagreement, then regenerate all three artifacts locally.
- [x] 3.4 Update Docs Review path filters and steps to run strict docs,
  generated-artifact, command-contract, prompt-command, and core-accountability
  checks against the resolved paired core ref.
- [x] 3.5 Make module-signature verification tolerate an unavailable optional
  public key on non-main branches and scope automatic repair to staged module
  payloads only.

## 4. Verification And Evidence

- [x] 4.1 Run focused wrapper, generator, pre-commit, and workflow tests;
  record passing evidence in `TDD_EVIDENCE.md`.
- [x] 4.2 Run the local pre-commit helper with representative docs-only,
  manifest-only, registry-only, and command-source staged changes.
- [x] 4.3 Run `hatch run check-command-overview`, command-contract and docs
  validation, and the core-accountability wrapper directly.
- [x] 4.4 Run required touched-scope quality gates, including format,
  type-check, lint, YAML validation, contract tests, and strict OpenSpec
  validation.
- [x] 4.5 Run `hatch run specfact code review run --enforcement changed
  --bug-hunt --json --out .specfact/code-review.json`; remediate every finding,
  rerun as needed, and record fresh evidence.
- [x] 4.6 Run focused signature-hook regression tests and a docs-only
  pre-commit simulation that proves no manifest is modified.
