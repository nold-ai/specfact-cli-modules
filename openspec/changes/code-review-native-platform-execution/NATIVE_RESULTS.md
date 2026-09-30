# Native macOS ARM64 experiments — 2026-09-30

## Decision

Production decision: NO-GO for the tested lifecycle designs. Native execution and bounded confinement are demonstrated, but the complete feasibility gate has not passed. These experiments ran on the physical ARM64 Mac, without Docker or Rosetta. The released CLI still returns incomplete evidence on macOS. Do not advertise capsule support or select a production backend from these results.

Confidence is high for the recorded fixture observations and low for generalizing to arbitrary customer projects. Evidence covers one OS build. The tests use existing pyenv interpreters and explicitly identified Homebrew libraries; this is a prototype dependency, not an approved fallback or a hermetic runtime.

## Environment and baseline

- macOS 27.0.1 (26A434), Mac17,9, native ARM64.
- Released core 0.55.4 and Code Review module 0.50.1.
- CPython 3.12.13 for analyzer/Seatbelt tests; App Sandbox also exercised CPython 3.11.15. CPython 3.13 was unavailable and remains untested.
- Helpers were compiled for ARM64 and ad-hoc signed. `security find-identity -v -p codesigning` returned `0 valid identities found`, including outside the agent sandbox. Developer ID, notarization and customer installation remain untested.
- The baseline invocation was `specfact code review run sample.py --enforcement full --json --out review.json`, in an isolated temporary Git repository with development overrides removed. Exit 1, assurance UNKNOWN, diagnostic `unsupported_controller_platform` for all ten analyzer members. No analyzer ran through the released capsule pipeline.

## Confinement experiments

The minimal Seatbelt helper closes descriptors 3 and above, applies a deny-default profile, then executes the interpreter. The profile permits declared input reads and private output writes. The current helper/profile is experimental: broad metadata, system-library, process and signal allowances have not passed a production authority review; standard descriptors, IPC, resource bounds and race-resistant launch are not proven.

Initial interpreter startup aborted. An explicit read allowance for the root directory itself, plus the identified interpreter/library paths, allowed startup. A crash or denied initialization was never counted as successful confinement.

