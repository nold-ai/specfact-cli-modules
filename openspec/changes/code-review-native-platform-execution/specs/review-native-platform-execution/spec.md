# Specification: review-native-platform-execution

## Scope revision — 2026-09-30

Owner-approved macOS ARM64 first delivery. This replaces the prior cross-platform/C15 prerequisite scope; deferred platforms remain unsupported by this change. The owner-approved managed-process revision of 2026-10-02 supersedes unrestricted subprocess compatibility. Production remains gated on signed feasibility.

## ADDED Requirements

### Requirement: Native local execution

Code Review SHALL add a dedicated macOS ARM64 capsule while preserving Linux x86-64 execution. The ordinary review and runtime inspect/prepare commands SHALL select the approved platform backend automatically. CPython 3.11–3.13 is the candidate ABI matrix; only tested macOS versions and native ARM64 runtime closures may be published. Windows, Intel macOS and Linux ARM64 are deferred, not acceptance obligations of this delivery.

#### Scenario: Agent invokes the native CLI

- **GIVEN** a signed supported macOS ARM64 installation
- **WHEN** an ordinary user runs review or runtime inspect/prepare
- **THEN** the selected runtime executes natively without requiring sudo, Docker, WSL, an additional VM, Rosetta or CPU emulation; compatible full VMs and physical systems are eligible, and diagnostics and reports identify the actual OS, architecture, ABI and backend

#### Scenario: Architecture is not silently substituted

- **GIVEN** a required interpreter, executable or library lacks a compatible ARM64 slice or the host OS is unvalidated
- **WHEN** runtime preparation or execution is requested
- **THEN** execution fails with an actionable unsupported diagnostic; no Homebrew, emulated or development-host fallback satisfies capsule acceptance

### Requirement: Native isolation capability evidence

Production backend approval SHALL follow harmless native feasibility tests of the initial-distribution managed broker/bootstrap against the capability contract. Earlier Seatbelt, App Sandbox and XPC experiments remain historical evidence; they are not alternate admission routes. The managed candidate is not preapproved. Mandatory boundaries SHALL cover filesystem reads/writes, network and IPC access, inherited descriptors, startup/load-path integrity, resource limits and complete child-process lifecycle. Exact mechanisms, OS support and numeric limits SHALL be frozen from measured results before production implementation.

#### Scenario: Isolation and cleanup are proven

- **GIVEN** a candidate helper and independently observable allow/deny fixtures
- **WHEN** tests exercise authorized reads/writes and prohibited host reads/writes, outbound and listening network operations, inherited descriptors and child processes
- **THEN** allowed operations succeed and denied operations fail for the intended policy reason; helper startup or parser failure is not successful confinement evidence

#### Scenario: Kernel RPC denial retains exception endpoints

- **WHEN** the signed control fixture receives KERN_DENIED or KERN_NO_ACCESS from exception-port swapping
- **THEN** acceptance still requires independent snapshots proving set, swap and clear cannot change the original endpoint, successful unconstrained positive controls, and the normal target exit
- **AND** unrelated errors or a changed endpoint cannot satisfy acceptance

#### Scenario: Required capability is unavailable

- **GIVEN** a required isolation capability or analyzer is missing, incompatible or unverifiable
- **WHEN** launch readiness is evaluated
- **THEN** the runtime rejects analyzer launch and reports incomplete evidence under the released status/exit contract without weakening isolation

#### Scenario: Linux launch identity is absent after platform selection

- **GIVEN** a Linux capsule runtime without its verified Bubblewrap identity
- **WHEN** a member launch is requested
- **THEN** the controller returns incomplete member evidence before preparing a sandbox or starting an analyzer

#### Scenario: Cancellation and descendants are bounded

- **GIVEN** a managed worker requests child execution or attempts forbidden direct creation, session changes or process-group escape
- **WHEN** timeout, user cancellation or controller failure occurs
- **THEN** all governed workers terminate within five seconds; fixtures independently check survivors and resource ceilings rather than treating killpg alone as proof

#### Scenario: A stalled bootstrap cannot hold startup indefinitely

- **GIVEN** an admitted, signed bootstrap has entered tracing but remains alive without sending its confinement-ready marker
- **WHEN** the startup deadline expires or the controller closes its private channel
- **THEN** the broker rejects launch, kills and reaps that worker, and leaves no reusable handle or uncontrolled process; it never blocks indefinitely on the marker pipe

#### Scenario: Hostile writable output cannot delay cancellation

- **GIVEN** a worker has created a large or changing tree in its granted output or temporary directory after launch
- **WHEN** its owner sends WAIT or CANCEL for the broker-assigned handle
- **THEN** the broker processes lifecycle control without recursively traversing worker-writable trees, and cancellation plus independent survivor observation remains within the five-second cleanup bound
- **AND** launch-time path, ownership, and tree checks and terminal output-file checks remain fail-closed

#### Scenario: Startup cannot bypass confinement

- **GIVEN** a fixture supplies loader injection variables, inherited open files or unauthorized IPC handles
- **WHEN** the helper starts and loads project code or a native extension
- **THEN** untrusted code cannot execute before the required boundary is active or use inherited access to bypass it; allowed Apple system libraries are explicitly distinguished from prohibited ambient dependencies

#### Scenario: Native XPC boundary candidate must prove descendant cleanup

- **GIVEN** the historical XPC candidate is retained as rejected feasibility evidence
- **WHEN** its ordinary-user ARM64 application runs bounded fixtures through an embedded XPC service
- **THEN** native acceptance MUST include normal subprocesses, detachment, cancellation, timeout, client death and service death with an independent observer
- **AND** any survivor after five seconds, missing receipt or emergency cleanup MUST reject the candidate, without enabling production selection
- **AND** repetition counts, architecture, build/profile identity, exact failure and observer cleanup MUST be recorded; 100 repetitions per lifecycle race are required before positive admission
- **AND** no privileged helper, process polling or cooperative PID report may substitute for a mechanism establishing descendant ownership

### Requirement: Portable review semantics

The macOS backend SHALL preserve the exact released baseline's scope, findings, differential classification and verdict/exit semantics. C15 delivery is independent. New platform evidence SHALL have explicitly versioned producer/consumer compatibility, and local evidence SHALL NOT acquire protected PR authority by declaring an identity.

#### Scenario: Portable fixture classification

- **GIVEN** equivalent approved analyzer/policy versions and portable clean/defective fixtures on Linux and macOS
- **WHEN** all required analyzer members execute
- **THEN** introduced, fixed and unchanged findings and authoritative status/exit results agree; skipped, empty or UNKNOWN required evidence cannot pass acceptance

#### Scenario: Synthetic enforcement tests use bounded isolated subjects

- **GIVEN** unit tests replace analyzer execution with synthetic complete evidence
- **WHEN** they verify changed-line enforcement, retained failures or report readback
- **THEN** they SHALL use a minimal isolated source fixture rather than repeatedly hashing the caller's entire checkout
- **AND** all existing enforcement assertions and real snapshot-identity, mutation and installed-customer checks SHALL remain required; no timeout, test inventory or sandbox gate may be weakened

#### Scenario: OS dependent project tests

- **GIVEN** a project intentionally behaves differently on macOS and Linux
- **WHEN** its native test slice runs
- **THEN** reports preserve the actual platform and outcomes without forcing cross-platform equality or relabeling genuine failures

#### Scenario: Older protected consumer receives native evidence

- **GIVEN** a consumer has not approved the native report/runtime contract
- **WHEN** it receives macOS evidence
- **THEN** it rejects unsupported evidence explicitly rather than interpreting it as historical Linux or protected PR assurance

#### Scenario: Native preparation fails before an analyzer launches

- **GIVEN** a macOS ARM64 controller selects a native analyzer ABI
- **WHEN** native acquisition or preparation returns incomplete evidence
- **THEN** the report retains the selected Darwin/ARM64 environment identity and native platform admission context
- **AND** it does not label the failed run as a Linux capsule or imply that an analyzer ran

#### Scenario: Pylint fatal diagnostics remain incomplete analyzer evidence

