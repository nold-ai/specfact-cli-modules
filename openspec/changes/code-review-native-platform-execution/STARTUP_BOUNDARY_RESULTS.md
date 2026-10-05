# Native startup and confinement checkpoint

Final rerun measured 2026-10-03 (Europe/Berlin), physical Mac17,9, native ARM64,
macOS 27.0.1 build 26A434. This is a local fixed-fixture experiment, not native
Code Review support or final-artifact admission. No paid Apple credentials,
Docker, security overrides or quarantine stripping were used.

## Implemented mechanism

An ordinary-user, private invocation launchd job starts a fixed native broker.
LaunchOnlyOnce removes the job after broker exit; KeepAlive is false and
AbandonProcessGroup is false. The pre-trace bootstrap has default termination
signals and remains in the job group. Only fixed trusted code executes there.
After PT_TRACE_ME, the broker confirms its trace stop and resumes it; a separate
libproc observer verifies the actual tracing flag, parent and birth identity.
Admitted fixtures may ignore SIGTERM and change sessions. A versioned deny-default
Seatbelt fixture profile permits only its observation files and explicit read
control, closes non-stdio descriptors and denies unmanaged process creation.

The fixture broker accepts only named benign modes, not customer commands or
managed launch requests. Its stdout is observation evidence, not the eventual
private authenticated request/result protocol. No production backend was enabled.

## Native passing evidence

The final repetition run executes 100 trials each of suspended creation,
running trusted pre-trace bootstrap, trace-confirmed stop, resumed tracing,
executable replacement and post-confinement execution: **600 positive races**.
All workers disappeared and every job was independently absent after broker
SIGKILL. The maximum observed worker-cleanup interval was **0.0153 seconds**, below
the mandatory five seconds. This is an observed maximum, not a universal hard bound.
The unsupervised running/default-signal negative control survived the five-second
window; only after measurement did the harness clean it up.

All binaries were built ARM64 with -Wall -Wextra -Werror, ad-hoc signed with
hardened runtime and strict native signature verification. No entitlements were
added. Profile SHA-256:
`e122fbd5467e7b594d70e2b5b27038f2e698e171d9b38f9fcb7e06d344867549`.
Local receipts also retain source and final executable hashes and codesign details;
these locally generated receipts are not SpecFact-signed release manifests.

Positive unsandboxed process, read and loopback UDP-connect controls succeeded.
After confinement, libc fork/vfork, raw ARM64 fork and posix_spawn failed with
permission denial. Approved read/output succeeded; forbidden read, network access
and signal-to-broker probes failed. An explicitly inherited forbidden-file FD was
readable in the positive control and closed in the confined fixture.

Raw vfork syscall 66 separately produced SIGSYS without a sandbox. It is retained
as an unavailable-kernel-route control, not counted as Seatbelt denial. The libc
vfork entry point is still exercised and denied. Published XNU conditionally
maps syscall 66 to nosys; shipping-OS behavior must be measured separately.

## Failed controls retained

An initial suspended negative control disappeared even with AbandonProcessGroup;
it did not establish attribution to launchd. The corrected running/default-signal
control proves the distinction. An untraced fixture deliberately ignoring SIGTERM
survived ordinary launchd cleanup. Such behavior is forbidden in the fixed trusted
pre-trace bootstrap, which executes no customer code. After tracing, the actual
SIGTERM-ignoring/session-changing worker died in every measured race.

The raw-fork positive control initially mishandled Darwin's second return register;
it was corrected against XNU fork return semantics before any denial claim. Raw
vfork's SIGSYS was then separated from the enforcement controls. Parser/compiler/
startup failures were never counted as confinement.

## Remaining acceptance

The creation-to-tracing candidate is now proven for these fixed fixtures on this
physical host; earlier source-only rejection was not a proof of impossibility.
This does not freeze the production backend or approve macOS 14/15/26.
Still required: startup interruption during confinement and exec stops, authenticated
CLI/worker protocol, CLI death/cancellation/timeout/concurrency, tracing manipulation
and IPC/loader escapes, resource enforcement, exact final distribution signatures
and authenticated manifests, full managed adapters and manager corpus, Linux
regression, and independent-Mac default-protection installation. Tracing's effects
on code-signing enforcement and third-party library loading remain explicit gates.

Reproduce as a maintainer:

```sh
hatch run python scripts/macos_managed_boundary/startup.py \
  --repetitions 100 --out .specfact/native-compat/startup-confinement-100.json
```

Raw logs, generated binaries and receipts remain ignored. Never promote this
subset receipt to signed_boundary_verified or production_approved. No module
version/signature/registry change is warranted by a non-shipped experiment.

## Independent review corrections and final rerun

The review-agent identified five concrete harness defects: delayed-signal timing,
fallback-alarm attribution, worker-first identity output, premature job-removal
failure and a birth-check-to-numeric-kill PID reuse race. All were addressed with
focused failing tests before fixes. Native observation now obtains real kernel
audit tokens through read-only task-name rights, and signaling uses
proc_signal_with_audittoken; no debugger or task-control entitlement is added.
Both broker and worker reject a deliberately stale token while the original
fixture remains alive. Positive timing uses the native pre-signal timestamp;
negative controls wait five full seconds after confirmed signal issuance.
Published fallback deadlines must not overlap that window. Job removal may
settle only within the remaining deadline. The corrected suite again passes all
600 native races. The max interval above refers to that corrected run.

Public source/API basis inspected 2026-10-02:
[Apple libproc wrapper](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.c#L462)
and the host SDK's libproc.h/mach task-info definitions. This local host API
behavior still requires the advertised OS matrix; it is not an implicit OS floor.

Final source/policy binding rerun: all 600 transitions passed, plus normal
completion, the negative survivor control, unsandboxed positive probes and the
actual exec/SIGTRAP control. Native sources compile from private byte snapshots;
the suite supplies one captured profile to every job and hashes those same bytes.
Imported analyzer helpers likewise execute captured source bytes. Later checkout
edits cannot be represented as the source of a previously tested binary.

The source-binding changes have focused mutation tests, and analyzer source
provenance tests recorded three failures before their fixes. The sealed native
Semgrep clean/defect cases again passed after these changes using spaces and
Unicode in their private roots. Full platform and customer-install admission
remain outstanding.
