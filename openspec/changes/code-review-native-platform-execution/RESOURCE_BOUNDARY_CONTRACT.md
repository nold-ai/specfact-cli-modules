# Native resource maintainer proof

Owner-authorized disjoint #460 resource scope, 2026-10-03 (Europe/Berlin).
Maps to native isolation capability evidence, required capability unavailable,
and cancellation and descendants bounded. No production admission or integration.

## Scenarios written before implementation

1. Resource controls: a native ad-hoc/hardened worker with empty entitlements
   establishes tracing, fixes soft and hard limits, reads them back, attempts
   to increase each hard limit as an ordinary user, and repeats the attempt
   after deny-default confinement. Raising must fail EPERM and readback must
   remain exact. Parser/startup/signature failures are not resource evidence.
2. Paired native probes: below-limit operations succeed; resource-specific
   over-limit operations run against both limited and unbounded controls.
   Probe 32 descriptors, 4096-byte individual file size, disabled core dumps,
   address-space ceiling measured from loaded baseline plus 32 MiB, and
   RLIMIT_DATA at 16 MiB. Neither DATA nor AS/RSS is assumed enforced.
   Anonymous memory probes exercise both mmap and mach_vm_allocate with
   separate 1 MiB positive and 64 MiB over-limit attempts, freeing the first
   method before the second. Peak simultaneous allocations are at most 65 MiB,
   never more than 128 MiB. Both APIs must enforce a claimed VM ceiling.
   AS is a virtual-address bound, never a measured RSS/physical-memory bound.
3. CPU: soft=hard=1 CPU second; default, ignored and blocked SIGXCPU controls
   burn a finite target of 3 CPU seconds, with loop/accounting overshoot recorded. A successful default-signal exit
   alone cannot establish an adversary-resistant hard CPU ceiling. Actual
   wait status and accumulated native user+system CPU time are required.
4. Native watchdog: a resource-specific trusted supervisor owns one traced
   direct worker; a native one-shot kqueue timer configured for 1500 ms issues SIGKILL.
   This is not an exact 1.500 s completion guarantee: the receipt requires
   native wait status within 2500 ms and independent absence within five
   seconds of the original CLOCK_MONOTONIC deadline, never a receipt-time reset.
   Ignored/blocked SIGXCPU workers continue to burn until that timer fires;
   their bounded safety loop ends only at 3 CPU seconds. Watchdog evidence
   requires timer record, SIGKILL wait status and independent absence within
   five seconds, without harness cleanup rescue. This proves a wall deadline,
   not kernel hard CPU accounting or an aggregate CPU budget.
5. Broker death: existing captured startup broker/controller and independent
   libproc observer test CPU-ignore and CPU-block workers. Capture actual
   birth, parent and traced flags before kernel-token-bound broker SIGKILL;
   require absence within five seconds. Death fixtures never self-complete: their CPU loop is finite, then they
   pause until owner cleanup. No cooperative completion or timer may overlap
   the five-second measurement. 100 trials of each race are required
   for this resource lifecycle subset, without claiming the parent's gate.
6. Fail closed: observer error, command timeout, missing/late evidence,
   mismatched readback, failed control, or post-measurement rescue cannot
   pass. Retain private immutable source/binary hashes, signing details,
   exact commands, OS build, identity and raw records. Receipt always leaves
   production_approved=false. Resource gate remains false while mandatory
   admitted measured ceilings or this subset's race counts remain unproven.
   CPU/RSS are observed-only; no hard CPU/RSS requirement is introduced.

## Research boundary

Primary Apple sources inspected 2026-10-03: [setrlimit manual](https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/setrlimit.2.html),
[XNU resource implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_resource.c),
[XNU signal implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c).
The archived manual is not sufficient evidence for current enforcement. Public
main source is mechanism context, not a claim of matching this host kernel.
Native paired measurements decide the receipt. Inspect CPU signal-ignore/block
behavior and vm_map_set_size_limit rather than importing Linux assumptions.

## Evidence

