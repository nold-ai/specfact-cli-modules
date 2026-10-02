# Specification: review-native-platform-execution

## Scope revision — 2026-09-30

Owner-approved macOS ARM64 first delivery. This replaces the prior cross-platform/C15 prerequisite scope; deferred platforms remain unsupported by this change. The owner-approved managed-process revision of 2026-10-02 supersedes unrestricted subprocess compatibility. Production remains gated on signed feasibility.

## ADDED Requirements

### Requirement: Native local execution

Code Review SHALL add a dedicated macOS ARM64 capsule while preserving Linux x86-64 execution. The ordinary review and runtime inspect/prepare commands SHALL select the approved platform backend automatically. CPython 3.11–3.13 is the candidate ABI matrix; only tested macOS versions and native ARM64 runtime closures may be published. Windows, Intel macOS and Linux ARM64 are deferred, not acceptance obligations of this delivery.

#### Scenario: Agent invokes the native CLI

- **GIVEN** a signed supported macOS ARM64 installation
- **WHEN** an ordinary user runs review or runtime inspect/prepare
- **THEN** the selected runtime executes natively without sudo, Docker, WSL, a VM, Rosetta or CPU emulation; diagnostics and reports identify the actual OS, architecture, ABI and backend

#### Scenario: Architecture is not silently substituted

- **GIVEN** a required interpreter, executable or library lacks a compatible ARM64 slice or the host OS is unvalidated
- **WHEN** runtime preparation or execution is requested
- **THEN** execution fails with an actionable unsupported diagnostic; no Homebrew, emulated or development-host fallback satisfies capsule acceptance

### Requirement: Native isolation capability evidence

Production backend approval SHALL follow harmless native feasibility tests of the release-signed managed broker/bootstrap against the capability contract. Earlier Seatbelt, App Sandbox and XPC experiments remain historical evidence; they are not alternate admission routes. The managed candidate is not preapproved. Mandatory boundaries SHALL cover filesystem reads/writes, network and IPC access, inherited descriptors, startup/load-path integrity, resource limits and complete child-process lifecycle. Exact mechanisms, OS support and numeric limits SHALL be frozen from measured results before production implementation.

#### Scenario: Isolation and cleanup are proven

- **GIVEN** a candidate helper and independently observable allow/deny fixtures
- **WHEN** tests exercise authorized reads/writes and prohibited host reads/writes, outbound and listening network operations, inherited descriptors and child processes
- **THEN** allowed operations succeed and denied operations fail for the intended policy reason; helper startup or parser failure is not successful confinement evidence

#### Scenario: Required capability is unavailable

- **GIVEN** a required isolation capability or analyzer is missing, incompatible or unverifiable
- **WHEN** launch readiness is evaluated
- **THEN** the runtime rejects analyzer launch and reports incomplete evidence under the released status/exit contract without weakening isolation

#### Scenario: Cancellation and descendants are bounded

- **GIVEN** a managed worker requests child execution or attempts forbidden direct creation, session changes or process-group escape
- **WHEN** timeout, user cancellation or controller failure occurs
- **THEN** all governed workers terminate within five seconds; fixtures independently check survivors and resource ceilings rather than treating killpg alone as proof

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

#### Scenario: OS dependent project tests

- **GIVEN** a project intentionally behaves differently on macOS and Linux
- **WHEN** its native test slice runs
- **THEN** reports preserve the actual platform and outcomes without forcing cross-platform equality or relabeling genuine failures

#### Scenario: Older protected consumer receives native evidence

- **GIVEN** a consumer has not approved the native report/runtime contract
- **WHEN** it receives macOS evidence
- **THEN** it rejects unsupported evidence explicitly rather than interpreting it as historical Linux or protected PR assurance

### Requirement: Verified provisioning and offline reuse

Module-shipped files SHALL retain full-module signature/checksum verification. External native runtimes SHALL have an approved signed manifest binding artifact and installed-payload digests, OS, architecture, ABI, complete dependency closure, released policy identity and backend/profile version. Cache identity SHALL include those bindings. Provisioning, extraction and each launch including offline reuse SHALL verify the selected payload and admission policy, and prevent substitution between verification and use.

