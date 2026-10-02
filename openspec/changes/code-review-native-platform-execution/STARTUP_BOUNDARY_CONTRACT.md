# Startup ownership candidate acceptance

Recorded 2026-10-02 (Europe/Berlin). This is a bounded experiment, not production
backend admission. Paid Apple identity is not required.

An ephemeral ordinary-user launchd job is the candidate owner of fixed trusted
bootstrap processes from creation until tracing is established. No customer code
may run in this interval or change the job process group. After admission,
confinement must prohibit direct descendants and tracing must own worker lifetime.
The system service is existing launchd; no installed daemon or LaunchAgent is
permitted. The experiment must boot out its unique invocation job on every exit.

The proof uses ARM64, build-time ad-hoc signatures and hardened runtime. Exact
payload digests and signing details must be recorded. It must not request Apple
credentials, strip quarantine or present a local build as customer-install proof.

A suspended child created by the broker must disappear within five seconds of
broker SIGKILL, without observer-assisted cleanup during measurement. An
independent libproc observer identifies the PID by birth timestamp; observation
errors fail the test. A negative control with AbandonProcessGroup enabled must
remain observable beyond the same deadline. Only after measurement may the
harness kill the identity-checked fixture. A normal completion control must return
expected output and exit status. Repeat each admitted race 100 times before any
positive lifecycle claim. Receipts always leave production approval false.

A passing startup subset does not prove the full boundary, descriptor/IPC grants,
resource limits, CLI loss, all ten analyzers, project managers or independent Mac
installation. Failure of launchd cleanup rejects this candidate; keep the mandatory
startup race instead of weakening acceptance.

## Fixed bootstrap versus admitted workers

The fixed pre-trace bootstrap must retain default, unblocked termination signals
and the launchd process group. The running pre-trace acceptance fixture obeys that
contract. A deliberate pre-trace SIGTERM-ignoring fixture is a rejected control,
not an allowed worker: launchd group cleanup alone was observed insufficient.
Suspended cleanup is necessary but may also involve kernel orphan-group handling;
it cannot by itself attribute ownership to launchd. Use a running, default-signal
negative control with AbandonProcessGroup enabled to establish that distinction.

After PT_TRACE_ME and its broker-confirmed stop, admitted fixture code may ignore
SIGTERM and change sessions. Test broker death while trace-stopped, after resume,
and after executable replacement. The independent observer must confirm the
original broker parent and each expected group/session transition before killing
it. Native signing configuration is verified on every built binary; no tracing
exception is silently added to make the experiment pass.

## Native confinement subset

A fixed fixture establishes tracing, closes non-stdio descriptors and applies a
versioned deny-default Seatbelt profile before exercising benign probes. It must
prove a granted observation stream and rejected libc fork/vfork/posix_spawn,
direct ARM64 fork syscall, host-file read, network connect and signal to its
broker. Independent libproc flags must verify tracing before every post-trace
kill. A matching unsandboxed fixture must demonstrate successful benign process
creation and file/network access; parser/startup failures are not negative proof.
This minimal fixture policy is not an analyzer/project filesystem grant policy.

The direct raw vfork syscall (66) is retained as a separate unsandboxed availability
control. This physical host terminates it with SIGSYS; that is not Seatbelt denial.
The libc vfork entry point remains exercised and denied. XNU conditionally maps
raw vfork to nosys when CONFIG_VFORK is absent; compare actual release behavior on
each candidate OS instead of attributing an unavailable syscall to our policy.
Source inspected 2026-10-02: [Apple syscall table](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/syscalls.master#L115).

## Acceptance-harness race corrections

Cleanup signaling must use a real kernel audit token and pid version, not a
birth-check followed by numeric-PID kill. Read-only task-name rights may supply
that token; no task-control or debugger entitlement is admitted. Measurement
starts at native signal issuance; negative controls require five full seconds
following successful issuance. Delayed observer work cannot consume that window.
If a fixture fallback alarm could expire within the window, reject the trial.
Wait for the explicit broker identity record even if worker output arrives first.
Allow automatic job removal to settle within the remaining cleanup deadline.

## Traced signal semantics

Only the first verified tracing SIGSTOP and the expected single exec transition
are control stops. A runtime SIGTRAP after executable replacement must retain
its terminating signal instead of being suppressed. Add an actual native traced
exec/trap fixture alongside the startup controls; signal failure rejects proof.

## Exact exercised inputs

Capture policy bytes once for the complete suite and supply that snapshot to
every launch. Compile private native-source snapshots and retain their digests;
checkout edits during or after execution cannot relabel tested artifacts.