Shared TDD, tasks, requirements and current control sources belong to the parent.
Exact logs and captured artifacts are private under
`/private/tmp/sf-resource-proof-20261003/` (0700 directory, 0600 log/receipt files).

Final commands (worktree root, serial native execution):

```sh
PYTHONDONTWRITEBYTECODE=1 hatch run python -m pytest tests/unit/test_macos_resource_limits.py -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 hatch run python scripts/macos_managed_boundary/resource_limits.py --out /private/tmp/sf-resource-proof-20261003/final.json --death-repetitions 100
PYTHONDONTWRITEBYTECODE=1 hatch run ruff check --no-cache scripts/macos_managed_boundary/resource_limits.py tests/unit/test_macos_resource_limits.py
PYTHONDONTWRITEBYTECODE=1 hatch run ruff format --no-cache scripts/macos_managed_boundary/resource_limits.py tests/unit/test_macos_resource_limits.py --check
PYTHONDONTWRITEBYTECODE=1 hatch run basedpyright scripts/macos_managed_boundary/resource_limits.py tests/unit/test_macos_resource_limits.py
openspec validate code-review-native-platform-execution --strict
```

RED: `red.log` exit 1, 12 missing-module errors, before either implementation file.
Further scenario REDs precede their implementations: `red-mach.log` (2 failed),
`red-evidence.log` (3 failed), `red-deadline.log` (1 failed),
`red-owner-clarification.log` (2 failed), and
`red-no-competing-completion.log` (3 failed).
GREEN: `green-final.log` exit 0, 23 passed; final native command exit 0,
`final.log` / `final.json`, 14 probes plus 100 death-ignore and 100 death-block
trials (214 total). Lint, format, types and strict OpenSpec validation pass.
Native compilation uses `-arch arm64 -Wall -Wextra -Werror`; all five native
artifacts verify ad-hoc hardened signatures, exact ARM64 and empty entitlements.
The captured startup controller, broker and observer were imported/built without
editing their shared sources. Signature details, source/build/binary hashes,
argv, wait statuses, native timers, identities and observer output remain in the
private receipt. No production integration, signed module asset edit, archive,
commit or push belongs to this subtask; full repository/analyzer gates remain
parent-owned.

Older native receipts are diagnostic/superseded only. Their finite CPU workers
could self-complete inside the death window, so none supplies lifecycle admission
counts. Only `final.json` uses the non-completing death fixtures. Earlier receipts
also contain the superseded self-imposed hard CPU/RSS admission rule.

Measured host: physical ARM64 macOS 27.0.1, build 26A434, Darwin 27.0.0,
XNU 13432.1.9; stdlib maintainer Python 3.14.7. This is native C boundary evidence,
not validation of the candidate CPython 3.11–3.13 analyzer matrix or older macOS.

| Resource | Exact final evidence / disposition |
| --- | --- |
| NOFILE | soft=hard=32; pre/post hard-raise attempts EPERM; over-limit dup EMFILE; independent 25 live FDs agrees with 21 duplicates + 4 inherited/private FDs. Ceiling is 32, not a promise of 32 usable slots. |
| FSIZE | soft=hard=4096 bytes; pre/post raise EPERM; 4096-byte write succeeds, next byte EFBIG; independent file size 4096. Per-file, not aggregate disk/output quota. |
| AS | Loaded VM baseline 500511719424 bytes; soft=hard=500545273856 bytes (baseline + 33554432). Pre/post raise EPERM; mmap ENOMEM and Mach VM KERN_NO_SPACE on 64 MiB attempts; both 1 MiB controls succeed. Independent VM 500513046528 bytes, RSS 6045696 bytes. Virtual address bound only. |
| Native wall timer | 1500 ms configured; SIGKILL wait status at 1.650375 s / 1.659333 s for ignored/blocked SIGXCPU. Independent absence at 0.161240 s / 0.171950 s after the original timer deadline. Both pass the 2500 ms status and five-second absence checks without rescue. |
| Owner death | 100 non-completing CPU-ignore + 100 CPU-block races; independently captured birth, parent and traced flags; kernel audit-token-bound broker SIGKILL. Maximum observed worker-disappearance latency 0.005831 s; automatic job removal separately verified within five seconds. |
| CPU observed-only | RLIMIT_CPU soft=hard=1; default SIGXCPU terminates; ignored/blocked workers consume 3.000107 / 3.000052 CPU s and exit 37. Blocked SIGXCPU is pending. Not admitted as a hard CPU budget. |
| DATA/RSS observed-only | DATA soft=hard=16777216 bytes, immutable, yet both 64 MiB mapping methods succeed. Independent RSS 73154560 bytes. DATA is not admitted as a mapping/RSS ceiling. No explicit mandatory RSS budget is introduced. |
| Fixture stress / worker count | At most 65 MiB simultaneously requested allocations per memory method; one fixed direct worker per resource job; actual worker fork denied. CPU loop targets three CPU seconds then death variants pause indefinitely, preventing completion rescue. |

