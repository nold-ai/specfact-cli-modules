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


## Owner-approved release continuation — 6 October 2026

The owner explicitly requested implementation of the three remaining delivery
issues: protected release/catalog, exact loader acceptance, and independent
ordinary installation. Paid Apple membership, Developer ID and notarization
remain optional #488. A normal first-run trust warning is acceptable for this
initial release; record its actual presence and acknowledgement. Do not strip
quarantine or disable system protections. Integrity, native signing, confinement,
dependency separation, resource limits and cleanup requirements remain mandatory.

Reuse the existing deterministic assembler, native cache, GHCR blob reader and
managed broker. Freeze the initial library profile to disable-library-validation
only on CPython and Semgrep Core; all other native images retain empty
entitlements. Secret-free build/acceptance precedes protected data-only manifest
signing. Signing/publishing code executes only from a protected reviewed ref;
candidate payloads are data and are never executed with the publisher key.

The first complete slice is cp312 final-byte release validation and signed
catalog acquisition, followed by three ABIs and all supported macOS cells.
Independent installation uses the signed module's packaged catalog and standard
client, with cold anonymous acquisition and offline reuse. Test fixture keys and
local artifact overrides establish unit evidence only. Human merge/promotion
remains required; a prepared workflow or green fixture does not mean publication.
No new core interface is planned. Maintainer builds may use existing SDK/Rust
tools; customers need no build tools, container engine, admin or Apple account.


## Approved test contexts — 2026-10-07

The maintainer explicitly approved separating ordinary-host/macOS proofs from confined Linux tests while retaining every assertion, and approved sending the bounded autofix diff to CodeRabbit. The completed approved review of 2aea48da..082e8b6d returns no findings. This resolves the earlier pending decisions; no publication or merge is authorized.

Use existing pytest filename discovery and explicit job invocations, rather than adding controller policy, granting host tools to confinement, or modifying authenticated installed 0.51.0. Keep the baseline proof files unchanged so an index review does not import unavailable proof contexts on its base side. Revised proof modules use proof_ filenames below tests/host or tests/native; portable additions use ordinary test_ modules. Required full/SMART host runs explicitly include host proofs. Required macOS jobs execute native parser proofs and retain the original broker/lifecycle repetitions and five-second cleanup bounds. All revised assertions remain verbatim or receive only module-reference relocation. Original baseline tests remain available.

This changes the repository's test context mapping, not analyzer budgets, artifact admission, skip verdicts, credential/network boundaries or customer behavior. Every scope's required execution remains blocking; unsupported proof-only capsule selection still fails visibly. The installed reviewer is unchanged. Preserve existing commands through their normal full-host wrappers and prove supported selection against the installed controller before claiming hosted acceptance.

The four baseline proof modules remain byte-identical to `origin/dev` so the
immutable index reviewer does not select their unavailable baseline contexts.
The full and SMART host entrypoints ignore those obsolete versions and explicitly
execute the current host module. Every current portable function moves into normal
`test_*.py` discovery; every current native function remains in an explicit
`proof_*.py` module. Required native jobs run the parser proofs on all three OS
labels and the minimal CPython proof with all three existing hash-pinned inputs.
The minimal CPython proof reuses the existing secret-free preparer; its additional
CI cost is three input preparations, without adding a new acquisition mechanism.

### Owner decision: temporary validator bootstrap authority (11 October 2026)

The owner explicitly authorized the immutable checker from c65a41e61a6b4e61e8dd2b69526a1cfc8650b3ad, blob cc549b5bbd945b64d055afe111bcaeeb059d585a, as temporary bootstrap authority until dev integration. This authority comes from that decision, not runtime signing provenance. Prefer the actual integrated origin/dev tip checker; use the exact approved commit/blob only while it has not reached dev and the integrated checker is absent. Ignore Git replacement objects for authority resolution and extract to a private temporary file. Missing objects, incomplete shallow bootstrap history, integrated checker removal after integration (including squash integration, detected through dev path history), and checker failures reject deferral. Candidate scheduling still uses the unchanged complete index and merge-base arguments.

### Deferral executor correction (11 October 2026)

An independently reproduced candidate `python` Hatch alias can return zero without running the pinned checker. Use the existing owner-installed repository `.venv/bin/python` directly with isolated Python startup, rather than resolving it through candidate Hatch scripts or environment configuration. This reuses the integrated default environment path and dependencies without creating another environment or granting a new checker authority. Missing interpreter fails closed. The existing developer-owned local tooling environment remains trusted; this correction does not claim containment against replacement of installed host executables or site packages. Real Hatch alias probes must reject a missing caller and retain valid scheduling without executing the alias.


### Host mutation-proof nesting correction (11 October 2026)

