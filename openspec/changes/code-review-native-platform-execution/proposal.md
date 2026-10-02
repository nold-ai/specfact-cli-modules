# Change: Dedicated macOS ARM64 Code Review Capsule

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

## Why

Mac developers need the ordinary Code Review workflow to execute reliably on their native host. The released Linux x86-64 capsule cannot provide that support by changing platform detection: its launcher, observation, filesystem layout and project native-library inventory are Linux-specific.

## Scope revision — 2026-09-30

The owner approved macOS ARM64 as the first new platform and separate native delivery from C15. This revision replaces the broader macOS/Linux/Windows x64/ARM64 delivery scope and the blanket core #679 prerequisite. Windows, Intel macOS and Linux ARM64 are deferred. Linux x86-64 remains supported and is a regression obligation.

## What Changes

- Preserve review and runtime inspect/prepare commands; select an approved native backend automatically.
- Plan dedicated signed macOS ARM64 artifacts, cache identities and platform evidence while preserving released review semantics and historical Linux artifacts.
- Rebase on Code Review 0.50.1 and completed portable project-runtime #473, including pip/pip-tools, Hatch, uv, Poetry, project workers, native extensions, plugins and coverage.
- Separate provisioning, preparation, launch, isolation, observation and cleanup from portable review logic; include Mach-O/dyld and relocatable user-owned paths.
- Require initial-distribution managed-broker boundary proof as the first milestone, then complete isolation and dependency feasibility before bounded production-design approval. Historical Seatbelt/App Sandbox/XPC experiments remain evidence of rejected or incomplete approaches, not alternative current milestones.
- Require signed customer-installation acceptance, native positive/negative tests and Linux regressions before advertising support.
- Retain the earlier bounded local candidate tooling: COPY-only Docker assembly, strict OCI/TAR/JSON verification against an operator-owned payload, regression tests and reviewed native feasibility results. This tooling never executes or publishes an archive and always rejects production eligibility; it does not satisfy the managed-process milestone.

## Capabilities

### New Capabilities

- `review-native-platform-execution`: bounded macOS ARM64 execution, trust, lifecycle and release acceptance.

### Modified Capabilities

No released runtime capability changes in this feasibility delivery. Any future platform evidence or consumer interface must be explicitly versioned and compatibility-tested.

## Dependencies

Parent: modules #163 under #162. Verified layout correction #459 is the completed direct baseline. Completed #466 and #473 are released runtime context; initial module baseline is 0.50.1. Pin the exact compatible released core/module and signed identities during feasibility.

Core #679 and modules #417 are not blanket blockers. Preserve the selected released verdict contract; native work does not implement C15. An actual native consumer incompatibility requires a named paired change and compatibility evidence, not wholesale adoption of unrelated C15/policy/exception work. Optional #431/#432/#434, preflight, seals and historical RED ledgers do not block this delivery.

The complete native closure must satisfy dependency policy. BasedPyright 1.39.10 directly requires prohibited `nodejs-wheel-binaries>=20.13.1`; replacing a Node executable alone does not resolve that metadata/closure conflict. No replacement source or policy exception is preapproved.

## Acceptance Criteria

- Issue, dependency edges, proposal, design, scenarios, tasks, evidence mapping and change order agree on macOS ARM64 first and independent C15 delivery.
- The feasibility milestone has executable proof obligations, explicit failure/stop conditions and a production approval gate.
- CPython 3.11–3.13 is a candidate matrix; minimum macOS version and actual supported combinations are frozen only from passing native evidence.
- Planning and candidate-tool validation pass; measured native experiments are recorded separately and never imply native support or released artifacts.
- First-release acceptance requires all ten analyzers and the pip/pip-tools, Hatch, uv and Poetry corpus, including plugins, coverage and compatible ARM64 extension imports, plus isolation, integrity, lifecycle, signed distribution and Linux regressions. Unsupported process diagnostics cannot excuse a missing required corpus result.

## Impact and Non-Goals

The earlier feasibility delivery included the scope revision, native feasibility results, a local COPY-only Docker fixture, the bounded `scripts/macos_capsule_candidate.py` verifier and its regression tests. Measured lifecycle failures keep production architecture approval blocked. Production runtime code, signed payloads, module versions, registry entries and support claims remain unchanged. Keep #460 open through feasibility; the recorded Todo status is historical metadata, not a fresh issue-status check. Production implementation, publication and OpenSpec archival remain future gated tasks. No unsandboxed, Homebrew, Rosetta or development-host fallback establishes capsule support.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#460](https://github.com/nold-ai/specfact-cli-modules/issues/460)
- **Last Synced Status**: open / Todo; signing scope split, 2026-10-02 Europe/Berlin
- **Sanitized**: true

## Native implementation checkpoint — 2026-10-03 (Europe/Berlin)

Actual physical-host work now includes fixed-bootstrap launchd/tracing ownership,
a private bounded broker control protocol and both sealed Semgrep rule-pack
analyzers. Startup proof passes 100 repetitions of six stages; control proof
retains historical results and review corrections separately. Native clean and
defective Semgrep fixtures execute with denied host/descriptor/process/network
controls and exact dependency grants. MANAGED_BOUNDARY_STATUS.md links measured
contracts and current limits. The public native command, all-ten-analyzer managed
integration, four-manager corpus, immutable runtime delivery and independent-Mac
installation still require implementation/admission; this checkpoint does not
claim those capabilities or justify a module release bump.
