# Reviewed feasibility evidence — 2026-09-30

Current project-driven evidence (2026-10-05, Europe/Berlin): pinned native pip
26.2.1 prepares unfamiliar dependencies and the actual project root without a
publisher project catalog. Separate network-denied workers execute setuptools
hooks and inspect the resulting wheel. PyPA sampleproject at
`621e4974ca25ce531773def586ba3ed8e736b3fc` executes all ten analyzers and returns
FAIL for genuine project findings; a private self-referential-extras project
executes all ten and returns PASS. Both reuse verified local caches offline.
Physical platform: ARM64 macOS 27.0.1 (26A434), capsule CPython 3.11.15.
One independent review agent's concrete preparation defects were reproduced and
fixed; its final focused review found no new defects. Full four-manager,
OS/ABI, boundary and independent-install acceptance remain incomplete. Raw
receipts stay private and production eligibility remains false. Historical
observations follow below; see TDD_EVIDENCE.md for current regressions.

Observed on physical Mac17,9, macOS 27.0.1 (26A434), ARM64. No Rosetta or Docker execution was counted as native execution. Confidence is high for these bounded observations, not for production support. Raw local execution transcripts are not included in this PR.

## Isolation

Seatbelt: ten positive-controlled cases passed, covering startup, allowed input/private output access, denied canary reads/writes, symlink escape, listening/outbound loopback sockets, child canary access and closure of a supplied descriptor. Initial startup crashes were failures; explicit root-directory and interpreter/library read permissions fixed startup. Ad-hoc signing only; broad metadata/process/signal allowances were experimental.

App Sandbox: an ad-hoc signed app bundle launched Python 3.11.15 and 3.12.13. Private writes worked; sibling canary and loopback access were denied. The bare executable failed initialization. Temporary entitlement exceptions and ambient pyenv/Homebrew libraries preclude a hermetic/distribution claim.

## Analyzers and dependencies

Ruff 0.15.12, Semgrep 1.144.0, CrossHair 0.0.109 and experimental npm BasedPyright 1.39.10 each passed clean/defective fixture expectations under Seatbelt: eight cases. Ruff/CrossHair/BasedPyright clean exits were 0 and defect exits 1. Semgrep exited 0 for both; finding counts were 0 and 1. Dependency writes/network bind were denied; private state writes worked. The dependency configuration hash did not change. OpenSSL read permissions were required for Semgrep's Python SSL import.

The inherited Z3 5.1.0.0 wheel has inconsistent filename/internal tags and fails `pip check`. A separately derived wheel, `5.1.0.0+specfact.1`, uses consistent `macosx_14_0_arm64` tags, local provenance and regenerated RECORD. Native bytes and copyright notices were preserved. Original SHA-256: `399a38a85d784105e5df5a05c04a581481bfdb80af7424779cf76fa843b4e66c`. Derived SHA-256: `038d38254f294321b8cf67f7f07e4e7b64541507e465920cbd42a6438afb0a6a`. Two fixed-tooling repacks agreed. Fresh candidate installation passed `pip check`, Z3 fixtures and CrossHair clean/defect cases; a separate fresh baseline reproduced the failure. Actual macOS 14, license review and policy admission are unproven. No derived wheel is published by this PR.

BasedPyright's Python dependency on prohibited `nodejs-wheel-binaries` remains unresolved for that delivery path. The npm/upstream-Node experiment is not policy admission. Existing artifact signatures, policies and environments were not rewritten.

## Lifecycle

Process-group timeout/cancel left a `setsid` descendant alive. A bounded supervisor passed tested timeout/cancel/controller-death cases, but supervisor death left workers alive. Enumeration is not atomic; `NOTE_TRACK` returned ENOTSUP. All 38 recorded processes from this experiment were absent after cleanup.

Denying process creation blocked `fork`, `vfork` and `posix_spawn` while threads ran. A real subprocess-dependent pytest case failed. Single-process tracing killed the root when the tracer died, including `setsid`/exec cases, but cannot substitute for arbitrary project subprocess semantics.

The final tracing experiment covered three creation methods with/without descendant `setsid`: all six descendants were untraced and survived tracer death while each traced root died. Descendants reparented to PID 1 and heartbeats advanced. All 18 fixture PIDs were absent after exact-PID cleanup. This rejects the tested tracing design; it is not a general impossibility theorem for every macOS design.

## Docker candidate

