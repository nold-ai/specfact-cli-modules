# Native macOS ARM64 experiments — 2026-09-30

## Preparation review checkpoint — 2026-10-05 (Europe/Berlin)

The Git/assembly integration passes 93 focused tests and now includes the
reproduced Git image, licenses and corresponding source, with an exact compiled
broker requirement. Private candidate identity:
`sha256:6a2861d097bd4a3df15d710574f698d063ddee3cf5be0f1cc09ccf2e871e1385`.
The initial Hatch checkout was a partial clone missing historical blobs; its
network-disabled VCS export correctly failed. A complete disposable checkout
of the same mandatory commit leaves the original fixture untouched. That native
attempt builds the root and workspace wheels and reaches authentic Hatch/uv
installation, where the private-copy wheelhouse path conflicts with the
admitted immutable input path. The handoff correction and its actual rerun
remain pending. No Hatch corpus pass is claimed.

Independent defect review found and reproduced five preparation bugs involving
workspace resolution/imports, executable modes, sanitized pip VCS context and
signature-check timeout reporting. Closure review identified four further gaps
in explicit member paths, uv modes, ancestor VCS context and pip hash mode. After
correction, the integrated preparation, discovery and analyzer suite passes
**312 tests**, and independent preparation closure review reports no findings. A namespace backend
without a verifiable file origin is rejected with a structured diagnostic.

The Requests, Flask and Poetry corpus repositories prepare and reuse their
environments offline. Nine analyzers execute against their canonical corpus
paths; their actual findings are retained. Required pytest evidence remains
incomplete while approval for the local project-origin policy projection is
pending. This is not a complete corpus pass or a release acceptance result.

## Project-driven corpus checkpoint — 2026-10-05 (Europe/Berlin)

The unchanged Poetry corpus at `be56ff07db06e9b82574648433ca228e4cac549b`
prepares with pinned Poetry 2.4.3, exact locked Git source acquisition, a confined
source build and verified offline reuse on native CPython 3.11.16. With its
declared corpus source/test paths, nine analyzers run; pytest remains incomplete
because its coverage exclusions require the pending owner-approved local
`project-origin-v1` policy change. Actual findings produce FAIL independently of
that missing evidence. Candidate artifact identity:
`sha256:b87b5a8ec8932beb5d6aebd7a200b816fa0952898942eae88c54334a9597e0c2`.

The unchanged Hatch corpus exposes matrix selection and local workspace
requirements that the adapter previously rejected. These have focused RED/GREEN
coverage (128 combined VCS, manager and controller tests pass). Packaged confined
Git and the actual offline uv child still require physical validation before
claiming that corpus passes. Neither this checkpoint nor controlled-project
passes establish the supported release matrix, authenticated independent
installation, complete boundary acceptance or production eligibility.

## Current project-driven preparation checkpoint — 2026-10-04 (Europe/Berlin)

The earlier lifecycle failures and guarded pytest checkpoints below are
historical evidence, not the current project-origin contract. The current pip
candidate runs all ten real analyzers on an unrelated dependency-bearing
repository through the native broker. Cold preparation and verified offline
reuse succeed without a project publisher catalog. Missing Developer ID is
not a blocker. Authentic Hatch/uv/Poetry managed launch, the full boundary and
supported OS/ABI matrix, independent installation and authenticated GHCR
release acceptance remain unfinished. Production eligibility stays false.

Target: PyPA sampleproject commit `621e4974ca25ce531773def586ba3ed8e736b3fc`.
Physical host: macOS 27.0.1, build 26A434, ARM64; capsule CPython 3.11.15.
Pinned pip 26.2.1 acquired backend and project wheels. Setuptools hooks ran in
separate network-denied disposable workers; a fresh sealed worker inspected
wheel metadata. The root distribution and dependencies were installed offline.
Source roots matched the built wheel's Python files to immutable snapshot
bytes. Pytest reported actual coverage failures instead of missing coverage;
the review verdict was FAIL for project findings, with all ten members `ran`.
The target checkout remained clean. A second unfamiliar requirements-only
project also passed native cold preparation and offline reuse.

These private maintainer candidates use ad-hoc native signing and do not have
publisher-authenticated release admission. They prove execution, not the
customer download route. No module or publisher signing keys were used; raw
logs and receipts remain private. See TDD_EVIDENCE.md for regressions and review.

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

