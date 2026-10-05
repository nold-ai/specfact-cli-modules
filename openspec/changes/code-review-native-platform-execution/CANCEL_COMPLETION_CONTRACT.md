# Owned-child completion reconciliation

Status: bounded native experiment; no production admission. This supplements
CONTROL_BOUNDARY_CONTRACT.md without changing kernel trace ownership or cleanup.

A directly owned, unreaped worker can enter a trace stop or exit after the
broker's last nonblocking wait-status read. Completion MUST NOT depend solely
on delivery of a signal-handler pipe byte or worker-output readiness. While
any registered child is unreaped, the event loop MUST request at most a
50 millisecond select sleep before reconciling its own children with waitpid.
It MUST preserve earlier worker, partial-frame, connection and session deadlines.
Once all registered children are reaped, it MUST retain ordinary event/deadline
waiting rather than introduce idle polling. This is a requested wait interval,
not a hard scheduler or resource guarantee.

A deterministic signed native fixture MUST exercise the actual event loop with
safe system-operation mocks. Suppress SIGCHLD/pipe readiness, expose a traced
SIGKILL stop followed by terminal status, and close the worker output. The
pending wait MUST complete with its recorded cancellation reason and signal.
Test active, intentionally held-stop, reaped and empty registries separately.
Runtime signal forwarding, bounds and unexpected wait failures remain unchanged.

This reconciliation observes only the eight registered direct children. It
MUST NOT enumerate processes, select host PIDs, send additional cleanup signals,
retry failed trials, or convert measured survivors into passing evidence.
Broker/CLI death MUST still rely on the kernel/launchd ownership boundary and
independent five-second absence proof, with 100 repetitions of every race.

Hosted head 1a0b68d9 passed all startup races on macOS 14, 15 and 26; macOS 15
also passed all 1,219 control records. macOS 14/26 failed cancel/request-wait
after 69/29 full lifecycle rounds. Their last snapshots reported wait accepted
and pending, worker not reaped and output not closed. These are historical
observations; they do not establish notification loss or a kernel root cause.
The new fixture proves the bounded completion contract separately, and fresh
hosted acceptance is still required.

Apple XNU's tracing signal path reports a stop before awaiting debugger release;
its ptrace continuation and parent-exit paths are distinct. Source inspection
informs this experiment but does not prove behavior of every released OS build.
Sources accessed 2026-10-03:

- [XNU signal path](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c)
- [XNU ptrace continuation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/mach_process.c)
- [XNU parent exit](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_exit.c)
