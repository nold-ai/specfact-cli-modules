# Native candidate dependency evidence

Owner-authorized disjoint dependency task, 2026-10-03 (Europe/Berlin).
This contract precedes tests and changes. It grants no production admission.
Shared specs/TDD, signed modules and registry remain parent-owned.

## Exact policy and distribution evidence

Candidate input audits SHALL bind the full reviewed analyzer version map, native
candidate pins and core security floors separately. Released Semgrep 1.144.0 and
candidate 1.175.0 are incompatible identities, never interchangeable. No version
relabeling, prohibited Python BasedPyright/nodejs-wheel-binaries installation,
resolver bypass or policy exception is permitted.

The npm audit SHALL authenticate the committed BasedPyright archive integrity
before parsing, verify its package name/version/license and dependency metadata,
and hash every packaged license/notice. Node provenance remains the existing
packager's responsibility. Optional fsevents omission is explicit; no required
npm dependency may be silently omitted. Audit receipts always retain
production_eligible=false and dependency_admitted=false.

## Semgrep rule layout and negative controls

The fixed parity matrix SHALL additionally exercise approved rule bytes at
.semgrep/clean_code.yaml and .semgrep/bugs.yaml on clean/defective/nosem fixtures.
It SHALL preserve exact emitted rule IDs; path-induced namespace differences
are admission failures. Existing root-path cases, parse error and invalid rule
remain mandatory. No rewriting, finding filtering, exit mapping or target-list
normalization may turn equal failures into acceptance. Identical invalid-rule
exit 2 responses SHALL not pass: the pinned expected native rule-parse exit is 7.
The receipt SHALL expose matched/required case counts and explicit policy drift;
fixture parity alone cannot imply candidate dependency admission.

## Z3 proof-carrying sidecar

The existing deterministic metadata-only correction SHALL remain byte-identical.
Its provenance sidecar SHALL verify the serialized output RECORD and compare all
members with the authenticated upstream mapping. Exactly METADATA/WHEEL/RECORD
may differ; renamed dist-info members are compared by their original identity.
The sidecar SHALL bind every unchanged member's digest/size and every retained
license's digest. Missing license payloads are explicit admission gaps. Altered source/native/license
bytes or extra members reject provenance rather than asserting preservation. No input code runs.

## Evidence and limits

RED/GREEN and actual native probes belong in private ignored logs. Focused gates
only; no ambient tool installation, concurrent analyzer cache writers, CodeRabbit
upload, broad Hatch quality, commits or pushes. Full security/license admission,
managed boundary, production version policy, Linux parity and supported-OS/final
signed distribution acceptance remain separate parent gates.

### Measured missing-license correction

The authenticated 42-member upstream Z3 wheel has MIT metadata but **no license
file**. The provenance contract therefore records `license_payload_complete=false`
and the concrete admission gap instead of preventing the already approved
metadata correction. It SHALL NOT claim preserved license bytes when none exist,
insert license text into the wheel, or change its known digest. Empty supplied
license files still reject provenance. Missing-license tests precede this amendment's
implementation. A separately authenticated redistribution license payload remains
required for eventual admission, including the wheel's bundled Windows DLLs.

## Dependency-task handoff — 2026-10-03 (Europe/Berlin)

Changed implementation: native_semgrep_parity.py, native_z3_wheel.py and new
native_analyzer_inputs/candidate_policy.py, with their focused tests and the native
input README. No signed module/manifest/registry, shared spec/TDD, production
backend or parent boundary file was edited by this dependency task.

Private ignored evidence directory:
`.specfact/native-compat/dependency-task-20261003/` (mode 0700).
`commands.json` binds final exact argv/cwd/status and UTC timestamps;
`source-sha256.json` binds the final seven script/test/runbook sources.
`facts.json` and captured core policy sources retain the complete security-floor,
trust-register/checker and three installed distribution inventories. Logs are
not public review or production authority.