The actual finite candidate identifies three long if/elif mutation selectors in host deferral proofs. Reuse Python's existing flat match dispatch to retain each mutually exclusive string case, guarded table membership and fallback body directly. A helper table would obscure fixture setup and add callbacks; splitting tests would disturb their parameter identities. This proof-only change retains all admission/assertion behavior and introduces no analyzer or trust-policy changes. Reconstruct each original if chain from match cases and compare the whole original module AST, in addition to the unchanged production policy and all required execution contexts.


### Added host policy import collision (11 October 2026)

The top-level KISS producer import added for host nesting controls collides with the existing acquisition test's required deferred import. Remove only the added private import and reuse the already imported public Radon runner in the added caller. Require completed analyzer evidence before inspecting KISS findings. Moving or deleting the old deferred import would change an original test body; changing analyzer policy would hide a genuine finding. The public runner already composes the same KISS producer with actual Radon execution; no wrapper, new import or analyzer policy is required. A private alias still triggers Pylint duplicate-import identity detection and is rejected before final gates. This is within the authorized proof-quality correction and does not attribute unavailable hosted Semgrep syntax diagnostics to this source.


### Current dev contract for local deferral (11 October 2026)

A branch behind dev can otherwise validate stale indexed workflows against its merge base even though checker authority comes from the current dev tip. Retain the merge base only for the complete candidate delta. Reuse the same resolved integrated dev commit inside the trusted checker executor as its workflow comparison baseline, including when the approved bootstrap supplies checker bytes. This is a minimal argument correction; rejecting every behind-dev branch would unnecessarily reject a candidate index that already matches the current contract. Do not change checker bytes or authority, owner-approved budget adaptations, workflows, runtime, candidate path inventory, or any enforcement policy. Owned divergent-history regressions cover detector execution, reusable caller, reusable review, quality consumer and root environment, with matching-current-index positive controls.


### Flat distribution ownership mutation dispatch (11 October 2026)

The actual current-head public KISS nesting location maps to the retained distribution-ownership mutation helper. Its chained branches accumulate nesting under unchanged production policy. Use two flat guarded match dispatches in place of the two existing if/elif chains, retaining every condition, branch body, order and no-match behavior. Reverse reconstruction must recover the whole original inventory module AST, including every original test assertion, argument and decorator. This preserves valid/same-owner/outside-script/missing/unrecorded/ambiguous/digest-changed/malformed ownership proofs and source precedence; it changes no runtime, workflow, checker authority, threshold, deadline, coverage or admission policy. Add a real public Radon runner regression without changing any previous runner test or import binding.


### Flat pytest incomplete-evidence fixture dispatch (11 October 2026)

The finite c72 candidate flags nested control flow in the retained real pytest failure evaluator proof. Flatten only its nested execute callback's artifact-mutation chain using guarded match cases, preserving each exact condition, branch body, order and final fallback. A table or extra helper would obscure owned artifact mutation or change private bindings. The whole original module AST must reconstruct exactly after reversing that match; all seven original failure cases, test identities/decorators/arguments, assertions, real evaluator and incomplete remedies remain. Add a real public Radon policy regression with completion rejection. No runtime, analyzer threshold, authority, signature, deadline, coverage or malformed-artifact admission change.


## Bounded canonical allocation proof construction

The finite exact-head ed1 candidate identifies the retained compiled canonical-sink proof as a function-length warning. Extract only its existing sink-specific admission source and C-source assembly into two private helpers in the same proof module. This keeps compiler invocation and every actual control in the original parametrized test, while bounding each helper under the unchanged KISS policy. Splitting test cases would disturb their identities; changing policy or C literals would weaken evidence. Reconstruct the whole original module AST by inlining the two helper calls and compare every original definition, assertion, argument and decorator. Generated C literals, native-source extraction, allocator/free controls, compiler flags, deadlines and all ten compiled cases remain exact in Full/SMART/Linux/all three macOS host contexts. No runtime, workflow, trust, signing or acceptance expansion.


## Bounded project-runtime proof callbacks (11 October 2026)

The exact-head hosted review identifies three retained project-runtime proof functions above the unchanged 80-line warning threshold. Reuse their existing private phase callbacks through two small factories and the existing session launch body through one direct helper in the same test module. Pass the exact existing closure inputs, return the same phase callbacks and retain the original session class/name/method signature, keeping each body verbatim. This shortens setup without splitting parametrized tests, hiding assertions in new dispatch tables or changing production code. Inlining each factory binding and launch-helper call must reconstruct the whole original test module AST; every original test identity, argument, decorator, assertion, request, result, order and incomplete/admission constraint remains. A real public Radon regression must first fail on the three unchanged definitions and then complete without scoped length findings; factories must also stay within the same policy. Existing parameter-count warnings remain separate unwaived findings. No runtime, signing, hook/checker authority, workflow, budget, threshold, coverage, admission or lifecycle change. This independent proof-quality correction does not implement the proposed external commit entry; that owner decision remains pending, and commit/push finalization waits for an authorized enforcement route.


## Owner-approved worktree commit entry (11 October 2026)

