# macOS ARM64 feasibility gate

## Distribution-signing split — 2026-10-02 (Europe/Berlin)

This owner-approved revision supersedes the earlier Developer-ID-first milestone.
Optional [#488](https://github.com/nold-ai/specfact-cli-modules/issues/488) /
[`code-review-macos-developer-id-distribution`](../code-review-macos-developer-id-distribution/proposal.md)
is blocked by #460; it does not block this change, shipment or publication.
"Signed runtime" in this change means native signatures plus an authenticated
SpecFact payload manifest, not a mandatory Apple publisher identity. Preserve
historical experiments as evidence, without treating their old signing policy as
current acceptance. Sandbox, dependency, lifecycle and real-installation gates
remain mandatory. Apple credentials do not solve the startup ownership gap.

## Managed-process revision — 2026-10-02 (Europe/Berlin)

The owner approved a managed-process contract for native macOS ARM64. This
supersedes unrestricted project subprocess compatibility; earlier failed
experiments remain historical evidence, not implementation of this revision.
This approved scope is normative for the current milestone; historical Seatbelt,
App Sandbox and XPC experiments neither mandate unrestricted subprocess support
nor establish acceptance of the managed candidate.
The first release still requires all ten analyzers and the pip, Hatch, uv and
Poetry corpus, plugins, coverage and compatible ARM64 extension imports.

The normal command automatically downloads and verifies a prebuilt signed
runtime on first use, shows progress and subsequently reuses verified caches
offline. Customers need no Docker, VM, Homebrew, Xcode, sudo or separately
installed daemon. Unsupported process behavior produces actionable incomplete
evidence, never host execution or PASS with missing required evidence.

The candidate must use an invocation-scoped native broker that owns every
worker directly. Each worker must establish tracing and a versioned Seatbelt
policy before project code runs. Kernel restrictions must deny direct
fork/vfork/posix_spawn and tracing/IPC escapes; compatibility adapters must
request bounded launches through private inherited channels. Python interception is not the security boundary. Acquisition,
build/preparation, sealed analyzers and project execution remain separate domains.

The first milestone is boundary proof using the exact initial distribution
configuration: build-time ad-hoc signatures for our native components, verified
upstream signatures where applicable, and SpecFact-signed manifests covering the
final payload bytes. Record and test hardened-runtime settings, narrow reviewed
entitlements, tracing and confinement together. Paid Developer ID membership and
notarization are optional follow-up work; missing Apple credentials do not block
compilation, execution, shipment or canonical GHCR publication.
Independently observe every startup transition, broker/CLI death, timeout,
cancellation and concurrent requests, with no survivor after five seconds and
100 repetitions per lifecycle race. Invalid native signatures, failed tracing or
confinement, or missing mandatory evidence reject the candidate. These lifecycle
bounds are mandatory admission gates, not tunable defaults.
Production integration, version 0.51.0 (or next available minor), registry and
publication changes follow the gate and complete acceptance, not this revision.

Implementation checkpoint: [MANAGED_BOUNDARY_STATUS.md](MANAGED_BOUNDARY_STATUS.md)
preserves the historical creation-to-tracing gap and optional Apple credential
tool. STARTUP_BOUNDARY_RESULTS.md records the passing physical-host subset;
CONTROL_BOUNDARY_CONTRACT.md and SEALED_ANALYZER_CONTRACT.md carry the executable
private control and analyzer checkpoints. Complete admission remains unproven.

## Status and decision rule

Historical feasibility was partially executed on native ARM64 macOS on 2026-09-30, with the rejected XPC follow-up on 2026-10-01 (Europe/Berlin). The approved managed-process milestone has not passed. See [native experiment results](NATIVE_RESULTS.md) and the recorded evidence. Initial launch, confinement and analyzer experiments ran; the complete gate has not passed. No backend approval or production support claim follows from these results. This document remains the execution contract for the outstanding milestone.

Run harmless fixtures for the initial-distribution managed broker on native ARM64 macOS under an ordinary user. The earlier Seatbelt/App Sandbox comparison and XPC follow-up are retained historical evidence; do not rerun them as alternative admission routes or reinterpret their failures as managed-process proof. Record exact OS build, hardware/process architecture, Python ABI, core/module/runtime/artifact/policy identities, command, expected outcome, observed outcome and diagnostic. Negative cases require a successful positive control; parser/startup failure is not confinement proof.

CPython 3.11–3.13 is the candidate matrix. Enumerate available macOS builds before execution; advertise only the tested combinations. Include a physical-Mac smoke and distinguish CI virtualization from application dependence on a VM. No Rosetta or emulated interpreter/library satisfies native acceptance.

## Required proof groups

| Group | Positive control | Negative/adverse cases | Required decision evidence |
|---|---|---|---|
| Launch and loading | Signed helper starts native interpreter and admitted extension | Missing helper, x64-only binary, dyld injection, pre-confinement initializer, inherited FD/IPC access | Confinement active before untrusted code; explicit Apple system-library allowance and actual load origins |
| Filesystem and network | Declared input read and private output write succeed | Host secret canaries, writes outside roots, symlink redirection, outbound/listening sockets, inherited sockets and undeclared IPC | Denial attributable to policy; source and sealed payload unchanged |
| Lifecycle and bounds | Broker-managed direct workers complete | Every startup transition, broker/CLI death, timeout, cancel, concurrent requests, direct fork/vfork/posix_spawn and detachment attempts, resource exhaustion | Kernel denies worker-created descendants; independent observation finds no survivor after five seconds; 100 repetitions per lifecycle race and enforced resource limits |
| Project preparation | Pinned pip/pip-tools, Hatch, uv and Poetry projects build/test with plugins and coverage | Build hook host access, credential access, undeclared downloads, incompatible extensions | Separate acquisition/build/analysis policies and preserved project pins |
| Native closure | ARM64 extension and declared dylibs load | Missing or wrong-slice dependency, unsafe rpath, substituted dylib, prohibited Node package | Complete policy-admitted Mach-O/Python closure and loader behavior |
| Cache and integrity | Cold install and verified offline warm use | Corrupt, stale, unbound, mixed, interrupted and concurrent caches; verification-to-use swaps | Atomic publication, no partial reuse, race-resistant launch and policy-bound identities |
| Customer distribution | Fresh CLI/GHCR install on a separate ARM64 Mac or clean independent macOS environment | Quarantine, invalid native signatures, third-party extension rejection, paths with spaces/Unicode, case-insensitive APFS and permissions | Default-protection route works without Apple credentials, local re-signing, build tools, sudo, quarantine stripping or security overrides |
| Review and regression | All ten analyzers and real pip/pip-tools, Hatch, uv and Poetry test slices, plugins, coverage and compatible ARM64 extensions | Deliberate defects, skipped/empty required evidence, unsupported consumer | Expected released verdicts, honest OS-specific outcomes and passing Linux regression matrix |

## Admission and production approval checklist

- Resolve BasedPyright's direct prohibited Node distribution dependency and the complete native closure; audit replacement metadata, provenance, licenses and build inputs.
- Identify any concrete report/runtime consumer incompatibility and the bounded paired change needed. C15 is not a blanket prerequisite.
- First pass exact initial-distribution native-signature, hardened-runtime/entitlement, tracing and confinement proof. Missing Apple credentials do not block; invalid signatures or absent boundary evidence do. Developer ID and notarization are optional #488 follow-up work.
- Freeze the backend and profile version, exact supported macOS/ABI matrix, runtime sources, Apple signing/distribution method, trust boundaries, observation limits and remaining resource bounds. Preserve the mandatory five-second survivor bound and 100 repetitions per lifecycle race.
- Require all ten analyzers and the full four-manager corpus for the first release; actionable incomplete evidence for unsupported behavior is not a waiver of these acceptance requirements.
- Record all group results and outstanding failures. A required failure or unresolved capability means no production approval; retain evidence and propose a reviewed correction.
- Approve a bounded production design only after required feasibility groups pass. Final analyzer corpus and public signed-installation acceptance must be repeated on the production candidate/publication.
- Use current-run results and concise notes. Planned requirements inspection is not executable proof, and no historical RED ledger or optional seal is required.
