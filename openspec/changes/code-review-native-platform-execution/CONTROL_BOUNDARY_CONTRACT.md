# Bounded native control fixture contract

Recorded 2026-10-02; updated 2026-10-03 (Europe/Berlin). This owner-authorized milestone is covered by
code-review-native-platform-execution. It is an experiment, not backend admission.
Only the three control sources, their unit test and this contract are in scope.
Parent owns repository gates and independent startup review; no archive is due.

## Protocol and authority

An invocation-scoped ordinary-user launchd job inherits the `control` Unix stream
listener through public `launch_activate_socket`. Its directory is 0700, socket
0600, inputs 0600. LaunchOnlyOnce=true, KeepAlive=false,
AbandonProcessGroup=false; no persistent agent/daemon or privileged entitlement.
The broker is built with one fixed worker pathname. Both are ad-hoc signed with
hardened runtime. Requests cannot name executables, projects, grants or host PIDs.

Requests: big-endian u32 length followed by exactly 52 bytes: u8 version=1,
u8 opcode, u16 reserved=0, u64 broker handle, u32 argument, u32 timeout_ms,
32-byte private random capability. Opcodes: 0 authenticate, 1 launch, 2 wait,
3 signal, 4 cancel. Launch takes only five fixed benign fixtures (output, hold,
pretrace, trace-stopped, runtime-trap), handle=0 and timeout 50..5000 ms. Signal takes SIGTERM
or SIGKILL only. Other unused fields must be zero. Responses are u32-length
prefixed JSON, at most 2048 bytes, version=1, with explicit error/state/status.
At most eight total workers, 64 requests, 1024 output bytes per worker and 4096
queued response bytes; completed handles are retained, never recycled. One
pending wait is permitted. Partial frames have a one-second assembly deadline.

Authentication checks ordinary UID, real LOCAL_PEERPID and LOCAL_PEERTOKEN
against the independently captured caller kernel token including pid version,
plus capability on every request. No synthetic audit token or task-control right.
A second connection cannot replace the owner or borrow a handle; other invocation
handles and capabilities must fail. Authentication is not a production seal:
same-user hostile code, descriptor delegation and mutable build paths need more
proof before any production boundary claim.

## Lifecycle

Broker creates direct children with fixed argv and sanitized environment; workers
inherit only stdio. Trusted pretrace fixtures keep default termination and their
launchd group. Worker PT_TRACE_ME/stop is observed and continuously serviced by
the broker, then deny-default Seatbelt applies before benign fixture work.
No project/customer code is admitted. Process-fork is denied; the worker performs
native fork, allowed-stream, forbidden-read and network probes.

The event loop watches client EOF during partial frames, startup and pending wait;
no blocking waitpid. EOF or fail-closed broker error terminates the broker with
SIGKILL, letting XNU traced-child exit and launchd pretrace group ownership remove
workers. Worker signals use direct unreaped-child ownership, never a PID selected
by a client or a birth-check followed by numeric-PID signaling. No polling cleanup
fallback is allowed to rescue a failed measurement. Timeouts/cancel/status are
explicit. Independent startup_observe captures real tokens, birth identity,
parent/group/tracing and checks no original worker survives five seconds, plus
automatic job removal. Harness cleanup occurs only after measurement.

## Required proof

Spec -> failing tests -> C/Python implementation -> actual signed native proof.
Cover output/exit=37, malformed version/opcode/length/reserved/arguments,
foreign handles/capabilities, authentication, fragmentation, bounded launches,
signal/cancel/timeout, CLI loss during wait and every fixed startup phase,
simultaneous invocation isolation and second-client rejection. Repeat each new
lifecycle case 100 times if feasible; partial runs cannot satisfy repetition gate.
Receipts always production_approved=false and signed_boundary_verified=false.
Only macOS 27.0.1 build 26A434 ARM64 is measured; no older-OS support assertion.

## Primary API evidence and limits

