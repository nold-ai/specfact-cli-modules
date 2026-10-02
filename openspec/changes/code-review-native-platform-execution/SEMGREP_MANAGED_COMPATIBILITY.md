# Bounded native Semgrep frontend parity

## Acceptance contract (specified before tests and implementation)

This is owner-authorized fixed-fixture feasibility work under the existing native
platform execution change. It does not implement startup ownership, production
selection, module delivery, or the managed sandbox. `production_eligible=false`,
`sandbox_verified=false`, and `single_process_verified=false` are mandatory even
when all parity cases pass. No customer repository or code is accepted as input.

The harness SHALL execute only the pinned CPython 3.13 local Python Semgrep
frontend and Semgrep 1.175.0 core in `.specfact/native-compat/venv`, with approved
local `clean_code.yaml` and `bugs.yaml` bytes copied into private fixtures. It
SHALL check absolute paths, executable permission, bounded regular-file sizes,
SHA-256 pins, and distribution version before execution. Interpreter symlinks
are permitted only for the pinned venv interpreter; rule/core/frontend symlinks
and symlinked fixture inputs are rejected. Digests identify locally reviewed
candidate bytes, not publisher authentication or the complete dependency closure.

Native launch SHALL use `argv[0]=osemgrep` with `Popen(executable=<verified core>)`,
then `scan --experimental --oss-only --jobs=1 --metrics=off --disable-version-check
--novcs --no-git-ignore --project-root <fixture> --disable-nosem --json --config
<approved local rule>` and fixed explicit targets. The Python frontend SHALL use
its explicit pinned interpreter and console script, the same scan controls, and
`--legacy` to bind the Python frontend, and no experimental flag.
A digest-verified local certifi CA bundle SHALL be passed explicitly: native
startup otherwise attempts a PATH-resolved macOS keychain helper even for local
rules. This is a fixed dependency input, not a customer configuration. Neither command accepts extra arguments or shell text.

Malformed-Python control SHALL use an incomplete call with an unterminated
string; parser recovery returning no error is a control failure. Error controls
SHALL require syntax/partial-parsing or rule-parse errors, respectively.

Scenarios SHALL cover both rule packs on clean, defective, and nosem-comment
fixtures, plus malformed Python and an embedded benign invalid-pattern rule.
Canonical findings SHALL preserve every rule id, fixture-relative path, start
and end line, message, and severity, including duplicates. Sorting and converting
absolute fixture paths to relative paths are allowed; suffix rewriting, finding
filtering, deduplication, and hiding errors are prohibited. Canonical errors
SHALL retain type, level (the pinned JSON error severity field), path and line when present. Successful cases SHALL
reconcile the complete scanned target list. Exit statuses SHALL match exactly.
Independent positive controls SHALL require the expected defect (rule/path/line)
and zero clean findings; equal empty responses must fail defective cases.
Missing/malformed JSON, evidence, rules, targets, version, errors, output bounds,
or timeout SHALL reject acceptance. Material differences SHALL remain in the
receipt and SHALL set `passed=false`; they must not be normalized away.

Each launch SHALL have a fixed 30-second timeout and reuse the smoke runner's
exit observation and process-group cleanup before reaping the leader. Captured
stdout/stderr SHALL be bounded at the existing 16 MiB smoke limit. Private HOME,
PATH and temp directories SHALL isolate ambient settings; local rules and
metrics/version-check controls avoid intentional remote rule retrieval.
This process-group supervision covers ordinary descendants only. It proves no
sandbox, fork absence, escaped descendant containment, or broker-death handling.

The CLI SHALL have no customer-target/config/command options and print its
receipt as JSON. Maintainer evidence belongs only in ignored `.specfact`.
Non-Darwin ARM64 execution SHALL not pass native acceptance. Runtime temporary
fixtures SHALL be deleted on exit. No installation, commit, push, publication,
production module edit, or existing smoke edit is authorized by this harness.

## Source basis

Accessed 2026-10-02, tag v1.175.0:

