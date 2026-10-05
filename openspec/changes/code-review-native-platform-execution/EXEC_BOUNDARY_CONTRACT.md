# Owned native executable handoff

Status: owner-authorized boundary milestone within #460, not production admission.
Recorded 2026-10-03 (Europe/Berlin). The current startup/control checkpoint at
bd173218 passes the ARM64 macOS 14/15/26 fixtures and actual current-head review.
This next slice addresses the missing bootstrap-to-executable transition.

## Failing witness

The unchanged Mach broker ran a fixed signed C worker that established tracing,
confined itself, then replaced its image with a fixed signed C target. Positive
worker probes and an ordinary target execution succeeded. The confined handoff
returned actual wait status signal 5, exit -1, traced=true, reason completed;
control-denials-ok/control-ready were present, target-entry was absent. The
worker disappeared and owned job cleanup completed within five seconds.
All four binaries were ad-hoc hardened with empty entitlements. Private receipt:
/private/tmp/mach-exec-witness-20261003-a/safe-receipt.json. This is a failing
physical-host witness, not a customer-runtime result or hosted acceptance.

Apple XNU preserves traced/Mach signal state and posts SIGTRAP on traced exec.
The Mach signal payload alone cannot identify an exec trap. The existing broker
correctly preserves runtime traps; extending it must not swallow a genuine trap.
Source inspected 2026-10-03: [Apple exec implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exec.c).
Published source does not prove every candidate OS build.

## One-use image-bound transition

Only explicitly selected fixed exec fixtures may replace their bootstrap image.
The broker SHALL bind each launch to the final signed target CDHash requirement.
Before permitting target entry it SHALL validate the kernel-origin exception,
direct owned unreaped PID/task/thread, SIGTRAP and the current dynamic code
identity against that requirement. Use public Security framework dynamic code
APIs; checking a pathname or static file alone cannot establish the running image.
A recognized still-running bootstrap image SHALL retain genuine signal behavior.
An invalid/unrecognized image or failed identity lookup SHALL fail closed.
Only one validated replacement stop may be suppressed. Later traps SHALL retain
actual signal delivery, including a second attempted replacement.

The worker SHALL establish tracing and confinement before exec. The target SHALL
inherit that confinement and direct tracing-parent ownership. Exec permission is
limited to the fixed signed target, with narrow Apple system-library read/map
roots and exact ancestor metadata. Do not grant all of /System: data-volume
aliases must not become host-data grants. Existing non-exec fixtures retain their
original deny-default profile. No user executable, grant, environment or PID is
added to the request protocol.

Native positive controls SHALL verify target initializer timing after broker
admission, output/exit=37 and inherited native fork/read/network denial. Negatives
SHALL cover a genuine pre-exec trap, a genuine post-exec trap, failed exec,
wrong/modified target identity and a second replacement. Missing identity or
loader evidence cannot be converted into successful handoff.

## Lifecycle and exact evidence

A separate fixed fixture SHALL hold the validated replacement stop before target
initializers. Cancellation and broker death at that stop, and cancellation,
client EOF and broker death after target entry, require independent kernel birth,
parent/group/tracing observation and absence within the existing five-second
bound. Preserve actual wait status for completed/cancelled workers. No observer
kill or bootstrap retry may rescue a failed measurement. Run 100 repetitions
per added lifecycle case on the physical Mac and each candidate hosted OS.
Production plan numbers SHALL never select this retained-reply behavior. After
the broker validates a production worker's replacement image it SHALL release
the exception reply immediately; the dedicated maintainer fixture remains the
only route for held-stop lifecycle evidence.

After confinement is active and before replacing itself, the bootstrap SHALL
enter the already validated project snapshot. This prevents inherited CLI host
working directories from becoming implicit filesystem grants and gives managed
tool adapters a stable caller directory for temporary directory changes. A
failed `chdir` SHALL terminate startup before analyzer, tool or project code.
Managed tool workers SHALL create bounded owner-only process-temporary, home,
cache and configuration roots below the granted invocation temporary directory.
Their environment SHALL select those roots, including `TMPDIR` and Ruff's cache override, so
upstream initialization cannot write to the immutable project or the user's
real home even when a tool was requested with its own no-cache option.
The initial profile MAY admit read/write access to the literal `/dev/null`
device required by sealed Python analyzers; no device subtree is admitted.
Semgrep SHALL use the pinned core's direct `-rules`/`-targets` interface
with `-json_nodots -j 1`. The trusted adapter SHALL accept immutable rule packs only from the
verified capsule or controller-projected configuration, derive both files from
the closed managed request, and SHALL not execute Osemgrep's network-initializing
frontend. The managed environment SHALL bind `SSL_CERT_FILE` to the immutable
verified capsule CA bundle so core startup performs no external `uname` probe.

Capture target source/final signed payload, exact helper/profile bytes and
Security requirement identities alongside existing SDK/MIG provenance. Receipt
and hosted gates SHALL require the target and all new protocol/lifecycle cases;
old three-artifact or incomplete receipts cannot approve the new handoff.
Maintain production_approved=false and signed_boundary_verified=false.
This fixed-target proof does not admit CPython, project imports or manager hooks.
All ten analyzers, managed adapters, hard-resource/escape proof, acquisition/cache,
customer installation and Linux acceptance remain required for delivery.

Loader-specific literal grant: the macOS 27 pilot aborted in libignition before
initialization with metadata-only root access. An exact file-read grant for `/`
permits its root-directory openat setup without granting descendants. The same
grant already exists in the sealed analyzer experiment. No broader `/System` or
Data-volume alias is admitted. Fresh native positive and host-read denial proof
are mandatory; the crash stack alone does not establish a syscall root cause.