- **WHEN** Pylint returns a fatal `F` diagnostic, including an internal crash or a diagnostic outside the selected source files
- **THEN** the review retains a `tool_error` finding anchored to the selected source and preserves the fatal rule and diagnostic
- **AND** ordinary project findings retain their existing mapping and cannot make the failed analyzer appear complete
- **AND** independent corpus acceptance rejects tool errors and fatal Pylint findings even in an older report that labels the fatal finding as style

### Requirement: Verified provisioning and offline reuse

Module-shipped files SHALL retain full-module signature/checksum verification. External native runtimes SHALL have an approved signed manifest binding artifact and installed-payload digests, OS, architecture, ABI, complete dependency closure, released policy identity and backend/profile version. Cache identity SHALL include those bindings. Provisioning, extraction and each launch including offline reuse SHALL verify the selected payload and admission policy, and prevent substitution between verification and use.

The signed native manifest SHALL bind the exact closed analyzer-version map used by that platform artifact. Native report evidence and profile-version admission SHALL use this authenticated map rather than the historical Linux version map. Linux artifacts and evidence SHALL retain their existing identities until a separately verified Linux upgrade is published. Missing, extra, malformed or mismatched native analyzer-version bindings SHALL fail before execution or yield incomplete evidence; a native analyzer result SHALL never be relabeled as a different released version.

#### Scenario: Large signed extraction budget does not preallocate that budget

- **GIVEN** a verified Linux regression capsule layer has a signed unpacked-byte allowance larger than the available controller memory
- **WHEN** acquisition decompresses a layer whose actual content fits the environment
- **THEN** it reads bounded chunks rather than allocating the entire signed allowance in advance
- **AND** compressed digest, complete uncompressed diff-ID, unpacked-byte and file-count limits, duplicate-path rejection and whiteout safety remain mandatory before application
- **AND** historical Linux artifact identities, worker limits and acceptance thresholds remain unchanged

#### Scenario: Maintained manager images retain their verified provenance

- **GIVEN** a capsule candidate includes the reviewed managed uv image and its complete source, patch, license, and signed-binary provenance
- **WHEN** analyzer preparation records native signatures and assembly copies the final runtime
- **THEN** it verifies the existing ad-hoc hardened uv signature without re-signing or changing the bound executable
- **AND** preparation revalidates the full maintained artifact after native inventory, while assembly rejects missing, changed, or substituted uv provenance before creating its output
- **AND** optional maintainer inputs are never inferred from host PATH, and candidate observations cannot approve production publication

#### Scenario: Managed uv build launches retain the fixed channel budget

- **GIVEN** a confined Hatch or uv build invokes the bound Python image with valid arguments and an inherited private environment
- **WHEN** XML serialization alone would exceed the existing 4096-byte managed request frame
- **THEN** managed uv serializes the unchanged launch document as a binary property list accepted by the existing broker parser
- **AND** the final wire request, individual strings, argument/environment counts, owned-handle lifecycle and execution grants retain their existing bounds; oversized binary requests fail before channel use
- **AND** managed uv provenance binds the changed bridge source and its newly built ad-hoc hardened executable; prior executable receipts are not reused for altered bytes

#### Scenario: Cached native runtime

- **GIVEN** a complete approved cache for the selected OS, ABI and policy
- **WHEN** review runs offline
- **THEN** it revalidates the payload and uses only the bound runtime while recording its identity

#### Scenario: Explicit local publication reuses a cache offline

- **GIVEN** an authenticated local publication supplied the manifest, detached signature and public key for a capsule already installed in the verified cache
- **WHEN** offline mode is selected and the source archive is unavailable
- **THEN** the backend constructs no archive reader, revalidates the cached payload and executes only that exact bound identity

#### Scenario: Native backend has no admitted artifact

- **GIVEN** Code Review runs on Darwin ARM64 with CPython 3.11, 3.12 or 3.13
- **WHEN** backend selection derives the matching `darwin-arm64-cp311`, `darwin-arm64-cp312` or `darwin-arm64-cp313` identity but the authenticated artifact catalog has no admitted entry
- **THEN** runtime preparation returns actionable incomplete evidence for that exact identity without executing host analyzers, compiling customer-runtime tools or selecting a Linux artifact

#### Scenario: Already incomplete native evidence keeps its root diagnostic

- **GIVEN** every analyzer is already UNKNOWN from a missing runtime, project acquisition, or snapshot failure
- **WHEN** report assembly cannot activate the platform-specific suppression catalog because no analyzer-version identity was available
- **THEN** the report remains UNKNOWN with the original actionable diagnostic for each analyzer
- **AND** suppression activation cannot promote the report or replace the root cause with a secondary policy-version mismatch

#### Scenario: Controller Python is newer than the native analyzer matrix

- **GIVEN** the SpecFact CLI runs under CPython 3.14 on Darwin ARM64
- **WHEN** Code Review selects its analyzer runtime
- **THEN** it selects the pinned CPython 3.12 native analyzer environment without claiming CPython 3.14 project-extension compatibility
- **AND** project dependencies or syntax incompatible with the selected runtime yield actionable incomplete evidence, never host execution or a false PASS

#### Scenario: Native signing metadata is bound to the payload

- **GIVEN** an authenticated Darwin ARM64 capsule manifest declares executable native-signing records
- **WHEN** cold acquisition or offline cache reuse verifies the capsule
- **THEN** every executable payload is covered by authenticated signing metadata and its observed native signature matches before the cache is returned for backend admission

#### Scenario: Native analyzer versions differ from Linux

- **GIVEN** the authenticated Darwin ARM64 manifest binds Semgrep clean and bug-hunt analyzers to 1.175.0 while the preserved Linux artifact remains on 1.144.0
- **WHEN** a native review report is assembled and its profile evidence is admitted
- **THEN** both native analyzers are reported and checked as 1.175.0 without changing or falsely relabeling Linux evidence

#### Scenario: Native analyzer-version binding is incomplete

- **GIVEN** a native manifest omits, adds or malforms any member of the closed ten-analyzer version map
- **WHEN** capsule acquisition authenticates the manifest
- **THEN** the capsule is rejected before cache publication or analyzer execution

#### Scenario: Invalid native artifact

- **GIVEN** a helper, interpreter or native library is modified, incompatible or unsigned contrary to the approved policy
- **WHEN** provisioning or launch validates the runtime
- **THEN** execution fails before untrusted analyzer or project code runs

#### Scenario: Module-shipped native artifact changes

- **GIVEN** a module-shipped helper or resource changes
- **WHEN** module integrity is verified
- **THEN** verification fails without narrowing the full-module boundary to Python files

#### Scenario: External cache has no approved binding

- **GIVEN** an external runtime is not covered by its approved signed manifest
- **WHEN** first use or offline reuse is attempted
- **THEN** it is rejected even if the module signature itself verifies

#### Scenario: Stale external cache identity

- **GIVEN** a cache belongs to an earlier runtime or policy/backend identity
- **WHEN** the current selection is launched
- **THEN** the stale identity is rejected before admission or execution

#### Scenario: Partial external runtime cache

- **GIVEN** preparation is interrupted or two preparations overlap
- **WHEN** a consumer examines the resulting cache
- **THEN** partial output never becomes reusable; publication is atomic and concurrent preparations cannot mix payloads

#### Scenario: Mixed external runtime cache

- **GIVEN** files mix versions, architectures or Python ABIs
- **WHEN** the selected payload is verified
- **THEN** the mixed closure is rejected despite individual valid file hashes

#### Scenario: Verification to launch substitution

- **GIVEN** an adversarial fixture replaces or redirects a verified payload before use
- **WHEN** the helper opens or executes it
- **THEN** the replacement cannot execute and the runtime reports integrity failure; the approved design records how this is enforced on macOS

### Requirement: Released baseline implementation gate

Native work SHALL use a verified released baseline incorporating layout correction #459 and portable project runtimes #473 (Code Review 0.50.1 as the initial review baseline). Core #679 and modules #417 SHALL NOT be blanket prerequisites. Actual consumer incompatibilities SHALL require explicit paired scope. Production implementation SHALL remain gated on approved isolation/dependency feasibility results and a bounded design. Optional #434, preflight, seals and historical RED ledgers SHALL NOT be prerequisites.