The human approved an external commit entry scoped only to the release-506-autofix worktree. A private installation freezes the entry, exact worktree/gitdir/branch and existing normal pre-commit implementation. Invocation uses only `git -c core.hooksPath=<private directory> commit`; shared hooks and persistent config remain unchanged. The external entry independently resolves the SAME current-dev checker or explicitly approved c65/blob bootstrap, with complete-history/expiry/object/replacement guards, and runs it against the full actual index before and after the unchanged normal hook. Candidate dispatcher/config cannot remove those two invocations. Missing interpreter, binding mismatch, scheduling failure, normal-hook failure or final-index failure rejects the commit. This protects this explicit owner workflow, not arbitrary commit paths or malicious installed tools; DEFERRED is never hosted PASS. Rollback stops selecting the private hook directory.

New owner-entry fixtures use bounded setup/verification helpers; factoring retains every original control assertion and all pre-existing host definitions. Real public Radon policy is checked before final suites; no threshold or analyzer scope changes.


## Preserved Semgrep parser compatibility — 11 October 2026

Independent Python3.12.13/Semgrep1.144.0 scans reproduce three actual Syntax errors in complete retained proof inputs. The first command dispatched newer pysemgrep through PATH and the next exact-version command hit a transitive Pydantic/MCP mismatch; neither is product failure evidence. Explicit private PATH, public CA and recorded capsule transitive versions establish actual1.144.0 before RED scans. The public CI aggregates errors at a selected-file fallback, so local original source locations are independent diagnosis, not original private CI evidence. Replace match phases with direct bounded helpers using the same ordered predicates, bodies and fallback; preserve whole original module AST under reversal and all assertions. Do not upgrade tools, change thresholds, ignore errors or infer full CI PASS.

The existing worktree-only owner authorization includes correction of the interpreter-binding bypass independently reported on e18d4eec. Resolve the existing worktree Python to its owner-installed executable outside the checkout and bind SHA256 bytes; use this resolved path in the generated shell entry and every checker invocation. This minimal adaptation reuses the installed interpreter and checker rather than introducing another runtime, shared hook/config or containment claim. Replacing the worktree path is rejected by pre/post binding comparison; protected/system installation integrity remains an existing tooling trust assumption.

### Unambiguous staged pathname serialization

Within the already approved worktree-only entry, consume Git NUL-delimited pathname bytes before calling the unchanged approved checker. The checker currently accepts line-delimited arguments: reject filenames containing any splitlines boundary rather than changing its byte authority or allowing a lossy conversion. Preserve literal quote, backslash, tab and spaces in representable names. Apply the same adapter to the local dispatcher; the independent external entry remains mandatory. This is a bounded input correction, with no shared hook/config, signed runtime or checker change. Real Git commits and local dispatcher controls precede implementation.

### Immutable integrated-dev binding across normal hooks

Within the existing approved external entry, freeze the independently verified integrated-dev commit in owner-installed binding metadata alongside caller/interpreter/hook identity. Every validation rejects any live ref mismatch before selecting checker bytes, and both use that same immutable bound SHA as authority/baseline. This also rejects ref substitution before invocation. A mutable per-call ref is insufficient; invocation-only capture would miss prior ref replacement. Refresh binding only in the authorized owner workflow after verifying actual remote dev, not from candidate-controlled hooks. Legitimate dev advancement requires that verified refresh; no shared hook/config or new checker authority.

### Candidate/independent failure diagnosis: reuse the CrossHair dispatch boundary

The owner explicitly requested diagnosis and fixes of candidate/independent failures on509, preserving every gate and the worktree-only commit route. Pinned0.0.109 reproduction through the existing target dispatch matches the five public locations and reveals normal pre-commit CLI stdout contaminating the diagnostic stream. Reuse that existing signed target_crosshair dispatch: scope redirects only around CrossHair's check execution while retaining its separately supplied reporter streams, exact return code and exceptions. A bounded discard sink prevents target text from becoming evidence; actual structured reporter messages are never filtered. This minimal adaptation uses existing invocation/context machinery rather than a new launcher, candidate plugin, contract waiver or stdout allowlist. Existing constructor/contract-registry/Literal models and all CLI argv remain exact. Local diagnostic reproduction is not sealed-hosted acceptance; actual new-head Linux completion remains mandatory. Expected exception/API-model and pytest/coverage/quality findings remain separate until independently proved and fixed. Signed source checksum refresh and normal CI signing remain required; no local keys or publication.

### Pinned symbolic truth diagnosis

Actual0.0.109 source SymbolicArrayBasedUniformTuple.__bool__ returns its SymbolicBool length comparison directly, violating Python's Boolean return protocol. Independent pinned dispatch reports this TypeError at both native replay and pre-commit argv truth checks. Correct only the verified symbolic model in the existing invocation context by realizing that same length comparison through Boolean conversion; retain solver forks and original application guard bodies. Add actual SMT empty/nonempty controls and real CLI valid/violated contracts; no timeout, argv, registry, branch or exception waiver. A product rewrite from truth checks to length checks would alter custom-sequence behavior and merely work around the analyzer model, so retain application semantics.