- Initial RED: 6 failed, 39 passed, 7 missing-implementation errors, 11 subtests.
  `red.log` retains the exact meaningful failures; contract preceded tests.
- Missing-license amendment RED: 1 failed / 22 passed (`license-red.log`).
- Semgrep METADATA hash-binding RED: 1 failed / 22 passed, 11 subtests
  (`metadata-red.log`). Same-version altered dependencies now reject before launch.
- Final GREEN: 109 passed, 18 subtests; pytest used `-B -p no:cacheprovider -o
  addopts=` on only the dependency/parity, smoke and Node packager test files.
  `green.stdout` and `commands.json` retain exact invocation and exit 0.
- Touched-file Ruff check, format and BasedPyright exit 0 (zero errors/warnings);
  strict native OpenSpec validation exits 0. No broad Hatch quality was run.
- Actual native prior-layout probe: 9/14 matched. Python emitted `semgrep.*`,
  native `.semgrep.*` for four nested defect/nosem cases (`layout-red.json`).
  Literal rule IDs via the upstream command option yield **13/14** matching cases
  (`parity.stdout`, exit 1). Original root matrix remains **7/8**.
- Invalid-pattern rule remains Python **exit 2 / scanned [fixture.py]**, native
  **exit 7 / scanned []**. Both raw outputs remain; no status mapping, namespace
  postprocessing, ignored errors, changed distribution or downgraded pin was used.
- Offline npm audit authenticates archive SHA-512, records exact metadata and
  two license payloads (BasedPyright MIT and bundled typeshed third-party text),
  and explicit fsevents omission. Released full ten-analyzer map still expects
  Semgrep 1.144.0, candidate 1.175.0. `npm.stdout` captures both exact drift entries.
  Core requires Semgrep >=1.175.0 / MCP >=1.28.1; candidate MCP is 1.29.0.
- Actual CPython 3.11.16, 3.12.14 and 3.13.14 ARM64 runs each pass all ten real
  clean/defective adapters. All three normal dependency checks exit 0 and inventory
  94 distributions; PyPI BasedPyright/nodejs-wheel-binaries are absent. Z3 reports
  native runtime 5.1.0 and distribution 5.1.0.0+specfact.1. Exact commands and outputs
  are cp311/cp312/cp313 smoke, inventory and pip-check logs in the directory.
- Actual Z3 rebuild remains SHA-256
  `af669755eabd97268a4141983a391cb4a832116d5a2c3cf04a4c53c7650ce72c`.
  `z3-provenance.json` binds all 39 unchanged members and accurately reports zero
  upstream license files. The existing metadata correction was not reworked.
- Required explicit-file SpecFact review exits **1**, verdict **FAIL**, assurance
  **UNKNOWN**, zero findings: all ten analyzer diagnostics are
  `unsupported_controller_platform`. This remains an unresolved parent review
  gate; no CodeRabbit upload or claim of clean-code gate completion was made.

### Exact outstanding admission gaps

1. Pinned Semgrep 1.175.0 invalid-rule exit/scanned-target discrepancy. Resolving
   it needs a genuinely compatible distribution/frontend contract with new exact
   pins and probes; receipt normalization or security-floor downgrade is prohibited.
2. Released version policy and candidate distribution mismatch (1.144.0 versus
   1.175.0). Parent owns production policy changes and exact Linux/cross-version
   semantic evidence; this task only exposes the drift.
3. Z3's MIT metadata supplies no license text; the wheel also bundles Windows DLLs.
   Authenticated redistribution/license closure is still missing. No source/native
   bytes or license files were silently added/removed to hide that gap.
4. Entire 94-distribution/Node/npm/native closure still needs final artifact-bound
   security/license/build-origin admission and approved signed manifests. npm
   authentication/known optional omission and pip check alone cannot confer it.

Managed boundary/control/resource proof, production adapters/acquisition, supported
OS/macOS/Linux acceptance and final customer installation remain parent-owned.
No production eligibility, commit, push, release or archive is granted here.