#### Scenario: Prerequisite remains incomplete

- **GIVEN** native confinement, dependency admission or required consumer compatibility is unresolved
- **WHEN** production implementation is prepared
- **THEN** it stops at the feasibility gate while planning and bounded feasibility work may proceed

#### Scenario: C15 remains unreleased

- **GIVEN** the selected released review contract and native consumer compatibility are established
- **WHEN** native readiness is assessed
- **THEN** open C15 issues alone do not block delivery and native work does not implement or claim C15 semantics

#### Scenario: Baseline drives the full lifecycle

- **GIVEN** the released identities and feasibility report are verified
- **WHEN** production design is approved and implemented
- **THEN** focused failing-first tests precede code, current native and Linux regression results verify the candidate, and signed published installation is read back

### Requirement: Dependency source admission

The full native closure SHALL satisfy released dependency policy independently of signature validity. nodejs-wheel-binaries remains prohibited; BasedPyright 1.39.10's direct requirement on that distribution SHALL be resolved explicitly rather than hidden by swapping a Node executable or using --no-deps. Replacement distributions/builds SHALL have reviewed provenance, licenses, metadata and compatibility, with fresh signed identities. No replacement is approved by this planning revision.

#### Scenario: Signed dependency is prohibited

- **GIVEN** a correctly signed runtime includes a prohibited dependency
- **WHEN** provisioning or offline launch checks admission
- **THEN** it fails before execution; signatures and ordinary trust exceptions cannot override the prohibition

#### Scenario: Inherited C14 lock conflicts with policy

- **GIVEN** the historical Linux lock and BasedPyright metadata reference nodejs-wheel-binaries
- **WHEN** the native dependency graph is audited
- **THEN** design approval remains blocked until a compliant complete closure or separately approved policy change exists; old signatures confer no exemption

#### Scenario: Policy-admissible replacement is verified

- **GIVEN** a reviewed replacement and complete transitive/native closure have new approved identities
- **WHEN** all admission, integrity and platform tests pass
- **THEN** native execution may proceed without satisfying the new selection from a superseded cache

#### Scenario: Explicit Darwin-only Z3 derivative preserves authenticated retained bytes

- **GIVEN** the pinned upstream wheel includes ten byte-identified Windows DLLs without verified redistribution terms
- **WHEN** a maintainer explicitly requests the versioned Darwin-only derivative with the pinned upstream release archive
- **THEN** preparation SHALL authenticate wheel, release, source/native linkage and license before output, omit only the exact reviewed DLL identities, and include the authenticated license in the new wheel
- **AND** the derivative SHALL have a distinct version, filename, complete RECORD and provenance binding every unchanged retained byte, omitted member and added license
- **AND** missing or altered linkage, unknown DLLs, license tampering or an absent release archive SHALL reject before output
- **AND** the historical metadata-only derivative SHALL remain reproducible, and no derivative alone SHALL grant dependency or production admission

### Requirement: Native project runtime preparation

The macOS backend SHALL carry forward pip/pip-tools, Hatch, uv and Poetry discovery, source selection, pytest plugins and coverage from #473. Acquisition, build hooks, preparation and analysis SHALL each have explicit trust, filesystem, process and network boundaries. Mach-O/dyld dependency handling SHALL replace Linux ELF assumptions for macOS. The trusted control domain SHALL remain separate from project code and extensions.

#### Scenario: Dependency-free pip project needs no acquisition entry

- **GIVEN** a pip project declares no dependencies, selected extras, requirements, constraints or dynamic dependency metadata
- **WHEN** its native project runtime is prepared on first use
- **THEN** the controller creates and verifies an empty sealed site-packages layer bound to the source plan and native runtime without requiring a project-specific remote bundle
- **AND** any declared or dynamically supplied dependency keeps the authenticated acquisition requirement

#### Scenario: Runtime preparation preserves the native controller platform

- **GIVEN** Code Review runs on an ARM64 macOS controller with a supported CPython ABI
- **WHEN** the developer invokes `specfact code review runtime prepare`
- **THEN** project Python selection starts from the matching `darwin-arm64-cp*` environment

#### Scenario: Prepared native runtime executes the managed pytest contract

- **GIVEN** an authenticated Darwin/ARM64 project runtime and a selected pytest inventory
- **WHEN** Code Review executes targeted pytest and coverage through the native broker
- **THEN** it binds sealed pytest and coverage projections plus the complete selected inventory to the fixed native worker plan
- **AND** it does not send the Linux portable-worker adapter protocol to the native worker
- **AND** Linux toolchain-lock identities are not passed to the native backend

#### Scenario: Project preparation uses an admitted resource budget

- **GIVEN** an authenticated native project bundle is ready for sealed preparation
- **WHEN** the controller creates the broker request
- **THEN** every resource value is within the versioned managed-process bounds
- **AND** oversized output or descriptor grants are rejected before project code can execute

#### Scenario: Project preparation returns a versioned result

- **GIVEN** the broker launches a fixed native project-manager plan
- **WHEN** preparation completes, is incomplete or rejects its input
- **THEN** the worker writes the exact versioned project-preparation result schema
- **AND** the controller rejects unversioned or differently versioned output

#### Scenario: Wheel installation admits only layouts it can materialize

- **GIVEN** an authenticated wheel places files in a top-level `.data` scheme directory
- **WHEN** sealed project preparation inspects its members before publishing output
- **THEN** it returns actionable `INCOMPLETE` evidence instead of `COMPLETE` with misplaced files
- **AND** no partial site-packages root is published

#### Scenario: Shared explicit wheel directories do not collide

- **GIVEN** two authenticated wheels each contain the same explicit directory entry and otherwise disjoint regular files beneath it
- **WHEN** sealed project preparation preflights and extracts the wheel closure
- **THEN** it accepts the repeated directory and publishes both files
- **AND** duplicate file paths, file/directory type collisions, case-insensitive aliases, and symlink entries remain rejected before extraction

#### Scenario: Native wheel tags respect the host's macOS version

- **GIVEN** an authenticated ARM64 or universal2 wheel declares a minimum macOS release
- **WHEN** the host release is older or cannot be established
- **THEN** the wheel is rejected before extraction with no prepared output
- **AND** a compatible minimum release remains eligible for the selected Python ABI

#### Scenario: Authenticated acquisition becomes a read-only worker view

- **GIVEN** the controller has authenticated a publisher bundle whose recorded files use private staging modes
- **WHEN** it copies the bundle into the project worker snapshot
- **THEN** regular files are sealed read-only before launch
- **AND** the worker requires the authenticated source mode and the sealed effective mode instead of requiring writable inputs

#### Scenario: Native snapshots use canonical macOS path identity

- **GIVEN** macOS exposes the same temporary or project directory through aliases such as `/var` and `/private/var`
- **WHEN** selected files are rebound into an immutable analyzer snapshot
- **THEN** containment and relative paths use one resolved root identity
- **AND** genuine aliases outside that root remain rejected

#### Scenario: Native extension and plugin execute

- **GIVEN** a pinned external project contains an ARM64 extension, pytest plugin and coverage configuration
- **WHEN** its declared manager prepares the runtime and the real test slice executes
- **THEN** Mach-O slices, dylib dependencies, relocatable paths and load origins are checked and actual collection/execution succeeds without changing project pins

#### Scenario: Preparation hook attempts host access

- **GIVEN** a build backend or package-manager hook attempts unauthorized filesystem, credential, process or network access
- **WHEN** preparation runs with its declared acquisition policy
- **THEN** the attempt is denied; acquisition credentials and host state are not exposed to project execution, and analysis remains network-denied

#### Scenario: Project runtime is incompatible

- **GIVEN** a required extension or library has no admitted native build
- **WHEN** preparation analyzes the project
- **THEN** it reports the root incompatibility honestly, preserves independent static evidence where supported, and never converts incomplete required evidence to PASS

#### Scenario: Native coverage exclusions use the admitted snapshot root

