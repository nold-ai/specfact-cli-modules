# TDD Evidence: docs-16-core-accountability-sync

## Archive refresh

### 2026-07-26 Europe/Berlin

- Initial `openspec archive docs-16-core-accountability-sync --yes` correctly
  aborted because the delta's modified `modules-docs-publishing` requirement
  omitted the newer `Docs-only pull request has broken published link` scenario
  in the current main spec.
- The delta now preserves that unchanged scenario verbatim alongside this
  change's core-accountability scenario, so archiving can update the canonical
  spec without dropping later behavior.
- The subsequent archive validation also identified the newer docs-only
  pre-commit scenarios; the delta now preserves both verbatim before adding
  the manifest and registry accountability behavior.
- The archive validator then confirmed that the deterministic staged-only
  signature requirement is absent from the current canonical spec. Its delta
  block is therefore correctly classified as an added requirement rather than
  a modification of a missing header.

## Failing-before

### 2026-07-10 Europe/Berlin

Command:

```bash
hatch run pytest tests/unit/test_core_documentation_accountability.py \
  tests/unit/test_pre_commit_quality_parity.py \
  tests/unit/test_check_docs_commands_script.py \
  tests/unit/docs/test_llms_overview_freshness.py -q
```

Result: failed as expected before production edits (7 failed, 21 passed).

- `scripts/check-core-documentation-accountability.py` did not exist.
- Pre-commit did not classify `packages/**` or `registry/**` as
  documentation-relevant and did not invoke a core-accountability gate.
- Docs Review did not trigger for package/registry inventory changes or run the
  core-accountability command.
- The command-overview generator had no authoritative inventory-to-mount
  validation, so an official record with no command mount was not rejected.

## Passing-after

### 2026-07-10 Europe/Berlin

Focused regression command:

```bash
hatch run pytest tests/unit/test_core_documentation_accountability.py \
  tests/unit/test_pre_commit_quality_parity.py \
  tests/unit/test_check_docs_commands_script.py \
  tests/unit/docs/test_llms_overview_freshness.py -q
```

Result: passed (50 passed).

- The modules wrapper resolves explicit, paired-worktree, and sibling core
  checkouts, fails closed with setup guidance, and delegates to the core-owned
  checker.
- The command overview rejects an official manifest/registry record with no
  command mount.
- Pre-commit and Docs Review policy tests prove package and registry changes
  trigger generated-artifact and core-accountability validation.

Direct gate commands:

```bash
hatch run check-core-documentation-accountability
hatch run check-command-overview
hatch run check-command-contract
hatch run python scripts/check-docs-commands.py
```

Result: passed. The core checker reported `documentation-accountability: OK`,
the generated contract validated 91 command paths, and docs validation reported
no findings.

Installed-hook proof:

```bash
hatch run pre-commit install
hatch run pre-commit run modules-block2 --hook-stage pre-commit
```

Result: passed using an isolated temporary Git index and pre-commit cache. The
installed Block 2 hook regenerated and verified the three generated command
artifacts, passed core accountability and docs validation, then passed its
review and contract stages without changing the real staging area.

## Final Quality Evidence

### 2026-07-10 Europe/Berlin

- The combined docs-accountability and deterministic-signature regression
  suite passed: 60 tests.
- `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run
  yaml-lint`, `hatch run check-bundle-imports`, and `hatch run contract-test`
  passed.
- `openspec validate docs-16-core-accountability-sync --strict` passed.
- `hatch run specfact code review run --enforcement changed --bug-hunt --json
  --out .specfact/code-review.json` reported zero errors and zero warnings.
  Its two remaining entries are informational design advisories only.
- Follow-up review regressions passed: 22 tests covering paired-worktree
  precedence, duplicate official registry entries, optional signer contracts,
  and pre-commit matcher routing.
- The initial `hatch run test` run completed 842 passing tests but could not
  complete cleanly in this environment: Semgrep failed to initialize its system
  CA trust store, producing 17 unrelated fixture failures. A docs-workflow path
  assertion was corrected during that run; its focused regression test passes.

## Deterministic signature-hook failing-before

### 2026-07-10 Europe/Berlin

Command:

```bash
hatch run pytest tests/unit/test_verify_modules_signature_script.py \
  tests/unit/test_pre_commit_verify_modules_signature_script.py -q
```

Result: failed as expected (2 failed, 7 passed).

- `verify_manifest` could not accept an optional missing-public-key mode, so a
  locally unavailable public key made every existing signed manifest fail even
  when signatures were not required for the branch.
- The non-main hook still selected `--changed-only` remediation and the
  `HEAD~1` fallback that passed every failed manifest explicitly, bypassing
  changed-only selection and risking unrelated patch bumps.

## Deterministic signature-hook passing-after

### 2026-07-10 Europe/Berlin

Commands:

```bash
hatch run pytest tests/unit/test_verify_modules_signature_script.py \
  tests/unit/test_pre_commit_verify_modules_signature_script.py -q
hatch run ./scripts/verify-modules-signature.py \
  --payload-from-filesystem --enforce-version-bump --allow-missing-public-key
```

Result: passed (10 tests; all 7 module manifests checksum-verified).

- An optional existing signature with no local public key no longer causes
  non-main checksum verification to fail or start remediation.
- The hook uses `--staged-only` and removes the failed-manifest/`HEAD~1`
  fallback; repair candidates come from `git diff --cached` only.

Installed-hook proof:

```bash
hatch run pre-commit run --hook-stage pre-commit
```

Result: passed with an isolated temporary index. SHA-1 hashes of every
`packages/*/module-package.yaml` file were identical before and after the full
hook, and `git diff HEAD -- packages` remained empty. The hook exercised the
generated-artifact, core-accountability, docs, review, and contract stages.

## Semgrep Environment Note

### 2026-07-10 Europe/Berlin

Inside the restricted execution sandbox, Homebrew Semgrep 1.168.0 fails before
scanning because its OCaml CA-store provider reports empty system trust anchors.
Outside that sandbox, `semgrep --version && semgrep scan --config tools/semgrep
--quiet tests/fixtures/semgrep/good_print_in_src.py` exits successfully. This
is host-sandbox access to macOS certificate anchors, not a repository rule,
source, or terminal configuration defect.

## PR #341 Review Follow-up

### 2026-07-11 Europe/Berlin

Failing-before evidence covered a delegated-checker timeout, Git inspection
failures, staged-only signing with differing staged and unstaged module content,
and workflow step/coverage assertions. Passing-after evidence: 37 focused
tests, shell syntax validation, strict OpenSpec validation, accountability and
generated-artifact gates, contract tests, and changed-file review with zero
errors and warnings.