Accessed 2026-10-02. Installed SDK public launch.h, sys/un.h, libproc.h and spawn.h
are compile-time authority. [Apple socket activation documentation](https://developer.apple.com/documentation/xpc/launch_activate_socket)
provides the exact function and ownership of returned descriptors.
Pinned [XNU 11417.140.69 Unix header](https://github.com/apple-oss-distributions/xnu/blob/xnu-11417.140.69/bsd/sys/un.h)
and [peer-token implementation](https://github.com/apple-oss-distributions/xnu/blob/xnu-11417.140.69/bsd/kern/uipc_usrreq.c)
explain LOCAL_PEERTOKEN; this tag is not asserted to match the running kernel.
Pinned [launchd 842.92.1 manual](https://github.com/apple-oss-distributions/launchd/blob/launchd-842.92.1/man/launchd.plist.5)
and installed launchd.plist(5) document socket mode and group abandonment.
Public sandbox.h marks sandbox_init deprecated and flags other than SANDBOX_NAMED
reserved. Custom Seatbelt text therefore remains an unsupported fixture API gap,
even when measured; do not advertise a supported production policy API.

## TDD results

- Initial RED: `python3 -m unittest discover -s tests/unit -p test_macos_managed_control.py`
  ran nine tests: eight errors (missing control.py), one native test skipped.
  Captured before C/Python implementation in `/private/tmp/specfact-control-red.txt`.
- Extended RED: twelve tests, two failures (path bound and incomplete proof receipt)
  plus two errors (missing protocol gate catalog), one skipped. Captured in
  `/private/tmp/specfact-control-red-extended.txt` before the corresponding fixes.
- Native debugging preserved explicit startup failures: asynchronous launchd
  socket setup initially produced FileNotFoundError, and buffered CLI stdout
  initially hid its wait handshake. Socket creation is now bounded observation
  only; no polling cleanup was introduced. Handshake reads are bounded and avoid
  TextIO read-ahead. Socket paths are checked against public sockaddr_un[104].
- Final GREEN: `SPECFACT_NATIVE_CONTROL=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p test_macos_managed_control.py`
  passed all twelve tests, no skips, in 4.371 seconds. Captured in
  `/private/tmp/specfact-control-native-green.txt`.
- Scoped Ruff lint/format checks pass; BasedPyright reports zero errors/warnings.
  C builds use ARM64 `-Wall -Wextra -Werror`. OpenSpec strict validation passes.
  Parent retains repository gates and independent startup review; this checkpoint
  does not claim final merge authority or complete/archived OpenSpec work.

## Historical signed native repetition proof — superseded

**Historical evidence only. This 1,218-trial receipt does not approve current
source bytes or satisfy the corrected acceptance gate.** Review exposed EOF
attribution, runtime-trap and terminal-reason defects; the original result is
retained for chronology rather than current acceptance.

`python3 scripts/macos_managed_boundary/control.py --repetitions 100 --out /private/tmp/specfact-control-native-100.json`
completed successfully on macOS 27.0.1 build 26A434, ARM64, SDK 27.0, ordinary
UID 501, on 2026-10-02 (Europe/Berlin). All 1,218 recorded trials passed:
18 protocol/positive controls and 1,200 lifecycle cases. Every lifecycle has
100 actual repetitions, not extrapolated counts. Each signed native component
is ad-hoc with hardened runtime and no entitlements; the broker additionally
checks its compiled worker CDHash requirement through public Security APIs.
Independent startup_observe obtains kernel audit tokens using read-only task-name
rights, not task-control/debugger access. Worker statuses and survivor checks are
independent; observation or cleanup errors fail the experiment.

| Lifecycle case | Passed repetitions | Maximum observed removal (seconds) |
| --- | ---: | ---: |
| cancel | 100 | 0.009897 |
| timeout | 100 | 0.574547 |
| signal | 100 | 0.009894 |
| eof-pretrace | 100 | 0.012974 |
| eof-trace-stopped | 100 | 0.014832 |
| eof-running | 100 | 0.010459 |
| eof-wait | 100 | 0.017278 |
| eof-partial | 100 | 0.013605 |
| partial-timeout | 100 | 1.092454 |
| broker-kill | 100 | 0.010975 |
| cli-kill-wait | 100 | 0.010616 |
| isolation | 100 | 0.014139 |

Removal timing begins at cancellation/signal, native broker/CLI token signal
issuance, or client disconnect/partial-frame submission as appropriate. Timeout
rows include the remaining worker deadline. Cancel/timeout/signal rows measure
worker removal while their broker remains available; EOF/broker-kill/partial-timeout
rows also require automatic job removal within the same five seconds. Every
isolation row checks a concurrent invocation's worker remains alive after the
first client's EOF, rejects foreign handles/capabilities and second connections,
and then completes its own cancellation. Pretrace rows independently confirm
an untraced direct child in the launchd group; trace-stopped rows confirm traced
startup in that group; running rows confirm a traced worker in its own session.
The separate CLI-death case uses actual SIGKILL with its captured real token.
No harness-assisted signal occurs inside a measured survivor window.

Protocol proof includes exit 37 with output, sandbox-denial markers, invalid
version/opcode/reserved/mode/signal/unused fields, host-PID and foreign-handle
rejection, oversized/undersized header rejection without allocation, fragmentation,
eight-total-worker limit, authentication/capability rejection, real foreign peer
PID rejection, negative stale pid-version rejection, and ignored SIGTERM followed
by native timeout. Unsandboxed worker mode 0 positively exercises fork, host read
and loopback UDP connect; sandboxed modes reject those native operations.

The receipt keeps `production_approved=false` and `signed_boundary_verified=false`.
Local raw receipt: `/private/tmp/specfact-control-native-100.json`;
progress log: `/private/tmp/specfact-control-native-100.log`. Temporary build
binaries/jobs are removed; these digests retain their exact evidence identity.

Receipt SHA-256: `d33aa3e7842fa2bc6535f5a845665957fd3bc868443fed4b07ca249b76818c78`.

| Component | Source SHA-256 | Signed binary SHA-256 |
| --- | --- | --- |
| worker | `29aea7caa80ca3b28289cecd21171b4a68781e8b530485415c0ed52521cd33ac` | `bf12b0b0361d5771827835de430d8454f6f6875fb6523ff4f8cce8cdaf23a1f8` |
| observer | `b6e03c3c6fbd023898e5c426258e1d5d5188758b0b4578fc47b16b84b89d6fd9` | `f4f31a4425f75515a09489324bf0b1ba6ece35d1e0a80360c3d404645648c2d5` |
| broker | `6ec6f685cea403086601c65247032b9e519a62c6811c57b52a0f9d6d167fa285` | `e0276b0e02815988c04e9f823dab5d120dea9d65df0b26ab69496d5faba2fdf9` |

## Limits, failure modes and next actions

Confidence: High that the historical run completed as recorded; its acceptance
conclusion is superseded by the review corrections below. No older OS,
independent installation, analyzer execution, production seal or resource-bound
admission is established. The test harness uses Python 3.14; this is not a claim
for the customer Python 3.11–3.13 matrix. The historical repetition run used the
native bytes of its original checkpoint, which differ from the corrected broker
and worker recorded below.

- Custom Seatbelt text/initialization is unsupported despite measured success.
  Require exact-profile acceptance on every advertised OS version; private API risk
  must be explicit in the frozen platform contract. Availability alone is neither
  approval nor a separate requirement for Apple to publish a supported profile API.
  The worker does not exec replacement binaries under confinement and needs no
  root-directory read grant; analyzer dyld grant work belongs to the parent.
- Mutable same-user fixture inputs, signature-check-to-exec replacement and Unix
  descriptor delegation are not a sealed hostile-user boundary. Private modes,
  real peer tokens, per-request capabilities and fixed CDHash constrain this
  experiment; production needs immutable payload ownership and delegation proof.
- Platform differences or startup/observer failures can invalidate lifecycle
  attribution. Keep the five-second/100-case gate and explicit failure receipts;
  do not substitute observer polling kills or synthetic audit-token signaling.

The fixture is bounded to eight workers per invocation, 64 frames and a 30-second
broker session, with one-second frame assembly and 50–5000 ms worker deadlines.
The repetition proof takes minutes locally and creates only ephemeral jobs/files.
Rollback is removal of these five new files; no module, runtime environment,
startup source, signature manifest, version or released adapter was changed here.
Next: parent review/gates, immutable payload and descriptor/IPC proofs, supported
policy API assessment and independent-Mac acceptance before production admission.

## Runtime signal regression, 2026-10-03

The fixed control worker has no executable replacement, so only its initial
tracing SIGSTOP is a control transition. A dedicated fifth benign mode raises
SIGTRAP after confinement; the broker must forward it and report signal 5.
Do not suppress traps or map crashes to clean completion. Native regression
precedes the broker correction; rerun the existing lifecycle cases afterward.

Accepted cancel/SIGKILL must retire the worker timeout while waiting for reap;
expiry cannot overwrite its terminal action reason. SIGTERM retains its deadline
because workers may ignore it. A deterministic native timer/decoder regression
uses a mocked signal syscall and an expired deadline; it is logic evidence only,
not a worker lifecycle proof.

## Scoped quality and EOF attribution corrections — 2026-10-03

The parent-owned final 100-repetition run failed after 20 completed rounds with
TimeoutError in isolation_trial's cancellation wait. Preserve
`.specfact/native-compat/control-final-100.json` and
`/private/tmp/specfact-control-final-100.log` as actual failure evidence.
The original receipt does not supersede that failure. Diagnosis and a fresh full
corrected proof are required; no retry can turn a failed same-byte run green.

Only control.py, its owned unit tests and this contract are edited in this slice.
FrameFields and PeerIdentity group the fixed Python request/caller parameters;
all owned callers were updated. Wire bytes and CLI entry points are preserved.
Small lifecycle/protocol/event helpers remove the flagged complexity and nesting;
receipt counts use one successful-case tally. Popen owns its streams through a
context manager; bounded kill/reap still runs before leaving that context.
JSON records use sys.stdout.write plus explicit flush, preserving protocol stdout.
The parent-authorized stdlib bootstrap icontract exception applies to these
fixture helpers: no runtime dependency, decorators or security boundary is added
to make an advisory contract scanner pass. Remaining substantive quality findings
must still be fixed, with no broad quality waiver.

Meaningful native baseline before refactoring: 14 tests passed in 4.888 seconds,
including bootstrap-timeout cleanup and runtime SIGTRAP regression. Pure quality
refactors use that baseline. New behavior REDs are retained in
`/private/tmp/specfact-control-quality-behavior-red.txt` (four errors) and
`/private/tmp/specfact-control-native-clock-red.txt` (three errors).

The broker's launch response now supplies deadline_ns in CLOCK_MONOTONIC. Retain
that launch value; cancel/status responses can expose a retired session deadline.
Python time.monotonic uses mach_absolute_time on this host; its epoch is not used
for comparison with native deadline_ns. Use stdlib
clock_gettime_ns(CLOCK_MONOTONIC) directly, verified by ten bracketed calls to the
actual public libc clock_gettime symbol with the SDK timespec layout. Native
cleanup observations end strictly before launch deadline_ns minus 250 ms, and
must independently finish within five elapsed seconds. Reject an initial native
horizon below 1.5 seconds after the margin. No limits were enlarged.

Primary source, accessed 2026-10-03:
[Apple Libc 1725.40.4 clock implementation](https://github.com/apple-oss-distributions/Libc/blob/Libc-1725.40.4/gen/clock_gettime.c)
shows distinct CLOCK_MONOTONIC and Mach-time paths; that tag is not asserted to
match every shipping kernel. Actual host libc/stdlib bracketing is authoritative
for this fixture's reader mapping.

A negative native test deliberately holds a duplicate of the client descriptor,
so closing the nominal client cannot deliver EOF. It requires failure before the
competing worker timer and confirms the original worker is still alive before
releasing the duplicate. C source mutation and observer-assisted rescue are not
used inside measurement. Descriptor delegation remains a separate production gap.

Failures snapshot bounded native event/error tails, captured/current kernel
identities, the signed broker digest and the last 64 request/results before
cleanup. Receipts are private 0600 files under /private/tmp, bounded to 256 KiB;
capabilities and authority input bytes are excluded. The main failure receipt now
retains completed trials and explicitly includes a failed trial. This makes a
future terminal wait timeout diagnosable rather than silently discarded by build
temporary-directory removal.

## Corrected lifecycle checkpoint before source snapshot fix — 2026-10-03

This lifecycle checkpoint predates the source snapshot correction below; its
source inventory used a post-build reread and cannot establish compiler-input
provenance. The fresh corrected run completed once, without retry, on macOS 27.0.1 build
26A434 ARM64: 1,219 passing records, comprising 19 protocol/positive records and
100 repetitions of each of the 12 lifecycle cases. Both control_subset_passed
and repetition_gate_passed are true. The original 1,218 record is historical;
the failed later 100-round receipt remains failure evidence. This acceptance
uses the parent's runtime-trap, terminal-reason and immutable launch deadline
corrections, plus the harness corrections above.

The original isolation cancellation-wait failure cannot be causally assigned
from its retained evidence: it did not retain native events or identities at
failure. It did not recur in 100 corrected isolation trials. No additional C
fix is established by this run, and this document does not claim the parent's
timer fix alone explains that failure. Future failures retain bounded evidence
before cleanup and stop the proof; they cannot silently retry.

| Lifecycle case | Passed repetitions | Maximum observed removal (seconds) |
| --- | ---: | ---: |
| cancel | 100 | 0.007510 |
| timeout | 100 | 0.647196 |
| signal | 100 | 0.007953 |
| eof-pretrace | 100 | 0.010280 |
| eof-trace-stopped | 100 | 0.009398 |
| eof-running | 100 | 0.009931 |
| eof-wait | 100 | 0.011468 |
| eof-partial | 100 | 0.010046 |
| partial-timeout | 100 | 1.170874 |
| broker-kill | 100 | 0.012106 |
| cli-kill-wait | 100 | 0.009487 |
| isolation | 100 | 0.009623 |

All loss-of-client/job-removal cases independently enforce the five-second
elapsed bound and the native pre-timeout cutoff. The isolation row measures
left-invocation cleanup, then requires the right worker to remain alive and
successfully complete cancellation/wait. The clock receipt contains ten actual
libc samples bracketed by the stdlib CLOCK_MONOTONIC reader; every sample passed.
The final focused suite passed 20 tests with no skips in 10.435 seconds, including
the withheld-EOF negative, actual SIGTRAP status, and native control subset.

Exact commands, from the dedicated worktree:

```sh
python3 scripts/macos_managed_boundary/control.py --repetitions 100 --out /private/tmp/specfact-control-corrected-100.json > /private/tmp/specfact-control-corrected-100.log 2>&1
SPECFACT_NATIVE_CONTROL=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p test_macos_managed_control.py > /private/tmp/specfact-control-quality-final-tests.txt 2>&1
ruff check --no-cache scripts/macos_managed_boundary/control.py tests/unit/test_macos_managed_control.py
ruff format --no-cache --check scripts/macos_managed_boundary/control.py tests/unit/test_macos_managed_control.py
.venv/bin/basedpyright scripts/macos_managed_boundary/control.py tests/unit/test_macos_managed_control.py
PYLINTHOME=/private/tmp/specfact-control-pylint .venv/bin/pylint --persistent=n scripts/macos_managed_boundary/control.py tests/unit/test_macos_managed_control.py
```

All commands exited zero. Ruff lint/format pass; BasedPyright reports zero errors,
warnings and notes; Pylint reports 10.00/10 with no findings. The actual repository
KISS metric helper reports zero findings for the owned Python scope. Cyclomatic
complexities: lifecycle_trial 6, cli_death_trial 1, protocol_trials 2, receipt 10,
wait_event 3. The narrow stdlib icontract exception remains; parent repository
gates were not rerun here.

Receipt SHA-256:
`b157a6cca7d90fb75ef274522b4f257f7ede85a25f7deca84390c2080a7ed2d7`.

| Component | Source SHA-256 | Signed binary SHA-256 |
| --- | --- | --- |
| worker | `67cbda681abc757db0e615675ba39e29ab5d30d4900c3bfdebf8b4840c948c8b` | `92e984e29316cc15f53b0e5e241309bab92c81617531f2e3a3e7461e88abfb81` |
| observer | `b6e03c3c6fbd023898e5c426258e1d5d5188758b0b4578fc47b16b84b89d6fd9` | `f4f31a4425f75515a09489324bf0b1ba6ece35d1e0a80360c3d404645648c2d5` |
| broker | `8fcf5dd23fd4a48e75ebeb4120cde61386d6d1281a753c21581d3ebb3048e489` | `97271346d74810e3e14e7586a3a11cc2622035a2bc82a672d35a21bf52151e56` |

All three native source digests match the on-disk sources after the proof.
Python control.py SHA-256:
`ecc88bfaf91f2438b99dbbd2c450560f0a4cacf358d95ed03596299a6bef9423`.
Owned test SHA-256:
`820f6d38de75a9140500c0558027a3e0585fedfc7ca1a46f71ded212bd6aca07`.
Temporary builds/jobs were removed normally. The raw receipt and log remain at
the command paths above. No C or parent-owned source was edited in this slice.

Confidence: High for this measured fixture and its corrected acceptance counts;
Low for assigning the historical isolation timeout's root cause. Both
production_approved and signed_boundary_verified remain false. No older OS,
independent Mac, production seal or resource/tracing/IPC escape admission is
established. Parent independent review and the separate full escape gate remain
next; these results do not authorize production enablement.

## Source snapshot provenance correction — 2026-10-03

Each build must read each fixed C source exactly once, write those bytes into a
read-only source snapshot inside the private 0700 build directory, and compile
that snapshot. The receipt must hash the captured bytes used for compilation,
never reread the repository pathname after building. This binds source evidence
to the compiler input despite concurrent repository edits; it does not seal
mutable same-user fixture inputs against a hostile owner. Worker CDHash binding,
fixed native sources, protocol limits and lifecycle deadlines remain unchanged.
A regression changes temporary source originals during compilation and requires
private read-only compiler inputs plus matching snapshot digests and single
original reads. No checked-in C source is mutated by that test.

Snapshot regression RED: 21 tests, seven failures, three native skips, retained
in /private/tmp/specfact-control-snapshot-red.txt. All seven failures are in the
new provenance test. The implementation captures each original once, writes a
0444 snapshot under a 0700 build directory, compiles it and hashes the captured
bytes. No live source reread is used for the inventory. The initial native test
suite after this correction passed all 21 tests with no skips in 9.959 seconds,
retained in /private/tmp/specfact-control-snapshot-native-green.txt.

The restricted-runner attempt is explicit failure evidence:
/private/tmp/specfact-control-snapshot-100.json and its same-stem log. It failed
before any lifecycle trial at the unsandboxed worker's native loopback positive
probe (status 28); the execution runner restricts network access. The native
acceptance uses the authorized escalated execution environment. No worker grants,
network grants, timer or cleanup limits were changed to make that probe pass.

Failure provenance: the original parent cancel/wait failure receipt has no trial,
identity or event records and records broker source digest
f6b54bdd3be76efe5867ef7966a91a35548cfe432e426fcca1d5369c5d3fa61e.
The log identifies isolation_trial's right.request(wait) after cancellation.
That differs from the corrected broker source recorded above. Neither the old
receipt nor log establishes whether child reaping, output EOF or response delivery
stalled. No native cancellation-wait failure snapshot exists in the retained
/private/tmp/specfact-control-failure-*.json catalog. The protocol/launchctl
10-second timeout snapshots match the deliberate bootstrap-timeout unit test
injection; the test logs include their diagnostic paths. They do not reproduce
the earlier terminal wait failure. Keep that historical failure unresolved and
separate from present passing acceptance; do not infer an additional C patch.

## Final acceptance with source snapshots — 2026-10-03

The final snapshot-build proof completed successfully with 1,219 passing records:
19 protocol/positive controls and 100 repetitions of each of the 12 lifecycle
cases. No lifecycle failure, cancellation-wait timeout or silent retry occurred
in this run. Both control_subset_passed and repetition_gate_passed are true.
The earlier 1,218 historical proof and pre-snapshot 1,219 checkpoint do not approve
this current harness. They remain separate historical evidence above.

The terminal wait failure in the old parent log remains causally unresolved:
there is no retained native cancellation-wait snapshot to distinguish child
reaping, output EOF and response delivery. The current corrected C and harness
passed 100 isolated cancellation/wait trials. No additional C patch is justified
by the available evidence. Failure capture remains active before cleanup; the
bootstrap-timeout diagnostics in unit output are deliberate test injections.

Native loss-of-client/job-removal proof records the original worker deadline in
900 lifecycle records and excludes timer death using a 250 ms native margin plus
the independent five-second elapsed bound. All ten libc/stdlib CLOCK_MONOTONIC
brackets passed. The native withheld-EOF test rejects disappearance attribution
while the duplicate descriptor keeps the worker alive, before releasing it for
post-measurement cleanup. No observer kill is used to rescue measurement.

| Lifecycle case | Passed repetitions | Maximum observed removal (seconds) |
| --- | ---: | ---: |
| cancel | 100 | 0.006606 |
| timeout | 100 | 0.649175 |
| signal | 100 | 0.008076 |
| eof-pretrace | 100 | 0.010695 |
| eof-trace-stopped | 100 | 0.009593 |
| eof-running | 100 | 0.009411 |
| eof-wait | 100 | 0.013063 |
| eof-partial | 100 | 0.012581 |
| partial-timeout | 100 | 1.170975 |
| broker-kill | 100 | 0.011486 |
| cli-kill-wait | 100 | 0.009239 |
| isolation | 100 | 0.011158 |

Exact native commands in the dedicated worktree, using the authorized escalated
runner so launchd and the unsandboxed loopback positive control can execute:

```sh
python3 scripts/macos_managed_boundary/control.py --repetitions 100 --out /private/tmp/specfact-control-snapshot-native-100.json > /private/tmp/specfact-control-snapshot-native-100.log 2>&1
SPECFACT_NATIVE_CONTROL=1 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests/unit -p test_macos_managed_control.py > /private/tmp/specfact-control-snapshot-final-tests.txt 2>&1
```

Final focused native suite: Ran 21 tests in 10.563s; OK, no skips. Includes the provenance
regression, actual native control subset, runtime trap and withheld-EOF negative.
The native suite ran after the 100-round proof finished. The withheld-EOF
assertions moved into a small helper to remove its nesting warning, preserving
behavior. Scoped Ruff lint/format, BasedPyright (zero errors/warnings/notes),
Pylint (10.00/10) and repository KISS metric checks (zero findings in both files)
pass. Only the narrow parent-authorized stdlib icontract exception remains.
Repository-wide parent gates were not repeated.

Receipt SHA-256: `3793ed61f3cd4c0e69bb7dad0793876db19fb11a798ae61404e363487ef6bdb2`.

| Component | Compiled snapshot SHA-256 | Signed binary SHA-256 |
| --- | --- | --- |
| worker | `67cbda681abc757db0e615675ba39e29ab5d30d4900c3bfdebf8b4840c948c8b` | `92e984e29316cc15f53b0e5e241309bab92c81617531f2e3a3e7461e88abfb81` |
| observer | `b6e03c3c6fbd023898e5c426258e1d5d5188758b0b4578fc47b16b84b89d6fd9` | `f4f31a4425f75515a09489324bf0b1ba6ece35d1e0a80360c3d404645648c2d5` |
| broker | `8fcf5dd23fd4a48e75ebeb4120cde61386d6d1281a753c21581d3ebb3048e489` | `6a291ff83c28ed86e63afd8a9c64a3b16f47a23a0814c0aa322d056a8569433f` |

All three snapshot digests match the current native sources after the run.
control.py SHA-256: `5ff101a877ae05be594a8c5c0caaae4eac971009146cb19fd08a59011492b626`.
test_macos_managed_control.py SHA-256: `7b93c6edfffe65d515419803f5d6e8a5e30632c619d6fea030fafc1b8342d84c`.

Only control.py, its owned test and this contract changed in this slice. No C,
startup/analyzer source, module environment or signature manifest was edited.
Confidence: High for the measured current fixture; Low for historical root-cause
attribution. production_approved=false and signed_boundary_verified=false remain
mandatory. This host is macOS 27.0.1 build 26A434 ARM64; no older OS or independent
Mac claim is made. Independent review, production sealing and the separate full
resource/tracing/IPC escape gate remain outside this fixture's acceptance.

## Failure reporting regression — 2026-10-03

Diagnostic capture and post-failure cleanup must preserve the original exception.
Secondary failures are noted by class only, without private message data; a
cleanup failure after a successful body must still fail. Diagnostic files remain
0600 and bounded, using an available private temporary directory on Linux tests.
A fixed failure-phase enum identifies trusted operations without exporting
request fields, native statuses, process identities, raw messages or capabilities.

RED: exception tests reported one failure/three errors; phase tests reported
eleven errors. GREEN: thirty focused tests passed with explicit native cases,
including original-exception identity and private-data rejection. Eight narrow
Pylint protected-access annotations apply only to deliberate white-box
diagnostic regression tests, consistent with existing repository test patterns.
They do not relax production/private API or security gates.

The native C sources were unchanged. A further physical-host 100-round run
passed 1,219 records and 100 additional isolation trials passed. The hosted
control failures remain unproven; these local passes cannot approve that matrix.