- **GIVEN** native selected inputs include production files, selected tests and helpers below sealed test roots
- **WHEN** the complete native pytest adapter evaluates coverage from its physical immutable snapshot
- **THEN** it rebinds controller-validated logical test roots and selectors to that snapshot before exclusion
- **AND** it preserves missing/low production coverage failures, escaping-root rejection, thresholds and project-origin provenance

### Requirement: Signed customer release acceptance

Support SHALL be claimed only after a canonical signed publication passes fresh ordinary-user installation on every advertised macOS/ABI combination and Linux regression acceptance. Distribution SHALL verify native signatures, quarantine, hardened-runtime/entitlement settings and third-party library loading through the real install route. Developer ID and notarization SHALL be optional #488 follow-up work, not initial-release prerequisites. Candidate/source-tree results SHALL NOT substitute for public release evidence.

#### Scenario: Customer installs the published capsule

- **GIVEN** a fresh user-owned installation without publisher credentials, signature bypasses or development links
- **WHEN** the official module acquires its native runtime and runs clean/defective fixtures and pinned external projects
- **THEN** all required analyzers and real tests execute with expected exits; cold acquisition and offline warm reuse pass on the supported matrix

#### Scenario: Customer filesystem differs

- **GIVEN** a repository/cache uses spaces, Unicode, default case-insensitive APFS, symlinks or restricted permissions
- **WHEN** ordinary review and interrupted/concurrent preparation run
- **THEN** paths cannot escape declared boundaries, valid layouts work and unsupported layouts produce actionable diagnostics without source mutation

#### Scenario: Apple distribution and loading controls apply

- **GIVEN** the final helper/runtime has been packaged and signed in the approved order
- **WHEN** a fresh customer installation launches with normal platform protections and loads project extensions
- **THEN** initial-distribution native-signature/quarantine checks and the approved hardening/library-loading policy pass without disabling host protections; final payload hashes match the shipped signed manifest

#### Scenario: Private socket metadata precedes listener readiness

- **GIVEN** the private launchd socket has the correct owner, type and mode before its listener accepts connections
- **WHEN** initial control connection receives ConnectionRefusedError
- **THEN** the fixture client SHALL observe readiness within its existing seven-second connection budget using fresh sockets and rechecking private metadata
- **AND** elapsed metadata checks and socket creation SHALL consume the same deadline; the remaining blocking connect timeout SHALL be refreshed immediately before connecting
- **AND** it SHALL close each unsuccessful socket, authenticate exactly once after connection, and never retry authentication, register another job or retry a fixture
- **AND** other connection errors and an expired budget SHALL remain failures; the three-second metadata, five-second cleanup and 100-repetition gates SHALL remain unchanged

#### Scenario: Native connection failures remain diagnosable

- **WHEN** a native fixture fails with a standard connection refusal, reset, broken pipe or permission error
- **THEN** the sanitized receipt SHALL retain only that explicitly allowlisted exception class
- **AND** raw failure text, authority bytes, private paths and identifiers SHALL remain private; an unknown class SHALL remain unknown
- **AND** this diagnostic SHALL NOT waive any readiness, cleanup or repetition gate

#### Scenario: Linux regression and rollback

- **GIVEN** a macOS candidate or publication is evaluated
- **WHEN** the existing Linux customer matrix and cross-platform fixtures run
- **THEN** Linux remains supported with historical identities intact; a faulty macOS publication can be withdrawn or superseded without disabling Linux or deleting evidence

#### Scenario: Platform-dependent local review is deferred to matching Linux CI

- **GIVEN** the maintainer explicitly authorizes deferring only the unavailable local capsule review to GitHub's matching x86-64 Linux runner
- **WHEN** the candidate PR is updated
- **THEN** CI reconstructs the exact event-bound candidate tree and stages its changes against the merge-base with the event-bound base in an isolated worktree
- **AND** the unchanged pre-commit review helper runs as an ordinary user with its existing enforcement, timeout, integrity and sandbox checks, and any nonzero exit fails the required customer job
- **AND** the controller excludes subject/current-directory imports and anchors missing-runtime bootstrap to the reviewer checkout
- **AND** the reviewer payload stays in the unchanged event-authenticated checkout while the disposable subject index holds the candidate delta; the GITHUB_SHA and tracked-payload checks remain mandatory
- **AND** the deferred review uses its own launcher-scoped cache and leaves the mandatory cold-customer cache empty
- **AND** the local deferral requires a final staged candidate delta against its merge-base with the fetched dev baseline that schedules the capsule workflow
- **AND** only the capsule step may be explicitly deferred on a local ARM64 Darwin feature worktree; invalid values, CI execution and other platforms reject the deferral, while every other original commit-hook component executes normally
- **AND** other local gates remain required, no credentials reach the review process, and this candidate result does not establish public installation or native macOS release acceptance

#### Scenario: Local Docker assembly preserves native identity

- **GIVEN** an experimental payload already built on native macOS ARM64
- **WHEN** Docker performs COPY-only assembly and exports an OCI candidate locally
- **THEN** the image config retains darwin/arm64, payload digests round-trip unchanged, and the candidate is explicitly experimental; container execution is not counted as native acceptance

#### Scenario: Candidate cannot be promoted without native proof

- **GIVEN** a locally assembled candidate lacks approved lifecycle, dependency, signing or customer-installation evidence for its final digest
- **WHEN** GHCR production promotion is considered
- **THEN** publication remains blocked; green packaging checks alone do not grant eligibility and no Linux artifact identity is reused

#### Scenario: Candidate outer archive contains unchecked entries

- **WHEN** a local candidate includes an unreferenced blob, extra regular file, or unexpected directory outside the referenced OCI graph
- **THEN** verification MUST reject it even when every referenced digest and expected payload matches

#### Scenario: Candidate TAR framing is malformed

- **WHEN** an outer archive or payload layer has malformed or truncated headers, incomplete end markers, nonzero trailing data, or unsupported extension headers
- **THEN** verification MUST reject it through ValueError and the CLI MUST report failure JSON rather than a traceback

#### Scenario: Candidate metadata includes non-JSON constants

- **WHEN** candidate metadata contains NaN, Infinity or -Infinity, including unused fields
- **THEN** verification MUST reject it as invalid JSON through both API and CLI

#### Scenario: Candidate metadata encoding or raw paths are noncanonical

- **WHEN** any OCI metadata uses UTF-16/32 or a raw directory header has redundant trailing slashes before TAR decoding normalizes it, or a name/prefix field contains nonzero bytes after its first NUL terminator
- **THEN** verification MUST reject it through API and CLI; metadata requires strict UTF-8 and raw paths are validated before normalization

#### Scenario: Candidate gzip framing is malformed

- **WHEN** a layer has reserved gzip flags, an incorrect optional header CRC, truncation, concatenated streams or trailing data
- **THEN** verification MUST reject it through API and CLI while retaining decompression bounds; a valid optional header CRC remains accepted

#### Scenario: Candidate TAR format identifier is unsupported

- **WHEN** a checksum-valid header has an unknown magic/version combination
- **THEN** verification MUST reject it through API and CLI; only ordinary ustar (ustar-NUL/00) and GNU (ustar-space/space-NUL) headers are supported by this bounded tool

#### Scenario: Candidate image configuration violates known field schemas

- **WHEN** a candidate contains malformed known image configuration fields, including nested config and history entries
- **THEN** verification MUST reject it against the pinned OCI image configuration schema with format checks before reporting success; schema resolution MUST be local and offline

#### Scenario: Candidate index manifest or descriptor violates known field schemas

- **WHEN** an index, manifest or referenced descriptor contains malformed known fields such as annotations, URLs, artifact type or subject
- **THEN** verification MUST reject it using pinned offline OCI schemas before accepting the candidate, including nested descriptor fields

#### Scenario: Candidate introduces unsupported alternative content references

- **WHEN** any selected descriptor includes embedded data, or the index or manifest includes a subject descriptor
- **THEN** the bounded verifier MUST reject the candidate; this profile accepts only the three externally stored manifest/config/layer blobs and does not support embedded data or subject graphs

#### Scenario: Candidate index declares a contradictory media type

- **WHEN** index.json includes an optional mediaType other than application/vnd.oci.image.index.v1+json
- **THEN** verification MUST reject it; the canonical value and omission remain accepted

