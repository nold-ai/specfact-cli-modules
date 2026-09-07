# Tasks: Repair C14 Installed Payload Layout Handling

## TDD / SDD order (enforced)

Future behavior work follows worktree -> current approved spec -> tests -> recorded failing evidence -> implementation -> passing evidence -> quality gates -> implementation PR. Do not implement production code until the mapped tests have run and failing-before evidence exists. Planning delivery completed none of these tasks. The 2026-09-07 evidence records the failing-first checkpoint and subsequent implementation below.

## 1. Establish the future implementation worktree

- [x] Refresh origin and create a dedicated bugfix/ implementation branch/worktree from origin/dev under the sibling specfact-cli-modules-worktrees directory; keep the primary dev checkout unchanged.
- [x] Bootstrap Hatch serially, verify core/module dependencies and worktree ownership, and run applicable preflight status checks.
- [x] Refresh hierarchy metadata; verify issue state, parent, labels, project, blockers, and concurrent work before implementation.

## 2. Specify test implement and verify

- [x] Revalidate current source and #459/#680 concurrency/dependencies before implementation.
- [x] Add installer/signature integration and flat-layout regression tests, including copy-time entry-type and ancestor substitutions, mapped to every scenario; capture failing-before evidence.
- [x] Implement bounded root resolution, manifest/copy consistency, and handoff diagnostics.
- [x] Run regression tests and real installed-payload startup on supported Linux; repeat the recorded range review and classify independent blockers (payload suites/startup pass; recorded range remains UNKNOWN due to Docker namespace refusal).
- [x] Record red/green commands and exact versions in TDD_EVIDENCE.md.
- [x] Complete mandatory quality/review gates and prepare patch-version/checksum/signature/registry consistency through canonical release tooling (dev-PR checksum/version checks pass; release signing and publication remain with CI).
- [ ] Open the future implementation PR to dev; close #459 only after its actual acceptance criteria are fulfilled.

## Post-merge lifecycle

- [ ] After actual implementation merge and acceptance, use openspec archive code-review-installed-payload-layout; never archive this planning-only delivery.
- [ ] Remove the future implementation worktree only after its merge and retain required verification/release evidence.
