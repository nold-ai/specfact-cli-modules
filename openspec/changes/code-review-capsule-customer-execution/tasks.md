# Tasks: Customer Capsule Execution

Implementation authorized on 2026-09-12 Europe/Berlin in the existing dedicated worktree and PR #467. Release acceptance remains pending. Behavior work follows spec → mapped tests → actual failing evidence → production repair → passing evidence. Planning checks are recorded separately in CHANGE_VALIDATION.md.

## 1. Revalidate implementation readiness

- [x] 1.1 Refresh origin and establish a dedicated implementation worktree; read current governance, this accepted change, released baseline, and paired core #680 proposal.
- [x] 1.2 Refresh hierarchy metadata and verify #466 type, assignee, parent, labels, project/status, native blocked-by/blocking edges, and concurrent In Progress state before implementation.
- [x] 1.3 Freeze exact released core/module/ABI artifacts and runner identities; map each spec scenario to a test selector and preserve scope independently of C14 bookkeeping, C15 and native-platform work.

## 2. Reproduce and capture failing evidence

- [x] 2.1 Add hosted Ubuntu 24.04 x86-64 customer jobs for Python 3.11/3.12/3.13 with fresh user-owned installation/cache paths and explicit non-root assertions.
- [ ] 2.2 Install public released core and signed modules through documented commands; exclude publisher credentials, development links, source PYTHONPATH, signature bypasses and prefetch from the customer path.
- [ ] 2.3 Run independent clean/defective Git fixtures and the modules repository through the installed CLI; capture nonempty scope, actual required analyzer coverage, JSON and exit outcomes, including conditional/runtime mount fixtures with valid existing prerequisites.
- [ ] 2.4 Capture namespace-denied baseline evidence separately, probe the actual verified descriptor/tracing launcher, and identify/document a narrowly scoped supported host prerequisite before positive non-root reruns.
- [ ] 2.5 Identify the exact cp312 failing digest stage using clean/warm caches, umasks 022/077 and content/mode entry comparisons; preserve expected/actual identities without edits to trusted hashes.
- [ ] 2.6 Trace the reported directory error to exact argv/path/errno/syscall, distinguish host staging from sandbox destination/state writes, and exercise every mount variant.
- [x] 2.7 Record real commands, versions and failing outputs in TDD_EVIDENCE.md before each related production repair; unresolved hypotheses remain explicit.

## 3. Implement only reproduced causes

- [x] 3.1 Repair proven anonymous acquisition/cache or deterministic materialization defects and add actionable stage/ABI/integrity diagnostics.
- [ ] 3.2 Repair verified-launcher capability reporting and supported setup documentation without privilege fallback or broad host policy changes.
- [x] 3.3 Establish mount destinations before sealing composition, authenticate new structure in the appropriate identity, and route analyzer state into declared private mounts; retain fail-closed path/collision checks.
- [ ] 3.4 Preserve core handoff, signed-module validation, existing CLI/schema/assurance semantics, and protected-consumer separation; do not widen into native-platform or unrelated analyzer redesign.

## 4. Verify candidate behavior

- [ ] 4.1 Run mapped acquisition/cache-corruption, three-ABI/two-cache-root determinism, namespace permit/deny, destination-variant, private-write/denied-write, cleanup, and diagnostics regressions with passing-after evidence.
- [ ] 4.2 Complete the actual-analyzer three-ABI matrix, distinguishing expected fixture FAIL from infrastructure UNKNOWN and retaining real repository findings.
- [ ] 4.3 Run required formatting, typing, lint, YAML/import, contract/smart/full-test gates and strict OpenSpec validation for the touched scope.
- [ ] 4.4 Generate fresh SpecFact review JSON with --bug-hunt and appropriate scope/enforcement; remediate every finding or document a rare approved exception, and record exact commands/timestamps.

## 5. Publish and accept later

- [x] 5.1 Update customer troubleshooting docs and affected published links; retain non-root setup, identity diagnostics and recovery guidance.
- [ ] 5.2 Publish changed OCI assets under new immutable identities and update current lock/resource bindings, patch version, module signatures and registry consistently through canonical tooling; preserve historical checkpoints and payloads.
- [ ] 5.3 Verify filesystem payload signatures/version bumps and complete implementation PR/review/merge gates with recorded release identities.
- [ ] 5.4 Repeat the full customer matrix against the actual public signed release with cold and verified warm caches; close #466 only after all required coverage and expected outcomes pass.
- [ ] 5.5 After implementation, merge and release acceptance, finalize with openspec archive code-review-capsule-customer-execution and update change order. Retain rollback/recovery evidence.