#### Scenario: Candidate map keys bypass value validation

- **WHEN** annotations or configuration maps contain keys not matched by their schema property pattern, including empty or newline-only names
- **THEN** the bounded verifier MUST reject those keys rather than letting values bypass map validation

#### Scenario: Expected payload contains hard-link aliases

- **WHEN** an expected regular file has more than one filesystem link, including an alias outside the expected tree
- **THEN** verification MUST reject it before reading its bytes rather than treating it as an independent regular file; this check does not claim race-free filesystem sealing

#### Scenario: Candidate numeric TAR fields contain hidden garbage

- **WHEN** mode, UID, GID, size, modification time, checksum or device-number fields contain bytes outside unsigned octal text and NUL/space padding
- **THEN** verification MUST reject the raw header before normalized TAR values are accepted; signed and base-256 numeric extensions are outside this bounded profile

#### Scenario: Candidate numeric fields omit digits or history disagrees with layers

- **WHEN** a required TAR numeric field contains only padding or present non-null OCI history has a non-empty-layer count different from rootfs diff IDs
- **THEN** verification MUST reject the candidate; unused device-number fields may remain padding-only for ordinary files/directories, and absent/null history remains valid

#### Scenario: Candidate TAR header padding contains hidden bytes

- **WHEN** an ordinary outer or layer TAR header contains nonzero bytes in its unused final twelve bytes
- **THEN** verification MUST reject the raw header before normalized TAR fields are accepted

#### Scenario: Candidate TAR ancillary text fields hide bytes

- **WHEN** a link-name, owner-name or group-name field contains nonzero padding after its first NUL terminator
- **THEN** verification MUST reject the raw field before TAR parsing, using the same strict UTF-8 and zero-padding rules as path fields

### Requirement: Managed native process boundary

The macOS ARM64 backend SHALL use broker-owned direct workers, each traced and confined before untrusted execution. Worker-created descendants SHALL be denied by the kernel; compatibility adapters SHALL request managed launches instead. This replaces unrestricted project subprocess compatibility. Broker requests SHALL be bounded, versioned and tied to private invocation channels and broker-owned handles, never arbitrary host PIDs or self-granted permissions.

#### Scenario: Managed subprocess completes

- **WHEN** an admitted Python or pinned native-tool adapter requests an allowed child operation
- **THEN** the broker launches a separately confined direct worker and returns its output, status and lifecycle through the managed channel
- **AND** the controller converts only tool-reported paths proven below that exact tool snapshot into stable relative snapshot paths before analyzer replay, rejecting paths outside the tool snapshot
- **AND** all ten analyzers and the existing pip/Hatch/uv/Poetry acceptance corpus remain release requirements

#### Scenario: Managed tools receive private writable state

- **GIVEN** an admitted tool whose upstream runtime initializes a home, cache or configuration directory even when persistent caching is disabled
- **WHEN** the broker launches its managed worker against an immutable project snapshot
- **THEN** the trusted adapter binds the process temporary directory, home, cache, configuration and tool-specific cache locations below the invocation's private temporary root
- **AND** no tool may create state in the project snapshot, capsule cache or developer home directory
- **AND** before each subsequent broker request the controller rejects indirection or special files in that state and seals admitted directories and regular files to owner-only modes
- **AND** the profile may grant the fixed null device needed by Python tooling, without granting other device paths

#### Scenario: Controller-generated policy projections use canonical roots

- **WHEN** the trusted controller creates immutable pytest, coverage, Ruff, BasedPyright or Pylint policy projections below a host temporary-directory alias
- **THEN** it records and binds the canonical existing projection root before native admission
- **AND** native execution still rejects caller-provided noncanonical, symbolic-link or missing configuration roots

#### Scenario: Managed pytest evidence stays in private temporary storage

- **WHEN** the targeted pytest adapter requests observer, coverage-data, coverage-report and JUnit outputs
- **THEN** the trusted pytest tool plan materializes their exact logical paths below the invocation temporary root, including fixed path-bearing option values
- **AND** it rejects other embedded host paths or option forms instead of writing into the immutable project
- **AND** complete-inventory pytest receives the bounded immutable project snapshot needed to resolve its controller-approved selectors, while analyzers without project-runtime needs keep the narrower selected-file snapshot
- **AND** the trusted tool adapter normalizes only bounded integer and integer-enum process exits to broker status values
- **AND** the pytest domain imports the immutable project snapshot whether or not a separate project dependency runtime exists; sealed project site-packages remain conditional on a verified runtime
- **AND** pytest cache state is overridden to a fixed invocation-private temporary path rather than attempting the projected `/opt/specfact` path on the host

#### Scenario: Native pytest reports project-origin evidence honestly

- **GIVEN** a selected project test registers an exit handler that rewrites observer, JUnit and coverage files and forces a successful process exit
- **WHEN** the native pytest tool finishes its pytest call
- **THEN** the controller labels the result as project-origin pytest evidence, including when its ordinary reconciliation reports PASS
- **AND** it never labels observer, JUnit, coverage, or process-exit facts as independently protected from project Python
- **AND** missing, malformed, or mismatched files remain incomplete; a known forged-result fixture is recorded as an accepted limit of project-origin results, not as a security proof
- **AND** protected consumers reject project-origin results unless an explicit versioned compatibility change authorizes them

#### Scenario: Native pytest opt-out remains explicit

- **GIVEN** a Darwin ARM64 review with `no_tests` requested, an empty selection, or a Python-stub-only selection
- **WHEN** the native controller builds the analyzer report
- **THEN** targeted pytest remains required for a complete native review; a requested opt-out is UNKNOWN with an explicit diagnostic
- **AND** the review cannot report PASS by treating pytest as NOT_APPLICABLE or by skipping its worker
- **AND** an explicit `no_tests` request fails before member execution rather than silently running tests against the requested opt-out
- **AND** the Linux `no_tests` compatibility behavior is unchanged

#### Scenario: Semgrep uses its admitted single-process core interface

- **GIVEN** the pinned Osemgrep frontend initializes networking support by launching an external operating-system probe
- **WHEN** a sealed Semgrep analyzer requests a managed scan
- **THEN** the trusted adapter validates and merges only immutable rule packs from the verified capsule or controller-projected configuration, writes the pinned version's exact target schema below private temporary storage, and executes the verified Semgrep core image directly with one job and JSON output without progress dots
- **AND** it binds TLS initialization to the immutable verified capsule CA bundle so the core does not probe the host with `uname`
- **AND** it does not run the Osemgrep frontend, resolve executables through `PATH`, enable networking or permit a worker-created child process

#### Scenario: Worker changes task or thread exception ports

- **WHEN** a worker calls task/thread exception-port set or swap operations
- **THEN** kernel-enforced message restrictions reject all four operations before they can alter broker observation
- **AND** positive controls establish that the same requests succeed outside confinement
- **AND** an unavailable newer named hook may not cause that message restriction to be omitted on older supported systems

#### Scenario: Worker bypasses compatibility adapter

- **WHEN** project code calls fork, vfork, posix_spawn, direct process-creation syscalls or unauthorized tracing, signals or IPC
- **THEN** the OS denies the operation; unsupported behavior is incomplete evidence and never triggers host fallback

#### Scenario: Broker dies during startup or execution

- **WHEN** the broker or CLI dies before tracing, during confinement, across exec or while workers are running
- **THEN** no unconfined project code runs and independent observation finds no surviving governed worker after five seconds
- **AND** 100 repetitions of each lifecycle race are required before admission

#### Scenario: Bootstrap fails before the trace handshake

- **GIVEN** the signed fixed bootstrap cannot establish tracing, resource limits or confinement
- **WHEN** startup fails before the ready handshake
- **THEN** the broker reports only bounded numeric bootstrap phase/error diagnostics through its private startup channel, rejects the launch and applies the original cleanup bound
- **AND** a failure marker cannot satisfy readiness, trace ownership or executable admission; invalid/future marker phases are rejected and no raw worker output is published

#### Scenario: Sandbox compiler rejects the sealed native profile