### Replay contract diagnosis

After correcting the pinned symbolic Boolean protocol, actual contract analysis reaches ReplayContractViolation on empty argv and the original WorkerContractError for extra replies. These are intentional closed-plan rejections, not permitted successful execution. Declare their exact existing Sphinx raises contracts alongside RequestPending and checked subprocess failure. Preserve every executable statement and existing result postcondition; do not catch BaseException, broaden to Exception, remove guards or suppress analyzer findings. Runtime checksum and normal CI signing remain required.

### Workflow loader API diagnosis

Pinned analysis invents a string as the untyped construct_mapping node and reports an AttributeError. A private diagnostic copy with PyYAML MappingNode/Boolean annotations then reaches the original malformed-node ValueError. Match the actual PyYAML API and declare only existing malformed-entry/duplicate-key ValueError, unhashable-key TypeError and unsupported-tag ConstructorError. Preserve the whole executable method and every scheduling guard. This is candidate contract metadata; the external entry still executes the independently approved immutable checker blob, not this candidate file.

### Owner-entry production coverage and public contracts

The candidate's sole generic public pytest testing/error anchor is owner_commit_entry.py; the public whitelist omits TEST_COVERAGE_LOW, so it cannot reveal the measured percentage. Actual portable selection has no matching test_owner_commit_entry.py and portable context tests never import this module; its substantial body is tested only by explicit Git/host proofs. Add portable tests of the actual Python guards and installation/cleanup using filesystem fixtures and exact controlled process responses. This supplements, never replaces, real host enforcement proofs or installed acceptance. No shell/compiler is added to the target. Require the existing native per-source80% policy on measured entry statements/branches. Four public APIs also have actual MISSING_ICONTRACT findings: add their existing None/integer return postconditions and exact expected error declarations, retaining executable bodies and authority decisions. An independently reviewed private installation refresh is required before using the revised entry; no persistent/shared hook/config change. This diagnosis remains independent until exact-head hosted evidence confirms it.

### Linux owner CLI analysis completion

Offline pinned CPython3.12.13/CrossHair0.0.109 whole-file analysis exits2 with no diagnostic because analysis of newly contracted owner main reaches argparse's original SystemExit before returning. Add its exact SystemExit declaration and real invalid/help controls. No parser option, status, caught exception class, invocation route or enforcement body changes. This expected parser outcome must not be generalized to Exception or BaseException; genuine unexpected analyzer failures still fail closed.

### Owner rejection contract completeness

Public return postconditions require corresponding precise rejection contracts: installation fails on invalid/private filesystem or unavailable Git data; validation/enforcement reject invalid JSON/fields/bindings or checker failures. Declare only the same concrete filesystem/validation/subprocess/key classes already recognized by owner main. Real rejected input controls and pinned metadata tests precede declarations. Original executable functions and main's exact exception handler remain unchanged; do not admit unexpected assertion/attribute/programming errors.

### Post-sign read-only audit: output closed-state semantics

The source/signature checkpoint1c1c4628/9a8d01cf passes all local and strict public-key gates, but final read-only review finds that overriding TextIOBase.write without checking closed accepts writes after target close. Reproduce using actual CLI stdout/stderr functions before adding the standard closed guard. This minimal existing-sink adaptation restores ordinary text-stream rejection without closing the original reporter or changing any review policy. Earlier audit/gates retain their bounded checkpoint scope; new final validation, checksum refresh and normal signing are required after this correction.

### Standard text-write error diagnosis

The same sink review identifies another precise protocol mismatch: calling encode on a non-text input raises AttributeError instead of standard TypeError, fabricating a counterexample for a valid caller that catches TypeError. Real ordinary-Python controls and pinned CLI cases precede a str guard after the standard closed-state guard. Preserve text subclasses, character-count returns, UTF-8 accounting and real error/counterexample reporting. This is a minimal existing-sink correction, not a policy exception, new launcher or broad exception allowance.

### Exact-head external-corpus startup root cause

Actual9a8 CPython3.11/3.13 artifacts contain five external projects each with CROSSHAIR_INCOMPLETE_EVIDENCE: target_crosshair.py's newly required icontract import is absent in customer environments. Local/full/offline environments contained icontract and masked this regression. Preserve the real helper postcondition and customer contract behavior. Reuse existing _DOMAIN_ENTRIES plus _selected_distribution/_domain_graph: declare icontract as a CrossHair entry without adding it to pinned ownership, so customer precedence and dependency metadata remain exact and absent customers use the existing recorded sealed fallback. This one declarative dependency change avoids a custom loader, decorator stub/waiver or broad analyzer sys.path fallback. Existing origin/RECORD/missing/incompatibility guards and all other domains remain intact. Actual isolated startup and provider/missing/substitution controls precede acceptance; checksum and normalCI signing remain required.

