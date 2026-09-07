# Tasks: Native Local Code Review Across macOS Linux and Windows

## TDD / SDD order (enforced)

Future behavior work follows worktree -> current approved spec -> tests -> recorded failing evidence -> implementation -> passing evidence -> quality gates -> implementation PR. Do not implement production code until the mapped tests have run and failing-before evidence exists. All tasks below are future implementation tasks; this planning delivery does not complete them.

## 1. Establish the future implementation worktree

- [ ] Refresh origin and create a dedicated codex/ implementation branch/worktree from origin/dev under the sibling specfact-cli-modules-worktrees directory; keep the primary dev checkout unchanged.
- [ ] Bootstrap Hatch serially, verify core/module dependencies and worktree ownership, and run applicable preflight status checks.
- [ ] Refresh hierarchy metadata; verify issue state, parent, labels, project, blockers, and concurrent work before implementation.

## 2. Specify test implement and verify

- [ ] Verify #459, published #434, and released core #679; retain transitive prerequisites and exact release/install evidence.
- [ ] Reassess this change with the released preflight/C15 baseline and refine the candidate design; complete the following dependency and platform audits before approval.
- [ ] Audit the complete dependency closure against released core/module policy; exclude nodejs-wheel-binaries under the current prohibition, select and review a compliant native Node source, and resolve the inherited C14 lock conflict through versioned contracts before design approval. Require a separately accepted policy change for any proposed prohibition change; keep this gate blocked while unresolved.
- [ ] Audit the complete OS/x64/ARM64/Python/analyzer matrix; resolve native build gaps and prove OS-native isolation prototypes.
- [ ] Specify versioned backend/runtime/evidence interfaces and paired core scope from that evidence; do not infer Linux-equivalent capabilities. Review and approve the resulting implementation design only after the dependency and platform gates pass.
- [ ] Add scenario-mapped failing native tests, including prohibited-but-signed dependencies, inherited policy conflicts, admissible replacements, full-module integrity, and unbound/stale/partial/mixed external cache cases before launch or offline reuse, and capture red evidence before production changes.
- [ ] Implement portable orchestration, native provisioning/backends, and required consumer changes within approved scope; use baseline checkpoint verification during work.
- [ ] Verify native execution, offline reuse, differential/C15 invariants, and adverse path/permission/process cases across the approved matrix without Docker/WSL/VM/emulation.
- [ ] Record red/green and final conformance evidence, run repository quality/review gates, and prepare native release/signature/registry compatibility proof.
- [ ] Open the future implementation PR or coordinated scoped PRs to dev; close #460 only after native acceptance and publication/readback are complete.

## Post-merge lifecycle

- [ ] After actual implementation merge and acceptance, use openspec archive code-review-native-platform-execution; never archive this planning-only delivery.
- [ ] Remove the future implementation worktree only after its merge and retain required verification/release evidence.
