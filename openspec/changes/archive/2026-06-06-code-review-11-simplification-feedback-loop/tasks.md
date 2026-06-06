## 1. GitHub readiness and change setup

- [x] 1.1 Verify issue [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276) is linked under parent Feature [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275), which is linked under Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162).
- [x] 1.2 Add [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275) and [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276) to the `SpecFact CLI` project board once a token with project scope is available.
- [x] 1.3 Confirm labels are complete: parent Feature has `enhancement`, `codebase`, `openspec`, `Feature`; change issue has `enhancement`, `codebase`, `openspec`, `change-proposal`.
- [x] 1.4 Confirm [#276](https://github.com/nold-ai/specfact-cli-modules/issues/276) is not already `in progress` before implementation begins, and record any blocker or blocked-by relationship updates in the issue body.
- [x] 1.5 Keep `openspec/CHANGE_ORDER.md` aligned with the new change under "Code review and sidecar validation improvements" as order 04, blocked by [#269](https://github.com/nold-ai/specfact-cli-modules/issues/269).
- [x] 1.6 Validate the OpenSpec change with `openspec validate code-review-11-simplification-feedback-loop --strict` before implementation begins.

## 2. Spec-first failing tests

- [x] 2.1 Add failing model tests proving `ReviewFinding` accepts optional simplification metadata and legacy finding payloads remain valid.
- [x] 2.2 Add failing runner tests proving `--focus simplify` retains only simplification-queue findings after existing scope resolution.
- [x] 2.3 Add failing analyzer tests for new deterministic overengineering patterns: accumulator loops, verbose boolean returns, redundant `None` branches, wrapper chains, pass-through defensive `try/except`, one-use temporaries, table-lookup candidates, and stdlib replacement candidates.
- [x] 2.4 Add failing duplicate-intent tests with same-domain functions that differ in local names but share normalized shape, call roots, and domain vocabulary.
- [x] 2.5 Add negative fixtures proving similar names alone, intentional compatibility wrappers, and ambiguous domain matches do not emit simplification findings.
- [x] 2.6 Add prompt contract tests proving `/specfact.08-simplify` groups by `intent_key`, shows related locations, and still requires accept/reject/skip/explain before edits.
- [x] 2.7 Record failing-before commands and output in `openspec/changes/code-review-11-simplification-feedback-loop/TDD_EVIDENCE.md`.

## 3. Review model and report metadata

- [x] 3.1 Extend the review finding model with optional simplification metadata fields: `confidence`, `rewrite_hint`, `canonical_pattern`, `intent_key`, `estimated_deletion_lines`, and `related_locations`.
- [x] 3.2 Bump emitted review report schema version to `1.1` when simplification metadata is present while preserving default compatibility for legacy reports.
- [x] 3.3 Ensure simplification metadata does not affect `is_blocking`, governed score, or existing severity validation.
- [x] 3.4 Add serialization examples or fixture reports covering both legacy and metadata-bearing findings.

## 4. Deterministic simplification analyzers

- [x] 4.1 Implement static analyzer helpers for the expanded overengineering patterns in `packages/specfact-code-review`.
- [x] 4.2 Implement duplicate-intent grouping from normalized AST shape, call roots, import/API evidence, path-domain tokens, and business vocabulary.
- [x] 4.3 Emit stable `intent_key` and `related_locations` only when multiple deterministic signals agree.
- [x] 4.4 Add confidence and estimated deletion calculations with conservative defaults suitable for advisory triage.
- [x] 4.5 Keep all new simplification findings advisory and score-neutral.

## 5. Review command and prompt integration

- [x] 5.1 Extend `specfact code review run --focus` to accept `simplify` and apply it after normal file-scope resolution.
- [x] 5.2 Update `/specfact.08-simplify` to group candidates by `intent_key`, then file/domain and rule, and to show related locations before drafting rewrites.
- [x] 5.3 Preserve the prompt's explicit per-change confirmation loop and prohibit autonomous batch edits.
- [x] 5.4 Run prompt validation with `hatch run validate-prompt-commands` if prompt command examples or resources change.

## 6. Docs, packaging, and signatures

- [x] 6.1 Update code-review documentation to explain simplification metadata, `--focus simplify`, duplicate-intent grouping, and advisory-only behavior.
- [x] 6.2 Bump affected `module-package.yaml` versions when packaged code, policy resources, or prompt resources change.
- [x] 6.3 Re-sign affected module manifests and update registry/signature artifacts as required by the modules repo signing policy.

## 7. Passing evidence and quality gates

- [x] 7.1 Re-run all targeted tests from section 2 and record passing evidence in `TDD_EVIDENCE.md`.
- [x] 7.2 Run `openspec validate code-review-11-simplification-feedback-loop --strict`.
- [x] 7.3 Run required gates in order: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, relevant `hatch run smart-test`, and relevant `hatch run test`.
- [x] 7.4 Run `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`, fix all findings or document approved exceptions, and rerun until passing.
- [x] 7.5 Commit, push, and open or update the PR to `dev` after verification is green.
