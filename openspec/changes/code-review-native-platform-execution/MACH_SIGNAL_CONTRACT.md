# Owned Mach signal exception experiment

Status: experimental replacement for the control fixture BSD stop transport.
No production admission; startup and analyzer fixtures retain separate acceptance.

Current-head 78b58bca hosted run 37092073540 failed on all macOS 14, 15 and 26
workers during completion. Bounded waitpid reconciliation did not establish a
fix. The kernel cause is unproven. Retain these failures as historical evidence.

Install an invocation-private EXC_SOFTWARE endpoint with spawn attributes before
worker code runs. The fixed bootstrap establishes PT_TRACE_ME then PT_SIGEXC
before its initial stop. The broker remains the direct tracing parent; launchd
continues to own the pre-trace bootstrap interval. Generated SDK MIG decoding
must validate bounded messages and kernel sender provenance, registered task
identity and thread membership. No customer-selected task/thread rights enter
this interface. Initial SIGSTOP alone is suppressed; later signals are forwarded
using PT_THUPDATE before the exception reply. A deliberately held initial stop
must remain held until broker death. Terminal wait status is reaped separately,
never inferred from a reply. Malformed/foreign messages terminate the invocation.

The single broker loop services bounded queued exceptions and its existing
50 ms owned-child reconciliation interval. This interval is not a scheduler or
resource guarantee; cleanup still relies on the tracing parent-exit mechanism
and launchd pre-trace ownership, not PID enumeration or polling-based killing.

Capture the SDK definitions and generated server hashes alongside final signed
payload bytes. Build-time tools are maintainer inputs, not customer dependencies.
Require exact ad-hoc hardened signing without new entitlements, positive and
negative signal controls, five-second independent cleanup and 100 repetitions.
All macOS 14/15/26 CI suites and remaining #460 gates remain mandatory. Reject
this candidate if its intended signing/confinement configuration fails.

Sources inspected 2026-10-03: Apple XNU [signal handling](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c),
[ptrace](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/mach_process.c),
and [parent exit](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exit.c).
Published source is an implementation reference, not proof of a hosted OS build.

## Owned reply destination closes during cancellation

A worker can die after its held initial stop is resumed but before its kernel
RPC reply is sent. Recoverable failed owned reply sends SHALL destroy their unsent rights.
MACH_SEND_INVALID_DEST SHALL be benign for this already-validated owned reply;
timeout/interrupted sends SHALL fail closed after disposal. Other send errors
SHALL fail closed through process cleanup without attempting to destroy rights
that the kernel may already have partially consumed. This applies to both
held and ordinary validated replies. A disappeared reply destination SHALL NOT
create terminal evidence: only waitpid establishes exit/signal status.
Signed safe-system-operation mocks SHALL prove successful sends, dead
destinations and fail-closed non-destination errors without touching host PIDs
or Mach rights. Actual signed lifecycle and held-stop cancellation acceptance
remain required.

Cancellation of a worker held at the initial Mach exception SHALL be a separate
100-repetition lifecycle case, cancel-held-stop, using independent birth/tracing
observation and the unchanged five-second bound. It SHALL preserve SIGKILL and
the accepted cancel reason; it is not covered merely by cancelling a running
worker or killing the broker at a held stop.
