# Bounded native CPython candidate

Owner-authorized disjoint implementation for #460; 2026-10-03 (Europe/Berlin).
Production remains disabled. This slice owns python_candidate.py/.c,
python_analyzers.py, python_analyzer_worker.py, managed_subprocess.py, dedicated
CPython/managed-subprocess unit tests and this contract. Shared broker/bootstrap
sources and signed modules remain parent-owned. Existing runtimes are untrusted candidate inputs, never
host-runtime admission or authenticated distribution evidence.

## CPython-only execution contract (v1)

Preparation SHALL copy a CPython 3.11, 3.12 or 3.13 ARM64 executable into a fresh
private fixture, construct an uncompressed pure-Python stdlib ZIP excluding
site-packages and cache bytes, and copy only explicitly selected native extension
inputs. No candidate input is executed during preparation. All non-system dylib
references SHALL reject this bounded fixture. Every copied image SHALL be signed
ad-hoc with hardened runtime and empty entitlements using the existing build
helper; no Developer ID or distribution trust is claimed.

A dedicated SDK-built bootstrap SHALL establish tracing before confinement,
apply deny-default Seatbelt with literal prepared code/read/map/exec paths and
ancestor metadata, then exec the actual prepared CPython path with -I -S -B,
fixed scripts and a clean environment. Existing broker exact CDHash static and
dynamic verification SHALL be reused without changing its source or protocol.
The boundary SHALL deny process creation via kernel policy, including native
os.fork, posix_spawn and unauthorized exec; Python adapters are not enforcement.

## Scenarios and evidence

Tests SHALL fail first without this implementation. Dedicated native trials
SHALL execute clean Python (exit 0), defective Python (exit 7 with expected
fixture finding), inherited fork/spawn/host-read/network/foreign-exec denials,
genuine SIGTRAP delivery, and a busy loop terminated by the broker deadline.
Each executed target SHALL have a broker exec-admission marker bound to its PID.
Timestamped Python entry SHALL occur after dynamic identity verification.
Missing loader/admission/denial evidence or wrong exits SHALL fail the candidate.

All prepared files and directories SHALL have an exact digest/mode inventory;
verify it before and after trials. Code bytes SHALL be read-only with no worker
write grant. This is worker immutability, not protection against the same host
owner changing modes/bytes during launch. That race, OS shared-cache provenance,
complete runtime dlopen/extension closure, adapters, resources, escape corpus,
all analyzers, upstream authentication, cold/offline acquisition and ordinary
customer installation remain production blockers. Static system load references
are recorded, not represented as a measured exact shared-cache inventory.

Runtime bytes and raw build/trial diagnostics SHALL remain private under
/private/tmp, outside tracked source. User output SHALL contain safe aggregate
counts and false production flags only. This maintainer fixture requires an SDK;
ordinary customer execution must eventually use a prebuilt verified fixture.
No commit, push, broad gate or shared cache writer is authorized in this slice.

## TDD evidence

Dedicated RED/GREEN and native evidence will be recorded here after execution.

## Profile version 1: explicit exception-port denial

The profile SHALL include `(deny mach-task-exception-port-set)` explicitly.
The parent's physical-host measurement found task and thread self exception-port
replacement succeeded under deny-default alone; its explicit-denial probe passed.
This is candidate evidence on that host, not an approved OS matrix. Further
swap/clear/other Mach-rights probes and macOS 14/15/26 measurements remain gates.

A second exec of the same prepared interpreter SHALL preserve the genuine traced
exec trap and terminate with signal 5; the broker SHALL not re-admit it. Native
fixed candidate scripts exercise this separately from foreign-exec errno denial.

### Measured evidence — 2026-10-03 (Europe/Berlin)

- Initial dedicated RED: `/private/tmp/python-candidate-red.log`, six tests failed
  because the implementation/bootstrap did not exist.
- Explicit Mach-profile RED: `/private/tmp/python-candidate-mach-red.log`, one
  failed, six passed before adding the requested explicit deny.
- Second-exec RED: `/private/tmp/python-candidate-reexec-red.log`, one failed,
  nine passed before the one-use replacement fixture was implemented.
- Final native GREEN: `/private/tmp/python-candidate-native-green.log`, twelve
  tests passed, including eighteen real native cases across three ABIs.