### Required dependency's owned virtual namespace

The real isolated pinned Linux startup after declaring icontract reaches another source-proven issue: asttokens2.4.1 imports Six's synthetic six.moves, whose actual spec has no file origin. The current PathFinder-only analyzer finder rejects it despite owning verified six.py. Reuse the registered importer of the verified Six parent for only its known six.moves names; validate exact parent origin/file and importer/spec identity, retaining real virtual specs and no generic fallback or fabricated origin. Bind the new lookup callable into existing startup fingerprinting. Real Six source/in-process controls and real isolated before/after CLI precede acceptance. Customer-owned libraries retain existing precedence. This is required package semantics within existing verified dependency routing, not a new checker/commit authority or arbitrary importer exemption.

### Virtual validation phase quality

The real public Radon runner reports new CC14 in the amended filesystem verifier (unchanged warning threshold12). A real public-runner policy assertion precedes a direct virtual-spec identity verification helper. The helper retains exact registered-parent/name/loader predicates and the same ImportError fallback; the filesystem caller retains all original location/origin checks. No threshold, predicate, side attribution or suppression changes; caller/helper source and AST reversibility are reviewed independently.

### Complete configured startup quality

Complete public BasedPyright/Pylint scans of the new registered-owner phase independently reproduce optional origin/loader diagnostics and a generic type-check advisory. Declare the actual ModuleSpec return protocol, retain exact loader class identity (subclasses remain rejected), and explicitly reject missing loader/origin before consumption. Hoist only newly introduced fixture imports, preserve all older deferred/private bindings, use public cached-module validation for the foreign virtual-loader proof and preserve literal startup mutation bytes under normal line formatting. No checker, analyzer policy or suppression changes.

Complete source scanning after explicit optional guards reveals CC13 in the registered-parent phase. Extend the same real policy case to every new phase before separating verified parent/importer acquisition from registered spec matching. Exact parent origin/file, missing-loader, exact class and namespace checks retain their order; bind the new parent verifier into the same startup fingerprint and exercise both replacement/in-place mutation negatives. No changed warning is hidden or threshold adjusted.

### Read-only ownership audit: registered importer startup binding

A separate root-owned audit identifies that checking a Six parent path and claimed class module is insufficient after customer startup: .pth code may replace both importer/class, mutate its implementation or registered map, or replace the spec factory without changing six.py origin. Real site.addsitedir controls precede binding. Preload only analyzer-owned Six through the existing verified finder before startup, then add its actual module namespace, importer class/function states and registered map identities to the existing before/after snapshot. Legitimate moves/xrange lazy lookup must pass; no generic importer or project-owned Six is changed. This binds the new dispatch participant under the established startup enforcement, not hostile installed-tool containment or new authority.

### Source-bound readonly I/O flag analysis

Actual pinned Linux Pylint4.0.7 reports W0125 for TextIOBase.closed despite real open/closed CLI cases proving that native readonly flag varies. Retrieve that same standard readonly descriptor explicitly through inspect.getattr_static before the same Boolean guard, avoiding inaccurate constant inference while preserving the C-owned state, exception text, no shadow flag and unchanged output/error budgets. A complete public producer RED precedes this narrow expression correction; existing genuine closed-stream and non-text controls remain mandatory. No diagnostic suppression, exception waiver or duplicated mutable closed state is introduced.

### Current-head commit tree race review

Codex P1 PRRT_kwDORVEFbs6rSvC- reports a detached normal-hook child changing the index after the last pre-commit validation. Pre-commit runs before Git creates a commit (Git githooks documentation, accessed12October2026). Independently reproduce with real Git, the actual approved checker, a detached bounded child and a commit-msg timing barrier; this barrier supplies scheduling only, never checker authority. Preserve the same mandatory git -c core.hooksPath route and both existing validations/all normal hooks. Add a worktree-only external prepared reference-transaction callback: it validates the actual immutable proposed commit tree through a private alternate index and the SAME approved checker before Git advances the bound branch. Nonzero prepared status aborts ref advancement; committed/aborted notifications do not become authority. No shared hook/config, checker policy, new signing authority, arbitrary Git-path containment or hostile installed-tool containment is introduced.

Actual Git valid-control diagnostics show a second prepared transaction deleting the AUTO_MERGE pseudo-ref after the real branch transaction succeeds. This is metadata cleanup, not commit/tree promotion. Permit only a canonical AUTO_MERGE-only deletion (new zero OID) after validating the same caller binding; never accept a nonzero metadata update or a different reference. Preserve actual branch/HEAD commit validation and all normal hooks. The earlier draft rejected cleanup after the valid branch update and is not passing evidence.

