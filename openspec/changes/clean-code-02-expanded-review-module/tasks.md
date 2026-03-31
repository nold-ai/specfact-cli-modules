# Tasks: clean-code-02-expanded-review-module

## 1. Branch and dependency guardrails

- [x] 1.1 Create dedicated worktree branch `feature/clean-code-02-expanded-review-module` from `dev` before implementation work.
- [x] 1.2 Confirm the archived runner and review-run changes are available locally and note the cross-repo dependency on specfact-cli `code-review-zero-findings`.
- [x] 1.3 Reconfirm scope against the 2026-03-22 clean-code implementation plan and `openspec/CHANGE_ORDER.md`.

## 2. Spec-first and test-first preparation

- [x] 2.1 Finalize spec deltas for finding schema expansion, runner behavior, policy-pack payload, and house-rules skill output.
- [x] 2.2 Add or update tests derived from those scenarios before touching implementation.
- [x] 2.3 Run targeted tests expecting failure and record results in `TDD_EVIDENCE.md`.

## 3. Implementation

- [x] 3.1 Extend the review finding schema and runner orchestration for the new clean-code categories.
- [x] 3.2 Implement or update the semgrep, radon, solid, yagni, dry, and checklist paths required by the new scenarios.
- [x] 3.3 Ship the `specfact/clean-code-principles` policy-pack payload and refresh `skills/specfact-code-review/SKILL.md` with the compact charter.

## 4. Validation and documentation

- [x] 4.1 Re-run targeted tests, quality gates, and review fixtures until all changed scenarios pass.
- [x] 4.2 Update bundle docs, changelog, and release metadata for the new categories and pack payload.
- [x] 4.3 Run `openspec validate clean-code-02-expanded-review-module --strict` and resolve all issues.

## 5. Delivery

- [ ] 5.1 Update `openspec/CHANGE_ORDER.md` dependency notes if sequencing changes again.
- [ ] 5.2 Open a PR from `feature/clean-code-02-expanded-review-module` to `dev` with spec/test/code/docs evidence.