Buildx 0.37.1 / BuildKit 0.33.0 on the local Linux ARM64 Docker daemon exported a COPY-only `FROM scratch` OCI artifact with actual index/config `darwin/arm64`. Descriptor size/digest, layer diff ID, native bytes and executable file mode checks passed. The extracted proof executable retained its ad-hoc signature and printed Darwin/ARM64 when run natively.

The checked-in [candidate guide](candidate-build/README.md) was reproduced separately. Its archive passed `scripts/macos_capsule_candidate.py`; manifest/config digests matched the Docker export receipt. The initial verifier suite passed 32 cases. After the review regressions through the text-field padding correction, all 309 focused cases pass on native CPython 3.11 and 3.14, as recorded in [TDD_EVIDENCE.md](TDD_EVIDENCE.md). Successful verifier output always reports `production_eligible=false`. This verifies tiny-fixture assembly, not the complete capsule. No registry push occurred.

## Evidence handling

Local raw JSON and its source/stored SHA-256 manifest are retained in ignored `.specfact/macos-feasibility/raw-evidence/`. Local scratch retains prototype sources and transcripts. This public summary intentionally contains no raw local execution trace. A fresh production candidate still needs an executable native acceptance suite, admitted dependency closure, signing identity and customer-installation proof bound to its final digest.

The host signing-identity check found zero valid identities. No Developer ID signature, notarization, GHCR production promotion or native capsule support is established. The baseline released CLI remains `unsupported_controller_platform` with UNKNOWN evidence.

## Native XPC follow-up

The checked-in native XPC experiment ran on 2026-10-01 Europe/Berlin: two positive controls passed and all sixteen detached lifecycle cases failed, with empty final cleanup audits. See [XPC boundary results](XPC_BOUNDARY_RESULTS.md). The candidate is rejected; production remains NO-GO.

## Distribution scope readback — 2026-10-02

The owner deferred paid Apple identity/notarization to optional #488, which is
blocked by issue #460. The historical zero-identity result no longer blocks initial delivery.
Ad-hoc native signatures plus SpecFact-signed manifests remain required, along
with exact-distribution sandbox/lifecycle and separate-Mac installation proof.
No new boundary or installation pass is established by this scope correction.

## Project-driven native checkpoint — 2026-10-05, Europe/Berlin

The physical host is macOS 27.0.1 (26A434), ARM64; this is supplemental
CPython 3.11.16 candidate evidence, not the supported release matrix. No
publisher signing key, Docker, host project environment or project catalog
was used. Paid Developer ID remains optional #488. Production eligibility
and publication flags remain false.

- Controlled pip, Hatch, uv and Poetry projects completed cold preparation,
  verified offline reuse and all ten analyzers. These are authentic pinned
  managers, not pip replacements for other managers. The upstream corpus
  remains a separate mandatory gate.
- Automatic discovery on an unfamiliar uv project without uv.lock or a
  publisher catalog completed with all ten analyzers and PASS, including
  pytest-cov and an actual MarkupSafe ARM64 extension import. Artifact
  identity: sha256:f04b93cbcd496a17287ea2f24243b8ccd83651034cc3e405cf7d6cfe6180a2e0.
- Managed uv built from the reviewed upstream commit and locked Cargo input
  using the private pinned toolchain. Its verified ad-hoc hardened binary
  digest is 3b1a6d08d941bdb0934ab72804748ae5ddd2aeb35940ee93c7a8a44b67cef151.
  The prepared candidate used that exact builder output.
- An authentic Poetry custom root build executed its managed Python child
  and completed preparation/offline reuse. All analyzers ran; genuine
  fixture findings and coverage deficits produced FAIL, not incomplete
  manager evidence. This custom-build trial is not a clean PASS fixture.
- The exact upstream Requests and Flask corpus commits completed native
  preparation/offline reuse. Initial review exposed internal-link snapshot
  handling, whole-file BasedPyright diagnostic parsing and policy projection
  gaps. Their initial incomplete reviews are retained privately and cannot
  count as passing corpus acceptance.
- Native live managed-child proof passed after adding sibling imports through
  -c, -m and script launches and reordered -I options. It also exercised
  streams, waits, timeout/kill, handle reuse and direct-fork denial.

Fresh signed supported-OS/ABI acceptance, all unchanged upstream manager
corpus members, complete boundary/resource/escape proof, an independent clean
installation route, Linux x86-64 VM regression, final repository gates and
actual current-head reviews remain mandatory. Module signing and canonical
publication are CI/CD follow-ups; neither occurred locally.
