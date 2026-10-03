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