#### Scenario: Cached native runtime

- **GIVEN** a complete approved cache for the selected OS, ABI and policy
- **WHEN** review runs offline
- **THEN** it revalidates the payload and uses only the bound runtime while recording its identity

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

### Requirement: Native project runtime preparation

The macOS backend SHALL carry forward pip/pip-tools, Hatch, uv and Poetry discovery, source selection, pytest plugins and coverage from #473. Acquisition, build hooks, preparation and analysis SHALL each have explicit trust, filesystem, process and network boundaries. Mach-O/dyld dependency handling SHALL replace Linux ELF assumptions for macOS. The trusted control domain SHALL remain separate from project code and extensions.

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

### Requirement: Signed customer release acceptance

Support SHALL be claimed only after a canonical signed publication passes fresh ordinary-user installation on every advertised macOS/ABI combination and Linux regression acceptance. Distribution SHALL verify applicable Apple code signing, notarization, quarantine and third-party library loading through the real install route. Candidate/source-tree results SHALL NOT substitute for public release evidence.

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
- **THEN** applicable signing/notarization/quarantine checks and the approved library-loading policy pass without disabling host protections; final payload hashes match the shipped signed manifest

#### Scenario: Linux regression and rollback

- **GIVEN** a macOS candidate or publication is evaluated
- **WHEN** the existing Linux customer matrix and cross-platform fixtures run
- **THEN** Linux remains supported with historical identities intact; a faulty macOS publication can be withdrawn or superseded without disabling Linux or deleting evidence

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
- **AND** all ten analyzers and the existing pip/Hatch/uv/Poetry acceptance corpus remain release requirements

#### Scenario: Worker bypasses compatibility adapter

- **WHEN** project code calls fork, vfork, posix_spawn, direct process-creation syscalls or unauthorized tracing, signals or IPC
- **THEN** the OS denies the operation; unsupported behavior is incomplete evidence and never triggers host fallback

#### Scenario: Broker dies during startup or execution

- **WHEN** the broker or CLI dies before tracing, during confinement, across exec or while workers are running
- **THEN** no unconfined project code runs and independent observation finds no surviving governed worker after five seconds
- **AND** 100 repetitions of each lifecycle race are required before admission

### Requirement: Release-signed managed boundary gate

The managed candidate SHALL require a Developer ID Application identity, hardened runtime, approved entitlement set and successful notarization before native boundary execution is treated as acceptance. Missing identity or credentials SHALL fail preflight before candidate execution. Ad-hoc signing, skipped signature checks, caller-asserted receipts and unit-test mocks SHALL NOT establish native acceptance.

#### Scenario: Signing prerequisites are unavailable

- **WHEN** no matching Developer ID identity or notarization configuration is available
- **THEN** the gate returns a specific blocked diagnostic without compiling or executing a substitute candidate or granting production eligibility

#### Scenario: Signed boundary is incompatible

- **WHEN** tracing, confinement, entitlements or notarization fails on the release candidate
- **THEN** the candidate is rejected before production integration; neither unsigned execution nor process polling replaces the failed mechanism

### Requirement: Automatic native runtime acquisition

The existing review command SHALL automatically acquire a prebuilt signed Darwin ARM64 runtime on first use and show progress. It SHALL verify platform, ABI, policy/backend identity and payload digests, publish caches atomically and verify offline reuse. Customer execution SHALL require no Docker, VM, Homebrew, Xcode, administrator privilege or separately installed daemon.

#### Scenario: First invocation and offline reuse

- **WHEN** the ordinary command runs with an empty cache and later with a verified warm cache offline
- **THEN** it first downloads and verifies the native runtime and later reuses exactly the admitted payload without additional customer setup

#### Scenario: Native evidence reaches an older consumer

- **WHEN** a consumer does not support the versioned native execution contract
- **THEN** it rejects that evidence rather than assigning a Linux identity or protected authority