The [local candidate build guide](candidate-build/README.md) reproduces native hello compilation, ad-hoc signing and Docker assembly without publishing. The initial verifier suite contained 32 focused rejection/positive cases; after review regressions through the text-field padding correction, all 309 cases pass on native CPython 3.11 and 3.14 (see [TDD_EVIDENCE.md](TDD_EVIDENCE.md)). The [actual local output](EVIDENCE_SUMMARY.md#docker-candidate) always marks production eligibility false. It is a bounded tiny-fixture inspector, not a complete capsule builder or GHCR publisher.

## Remaining gates and failure controls

- Detached descendants can outlive process-group termination. Require independently verified containment and cleanup; do not substitute process polling or cooperative PID reporting for a race-resistant security contract.
- Ambient interpreter/library linkage prevents hermetic distribution. Build and admit a relocatable native closure, then repeat the loading and tamper tests with host package-manager paths unavailable.
- The signed customer route is unproven. Use an approved signing identity and delivery design, then test a fresh ordinary-user installation without bypassing OS protections.

Full analyzer integration, project preparation/build hooks, pytest plugins and coverage, all project-manager corpora, cache integrity/concurrency, verification-to-launch races, resource bounds, complete lifecycle cleanup, consumer evidence and Linux regression suites remain required. None is marked passing by these smoke tests.

### Managed project-corpus acceptance candidate

On 3 October 2026, a new maintainer harness bound the pinned portable-runtime
pip, Hatch, uv and Poetry corpus entries to immutable managed-process plans.
Preparation and execution have separate domains; commands come only from the
trusted plan, and unknown executables, argv, environment, paths and child-process
semantics fail as incomplete evidence with no host fallback.

The prepared-project observer passed on native ARM64 macOS 27.0.1 build 26A434
using the sealed CPython 3.13 analyzer candidate. Two broker-owned workers proved
separate preparation and execution, one real pytest call, explicit project-plugin
loading, coverage of the declared source and import of the sealed generic ARM64
`_cffi_backend` extension. All 20 focused cases passed, including the physical
case. This proves the bounded observer path, not real package-manager preparation.

The candidate payload has no admitted pip/Hatch/uv/Poetry preparation adapter
images. Consequently no manager build hook or pinned upstream dependency closure
was executed by this slice. The four-manager release gate remains incomplete and
production eligibility remains false until those fixed adapters and real corpus
runs pass the complete supported matrix.

This is a substantial backend/packaging effort; these observations do not justify a delivery estimate. Rollback is to retain the released Linux backend and withdraw any experimental macOS publication. No production assets, module signatures or runtime selection were changed by these experiments.

## Evidence handling

Raw JSON commands, outputs, source/stored digests and local paths are retained under the ignored `.specfact/macos-feasibility/raw-evidence/` directory and the original local experiment directories. They are not part of the PR. The [reviewed evidence summary](EVIDENCE_SUMMARY.md) records the relevant observations and limits. The candidate build guide and focused tests provide reproducible packaging checks; historical native experiment summaries are observations, not a checked-in production acceptance suite.

Evidence validation: strict OpenSpec validation, structural Markdown checks (existing MD013/MD060 exclusions), Git whitespace checks, JSON parsing and stored SHA-256 digest checks passed. Production quality/acceptance gates were not run or claimed passing; the native baseline remains UNKNOWN. These changes record bounded feasibility and candidate tooling; they do not approve a production backend.

Next: resolve the lifecycle and dependency admission failures, complete the remaining proof groups, and approve the bounded production design. Keep #460 open and do not archive the change.

## Native XPC follow-up

The checked-in native XPC experiment ran on 2026-10-01 Europe/Berlin: two positive controls passed and all sixteen detached lifecycle cases failed, with empty final cleanup audits. See [XPC boundary results](XPC_BOUNDARY_RESULTS.md). The candidate is rejected; production remains NO-GO.

## Fixed manager adapter matrix — 2026-10-03

The maintainer harness now contains executable broker-only preparation adapters
for fixed offline pip, Hatch, uv and Poetry plans, plus deterministic sealed
output inventory and domain-bound execution handoff. Unit acceptance covers
successful fixed pip dispatch, external toolchain refusal, byte tampering and
cross-domain descriptor reuse. The repository-owned Hatch reconstruction passed
native broker admission; no manager command fell back to a host executable.

Current CPython 3.13 result: pip 0/1, Hatch 0/1, uv 0/1 and Poetry 0/1 complete.
The exact blockers are missing pinned upstream source/lock inputs and missing
sealed manager artifacts. The locally available Hatch reconstruction additionally
lacks `hatch.lock`, `specfact-hatch-adapter`, `pyodbc` and `pytest-asyncio`.
Therefore the manager matrix is 0 passed, 4 incomplete, production false. The
adapter and handoff implementation is present, while real upstream preparation
remains blocked on authenticated artifacts rather than being simulated.

## Trusted acquisition/offline preparation result — 2026-10-03

The maintainer harness now creates a signed-content descriptor for a pinned
source archive, verified Git commit/tree evidence, extracted source inventory,
generated manager lock and exact dependency wheel/sdist closure. It installs the
complete bundle atomically and permits offline reuse only after signature,
content, path, hash, tag, mode and completion-marker verification. Acquisition
does not execute project code or build hooks. Preparation has no network or
credentials and uses only the fixed manager adapter and authenticated bundle;
execution receives only sealed prepared output.

Local reconstructed acceptance completed all fixed adapter rows: pip 1/1, Hatch
1/1, uv 1/1 and Poetry 1/1. Compatible generic ARM64/Universal2 and ABI3 wheels
are admitted; sdists are explicitly marked for preparation-domain build hooks.
External SDK/compiler failures remain actionable incomplete evidence and partial
prepared output is removed. The focused result is 50 passed, two skipped; the
broader native macOS unit regression passed 863 tests and 69 subtests with 56
explicitly gated cases skipped. Ruff and BasedPyright reported zero findings,
and strict OpenSpec validation passed.

This does not change the physical upstream matrix: pip 0/1, Hatch 0/1, uv 0/1
and Poetry 0/1. Completing those rows requires release-authenticated source-fetch
evidence, resolved wheelhouses and the four sealed adapter binaries inside the
candidate artifact, followed by broker-owned preparation across the supported
macOS/ABI matrix. No network fetch, production signing, runner integration,
publication or production approval is claimed by this slice.

## Complete local candidate and bounded project matrix — 2026-10-03

On the physical ARM64 macOS 27.0.1 (26A434) host, the complete candidate
assembler produced separate CPython 3.11, 3.12 and 3.13 archives. Each archive
contains all ten analyzer dependencies and 34 inspected native images. The
candidate summaries record 10,629/10,629/10,630 files respectively, ad-hoc
native signing and `production_eligible=false`. Clean and defective analyzer
fixtures passed 20/20 per ABI; the pinned Semgrep reference cases passed 14/14
per ABI. The archive manifests are signed with a private **test** key and are
not publication identities.

An additional private acceptance variant embedded the matching public key for
the fixture acquisition signer and rebuilt each candidate archive and manifest.
This did not alter the module's checked-in acquisition trust key or locally sign
the module. The mismatch against the checked-in key had correctly failed closed
as `project_native_acquisition_authentication_failed` before this variant was
built. The four tiny Git project fixtures (pip, Hatch, uv and Poetry) then each
prepared an authenticated offline project runtime and ran the public full-scope
Code Review command under CPython 3.11, 3.12 and 3.13. All 12 reviews exited 0,
reported PASS with no findings or unknown required evidence, and recorded all
ten analyzers as executed with PASS evidence. Private reports and the 12-row
allowlisted summary are retained in the local acceptance directory.

This establishes executable local compatibility for the bounded fixtures on one
physical OS build. These are not the pinned external project corpus, a clean
customer installation, the published GHCR route, or a multi-OS signed boundary
admission. The current module catalog has no published native entries. The
production acquisition signing identity still needs to be provisioned in the
protected release workflow; the fixture key cannot be used as that identity.
Module signatures remain a CI/CD PR follow-up, not a local signing step.

The final source snapshot was rebuilt after the broker startup and dispatch
corrections. The three ad-hoc-signed candidate archives again contain
10,629/10,629/10,630 files and 34 native images each. Their archive SHA-256
digests are `41da81b124ca15edab5c946f7ff64f505fea7fe0bff4cc49c60e09e1258a45f5`
(CPython 3.11), `555f196f545393c51d6e7f158ec6ffcef96bcaea60c0a59e24616142baa17998`
(3.12), and `73e1cc8a4396fd5750ba1f67f738c67acdd239b95cdfde571eded9206dda1ca7`
(3.13). Every manifest records `production_eligible=false`. A private
test-trust variant of these final archives completed the same 12/12
manager-by-ABI public full-review matrix, with ten analyzer PASS records,
zero findings and no unknown required evidence in every row. A further
CPython 3.12 pip run selecting only `app.py` passed all ten analyzers while
importing its unchanged sibling `support.py` from the staged source context.
The allowlisted results are in the private
`/private/tmp/specfact-project-acceptance17/project-matrix-final-summary.json`
and `pip-selected-cp312-final.json` files. These remain local fixture results;
the independently acquired customer route, pinned external project corpus and
other macOS versions have not passed complete acceptance.

## Current controller acceptance limit — 2026-10-04

**Later 2026-10-04 contract revision:** the owner accepted project-origin
pytest results for local native reviews after the separate-receiver probe
showed that arbitrary project code can impersonate its result channel. The
prelaunch refusal described below is historical. Current source launches the
managed pytest worker and labels executed results `project-origin-v1` in
analyzer and scope evidence. It keeps protected range reviews UNKNOWN until
their consumer contract explicitly admits that provenance. The historical
pre-guard PASS matrix below is not fresh proof for this revision. The packaged
native runtime and project-acquisition catalogs remain empty; no customer
artifact is admitted or published.

The 12/12 tiny project reviews above and the selected-file CPython 3.12 case
were measured **before** the native pytest receipt guard. They are historical
candidate observations, not passing acceptance of the current controller. The
physical forged-receipt regression showed that project code could rewrite
worker-owned pytest evidence and make a failed test appear clean. The controller
now returns `native_pytest_receipt_boundary_unverified` before launching that
worker. Accordingly the current source cannot claim full ten-analyzer PASS, even
when a pre-guard test-trust capsule did so. A process-separated, non-impersonable
pytest outcome channel and fresh complete acceptance are required. All native
capsule manifests in this work remain `production_eligible=false`; no production
GHCR catalog entry exists.

This change does not use or require a local **module-signing** key. The Code
Review module signature is reserved for the protected CI/CD PR follow-up.
Ad-hoc code signatures on native Mach-O test components and private test-only
capsule manifest signatures are distinct from the module signature.

The final physical full-scope CPython 3.12 run on this host, using the current
controller and a private test-trust candidate capsule, retained a real Ruff F401
finding and marked `targeted-pytest-coverage` `error/UNKNOWN` with diagnostic
`native_pytest_receipt_boundary_unverified`; required unknown evidence is true.
An earlier run with the narrower tool-only guard falsely reported this analyzer
`ran/PASS`, which prompted the analyzer-level refusal. The current observation
is a safe incomplete result, not the requested complete native acceptance.

## Final local verification status — 2026-10-04

On the physical ARM64 host, the ad-hoc-signed broker WAIT controller-loss,
spawn-flag fault-injection and independent file-budget regressions passed
serially (`3 passed`). The default Codex tool sandbox denied `PT_TRACE_ME`
with `EPERM`; a disposable diagnostic build identified this as the reason for
broker detail 105. Native proofs were rerun with the tool sandbox disabled.
No worker policy or macOS protection was relaxed.

The repository smart and full suites each passed `4433 passed, 69 skipped`
when run outside that tool sandbox. Format, type-check, lint, YAML, bundle
import, module checksum/version/public-key verification, 28 contract tests and
strict OpenSpec validation passed. The Code Review module manifest is
checksum-only for the protected CI/CD signing follow-up, as required by the
module release policy. A local `specfact code review run --enforcement changed
--bug-hunt` and the normal staged pre-commit Block 2 review gate both returned
`assurance_status=UNKNOWN`, `ci_exit_code=1`, zero findings. The manual run
reported `unsupported_controller_platform`; the staged-hook report gives the
more specific `native_capsule_python_abi_unsupported:darwin-arm64-cp314` for
all ten analyzers in this checkout's Python 3.14 environment. Its legacy
`linux-x86_64-cp314` environment label does not indicate actual Linux
execution. At that checkpoint, even a supported Python 3.12 controller lacked
an admitted catalog entry and the then-required protected pytest evidence channel. This is a
blocking review-gate result, not a clean review.
No commit, PR update, publication or production claim follows from the local
test passes while that gate and native acceptance remain incomplete.

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