Confidence: High for these exact physical-host fixtures/digests; wider admission
is incomplete. Assumptions: fixed distributions/rule bytes, current released map
and controlled one-shot npm use; changing them requires fresh evidence. Missing or
changed metadata/licenses fail or remain an explicit gap; malformed/missing native
output never passes; ordinary process-group cleanup is not a managed boundary.
Runs take seconds to tens of seconds on this host, with no new service/tool cost.
Rollback is limited to this task's eight changed/new files and private evidence;
retain or restore parent-owned concurrent work independently.

Source consulted 2026-10-03: pinned [Semgrep v1.175.0 Scan_CLI.ml](https://github.com/semgrep/semgrep/blob/v1.175.0/src/osemgrep/cli_scan/Scan_CLI.ml).
The authenticated local distribution's commands/scan.py and config_resolver.py
also document `--no-rewrite-rule-ids`; the actual native probes above establish
its effect on these fixed cases, not arbitrary policy equivalence.

## Owner-authorized versioned compatibility continuation

2026-10-03: the owner explicitly authorizes a versioned native admission adapter
for released result semantics and authenticated upstream Z3 license/provenance
inputs. This supersedes the earlier prohibition on explicit status adaptation;
raw frontend comparison remains unchanged and is never relabeled as equivalent.

### Semgrep discovery/error adapter v1

`specfact-semgrep-1.175.0-legacy-result-v1` SHALL retain raw native exit/stdout/stderr
and independently execute the pinned native `--x-ls` target-discovery mode with the
same exact target/config/selection controls before the native scan. This internal
upstream option is bound to exactly 1.175.0 and requires a new contract for any
upgrade. Discovery is not parsing/matching; the protocol SHALL distinguish both.
Only a native exit 7 with zero results/scanned targets and exclusively structured
Rule parse errors (code 2, level error) may become legacy-result exit 2. It SHALL
retain each complete error (including code/message), use actual discovered paths
for the legacy `paths.scanned` field, and expose `analyzed_targets=[]` and
`legacy_scanned_means=selected_targets_on_rule_failure`. It SHALL NOT invent paths,
run a replacement successful scan, drop errors or turn failure into clean evidence.
Missing/failed/duplicate/outside discovery, malformed/mixed error types, changed
version, unexpected findings/targets or an invalid adapter schema reject adaptation.
Native positive/parse cases are passed through without semantic changes.

Both raw and versioned-adapter matrices SHALL be recorded. Admission conformance
requires every adapted case to match the pinned Python reference's exact semantic
findings/errors/scanned paths and return status with independent positive controls;
it does not require raw frontend identity and grants no production/sandbox proof.
Full error code/message comparisons SHALL apply to both matrices. Raw 13/14 is
retained as historical measured difference, not hidden by the adapter's result.

### Proposed version policy

The candidate inputs SHALL freeze a **proposed**, full ten-member analyzer map
with Semgrep-clean and Semgrep-bugs 1.175.0 plus this exact adapter schema. The
released 1.144.0 map remains separately identified. Candidate admission SHALL
explicitly require the parent to update every production producer/consumer/lock/
profile policy and validate Linux/portable semantics later; it must never assert
that the released map has already changed or label 1.175.0 results as 1.144.0.

### Authenticated supplemental Z3 license

Store the unmodified LICENSE.txt from official z3-5.1.0 at full tag commit
0b6cdcdbc65da25ef0f73ac9da210574d0f66cf8 as a reviewed repository input. Bind its
SHA-256/Git blob identity, verified GitHub commit signature, exact upstream wheel
hash, METADATA identity, tagged version/source byte linkage and the published
ARM64 release archive digest. Admission checks SHALL authenticate that archive
and compare the wheel's native dylibs/executable/Python/header members against
its actual bytes; a tag name or MIT string alone is insufficient. Changed license,
metadata, archive digest, incomplete linkage or any mismatched member rejects.
The supplemental license is separate from the byte-identical corrected wheel;
provenance SHALL accurately distinguish missing in-wheel text from supplied text.

Supplemental Z3 MIT evidence SHALL explicitly exclude Microsoft VC runtime DLLs
from its license coverage. Any unverified bundled toolchain terms remain named
admission gaps; no MIT assumption may cover those third-party bytes. Complete
closure/production admission stays false until the parent supplies all remaining
artifact-bound policy/boundary/toolchain evidence.

## Completed concrete continuation — 2026-10-03 (Europe/Berlin)

This section supersedes the earlier dependency-task outstanding items 1–3 for
**candidate** adapter/proposed policy/Z3 source-and-native license evidence.
It does not authorize production policy changes or admit the complete closure.

### Implementation and exact evidence

- The versioned native protocol actually passes **14/14** on the physical Darwin
  ARM64 host. Raw frontend comparison remains **13/14**, with both independently
  correct raw error positive controls: reference exit 2 / selected fixture and
  native exit 7 / no scanned target. The protocol retains raw exit/JSON/stderr,
  performs actual pinned native `--x-ls` discovery and preserves the reference
  selected-target semantics separately from `analyzed_targets=[]`. Invalid-rule
  result is still a rule failure, never a clean scan. Complete error arrays are
  compared, including code/message/columns/offsets. The CLI exits 0 for protocol
  conformance; the schema-2 receipt still exposes raw `passed=false` and separate
  `adapter.passed=true`. These fields are not interchangeable.
- Frozen reviewed `candidate-version-policy.json` explicitly proposes Semgrep
  1.175.0 for both members and the new adapter, with the full ten-member version
  map. Candidate policy reports its exact input digest, original released map
  (1.144.0), proposal-only status and required future parent policy updates.
- `Z3-LICENSE.txt` is the **unmodified 1,096-byte upstream text**, SHA-256
  `e617cad2ab9347e3129c2b171e87909332174e17961c5c3412d0799469111337`.
  Reviewed `z3-license-provenance.json` binds full official tag commit
  `0b6cdcdbc65da25ef0f73ac9da210574d0f66cf8`, Git blob
  `cc90bed7477d0809f4309b718e920d411e1f3da8`, GitHub's verified commit-signature
  observation, wheel metadata digest, tagged source/version and ARM64 release.
  Authentication is an explicit reviewed-input pin plus HTTPS/GitHub primary
  source evidence, not a claim of locally reproduced native compilation.
- Downloaded ARM64 release ZIP is authenticated before parsing against upstream
  published SHA-256
  `81d29e934fd863079a74af35eecaeaef8047e0e12414d33ca322b358d68383db`.
  Its license bytes equal the tagged Git blob. The new checks compare **28**
  wheel native/Python/header members against actual release bytes, including both
  dylib filenames and bin/z3. Tagged `z3.py` also matches the wheel byte-for-byte.
  Missing/changed metadata, license/provenance, source or release member rejects.
- Licensed preparation emits the verified supplemental license alongside the
  unchanged corrected wheel and a schema-3 sidecar. Captured license bytes are
  reauthenticated before exclusive output creation and never reread unverified
  for delivery. Supplemental text must accompany the final signed redistribution;
  ordinary wheel installation alone still does not install it. Wheel SHA-256
  remains `af669755eabd97268a4141983a391cb4a832116d5a2c3cf04a4c53c7650ce72c`.

Private ignored continuation evidence:
`.specfact/native-compat/dependency-task-20261003/continuation/`.
`commands.json` binds exact final argv/cwd/UTC starts/statuses, and
`source-sha256.json` binds the ten script/test/reviewed-input/runbook files.
`adapter.stdout`, `policy.stdout`, `z3-provenance-final.json`, source/tag/release
records and wheel/delivered-license digest files preserve the measured facts.
`semgrep-primary-source-linkage.json` authenticates fetched source/tests to full
v1.175.0 commit `7963c5a2d7e784ab24d0c14e29c63c6d53751336` and its exact Git tree;
installed output.py/error.py bytes match those upstream files.

Failing-first continuation: `red.log` records 15 failures, 73 passes and 22
subtests (including absent adapter/license/proposed-map behavior and lost error
messages). `freeze-copy-red.log` records 2 failures / 35 passes for frozen-policy
identity and verified output-license copying; `error-structure-red.log` and
`raw-control-red.log` each record one meaningful failing regression. Final focused
GREEN is **122 passed, 26 subtests**. Ruff check/format and BasedPyright all exit 0
with zero errors/warnings; strict OpenSpec validation exits 0. Exact real adapter,
policy and authenticated Z3 preparation commands exit 0. SpecFact explicit-file
review still exits 1 / FAIL / UNKNOWN with zero findings and all ten diagnostics
`unsupported_controller_platform`; that parent gate is not passed or waived.
No broad gates, shared analyzer cache writers, ambient installs, CodeRabbit upload,
commits, pushes or parent Mach/image/boundary edits were performed.

### Precise remaining complete-closure/toolchain obligations

The Z3 MIT text is **not** applied to unmatched third-party or Windows bytes.
Exact upstream hashes/sizes are recorded for the ten unlinked .dll entries in
`z3-license-provenance.json` and every generated licensed sidecar:

- z3/lib/libz3.dll (Windows Z3 binary release/source linkage not verified here).
- z3/lib/msvcp140.dll, msvcp140_1.dll, msvcp140_2.dll,
  msvcp140_atomic_wait.dll, msvcp140_codecvt_ids.dll.
- z3/lib/vcomp140.dll, vcruntime140.dll, vcruntime140_1.dll,
  vcruntime140_threads.dll.

Those nine VC runtime entries still need exact Microsoft runtime provenance and
redistribution-term evidence; a Z3 MIT string cannot supply it. These files remain
unchanged in the source/corrected wheel. The parent must either authenticate their
terms/provenance for actual distribution or explicitly approve/test a native-only
payload assembly with correct metadata/integrity; this task does neither silently.

The exact **94 Python name/version entries**, declared-license metadata and actual
installed license-file paths are recorded in
`python-closure-admission-inventory.json`. Final vulnerability/security/license
admission for that closure, CPython/Node native build/linked-library provenance,
final authenticated artifact manifests, producer/consumer policy adoption and
Linux/portable acceptance still remain parent gates. This inventory records
uncompleted admission; declaration or license-file presence is not a legal or
security approval. Native controlled adapter compatibility already passed on the
three candidate ABIs in the preceding checkpoint; it is not an OS support matrix.

Confidence: High for exact candidate protocol/source/native license evidence.
Assumptions: the pinned distribution, internal discovery option and fixed-input
selection remain unchanged; any upgrade requires new conformance. Discovery
failure/mixed errors reject the adapter, source/license changes reject linkage,
and omitted supplemental license or unauthenticated toolchain terms still block
redistribution admission. Rollback concerns only the dependency task's eleven
files and private evidence; preserve concurrent parent work. No production
eligibility or complete clean-code gate is claimed.

Primary sources inspected 2026-10-03:
[Semgrep pinned scan/discovery source](https://github.com/semgrep/semgrep/blob/7963c5a2d7e784ab24d0c14e29c63c6d53751336/src/osemgrep/cli_scan/Scan_subcommand.ml),
[Python target-output semantics](https://github.com/semgrep/semgrep/blob/7963c5a2d7e784ab24d0c14e29c63c6d53751336/cli/src/semgrep/output.py),
[pinned rule error tests](https://github.com/semgrep/semgrep/blob/7963c5a2d7e784ab24d0c14e29c63c6d53751336/cli/tests/default/e2e/test_rule_parser.py),
[Z3 tagged license](https://github.com/Z3Prover/z3/blob/0b6cdcdbc65da25ef0f73ac9da210574d0f66cf8/LICENSE.txt),
[Z3 release](https://github.com/Z3Prover/z3/releases/tag/z3-5.1.0),
[exact wheel metadata](https://pypi.org/pypi/z3-solver/5.1.0.0/json).
