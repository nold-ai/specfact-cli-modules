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
Issue #488 blocked by #460, #460 blocking #488, and #460 still blocked only by completed
Issue #459. Updated #460's current scope while preserving superseded historical evidence.

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

## PR #489 review fixes and hosted diagnostic attribution — 2026-10-03

Independently validated five findings: Markdown issue-reference wrapping, stale
Node packager TDD/rollback, missing analyzer stderr, exception masking and
Node version validation/error reporting. Documentation retains historical scope;
no packager shipment or module enablement is claimed.

Analyzer/Node diagnostic RED: six failures, forty-five passes. Final focused
GREEN: forty-nine passes. Control exception RED: one failure/three errors;
phase RED: eleven errors. Native focused GREEN: thirty passes. Contracts carry
exact scope and private-data limits. Node packager/input proof: thirty-seven
passes. No native C implementation or containment policy changed in these fixes.

Workflow attribution RED: the nested first-failure test failed; GREEN: seven
passes. Fixed-phase privacy RED: missing failure_phase; GREEN: eight passes.
First-failure attribution and allowlisted phase reporting cannot approve a
failed suite. Complete hosted startup passed on all three OS builds; control
passed only macOS 14 in the second attempt. Other control failures remain open.

### Independent ownership review and final focused validation

The requested read-only review-agent reproduced two additional P2 diagnostic
defects: unwind-order ownership inference and stale phases after decoded reply
validation. Both were fixed through failing-first controller/workflow tests.
The controller stamps the active invocation and phase once before cleanup;
the wrapper requires an explicit boolean owner marker. A successful-body
cleanup failure has its own fixed cleanup phase and still fails.

Workflow ownership RED: five parameterized failures. GREEN: thirteen workflow
cases. Cleanup phase RED: one failure; GREEN: thirteen cases. Final combined
focused run with native control enabled passed **95 tests with no skips**.
Independent review of the complete follow-up diff returned **No findings**;
its controller/workflow reproductions passed ninety tests with thirty subtests
(three explicitly native cases skipped, two unrelated supervision cases
deselected in the restricted review-agent environment). The parent's focused
run covers those native and supervision cases without the restriction.

Actual post-fix sealed Semgrep passed all four scans, and all ten real native
CPython 3.13 analyzer compatibility adapters passed. These are separate scopes;
no all-ten sealed acceptance or production-native enablement is claimed.

### Physical teardown reproduction and passing rerun

The fresh pre-fix control run failed after 76 complete rounds during timeout-case
teardown. Its independent diagnostic observed both broker and worker absent;
immediate launchd job inspection after bootout was still registered. Preserve
that failed receipt and log; this is not proof of the separate hosted isolation
timeout's cause. The startup teardown contract now requires removal once and
bounded independent absence observation within a deadline established before
teardown. The original measured death windows and native C sources are unchanged.

RED: two teardown tests failed, thirty-seven passed, one native opt-in skipped.
GREEN: scoped startup/control/analyzer tests passed ninety-eight with four
opt-in skips. Final actual native focused validation passed **135 with no skips**.
Fresh serial full native runs passed **600 startup races** and **1,219 control/
protocol records**, each with all required 100-round groups; production and
signed-boundary approval flags remain false. The independent review-agent
reviewed teardown and its callers with fault injections and returned **No findings**.
Existing subprocess timeouts may delay reporting failure beyond five seconds;
after-deadline verification can never be accepted.

Final frozen-tree smart and full repository suites each passed **3,623 tests
plus 43 subtests**, with eight platform/explicit-native skips. New native
startup/control cases were executed in the 135-case focused run; unchanged
native timer fixtures retain their preceding explicit proof. YAML, bundle
imports, module signature/version integrity, twenty-eight contract tests and
smart-test coverage checks also passed. Native full boundary/platform admission
is still incomplete; no version bump, publication or production support claim.

## Socket readiness and bounded transition diagnostics — 2026-10-03

Current-head hosted run 37084629954 (`314e5b6c`) passed 600 startup races on
macOS 14, 15 and 26, but control failed on 14/15 at bootstrap-socket and on 26
at cancel/request-wait. None is counted as complete matrix acceptance. The
socket observation now waits within its original three-second budget for an
owned socket with mode 0600, using lstat and rejecting wrong types/owners and
symlinks. The signed C broker adds private transition observations only; no
signal/tracing/wait algorithm, confinement or death deadline is changed.

