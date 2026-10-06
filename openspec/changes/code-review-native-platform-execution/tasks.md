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
- [x] Prove fixed-bootstrap creation-to-tracing ownership on the physical host without relaxing startup cleanup; matrix and complete admission remain separate gates.
- [x] Implement a fixed-fixture native broker/bootstrap with tests before implementation.
- [x] Pass 100 repetitions of six startup stages on the physical ARM64 host, with independent tracing/birth observation and deny-default native probes; retain matrix and full-lifecycle gates.
- [x] Implement private bounded broker launch/wait/signal/cancel fixtures and exercise CLI death, malformed requests, timeouts and concurrent invocations on the physical host; retain full boundary admission below.
- [x] Execute both pinned Semgrep rule packs against clean/defective fixtures inside the traced deny-default boundary with exact native dependency grants.
- [ ] Verify exact initial-distribution native signatures, hardened-runtime settings and narrow entitlements before boundary acceptance; Apple credentials are not required.
- [x] Pass private fixture control/lifecycle acceptance on the physical host: 100 repetitions of 12 cases plus 19 protocol checks, with native-clock EOF attribution and exact source snapshots.
- [ ] Pass complete signed boundary admission, including tracing/IPC/loader escapes, hard resource limits and the supported OS matrix.
- [ ] Integrate managed Python/multiprocessing and pinned native-tool adapters without weakening the kernel boundary.
- [ ] Pass every required analyzer and existing pip/Hatch/uv/Poetry corpus; preserve unsupported-operation diagnostics.
- [ ] Admit Node/npm, Semgrep and Z3 closure, Mach-O loading, signed caches and versioned evidence.
- [ ] Implement first-use acquisition, offline reuse and compatibility rejection; repeat signed customer installation.
- [ ] Complete native ARM64 CI and physical-Mac proof plus Linux regression, all repository gates and independent review.
- [ ] Prepare patch 0.51.1 for completion/correction of the released 0.51.0 promise; sign and publish through CI only after acceptance, and update registry identities from actual release bytes.
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

### Hosted fixed-boundary acceptance

- [x] Configure explicit ARM64 macOS 14/15/26 CI with exact OS/build, ordinary-user GUI launchd, serial 100-round startup/control, sanitized summaries and no release permissions.
- [ ] Record actual PR merge SHA, platform identity and passing hosted suite results; resolve runner availability without dropping mandatory coverage.

### Owned Mach signal exception candidate

- [x] Replace the control-fixture BSD stop transport with bounded owned Mach exception handling; capture exact SDK/generated source provenance.
- [ ] Prove native signal semantics, startup holds and broker-death cleanup against exact ad-hoc hardened builds; retain all hosted failures and require 100 repetitions on each candidate OS.

### Image-bound executable handoff

- [x] Record the real signed confined Mach exec failure and specify one-use dynamic image admission before implementation.
- [x] Prove replacement-before-initializer ordering, inherited confinement, genuine traps, failed exec, substituted targets and second-image rejection on the physical Mac; hosted proof remains below.
- [ ] Pass 100 repetitions of cancellation, connection loss and broker death both at the verified replacement stop and after target entry on the physical Mac and macOS 14/15/26.
- [x] Bind four final signed fixture artifacts, shared headers, dynamic requirements and image-stop evidence to the revised experimental receipt; old receipts cannot approve the new handoff.
- [ ] Integrate actual admitted interpreter/analyzer execution only after this subset and the remaining full boundary gates pass.
## Project-driven preparation correction — 2026-10-04

- [x] Synchronize #460, proposal/design/spec/evidence and change order with caller-driven discovery and full-VM acceptance.
- [x] Return structured JSON discovery failures and update the installed skill.
- [x] Capture failing unfamiliar-project preparation without a catalog entry; implement a real cold pip preparation and complete review (physical CPython 3.11 candidate; complete release matrix remains below).
- [x] Implement authentic Hatch/uv/Poetry preparation and managed subprocess adapters; prove all four managers' cold/offline preparation on the physical CPython 3.11 candidate without catalog dependence. Complete corpus and matrix acceptance remain below.
- [ ] Validate all ten analyzers, manager corpus, plugins, coverage and compatible native extensions against unrelated projects.
- [ ] Pass clean ordinary-user installation in an independent macOS ARM64 VM or Mac, supported macOS matrix and Linux x86-64 CI VM regression.
- [ ] Run final repository gates and independent security/defect review; update PR #489 and actual current-head reviews with CI-only signing follow-up.

## Delivery continuation — 2026-10-06 (Europe/Berlin)

Earlier umbrella tasks remain unchecked until their complete acceptance passes.
The following bounded checkpoint preserves historical failures and does not
replace sections 3, 4 or 6. Exact facts: DELIVERY_CHECKPOINT_2026-10-06.md.