- Focused Ruff lint/format and BasedPyright: passing; type result zero errors,
  warnings and notes. Raw logs are `/private/tmp/python-candidate-lint.log`,
  `/private/tmp/python-candidate-format.log`, `/private/tmp/python-candidate-types.log`.

Physical ARM64 host OS build: **26A434** (measured from each receipt, not an OS
marketing-version inference). Profile identity:
`specfact-cpython-candidate-profile-v1`. Candidate inputs were existing UV
CPython distributions named 3.11.15, 3.12.13 and 3.13.14; source bytes are hashed
but these names do not establish authenticated upstream provenance. The actual
Python script asserts CPython and the selected ABI after broker admission.

| ABI | Native cases passed | Private raw evidence |
| --- | --- | --- |
| 3.11 | 6/6 | `/private/tmp/sf-python-pytest-ryvvdvh6/receipt.json` |
| 3.12 | 6/6 | `/private/tmp/sf-python-pytest-_duxht6i/receipt.json` |
| 3.13 | 6/6 | `/private/tmp/sf-python-pytest-dimjmxfm/receipt.json` |

Cases: clean exit 0; intentional defective calculation detected with exit 7;
actual fork/posix_spawn, host-read, immutable-script write, network and foreign
exec errno denials; genuine SIGTRAP -> signal 5; second same-image exec ->
signal 5; busy Python loop -> broker timeout, signal 9. Every case checks traced
status, PID-bound dynamic exec marker and post-verification Python entry time.
Receipts capture final signed interpreter byte/mode inventory, static ARM64
Mach-O dependencies/rpaths, exact bootstrap/profile/broker snapshots, CDHashes
and SDK/MIG inputs. Hash/mode inventories are rechecked around every trial.
Native builds compile C with `-Wall -Wextra -Werror`.

The native matrix is deliberately opt-in through
`SPECFACT_CPYTHON_CANDIDATE_INPUTS`, a JSON mapping of all three ABI names to
absolute candidate input directories. Run the dedicated pytest file with
`-o addopts=''` to avoid shared coverage/cache writers. Default dedicated tests
skip the native fixture; no customer SDK requirement is introduced. The CLI
accepts explicit `--runtime-input` and `--version`; it emits only aggregate
counts/false production flags and retains diagnostics privately.

### Limits, failure modes and next gates

Confidence: High for this bounded physical-host candidate; insufficient for
production or OS-matrix approval. These measurements assume the selected input
interpreter implements required modules as built-ins. This candidate deliberately
admits no extension `.so` or third-party dylib; a missing built-in fails the run.
The original candidate input is never launched. Prepared CPython is privately
re-signed ad-hoc/hardened with empty entitlements; no native identity is relabeled
as Developer ID, trusted upstream distribution, or a SpecFact production manifest.

- Loader closure: system references and build 26A434 are recorded; exact live
  Apple shared-cache bytes and all possible runtime dlopen paths are unproved.
  Missing/foreign dylib references and ambient rpaths reject this subset; full
  native dependency admission remains required. Only contained build-owned
  `@executable_path/../lib` rpaths are allowed.
- Substitution: workers cannot write prepared code; host-owner mutation across
  verification/exec is not eliminated by read-only modes and before/after hashes.
  Complete protected cache/substitution proof remains required.
- Escapes/resources: explicit exception-port denial is present; the parent's
  swap/clear/other Mach-rights probes, full process/IPC escape corpus, hard
  resource limits and 100-repetition lifecycle proof remain independent gates.

macOS 14/15/26 acceptance, all analyzers and process adapters, preparation/build
hooks, upstream acquisition authentication/offline reuse, ordinary-user prebuilt
installation, Linux regressions and independent review remain open. Full
production backend stays disabled; both production approval flags are false.
No shared analyzer/cache writers, broad gates, commit, push or OpenSpec archive
were run. This slice is not finalization of #460.

Measured dedicated suite duration: about 15 seconds (excluding separate earlier
preparation/build attempts). No acquisition/download or paid signing was used.
Rollback: remove these four new disjoint files; private fixture directories can
be removed after review. Read-only payload modes must be restored by the owner
for recursive cleanup; no installed runtime/cache or signed module was changed.

