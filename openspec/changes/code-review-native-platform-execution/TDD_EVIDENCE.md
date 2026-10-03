# Current candidate-tool evidence — 2026-09-30

Scope: bounded local OCI candidate verification only. Native runtime production is blocked by the lifecycle failures in NATIVE_RESULTS.md. Requirements remain planned for the full capsule; these results do not advance native release acceptance.

## Specification and failing-first sequence

The local Docker identity/promotion scenarios were added to `specs/review-native-platform-execution/spec.md` before the verifier implementation. Tests cover exact platform metadata, digests/sizes/diff IDs, payload bytes and regular-file modes, canonical paths, links/special files, resource bounds, JSON types and unconditional experimental status.

Command from the worktree root:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts= -p no:cacheprovider tests/unit/test_macos_capsule_candidate.py -q
```

- Initial run: exit 1, 27 errors because the implementation was absent.
- Malformed-deflate regression: exit 1, one failure and 27 passes; `zlib.error` escaped the API. Added the error translation only after observing failure.
- Schema-type regression: exit 1, two failures and 30 passes; floating-point schema versions were accepted. Added exact integer checks after observing failure.
- Final focused run: exit 0, 32 passed.
- Focused Ruff check/format and BasedPyright: passed, zero type errors/warnings.
- Self-contained candidate-build/README.md reproduction: passed against the local Docker daemon; verifier manifest/config identities match the Docker export receipt.

The Docker proof retains actual `darwin/arm64` metadata. The verifier never executes/extracts the archive, does not authenticate operator-supplied native claims, and always emits `production_eligible=false`. Its input/memory bounds deliberately support a tiny fixture, not a complete analyzer closure. Native baseline remains unsupported; no production Linux/macOS acceptance pass is claimed.

## Review-driven correction and repository gates

The initial local SpecFact review found complexity/nesting, fixture naming, CLI output and missing-contract findings. The parser and test fixtures were split into focused helpers; the public verification API now enforces ineligibility through a postcondition. The private CLI adapter is exercised through real subprocess tests. All 32 cases still pass. An isolated CrossHair environment supplies its pytest/icontract imports; no global interpreter installation was changed.

Final local review used `--enforcement changed --bug-hunt --json --out .specfact/code-review.json` for the two staged Python files: PASS, zero findings. This uses the repository's existing development-source review behavior and is not native capsule acceptance. Raw local reports remain ignored.

Full tests passed with 3,046 passes, one Linux proc-contract skip and two dependency deprecation warnings. Contract tests passed 28 cases. Repository format/type/lint, YAML/manifests, bundle imports, module payload/version verification, planned Requirements evidence, strict OpenSpec and structural Markdown/whitespace checks passed. No signed module payload changed.

Final smart-test run (`hatch run smart-test -o 'addopts=-ra --import-mode=importlib' -q`) passed: 3,046 passed, one Linux-only skip, two dependency deprecation warnings. Earlier invocation removed importlib mode; a subsequent run exposed an isolated review environment outside the recognized `.venv` directory. Correcting the invocation and relocating that tool environment resolved both without changing production guards.

## PR #486 outer archive review correction

Review annotation 4146920413 was reproduced after adding the rejection scenario: three failures and 32 passes for extra outer files, unreferenced blobs and unexpected directories. Exact referenced-file membership and allowed parent-directory checks then produced 35 passes. The actual local Docker export still passes. Optional parent directory headers are permitted; unrelated directories are rejected.

## PR #486 physical TAR framing corrections — 2026-09-30

Scope: review annotations 4146938381 and 4146938392. The owner-added scenario `Candidate TAR framing is malformed` was visible before tests and implementation. Only the candidate script, its unit tests, and this appended evidence were edited for this correction; no commit or push was performed.

Added 48 regression cases: 12 physical TAR faults at both outer-archive and payload-layer locations, exercised independently through the API and real CLI subprocesses. Cases cover invalid trailing headers, nonzero bytes after end markers, a single zero end block, missing end blocks, partial headers, unaligned archives, nonzero member padding, truncated GNU sparse extensions, PAX/global PAX headers, and GNU long-name/long-link headers. Layer fixture digests and OCI descriptors are recomputed so framing validation is actually reached.

Failing-first command: `hatch run python -m pytest tests/unit/test_macos_capsule_candidate.py -o addopts= -q`. Before parser changes: **44 failed, 39 passed**. The real CPython 3.11.15 interpreter lacked pytest, so a temporary isolated environment was created at `/private/tmp/pr486-py311` with pytest and icontract. Before parser changes, `/private/tmp/pr486-py311/bin/python -m pytest tests/unit/test_macos_capsule_candidate.py -k sparse -o addopts= -q` produced **4 failed, 79 deselected**: both API cases leaked `IndexError`, and both CLI cases emitted tracebacks instead of failure JSON. Raw baseline logs remain in `/private/tmp/pr486-tar-red.log` and `/private/tmp/pr486-tar-py311-red.log`.

The parser now walks physical 512-byte records directly. `TarInfo.frombuf` checks each nonzero header checksum; a separate header validator permits only regular files and directories, rejecting extension/sparse/link/special headers before archive-level extension processing. It validates member size, aligned boundaries, zero member padding, two zero end blocks, and an entirely zero trailing region. Existing path, member-count, cumulative byte, OCI identity, and payload equality checks remain enforced. Directory payload bytes are rejected. Unsupported TAR extensions are deliberately outside this tiny COPY-only proof's contract.

Final focused commands above without `-k sparse`: **83 passed** in the Hatch environment (CPython 3.14.7) and **83 passed** on actual CPython 3.11.15. Ruff format/check and targeted BasedPyright passed with zero errors/warnings. Initial SpecFact review reported one complexity warning; extracting header validation resolved it. Final repository SpecFact review of both owned Python files with `--enforcement changed --bug-hunt --json --out /private/tmp/pr486-tar-code-review.json` returned **PASS, zero findings**. No local CodeRabbit CLI was invoked. All 38 functions across the two files have concise docstrings (AST count: 19/19 in each file).

Actual Docker export acceptance was preserved by running `hatch run python scripts/macos_capsule_candidate.py /private/tmp/specfact-460-candidate-z9YAR6/candidate.oci.tar --expected-payload /private/tmp/specfact-460-candidate-z9YAR6/context/payload`: **PASS**, still `production_eligible=false`. Raw passing logs and receipt remain under `/private/tmp/pr486-*`; they are not added to the PR. This bounded correction does not claim native runtime readiness or replace the owner's whole-PR gates.

## PR #486 strict JSON correction

Annotation 4147060545 was reproduced after specifying strict JSON constants: six failures and 83 passes for NaN/Infinity/-Infinity in unused metadata fields through API and CLI. A rejecting parse_constant callback then produced 89 passes. All OCI metadata uses the same strict decoder.

## PR #486 raw-path and metadata-encoding corrections

Annotations 4147171007 and 4147171019 were reproduced on native CPython 3.11 after specifying raw path/UTF-8 requirements: 20 failed, 89 passed. Cases cover redundant directory slashes in outer/layer headers and UTF-16/32 in each of layout/index/manifest/config, through both API and CLI with recomputed descriptors. Raw name/prefix validation before accepting TarInfo normalization and strict UTF-8 decoding then yielded 109 passes on CPython 3.11 and 3.14. The actual Docker-exported candidate still passes and remains production-ineligible.

## PR #486 strict gzip framing correction

Annotation 4147615146 was reproduced after adding the gzip scenario: 12 failed and 114 passed on native Python 3.11. API/CLI regressions cover all three reserved flag bits, invalid header CRC, concatenated streams, trailing bytes/zero padding and truncation; a positive control accepts a valid optional header CRC. Bounded zlib gzip decoding now validates header/trailer checksums, requires stream completion and rejects all unused input while preserving the decompressed byte ceiling. All 126 tests pass on native Python 3.11 and 3.14; the actual Docker export still passes. No production eligibility changes.

## PR #486 TAR identifier correction

Annotation 4147769543 was reproduced after specifying the supported ustar/GNU format pairs: 16 failed, 130 passed. Tests cover unknown magic, invalid ustar/GNU versions and unsupported V7 identifiers in outer and layer headers through API/CLI, with valid checksums/descriptors. Four positive controls retain ordinary ustar/GNU acceptance. After explicit magic/version validation, all 146 tests pass on native Python 3.11 and 3.14. Actual Docker output still passes. Annotation 4147752970 corrected README grammar and separated outer-archive membership from the expected layer tree.

## PR #486 path-terminator correction

Annotation 4147882183 was reproduced after extending the raw-path scenario: eight failed and 146 passed on native Python 3.11. Checksum-valid outer/layer name and prefix fields hid nonzero bytes after a NUL; both API and CLI accepted them. A shared path-field decoder now requires zero padding after the first terminator before strict UTF-8 decoding. All 154 tests pass on Python 3.11 and 3.14; the actual Docker export still passes.

## PR #486 offline OCI configuration schema correction

Annotation 4148265734 was reproduced after specifying schema validation: 19 failed, 155 passed for malformed known runtime/history/platform fields and dates. The pinned Apache-2.0 OCI image-spec v1.1.1 config schema and its two map definitions are stored locally with provenance hashes/license; references are local only. Explicit Hatch development dependency `jsonschema[format-nongpl]>=4.25.1` enables typed field and date-time validation, translating schema failures to ValueError. Three additional CLI cases verify failure JSON. All 177 tests pass on native Python 3.11 and 3.14; valid optional nullable fields and the real Docker-exported candidate still pass. No native dependency-policy admission or production eligibility changes.

## PR #486 OCI graph schema correction

Annotation 4148429641 was reproduced after specifying graph schema validation: 21 failures, five positive controls passed. Cases cover malformed annotations/artifact types across index, manifest and each descriptor, plus descriptor URL/data types. Pinned OCI v1.1.1 manifest/index/descriptor schemas are now vendored with source hashes; references are expanded locally and identifier annotations removed. All documents use the shared offline schema gate. All 203 focused tests pass on native Python 3.11 and 3.14; the real Docker candidate remains accepted and production-ineligible.

## PR #486 alternative-reference correction

Annotations 4148552110 and 4148552120 were reproduced after specifying the fixed graph profile: 16 failures through API/CLI for embedded descriptor data (including empty data) and schema-valid dangling subjects. The verifier now rejects any data field on selected descriptors and any subject on index/manifest. All 219 tests pass on native Python 3.11 and 3.14; actual Docker output remains accepted. This deliberately excludes those optional OCI features rather than claiming to validate extra content.

## PR #486 index media identity correction

Annotation 4148676592 was reproduced after specifying optional index media identity: four failures and two valid controls passed through API/CLI. A present index mediaType must now equal application/vnd.oci.image.index.v1+json; omission stays valid. All 225 focused cases pass on native Python 3.11 and 3.14, and the actual Docker candidate still passes.

## PR #486 unmatched map-key correction

Annotation 4148825908 was reproduced after specifying unmatched-key rejection: 16 failures for empty/newline-only keys across five annotation locations and configuration Labels/Volumes/ExposedPorts. Local schema maps now set additionalProperties=false alongside patternProperties, explicitly documented as stricter than upstream. All 241 focused cases pass on native Python 3.11 and 3.14; the actual Docker export remains accepted.

## PR #486 expected hard-link correction

Annotation 4148930393 was reproduced after specifying single-link expected files: two API/CLI failures with a hard-link alias outside the expected tree. Expected regular files now require st_nlink==1 before reading. All 243 focused tests pass on native Python 3.11 and 3.14, and the actual Docker candidate still passes. The operator-owned immutable-tree assumption and lack of TOCTOU sealing remain explicit.

## PR #486 raw TAR numeric-field correction

Annotation 4149074244 was reproduced after specifying raw numeric-field validation: 32 API/CLI failures covering all eight numeric fields in outer and layer headers, with valid checksums/descriptors. The verifier now requires unsigned octal text with NUL/space padding before TarInfo parsing; signed and base-256 extensions are outside the bounded profile. All 275 focused tests pass on native Python 3.11 and 3.14; the actual Docker-exported candidate still passes and remains production-ineligible.

## PR #486 numeric-digit and history cardinality corrections

Annotations 4149222450 and 4149222458 were reproduced with eight API/CLI padding-only UID failures and three history/layer cardinality failures. A null-history positive control also failed despite OCI optional-field semantics; two other positive controls passed. Required numeric fields now contain at least one digit while unused device fields retain padding-only compatibility. Present non-null history must match rootfs diff-ID cardinality; the local schema explicitly accepts null history. All 289 focused tests pass on native Python 3.11 and 3.14, and the actual Docker-exported candidate still passes with production eligibility false.

## PR #486 TAR header-tail correction

Annotation 4149326593 was reproduced after specifying zero header-tail padding: eight API/CLI failures for checksum-valid nonzero bytes at offsets 500 and 511 in both outer and layer headers. The verifier now rejects nonzero bytes in the unused final twelve header bytes before TarInfo parsing. All 297 focused cases pass on native Python 3.11 and 3.14; the actual Docker-exported candidate still passes and remains production-ineligible.

## PR #486 ancillary TAR text-field padding correction

Annotation 4149448126 was reproduced after specifying ancillary text-field validation: twelve API/CLI failures for checksum-valid hidden post-terminator bytes in link name, owner name and group name, in both outer and layer headers. All three fields now use the shared strict UTF-8/zero-padding decoder before TarInfo parsing. All 309 focused tests pass on native Python 3.11 and 3.14; the actual Docker-exported candidate still passes with production eligibility false.

## Native XPC boundary follow-up

The specification preceded four failing tests for the absent runner. The previous
tracing negative control reproduced six descendant survivors with an empty final
18-PID audit. Observer hardening added failing-first readiness and receipt/error
cases; all 15 focused tests now pass. The final native run had 18 ready cases:
two positive controls passed, all sixteen detached lifecycle cases failed and
all emergency-cleanup audits were empty. See XPC_BOUNDARY_RESULTS.md.

Full repository suite: 3335 passed, one Linux-only skip (209.11 seconds), before
the last three observer tests; those passed in the focused suite. Format, type/lint,
YAML, bundle imports, module signatures and 28 contract tests passed. The manual
released SpecFact review command executed but returned FAIL/UNKNOWN because the
native capsule is unsupported; zero findings is not clean-review evidence. The
normal staged-file hook and protected Linux CI remain separate review gates.

Final smart-test suite: 3338 passed, one Linux-only skip (209.65 seconds), including all 15 observer tests. Normal commit hooks passed, including the staged explicit-files review and 28 contract tests. This hook result does not replace the unsupported native capsule review or protected PR assurance. Final independent native audit: all 53 recorded process identities absent.

## Optional Apple distribution split — 2026-10-02 (Europe/Berlin)

The owner approved replacing Developer-ID-first admission with exact initial
ad-hoc distribution acceptance. Updated the normative proposal/design/feasibility,
scenarios, planned mappings, tasks, status and change order before modifying tests
or preflight. Created optional OpenSpec `code-review-macos-developer-id-distribution`
and public story #488; verified parent #163, SpecFact CLI project/Todo, no milestone,
#488 blocked by #460, #460 blocking #488, and #460 still blocked only by completed
#459. Updated #460's current scope while preserving superseded historical evidence.

Added five prerequisite-routing cases before implementation. Focused execution
reported **5 failed, 21 passed**: no initial checker/Path import/mode existed.
Implemented default initial checks without keychain/notary probes and explicit
optional Developer ID mode. Re-run: **26 passed**. The optional Apple checker keeps
its original fail-closed certificate/team/notary checks. Default initial checks
only verify native host and system signing-tool availability; they inspect no
artifact and grant no signature, boundary or publication acceptance.

Actual local default preflight returned exit 0 / `initial_prerequisites_available`,
`signing_mode=ad-hoc`, `signed_boundary_verified=false`, `production_approved=false`.
Explicit `--signing-mode developer-id` without credentials returned exit 2 / blocked.
Neither command launched a worker or contacted a notary service.

Strict OpenSpec validation passed for both changes. Staged Requirements evidence
passed for both sources at **planned** maturity; implementation evidence remains
**not-yet-available**. Format, type-check, lint, YAML, bundle imports and full-payload
signature/version gates passed; seven module manifests remain unchanged. No module
version bump is warranted by this prerequisite/scope change; the completed native
capability still requires its minor bump and full final-artifact acceptance.

Raw RED logs and review/test reports remain ignored or outside the repository.
This revision does not resolve the creation-to-tracing ownership gap, implement a
native capsule backend or prove installation on another Mac. Those requirements
remain mandatory. Neither OpenSpec change is complete or ready to archive.

Final scope-split verification: 28 contracts passed; full suite **3,490 passed,
one Linux-only skip**; serial smart-test **3,490 passed, one Linux-only skip,
five subtests passed**. The first smart run had two failures in unchanged runner
assurance tests while other checks were active. One isolated test passed, then
both the serial full suite and serial smart rerun passed. The cause was not
established; no runner code, expectations or security gate was weakened.

The independent read-only review-agent reviewed the complete scope-split patch
and new optional change: **No findings**. Explicit-files maintainer Code Review
with the existing isolated CrossHair/pytest environment returned
**PASS_WITH_ADVISORY**: seven MISSING_ICONTRACT warnings on the standard-library
preflight helpers, covered by the existing narrow bootstrap exception in
NATIVE_COMPATIBILITY_RESULTS.md. No other warnings remained. The initial ambient
CrossHair interpreter could not import pytest; using the admitted isolated review
tools resolved that environment warning.

Actual public native `specfact code review run --enforcement changed --bug-hunt`
returned exit 1 / **FAIL**, assurance **UNKNOWN**, with
`unsupported_controller_platform`. That remaining native-backend limitation is
not repaired or waived by the signing split. No boundary worker, independent-Mac
installation, merge or GHCR publication was performed by this revision.

## Native managed startup and confinement — 2026-10-02 (Europe/Berlin)

STARTUP_BOUNDARY_CONTRACT.md preceded new tests and native fixtures. Focused
missing-implementation RED: 10 import errors. Repetition/transition RED: 2 failed,
10 passed. Independent tracing/confinement expansion RED: 12 failed, 11 passed.
After implementation, 23 focused unit cases pass. Native positive-control failures
(SDK vfork/descriptor API mismatch, raw-fork ABI and unavailable raw vfork) were
corrected or explicitly separated before enforcing denial acceptance. Two accidental
full-suite invocations were cancelled; they are not claimed as verification.

Actual local ad-hoc/hardened ARM64 experiments passed five startup stages 100
times, then all six stages including deny-default confinement 100 times (600 races).
The observer confirms kernel trace flags, birth/parent and session transitions;
negative running control survives five seconds. Initial suspended negative and
SIGTERM-ignoring untraced controls are retained as failed attribution/ownership
controls. See STARTUP_BOUNDARY_RESULTS.md for measured limits. No production
capsule or supported-OS matrix pass follows from this subset.

Independent review found five actionable P2 harness races. Regression RED: five
failed, 28 passed; GREEN after fixes and added audit-token timing checks: 35
startup tests. Native final rerun: 100×6 transitions passed, both native stale
pid-version tokens rejected without killing the original fixtures. The Semgrep
parity sidecar has 18 unit cases; combined focus is 53 passed. It records a real
invalid-rule/frontend mismatch rather than claiming complete native parity.


## Native control, sealed analysis and source-binding follow-up (2026-10-03)

The private broker now supports bounded authenticated fixture launch/wait/signal/
cancel requests. Sealed actual native Semgrep executes both module rule packs
inside the traced deny-default profile. Initial dyld/profile failures were kept
as failures and repaired with exact pinned library/path grants and forbidden
host-read controls; no host execution fallback was used.

Independent review additionally found suppressed runtime SIGTRAP, cancellation
reason overwrite at timeout, EOF attribution to a competing worker timer and
source/policy digest rereads. The actual C terminal-reason tests failed two cases
before the fix and passed all three afterwards. The traced exec/SIGTRAP fixture
failed with a suppressed signal before the broker fix and now terminates with
signal 5. Analyzer provenance regression RED: three failures, one existing
profile case passed; GREEN with startup snapshot regressions: 62 passed, one
explicit native-only case skipped.

Actual ARM64 startup final captured-input rerun: 100 repetitions of all six
transitions passed (600 races), max observed cleanup 0.0103 seconds. The four
sealed clean/defective cases also passed, with spaces/Unicode fixture paths and
negative profile probes. Final control repetition acceptance is tracked
separately in CONTROL_BOUNDARY_CONTRACT.md; historical success cannot stand in
for proof after review corrections.

The serial repository test rerun before the last provenance additions passed
3,570 tests with two platform/explicit-native skips. Subsequent final gates must
identify their own counts and executed revision. No experiment receipt approves
production selection, publication or a module version change.

Final control source-snapshot acceptance passed 1,219 records (100×12 lifecycle
cases plus 19 protocol controls) after the corrected native-clock/EOF proof.
The source mutation regression recorded seven failed assertions before the fix;
the owned native control suite then passed all 21 tests without skips. Bounded
failure snapshots now retain observations and request history before cleanup,
without authority bytes. The historical cancellation/wait failure did not recur
but its cause is unproven; this is not represented as a diagnosed C regression.
See CONTROL_BOUNDARY_CONTRACT.md for exact executable/source identities.

After the final standard-import/compiler-helper refactor, the actual native
focused suite passed all 105 cases (no skips), including traced runtime trap,
C terminal-reason expiry, control protocol and withheld-EOF negative. The
source/profile-bound 600-race startup suite was repeated successfully; its final
max observed cleanup was 0.0153 seconds. All four sealed analyzer cases passed
again. Planned requirement evidence and both strict OpenSpec validations pass.

The final public native capsule command was executed with staged inputs and
exited 1: FAIL/UNKNOWN, unsupported_controller_platform for all ten members.
This remains a production-integration requirement, not a passing review. The
parent helper advisory returned PASS_WITH_ADVISORY with only the documented
stdlib MISSING_ICONTRACT exception. Independent review-agent's final startup,
control and sealed-analyzer scope returned no findings.

A smart-test run made during remaining tree edits failed the existing
unchanged-blocker assurance test (pre_enforcement_evidence_outcome absent):
3,587 passed, one failed, eight skips and 26 passed subtests. The runner binds
all Git-visible paths, so final verification must use a frozen worktree; the
failed run is retained and cannot count as a pass.

The Semgrep sidecar review found the same post-run source-reread defect. A
regression failed before changing its smoke import to a captured-source loader
and removing the unsupported controller-source identity claim; the sidecar
suite then passed all 19 cases. Test-only import, resource-lifetime, fixture
name and complexity findings from staged review were corrected without global
rule changes. The existing assurance case passes alone (13.57 seconds); full
frozen-tree gates below remain authoritative.

ARM64 macOS 14/15/26 CI is configured in code-review-macos-boundary.yml for
serial 100-round startup/control suites. Exact OS/build and ordinary GUI
launchd gates fail closed. No secrets, paid credentials, raw-log uploads or
publication permissions are introduced. Configuration validation passes;
hosted executed evidence remains pending a PR run.

CI review corrections: actual embedded-function tests recorded three failures
(one valid positive passed) for omitted normal/runtime-trap controls and starting
control after startup's hard timeout. The workflow now requires both controls
exactly once and stops before any second suite after a timeout. These are
behavioral tests of the actual workflow functions, not mirrored YAML checks.

Independent review-agent re-reviewed the corrected sidecar, tests and CI
functions with no findings. Staged source review has only the documented
stdlib MISSING_ICONTRACT exception (83 warnings, zero other findings). The new
CI test initially exposed a missing PyYAML dependency in the isolated CrossHair
review environment; installing the already-declared PyYAML 6.0.3 there repairs
that tool-environment gap without changing module/runtime dependency policy.


## Final frozen-tree verification (2026-10-03, Europe/Berlin)

- Native focused suite: 110 passed, no skips (actual C timer, traced trap,
  private control subset, withheld-EOF negative and CI behavior tests included).
- Smart suite: 3,593 passed, eight skips, 26 passed subtests (267.11 seconds).
- Full suite: 3,593 passed, eight skips, 26 passed subtests (270.79 seconds).
- Skips: one Linux proc contract and seven explicit-native tests; all seven
  explicit-native cases ran in the passing native focused suite above.
- Four sealed native Semgrep clean/defect cases passed on final helper bytes.
- Final staged Code Review: PASS_WITH_ADVISORY, 83 documented stdlib
  MISSING_ICONTRACT warnings, no other findings.
- Script-specific BasedPyright: zero errors, warnings and notes; repository
  format/type/lint, manifests/imports/signatures, 28 contracts, strict OpenSpec
  for both changes, planned evidence mappings and actionlint passed.
- Independent review-agent: no findings after native, sidecar and CI fixes.

The previous assurance failure did not recur in either frozen-tree suite.
No production native runtime/public command, OS matrix or independent-install
acceptance is claimed. Public capsule-required native review still returns
FAIL/UNKNOWN unsupported_controller_platform. Hosted matrix results must be
recorded from the actual PR; these checks do not authorize merge/publication.

## PR #489 bounded failure diagnostics — 2026-10-03

Initial hosted run 37079681523 passed all six-by-100 startup races on macOS
14 and 26; both control helpers failed. Original sanitized output reported only
helper_failed, so the failure cause is unproven. Preserve those failures; no
retry or later result retroactively approves the first run.

Specification: NATIVE_BOUNDARY_CI.md now permits only bounded allowlisted
failure case/exception-class/count diagnostics. Raw messages, native statuses,
audit identities, capabilities and paths remain private.

RED: actual workflow tests failed twice with missing failure_type/failed_case;
four existing tests passed. GREEN: all six tests passed after implementation.
Tests inject private paths/identities and unknown names, check rejection and
raw-file deletion, and retain failure status. No boundary or timing gate changed.
