# Design: Dedicated macOS ARM64 Code Review Capsule

## Project-driven preparation and VM acceptance — 2026-10-04

ProjectPlan and existing --project-config/--project-runtime interfaces are shared
across backends. Selection is explicit configuration, verified active context,
then unambiguous metadata. JSON discovery failures expose diagnostic, candidates
and required_fields with exit 2; successful inspection remains compatible.
Unknown projects are locally prepared without publisher project registration.
Real pinned managers preserve locks, selected groups/extras and environment
semantics in disposable storage. Build hooks and project plugins do not execute
in the credential/network-bearing acquisition domain. Managed launch requests
inherit only narrower permissions; unsupported operations remain incomplete.

Publisher authentication applies to SpecFact runtime artifacts. Project layers
retain unsigned local_build provenance and content identities, verified before
atomic cache publication and warm reuse. Per-project signed acquisition catalogs
and the earlier static offline wheel adapters are superseded as normal setup.

Full VMs with a supported guest OS/kernel, architecture and ABI are equivalent
acceptance environments to physical systems. VM status is not an authorization
or artifact-selection input. The test harness records guest build, architecture,
ABI, artifact digest and configured virtualization/emulation mode. A fresh
independent matching-architecture VM can provide ordinary-user installation
acceptance. UTM x86-64 emulation on Apple Silicon is supplemental; Windows ARM64
running translated x64 programs does not establish native Windows x64 acceptance.
Docker/WSL Linux execution provides Linux evidence only. Windows and Linux ARM64
remain linked follow-up deliveries, never implied by booting their guests.

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
retains the earlier creation-to-tracing gap and optional Apple credential tool.
[STARTUP_BOUNDARY_RESULTS.md](STARTUP_BOUNDARY_RESULTS.md) now records a passing
fixed-fixture launchd/tracing startup subset on the physical host. The candidate
has not passed full admission.

## Baseline and product boundary

The ordinary `specfact code review run` and existing runtime inspect/prepare commands select the backend automatically. This delivery targets macOS ARM64; Linux x86-64 remains the regression baseline. Windows, Intel macOS and Linux ARM64 are deferred. No Docker, WSL, VM, Rosetta or CPU emulation is a customer runtime prerequisite.

Start feasibility from the released Code Review 0.50.1 / #473 implementation and verified #459 layout correction; record exact compatible core/module versions, commits, signatures and policies. Preserve released scope, findings, differential classification and status/exit behavior. C15 #417/core #679 is independently scheduled, not a prerequisite. New native producer/consumer interfaces require explicit versioning and compatibility tests; old protected consumers must reject unknown evidence instead of interpreting it as Linux identity or protected PR authority.

## Architecture boundary

Keep portable review logic shared. Introduce a bounded platform backend responsible for capabilities, native provisioning, path layout, preparation, launch, observation, cleanup and result identity. Exact interfaces are frozen after feasibility; this revision does not approve public CLI/schema changes.

The existing Linux implementation uses Bubblewrap, ELF descriptors, /proc observation, ptrace and /opt/specfact mounts. macOS cannot reuse those claims. Its project-runtime path must inventory Mach-O slices, dylib dependencies and dyld load origins, account for Apple system libraries/shared caches, and use relocatable paths under user-owned storage. Never require writes to system roots or silently source libraries from Homebrew.

Carry forward #473's manager discovery, source locks, worker separation, pytest plugins and coverage. Acquisition, build backends, package-manager hooks and project preparation are executable trust boundaries too. Specify narrowly scoped acquisition network access and credential handling separately from network-denied analysis. Keep sealed controller/analyzer imports distinct from project code and extensions. Preserve genuine project incompatibilities and independent static results without turning missing required evidence into PASS.

## Isolation feasibility before production

Evaluate the initial-distribution managed broker against the harmless allow/deny fixtures in [FEASIBILITY.md](FEASIBILITY.md). The earlier minimal Seatbelt helper, App Sandbox and XPC comparisons remain historical experiments; they are not parallel implementation requirements for this revision. Preserve their parser and lifecycle failures as negative evidence, never as proof that the managed candidate passes.

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