## Analyzer integration candidate v2 — 2026-10-03

The disjoint candidate SHALL prepare selected files from existing hash-pinned
CPython candidate venvs, validate installed distribution versions against the
ABI lock and each selected file against its installed RECORD SHA-256/size, and
freeze exact copied code/native image inventory. RECORD and lock binding are
candidate integrity evidence, not authenticated upstream wheel provenance.
Native extension/dylib closure SHALL resolve only inside prepared payload or
Apple system roots; ambient paths reject. Code and analyzer rules are immutable;
project inputs/scratch/results are separate data domains. Broker never imports
project Python. Re-sign only private prepared native images, reporting ad-hoc.

All ten existing adapters SHALL execute clean/defective fixtures in traced,
confined CPython, first 3.13 then 3.11/3.12. Managed subprocess SHALL map only
exact admitted command plans to real broker-owned execution; unknown executables,
shell, preexec_fn, arbitrary environment and descriptor inheritance reject with
actionable incomplete evidence. Never execute subprocess on the development host.

Candidate staging may restart the trusted adapter after an unresolved command
request: the controller validates exact bound argv/cwd/domain and hashes, executes
a new fixed-image broker worker and supplies its actual status/output transcript
to the restarted adapter. This is an explicit bounded request/replay protocol,
not asynchronous subprocess compatibility or fabricated analyzer output. Project
execution (pytest/CrossHair) requires separate worker domains. All stages have the
existing kernel broker deadline; longer-running stages fail incomplete. Results
are private files, not shared analyzer caches or raw stdout publication.

Requested parent-owned native API: per-worker inherited private FD3 channel,
kernel-peer-bound immutable plan-ID launch/wait/signal/cancel with owned handles,
and build-owned bounded timeout/output constants. No arbitrary client paths,
argv/env or native launch. Native ancestor messaging is unavailable in this child;
the concrete API request is retained here for parent coordination. Shared files
remain parent-owned. Production flags remain false.

Embedded external Semgrep rpaths SHALL be rejected or explicitly relocated only
when every @rpath dependency is a selected, RECORD-hash-verified bundled dylib.
Record each original/post-relocation digest and operation before private re-signing.
No host Homebrew library may resolve. This candidate relocation is not upstream
byte-identical provenance or production admission.

Analyzer candidate budget: 30,000 entries / 640 MiB, checked before mapping or
launch; production inventory defaults remain unchanged. Omit the versioned Z3
dylib alias only after proving byte equality with the selected libz3.dylib and
record its omitted-input digest. Runtime bytes remain privately copied.

The analyzer profile may read the private frozen payload tree after verifying
the complete no-link byte/mode inventory; workers receive no write grant to that
tree. Executable maps remain literal-only for the exact signed native inventory.
This avoids unbounded Seatbelt compilation from thousands of individual stdlib/
typeshed literals. Owner-level insertion races remain a production blocker.

### Explicit library-loading experiment, distinct profile identity

Actual hardened empty-entitlement CPython execution failed at pydantic-core:
macOS rejected the ad-hoc extension because mapping and mapped files have no
matching Team ID. The analyzer-only experiment may therefore explicitly select
an interpreter/engine `com.apple.security.cs.disable-library-validation=true`
entitlement, with the entitlement bytes and final signature recorded and checked.
Broker, bootstrap and dylibs retain hardened empty entitlements. The original
CPython-only fixture is unchanged. Exact native literal map grants and whole
payload inventory checks remain enforced by kernel policy; host-owner mutation
races remain unproved. Label this experiment separately; it is not empty-
entitlement compatibility, distribution trust or an approved production profile.
Default preparation SHALL retain empty entitlements; selection must be explicit.

Measured initialization denies uname/sysctl in Python ctypes and anonymous
guard-page setup in Rust/Node. The analyzer experiment permits only fingerprint
sysctls kern.ostype/osrelease/version/hostname and hw.machine/pagesize/ncpu/activecpu;
it grants no sysctl writes. The same explicitly recorded library-validation
experiment applies to the Semgrep executable because its private dylibs otherwise
fail Team-ID validation. Node executes --jitless, with no allow-jit entitlement.
BasedPyright uses explicit ABI/platform fixture arguments, not native Python
discovery via a prohibited spawn. This is bounded fixture adaptation, not general
project environment discovery support. Further syscall/IPC negative proofs gate
any approved profile.