The accepted tree is the complete actual index snapshot captured before normal hooks. Validate that immutable snapshot with the approved checker, execute every normal hook against the original caller index, require the index to remain identical on successful completion, then validate the same immutable tree again and record it privately. Intentional hook staging/repair changes require a review/retry; they cannot silently authorize a different source tree. This retains both real authority checks and normal status propagation while removing the last mutable-index handoff. The prepared callback additionally checks actual proposed-tree equality and the same authority before reference advancement.

### Bounded actual commit-race proof phases

Separate the existing late-barrier fixture preparation into direct private phases without altering any generated child/barrier bytes, Git arguments, timing, assertions or valid-tree fallback. Use the actual Popen context manager for the owned Git process and retain reader/marker/result behavior. The complete public Radon and configured Pylint producers must report no new targeted length, resource-lifecycle or import-order findings; unchanged thresholds and earlier definitions remain mandatory.

The complete original pinned Semgrep packs also cover the new transaction diagnostic and cleanup proof name. Preserve CLI bytes and old calls; use an explicit stderr write for the new diagnostic and a specific Git cleanup test identity. Do not suppress original retained fixture findings.

The private complete-tree acceptance record must clean its allocation even if writing/flush/rename fails. A real NamedTemporaryFile allocation with an injected filesystem write rejection proves no private temporary file remains; failure never yields commit authority.

### Standard stream protocol within the bounded discard adapter

The source5c review reports real normal-stdio incompatibility: the discard TextIOBase lacks encoding/errors, reconfigure and binary buffer writes. Within the already authorized analyzer-output correction, use native TextIOWrapper/BufferedWriter operations over a bounded non-collecting raw sink. Capture each original standard stream's codec/error policy, line buffering, write-through and ordinary name/tty/descriptor metadata; reconfigure only the private proxy, never reporter streams. Text/binary writes are drained synchronously so overflow rejects inside the write before contract acceptance. Preserve the existing four-MiB physical byte cap and canonical UTF-8 text charge; mixed binary/text shares that same cap. Default standalone sink keeps UTF-8/strict. This is not general file/seek emulation or protection against arbitrary direct descriptor writes/hostile in-process mutation, matching prior isolation limits. No third-party dependency, authority, deadline, output-reader bound, filter or coverage policy changes.

Actual complete CLI ordinary-stdio controls must succeed before the adapter and under pinned CrossHair afterward, including metadata, reconfiguration and bytearray/memoryview buffer writes; false contracts still fail and actual reporter identities/text remain. Additional binary/mixed/alternate-codec quota and closed/type controls exercise real standard IO layers. Real native wrappers are preferable to a hand-built codec/attribute facade; that facade would duplicate standard error and reconfiguration semantics. A direct raw byte counter plus native wrapper is the bounded milestone; all gates and normal CI signing remain required.

Budget domains are explicit: all actual encoded/binary/raw output shares one four-MiB physical counter; text separately retains the original four-MiB canonical UTF-8 counter. Do not temporarily charge UTF-16 physical bytes against the canonical text counter or combine two encodings as if they were one. Valid writes below both limits must succeed. Canonical charge belongs to text; direct binary bytes belong to the shared physical counter. This preserves the original text threshold and the new standard binary interface under the unchanged physical bound, without context flags or caller-stack heuristics.

### Portable prepared-transaction fixture boundary (12 October 2026)

Actual ee9d candidate CPython3.12 public rows show transaction test setup FileNotFoundError. The fixture simulates all Git/interpreter/hook state but still invokes production host-only ps for process birth. Independently reproduce the exact fixture with PATH containing no process tools before changing it. Supply a stable owned fixture birth identity alongside the already simulated PID/Git metadata; keep all original test assertions and production entry bytes exact. This does not substitute for the mandatory real Git host proofs, which retain actual ps birth validation and complete prepared-tree enforcement. Hosted original private stack traces remain unavailable; independent incomplete/oversized and macOS incomplete analysis are not waived by this bounded reproduction.

### Reporter descriptor isolation amendment (12 October 2026)

Fresh signed-head review identified that borrowed fileno metadata grants an actual write capability to the original reporter. The prior scope statement excluding direct OS writers does not justify introducing this capability from the discard adapter. Preserve native encoding/errors/reconfigure/binary protocols and every existing four-MiB quota, but reject descriptor access with standard UnsupportedOperation at text/binary/raw layers. This restores the old discard stream descriptor behavior. The existing metadata proof must compare readable non-capability metadata only; retain its identity/parameters/assertions and add actual raw OS-write rejection controls. Do not claim confinement of arbitrary literal OS descriptors or hostile in-process mutation. The separate same-owner transaction guard finding remains unresolved and requires independent boundary analysis; no new protected owner/OS enforcement authority is introduced by this routine runtime repair.

### Materialized native adapter argument branches (12 October 2026)

