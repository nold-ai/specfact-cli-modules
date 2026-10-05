# Native execution component contract

Public plan 28 is the fixed sealed uv acquisition worker. Private managed
Python children retain plan 27, which controller requests cannot select. uv
receives an exact native image requirement and a separately versioned launch
adapter. Its build/probe children inherit filesystem and resource grants but
receive no acquisition network permission.

Status: implementation candidate within #460. This contract does not admit a
production macOS capsule by itself.

## Artifact and request boundary

The Darwin ARM64 capsule SHALL contain a prebuilt `specfact-native-broker` and
`specfact-native-bootstrap`. Both binaries SHALL be ad-hoc signed with hardened
runtime at build time. Customer execution SHALL NOT invoke a compiler,
`codesign`, Xcode, Homebrew, Docker, or a host analyzer.

If a native Python tool entrypoint returns or raises during testing or embedding,
it SHALL restore the caller process environment, argument vector, import path
and working directory; a successful image replacement remains process-local.

The Python controller SHALL accept only a live verified native-capsule lease and
a versioned plan identifier from a closed allowlist. A request SHALL NOT contain
an executable path, host PID, sandbox profile, loader override, signing
requirement, or arbitrary command line. Unsupported plans produce actionable
`INCOMPLETE` evidence and never fall back to the host.

Before transport, the controller SHALL verify:

- native manifest and ad-hoc signature evidence on the lease;
- the lease path and every granted path without following symlinks;
- an owner-only invocation root, immutable capsule tree, read-only project
  snapshot, and owner-only output and temporary directories;
- output and temporary grants remain below the invocation root and are
  disjoint from the project snapshot and capsule;
- a closed environment-key allowlist with bounded UTF-8 values and no loader or
  Python path injection;
- named standard-stream descriptor grants only; and
- bounded timeout, output, address-space, file-size and open-file budgets.
  The file-size resource limit SHALL use the independent file budget; stream
  output remains broker-enforced and SHALL NOT lower the project file ceiling.

Validation SHALL return an immutable canonical request. It SHALL retain the
lease identity, exact plan version, normalized grants and resource policy.

## Broker/bootstrap lifecycle

The broker SHALL be invocation-scoped and created from the verified capsule.
Its private authenticated channel supports only launch, wait and cancel using
broker-assigned handles. The caller cannot select a PID. EOF from the controller
stops admission and terminates every admitted worker within five seconds.

The broker SHALL stop itself before reading a request. The controller SHALL
verify that exact stopped PID against the authenticated designated requirement,
recheck the lease-bound broker and verifier inodes, and only then resume it.

The broker SHALL require successful application of suspended and close-on-exec
spawn flags before spawning; failure SHALL abort without a worker launch. The
broker SHALL spawn only its fixed bootstrap suspended, verify the exact
running bootstrap image, and resume it only after verification. The bootstrap
closes every descriptor except the protocol-declared grants, establishes
`PT_TRACE_ME`, resource limits and the versioned Seatbelt profile, reports a
startup marker, and stops before replacing its image. The broker SHALL validate
the admitted final image at the traced executable-replacement stop before
allowing project code to run. A missing marker, identity mismatch, unexpected
stop, unadmitted image replacement, protocol error or controller loss fails
closed.

The bootstrap maps a plan identifier to a fixed capsule executable and argument
template. It does not accept an executable or host PATH lookup. Managed child
creation requested by an admitted worker must return to this broker; direct
`fork`, `vfork`, `posix_spawn`, task-port manipulation and external execution
services remain denied by the kernel profile.

Plan numbers are frozen as follows: 1 is the boundary self-test; 2 through 11
are the ten analyzer worker plans; 12 through 18 are Ruff, Radon, Semgrep,
BasedPyright, Pylint, CrossHair and pytest tool replay; 19 through 22 are
historical authenticated pip, Hatch, uv and Poetry import plans; and 23 through
26 are on-demand pip acquisition, offline installation, confined build hooks
and sealed wheel inspection. Plan 27 is reserved for broker-owned Python
children and cannot be selected by the controller. Analyzer plans invoke the fixed capsule
CPython module `specfact_code_review.run.native_worker` with exactly the capsule,
project, output and temporary roots. Tool and project plans use their fixed
modules and a plan-derived tool or manager name. No target or argument vector is
accepted over the wire. Direct Ruff, Semgrep Core and Node replacement images
require their own build-generated code requirement before release.

Worker stdout and stderr SHALL use separate owner-only, no-follow, exclusive
files under the validated output grant. The readiness marker uses a dedicated
descriptor. The broker enforces the combined output budget and authoritative
wait status; the controller reopens and verifies the bounded files after wait.

For the fixed pytest tool plan, observer, JUnit, coverage and exit facts are
project-origin results. The controller SHALL reconcile them with the selected
inventory and reject missing or inconsistent evidence. It SHALL label executed
native pytest evidence `project-origin-v1` in the analyzer and review scope.
This does not authenticate test outcomes against project Python: a test or
plugin can rewrite the files, emit a forged frame, or exit before pytest
finishes. The physical forged-result fixtures remain negative trust evidence.
Local native reviews may use project-origin results; protected range reviews
SHALL return UNKNOWN until their consumer contract explicitly admits this
versioned provenance. The managed worker sandbox and artifact-integrity gates
remain mandatory. This change alone does not admit customer publication.

## Evidence and present limit

Unit tests may use a fake broker transport only to prove controller validation
and state handling. Maintainer native tests may compile the checked-in C sources
and ad-hoc sign them, but raw receipts remain ignored.

Production admission additionally requires the final artifact builder to embed
the fixed Python worker, exact plan payloads and Seatbelt profile; verify the
signed broker/bootstrap/CPython images; and pass the complete native lifecycle,
escape, analyzer and project-corpus suites on every supported macOS build. Until
that evidence exists, this API reports `production_eligible=false` and the
component metadata remains `candidate`.

The earlier plan-1/initial-CPython milestone is historical. The current private
ARM64 candidate runs all ten analyzers on an independent pip project and a
source-only project; genuine cold pip preparation and verified offline reuse
also pass. The live build-hook proof exchanges child standard streams, verifies
exit codes, timeout and termination, and denies direct fork. These focused
results do not establish the complete OS/ABI, manager or customer-installation
matrix. Production flags remain false.

## Live managed children

Current candidate backend and profile identity is `managed-v3` /
`project-domains-v3`. It includes the private live worker channel, bounded
private Python prefix/alias selection and relocated interpreter metadata.
Earlier backend/profile identities must not be reused for this payload or
treated as evidence of these capabilities. Linux artifact identities remain unchanged.

Workers receive only private inherited request/reply pipes on descriptors 5 and
6. A bounded, versioned frame carries a closed binary property-list launch
document or an operation on a broker-assigned child handle. The broker validates
the exact Python program identity, arguments, cwd, environment and import paths
against the registered parent's existing grants. It never accepts a host PID,
loader override, arbitrary executable or broader grant from a worker.

The broker creates every child itself through the same suspended bootstrap,
signature verification, tracing and confinement handshake. A child is a direct
OS child of the broker and a logical child of its requesting worker. Its private
streams, polling, stdin, signals and release operations remain broker-owned.
Only the requesting parent may operate on its handles. Parent exit terminates
its logical children; controller loss terminates the whole invocation.
Request/reply processing is nonblocking and bounded so partial frames cannot
prevent controller-loss observation or another worker's progress.

The child bootstrap retains its private configuration pipe only until trusted
Python startup consumes it, then closes it before any project code. Python
subprocess interception supplies compatibility; kernel direct-process denial
remains the independent security boundary.