The private bootstrap measured sysconf(_SC_PAGESIZE)/getpagesize = -1, EPERM
under the fingerprint profile; Ruff/Node/OCaml subsequently aborted. Apple XNU
registers numeric HW_PAGESIZE as hw.pagesize_compat. Add only that exact read
selector and verify native page size and actual analyzer behavior; no broad
sysctl grant follows. Primary source inspected 2026-10-03:
https://github.com/apple/darwin-xnu/blob/main/bsd/kern/kern_mib.c (published historical source; actual host behavior is measured).

Each stage SHALL expose read access only to its immutable request and private IO,
not broker authority tokens or generated build inputs. Output reads SHALL reject
non-regular/symlink files and enforce 4 MiB before decoding. Receipts SHALL bind
fixed argv/environment/profile/request bytes and header digest to native artifacts.

Semgrep's signed engine SHALL execute with the fixed `osemgrep` argv[0] identity,
selecting its real native CLI; the executable path remains exact semgrep-core.
BasedPyright's Node may select only verified interpreter-mode WASM flags under
--jitless; no JIT entitlement or executable memory grant is admitted. Unsupported
WASM builds fail incomplete. See V8 interpreter architecture (access 2026-10-03):
https://github.com/v8/v8/blob/main/docs/wasm/architecture.md.

Measured Node rejects --wasm-jitless and --expose-wasm. A trusted, inventoried
preloader MAY provide only a fail-closed WASM namespace for HTTP-library type
checks: every constructor/compile/instantiate rejects actionable unsupported WASM,
with no fabricated module, memory, instance or execution. This is an explicit
fixture compatibility adapter; actual WASM-dependent analyzers stay incomplete.

Node's fixed CLI may retain rejected eager HTTP-WASM initialization as warnings
(--unhandled-rejections=warn), preserving private stderr. WASM calls still reject;
only actual type-checker output/exit can establish fixture parity. This flag does
not admit executable memory, native processes or HTTP. Semgrep's native uname
launch is unadapted and SHALL produce incomplete evidence, never a host launch.

## Analyzer native evidence — 2026-10-03 (Europe/Berlin)

Physical ARM64 host build 26A434. All ten existing adapters were attempted with
clean/defective fixtures on CPython 3.13 first, then 3.11/3.12. Each ABI passed
8/10 adapters (16 completed cases): Ruff, Radon, AI Bloat, AST Clean Code,
BasedPyright, contracts/CrossHair, Pylint and pytest coverage. Total: 48 passing
fixture cases, 12 incomplete Semgrep cases. Semgrep clean-code/bugs execute the
actual signed native engine, then stop at unadapted native `uname -s` creation.
No host command was substituted and no clean result was fabricated. CLI exit 2
is intentional while any member is incomplete; every production flag is false.

Exact private candidate/plan/artifact/status receipts and safe summaries:

- 3.13: `/private/tmp/sf-analyzers-313-final-iicrpvjg/analyzer-receipt.json`
- 3.11: `/private/tmp/sf-analyzers-311-mx5bsxki/analyzer-receipt.json`
- 3.12: `/private/tmp/sf-analyzers-312-l2xfwaf8/analyzer-receipt.json`

Each candidate contains 94 version-bound distributions and 30 signed native
images, with 12,254 inventory entries (3.11/3.12) or 12,255 (3.13). Selected
installed files match RECORD digests/sizes; locks, original source bytes, explicit
loader relocation and final signature/inventory bytes are retained separately.
This is not authenticated wheel hash/provenance proof. Source and payload bytes
can differ after documented relocation/signing; no identity misrepresentation.
All runs explicitly selected `cpython-analyzers-library-loading-v1`, never the
default empty-entitlement profile. Actual profiles/argv/clean environment/request
and header digest are bound into each native result. Fixed fixture adaptation
uses the compiled clean environment, not general caller-selected environment
semantics; live environment/stream/async compatibility is not admitted.

