# Tasks: Repair C14 Installed Payload Layout Handling

Current disposition (2026-09-21 Europe/Berlin): #459 is closed completed and project Done. The implementation checklist below is a historical record, not authority to resume delivery or reopen the issue. Retain its recorded results without inferring new acceptance evidence from issue closure.

## Historical TDD / SDD order

The implementation order was worktree -> current approved spec -> tests -> recorded failing evidence -> implementation -> passing evidence -> quality gates -> implementation PR. The historical planning instruction required mapped tests and failing-before evidence before production changes. Planning delivery completed none of these tasks. The 2026-09-07 evidence records the failing-first checkpoint and subsequent implementation below.

## 1. Historical implementation readiness

- [x] Refresh origin and create a dedicated bugfix/ implementation branch/worktree from origin/dev under the sibling specfact-cli-modules-worktrees directory; keep the primary dev checkout unchanged.
- [x] Bootstrap Hatch serially, verify core/module dependencies and worktree ownership, and run applicable preflight status checks.
- [x] Refresh hierarchy metadata; verify issue state, parent, labels, project, blockers, and concurrent work before implementation.

## 2. Specify test implement and verify

- [x] Revalidate current source and #459/#680 concurrency/dependencies before implementation.
- [x] Add installer/signature integration and flat-layout regression tests, including copy-time entry-type and ancestor substitutions, mapped to every scenario; capture failing-before evidence.
- [x] Implement bounded root resolution, manifest/copy consistency, and handoff diagnostics.
- [x] Run regression tests and real installed-payload startup on supported Linux; repeat the recorded range review and classify independent blockers (payload suites/startup pass; recorded range remains UNKNOWN due to Docker namespace refusal).
- [x] Record red/green commands and exact versions in TDD_EVIDENCE.md.
- [x] Complete mandatory quality/review gates and prepare patch-version/checksum/signature/registry consistency through canonical release tooling (dev-PR checksum/version checks pass; canonical CI signing and registry publication completed in #463).
- [x] Merge implementation PR [#462](https://github.com/nold-ai/specfact-cli-modules/pull/462) to dev; registry publication completed in #463; #459 was then open pending final acceptance; that lifecycle note is superseded by the current disposition above.

## Post-merge lifecycle

- [ ] Reconcile the existing merge, acceptance, and shipment evidence, then use openspec archive code-review-installed-payload-layout; preserve historical planning evidence without claiming unverified acceptance or repeating delivery.
- [ ] Remove the future implementation worktree only after its merge and retain required verification/release evidence.
