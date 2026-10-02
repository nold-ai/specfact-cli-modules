# Design: Dedicated macOS ARM64 Code Review Capsule

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

The first milestone is release-signed boundary proof: Developer ID, hardened
runtime, tracing and notarization must work together. No ad-hoc fallback is an
admission result. Independently observe every startup transition, broker/CLI
death, timeout, cancellation and concurrent requests, with no survivor after
five seconds and 100 repetitions per lifecycle race. Missing credentials block
signed execution before a substitute candidate is compiled or run; failed signed
tracing or confinement rejects this candidate. The five-second bound and 100
repetitions per lifecycle race are mandatory admission gates, not tunable defaults.
Production integration, version 0.51.0 (or next available minor), registry and
publication changes follow the gate and complete acceptance, not this revision.

Implementation checkpoint: [MANAGED_BOUNDARY_STATUS.md](MANAGED_BOUNDARY_STATUS.md)
records the unresolved creation-to-tracing ownership gap and signing prerequisite
tool. The candidate has not passed admission.

## Baseline and product boundary

The ordinary `specfact code review run` and existing runtime inspect/prepare commands select the backend automatically. This delivery targets macOS ARM64; Linux x86-64 remains the regression baseline. Windows, Intel macOS and Linux ARM64 are deferred. No Docker, WSL, VM, Rosetta or CPU emulation is a customer runtime prerequisite.

Start feasibility from the released Code Review 0.50.1 / #473 implementation and verified #459 layout correction; record exact compatible core/module versions, commits, signatures and policies. Preserve released scope, findings, differential classification and status/exit behavior. C15 #417/core #679 is independently scheduled, not a prerequisite. New native producer/consumer interfaces require explicit versioning and compatibility tests; old protected consumers must reject unknown evidence instead of interpreting it as Linux identity or protected PR authority.

## Architecture boundary

Keep portable review logic shared. Introduce a bounded platform backend responsible for capabilities, native provisioning, path layout, preparation, launch, observation, cleanup and result identity. Exact interfaces are frozen after feasibility; this revision does not approve public CLI/schema changes.

The existing Linux implementation uses Bubblewrap, ELF descriptors, /proc observation, ptrace and /opt/specfact mounts. macOS cannot reuse those claims. Its project-runtime path must inventory Mach-O slices, dylib dependencies and dyld load origins, account for Apple system libraries/shared caches, and use relocatable paths under user-owned storage. Never require writes to system roots or silently source libraries from Homebrew.

Carry forward #473's manager discovery, source locks, worker separation, pytest plugins and coverage. Acquisition, build backends, package-manager hooks and project preparation are executable trust boundaries too. Specify narrowly scoped acquisition network access and credential handling separately from network-denied analysis. Keep sealed controller/analyzer imports distinct from project code and extensions. Preserve genuine project incompatibilities and independent static results without turning missing required evidence into PASS.

## Isolation feasibility before production

Evaluate the release-signed managed broker against the harmless allow/deny fixtures in [FEASIBILITY.md](FEASIBILITY.md). The earlier minimal Seatbelt helper, App Sandbox and XPC comparisons remain historical experiments; they are not parallel implementation requirements for this revision. Preserve their parser and lifecycle failures as negative evidence, never as proof that the managed candidate passes.

Prove confinement before untrusted Python, plugins, build hooks or native-library initializers run. Account for inherited file descriptors, IPC handles, dyld injection and system-library initialization. Define a macOS-specific observation contract; do not claim Linux's static-ELF or /proc proof on macOS.

Prove allowed reads/writes separately from denied host access; deny undeclared network and IPC access. Test denied direct creation/detachment attempts and broker-managed workers across timeout/cancellation/controller failure, concurrent runs and resource bounds. Process-group cleanup alone is insufficient proof. Enforce no survivors after five seconds and 100 repetitions per lifecycle race; freeze remaining resource limits and supported OS builds from measurements; inability to enforce a required boundary blocks the backend rather than weakening it silently.

Seatbelt profiles are an undocumented third-party interface with compatibility risk. App Sandbox's entitlement/inheritance model was a historical alternative, not proof of arbitrary project-runtime support or the approved managed boundary. Document backend choice, rejected alternatives, maintenance risks and stop conditions before production approval.

## Native artifacts, policy and cache identity

Use separate signed macOS runtime artifacts and a signed manifest binding artifact digests, extracted payload/root manifest, OS, ARM64 architecture, Python ABI, complete dependency closure, released dependency-policy identity and backend/profile version. Include those bindings in cache identity. Preserve full-module signature/checksum coverage for module-shipped files.

Verify acquisition/extraction and every launch, including offline reuse. Reject missing, partial, stale, mixed, corrupted or unbound caches. Atomic publication and concurrency controls must prevent partial reuse. Prove protection against substitution between verification and execution, including symlinks and redirected library paths. Freeze the concrete enforcement mechanism only after the race fixtures pass.

Retain immutable historical Linux artifacts. Never reuse their identities for macOS. Final artifact hashes must describe the final distributed bytes after applicable signing/notarization processing; maintain upstream provenance separately when packaging modifies files.

## Dependency closure admission

The inherited Linux lock contains `nodejs-wheel-binaries`, prohibited by current core policy. BasedPyright 1.39.10 directly declares `nodejs-wheel-binaries>=20.13.1`. A Node executable swap, `--no-deps`, historical signature or ordinary trust exception cannot resolve this conflict.

