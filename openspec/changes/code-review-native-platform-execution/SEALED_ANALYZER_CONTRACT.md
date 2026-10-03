# Sealed native Semgrep fixture acceptance

Before production integration, run the actual pinned native Semgrep core against
fixed clean/defective local-rule fixtures from a traced native bootstrap and a
deny-default Seatbelt profile. No customer code or paths are accepted. Reuse the
startup launchd owner, strict ad-hoc/hardened signing and independent observer.
The worker must establish tracing, close inherited non-stdio descriptors, clear
ambient environment and apply confinement before exec of the sole pinned core.
The profile grants verified core/rule/CA inputs, Apple system libraries, private
temporary storage and observation output; deny process creation and network.
Successful clean analysis and expected defect findings must both execute. A
startup/policy/loader failure is incomplete evidence, never a clean result.
Preserve actual tool JSON and process exits. This proves the sealed analyzer
subset only: it does not admit manager/build hooks, Python adapters, native error
parity, full broker protocol or supported customer installation. All receipts
remain production=false and complete_boundary=false. Maintainer compilers are
not a customer requirement.

The tracer must deliver ordinary worker signals with their original semantics;
only verified startup/exec stops are control transitions. Unknown signal stops
cannot silently discard the signal or turn a finished/crashed worker into timeout.

Loader compatibility grants may include opening the root directory itself for
libignition's openat bootstrap; this is a literal directory grant, not recursive
host-file access. Before the scan, the exact analyzer profile must prove denial
of a known-readable host fixture outside its inputs, direct process creation,
network connection and signaling the broker. Such failures prevent acceptance.

All seven bundled Semgrep dylibs must match bytes from the existing hash-pinned
ARM64 wheel, pass strict native signature verification and appear in the receipt.
The sandbox grants only those literal dependency files, never Homebrew fallbacks.
Corruption or an unlisted library rejects execution before launch. This fixture
preflight does not prove atomic verification-to-launch or release authentication.

Canonicalizing approved inputs may inspect only their ancestor-directory metadata.
Grant no content reads or writes to host ancestor directories. The known-readable
host-file denial control must continue passing under this loader/path profile.

Acceptance also requires the pinned analyzer version and exact expected rule ID,
fixture path and line; suffix matching or an unrelated finding cannot prove the
defective control. Positive clean/defect controls accompany negative receipt tests.

Read the policy once into an immutable byte snapshot before cases; use those
bytes for every launch and its receipt digest. Preserve actual terminating signal
identity as a negative process status. Registration failures/timeouts still require
job removal, because a failed controller command may have registered the job.

Require all four named clean/defective rule-pack cases in the receipt; an empty
case set cannot pass by vacuous truth. Negative execution/error/target tests use
an otherwise valid pinned version so they exercise their intended failure.

Repeat the fixed analyzer execution with spaces and Unicode in its private fixture
root; record the actual exercised case paths. This is local path-handling proof,
not the separate cold-acquisition/default-protection customer installation gate.

Source provenance describes the bytes actually compiled or loaded. Copy native
sources into the private build directory before compilation and retain the digest
of that snapshot; later edits to checkout sources must not relabel tested binaries.
Imported helper modules execute their captured byte snapshot. Do not claim a
post-execution read of a controller file identifies the code already executed.

## Physical-host result, 2026-10-03 (Europe/Berlin)

All four cases passed on ARM64 Mac17,9, macOS 27.0.1 build 26A434 with
ad-hoc/hardened native bootstrap signing and no additional entitlements:

| Case | Core exit | Expected result | Measured |
| --- | --- | --- | --- |
| Clean-code clean | 0 | No findings | Passed |
| Clean-code defect | 0 | print-in-src at fixture.py:2 | Passed |
| Bugs clean | 0 | No findings | Passed |
| Bugs defect | 0 | specfact-bugs-eval-exec at fixture.py:2 | Passed |

Each execution also passed forbidden host-file, process, inherited-descriptor,
network and broker-signal probes before the core executed. The core's seven
bundled library identities are recorded in the ignored local receipt. All case
paths included spaces and Unicode. Profile and compiled-source provenance use
the exact captured inputs. This proves two analyzer members on this physical
host; it does not approve the candidate 14/15/26 OS matrix, ten-member pipeline,
manager corpus, verified artifact acquisition or independent-Mac installation.

## Missing stderr diagnostic contract — 2026-10-03 (Europe/Berlin)

A bounded scan timeout SHALL raise the sealed analyzer timeout diagnostic with
the service identity and the last 4000 characters of available events and stderr.
If launchd has not created the stderr file, use an empty stderr tail; a missing
optional diagnostic file SHALL NOT replace the timeout with FileNotFoundError.
A completed scan SHALL likewise retain its actual status, payload and boundary
checks when stderr is absent, recording an empty stderr string. Only a missing
file is optional; other read failures SHALL propagate. Job cleanup remains
mandatory on completion and timeout, and missing scan/boundary evidence still
fails acceptance.

### PR489 diagnostic regression evidence

Independently confirmed saved review comment 4170800535 (thread
PRRT_kwDORVEFbs6ohyts). Tests reproduced missing stderr masking the timeout and
completed-case reporting before production changes. Tests cover event/error
tail limits, exact service identity, completed payload/status and cleanup on
timeout/completion.

Focused verification used Python 3.14.7 / pytest 9.1.1 on Darwin, 2026-10-03
(Europe/Berlin). Command: `hatch run python -m pytest
tests/unit/test_macos_sealed_analyzer.py tests/unit/test_native_analyzer_smoke.py -q`.
The combined failing-before run exited 1: 6 failed / 45 passed (including two
Node subtest failures). The final passing-after run exited 0: 49 passed in
1.29 seconds. Exact logs: `/private/tmp/specfact-pr489-analyzer-smoke-review/red.log`
and `/private/tmp/specfact-pr489-analyzer-smoke-review/green-final.log`.

Touched-file checks exited 0: `hatch run ruff check --no-cache <four Python files>`,
`hatch run ruff format --no-cache --check <four Python files>`, and
`hatch run type-check <four Python files>` (0 errors, 0 warnings, 0 notes).
Logs are `ruff-check.log`, `ruff-format.log`, and `type-check.log` in the same
private evidence directory. The four files are the analyzer and smoke scripts
and their corresponding unit-test files.

The scoped SpecFact review (`--enforcement changed --bug-hunt --json`) exited 1:
all ten required analyzer records report `unsupported_controller_platform`;
assurance is UNKNOWN, not a clean review. Exact evidence is
`specfact-review.json` and `specfact-review.log` in that directory. Supported
controller review remains a parent gate. These mocked diagnostic tests and local
POSIX worker tests do not establish fresh native analyzer, signed-boundary or
customer-support acceptance.