Final receipt: `resource_gate_passed=true`, `resource_lifecycle_subset_passed=true`,
`kernel_hard_cpu_enforced=false`, `physical_ram_ceiling_proven=false`,
`production_approved=false`, no blocker for the admitted measured resource subset.
Full proof run took approximately 95.6 seconds. Parent-owned integrated output,
concurrency, alternate Mach APIs, runtime workload budgets and OS/ABI matrices
still require their own evidence. Confidence: high for this measured fixture/host;
no wider supported-platform assertion follows. Scheduler/observer delay fails the
original deadlines; unsupported limit behavior fails its admitted resource case;
parent transport/API changes require fresh integrated acceptance. Cleanup occurs
only after measurement and cannot rescue a failed receipt. Rollback is removal of
these four new source/contract files; private artifacts remain recoverable.

Harness SHA-256:
`e7750a480089913eb0a8abe778615e2a5f9e38eae72d2f6fc76dc7de122d5ba6`.
Native C source SHA-256:
`5fb953125f08222cfe5d0da1a8bc2d39af34467121832c8857b30e8db82017d3`.


## Owner clarification — 2026-10-03 (Europe/Berlin)

The selected design/spec require enforced configured numeric ceilings frozen from
measurements; they do not require an explicit kernel hard CPU or RSS budget.
This supersedes this proof's earlier self-imposed CPU/RAM admission blocker.
Admitted resource cases are NOFILE, FSIZE, AS and the native wall watchdog, with
100 death-ignore and 100 death-block trials. CPU/RSS observations and the DATA
non-enforcement result must remain explicit without becoming admission blockers.
No output byte ceiling is proven here: the 65536-byte parser guard is observation,
not kernel enforcement. Parent owns integrated output/worker/control budgets.
The resource supervisor has one fixed direct worker and denies worker fork;
this does not validate the parent's eight-worker concurrency contract.

The parent reported a Mach exception-port replacement gap, then its explicit
mach-task-exception-port-set denial passing both native tests; alternate API proof
is still parent-owned. This resource fixture reuses captured startup PT_TRACE_ME
BSD tracing and cannot approve or replace the parent's Mach transport proof.
Production remains false regardless of the resource subset's result.

## Actual Mach worker integration scenarios — 2026-10-03

Owner-authorized writes: control_worker.c, new control_resource.h, resource proof
sources/tests and this contract. Parent owns build capture/checker/broker/Mach
loops and selectors; modes remain 0..15. No BSD fallback can satisfy this gate.

Before confinement of every governed worker, configure hard/soft NOFILE=128,
FSIZE=16777216 bytes and AS=loaded VM baseline +1073741824 bytes. Capture the
loaded baseline before confinement via native task_info, name baseline/delta/
ceiling separately, reject overflow or inexact readback. Native raised-hard
attempts must fail before confinement. Both profiles explicitly deny setrlimit
syscalls and process-info-setcontrol; unchanged/lowering/raising libc calls and
raw Darwin syscall attempts after confinement must fail while readback stays
exact. Limits are inherited through admitted exec before target initializers.
No CPU or RSS budget is admitted; actual broker 5000 ms wall and 1024-byte output
and eight-worker caps remain the parent's enforcement and protocol contracts.