RED/GREEN evidence:

- Socket readiness: see CONTROL_BOUNDARY_CONTRACT.md for the deterministic
  permission-transition, delayed binding, owner/type/symlink and late-deadline
  failures followed by 46 native-enabled passing tests.
- Last-owned-worker state: 24 missing-module RED errors, then 24 passes;
  controller integration failed once with 24 passes, then passed. Snapshots bind
  to the failing wait's launched worker and export only four actual booleans.
- Actual workflow definitions: eight RED failures with 33 passes, then 41 passes.
  Missing, non-boolean, foreign-origin and wrong-phase observations remain
  omitted; private fields are excluded.
- Native C transition fixtures: ten expected RED failures, then ten event and
  three timer tests passed using ad-hoc signed/hardened ARM64 test binaries.
  Both terminal orders exercise actual loop completion; bounds and rejection
  paths are covered with safely mocked system operations.
- Combined focused validation: 214 passed without skips, including native
  startup/control/event/timer fixtures. After strict-type lint adjustments,
  the state/controller/workflow tests passed again (66 cases).
- Physical macOS 27.0.1 build 26A434 control proof: 1,219 passing records,
  100 repetitions of all twelve lifecycle cases plus nineteen protocol checks.
  Receipt: `.specfact/native-compat/pr489-socket-state-control-100.json`.
  Production approval and complete signed-boundary verification remain false.
- Independent requested review-agent inspected all thirteen changed files,
  including new files, and returned no findings; its small strict-type follow-up
  also returned no findings. Repository broad gates and normal hooks are required
  separately before commit. No current revision's hosted success is claimed.

CodeRabbit completed head `314e5b6c` review 5398281990 with one documentation
finding. NATIVE_NODE_TDD.md now reports the shared manifest and aggregate adapter
results, explicitly avoiding unrecorded per-build/BasedPyright-specific claims.
The current hosted wait-timeout cause remains unknown; 300 additional unchanged
local cancellation trials passed and do not explain it. These diagnostics must
not be represented as a production backend, runtime admission or shipment.

Final frozen-source validation after the commit-hook complexity corrections:

- Native-enabled focused suite: 214 passed without skips (14.39 seconds).
- Physical control suite: 1,219 passed, including all twelve-by-100 lifecycle
  cases and nineteen protocol checks. Final receipt:
  `.specfact/native-compat/pr489-final-state-control-100.json`; SHA-256
  `0f0b3cdf792abba541ade1b94d577835dd4a3ec1bc64248c2a1845f66f62cb60`.
  Production approval and complete signed-boundary verification remain false.
- Serial smart and full suites: each 3,689 passed, eighteen skipped and
  63 subtests passed (266.18 and 273.07 seconds respectively). Seventeen native
  opt-in skips were exercised in the focused suite; one proc-descriptor contract
  requires Linux. An earlier concurrent smart-suite attempt returned UNKNOWN
  in an unchanged verdict test; its isolated run and both serial suites passed.
  A private probe confirmed ignored analyzer-cache changes affect the worktree
  identity guard; the exact cause of that initial result remains unproven.
- Format, typing, lint, YAML, imports, public-key signature/version verification,
  twenty-eight contract tests, both strict OpenSpec changes, actionlint and
  planned requirements evidence mappings passed. Signed payloads are unchanged.
- Staged development-host Code Review returned PASS_WITH_ADVISORY: only
  32 MISSING_ICONTRACT advisories covered by the existing standalone-script
  exception, with no remaining defect or clean-code findings. The independent
  follow-up review of the refactored helpers and tests returned no findings.

Normal commit hooks and current-head hosted review remain separate gates.
No hosted result from the previous head approves this revision.

## PR #489 finding 4171361951 — complete raw wait history

2026-10-03 (Europe/Berlin), starting head
`1a0b68d92e89405a0d536fa0201a0d578760a2f7`, worktree
`codex/macos-native-capsule-runtime`. User authorized this isolated correction
while the parent investigates native C cancellation. The current
`code-review-native-platform-execution` contract covers this diagnostic scope;
strict OpenSpec validation passed before implementation and after the fix.
No hierarchy refresh or cache-writing verification was run in this slice.