The retained native worker's actual public KISS metric reports nesting5 against unchanged3. Use flat ordered guards with explicit iteration continuations in the existing for loop, retaining each original equality/startswith predicate, branch body, path-escape rejection, argument order and fallback. Reversing those guards must reconstruct the entire original worker module AST. This is a scoped source quality correction, not a parameter-count waiver or trust/lifecycle/ownership change. All existing worker requests/replies/arguments and bool/type/RECORD/source-precedence controls remain. The separate owner OS restriction decision is still pending; no dependent restriction is implemented.

### Standalone bootstrap proof execution roles (12 October 2026)

The actual candidate and independent public rows contain54 isolated-startup probe failures in15functions. These controls deliberately start a fresh owner interpreter with -I/-S to test runtime attachment from an empty interpreter. They require mandatory host execution; an attached project launcher must continue rejecting those flags. Move the original complete proof definitions and their factory/fixture closure directly into the existing mandatory host module, retaining all original bodies, parameters, decorators, assertions and literal subprocess arguments. Keep the one factory shared with a retained portable test exported there without copying or changing it. Keep all15tests plus fixture defined directly in the already mandatory controller host proof file so Full, SMART, Linux canonical and all three macOS boundary executions still require all54cases. Default portable discovery must not collect the standalone probes. This is execution-role correction, not a skip or raw interpreter bypass inside a capsule. Keep pyproject/SMART/orchestrator/customer workflows, every existing31Bash/10compiled control, timeouts/thresholds and acceptance unchanged. The host workflow gains only the actual source import environment and missing direct icontract dependency (packaging pinned consistently) required by the unchanged factory; no installed controller or analyzer upgrade. Prove actual collected case suffixes identical, original AST reconstruction and exact approved checker admission before finalization. Existing OS-boundary question remains pending; no dependent enforcement implementation.


## Complete CrossHair adapter type correction (2026-10-12)

The human-authorized CI repair includes twelve independently reproduced basedpyright errors at the exact public locations. Pinned Linux basedpyright1.39.10 and local1.39.6 both report the same eight private-re-export accesses and four argument-type mismatches. Normal repository type selection omits `packages`, so it does not discharge this complete-file finding. Preserve every live binding using explicit module namespace operations already used by the existing proofs, accurately typed as the mutable dictionaries of these actual module objects. Preserve original constructor annotations and cast reporter call sites without altering their objects; retain native error-policy values and the original Literal marker with type-only casts justified by upstream registration accepting typing annotations. Compare the complete AST under the declared annotation/namespace/cast reversal; run the real public producer and retain every old behavioral proof. No policy, workflow, checker, entry or authority change is required. The separate unresolved OS-boundary decision still holds commits.

The earlier three-module offline contract diagnostic is bounded independent evidence, not the private hosted report: raw and wrapped genuine counterexamples have identical nonzero diagnostics, while report-all returns three Not confirmed conditions. It neither waives incomplete contracts nor establishes a sealed CI root cause.

## Retained pytest selector literal layout (12 October 2026)

Two current C0301 findings are long literal pytest selectors in the existing regression that checks later project contract enforcement. Use adjacent string literals within parentheses, preserving the complete Python AST and every actual subprocess argument. This is a reversible lexical correction; no new repository test is needed. A bounded actual public-producer assertion supplies failing/passing quality evidence, and the original behavioral regression plus mandatory final gates remain. Existing deferred imports, private references, exact-type semantics and callback signatures are untouched. The independent annotation/cast scratch probes did not remove the remaining E1102 clone inference diagnostic and were not applied; it remains unwaived. The new OS-boundary question still holds commits.

## Owner-approved CI completion boundary (13 October 2026)

The owner canceled the protected broker/admin path and approved reuse of the existing CI process. This developer utility works on developers' own source; deliberate hostile local programs and administrator bypass prevention are outside this correction. Retire private hook installation/reference-transaction coordination rather than attempting local immutability. Keep all ordinary hooks and the existing narrow capsule-only DEFERRED exception.

Reuse the existing scheduling checker on an alternate index loaded from the actual PR head commit. Retain approved integrated/immutable-bootstrap selection, complete history/path/object/expiry guards, complete delta and NUL-safe serialization. Run the check in the existing required Verify Module Signatures job before its signing steps, after dependency setup. Broaden only that workflow's PR trigger to all dev/main PRs so relevant test/script-only changes cannot omit the required check; run this scheduling contract for feature PRs to dev. The release dev-to-main process retains its existing separate gates. This placement leaves the already pinned review orchestrator and reusable review bytes unchanged. Quality prerequisite propagation remains exact.

Preserve non-capsule CI behavior: report no relevant scheduling delta without inventing a local PASS for deferred capsule review. Regressions prove actual committed-tree selection despite unrelated live index/worktree changes, disabled/filtered/nonblocking scheduling rejection, exact approved authority selection, cleanup, CLI failure status and all quality prerequisite outcomes. Replace tests solely for retired private installation/process-birth/transaction machinery with CI boundary tests; keep ordinary local deferral and every runtime/canonical proof. Original P1 reproduction and earlier evidence remain historical, not invalidated. No CI/controller/signing authority upgrade or new service is introduced.