Ten positive-controlled Seatbelt cases passed: native startup, allowed input read, denied canary read, allowed private write, denied canary write, denied symlink escape, denied listening socket, denied child canary read, closure of an inherited canary descriptor and denied outbound loopback connection. See [initial cases](EVIDENCE_SUMMARY.md#isolation) and [descriptor/network cases](EVIDENCE_SUMMARY.md#isolation). These tests do not establish denial of every IPC/network mechanism.

The independent App Sandbox experiment found that a bare executable failed before `main`, while an ad-hoc signed app bundle entered the sandbox and launched both native Python versions. Private writes succeeded; sibling canary access and loopback connect/bind failed with EPERM. The temporary entitlement exceptions explicitly name interpreter and linked-library locations. This does not establish that the same entitlement/package design is appropriate for distribution. See [App Sandbox evidence](EVIDENCE_SUMMARY.md#isolation).

## Dependency and analyzer experiments

The dependency experiment verified Mach-O ARM64 for Python, Ruff, Semgrep core, the CrossHair extension, Z3 and upstream Node. All 69 installed Python distributions in the selected subset matched the existing lock versions; this is not a complete admitted macOS lock. No prohibited Node wheel distribution was installed.

| Analyzer | Version | Unconfined clean fixture | Unconfined defective fixture |
| --- | --- | --- | --- |
| Ruff | 0.15.12 | Exit 0 | Exit 1, F401 |
| Semgrep | 1.144.0 | Exit 0, no finding | Exit 0, one finding |
| CrossHair | 0.0.109 | Exit 0 | Exit 1, counterexample |
| BasedPyright, experimental npm delivery | 1.39.10 | Exit 0 | Exit 1, assignment error |

Z3 distribution 5.1.0.0 also solved the explicit SAT fixture. See [dependency metadata and blockers](EVIDENCE_SUMMARY.md#analyzers-and-dependencies). Semgrep's successful exit on a finding is expected for the tested command; finding content must be inspected.

BasedPyright's Python package still requires the prohibited `nodejs-wheel-binaries` distribution. Running its upstream npm package with upstream Node 24.16.0 proves an experimental execution path only. Admission requires provenance, licensing, metadata and dependency-policy review. Z3's wheel filename and internal WHEEL tags disagree; `pip check` fails. Do not suppress that failure or rewrite installed metadata to claim compatibility.

## Confined analyzer and lifecycle follow-up

All eight clean/defective analyzer cases also passed under the Seatbelt helper, with the expected exits and findings. Semgrep initially failed because Python's SSL extension needed two Homebrew OpenSSL dylibs. Explicit read permissions for those resolved files fixed startup; the default network denial remained. Dependency-write and network-bind probes failed as intended, private-state writes succeeded, and the dependency configuration hash remained unchanged. See [commands and outputs](EVIDENCE_SUMMARY.md#analyzers-and-dependencies), [summary](EVIDENCE_SUMMARY.md#analyzers-and-dependencies), and [integrity probes](EVIDENCE_SUMMARY.md#analyzers-and-dependencies). This does not exercise all ten released analyzer members through the CLI.

The independent lifecycle tests reproduced surviving detached descendants after process-group timeout and cancellation. A corrected native supervisor passed the bounded timeout, cancellation and controller-death fixtures while it remained alive. Killing that supervisor left both worker and descendant alive. `NOTE_TRACK` registration returned ENOTSUP (45); the tested replacement uses `NOTE_FORK`/`NOTE_EXIT` plus child enumeration. Enumeration, reparenting, PID reuse, normal-parent-exit and supervisor-death gaps remain. The measured cleanup observations are not worst-case guarantees. See [lifecycle results](EVIDENCE_SUMMARY.md#lifecycle).

All 38 recorded test-process PIDs were absent in the [final independent audit](EVIDENCE_SUMMARY.md#lifecycle). Escaped fixture processes were cleaned using their exact recorded PIDs after checking identity.

The [Z3 remedy investigation](EVIDENCE_SUMMARY.md#analyzers-and-dependencies) found a binary minimum of macOS 13.3. Rewriting the tag to 13.0 would overstate compatibility. A consistently tagged replacement or genuine rebuild is a candidate for review; neither was admitted or used to hide the failing check in that initial investigation. The later derived-candidate experiment below is separate.

## Docker assembly and lifecycle refinement

A COPY-only `FROM scratch` build using Docker Buildx 0.37.1 / BuildKit 0.33.0 on the local Linux ARM64 Docker daemon exported a Darwin ARM64 OCI archive. Both the image config and index platform identify `darwin/arm64`. Descriptor digests/sizes and the layer diff ID matched. Extracted Mach-O bytes and executable mode matched the native input, its ad-hoc signature verified, and native execution returned the expected Darwin ARM64 message. This was a tiny native fixture, not the complete capsule. See [Docker proof](EVIDENCE_SUMMARY.md#docker-candidate) and [config](EVIDENCE_SUMMARY.md#docker-candidate).

A second lifecycle experiment denied `fork`, `vfork` and `posix_spawn` with EPERM while threads and separately orchestrated workers ran. Signal restrictions denied worker-to-controller signaling. Killing the ordinary supervisor still left the root alive. Retaining a tracer caused the single worker to disappear when the tracer died in three tested cases, including `setsid` and another `exec`. Three restricted pytest canaries passed, but a real subprocess-dependent test failed. This narrower no-fork approach cannot preserve the arbitrary project subprocess contract and is not adopted as a silent capability downgrade. See [no-fork tests](EVIDENCE_SUMMARY.md#lifecycle) and [tracing/pytest tests](EVIDENCE_SUMMARY.md#lifecycle).

A follow-up tested traced roots with `fork`, `vfork` plus `execve`, and `posix_spawn`, each with and without descendant `setsid`. All six roots were traced; no descendant inherited tracing. Killing the tracer killed each root but left every descendant alive, reparented to PID 1 with a growing heartbeat. This rejects recursive tracing as a solution to the current contract. `NOTE_FORK` supplied the parent PID and `data=0`, with no child-attachment barrier. All 18 fixture PIDs were absent after exact-PID cleanup. See [traced descendant failures](EVIDENCE_SUMMARY.md#lifecycle).

## Z3 packaging correction candidate

A separate downstream wheel `z3_solver-5.1.0.0+specfact.1-py3-none-macosx_14_0_arm64.whl` corrects the packaging metadata with an explicit local version and provenance. Filename/internal tags agree, native contents and copyright notices remain byte-identical, and RECORD is regenerated and verified. Two repacks using the same fixed tooling produced identical bytes. A fresh baseline reproduced `pip check` exit 1; a separate fresh candidate environment passed `pip check`, Z3 solver fixtures and CrossHair clean/defective checks. Existing environments and upstream artifacts were not edited.

See [derivation identities](EVIDENCE_SUMMARY.md#analyzers-and-dependencies) and [installation and execution results](EVIDENCE_SUMMARY.md#analyzers-and-dependencies). This fixes the observed metadata incompatibility in a candidate, not the complete admission gap. Execution on actual macOS 14, redistribution-license review, confinement and signed policy admission remain unproven. The original wheel has MIT metadata and copyright notices but no standalone full license file; a redistribution review is still needed. Only macOS 27.0.1 / CPython 3.12.13 was exercised. BasedPyright's source-policy review remains separate.

The [local candidate build guide](candidate-build/README.md) reproduces native hello compilation, ad-hoc signing and Docker assembly without publishing. The initial verifier suite contained 32 focused rejection/positive cases; after review regressions through the offline OCI graph schema correction, all 203 cases pass on native CPython 3.11 and 3.14 (see [TDD_EVIDENCE.md](TDD_EVIDENCE.md)). The [actual local output](EVIDENCE_SUMMARY.md#docker-candidate) always marks production eligibility false. It is a bounded tiny-fixture inspector, not a complete capsule builder or GHCR publisher.

## Remaining gates and failure controls

- Detached descendants can outlive process-group termination. Require independently verified containment and cleanup; do not substitute process polling or cooperative PID reporting for a race-resistant security contract.
- Ambient interpreter/library linkage prevents hermetic distribution. Build and admit a relocatable native closure, then repeat the loading and tamper tests with host package-manager paths unavailable.
- The signed customer route is unproven. Use an approved signing identity and delivery design, then test a fresh ordinary-user installation without bypassing OS protections.

Full analyzer integration, project preparation/build hooks, pytest plugins and coverage, all project-manager corpora, cache integrity/concurrency, verification-to-launch races, resource bounds, complete lifecycle cleanup, consumer evidence and Linux regression suites remain required. None is marked passing by these smoke tests.

This is a substantial backend/packaging effort; these observations do not justify a delivery estimate. Rollback is to retain the released Linux backend and withdraw any experimental macOS publication. No production assets, module signatures or runtime selection were changed by these experiments.

## Evidence handling

Raw JSON commands, outputs, source/stored digests and local paths are retained under the ignored `.specfact/macos-feasibility/raw-evidence/` directory and the original local experiment directories. They are not part of the PR. The [reviewed evidence summary](EVIDENCE_SUMMARY.md) records the relevant observations and limits. The candidate build guide and focused tests provide reproducible packaging checks; historical native experiment summaries are observations, not a checked-in production acceptance suite.

Evidence validation: strict OpenSpec validation, structural Markdown checks (existing MD013/MD060 exclusions), Git whitespace checks, JSON parsing and stored SHA-256 digest checks passed. Production quality/acceptance gates were not run or claimed passing; the native baseline remains UNKNOWN. These changes record bounded feasibility and candidate tooling; they do not approve a production backend.

Next: resolve the lifecycle and dependency admission failures, complete the remaining proof groups, and approve the bounded production design. Keep #460 open and do not archive the change.