Verify native signatures, quarantine, hardened-runtime settings, entitlements and third-party extension loading through actual ordinary-user installation on a separate ARM64 Mac or clean independent macOS environment. The default-protection CLI/GHCR route must work without customer signing or build tools. Do not strip quarantine, disable Gatekeeper or require security overrides; a concrete incompatibility is a failed acceptance case. Apple Developer ID and notarization are deferred to #488. Review library-validation exceptions narrowly for the target worker; never disable host protections or broaden the trusted control domain simply to make an extension load.

Specify versioned platform evidence and paired core scope only where real compatibility tests demand it. Preserve local-versus-protected authority boundaries and released verdict semantics without claiming future C15 guarantees.

Run native macOS ARM64 customer acceptance for each advertised OS/Python combination, plus the existing Linux customer matrix. Record the guest or physical OS/build, architecture and required kernel capabilities. A compatible matching-architecture full VM is eligible; customers need no additional VM to run the capsule. Retain a physical-Mac smoke and record CPU emulation only as supplemental evidence.

## Local Docker assembly and GHCR promotion

Docker Desktop runs Linux containers on macOS. Use it only for COPY-only packaging of a payload already built and tested on native macOS; Docker execution is not Darwin acceptance. A local candidate export must retain `darwin/arm64` OCI config identity, payload digests and explicit experimental status. Do not alter historical Linux image identities. Candidate tooling must not push or grant production eligibility.

Protected GHCR promotion requires the exact final initial-distribution payload with valid native signatures and a SpecFact-signed manifest, complete admitted dependency closure, native acceptance and Linux regressions, and all mandatory repository gates. Bind acceptance and provenance to the exact final distributed digest. A successful Docker export or green packaging PR alone is insufficient. The production publisher must reject missing or stale proof. SpecFact manifest-signing credentials belong only in the protected release environment, never the Docker context or PR builds. Apple credentials are not required for this initial publication; their protected integration belongs to #488.

## Delivery and rollback

The earlier feasibility delivery provided the scoped contract, measured native experiments in [NATIVE_RESULTS.md](NATIVE_RESULTS.md), and bounded local candidate tooling: a COPY-only Docker fixture, strict OCI verifier and regression tests. The experiments establish partial launch/confinement/analyzer and packaging evidence; the tested descendant-lifecycle designs fail the required contract, so production backend approval remains blocked.

The current approved milestone must first prove the initial-distribution managed boundary. It must then resolve the outstanding lifecycle and dependency-closure gaps, complete the remaining proof obligations in [FEASIBILITY.md](FEASIBILITY.md), and freeze supported OS builds, backend, admitted dependencies, signing approach and limits from passing evidence before obtaining bounded production-design approval. Production implementation with focused failing-first tests, Linux/native acceptance and canonical signed publication follows that approval. Repeat customer installation after publication before closing #460 or archiving.

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

## Distinct trust evidence

Versioned runtime inspection/evidence must distinguish SpecFact manifest
authentication, per-component native signing mode, notarization status and
boundary verification. An ad-hoc signature is not authenticated Apple publisher
identity. Credential availability, signature verification and notarization never
alone confer boundary acceptance or production eligibility. Existing Apple
credential preflight is optional and cannot be called as an initial-release gate.

Apple documentation inspected 2026-10-02: [ARM64 ad-hoc signing](https://support.apple.com/guide/security/rosetta-2-on-a-mac-with-apple-silicon-secebb113be1/web)
and [trusted execution](https://developer.apple.com/forums/thread/706442).
Their guidance does not prove our cross-machine installation route.

## Owned Mach signal stop experiment (2026-10-03)

See MACH_SIGNAL_CONTRACT.md. Current-head 78b58bca hosted completion fails on
macOS 14, 15 and 26; bounded reconciliation has not demonstrated a fix. The
control fixture now evaluates pre-spawn owned exception endpoints and PT_SIGEXC
with SDK MIG decoding. BSD unit mocks retain historical transition checks only;
they are not a runtime fallback or proof of the Mach transport. Startup/analyzer
fixtures retain their separate evidence. Exact signed hosted acceptance remains
mandatory before any support claim.