- [Main.ml](https://github.com/semgrep/semgrep/blob/v1.175.0/src/main/Main.ml):
  selects native CLI by the executable argument name.
- [Scan_subcommand.ml](https://github.com/semgrep/semgrep/blob/v1.175.0/src/osemgrep/cli_scan/Scan_subcommand.ml):
  experimental maturity continues native scanning; default scan falls back.
- [Pysemgrep.ml](https://github.com/semgrep/semgrep/blob/v1.175.0/src/osemgrep/core/Pysemgrep.ml):
  Unix fallback resolves pysemgrep through PATH.

The prior single-job/native Parmap audit remains a hypothesis until independent
process-boundary evidence proves it. This harness does not redo startup proof.

## Fixed command incompatibility probe

The requested `--oss` spelling is rejected by both pinned parsers. Preserve that
native candidate exactly and fail its acceptance. For diagnostic comparison only,
SHALL also run a fixed `native_oss_only` variant using upstream `--oss-only`.
The reference Python command SHALL use `--oss-only --legacy`. Report the supported
spelling comparison separately; it cannot override a failed requested candidate.
No finding or error normalization changes are permitted for this diagnostic.

[Scan_CLI.ml, v1.175.0](https://github.com/semgrep/semgrep/blob/v1.175.0/src/osemgrep/cli_scan/Scan_CLI.ml)
defines `oss-only` (accessed 2026-10-02). The locally installed Python
`console_scripts/entrypoint.py` requires `--legacy` to bypass native dispatch.

## TDD and measured evidence

Measured on 2026-10-02, Europe/Berlin. This document carries scope-specific TDD
evidence because the authorized write scope excludes TDD_EVIDENCE.md, tasks.md
and spec.md. The wider change remains ongoing and is not archived by this subtask.

### RED / GREEN

- Spec contract was written before the tests and implementation.
- Initial RED: `.venv/bin/python -B -m unittest discover -s tests/unit -p
  test_native_semgrep_parity.py` exited 1 because the harness did not exist.
- Behavioral RED was also observed for missing `--legacy` reference selection,
  unsupported diagnostic variant, the actual JSON error `level` field, structured
  PartialParsing errors, external error-span paths and discarded error end lines.
  The final two tests specifically failed before the span implementation.
- GREEN: the same unittest command passed all 18 tests. Tests cover preserved
  rule ids/duplicates, positive controls, path traversal/symlinks, digests/sizes,
  malformed evidence, missing targets/findings, changed lines/messages/severities,
  errors/exits, fixed argv/executable, timeout/output cleanup, fixture integrity,
  CLI target rejection and mandatory false authority flags.
- Final regression: `.venv/bin/python -B -m pytest -p no:cacheprovider -o addopts=
  tests/unit/test_native_semgrep_parity.py tests/unit/test_native_analyzer_smoke.py`
  passed 35 tests in 1.16 seconds. Execution required the approved host tool context:
  the filesystem sandbox initially blocked process-group signals and `/bin/ps`.
  Existing smoke code was not edited. Evidence:
  `.specfact/native-compat/semgrep-parity-tests.txt`.
- Focused Ruff check/format and BasedPyright: zero errors/warnings. Strict OpenSpec
  validation, repository manifest validation and bundle import boundaries passed.
- Mandatory SpecFact review was run on only the two authorized Python files with
  `--enforcement changed --bug-hunt --json --out
  .specfact/native-compat/semgrep-parity-code-review.json`. Its final verdict is
  FAIL/UNKNOWN with zero findings: all analyzer evidence reports
  `unsupported_controller_platform`. This is a remaining review gate limitation,
  not a passing clean-code review. Repository-wide contract/smart/full-test gates
  remain the parent implementation's responsibility and are not claimed here.
- The signature verifier with `--payload-from-filesystem --enforce-version-bump`
  failed because the local public verification key is unavailable. No signed
  module assets/manifests were changed by this subtask; no signature bypass was
  used. Full merge/release gate completion is not claimed.

### Actual native measurement

Command: `.venv/bin/python -B scripts/native_semgrep_parity.py >
.specfact/native-compat/semgrep-native-parity.json`. Exit: **1**, expected rejection.
The final run completed at **2026-10-02 23:21:13 Europe/Berlin** in **9.645 seconds**
on physical Darwin ARM64. The two analyzer frontends used the digest-verified
CPython 3.13 venv and Semgrep 1.175.0 payload; the controller/test environment is
CPython 3.14.7 and does not establish a supported production Python matrix.

| Fixed scenario | Python / supported native spelling | Parity |
| --- | --- | --- |
| clean_code clean | exit 0, no findings, fixture scanned | match |
| clean_code defective | exit 0, print-in-src at fixture.py:2 | match |
| clean_code nosem | exit 0, same finding despite comment | match |
| bugs clean | exit 0, no findings, fixture scanned | match |
| bugs defective | exit 0, specfact-bugs-eval-exec at fixture.py:2 | match |
| bugs nosem | exit 0, same finding despite comment | match |
| malformed Python | exit 0, same PartialParsing error at fixture.py:2 | match |
| invalid local rule | Python exit **2**, scanned fixture.py; native exit **7**, scanned [] | **mismatch** |

The requested native `--oss` command exits 2 without JSON for every case:
unknown option `--oss`. Its raw stdout/stderr and exact executable/argv remain
in each primary comparison. The separate fixed `--oss-only` diagnostic matches
**7 of 8 cases**, including full finding message/severity/rule/path/line and
error comparisons. Both invalid-rule positive controls pass, but the mismatched
exit statuses and scanned target lists reject compatibility. Nothing is removed
or normalized to produce an acceptance result. The receipt explicitly reports
`passed=false`, `supported_spelling_parity_passed=false`,
`production_eligible=false`, `sandbox_verified=false`, and
`single_process_verified=false`.

Final harness SHA-256:
`ef8fe7379d963558516e45146c2d1ee1c4c65b8188c9f98a572a05b94af453b8`.
Final receipt SHA-256:
`fc69f05b86fb779fcbfef1bddc6d9ee7a100b55e7b2ca288d1d0ce56f28c1684`.
The receipt includes pins for interpreter, console script, core, both approved
rule packs and the local CA bundle, plus harness/smoke hashes, timestamps, raw
outputs and canonical comparisons. All actual evidence is gitignored `.specfact`.
Initial CA-lookup/reference-selection and rejected-option receipts are retained
there as `semgrep-native-parity-initial.json` and
`semgrep-native-parity-oss-rejected.json`.

### Limits, failure modes and next action

Confidence: High for these measured fixtures and candidate rejection; no wider
frontend equivalence or managed-boundary admission is established. Changing
Semgrep, interpreter, CA or approved rule bytes invalidates the pinned experiment.
The pins cover selected inputs, not publisher authentication or the full Python
package closure. Separate startup proof and customer installation remain required.

- Missing or changed findings/errors/targets reject the comparison; full raw
  outputs remain available for diagnosis.
- Digest/path/JSON/timeout/output failures reject acceptance before they can be
  treated as empty clean evidence. Each of the fixed 24 launches has a 30-second
  scan timeout, bounded cleanup and the smoke runner's 16 MiB per-stream cap.
- Process-group cleanup covers ordinary descendants only. Escaped descendants,
  fork absence, broker death and confinement need the separate startup/boundary
  proof; authority flags always remain false here.

Next action: resolve the invalid-rule exit/scanned-input contract and explicitly
select a supported native argument contract before any native adapter admission.
The requested `--oss` candidate remains rejected. No production module, existing
smoke, startup proof, commit, push, delegation or publication was performed by
this subtask. Rollback consists of removing only this subtask's three added files
and its ignored parity evidence; temporary fixtures are automatically deleted.


## Corrected primary candidate, 2026-10-03

The unsupported `--oss` spelling was an implementation experiment, not a user
requirement. It is superseded by the upstream `--oss-only` contract above; retain
the failed historical receipts but do not keep executing a known-invalid primary
command. The sole native candidate now uses that supported flag. Strict comparison
continues to reject the genuine invalid-rule exit/scanned-target discrepancy;
changing the flag must not suppress that failure. Actual sealed clean/defect runs
are independently recorded in SEALED_ANALYZER_CONTRACT.md.


Source attribution uses captured smoke-helper bytes with standard import-loader
execution, not a post-run checkout reread. The sidecar omits a controller-source
execution identity because no captured launcher establishes it. Later checkout
replacement cannot relabel already executed smoke fixtures; a negative receipt
regression proves no post-run source file read is needed. This fixes provenance
only and does not change the retained invalid-rule native/frontend mismatch.