Focused final unit evidence: 23 passed / 1 opt-in native test skipped; with native
inputs selected, CPython suite 12 passed including 18 actual native executions.
Ruff focused lint passes; BasedPyright focused types: 0 errors/warnings/notes.
RED evidence includes `python-analyzers-output-red.log`, `-cli-red.log`,
`-node-red.log`, `-node-warning-red.log`, `-native-spawn-red.log` and original
CPython RED logs under private `/private/tmp`. Final logs: `python-analyzers-
unit-final.log`, `python-analyzers-lint-final.log`, `python-analyzers-types-
final.log`, `python-candidate-native-recheck.log`. No broad/shared cache gates.

### Concrete remaining implementation/API boundary

The staged run adapter needs no shared protocol change for these fixed fixtures.
The next parent-owned API is an inherited private peer-bound FD channel accepting
only immutable build-owned plan IDs, with owned-handle wait/signal/cancel, real
bounded output/deadline status and no arbitrary executable/argv/environment.
Semgrep additionally needs a reviewed native-engine process adapter or pinned
engine rebuild removing its bootstrap shell-out; protocol extension alone cannot
adapt an unmodified OCaml native process call. Do not grant fork/host uname.
Popen streams/async semantics fail with actionable ENOTSUP, not emulation.

Production blockers remain: default library identity compatibility, owner mutation
races, complete OS-specific exception/Mach-rights escapes and resource bounds
(including disk output), full analyzer error/parity proof, authenticated upstream
provenance, and prebuilt ordinary-customer installation. Parent/Sagan own broader
parity, resources and shared native control changes; none are integrated here.
No shared control source, signed module, commit or push was changed by this slice.

Owned files are exclusively: `scripts/macos_managed_boundary/python_candidate.py`,
`python_candidate.c`, `python_analyzers.py`, `python_analyzer_worker.py`,
`managed_subprocess.py`, `tests/unit/test_macos_python_candidate.py`,
`tests/unit/test_macos_managed_subprocess.py`, and this `CPYTHON_CONTRACT.md`.
Private cleanup is reversible: remove these fixture roots after evidence review;
read-only payload modes may require owner chmod. Keep retained receipts first.

Final alternative probe used the same signed engine with fixed offline core CLI
`-json -rules <bound rule> -lang python -j 1 <fixture>`. It also exited 1 before
output at the same native `uname -s` bootstrap. Thus selecting the offline core
CLI alone does not resolve the process-adapter blocker. Private actual artifact
receipt: `/private/tmp/sf-analyzers-313-1_zsz73h/core-probe.json`.

## Semgrep immutable distribution adapter v2 — 2026-10-03

Use plan ID `semgrep-1.175.0-offline-ca-v2`: bind SSL_CERT_FILE to the exact
RECORD/inventory-pinned private certifi/cacert.pem. Reject missing, symlinked or
changed certificate bytes. The clean compiled environment SHALL never inherit
NIX_SSL_CERT_FILE, OCAML_EXTRA_CA_CERTS, proxies or arbitrary SSL_CERT_FILE.
Preserve deny-default, explicit exception-port denial and absent process-fork
grants; no uname/security executable is copied, admitted or replayed.

Source inspection identifies native certificate initialization through
Conduit/ca-certs; published ca-certs v1.0.3 system_trust_anchors checks
SSL_CERT_FILE before uname/security. This tag is source evidence, not an asserted
compiled dependency version. Pin the actual engine digest and verify measured
behavior; manifest captures system/machine using trusted platform evidence,
without spoofing uname. No engine binary patch or platform result fabrication.
Primary source accessed 2026-10-03:
https://github.com/mirage/ca-certs/blob/v1.0.3/lib/ca_certs.ml.

Require native 14/14 reference-semantic cases using Sagan's read-only pinned
versioned result adapter and actual in-boundary discovery (invalid-rule included),
plus actual all-ten clean/defective matrices on CPython 3.13/3.11/3.12. Reference
receipts must bind exact assets/fixtures; never synthesize scan results.

A dedicated immutable bootstrap negative plan SHALL attempt native fork and
posix_spawn of the already-bound prepared target after policy installation.
Both must return EPERM before the admitted exec; unexpected owned child creation
must be killed/reaped and fail the probe. No host executable is attempted. This
probe is opt-in test-only and shares the actual Semgrep policy/image admission.

