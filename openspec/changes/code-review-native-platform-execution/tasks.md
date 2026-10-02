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
- [ ] Evaluate the initial-distribution managed broker/bootstrap against every FEASIBILITY.md proof group with positive controls; preserve earlier alternatives as historical evidence.
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

## 5. Historical no-admin XPC execution-boundary follow-up (rejected)

- [x] Check in a native app/XPC/fixture harness and independent observer with negative controls.
- [x] Reproduce lifecycle failures before candidate implementation; test the physical ARM64 Mac.
- [x] Reject the candidate on any surviving descendant; require mechanism review and 100 race repetitions before positive admission.
- [ ] Preserve production gating; add project-runtime integration only after lifecycle admission.

## 6. Managed-process delivery (owner approved 2026-10-02)

- [x] Record managed processes and automatic first-use acquisition; retain historical failures.
- [x] Synchronize #460 and planned requirement evidence with the approved revision.
- [x] Implement fail-closed optional Apple signing preflight with focused RED/GREEN tests; credential availability is not boundary acceptance.
- [ ] Resolve the creation-to-tracing ownership gap recorded in MANAGED_BOUNDARY_STATUS.md without relaxing startup cleanup.
- [ ] Implement a fixed-fixture native broker/bootstrap with tests before implementation.
- [ ] Verify exact initial-distribution native signatures, hardened-runtime settings and narrow entitlements before boundary acceptance; Apple credentials are not required.
- [ ] Pass independent signed lifecycle/startup/escape/resource proof and 100 race repetitions.
- [ ] Integrate managed Python/multiprocessing and pinned native-tool adapters without weakening the kernel boundary.
- [ ] Pass every required analyzer and existing pip/Hatch/uv/Poetry corpus; preserve unsupported-operation diagnostics.
- [ ] Admit Node/npm, Semgrep and Z3 closure, Mach-O loading, signed caches and versioned evidence.
- [ ] Implement first-use acquisition, offline reuse and compatibility rejection; repeat signed customer installation.
- [ ] Complete native ARM64 CI and physical-Mac proof plus Linux regression, all repository gates and independent review.
- [ ] Bump module minor version, manifests/signatures, changelog and registry only for the completed capability.
- [ ] Open implementation PR to dev and resolve current-head reviews/checks; no automatic merge or publication.

## 7. Parallel native compatibility (owner approved 2026-10-02)

- [x] Package pinned Node/npm BasedPyright offline; verify upstream Node release signature and native clean/defective behavior.
- [x] Implement bounded static Mach-O architecture/load-path inventory and negative tests; inspect the actual Node/Z3 payloads.
- [x] Produce an explicitly versioned, deterministic Z3 metadata correction with unchanged native/source/license bytes and provenance.
- [x] Generate complete hash-pinned analyzer candidate locks for CPython 3.11–3.13; install normally and pass dependency checks.
- [x] Run every actual analyzer adapter against fixed clean/defective fixtures on physical ARM64 macOS for all three Python versions.
- [ ] Complete final repository gates and independent review of this compatibility checkpoint; retain any explicit failures in evidence.
- [ ] Run the full four-manager project corpus inside the admitted native execution boundary; fixed-fixture compatibility is not this acceptance.

See NATIVE_COMPATIBILITY_RESULTS.md for exact scope, versions and evidence. These
items do not complete production tasks in sections 3, 4 or 6.

## 8. Optional Apple distribution split (owner approved 2026-10-02)

- [x] Replace Developer-ID-first admission with exact initial-distribution acceptance; retain every security/lifecycle gate.
- [x] Create optional #488 and `code-review-macos-developer-id-distribution`; #460 blocks the follow-up, never the reverse.
- [x] Route default prerequisite checks without Apple credential probes; retain explicit optional Apple checks and test proof limits.
- [x] Validate both changes, planned evidence mappings, issue dependency readback and relevant repository gates.
- [ ] Prove cold/offline installation on a separate Mac or clean independent macOS environment with default protections; never require quarantine stripping or security overrides.

Paid enrollment, Apple certificate management, notary credentials, notarization,
applicable stapling and certificate renewal/revocation belong only to #488.