The ruleset already requires quality/signing checks and resolved threads; the owner retains administrator bypass. The normal maintainer workflow must not use bypass to claim checks passed. A fresh signed head and complete required hosted review remain acceptance, not local component success.

The scheduling checker retains its local deferral surface restriction for local hooks. In CI, its scheduling arguments contain the complete capsule-related committed delta; unrelated source still belongs to the unchanged full candidate/independent review subject. A mixed PR must not acquire a new local-deferral-only restriction from reusing the checker. No reviewed path is removed from either hosted review.

The actual public Radon producer identifies complexity15 in the new combined real-Git fixture. Split only subject preparation into a direct private helper and keep every Git argument, mutation, assertion and parameter identity unchanged. This obeys existing quality thresholds without adding a test abstraction framework or suppressing the warning.

### Actual hosted host-proof dependency closure (13 October 2026)

Signed head6573e67e Linux job115038801593 fails actual collection on beartype, before any canonical/host proof executes. The ordinary import of specfact_code_review.run also imports findings/scorer and therefore Pydantic. Preserve all existing package/module imports and proof bodies; declare beartype0.22.9 and pydantic2.14.0, matching the validated repository environment, alongside existing exact host prerequisites in both mandatory Linux/macOS setup commands. Prove the actual minimal environment fails collection before provider installation, then completes collection and all54standalone cases afterward; this diagnostic does not replace hosted compiled/installed acceptance. No controller upgrade, altered launcher flags, raw capsule interpreter bypass, test skip or code/signature change.


## Current-head native failure diagnosis (13 October 2026)

All nine actual b90a7bd native execution cells fail completed-review validation, while Linux candidate reviews succeed. Their private analyzer reports are not retained; the generic exception cannot identify the incomplete member. Add a small allowlisted console projection at the existing validator failure point. Preserve the original exception, exit, report/assertion rules, deadlines, matrices and publication gates. Do not upload raw reports or infer a sealed analyzer root cause. This is a bounded diagnostic repair within the approved existing-CI developer workflow; no broker, administrator setup or new enforcement authority.

The original local-script diagnostic attempt passed full gates but its commit was correctly rejected by the immutable approved checker: those two local review surfaces are outside the capsule-only deferral inventory. Do not expand that inventory or bypass the hook. Preserve the complete attempted patch/evidence and return both acceptance files to exact HEAD bytes. Place the failure-only projection in the existing native execution workflow, with behavioral controls in the existing capsule projection test module. This uses the approved existing-CI scope: no local acceptance code changes, new authority, threshold change or raw-report artifact.

### Native contract observation refinement (13 October 2026)

Actual17765 native reports identify contracts error/UNKNOWN in seven cells, while two independent pre-review boundary paths write no report. The exact CP312 artifact and Flask commit reproduce identical raw/wrapped CrossHair exit0/no stdout outside the attached capsule; this does not establish the hosted cause. Extend only the existing failure-only projection with fixed CrossHair process/unrecognized/timeout/launch codes and native-worker request/result/replay codes. Derive these from recognized tool/rule identities or the already allowlisted contracts error row; never print raw diagnostic strings. Emit the optional field only when a known observation exists, preserving existing records and all original execution, report bounds, matrix, timing, validation and authority. No parser relaxation, signature creation, local installation or acceptance inference.

### Required CI wrapper source authentication (13 October 2026)

Actual Codex P1PRRT_kwDORVEFbs6r_k81 identifies that the existing signature job selects the candidate checkout and invokes its scheduling wrapper. Preserve the simple existing-CI design: add one blocking stdlib SHA-256 authentication step immediately before that invocation, under the exact same PR-to-dev condition. Pin the already reviewed wrapper bytesda892a322e0036cda78874adbea9a8169ec899752c797621bebcd52446b664bb; the wrapper continues to select actual integrated checker bytes or the same approvedc65/blobcc bootstrap. No checker, signing authority, administrator provisioning or local enforcement boundary changes. Every original workflow field and validator command reconstructs after removing this authentication step. A controlled early-success wrapper regression is ordinary CI regression evidence, not a malware model; intentional wrapper updates need the usual reviewed source/pin update.


### Complete committed review surface (13 October 2026)

Current Codex P2 PRRT_kwDORVEFbs6sAvNA identifies a missing complete-path argument in the existing CI wrapper. Reuse its existing NUL-delimited Git helper without selectors for the complete committed delta. Keep capsule paths as the first approved-checker argument and pass complete paths second. Both come from the same private alternate index and merge base. Preserve the approved checker bytes and authority; update only the reviewed wrapper digest in the existing authentication step and its exact regression expectation after the source change. Strengthen the existing mixed-source control to reject its unrelated reviewable path; all old test identities, arguments and other assertions remain. No broker, admin setup, policy waiver or hostile-program containment is added.