- [x] Reopen #460, restore Todo, verify parent/labels/project/dependencies and create one isolated codex worktree from current origin/dev; confirm main release files are present.
- [x] Specify, reproduce and correct missing ordinary-output diagnostics; preserve JSON and literal rendering.
- [x] Specify, reproduce and add keyless deterministic archive/manifest assembly; use no local publisher key.
- [x] Assemble actual cp311/cp312/cp313 empty-entitlement archive candidates; retain their extension-loading rejection and unsigned identities.
- [x] Run actual ten-analyzer clean/defective fixtures and plugin/coverage/native-extension observers for each ABI using the existing library-loading experiment; retain candidate-only status.
- [x] Reproduce generated controller bytecode changing the sealed payload identity; exclude exactly the signing boundary's cache/bytecode categories with four regression cases.
- [x] Run full unit/contract/smart suites and bounded independent security/defect review; these do not complete the UNKNOWN capsule review gate.
- [ ] Complete current-head Linux CI and obtain a non-UNKNOWN required SpecFact review; any local deferral requires explicit human approval under the quality rule.
- [ ] Admit exact native loader entitlements, complete dependency policies and four-manager upstream corpus with final artifact bytes.
- [ ] Add the protected native build/accept/sign/stage workflow and its protected environment; all signing remains CI-only and candidate code cannot control signing authority.
- [ ] Populate authenticated cp311/cp312/cp313 catalog resources from accepted, CI-signed immutable GHCR artifact identities.
- [ ] Pass final-artifact macOS 14/15/26 x cp311/cp312/cp313 and independent signed installation, cold/offline reuse, physical changecost/unrelated project and Linux regression.
- [ ] Open reviewed implementation PR to dev after applicable gate/approved-deferral handling; complete current-head findings and human merge/promotion review.
- [ ] After authorized publication, repeat canonical fresh installation, close #460 and archive with openspec archive.

- [x] Correct the hosted independent reviewer's unavailable literal version pin to the signed published 0.51.0 baseline; retain isolation and all required review execution.
- [x] Reproduce and correct staged bug-hunt activation and explicit matching-test ambiguity; preserve required coverage and analysis budgets.
- [x] Add bounded tracked public finding locations and fixed native connection failure classes so hosted failures remain diagnosable without publishing private reports.
- [ ] Obtain current-head hosted review completion and resolve every valid changed finding; fixed macOS14/15/26 boundary fixtures passed at dc8eb069, while final native and physical-Mac acceptance remain open.

- [x] Open draft PR #498 toward dev under the explicit local capsule-only deferral; keep hosted review and human merge/promotion pending.

- [x] Reduce introduced builder/workflow complexity while preserving exact controlled archive/manifest/summary bytes and public maintainer arguments.
- [x] Specify/reproduce fixed missing-report/timeout diagnostics and execution-error priority within the unchanged public200-location cap.
- [x] Add explicit authenticated Darwin-only Z3 specfact.2 projection; preserve historical specfact.1 bytes, update only candidate Z3 lock/policy identities and pass all three complete offline closures and confined analyzer/parity fixtures. No production admission.


### Incomplete runtime correction — 6 October 2026

- [x] Specify and reproduce maintained uv signature/provenance drift; preserve verified bytes and reject changed/missing preparation or assembly receipts.
- [x] Align nested Python environment exclusion across source capture and ordinary worktree identity, preserving selected/tracked input and alias rejection.
- [x] Retain bounded native pytest execution and coverage observations in local CLI reports with project-origin-v1 authority.
- [x] Materialize valid contained source aliases before native preparation sealing, preserving empty directories and source identity checks.
- [x] Run initial real cp313 candidate module-command reviews and diagnose insufficient completion-checker PASS from Pylint fatal/style misclassification; retain actual offline/test/coverage observations without claiming release acceptance.
- [x] Preserve executable modes and safely clean owned read-only source aliases with failing-before/passing-after regressions.
- [x] Retain verified relocated frozen stdlib source for Astroid and classify every fatal Pylint diagnostic as incomplete evidence.
- [x] Correct real Hatch source inference when generated wheel modules coexist with byte-identical project sources; retain size/byte/ambiguity rejection.
- [x] Retain actually observed Poetry distributed-test selectors without inventing requested selectors or protected authority.
- [x] Recheck actual four-manager cp313 project commands; retain fixture trust, actual findings and remaining final-byte acceptance limits.
- [x] Preserve sealed generated imports and ordinary venv source packages; bound exact suffix matching and resolve measured introduced complexity.
- [x] Record stable local current-source repository gates and bounded independent review.
- [ ] Verify fresh CI signature and exact-head hosted review for the runtime correction.
- [ ] Complete final current-source mandatory gates, CI-only module signing and exact-head blocking review; keep prior hosted failures.

- [x] Reproduce and preserve blocking timeout exit124; wire existing capsule progress and bounded fixed-analyzer timeout diagnostics without exposing raw content or changing budgets.

- [x] Reproduce actual cp311 Hatch hook launch failure and compact managed uv requests with native parser/literal round-trip and unchanged-budget rejection tests.
- [x] Rebuild the changed managed uv image, verify full provenance, and repeat exact archive manager execution; retain old candidate failures.


### Owner-approved release implementation continuation — 6 October 2026

- [x] Record explicit acceptance of normal initial trust warnings while retaining all integrity/boundary gates and optional Apple follow-up.
- [x] Implement exact archive/profile/acceptance validation, protected data-only signing and authenticated catalog preparation with RED/GREEN tests.
- [x] Implement reproducible secret-free native builds and all nine final-byte acceptance jobs; prove the real cp312 build and local execution.
- [ ] Execute and pass all nine hosted final-byte acceptance cells at the reviewed source identity.
- [x] Implement independent signed installed-customer cold/offline execution, exact composition comparison and read-only quarantine observation; preserve unattended dialog limits.
- [ ] Execute independent ordinary installation after approved public catalog/module publication and record actual trust behavior.
- [ ] Configure reviewed protected signing/staging environments and prepare human promotion with immutable identities; do not auto-merge or publish.

Runbook and exact candidate limitations: [NATIVE_RELEASE.md](NATIVE_RELEASE.md). Implementation checkmarks do not replace pending release acceptance.