Order: appended the raw-wait contract first, then added regression tests, ran
RED, implemented the small shared-history correction, and ran GREEN.
Inspection confirmed `_prepare_wait` bypassed `Client.request` for a complete
`eof-wait`, leaving history at launch and preventing worker-PID resolution.
`Client.record_request` now shares the newest-64-entry bound with ordinary
requests and records opcode, fields and monotonic start before sending. Failed
raw sends retain the attempted wait; incomplete frames remain unrecorded.
No native acceptance is inferred from a send attempt.

The identical focused RED/GREEN command was:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/unit/test_macos_control_state.py -q
```

- RED: exit 1; four failed, 30 passed in 1.66 seconds. Failures were the
  before-send history assertion, complete-send-failure history retention,
  newest-64 raw history retention, and complete-wait controller state output.
  Log: `/private/tmp/specfact-4171361951-red.txt`.
- Final GREEN: exit 0; all 34 passed in 0.08 seconds. Tests also exercise ordinary
  request history bounding, valid owned-worker state integration, unchanged full
  and partial frame bytes, and omission for both partial cases on successful and
  failed sends. Log: `/private/tmp/specfact-4171361951-green.txt`.
- Scoped Ruff lint and formatting checks passed for the two owned Python files.
  Final `control.py` length is exactly 1,000 lines (starting length: 996).

Only `scripts/macos_managed_boundary/control.py`,
`tests/unit/test_macos_control_state.py`, and appends to
`CONTROL_BOUNDARY_CONTRACT.md` and this evidence file were changed by this slice.
No C, other tests, protocol/deadline behavior, signed payloads, commit, push,
GitHub comments or local CodeRabbit upload. Broad suites, actual normal hooks
and native cancellation verification remain parent-owned and unclaimed here.

Confidence: High for the bounded history correction, based on failing-before
and passing-after focused evidence. Limit: tests mock transport; they do not
establish hosted native lifecycle acceptance. Failure modes: a failed send is
only an attempt (native state still requires a valid owned snapshot); a partial
frame must never look accepted (both partial cases tested); eviction of an old
launch can prevent PID mapping (existing fail-closed omission remains intact).
Assumption: the launch record is retained when worker-state mapping is needed.
Focused test runtime is under two seconds; no native jobs are created. Rollback:
revert only this history/helper slice and its tests, and remove these appended
contract/evidence sections after checking the parent's concurrent changes.

## Bounded owned-child completion — 2026-10-03

Hosted run 37089687409 at head 1a0b68d9 passed 600 startup races on all three
macOS versions and all 1,219 control records on macOS 15. macOS 14/26 failed
cancel/request-wait after 69/29 complete lifecycle rounds respectively. Both
last-observed snapshots had wait_accepted and wait_pending true, worker_reaped
and output_closed false. These do not establish the underlying notification or
kernel root cause. CANCEL_COMPLETION_CONTRACT.md specifies the bounded status
reconciliation correction and preserves the independent kernel cleanup proof.

After the specification, deterministic ad-hoc signed ARM64 event-loop tests
failed three cases with twelve passing, rejecting the unbounded select sleep.
The implementation limits the requested sleep to 50 milliseconds only while a
registered direct child is unreaped; earlier deadlines remain unchanged.
New positive controls retain a 10 millisecond worker deadline, avoid idle polling
for empty/reaped registries and cover a reaped first child with a later active
child. A missing-notification fixture executes the actual cancellation request
and trace-stop continuation, then checks returned signal/reason/captured output
without additional kill signals. Its clock and system operations are safely
mocked; it is not a scheduler, resource or kernel-death timing measurement.

Focused final native event/timer/state/controller suite: 100 passed in
10.77 seconds. Formatter and type checks passed. The requested independent
review-agent found no actionable defects; full native repetition and repository
gates remain separate proof obligations before this revision is finalized.

Final frozen-source validation of this correction:

- Physical Mac17,9, macOS 27.0.1 build 26A434, ARM64: all 1,219 control records
  passed (twelve-by-100 lifecycle cases and nineteen protocol checks). Receipt
  `.specfact/native-compat/pr489-reconcile-control-100.json`, SHA-256
  `16ed0adf14f2444023f0571d789beb8d0412b6c46435b43fcc934ff209f528ae`.
  Production approval and full signed-boundary verification remain false.
- Native-enabled focused suite: 230 passed without skips in 13.51 seconds.
- Serial smart/full suites: each 3,698 passed, twenty-five skipped and
  63 subtests passed, in 266.03/272.31 seconds. Twenty-four native opt-in skips
  were separately exercised above; one proc-descriptor test needs Linux.
- Format, typing, lint, YAML, imports, public-key signature/version verification,
  twenty-eight contract tests, both strict OpenSpec changes, planned requirements
  evidence mappings, Markdown and smart coverage checks passed. The independent
  follow-up review found no defects after the added completion/multiple-child
  positive controls. Normal hooks and current-head hosted review remain required.

The exact cause of the earlier hosted cancellation stalls remains unproven.
The bounded completion contract is demonstrated separately; this local proof
does not approve the supported OS matrix or production capsule integration.

## Owned Mach signal transport — 2026-10-03

The preceding completion revision did not fix hosted run 37092073540:
macOS 14, 15 and 26 all failed during request-wait. Preserve those failures;
the kernel cause remains unproven. MACH_SIGNAL_CONTRACT.md and the native
scenario/mapping were added before tests or implementation.

RED: eight missing native admission-fixture errors in
/private/tmp/specfact-mach-red.log; SDK build helper had 15 missing-helper
errors in /private/tmp/mach-build-red.txt. GREEN: eight signed native admission
checks and 18 SDK-build/provenance tests. These mocks cannot approve runtime
acceptance. Generated callback ABI was actually compiled with the selected SDK.

The control broker now installs private EXC_SOFTWARE ports through spawn
attributes before worker execution. The fixed worker establishes PT_TRACE_ME
and PT_SIGEXC before its initial stop. SDK MIG decoding requires kernel sender
provenance, the registered child task and a member thread. Initial SIGSTOP alone
is suppressed; runtime signals use PT_THUPDATE and terminal wait status stays
separate. Held initial replies remain owned until cancellation or broker death.
BSD compile-time mocks retain historical transition tests only; no runtime
fallback is available. Capture hashes of the top-level SDK defs, generated
server/headers and both owned includes; transitive SDK headers remain resolved
through the selected SDK and are not claimed as a fully snapshotted closure.

Actual exact ad-hoc hardened build on Mac17,9, macOS 27.0.1 build 26A434,
ARM64, empty entitlements: 1,219 checks passed (12 lifecycle cases x 100 plus
19 protocol checks). Every repetition gate passed; maximum independent
observation was 1.160949 seconds, below five seconds. Receipt stays ignored:
.specfact/native-compat/pr489-mach-control-100.json, SHA256
e6d27d80b00a709edc1173eede80de00204aa5f059cf8e4f0763bf475d9a32a4.
Log /private/tmp/specfact-mach-control-100.log stays local.

Focused native suite: 256 passed in 17.34 seconds. An additional held-stop
cancellation test initially used the running-worker observation mode and failed
on its missing-output marker; selecting the existing held-stop observation mode
produced 47/47 control tests passing in 14.53 seconds, including that new case.
No mechanism or acceptance bound was weakened.

Independent exact review-agent security/defect review of the entire uncommitted
Mach slice reported No findings, with medium confidence and hosted/production
evidence gaps retained. Format, types, lint, YAML/import checks, all seven
module signatures, 28 contract tests, strict validation of both changes,
Markdown and actionlint passed. Full repository results and current-head hosted
acceptance are recorded separately below after completion.

This is a fixed-fixture boundary checkpoint, not production enablement. The
public command, all-ten sealed analyzers, four-manager corpus, complete escape
and resource proofs, registry/customer installation and final artifact admission
remain pending. Code Review remains 0.50.1; no signed module payload changed.
No merge or GHCR publication. Rollback restores the experimental control
transport and retains this failure history; it grants no BSD fallback support.

Serial smart-test: 3,716 passed, 34 skipped and 63 subtests passed in 271.20
seconds. Native opt-ins above exercise the newly skipped native cases. The
existing Linux descriptor proof still requires Linux.

Serial full test: 3,716 passed, 34 skipped and 63 subtests passed in 271.46
seconds (/private/tmp/specfact-mach-full.log). Smart/full suites were serialized;
no analyzer-cache writers overlapped them. Planned requirements-evidence
mapping passed and intentionally reports implementation evidence not yet
available for the complete change.

The actual public capsule command was also rerun: `hatch run specfact code
review run --enforcement changed --bug-hunt --json --out .specfact/code-review.json`.
It produced FAIL/UNKNOWN with unsupported_controller_platform for every
required analyzer. The ignored report is preserved separately as
.specfact/native-compat/pr489-mach-public-capsule-unsupported.json. This is
an explicit production limitation, not a passed native capsule gate. The
normal staged-file repository quality review remains a separate check.

The first host quality review found CC17 and six non-contract warnings in the
build helpers/tests. Cohesive helper extraction reduced prepare complexity
from 17 to 2 and removed all non-contract findings. The exact commands,
callback ABI, phase/provenance contracts and leaf C sources are unchanged.
Final native focus: 257 passed in 18.77 seconds, including held-stop
cancellation. Final independent review-agent again reported No findings.

A concurrent lint/cache writer invalidated one manual review snapshot; that
FAIL/UNKNOWN is not counted as quality acceptance. The serial explicit-file
review with --enforcement changed --bug-hunt returned PASS_WITH_ADVISORY,
33 MISSING_ICONTRACT findings only and zero blocking/clean-code findings. The
existing narrow standalone standard-library experiment exception in
NATIVE_COMPATIBILITY_RESULTS.md applies to these build helpers as well; it
grants no runtime or capsule acceptance. Markdown checks passed with MD013
excluded for historical long evidence lines; the new contract passes defaults.

Final post-refactor serial gates: smart-test 3,716 passed, 34 skipped and
63 subtests passed in 267.52 seconds; full test the same counts in 271.69
seconds. Logs /private/tmp/specfact-mach-final-smart.log and
/private/tmp/specfact-mach-final-full.log remain local. No quality/cache writers
overlapped these final suites. Final lint/types passed after refactoring.

## Owned reply cleanup and socket startup evidence — 2026-10-03

Head 030debe183e9a487868a781cc330e3fe6a0e42a9 hosted native run
37095618367 passed complete signed startup/control acceptance on macOS 14
(job 111124815166) and macOS 26 (job 111124815026). macOS 15
(job 111124815209) passed all six startup races x 100 and all 19 protocol
controls, then failed bootstrap-socket after 58 complete lifecycle rounds.
The sanitized RuntimeError alone does not identify the readiness condition.
Do not erase this failure, claim its cause or increase/retry the three-second
readiness budget. All repository CI checks passed at this head.

CodeRabbit completed review 5398975693 at 04:22:32 UTC, covering 1a0b68d9
through 030debe1, and raised valid finding 4171673257: a cancelled worker can
lose its owned kernel reply destination before send. Independent inspection of
Apple XNU libsyscall/mach/mach_msg.c (accessed 2026-10-03) distinguishes
recoverable sends from errors that may have partially consumed rights. The
shared reply helper disposes invalid-destination/timeout/interrupted replies;
invalid destination is benign, while all other errors fail closed. Unrecoverable
errors rely on process cleanup to avoid double-destroying rights. Both held
and ordinary validated replies use the helper. Only waitpid establishes
terminal status. This narrows the reviewer suggestion to Apple's ownership
contract, rather than blindly destroying every failed send.

Specification preceded tests and code. RED reply fixture: eight admission
checks passed and four missing-fixture errors; GREEN: all five safe reply
cases pass, including the added interrupted-send case. RED held lifecycle
scenario: the missing cancel operation produced timeout status instead of
accepted cancellation. The separate cancel-held-stop case now retains kernel
birth/tracing observation, SIGKILL/cancel status and the five-second bound,
and is mandatory at 100 repetitions in local/hosted acceptance.

RED readiness producer: two failed, 43 passed, four native skips; GREEN:
45 passed and four native skips. Controller/CI projection RED: 12 failed and
75 passed; GREEN: 87 passed. Fixed categories are exported only for the
original owning bootstrap-socket failure; unknown/foreign/malformed values,
other phases and raw authority/path/error fields are omitted. This is
diagnostic evidence only, not a startup fix or new acceptance.

Combined final native-focused suite: 311 passed in 19.36 seconds, no skips.
Independent exact review-agent security/defect review reported No findings,
medium confidence, with fresh signed acceptance and macOS 15 diagnosis pending.
Formatting, types/lint and whitespace checks pass. Raw logs/receipts stay local
and ignored. The complete native capsule remains unimplemented; production
flags stay false, module version/signatures unchanged, no merge/publication.

Fresh signed physical acceptance: all 1,319 records passed (13 lifecycle cases
x 100 plus 19 protocol controls), including 100 cancel-held-stop observations.
Maximum independent cleanup observation: 1.170468 seconds. Receipt
.specfact/native-compat/pr489-owned-reply-control-100.json stays ignored, SHA256
82a51b4cfae21ada7fc8ecddbad52cb76f3b91af680c16ef568cce12bda1e7f9.
The final broker inventory includes the new reply header digest.

SpecFact found duplicated native fixture setup; the test uses one parameterized
signed fixture now, with all 13 C admission/reply cases passing. Final serial
explicit-file --enforcement changed --bug-hunt review is PASS_WITH_ADVISORY:
only documented standalone-script MISSING_ICONTRACT advisories, zero other
findings. These are repository quality checks, not production capsule proof.

Final serial repository verification: smart suite 3,764 passed, 40 skipped,
65 subtests passed in 265.34 seconds; full suite the same counts in 272.70
seconds. Native-only skips in these portable runs were executed separately
in the 311-test explicit native suite. The explicit-file host review has
33 MISSING_ICONTRACT advisories covered by the existing narrow exception.
No other findings or clean-code regressions remain. YAML/import boundaries,
seven unchanged module signatures, actionlint, strict validation of both
linked changes and Markdown (historical line-length exemption only) pass.

## Explicit launchd socket owner — 2026-10-03

Hosted head b44a4afa passed all startup races and full control on macOS 15/26;
macOS 14 failed bootstrap-socket with socket_owner_invalid after 22 complete
rounds. The public fixed-category diagnostic established owner mismatch, not
the numerical UID or transition timing. The contract was revised first to
request documented SockPathOwner=the invoking UID and observe ownership/mode
within the original three-second deadline. No unsafe endpoint is usable and
no chmod/chown, bootstrap retry or deadline extension was introduced.

RED before implementation: seven failures, 45 passed, five native skips and
45 passing subtests, covering missing owner configuration and readiness
transitions. GREEN explicit native focused suite: 213 passed, 49 passing
subtests, no skips, in 20.73 seconds. Independent exact review-agent
security/defect review: No findings, medium confidence; hosted ownership timing
and fresh signed acceptance were still pending at review time. Final serial
SpecFact explicit-file --enforcement changed --bug-hunt host review:
PASS_WITH_ADVISORY, 32 MISSING_ICONTRACT advisories covered by the existing
standalone stdlib experiment exception, no other findings or clean-code
regressions. Types/lint, YAML/imports, seven unchanged module signatures and
strict change validation pass. C/signing/lifecycle remain unchanged.

Fresh exact ad-hoc hardened physical run: 1,319/1,319 records passed, every
one of 13 lifecycle cases at 100 repetitions, maximum independent observation
1.167821 seconds. Ignored receipt
.specfact/native-compat/pr489-socket-owner-control-100.json SHA-256:
5c7970a2e49809b7607837e2eed0a6835831c32d3625f0408f322583d43095b1.

The first smart run returned UNKNOWN rather than FAIL in one existing mocked
capsule verdict test while tracked evidence documents were being updated.
The exact isolated test passed in 13.73 seconds; no verdict code was changed.
Concurrent workspace mutation is a hypothesis supported by the existing
snapshot guard, not a reproduced root-cause trace. With tracked files frozen
and no overlapping analyzer-cache writes, serial smart and full suites each
passed 3,767 tests, 40 skips and 67 subtests. All native-only skips for the
touched startup/control scope were separately executed in the focused suite.
Historical failed evidence is retained; fresh hosted acceptance remains pending.
No production capsule, module version bump, merge or publication is claimed.

## Image-bound executable handoff — 2026-10-03

The bd173218 checkpoint passed startup and control on all three hosted ARM64
versions (run 37099551157). CodeRabbit completed actual review through that
head with no actionable comments; this was fixed-fixture acceptance only.

Before the new implementation, a private exact ad-hoc hardened witness proved
that confined exec into a signed fixed target died with SIGTRAP 5 before
`target-entry`, while both unsandboxed positive controls succeeded. Three
bounded trials retained source, final bytes, native signatures and independent
absence in /private/tmp/mach-exec-witness-20261003-a/safe-receipt.json; no raw
runtime evidence was uploaded. EXEC_BOUNDARY_CONTRACT.md was written first.

RED: seven new policy cases lacked their native fixture; initializer-ordering
acceptance failed because the verifier did not yet exist. GREEN policy:
20 signed native policy/reply cases pass. The new controller additionally
requires actual image-stop evidence before target initializers, genuine traps,
failed exec, a second replacement, altered-target rejection and six distinct
exec lifecycle races. Full signed physical/matrix proof is still pending.

The initial real handoff tests reached dynamic verification but then exited
with SIGABRT 6 before initialization. The macOS 27 crash stack ended in dyld
libignition. Granting file-read access to the exact root directory, as in the
existing sealed-analyzer profile, made both native tests pass while host-read,
network and fork denials remained effective. This establishes the tested grant's
behavior; the crash stack alone does not prove the underlying denied syscall.
No root descendant, all-/System or Data-volume alias grant was added.

GREEN native image/signal/lifecycle tests: 3 passed in 5.78 seconds. Corrupt and
validly signed wrong-image targets both reject before spawn. The full affected
explicit-native suite passed 343 tests without skips in 28.04 seconds. The old
seven-input inventory assertion first failed and was updated to require eight,
including the captured image-policy header. Independent exact review-agent
review and final incremental review: No findings, medium confidence. Remaining
proof gaps include live Security lookup/unknown-image failures and durable
per-lifecycle image-stop markers; these are not claimed as complete admission.

Fresh physical ad-hoc hardened acceptance on Mac17,9, ARM64 macOS 27.0.1 build
26A434: 1,925/1,925 records passed (19 lifecycle cases x 100 plus 25 protocol
controls), maximum independent cleanup observation 1.166803 seconds. The full
run took 693.785 seconds, within the unchanged 720-second CI helper ceiling.
Private ignored receipt .specfact/native-compat/pr489-exec-control-100.json:
1,425,607 bytes, SHA-256
0d181667616179d44002a784c205979207cc06f82184473d73a61955a152ed6b.
The strict v2 hosted receipt validator accepted this actual receipt, including
four artifact/source bindings, shared probes, eight broker inputs, two target
substitutions and all new handoff/lifecycle results. Production flags stay false.

Repository smart/full suites passed serially with tracked files frozen: each
3,876 passed, 49 skipped and 87 subtests; smart 270.88 seconds, full 276.78
seconds. The touched native skips were explicitly exercised separately. Format,
types/lint (10/10), YAML/imports, seven unchanged module signatures, 28 contracts,
actionlint, strict validation of both linked changes and planned evidence mapping
pass. The initial signature command lacked its public key configuration; the
established repository verification key resolved that prerequisite, with no
payload changes. Fresh hosted matrix and actual current-head GitHub review remain
required before checkpoint completion. Full #460 delivery remains unfinished.

Final review corrections: the extracted receipt checker initially produced
complexity/style findings and the controller's new observation loop exposed
optional-value typing errors. Cohesive validation functions, explicit fail-closed
None handling and smaller test cases resolve every non-contract finding.
A real Python -O subprocess accepted an empty receipt before the new optimization
guard; afterward the guard rejects before jobs or admission. Independent review
confirmed both -O and -OO rejection with no native jobs. All 170 receipt tests
and the actual 1,925-record receipt remain accepted in normal mode.

Final serial explicit-file SpecFact --enforcement changed --bug-hunt:
PASS_WITH_ADVISORY, exactly 44 MISSING_ICONTRACT advisories, zero other findings
or clean-code regressions. The existing narrow exception covers these private
stdlib-only experiment/CI helpers: adding an icontract dependency would violate
the dependency-free hosted proof; runtime checks and failing-first tests remain
mandatory. A separate narrow R1732 suppression documents unittest.enterContext's
actual teardown ownership; it does not suppress production resource cleanup.
Final independent exact review-agent and incremental reviews: No findings,
medium confidence; hosted acceptance and the recorded remaining proof gaps persist.

After all review fixes, the explicit native startup/control/receipt suite passed
386 tests with no skips in 30.17 seconds. Final frozen serial smart and full
suites each passed 3,879 tests, 49 skipped and 87 subtests; smart 267.38 seconds,
full 273.37 seconds. Native skips for the touched scope were exercised separately.
No native C, signing or sandbox-policy changes were made after the 100-round
physical proof; the Python verification refactor was rechecked against its receipt.
No full native module enablement, merge, publication or #460 completion is claimed.