Audit all direct/transitive Python and native dependencies, build inputs, licenses, interpreter origins and platform tags. Review an admissible distribution/build and any necessary BasedPyright metadata change with matching provenance and compatibility tests. Upstream Node archives are a candidate source only; none is preapproved. A policy prohibition change, if needed, requires separate explicit approval. Correctly signed prohibited dependencies fail admission before provisioning/launch, including offline reuse.

Metadata read on 2026-09-30 confirms macOS ARM64 artifacts for Semgrep 1.144.0, CrossHair 0.0.109 (including CPython 3.11–3.13), and Z3 5.1.0.0. The Z3 ARM64 wheel advertises macOS 13.0; that is one dependency's artifact tag, not a supported product OS floor or complete closure proof.

## Distribution and compatibility

Verify applicable Apple signing, notarization, quarantine, entitlements and third-party extension loading through actual customer installation. Review library-validation exceptions narrowly for the target worker; never disable host protections or broaden the trusted control domain simply to make an extension load.

Specify versioned platform evidence and paired core scope only where real compatibility tests demand it. Preserve local-versus-protected authority boundaries and released verdict semantics without claiming future C15 guarantees.

Run native macOS ARM64 customer acceptance for each advertised OS/Python combination, plus the existing Linux customer matrix. Record whether CI infrastructure is virtualized independently of the application's no-VM runtime requirement; require native ARM64 processes and a physical-Mac smoke, never emulated execution as native evidence.

## Local Docker assembly and GHCR promotion

Docker Desktop runs Linux containers on macOS. Use it only for COPY-only packaging of a payload already built and tested on native macOS; Docker execution is not Darwin acceptance. A local candidate export must retain `darwin/arm64` OCI config identity, payload digests and explicit experimental status. Do not alter historical Linux image identities. Candidate tooling must not push or grant production eligibility.

Protected GHCR promotion requires the final signed/notarized payload, complete admitted dependency closure, native acceptance and Linux regressions, and all mandatory repository gates. Bind acceptance and provenance to the exact final distributed digest. A successful Docker export or green packaging PR alone is insufficient. The production publisher must reject missing or stale proof. Signing credentials belong only in the protected release environment, never the Docker context or PR builds.

## Delivery and rollback

The earlier feasibility delivery provided the scoped contract, measured native experiments in [NATIVE_RESULTS.md](NATIVE_RESULTS.md), and bounded local candidate tooling: a COPY-only Docker fixture, strict OCI verifier and regression tests. The experiments establish partial launch/confinement/analyzer and packaging evidence; the tested descendant-lifecycle designs fail the required contract, so production backend approval remains blocked.

The current approved milestone must first prove the release-signed managed boundary. It must then resolve the outstanding lifecycle and dependency-closure gaps, complete the remaining proof obligations in [FEASIBILITY.md](FEASIBILITY.md), and freeze supported OS builds, backend, admitted dependencies, signing approach and limits from passing evidence before obtaining bounded production-design approval. Production implementation with focused failing-first tests, Linux/native acceptance and canonical signed publication follows that approval. Repeat customer installation after publication before closing #460 or archiving.

A failing mandatory feasibility case blocks production. Retain results and revise the design explicitly; do not silently downgrade the contract. Withdraw or supersede a faulty macOS publication while preserving Linux support, historical signatures and diagnostic evidence. Effort remains unestimated until feasibility establishes a workable backend.

## Sources

Accessed 2026-09-30; packaging availability is not execution or admission proof.

- [Apple helper inheritance](https://developer.apple.com/documentation/xcode/embedding-a-helper-tool-in-a-sandboxed-app)
- [Apple DTS on custom sandbox profiles](https://developer.apple.com/forums/thread/661939)
- [Chromium macOS sandbox design](https://chromium.googlesource.com/chromium/src/+/main/sandbox/mac/seatbelt_sandbox_design.md)
- [Apple library validation](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.disable-library-validation)
- [BasedPyright metadata](https://pypi.org/pypi/basedpyright/1.39.10/json)
- [Semgrep metadata](https://pypi.org/pypi/semgrep/1.144.0/json)
- [CrossHair metadata](https://pypi.org/pypi/crosshair-tool/0.0.109/json)
- [Z3 metadata](https://pypi.org/pypi/z3-solver/5.1.0.0/json)

## Historical XPC lifecycle follow-up (rejected candidate)

The no-admin follow-up used a trusted native launcher and an application-scoped
App Sandbox XPC service. A fixed bundled C fixture inherits the service sandbox;
customer commands and runtime selection are not exposed. Version-one requests
start a single fixture per connection or cancel it. XPC carries an explicitly
passed output descriptor; other inherited descriptors are closed at spawn.

An independent host observer measures process birth identity, executable path,
readiness and completion. Process-group termination is a tested candidate action,
not a claim of descendant ownership. A detached survivor rejects this design.
The experiment failed its lifecycle contract: two positive controls passed and
all sixteen detached lifecycle cases failed, as recorded in
[XPC_BOUNDARY_RESULTS.md](XPC_BOUNDARY_RESULTS.md). The five-second bound and
100 repetitions per lifecycle race remain mandatory for the managed candidate;
positive admission also requires a mechanism review and the remaining feasibility
groups. Ordinary-user installation remains mandatory. The unrestricted subprocess contract in this historical experiment is superseded by the managed-process revision above. No publication follows from fixture execution.