Reuse API: control_resource_configure(struct control_resource_state *), followed
by control_resource_verify(const struct control_resource_state *, int confined).
CONTROL_RESOURCE_POLICY appends the exact resource-change deny operations.
CPython owner can use the same API before its sandbox and inherited exec; no
CPython source edits are authorized here. Parent captures the header for worker
provenance. Actual Mach acceptance must retain target initializer ordering,
identity/tracing, denial probes, concurrent eight-worker cleanup and required
100 race repetitions, with no competing worker completion or rescue.

Mode 13 must keep default SIGTERM until PT_TRACE_ME succeeds, then ignore SIGTERM
before PT_SIGEXC and the initial SIGSTOP. No pre-trace ignored termination is
admitted. Resource configuration remains after established tracing and before
confinement. Parent owns pre-initializer suspended/CDHash admission.

### Integrated proof method and intermediate evidence

Private evidence is `/private/tmp/sf-mach-resource-20261003/`, directory 0700,
logs/receipts 0600. The Mach harness copies parent sources read-only and invokes
its existing signed build, protocol trials and all lifecycle loops unchanged.
Until parent header capture lands, it places the exact captured header in the
private build directory and explicitly adds that hash to the private worker
inventory. This is maintainer provenance, not canonical checker admission.

Paired signed native `RESOURCE_CONTROL_TEST` processes use the same configuration
API. Limited descriptor duplication reaches EMFILE after 124 duplicates plus
four inherited/private descriptors; unbounded control reaches 129 duplicates.
Sparse file writes touch one byte at offsets 16 MiB minus one and 16 MiB: limited
second write fails EFBIG and file length remains 16777216; control reaches
16777217. Both mmap and Mach VM deny a 1140850688-byte untouched virtual
reservation under baseline plus 1073741824, while both unbounded reservations
succeed and are immediately released. This reservation commits no physical
pages. Both 1 MiB positive probes succeed; only 1 MiB is physically touched.
No RSS bound follows. The sparse file is a per-file ceiling test, not output or
aggregate disk enforcement. Existing actual worker profiles grant no private
file-write capability.

`smoke3.json`: actual Mach worker baseline 500511965184 bytes, allowance
1073741824 bytes, ceiling 501585707008 bytes; libc and direct svc unchanged,
lowered-soft and raised-hard attempts denied after confinement; exact readback.
All 20 parent lifecycle cases, both resource eight-worker cases and 27 parent
protocol cases passed. A one-repetition smoke cannot admit the 100-race gate.
Eight-worker cases capture each original traced identity and resource record,
reject a ninth worker, then independently observe all workers and launchd job
removal after EOF or audit-token-bound broker SIGKILL. Every observation excludes
the original native timer, with no command-timeout or post-measurement rescue
acceptance. The 850-second harness allowance is maintainer runtime only.

RED evidence: `red.log` three failures/23 passes for missing header, worker hookup
and receipt gate; `red-mode13.log` three failures/24 passes before tracing-order
fix; `red-numeric.log` two failures/28 passes for absent numeric probe validator
and missing-case rejection. GREEN: `green-final.log` 30 passes; scoped Ruff check
and format checks pass, basedpyright zero errors/warnings. Initial smoke failures
remain rejected diagnostic evidence. `smoke.json` used the wrong target root;
`smoke2.json` recorded SIGKILL launching the restored target after destructive
protocol tests. Fresh `smoke3.json` runs lifecycle before those protocol negatives
and passed every actual protocol check. No cause beyond these observations is
asserted, and failed receipts never contribute acceptance counts.

### Final integrated GREEN — 2026-10-03 (Europe/Berlin)

