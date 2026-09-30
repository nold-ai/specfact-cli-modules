# Tasks: Dedicated macOS ARM64 Code Review Capsule

## 1. Planning revision

- [x] Narrow #460 to macOS ARM64, preserve Linux regressions, and defer other platforms.
- [x] Specify independence from blanket C15 delivery while retaining released semantics and real compatibility obligations.
- [x] Rebase design on Code Review 0.50.1 / #473, including project preparation and Mach-O/dyld handling.
- [x] Define feasibility gates, dependency-policy admission and native reliability/release scenarios.
- [x] Synchronize public issue scope and native dependency edges; retain open/Todo planning status.
- [x] Validate OpenSpec, planned evidence mapping, Markdown/YAML and applicable planning review; prepare the planning PR to dev.

## 2. Native feasibility (partially executed; production remains gated)

- [x] Run bounded native baseline, Seatbelt, App Sandbox and analyzer experiments; record results and outstanding blockers in NATIVE_RESULTS.md.
- [ ] Verify exact released core/module, layout #459, portable runtime #473, signed policy/artifact and consumer identities.
- [ ] Enumerate candidate macOS builds and CPython 3.11–3.13; identify native runners and physical-Mac smoke.
- [ ] Audit complete ARM64 Python/native/build dependency closure and resolve BasedPyright/Node prohibition without metadata or signature bypass.
- [ ] Evaluate signed Seatbelt and App Sandbox candidates against every FEASIBILITY.md proof group with positive controls.
- [ ] Prove preparation/build-hook boundaries, Mach-O/dyld/native extension behavior, plugins and coverage.
- [ ] Record isolation, startup, race, lifecycle, resource, cache and distribution results; freeze limits and support matrix only from proof.
- [ ] Resolve named consumer incompatibilities through bounded paired scope; do not wait for C15 solely by issue association.
- [ ] Review and approve backend, dependency sources, signing approach and bounded production interfaces. Stop if required evidence is missing.

- [x] Validate Docker-only artifact assembly with Darwin/ARM64 OCI metadata and explicit candidate status; keep native build/sign/test and protected GHCR promotion separate.

## 3. Production implementation (gated)

- [ ] Work in a fresh implementation worktree against the approved baseline/design; recheck ownership and dependencies.
- [ ] Add scenario-mapped focused tests, observe meaningful failures before production edits, and record failing-before and passing-after runs in TDD_EVIDENCE.md.
- [ ] Implement platform backend selection, signed native provisioning and versioned evidence without changing released review semantics.
- [ ] Implement native preparation, Mach-O/dyld loading, isolation/observation, lifecycle and cache enforcement.
- [ ] Run native complete-analyzer and pinned external-project acceptance plus Linux regressions; fix all actionable review findings.
- [ ] Run the mandatory touched-scope format, type-check, lint, YAML, bundle-import, signature/version, contract-test, smart-test, full-test and SpecFact Code Review gates; fix findings and record the results before release preparation.
- [ ] Verify consumer compatibility and applicable Apple distribution controls; prepare canonical signatures/version/registry changes.

## 4. Publication and completion (gated)

- [ ] Publish immutable signed macOS artifacts and compatible module/core changes through canonical release tooling.
- [ ] Repeat fresh ordinary-user customer installation, cold/offline warm matrix and Linux regressions against published identities.
- [ ] Document only proven combinations and rollback; close #460 only after acceptance.
- [ ] After actual implementation merge and acceptance, run openspec archive code-review-native-platform-execution; never archive this planning and feasibility revision.
