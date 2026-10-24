# Tasks

The owner approved diagnostic-only implementation on 2026-10-25, Europe/Berlin. Planning validation is not runtime evidence.

## 1. Establish readiness

- [x] Obtain approval for this diagnostic-only unit and record its scope.
- [x] Refresh public hierarchy metadata, check for an existing follow-up issue, and establish parent, labels, project, blockers, blocked-by relationships, assignee, and current ownership before implementation. Reuse the authorized #513 takeover only within its agreed scope.
- [x] Use the existing dedicated #513 branch/worktree, preserve #524 and other worktrees, and revalidate exact source/reviewer identities and current change order.
- [x] Revalidate this change with `openspec validate code-review-linux-analyzer-diagnostics --strict`.

## 2. Specify and reproduce

- [x] Confirm all spec scenarios and convert planning inspection mappings to exact executable selectors before production edits.
- [x] Add focused Python-only tests of actual workflow snippets covering normal/oversized provenance, pytest unknowns/native skip classification, lifecycle/blocking, malformed inputs, redaction, bounds, and unchanged gate exits. Keep all existing tests enabled.
- [x] Capture genuine failing-before evidence against the unchanged projection in `TDD_EVIDENCE.md`.

## 3. Implement the diagnostic boundary

- [x] Adapt only existing candidate and independent inline projections. Preserve parser/iteration/output limits, private artifact boundaries, trusted workflow ownership, and captured review exit behavior.
- [x] Emit validated enums and strict Booleans with explicit unavailable/unclassified cases. Do not change analyzers, source/test selection, toolchain, admission, enforcement, verdicts, dependencies, or budgets.
- [x] Run focused tests to GREEN and record source-bound RED/GREEN evidence and Requirements reconciliation.

## 4. Verify and return evidence

- [x] Run format, type-check, lint, YAML lint, imports, strict module signature verification, contracts, SMART tests, and full tests. Confirm no signed payload changed; if one must change, stop for scope review rather than bypassing version/signing requirements.
- [x] Retain the documented Darwin DEFERRED condition with mandatory blocking exact-head Linux review, and complete CodeRabbit/independent review before finalization. This local condition is not hosted review PASS.
- [x] Run all existing workflow privacy/shell tests and verify that private strings, paths, raw reports, and receipts cannot enter public output or uploaded artifacts.
- [ ] After authorized signed commit/push, run the unchanged required Linux matrix and independent signed review on the exact new head. Record actual class/side/lifecycle observations and preserve all underlying failures as blocking.
- [ ] Return the observed remaining root causes and a separately justified minimal repair proposal if needed. Do not merge #524 or archive change 17 on this evidence.
- [ ] Archive this follow-up only after its approved implementation merges, using `openspec archive code-review-linux-analyzer-diagnostics`.