## Remaining admission proofs — owner-authorized completion

The full change continues beyond the reviewed fixed-image checkpoint. Every
successful exec lifecycle receipt SHALL retain the observed image-stop marker,
bound to the same kernel worker identity and the correct held/released state.
Missing, foreign or wrong-state markers SHALL reject acceptance.

A trusted fixture SHALL hold a direct bootstrap at its initial traced stop after
static verification. Atomic substitution of a different validly signed target
at the approved path followed by continuation SHALL encounter dynamic image
rejection before that image's initializer. Observe worker and job absence within
five seconds, before its competing timeout; repeat this race 100 times.

Native post-exec negative probes SHALL attempt task/thread software-exception
handler replacement, broker task-port acquisition, tracing detachment and direct
fork/vfork/spawn/syscall creation. A claimed denial requires real execution and
an ordinary successful positive control where the operation can succeed without
confinement. A kernel self-termination response to deny-attach is distinct from
a policy denial and cannot be reported as an errno denial. Failed API identity
lookup tests must exercise the real Security framework, never relabel a mocked
failure as native evidence. No production activation follows from subset proof.

### Native task/thread exception-port policy (2026-10-03)

Real task and thread `set_exception_ports` attempts installed a replacement
software-exception endpoint despite deny-default confinement. The explicit
`deny mach-task-exception-port-set` rule prevents both measured replacements
on the physical macOS 27.0.1 host. Acceptance must inspect the actual installed
ports, since success return codes alone cannot prove that an action changed.
Unconfined positive controls must install the endpoint with the same API.
Alternate swap/clear operations and advertised OS builds remain required;
no production admission follows from the two physical-host probes.

### Admission proof receipt extension

Control evidence SHALL include 100 actual post-verification signed-target
replacement trials in addition to the earlier lifecycle trials. Reject foreign
image identity before its constructor and observe actual bounded worker output
while the kernel exception is held. Require independent worker/job disappearance
inside five seconds and before the competing worker deadline. An empty fabricated
output field cannot establish constructor non-execution. Each foreign payload
must execute its constructor in the unconfined positive control.

The maintainer control-suite outer ceiling increases from 720 to 900 seconds
only to accommodate the added 100 image-race trials and native endpoint probes.
Worker timeouts, output limits, five-second cleanup, minimum repetition counts
and the 30-minute hosted job ceiling remain unchanged. Serial suites still stop
on the first failure. This changes acceptance workload, not a runtime budget.

### Trusted bootstrap verification before execution

The broker SHALL create the fixed bootstrap with
`POSIX_SPAWN_START_SUSPENDED`, validate the identity of that exact running
process against the pinned bootstrap requirement, confirm that its observation
pipe is still empty, and only then resume it. The native receipt SHALL retain a
bootstrap-identity marker before the tracing marker. A pathname signature check
alone cannot establish this property. Any identity lookup failure, foreign
identity, premature output, resume failure, or missing marker fails closed.

The resumed bootstrap remains trusted and must establish `PT_TRACE_ME` before
changing signal behavior, resource controls, confinement, or project-code
execution. This closes the static-verification-to-spawn pathname race without
claiming that a suspended process is already a confined worker.

The deny-default profile must permit canonical resolution of the authenticated
capsule and private invocation roots without granting their host parent trees.
The bootstrap therefore binds a bounded, deduplicated set of capsule and
invocation ancestors as metadata-only literals. Project, output and temporary
trees remain reachable only through their invocation grants. Python workers
must also use `-B`; `-I` ignores `PYTHONDONTWRITEBYTECODE`, so the environment
entry alone cannot prevent unsigned bytecode writes to a writable capsule.

Controller-created analyzer policy projections must be canonicalized after
creation and before they are added to the native request. This includes the
pytest and coverage files created below the macOS temporary-directory alias.
The admission side remains strict: caller-provided noncanonical, symbolic-link
or missing configuration roots are rejected rather than silently normalized.

The managed pytest plan owns observer, coverage-data, coverage-report and JUnit
artifacts below the invocation temporary root. Its trusted tool adapter may
materialize the two fixed embedded path forms `--cov-report=json:<logical>` and
`--junitxml=<logical>`; arbitrary embedded option paths remain inadmissible.
Complete-inventory pytest receives a bounded immutable copy of the project
snapshot so its controller-approved selectors are present. Its Python return
adapter accepts only bounded built-in integers or `IntEnum` values.
The immutable project root is always appended after sealed capsule tool paths
for pytest imports. Project `site-packages` is appended only when its verified
runtime descriptor and immutable tree are present.

Those temporary artifacts are transport, not authoritative evidence: the
pytest worker also executes project tests, plugins and native extensions, so
project code can write the files or any channel exposed to that process. A
separate trusted result owner must establish completion and outcome without
accepting a self-declared PASS from the project worker. In particular, moving
the same-process observer bytes into a pipe, socket or stdout frame does not
meet the non-impersonation contract; an abrupt zero exit without protected
completion remains UNKNOWN. Native pytest stays disabled at the analyzer
prelaunch guard until an adversarial physical proof of that design passes.

Control receipt schema v4 adds a mandatory `bootstrap-identity` protocol trial.
The strict consumer binds its exact PID to the corresponding wait result and
rejects missing, foreign, resumed or premature-output markers. Earlier control
receipt schemas cannot establish this startup property.
