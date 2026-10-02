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