The initial 850-second maintainer run stopped after 79–80 repetitions per case:
`partial-850.json` has `mach_resource_subset_passed=false` and explicit
`maintainer budget exceeded; proof rejected`. It is diagnostic only; none of its
counts supplies final admission. A fresh run uses 1800 seconds of maintainer
allowance. This changes no broker timer, output limit, observer window, cleanup
or lifecycle loop. Final command, serial native execution:

```sh
PYTHONDONTWRITEBYTECODE=1 hatch run python scripts/macos_managed_boundary/resource_limits.py --mach-control --death-repetitions 100 --out /private/tmp/sf-mach-resource-20261003/final.json
```

`final.json` and `final.log` record GREEN on native ARM64 macOS build 26A434:
2227 passing trials = 20 parent lifecycle cases ×100, two resource eight-worker
cases ×100, and 27 parent protocol checks. Every case count is exactly 100.
The 200 resource concurrency trials retain 1600 distinct worker resource records
and independent cleanup observations. Maximum eight-worker cleanup observation
was 0.086941 seconds; maximum recorded parent lifecycle observation was
1.169897 seconds. All pass the five-second observation window and their original
native timer exclusion. No command timeout, failed native case or cleanup rescue
is admitted. The ninth-worker rejection is exercised in every concurrency trial.
Target initializer ordering, exception endpoint controls, genuine signals and
mode 13 identity-swap remain part of the passing parent tests.

Representative actual Mach worker: loaded VM baseline 500512030720 bytes,
allowance 1073741824 bytes, absolute AS ceiling 501585772544 bytes; NOFILE 128,
FSIZE 16777216 bytes, post-confinement API mutation denied. Across all concurrency
records, VM baseline ranged from 500511719424 to 500512768000 bytes; every ceiling
was its own measured baseline plus the frozen allowance. These large VM numbers
are address space, not physical memory.

Final paired configuration process: baseline 500512686080 bytes, AS ceiling
501586427904 bytes. NOFILE: 124 duplicates + four pre-existing FDs reaches 128,
then EMFILE (24); unbounded control reaches 129 duplicates. FSIZE: last admitted
byte succeeds, next byte fails EFBIG (27), size remains 16777216; independent
filesystem stat agrees, and control size is 16777217. AS: mmap ENOMEM (12),
Mach KERN_NO_SPACE (3) for untouched 1140850688-byte virtual reservations;
both unbounded controls succeed and are released. Both 1 MiB positive probes
succeed; 1048576 physical bytes touched. No hard CPU or RSS ceiling is introduced.

Final flags: `signal_transport=mach-exception-v1`,
`mach_resource_subset_passed=true`, `all_trials_passed=true`,
`worker_header_bound=true`, `production_approved=false`.
`parent_header_capture_present=false` remains explicit: parent must add canonical
worker header capture/checker provenance before production-candidate admission.
No concrete enforcement blocker remains for this measured resource subset.
The native OS/ABI/analyzer matrix and production approval remain parent-owned.

Captured source SHA-256 values match the current files:

- control_worker.c: `95c55e6dd1862893d67b7c9bccc2a9ec23cb22f3ca0d6d09a791a10ae7d70aa0`
- control_resource.h: `f967f7bb8942b26ac02cc56830143bb07ddf461e18301f31000af716fcb87ae1`
- resource_limits.py: `5ea23a495c12f8e25153bb229860507eec587cba9e78d4584eef3b7faa8ac58c`
- resource_limits.c: `a511b516bbd8853aa65aed9cfb088a0d961eec524535f180b343dcf31e68674f`

Signed worker SHA-256:
`8cbaa02517a2e2428dfc7944e3f92d6f2135a728abea0c0cbb7e23a1e504ff21`.
All native fixture artifacts are thin ARM64, ad-hoc/hardened, empty entitlements;
private worker inventory additionally binds the captured header hash.
Confidence is high for these measured fixtures on this host. Unsupported limit
behavior, missing/late observation or provenance mismatch fails closed. Rollback
is removal of the resource include/configuration/record and these new resource
files while preserving parent-owned worker edits, including mode 13 trace-order
correction. No commits, pushes, broad integration or production approval occurred.