The selected CA bundle additionally SHALL match the explicit reviewed certifi
bundle SHA-256 `9cc2a774b5198dcff14d9be1e66091f538975d867ce029a96bce15a55dfd730f`;
a self-consistent altered inventory/RECORD cannot authorize different CA bytes.

## Semgrep resolution and native GREEN — 2026-10-03

The previous uname/native-engine blocker is RESOLVED for the fixed offline
candidate plans. Configure the exact pinned private CA bundle via SSL_CERT_FILE;
no engine/source patch, fake platform answer, extra executable admission or host
subprocess is needed. Trusted platform.system/machine evidence is captured in
each freshly prepared candidate manifest. The engine original-input digest,
private relocation/signature identities, certifi digest, plan ID, compiled
argv/environment/profile and actual broker status remain distinct and recorded.

| ABI | All-ten adapters | Clean/defective cases | Semgrep reference semantics |
| --- | --- | --- | --- |
| 3.13 | 10/10 | 20/20 | 14/14 |
| 3.11 | 10/10 | 20/20 | 14/14 |
| 3.12 | 10/10 | 20/20 | 14/14 |

Actual native private receipt roots, each containing candidate.json, per-stage
native-result.json, analyzer-receipt.json, semgrep-reference-receipt.json and
separate safe summaries:

- `/private/tmp/sf-analyzers-313-bc2tuvce`
- `/private/tmp/sf-analyzers-311-o89l4326`
- `/private/tmp/sf-analyzers-312-f34p5sh3`

Reference proof uses the exact pinned Sagan source helper
SHA-256 `471977480df00f50a7f3e624802db9d964f2afad0a9f6c01707e803ab51be45e`
and golden reference SHA-256
`efbae0e733db2ea821702d36f9dfdd377194a22f11335f4208d4a233a76075f8`.
The helper is read/imported only; its host launcher/cache writers never run.
Both discovery and scanning execute through the signed traced broker. All
findings, locations, messages, suppression/nested rule IDs, selected target
semantics, return status and COMPLETE error structures match the versioned
reference adapter. Invalid-rule raw native exit 7 remains recorded; existing
pinned legacy result adaptation produces reference exit 2 using actual in-boundary
discovery. This is 14/14 versioned reference-semantic proof, not a claim that
raw Python/native frontend behavior is identical. Actual positive controls pass.

Native process proof: dedicated C bootstrap attempts fork and posix_spawn of its
already-bound prepared target AFTER policy installation. On each ABI both return
EPERM; the admitted signed native engine then reports version 1.175.0 under the
same broker/profile. Final dedicated native suite: 17 tests passed, including
three real per-ABI process-denial launches (six denied creation attempts).
Evidence `/private/tmp/python-analyzers-process-final.log`; each raw negative
probe/artifact receipt lives under private `sf-semgrep-denial-*` roots.

Final focused unit checks: 27 passed, 2 opt-in native tests skipped. With native
CPython inputs selected, 12 passed including 18 actual executions. Focused Ruff
lint and BasedPyright types pass. RED logs: `python-analyzers-ca-red.log`,
`python-analyzers-reference-red.log`, `python-analyzers-process-red.log`,
`python-analyzers-ca-pin-red.log`. GREEN logs: `python-analyzers-ca-unit.log`,
`python-analyzers-ca-lint.log`, `python-analyzers-ca-types.log`,
`python-analyzers-process-final.log`, `python-candidate-native-final.log`; all
under private `/private/tmp`. Native CLI receipts return 0 only when all ten
adapters AND all 14 reference cases pass. Runtime/source fixtures stay untracked.

This continuation changes only python_analyzers.py, python_candidate.c,
test_macos_managed_subprocess.py and this contract. No shared native control,
Sagan parity/dependency files, signed module, commit/push or cache writer changed.
No parent protocol extension is required for these fixed Semgrep plans; inherited
channel/owned-handle APIs remain future live async/stream integration work.
Production still false: the library-validation experiment remains explicit and
separate, and OS matrix/escapes, complete resources/owner-race proof, upstream
provenance and ordinary-customer prebuilt delivery remain parent integration gates.
Confidence high for these measured fixed cases on ARM64 build 26A434, not a
production assurance claim. Retain private receipts before owner cleanup.