- **WHEN** the fixed bootstrap cannot initialize its versioned Seatbelt profile
- **THEN** a bounded numeric compiler line diagnostic may accompany the failed startup marker
- **AND** raw compiler messages are not published and no failure record can satisfy readiness or image admission

#### Scenario: Fixed trusted bootstrap owns the pre-trace interval

- **GIVEN** an initial-distribution fixed bootstrap with default unblocked termination signals and no customer code or process-group changes before tracing
- **WHEN** its broker dies while it is suspended or running before tracing, trace-stopped, resumed, across exec or confined
- **THEN** independent birth/tracing observation and positive/negative controls establish five-second cleanup and invocation-job removal with 100 repetitions per tested transition; a launchd-only group claim does not approve arbitrary untraced workers or replace the remaining complete boundary and OS-matrix acceptance

#### Scenario: Confined workers resolve only explicitly granted roots

- **GIVEN** a capsule and invocation whose canonical paths traverse host directories outside both granted trees
- **WHEN** the fixed bootstrap applies confinement and starts an isolated Python analyzer, tool or project worker
- **THEN** the profile grants read-metadata access only to the bounded canonical ancestor chains needed to resolve the capsule and invocation roots, while project, output and temporary paths remain confined below the invocation root
- **AND** isolated Python runs with bytecode generation disabled by an interpreter flag, so execution cannot add unsigned cache entries even when environment variables are ignored

#### Scenario: Production workers enter the granted project root

- **GIVEN** the CLI process was started from a host directory outside the invocation and capsule grants
- **WHEN** the fixed bootstrap has established confinement and is ready to replace itself with an analyzer, tool or project worker
- **THEN** it changes its working directory to the verified project snapshot before replacement, so worker compatibility code never needs access to the CLI caller's host working directory
- **AND** inability to enter that snapshot fails the launch before project code executes

#### Scenario: Private control protocol preserves authority and terminal status

- **GIVEN** an invocation-scoped broker with a verified CLI peer and private capability
- **WHEN** a caller sends launch, wait, signal or cancellation requests, loses its connection or supplies malformed/foreign authority
- **THEN** bounded versioned requests affect only broker-assigned owned handles; incomplete frames and connection loss fail closed, terminal signals and accepted cancellation reasons are preserved, and independent lifecycle proof excludes competing timer/fallback cleanup

#### Scenario: Owned Mach signal exceptions complete without BSD wakeup dependence

- **GIVEN** a fixed signed worker whose exception endpoint is installed by the broker before spawn, then establishes PT_TRACE_ME and PT_SIGEXC before its initial stop
- **WHEN** initial stops, terminal signals, cancellation or broker death occur
- **THEN** bounded kernel-origin exception messages are admitted only for the registered direct child and its thread; only the initial SIGSTOP and an explicitly requested, independently verified one-use image handoff trap are suppressed, runtime signals retain their meaning, and terminal wait status remains distinct from exception replies
- **AND** exact ad-hoc hardened builds, five-second independent cleanup, 100 repetitions and the entire hosted matrix remain required; malformed or foreign exceptions fail closed and no BSD transport fallback establishes acceptance

#### Scenario: Production plan admission never activates fixture-only exception holds

- **GIVEN** a production request for any analyzer, managed tool or project-manager plan
- **WHEN** the broker admits the initial trace stop and the verified replacement image stop
- **THEN** it resumes the worker immediately and reports the admitted image as released
- **AND** lifecycle experiments that intentionally retain a kernel exception reply use a separate fixed maintainer fixture and cannot be selected by a production plan number

#### Scenario: Replacement image is verified before initialization

- **GIVEN** a fixed native bootstrap with active tracing and confinement and one broker-declared replacement identity
- **WHEN** the kernel stops its directly owned worker across exec
- **THEN** public dynamic Security validation must match the expected final signed replacement image before any target initializer; bootstrap traps, subsequent target traps and second replacements retain their real signal semantics
- **AND** the exact profile, shared source inputs and four signed fixture artifacts are bound to versioned evidence; cancellation, CLI connection loss and broker death at the verified exec stop and after entry require independent five-second observation and 100 repetitions each on every candidate OS
- **AND** this fixed-image subset does not admit CPython, analyzer adapters, project-manager workflows or customer installation

#### Scenario: Sealed analyzer executes with exact native inputs

- **GIVEN** the pinned native Semgrep core, reviewed rule packs and exact verified dylib closure
- **WHEN** the traced bootstrap runs clean and defective fixed fixtures under its versioned deny-default analyzer profile
- **THEN** both actual rule-pack members execute with expected outputs and exits while unauthorized host reads, descriptors, spawning, network and broker signals remain denied; snapshots bind the exercised policy to the receipt, which cannot approve the complete capsule from this subset

### Requirement: Initial-distribution managed boundary gate

The managed candidate SHALL prove its boundary using the exact initial distribution configuration: build-time ad-hoc signatures for our native components, verified upstream signatures where applicable and SpecFact-signed manifests covering final payload bytes. Hardened-runtime settings and narrow reviewed entitlements SHALL be recorded and tested with tracing and confinement. Missing Apple Developer ID credentials or notarization SHALL NOT block compilation, native execution, shipment or canonical GHCR publication. Invalid native signatures, corrupt payloads, failed confinement, missing boundary evidence, caller-asserted receipts and unit-test mocks SHALL NOT establish native acceptance. Optional Apple credential preflight SHALL NOT be an initial-release dependency. #460 SHALL block optional #488, never the reverse.

#### Scenario: Apple credentials are unavailable

- **WHEN** no Developer ID identity or notarization configuration is available
- **THEN** initial-distribution preparation and boundary testing may proceed without Apple credential probes
- **AND** this prerequisite result alone grants no boundary acceptance or production eligibility

#### Scenario: Initial-distribution boundary is incompatible

- **WHEN** native signatures, tracing, confinement, hardening or entitlements fail on the exact candidate
- **THEN** the candidate is rejected before production integration; neither unsigned execution nor process polling replaces the failed mechanism

#### Scenario: Integrity or proof is missing

- **WHEN** the payload is corrupt, its native signatures are invalid or required independent boundary evidence is absent
- **THEN** admission rejects the candidate even if Apple credentials are available

### Requirement: Distinct native trust evidence

Versioned inspection and evidence SHALL distinguish SpecFact manifest authentication, per-component native signing mode, notarization status and independent boundary verification. Ad-hoc signing SHALL NOT be reported as authenticated Apple publisher identity. Initial customer installation SHALL pass on a separate ARM64 Mac or clean independent macOS environment through the real CLI/GHCR route under an ordinary user with default protections; customers SHALL require no Apple credentials, local re-signing or build tools. Quarantine SHALL NOT be stripped, Gatekeeper SHALL NOT be disabled and security overrides SHALL NOT satisfy automatic installation acceptance.

#### Scenario: Initial native trust is inspected

- **WHEN** a verified initial-distribution runtime uses ad-hoc native signatures and has no notarization
- **THEN** inspection distinguishes these facts from manifest authentication and boundary verification without claiming Apple publisher trust

#### Scenario: Default-protection installation is blocked

- **WHEN** the actual independent-Mac CLI/GHCR route is blocked by quarantine or another host protection
- **THEN** installation acceptance fails with the concrete incompatibility rather than bypassing the protection or claiming support

### Requirement: Automatic native runtime acquisition

The existing review command SHALL automatically acquire a prebuilt signed Darwin ARM64 runtime on first use and show bounded progress at phase changes and coarse byte intervals, including the final byte count. It SHALL verify platform, ABI, policy/backend identity and payload digests, publish caches atomically and verify offline reuse. Customer execution SHALL require no Docker, VM, Homebrew, Xcode, administrator privilege or separately installed daemon.

#### Scenario: Controller bytecode does not change runtime composition

- **GIVEN** the same verified installed module source on cold and warm runs
- **WHEN** controller imports create or update `__pycache__`, `.pyc` or `.pyo` files excluded by module signing
- **THEN** those generated files are omitted from the copied capsule payload and its composition identity
- **AND** source, resource and executable changes still invalidate the verified payload; cached controller bytecode is never an analyzer input

#### Scenario: Ordinary review output identifies unavailable native delivery

