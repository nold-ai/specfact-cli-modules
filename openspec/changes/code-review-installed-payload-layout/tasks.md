# Tasks: Repair C14 Installed Payload Layout Handling

## TDD / SDD order (enforced)

Future behavior work follows worktree -> current approved spec -> tests -> recorded failing evidence -> implementation -> passing evidence -> quality gates -> implementation PR. Do not implement production code until the mapped tests have run and failing-before evidence exists. All tasks below are future implementation tasks; this planning delivery does not complete them.

## 1. Establish the future implementation worktree

- [ ] Refresh origin and create a dedicated codex/ implementation branch/worktree from origin/dev under the sibling specfact-cli-modules-worktrees directory; keep the primary dev checkout unchanged.
- [ ] Bootstrap Hatch serially, verify core/module dependencies and worktree ownership, and run applicable preflight status checks.
- [ ] Refresh hierarchy metadata; verify issue state, parent, labels, project, blockers, and concurrent work before implementation.

## 2. Specify test implement and verify

- [ ] Revalidate current source and #459/#680 concurrency/dependencies before implementation.
- [ ] Add installer/signature integration and flat-layout regression tests mapped to every scenario; capture failing-before evidence.
- [ ] Implement bounded root resolution, manifest/copy consistency, and handoff diagnostics.
- [ ] Run regression tests and real installed-payload startup on supported Linux; repeat the recorded range review and classify independent blockers.
- [ ] Record red/green commands and exact versions in TDD_EVIDENCE.md.
- [ ] Complete mandatory quality/review gates and prepare patch-version/checksum/signature/registry consistency through canonical release tooling.
- [ ] Open the future implementation PR to dev; close #459 only after its actual acceptance criteria are fulfilled.

## Post-merge lifecycle

- [ ] After actual implementation merge and acceptance, use openspec archive code-review-installed-payload-layout; never archive this planning-only delivery.
- [ ] Remove the future implementation worktree only after its merge and retain required verification/release evidence.