- **GIVEN** native acquisition or verification leaves required analyzer evidence UNKNOWN
- **WHEN** a developer runs the ordinary review command without JSON output
- **THEN** the text report includes each distinct recorded analyzer diagnostic as literal text, including the unavailable ABI or acquisition cause
- **AND** repeated diagnostics are shown once, successful analyzer diagnostics are omitted, and JSON retains its existing evidence contract

#### Scenario: First invocation and offline reuse

- **WHEN** the ordinary command runs with an empty cache and later with a verified warm cache offline
- **THEN** it first downloads and verifies the native runtime and later reuses exactly the admitted payload without additional customer setup

#### Scenario: Native evidence reaches an older consumer

- **WHEN** a consumer does not support the versioned native execution contract
- **THEN** it rejects that evidence rather than assigning a Linux identity or protected authority
### Requirement: Prepare unfamiliar projects from discovered or caller-supplied setup
The native backend SHALL reuse portable project discovery and prepare dependencies on demand from the actual repository. Explicit project configuration SHALL precede verified active context and unambiguous metadata. No project identity SHALL require registration in a publisher acquisition catalog. Failed JSON inspection SHALL identify the diagnostic, candidate selections and required configuration without executing project code. Dependency/build hooks SHALL execute only in a confined project preparation domain with no acquisition credentials or direct network access.

#### Scenario: First review of an unfamiliar dependency-bearing project
- **GIVEN** a compatible project absent from every publisher project catalog
- **WHEN** the caller runs review with an unambiguous or explicit manager selection
- **THEN** the backend SHALL resolve and prepare its dependencies using authentic pinned manager semantics
- **AND** SHALL retain independently available findings and report incomplete evidence if required preparation is unsupported

#### Scenario: Native preparation materializes contained source aliases

- **GIVEN** an unfamiliar project contains valid internal file or directory aliases, including empty directories
- **WHEN** native preparation copies the source and verifies its discovered identity before any hook or acquisition
- **THEN** it materializes those aliases into ordinary private files and directories within the unchanged native source limits
- **AND** external aliases, excluded environments, cycles, path collisions, substitution during capture and changed source inputs remain rejected before execution
- **AND** source executable bits are retained, owner-read-only source directories are handled within the owned private copy, the original checkout is unchanged and the sealed dependency runtime remains indirection-free

#### Scenario: Native local pytest retains actual execution observations

- **GIVEN** the confined native pytest adapter executes project tests and produces observer, JUnit and coverage artifacts
- **WHEN** the worker completes replay and the ordinary command emits its versioned report
- **THEN** analyzer evidence retains the actual collected selectors, phase records, process exit and coverage data before temporary artifacts are removed
- **AND** the observations retain `project-origin-v1` provenance; they do not become protected PR evidence or override incomplete execution and genuine failed findings
- **AND** absent, substituted or malformed artifacts remain incomplete evidence under the existing limits

#### Scenario: Nested local environments do not block ordinary project review

- **GIVEN** an unfamiliar project contains an ignored local Python environment identified by `pyvenv.cfg`, under an arbitrary nested directory
- **WHEN** ordinary review captures worktree identity and the native source snapshot
- **THEN** both exclude that environment using the same rule as project preparation, without reading or executing its installed dependencies
- **AND** tracked or explicitly selected files inside an excluded environment remain incomplete inputs rather than silently disappearing
- **AND** ordinary source directories, mutations to analyzer inputs, and aliases to outside or excluded inputs retain their existing rejection and identity checks

#### Scenario: Caller resolves ambiguous discovery
- **GIVEN** repository metadata admits multiple project managers or environments
- **WHEN** the caller invokes runtime inspect with JSON output
- **THEN** the command SHALL return a structured diagnostic with candidates and required configuration fields
- **AND** explicit project configuration SHALL allow the caller to repeat inspection without modifying repository setup

#### Scenario: Deferred review uses independent signed controller code

- **GIVEN** a candidate change can modify every reviewer helper and module in its checkout
- **WHEN** the hosted job replaces an approved local capsule-only deferral
- **THEN** a separate blocking review runs on a fresh VM that has never executed candidate host code, and uses the installed authenticated published module through the trusted core interpreter in isolated Python mode, with the immutable candidate index as its subject
- **AND** isolated bootstrap and installed command loading occur outside the candidate checkout before entering the subject; candidate import paths, module roots, unsigned overrides and ambient credentials are absent from that review process
- **AND** the review retains changed-line enforcement, all required analyzers, bug-hunt activation and the existing 300-second bound
- **AND** unsupported published-reviewer policy or required incomplete evidence fails the job explicitly; a candidate helper returning success cannot approve it
- **AND** candidate runtime/corpus validation remains separately required and never establishes independent reviewer authority

#### Scenario: Independent review installs an available published baseline

- **GIVEN** the independent reviewer starts in a fresh ordinary-user environment before candidate execution
- **WHEN** it installs its explicitly pinned authenticated Code Review version through the main marketplace
- **THEN** the pinned version SHALL exist in the published registry and satisfy the pinned released core's compatibility range
- **AND** candidate manifests, helper scripts, module roots, unsigned overrides and dynamic candidate version selection SHALL NOT choose the reviewer
- **AND** an unavailable or incompatible published baseline SHALL fail the job rather than falling back to candidate source

#### Scenario: Hosted failure exposes bounded public finding locations

- **WHEN** candidate or independently installed review fails in the public repository
- **THEN** hosted diagnostics SHALL expose at most 200 finding locations bound to tracked public paths with integer lines and declared severities
- **AND** diagnostics MAY include only fixed public analyzer/category/rule identities and fixed failure classifications; independent review SHALL use trusted inline projection, never candidate host scripts
- **AND** raw findings, messages, private absolute paths, receipts and tool logs SHALL remain private
- **AND** the diagnostic step SHALL preserve the review failure exit code
- **AND** incomplete execution findings SHALL precede ordinary findings within the same 200-location limit
- **AND** a trusted independent analysis timeout or missing report SHALL expose only a fixed public status while retaining the original 300-second analysis budget
- **AND** structured Semgrep failures MAY expose at most three recognized public error variant tags from bounded JSON details; unknown tags, variant payloads, raw messages and source excerpts SHALL remain private
- **AND** the staged helper preserves the distinct analysis-timeout exit124 after the unchanged300-second deadline, so missing-report diagnostics cannot conceal the timeout; every timeout remains a blocking failure
- **AND** capsule review SHALL reuse the existing progress callback before each analyzer check; timeout diagnostics MAY identify only the last recognized fixed analyzer from a bounded stderr tail, without copying raw tool output or claiming successful execution

#### Scenario: Staged review activates bug-hunt

- **WHEN** the pre-commit helper builds a staged review command
- **THEN** it SHALL activate bug-hunt for the conditional bug analyzer and contract budgets
- **AND** changed-line enforcement, JSON evidence, explicit project configuration and the existing 300-second analysis timeout SHALL remain unchanged

#### Scenario: Explicit matching tests resolve ambiguous source mapping

- **GIVEN** partial review discovers multiple conventional tests matching a source filename
- **WHEN** the caller supplies at least one of those matching tests explicitly
- **THEN** test selection SHALL use the supplied matching tests while retaining other explicit tests and uniquely inferred tests
- **AND** ambiguity without an explicit matching test SHALL remain actionable incomplete evidence
- **AND** source/test ordering SHALL NOT change the selected inventory

#### Scenario: Hosted review selects its declared project environment

- **WHEN** the deferred review caller reviews a repository with multiple Hatch environments
- **THEN** the caller supplies an explicit project-config selecting the declared default environment
- **AND** the pre-commit helper forwards the selection to the existing native review command without changing project discovery rules
- **AND** unsuccessful preparation or analyzer execution still fails the hosted gate.

#### Scenario: Prepare both immutable index runtimes before bounded analysis

- **WHEN** a caller selects runtime prepare with index scope
- **THEN** preparation captures the same immutable base and staged snapshots used by review and seals each independently bound environment
- **AND** preparation cleans snapshots and exposes only local-build provenance without granting protected PR authority
- **AND** a captured index without governed Python impact returns explicit NOT_APPLICABLE with no prepared runtimes or capsule acquisition
- **AND** hosted cold acquisition and preparation have a separate bounded provisioning phase while the review helper retains its existing 300-second analysis timeout


#### Scenario: Pinned BasedPyright primary configuration precedence

- **GIVEN** a project containing both pyrightconfig.json and pyproject.toml
- **WHEN** the pinned 1.39.10 policy loader binds analyzer inputs
- **THEN** the JSON primary takes precedence as defined upstream, its complete bounded reference graph is sealed, and malformed or unsafe selected JSON remains incomplete evidence without TOML fallback
- **AND** ignored TOML cannot suppress governed findings; projection and anti-suppression checks remain mandatory

#### Scenario: Full native pytest uses normal project discovery

- **WHEN** full native review selects an empty positional test inventory for normal pytest discovery
- **THEN** the controller still binds the projected pytest and coverage policies, marks complete inventory and executes project-origin-v1 tests without inventing selectors
- **AND** a failed selection or unsupported policy remains UNKNOWN
- **AND** native project-origin full discovery reconciles nonempty observer/JUnit outcomes and strict production coverage; protected complete inventories still reject absent selectors
- **AND** production modules collected as doctests retain the production coverage threshold

#### Scenario: Default contract discovery preserves production inputs

- **WHEN** testpaths is absent or dot, including a project with no test files
- **THEN** contracts receive a valid versioned inventory of actual test files, excluding only those files from CrossHair while retaining production sources
- **AND** empty test inventory does not exclude the entire project or accept path escapes
- **AND** the native v2 inventory is a bounded sealed configuration file rather than one launch argument per test file; projects with 64 or more tests retain the existing worker argument-count limit

#### Scenario: Native integration changes schedule ARM64 checks

- **WHEN** a file in the runtime integration package changes
- **THEN** the native matrix workflow is scheduled even when the basename does not start with native_

#### Scenario: Native source capture preserves ordinary packages named venv

- **WHEN** a project contains a regular Python source package named venv without a pyvenv.cfg marker
- **THEN** native snapshot capture and worktree support identity retain its actual source bytes
- **AND** real local environments still remain excluded by their marker, and tracked/selected environment inputs remain rejected

#### Scenario: Distributed native pytest retains actually observed selectors

- **WHEN** project pytest plugins provide actual test phase records without coordinator collection records
- **THEN** native local execution observations retain the node identifiers observed in setup, call or teardown as collected selectors
- **AND** an empty observer remains empty; no declared or requested but unobserved selectors may be invented

#### Scenario: Native generated wheel modules preserve bound project source imports

- **WHEN** a real built root wheel includes a generated module absent from the source checkout alongside byte-identical source modules
- **THEN** native preparation retains source roots proven by unambiguous matching source bytes only when generated modules remain reachable through a sealed project-runtime overlay in private analyzer snapshots
- **AND** the overlay contains only missing modules from the actual built root wheel, never overwrites customer source, and is bound by the project runtime inventory and identity
- **AND** existing source modules with differing wheel bytes or ambiguous source matches still reject automatic root inference; no path is inferred only from its name
- **AND** source matching indexes exact package-path suffixes with a bounded index construction budget; shared short path tails cannot trigger unbounded candidate scans

#### Scenario: Preserved Linux analyzer parses reviewed test callbacks

- **GIVEN** a native-runtime correction also touches the established command tests
- **WHEN** the preserved Linux Semgrep1.144.0 scans those complete Python inputs
- **THEN** test callbacks use equivalent supported syntax while retaining keyword-only invocation contracts and all existing assertions
- **AND** structured parser failures remain incomplete evidence rather than being ignored, skipped or relabeled as successful execution

### Requirement: Equivalent execution on supported physical machines and full virtual machines
Support SHALL depend on guest OS/build, CPU architecture, Python ABI and required kernel capabilities. A matching-architecture full VM SHALL be eligible for the same acceptance as a physical machine. VM detection SHALL NOT reject an otherwise supported environment or weaken isolation. Full-system CPU emulation SHALL be recorded as supplemental evidence; translated user-mode binaries SHALL NOT establish native acceptance for their translated architecture. Windows and Linux ARM64 remain follow-ups; this delivery covers macOS ARM64 and Linux x86-64.

#### Scenario: Clean installation in a matching-architecture guest
- **GIVEN** an ordinary user in a clean supported full VM with default protections
- **WHEN** the final capsule is acquired through the documented installation route
- **THEN** cold acquisition, offline reuse, analysis, integrity and lifecycle acceptance SHALL run without publisher keys or host development tools
- **AND** evidence SHALL record guest OS/kernel build, architecture, ABI, artifact identity and configured virtualization mode

### Requirement: CI-only native artifact assembly

Native build and test jobs SHALL emit deterministic final archive and canonical manifest bytes without publisher signing authority. Only separate protected CI/CD jobs running reviewed pinned code SHALL authenticate accepted manifests. Unsigned outputs SHALL NOT populate the customer catalog or establish production eligibility.

#### Scenario: Build final archive bytes without manifest signing authority

- **GIVEN** a complete verified native runtime root and no publisher key
- **WHEN** the maintainer or read-only build job selects unsigned assembly
- **THEN** the builder emits the same deterministic archive and canonical manifest as the signed path, without calling a signer or creating a signature sidecar
- **AND** the summary declares manifest authentication false and production eligibility false; only a separate protected CI signing step can authenticate the manifest

#### Scenario: Native standard-library source remains available for static inference

- **WHEN** the relocated native CPython closure supplies frozen or ZIP-loaded standard-library modules to Pylint and Astroid
- **THEN** the same authenticated bounded standard-library source bytes also exist at their relocated filesystem paths, including `_collections_abc.py`, `collections/abc.py`, and dataclass dependencies
- **AND** no host interpreter, site-packages, source symlink, or unrecorded fallback supplies those files


### Requirement: Protected native release and authenticated catalog

Native release tooling SHALL validate the exact deterministic archive, native
signing metadata and supported-platform acceptance before protected CI signs
the unchanged manifest. Signing SHALL execute reviewed protected workflow code
without executing candidate content or exposing keys to build/test jobs. Catalog
resources SHALL bind the authenticated manifest and immutable anonymous GHCR
blob using the existing consumer format. Human promotion remains separate.

#### Scenario: Candidate code cannot control signing authority

- **GIVEN** an unsigned artifact and its exact supported-matrix acceptance
- **WHEN** protected CI signs it
- **THEN** branch/workflow/source identity and all required evidence are checked before key access; PR, unprotected, substituted, incomplete or stale inputs fail without signing or publication

#### Scenario: Signed catalog round-trip preserves final bytes

- **GIVEN** accepted cp311/cp312/cp313 archives and CI-authenticated manifests
- **WHEN** catalog preparation runs
- **THEN** each entry contains only matching manifest/signature/public-key resources and the dedicated immutable GHCR archive digest/size; altered archives, foreign keys, duplicate ABI inputs and partial output are rejected

### Requirement: Initial ad-hoc loader and installation acceptance

The initial ARM64 distribution SHALL use verified ad-hoc hardened native images
and SpecFact-authenticated manifests without Apple membership. Only CPython and
Semgrep Core may carry disable-library-validation. Every other native image must
have empty entitlements. A normal first-run trust warning MAY be acknowledged
and recorded; system protections and quarantine SHALL remain enabled.

#### Scenario: Loader entitlement substitution fails before release

- **GIVEN** final archive signing metadata
- **WHEN** a control component, unrelated tool or library gains an entitlement or a required loader loses its exact entitlement
- **THEN** release validation rejects the artifact before signing or catalog creation

#### Scenario: Independent customer acquires and reuses the capsule

- **GIVEN** a clean independent supported ARM64 environment and the signed module installed through the ordinary route
- **WHEN** review runs on a dependency-bearing project cold and then offline
- **THEN** the packaged catalog and standard anonymous GHCR client acquire and verify the exact final archive, all ten required analyzers execute, actual tests/plugins/coverage/native extensions are observed, and verified caches are reused without a local artifact override, development link, unsigned override, security disablement or customer signing
