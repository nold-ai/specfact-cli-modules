# Current candidate-tool evidence — 2026-09-30

## Approved local pytest policy — 2026-10-05 (Europe/Berlin)

The human explicitly approved the previously rejected local compatibility
patch. Eight regressions were RED before implementation. Local project-origin
pytest now retains `--doctest-modules` and coverage exclusion expressions;
multiline INI values become continuation lists, including section-like text.
Protected/unknown assurance modes and coverage plugins remain rejected.
Report-only `.coveragerc` files are located rather than silently discarded.
The affected projection/receipt/scope suite is GREEN (**209 tests**); full
format/type/lint gates pass with no type errors.

The rebuilt private native CPython 3.11.16 candidate
`sha256:6d26c4873dd96d7f629d11bd233d6cd1f3c5080e988bb41892548b323f12a087`
prepares the original pinned Requests checkout cold and verifies offline reuse.
All ten analyzers execute; pytest coverage is PASS with project-origin-v1
provenance. The overall review is genuinely FAIL from independent findings.
This does not admit protected evidence or a published customer artifact.

Flask passed preparation and coverage-policy projection, then exposed pytest's
scratch-directory symlink at the subsequent controller handoff. Three safety
regressions were RED. The completed-worker scratch correction unlinks owned
aliases without following them, prunes directory links, preserves target
bytes/modes and leaves substituted linked receipts missing. Default rejection,
hardlink/special-file and foreign-owner rejection remain. The affected native
runner/execution/snapshot/receipt suite is GREEN (**114 passed, 9 explicit
maintainer proof skips**). The original pinned Flask checkout subsequently
prepared cold, reused offline and executed all ten analyzers with pytest PASS
at private candidate `c6b2…`; Requests repeated the same complete execution.
Their overall verdicts remain FAIL from actual independent findings.


The confined pytest plugin loader now preserves project distribution metadata,
so `required_plugins` validates actual versions. Independent review exposed
three P2s (missing plugin metadata, TOML threshold parsing, and supplementary
Unicode serialization); meaningful regressions were RED and the affected suite
passed **145 tests** after correction. Independent closure confirmed all three
fixes. Local multiline patterns preserve Coverage defaults and cannot inject
configuration sections. Approval above supersedes the historical pending
approval descriptions below.

The native profile permits only the two exact read-only CPU topology selectors
needed by xdist. The physical capsule fixture returned both positive counts
and received `EPERM` for `hw.memsize` (**1 native test passed**). No arbitrary
sysctl access, resource limit or direct-spawn permission was added.

Real Poetry parallel tests then exposed inert missing `sys.path` entries and
a binary-stream `.buffer` collision with execnet. Each actual failure preceded
a focused RED regression; the corrected managed-child suite passed **70 tests**.
Missing paths are omitted, existing paths retain canonical/grant checks, and
internal pending bytes no longer shadow the public stream interface. The next
actual run hit the unchanged eight-worker capacity because `-n logical` chose
18 workers. A RED regression preceded a native xdist automatic preference of
four, retaining test selection and explicit counts. The subsequent original
Poetry slice executed all ten analyzers with pytest PASS. This does not erase
the intermediate failures or establish the complete release corpus/matrix.

The full repository run before these final corrections reported 4,890 passed,
73 explicit skips and two failures: a stale exact-selector test and environment
leakage in direct worker-entrypoint test fixtures. The corrected focused
regressions pass **20 tests**. The next full run passed **4,897 tests**, with
73 explicit skips and 95 subtests. That run preceded the final plugin/uv
corrections; a fresh final full-suite gate remains required.

## Confined plugin compatibility closure — 2026-10-05 (Europe/Berlin)

Original Poetry parallel execution exposed project plugin discovery in execnet
children. Specification and failing regressions preceded the lazy pytest config
adapter. Entry-point discovery remains limited to the verified project site;
ambient autoload stays disabled. Independent review found two additional P2s:
dependency-free children inadvertently requiring pytest, and duplicate explicit
plugins. Three regressions were RED before correction. The deferred import
adapter now preserves both cases and plugin distribution metadata.

Original Hatch then exposed pytest-rerunfailures 14.0's localhost socket, which
remains denied. The version-specific adapter replaces only failure-count IPC
with an opaque-token, invocation-private SQLite store. Upstream rerun selection,
counts and reporting remain active. Invalid path tokens, concurrent increments
and file identity checks have focused coverage. A non-default 64 KiB SQLite
page-size regression was RED before deriving the four-MiB page limit from the
actual page size. No network or direct-process permission was added.

Hatch's original fixture also needed executable discovery for packaged uv.
Specification and a RED regression preceded discovery from the verified capsule
image; host PATH, mutable images and foreign paths remain rejected. Existing
Git discovery uses the same image validation. The latest affected suite passed
**124 tests**; full formatting/type/lint checks passed. The independent
review-agent reported no findings in the uv scope, confirmed closure of both
plugin P2s, and reported no additional SQLite transport findings. Its source
checks included 512-byte, four-KiB and 64-KiB page budgets and oversized-write
rollback; physical concurrency was covered by the author, not independently.

Actual Hatch executed all ten analyzers with pytest PASS. A separate ephemeral
flaky uv fixture ran two managed xdist workers and reported **one passed, one
rerun**. Strict observer/JUnit/process reconciliation rejected its conflicting
evidence as UNKNOWN. That rejection is preserved: successful retries do not
hide earlier failures or satisfy complete pytest evidence.

Supplemental Linux regressions passed **279 tests** in an x86-64 userspace
container on an ARM64 Docker guest with networking disabled and a read-only
checkout mount. This is emulated supplemental validation, not native x86-64
release acceptance. The unchanged container namespace probe returned EPERM;
no privileged mode or relaxed security profile was used to override it.

The final candidate and final repository results are recorded separately below.
Publisher/module keys remain in CI/CD. No normal hook bypass, synthetic signed
catalog admission, merge, publication or release acceptance is claimed.

## Final-build runtime checkpoint and quality refactor — 2026-10-05

The reviewed private candidate
`sha256:0fb55479b6081a34804f2191b64469f9b94eef184bc277e75e90a616616cf278`
completed cold preparation, verified offline reuse and all ten analyzers on
unchanged pinned Requests/pip, Flask/uv, Poetry and Hatch source/test slices.
Pytest evidence was PASS for each; genuine independent findings retained their
FAIL verdicts. Automatic uv discovery with the ARM64 extension returned PASS.
All four upstream caller checkouts remained clean. This is physical macOS
27.0.1 build 26A434 / CPython 3.11.16 candidate evidence, not authenticated
customer distribution or the complete release matrix/corpus.

Manifest checksum/version/public-key verification passed for seven manifests,
as did YAML, bundle imports, strict OpenSpec for native and Windows changes,
planned evidence mapping and 28 contract tests. An unfrozen full run reported
one UNKNOWN-versus-FAIL assertion and 4,903 passes; a documentation edit during
that run could invalidate its captured worktree. The unchanged assertion passed
in isolation. With tracked files frozen, the full `hatch run test -q` gate passed
**4,904 tests**, 73 explicit skips, five warnings. No assertion or integrity
condition was weakened. This full result predates the quality refactor below.

Actual confined native static analysis of the three core worker/adapter files
and plugin helper exposed complexity/nesting, diagnostic and naming findings.
The executable dispatch sites were independently reviewed: Python -c/stdin
and the controller-generated pytest observer intentionally execute code only
inside broker-admitted, image-verified, confined workers. The two statements
receive a narrowly documented intentional-use exception; the source text or
Python namespace is never treated as a security boundary. No security rule was
changed and this classification does not approve artifact admission.

The complexity fixes separate exact argument/environment/image/alias/SCM
checks, bounded stream progression, child startup phases, fixed-tool inventories,
import-cache classification and execution/state restoration. Every admission
predicate is retained. Existing affected behavioral tests pass **149 cases**;
formatting, types and lint pass. Standard subprocess compatibility names and
its fixed `run` keyword signature remain intentional interface requirements,
not generic application APIs; contract predicate wrappers retain their named
argument binding. These limited style exceptions do not waive real defects or
the required authenticated reviewer gate. Fresh native and repository results
for the refactor remain required below.

## Project-driven runtime correction — 2026-10-05 (Europe/Berlin)

The physical ARM64 Mac (macOS 27.0.1, build 26A434) ran the corrected CPython
3.11.16 candidate `sha256:78a10f2b7a03ab720b11838e829a38550fd2bafd65e31c123354e72bb0832a20`.
An automatically discovered uv project prepared cold and reused its verified
cache offline without caller configuration or a publisher project catalog.
All ten analyzers executed and returned PASS, including pytest coverage and a
compatible ARM64 native-extension import. This private ad-hoc proof does not
authenticate a customer publication or extend the supported release OS matrix.

Authentic Hatch now prepares and reuses its private environment offline. Its uv
installer needed the stable admitted wheelhouse and an explicit verified
private interpreter alias instead of the capsule's read-only interpreter.
Bounded project-origin SystemExit receipts preserve installation failures.
The affected Hatch/hooks/managed-process suite passed **122 tests** with types
and lint clean; independent review found no further defects in that correction.

The original Requests partial clone exposed unnecessary historical-blob export.
The contract preceded a meaningful RED (one failure, one negative control pass).
Export now retains available bound objects while requiring all history metadata
and complete selected/index source trees, with no lazy fetching or remotes.
All **61 VCS tests** pass; focused types/format/lint pass. Independent review
reported no findings in this narrow change. Fresh Requests, Flask and Poetry
cold preparation/offline reuse and all nine independent analyzers passed their
execution checks at candidate `sha256:86e45756a0ace3df76644f54b8a1c5495758d42e49541e70dcbe3e84450df192`.
Their reviews remain FAIL with required pytest evidence incomplete because the
local policy compatibility patch is awaiting user approval; no fixture was
removed or outcome relabelled.
The original pinned Hatch partial clone also completes cold preparation and
offline reuse at candidate `78a10f2b…`, with all nine independent analyzers
executing and the same explicit coverage-policy limitation. All four upstream
caller checkouts remain clean after preparation and review.

The remaining independent runtime review reported five P2 defects. Registry,
cache-path and archive regressions reproduced four RED failures; PAX allocation
and global-header regressions reproduced two more. Streamed bearer responses,
absolute leases and bounded header/member enumeration now pass **122 tests**.
Types, format and lint pass, CPython 3.11 successfully round-trips an ordinary
PAX archive, and an anonymous exchange with the existing public SpecFact GHCR
repository accepted the actual streamed token response (HTTP 200, identity
encoding; no credentials or token were exposed).

The remaining analyzer-view omissions and full wheel ABI corrections have their
own spec/RED/GREEN evidence in `ANALYZER_VIEW_WHEEL_ABI_CORRECTION_CONTRACT.md`
(**130 tests**, including the existing member-view caller regression). Final
independent closure review found no further production defects across all five
corrections; its draft-only multiline INI finding was retained for the later
approved local policy work. Module/publisher keys were not used;
production/publication flags remain false. Final repository, independent
installation, macOS/ABI and Linux VM acceptance are not claimed here.

## Independent preparation review corrections — 2026-10-05 (Europe/Berlin)

The separate Git/assembly review found a relative-cwd Git selector issue and
two builder defects. Assembly ownership tests reproduced deletion of another
invocation's outputs (2 RED failures); a reserved signing-component test was
RED because input members were overwritten. Cleanup now checks invocation-owned
file identities, and the generated signing component cannot collide with input.
The affected assembly/build/Git/parity suite is GREEN (**122 passed, 19 subtests**).
The relative-cwd fix is handled alongside the authentic Hatch uv handoff.

The Git relative-cwd correction passes its focused managed-process tests.
Independent closure review reports **No findings** for all three assembly/Git
P2s and verifies that the assembler CLI starts outside the repository without
PYTHONPATH. The two assembly/build suites pass **87 tests** after the CLI
regression; focused script types and lint pass. Remaining backend/worker review
and actual Hatch installation diagnostics are still in progress.

Closure review found four additional compatibility gaps. Explicit-root,
hash-mode and uv-copy tests were RED (3 failures, 3 passes); ancestor-workspace
and bounded-subdirectory tests were RED (7 failures, 1 pass). Workspace hooks
now retain the full sanitized snapshot and execute from a bounded member
subdirectory; imported member roots augment explicit root paths. uv preserves
executable status, and local wheel hashes follow the caller's existing hash
mode. The combined affected suite is GREEN (**95 passed**), including actual
offline pip resolution with and without hashes and negative member containment.
Independent closure review reports **No findings** for the frozen preparation
surface and confirms all nine findings from both passes are closed. The final
integrated preparation/discovery/analyzer run passes **312 tests**. This does not
cover the separate Git/assembly work or supersede release gates. UTM is installed
locally, but its guest inventory did not return; no VM acceptance is claimed.

The independent review identified five concrete defects. Focused regressions
first failed for workspace wheel resolution, workspace source-root binding,
executable-mode copying, missing pip VCS context and signature-check timeouts.
Explicit local wheel candidates now participate in dependency resolution before
index lookup; the complete local wheel collection binds workspace imports.
Snapshots retain sanitized VCS context and executable status without granting
direct process creation. Signature-check timeouts return bounded diagnostics.

The combined affected suite passed **179 tests** after these fixes. A subsequent
namespace-backend origin regression was RED (one failure), requiring a verified
file origin for a declared backend path; the leaf suite then passed 8 tests.
The final integrated preparation/discovery/analyzer suite passed **304 tests**;
focused types and lint pass. The broad type check has only the two expected
missing-parameter errors in the pending policy regression. These are preparation proofs, not
release acceptance. The pending local pytest policy proposal is excluded from
this result and remains unimplemented pending approval.

## Hatch workspace and matrix correction — 2026-10-05 (Europe/Berlin)

- The unchanged upstream Hatch corpus first failed with `Unknown environment:
  hatch-test`; matrix-root regressions were RED (3 failures), then GREEN (11).
- The next physical attempt exposed a local workspace dependency incorrectly
  sent to index acquisition. Containment/workspace regressions were RED (6),
  followed by controller integration RED (2). The combined focused Hatch suite
  is GREEN (19 passed, 51 deselected), retaining negative path tests.
- Matrix selection uses authentic Hatch-generated configurations for the admitted
  ABI; workspace builds and original manager installation remain confined.
- This scoped GREEN does not establish upstream Hatch installation acceptance;
  confined SCM and offline native uv execution are still being verified.

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

### Hosted handoff and review correction

On 2026-10-03 (Europe/Berlin), native ARM64 macOS 14/15/26 run 37106053209
passed the complete startup/v2-control fixture suites at f7af7916; each row
passed 600 startup trials and 1,925 control checks. Exact platform, merge-tree
and sanitized check identities are recorded in NATIVE_BOUNDARY_CI.md.
CodeRabbit actually reviewed f7af791678e768b8d1786864fe871c3ae0f5ca10 at
09:33 Europe/Berlin (review 5399554719, run a00857b1-f317-4105-8b13-c461187ba150).
Its one outside-diff minor finding identified a stale required-evidence checklist
still using the old twelve-by-100/nineteen counts. Independently comparing that
checklist with the v2 checker confirmed the issue. The checklist now requires
nineteen-by-100 lifecycle cases, twenty-five protocol checks and four control
signed-artifact digests. This is a documentation correction; no native source,
profile, signing configuration or receipt behavior changed. Strict OpenSpec,
Markdown and whitespace checks pass. Normal commit hooks remain required.
No full native capsule enablement, shipment or #460 completion is claimed.

## Four-manager native project-corpus acceptance slice — 2026-10-03

The project-corpus contract was added before executable tests. It binds the
existing `tests/fixtures/portable-runtime/corpus.json` pip, Hatch, uv and Poetry
entries to fixed versioned plans, separates preparation from execution, and
requires actionable incomplete evidence for unadapted spawning with no host
fallback. It also requires actual pytest, explicit plugin, coverage and generic
ARM64 extension-import evidence before a prepared-project execution can pass.

RED: `hatch run pytest tests/unit/test_macos_project_corpus.py -q` collected
18 cases; 17 failed because `project_corpus.py` did not exist and the physical
case skipped because no candidate was selected. This established that no native
four-manager plan or project observer implementation existed.

GREEN: the focused suite with `SPECFACT_MACOS_PROJECT_CANDIDATE` bound to the
verified private CPython 3.13 candidate passed 20/20. The combined project-corpus
and managed-subprocess regression run passed 36, with one unrelated Semgrep
maintainer-input case skipped, in 5.28 seconds. The physical case used native ARM64 macOS 27.0.1
build 26A434 and CPython 3.13. It ran separate preparation and execution workers
through the signed broker, executed one pytest test, loaded the explicit
`fixture_plugin`, wrote coverage for the declared project source and imported
the sealed generic ARM64 `_cffi_backend` extension. The public assertion records
only booleans, ABI/architecture and production-false status; raw stages remain
private.

Focused BasedPyright completed with zero errors, warnings or notes. Ruff lint,
format, whitespace and strict OpenSpec validation pass. Unit transport cases
exercise all four fixed manager plans and reject unknown managers, traversal,
project-selected argv, missing or mismatched pinned source identity, cross-domain
or unverified responses, malformed evidence and unsupported spawning.

This is not complete upstream-corpus acceptance. The current sealed candidate
does not yet contain admitted pip/Hatch/uv/Poetry preparation adapter images, so
their real pinned dependency/build-hook executions cannot be broker-launched by
this scoped harness. The result remains production-ineligible until those exact
adapter artifacts are added to the native payload and all four pinned upstream
projects pass this transport on every supported macOS/ABI row.

## Package provisioning and backend-selection slice — 2026-10-03

Scope was restricted to the package-native manifest/cache verifier, backend
selection, the existing runner platform seam, directly mapped tests and the
OpenSpec scenarios. Native C/control files, module metadata, versions and
publication inputs were not changed by this slice.

Specification was updated first with ABI-specific no-artifact and native-signing
scenarios. Initial collection RED reported two missing package modules. After
interface-only placeholders, behavioral RED completed with 20 failed and one
passed test; every failure was an explicit `NotImplementedError` or missing
runner dispatch. No production behavior existed at that checkpoint.

Focused GREEN: 25 tests passed in 0.31 seconds. Coverage includes Darwin ARM64
CPython 3.11–3.13 identity derivation, preserved Linux selection, unsupported
ABI/platform rejection, empty and admitted catalogs, no host fallback, signed
manifest authentication, exact payload/closure/signing binding, cold and offline
verification, interrupted and concurrent atomic installation, corruption and
signature mismatch rejection. A physical ARM64 macOS test copied `/usr/bin/true`,
applied an ad-hoc hardened-runtime signature and read back its identifier,
CDHash, mode and runtime flag through the production inspector.

The original script candidate's 42 cache-invariant tests passed in 0.67 seconds.
Focused Ruff format/lint and BasedPyright completed with zero findings. Strict
OpenSpec validation passed. Expanded runner attempts exposed existing
order-dependent mocked snapshot evidence (`UNKNOWN` and missing pre-enforcement
fields); the exact initial failure passed in isolation. The final expanded run
was stopped at the owner's instruction to finalize only the bounded focused
slice. Those attempts are retained as non-green, out-of-scope evidence and are
not claimed as regression acceptance for this slice.

No artifact is admitted, downloaded or executed by ordinary review yet. The
slice proves bounded provisioning and fail-closed backend selection; broker
launch integration, analyzer/project execution, complete artifact admission and
customer-installation acceptance remain required before native support or
production eligibility can be claimed.

## Fixed manager preparation adapters and sealed handoff — 2026-10-03

The contract was extended first with fixed offline command identities, build-hook
policy and deterministic preparation-to-execution handoff. RED collected 27
cases: seven failed because fixed adapter, reconstruction, inventory, handoff and
toolchain-policy functions did not exist; 19 prior cases passed and one native
candidate case skipped. A separate integrated-handoff RED failed because
`run_fixed_entry` did not exist.

GREEN implements exact pip, Hatch, uv and Poetry command shapes, sealed artifact
and lock admission, broker-only manager execution, deterministic path/size/mode/
SHA-256 inventory, descriptor binding to both domains, verified copy handoff and
actionable external SDK/toolchain refusal. Tampering and cross-domain descriptor
reuse fail before project execution.

The final focused project-corpus and managed-subprocess run passed 47 tests in
7.65 seconds with one unrelated Semgrep maintainer-input case skipped. Both
physical project tests ran on native ARM64 macOS: prepared pytest/plugin/coverage/
extension execution passed, and the genuine repository-owned Hatch reconstruction
passed broker admission in 2.72 seconds. Ruff format/lint, BasedPyright with zero
findings, whitespace and strict OpenSpec validation passed.

The current CPython 3.13 candidate completes zero of four real upstream manager
rows. Requests/pip lacks the pinned source, `requirements.lock` and sealed pip;
Hatch lacks its pinned source, `pyproject.toml`, `hatch.toml`, `hatch.lock` and
sealed Hatch adapter; Flask/uv lacks its pinned source, `pyproject.toml`, `uv.lock`
and sealed uv adapter; Poetry lacks its pinned source, `pyproject.toml`,
`poetry.lock` and sealed Poetry adapter. The available Hatch reconstruction is
also incomplete because `hatch.lock`, the sealed Hatch adapter, `pyodbc` and
`pytest-asyncio` are absent. No host fallback was used and production remains
false.

## Trusted acquisition and offline manager preparation — 2026-10-03

The project-corpus contract was revised first to remove the invalid requirement
that each upstream repository carry SpecFact-generated lock files. The revised
contract separates authenticated network acquisition, network-denied managed
preparation and sealed project execution. Initial RED collected 43 cases: 12
failed because `project_acquisition.py`, acquisition-bound plans and binding
validation did not exist; 29 prior cases passed and two physical-candidate cases
skipped.

GREEN adds an authenticated source/archive/wheelhouse/generated-lock bundle,
atomic verified cache installation and offline reuse, and fixed acquisition-bound
pip 26.2.1, Hatch 1.18.0, uv 0.12.13 and Poetry 2.4.3 adapters. Unit acceptance
passes one offline preparation row for each manager with a fixed executable,
argv, environment, descriptor, manager lock and wheelhouse. Project-selected
argv/environment/host executables, URL/path/filename/hash/tag substitutions,
partial caches, extra files and changed bytes or modes fail closed. External SDK
or compiler requirements produce actionable incomplete evidence and remove
partial preparation output.

After review, source extraction was changed from a potentially 512 MiB read to
preflighted bounded streaming into exclusively created no-follow files while
hashing. Authenticated source evidence now binds the requested GitHub repository
and archive route, exact commit, verified Git tree, archive SHA-256 and extracted
tree SHA-256. A caller-supplied observed commit string is insufficient. Unit
fixtures use an explicitly test-only HMAC signer and trusted-fetch verifier;
neither is production signing evidence.

Final focused GREEN: 50 passed and two expected physical-candidate tests skipped
in 0.43 seconds. The broader native macOS unit regression passed 863 tests and
69 subtests, with 56 explicitly gated native/candidate cases skipped. Ruff
format/lint and BasedPyright completed with zero findings; strict OpenSpec and
scoped whitespace validation passed. No network fetch was
needed: source and package artifacts were reconstructed locally while all four
pinned corpus identities and manager versions remained authoritative.

The implementation matrix for generated offline inputs is pip 1/1, Hatch 1/1,
uv 1/1 and Poetry 1/1 in local unit acceptance. The actual upstream/broker matrix
remains pip 0/1, Hatch 0/1, uv 0/1 and Poetry 0/1 because no complete signed
manager adapter images, authenticated upstream archives and resolved dependency
wheelhouses have yet been admitted into the native capsule. Production approval
remains false.

## Physical complete-candidate/project fixture matrix — 2026-10-03

The private native candidate builder assembled three complete, ABI-specific
Darwin/ARM64 runtimes from the pinned analyzer inputs. Each has ten analyzers,
34 signed native images, a deterministic archive, an authenticated manifest and
`production_eligible=false`. Clean/defective analyzer cases passed 20/20 and
Semgrep reference cases passed 14/14 for each ABI. The signed manifests and raw
runtime reports remain in `/private/tmp`; only these bounded counts are recorded.

The first project preparation with a fixture-signed acquisition descriptor
returned `project_native_acquisition_authentication_failed`: its signing public
key differed from the candidate's checked-in acquisition trust key. This is the
required fail-closed RED result, not a production defect. A separate private
acceptance variant embedded the fixture public key and rebuilt all three
archives/manifests with the candidate builder. No repository trust key, module
signature or published artifact was changed. The tiny pip/Hatch/uv/Poetry
fixtures were initialized as Git repositories because the public full-scope
command selects files from Git; descriptors were regenerated after this setup.

GREEN: the public `code review runtime prepare` and `code review run --scope
full --include-tests --bug-hunt --enforcement full --json` commands completed
12/12 rows on native ARM64 macOS 27.0.1 build 26A434: CPython 3.11, 3.12 and
3.13 by pip, Hatch, uv and Poetry. Every review exited 0 and reported PASS,
zero findings, zero unknown required evidence, and ten executed analyzer PASS
records. The allowlisted private summary is
`/private/tmp/specfact-project-acceptance17/project-matrix-summary.json` plus
`project-matrix-cp312-summary.json`. The exact production acquisition signing
identity, upstream external-project corpus, other supported OS builds and
customer GHCR installation remain untested. Module signing is reserved for the
CI/CD PR follow-up.

## Wheel layout and minimum-macOS compatibility correction — 2026-10-03

The native preparation scenarios now require an actionable incomplete result for
wheel `.data` installation schemes and reject ARM64/universal2 wheel tags whose
minimum macOS version exceeds the host. Tests were added before the implementation.
Focused RED (`hatch run python -m pytest
tests/unit/specfact_code_review/run/test_native_project_manager.py -k
'data_scheme or newer_macos or compatible_macos or preserves_native_extension'
-o addopts= -q`): **4 failed, 2 passed, 32 deselected**. Both `.data` schemes
incorrectly returned COMPLETE, and both future-minimum tags were admitted on a
mocked macOS 14.7 host. The positive controls passed.

The sealed installer now returns `INCOMPLETE` before publishing a prepared root
for `.data` scheme wheels. A host-version comparison rejects future-minimum
ARM64 and universal2 tags, and fails closed when the host release is unknown.
No module was signed locally; signing remains in the CI/CD PR follow-up.

Focused GREEN: **39 passed** in the preparation unit file. The related
preparation, project-runtime and corpus unit suites passed **101 tests**, with
two existing physical-candidate skips. Targeted BasedPyright returned zero
errors/warnings, Ruff check and format passed, and strict OpenSpec validation
passed. Pytest reported twelve temporary-directory cleanup warnings from
pre-existing test trees; they did not affect test results.

## Broker startup and cancellation lifecycle correction — 2026-10-04

Two independent review findings exposed an unbounded marker-pipe read after
tracing and recursive output/temporary-tree validation before WAIT/CANCEL.
The spec now requires a shared startup deadline with controller-loss handling
and lifecycle dispatch independent of worker-writable tree size.

Focused RED on the unchanged broker: two new broker regressions failed, with
23 existing cases deselected. The marker test found no deadline/EOF observation;
the dispatch test found no launch-only validation. The broker now uses a
monotonic five-second startup deadline, nonblocking marker reads, and controller
EOF checks across tracing, marker and executable admission. Startup failure
uses bounded worker termination/reaping. Recursive path and tree validation
remains on LAUNCH; WAIT/CANCEL admit only the versioned opcode and owned handle,
while terminal output-file checks remain on WAIT.

An ad-hoc signed ARM64 component built from the modified source passed strict
code-signature verification. A separate ad-hoc signed, private test bootstrap
entered tracing and deliberately stalled before its ready marker; no module
signing key was used. The physical macOS 27.0.1 tests exercised ordinary
self-test execution, cancellation, timeout, controller EOF, a 4,096-file
post-launch output tree, a missing-marker deadline and EOF during stalled
startup. Combined focused GREEN was 9 passed. With three repetitions of each
native case, the complete scoped file passed 42 tests in 19.78 seconds.
Independent survivor observation was included in cancellation and EOF cases;
the initial stalled-deadline run did not yet carry its final survivor assertion.
The native build and raw logs are private under
`/private/tmp/specfact-broker-lifecycle-eO8Azs`.

The final signed physical suite passed **100/100 file-storm cancellations**
with harness-created entries and a symlink in the worker-writable output tree
after launch, plus **100/100 missing-marker deadlines** and
**100/100 controller-EOF startup trials** with the stricter independent
survivor checks. The first 300-case run passed in 571.29 seconds; the final
200 startup cases passed in 542.92 seconds. The missing-marker fixture's
response was verified as marker-stage error 106, rather than an earlier trace
timeout. Separate native controls passed launch-time unsafe-tree rejection and
WAIT after a post-launch symlink. With the final assertions, the full scoped
test file passed **30/30** on this physical ARM64 Mac. These repetitions cover
the two broker fixes; the other release lifecycle, supported-OS, artifact and
customer-installation gates remain separate and unclaimed. A fixture that
itself creates the file storm remains a separate end-to-end boundary control;
the broker dispatch result is independent of who populated the granted tree.

Scoped Ruff check/format, strict OpenSpec validation and `git diff --check`
passed. No module version/signature, PR, or published artifact was changed by
this correction. Production admission remains subject to the complete signed
artifact and lifecycle acceptance gates.

## Final-source local capsule replay — 2026-10-04

After integrating the independent review fixes, the final native C components
were rebuilt and ad-hoc signature verified. The complete CPython 3.11, 3.12
and 3.13 capsule candidates were reassembled with 34 native images each.
A private test-trust variant used only the fixture acquisition public key;
it did not alter the module's checked-in trust key or use module signing keys.
The public `runtime prepare` and full Code Review commands passed all 12
pip/Hatch/uv/Poetry by ABI rows on physical ARM64 macOS 27.0.1 (26A434):
each returned exit 0, PASS, ten analyzer PASS records, zero findings and no
unknown required evidence. An additional CPython 3.12 selected-file run
reviewed `app.py` and successfully imported its unchanged sibling
`support.py`, with the same ten-analyzer PASS result. Private allowlisted
summaries are under `/private/tmp/specfact-project-acceptance17/`.

These tiny, fixture-signed projects do not replace the pinned external corpus,
other macOS versions, a clean customer install or a release-authenticated
acquisition route. Production eligibility remains false; module signing is
left for the CI/CD PR follow-up.

## Managed diagnostic replay correction — 2026-10-04

Independent security/defect review found that tool diagnostics kept absolute
`project-001` paths while the analyzer replayed them in `project-002`. Ruff,
Pylint, BasedPyright, Radon and CrossHair adapters could therefore drop a real
finding as though it did not target a selected file. Ten focused RED cases
failed before the correction: five stale-path cases and five outside-snapshot
negative cases. The controller now accepts only paths inside the exact tool
snapshot and rebinds all supported path-bearing tool outputs before replay.
Thirteen focused GREEN cases passed, including a real Ruff F401 diagnostic
accepted after changing the analyzer-stage project root. The full native
defective-project replay still needs to run on the final rebuilt artifact.

## Independent-review broker WAIT controller-loss correction — 2026-10-04

The existing native execution contract requires controller EOF to terminate every
admitted worker within five seconds. On ARM64 macOS 27.0.1, a newly built,
ad-hoc-signed broker and held self-test worker reproduced the missing WAIT
check. The disposable CLI sent a 900-second WAIT and was killed; an independent
`ps` observer still saw the same worker five seconds later. Failing-first:
`SPECFACT_NATIVE_CONTROL=1 hatch run python -m pytest tests/unit/test_macos_native_broker_wait.py -o addopts= -p no:cacheprovider -q`
returned **1 failed in 5.96s** before the broker edit. The test cleaned up the
survivor after recording the failure.

The broker now checks controller closure during bounded WAIT and exits through
the existing all-worker stop/reap loop without replying to the dead socket.
The same signed physical command returned **1 passed in 1.08s** on the final
broker and test source. Scoped BasedPyright returned zero errors,
warnings and notes; Ruff check/format, strict OpenSpec validation and
`git diff --check` passed. The adjacent native execution unit file returned
**21 passed, 9 skipped** without the separate maintainer build input. This
one physical regression does not replace the unchanged full lifecycle gates.
The scoped SpecFact review returned FAIL/UNKNOWN with zero findings because all
ten analyzers reported `unsupported_controller_platform`; the signature gate
also failed on the shared in-progress tree (Code Review checksum mismatch and
other modules lacking public keys). These gates need the parent's final
assembled artifact and review environment; this bounded fix changes neither.

## Native pytest shutdown receipt forgery investigation — 2026-10-04

The physical regression in `test_native_pytest_receipts.py` runs the actual
native tool worker as a subprocess with a failing project test. Its `atexit`
handler rewrites observer, JUnit and coverage files and forces exit 0. Before
the controller guard, `.venv/bin/python -m pytest -o addopts=
-p no:cacheprovider tests/unit/specfact_code_review/run/test_native_pytest_receipts.py
-q --tb=short --disable-warnings` is **RED: 1 failed** because reconciliation
returns `PASS`. The final characterization test asserts this unsafe lower-level
result explicitly; it does not count as native pytest acceptance.

A bounded in-process trial captured files after `pytest.main` returned and
framed them on worker stdout. It passed 100 focused tests, including the
original `atexit` fixture, but a second physical project fixture wrote its own
valid-looking frame and called `os._exit(0)` before the adapter resumed. The
controller accepted the forged frame and reconciled `PASS`. The trial was
removed from `native_tool_worker.py` and `runner.py`; its GREEN result is
invalid as P1 closure. The shared worktree currently has no receipt handoff
implementation. The historical bypass script is
`/private/tmp/specfact-pytest-frame-bypass.py`; it requires the removed trial
handoff helper and is retained only as investigation evidence.

The spec and native execution contract now require an authoritative handoff
that project Python cannot write or impersonate. That boundary cannot be
established by a frame from the same CPython process. A focused controller
test was RED (1 failed) before mitigation: native execution launched the
untrusted pytest worker. The controller now returns
`native_pytest_receipt_boundary_unverified` before that launch. The physical
forgery characterization and all native runner tests passed **28/28** together;
the latter proves the guarded route does not expose the forgeable receipts as
PASS. This is a fail-closed mitigation, not a ten-analyzer release. Production
native acceptance remains blocked on a process-separated design and physical
GREEN proof for complete pytest evidence. Arbitrary pytest plugins can still
alter pytest's own semantics even after receipt transport is separated.

### Native pytest analyzer prelaunch guard — 2026-10-04

The first fail-closed mitigation blocked only the managed pytest tool request.
A full physical pip fixture review still reported `targeted-pytest-coverage`
`ran/PASS`, because that path did not reach the guarded request. The same run
reported a real Ruff F401 finding; it therefore exposed a guard placement gap,
not a valid complete pytest proof.

The normative scenario was strengthened before changing code: without a
non-impersonable receipt channel, refusal occurs before the native pytest
**analyzer** launch. Two focused tests were RED (2 failed) when they required no
analyzer launch and no snapshot capture. The controller now returns
`native_pytest_receipt_boundary_unverified` immediately for that member; the
focused native runner file is GREEN (27 passed). A physical full-scope rerun with
the current controller and private test-trust CPython 3.12 capsule reported the
Ruff F401 and `targeted-pytest-coverage` `error/UNKNOWN` with that diagnostic;
`has_unknown_required_evidence=true`. The candidate capsule was assembled just
before the final controller edit, so this is controller-path proof, not an
exact-final-artifact or supported-OS matrix. Raw reports remain private under
`/private/tmp/specfact-project-acceptance17`. Production remains NO-GO.

### Native worker test-process state and hosted receipt ordering — 2026-10-04

The first serial smart-test run on the integration patch failed **50** tests
(4,368 passed, 67 skipped). Most tool-runner failures shared missing
`basedpyright`, `pylint`, `ruff`, `radon` and `semgrep` executables on PATH. A
later source-alignment failure showed a native tool fixture's project root in
`sys.path`. The native tool entrypoint had restored cwd but not environment,
arguments or import paths when invoked in-process by tests. A focused
restoration regression was RED (1 failed) before the fix. Restoring all caller
process globals in the entrypoint's `finally` block made it GREEN, and the
native tool tests followed by previously failing analyzer and source-alignment
tests passed **30/30** in one process. A successful `execve` remains unaffected.

One separate smart-test failure came from placing the new broker-WAIT CI step
after the existing receipt checker. The established workflow test requires the
checker to be last so there are no subsequent artifact upload or acceptance
steps. Moving the broker test ahead of that checker passed the focused workflow
test. The full serial smart-test rerun is the deciding repository gate; the
initial 50-failure run is not accepted as passing evidence.

The second serial smart-test run reduced the failures to **37** (4,381 passed,
67 skipped), all in `test_native_worker.py`. Restoring the real Hatch process
environment exposed a pre-existing test-fixture dependency on the earlier
leak: those tests invoked the broker worker in-process without clearing the
unsafe environment keys that the broker excludes in production. The tests
returned rejection exit 76, correctly. Their autouse fixture now removes only
`native_worker._UNSAFE_ENVIRONMENT` with pytest `monkeypatch`, preserving the
negative tests that explicitly add a forbidden key. The native tool and
analyzer worker files, BasedPyright runner tests and bundle-source alignment
passed **80/80** in one process after this test-only correction. The full
serial smart-test gate is being rerun; neither failed run is accepted as
passing evidence.

### P2 capsule output path safety — 2026-10-04

Acceptance criteria for this bounded review finding: the output directory is
an ordinary directory, never a symlink; each of the four fixed output names is
created exclusively without following links; an existing name aborts the build
without changing any existing file or leaving new output files; and a failed
build removes its own partial outputs. Successful archive and metadata bytes
remain deterministic and consumer-compatible. This specializes the active
native artifact build contract's deterministic candidate output requirement.

RED, before builder edits (from this worktree):

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts= -p no:cacheprovider tests/unit/test_build_macos_native_capsule.py -q -k 'output_directory_symlink or existing_output_name or failed_build_removes' --tb=short
```

Result: **10 failed, 29 deselected**. The builder followed the output-directory
symlink, overwrote each symlink or regular-file collision, and left a partial
archive after manifest-size rejection. Existing victim bytes changed in the
collision cases.

GREEN, after the builder reserved four names with `O_CREAT|O_EXCL|O_NOFOLLOW`
relative to an `O_DIRECTORY|O_NOFOLLOW` directory descriptor, fsynced each
stream and removed its own files on failure:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -o addopts= -p no:cacheprovider tests/unit/test_build_macos_native_capsule.py -q --tb=short --disable-warnings
```

Result: **39 passed, 12 warnings**. Ruff check and format check passed for the
two touched Python files; scoped BasedPyright returned **0 errors, 0 warnings,
0 notes**. `openspec validate code-review-native-platform-execution --strict`
and `git diff --check` passed. The 12 pytest warnings came from cleanup of
other old temporary fixture directories, outside this focused test file.

### P2 repeated explicit wheel directories across disjoint artifacts — 2026-10-04

The normative wheel scenario was added first. A two-wheel fixture then asserted
that identical explicit `shared/` entries with disjoint files prepare as
`COMPLETE`, while duplicate file and file/directory collisions remain rejected
before output publication.

RED: `hatch run pytest tests/unit/specfact_code_review/run/test_native_project_manager.py -k 'repeated_explicit_directory_across_disjoint_wheels or repeated_directory_still_rejects_file_and_type_collisions' -q` returned **1 failed, 2 passed**. The positive case raised `wheel output collision: shared` in `_preflight_wheels` before extraction.

The preflight now permits an already recorded directory only when its inferred
kind is still `directory`. It continues to reject every repeated file path,
file/directory type mismatch, case-insensitive alias, and link/special member.

GREEN: `hatch run pytest tests/unit/specfact_code_review/run/test_native_project_manager.py -q --disable-warnings` returned **42 passed** (12 pytest temporary-cleanup warnings). `openspec validate code-review-native-platform-execution --strict`, targeted Ruff lint and format checks, `hatch run type-check`, and `git diff --check` passed. The source, tests, and normative scenario are the only implementation edits for this finding; no module manifest or release artifact was changed.

### Independent review: spawn flags and file ceiling — 2026-10-04

The independent review-agent identified an unchecked
`posix_spawnattr_setflags` return (P1) and a file-size limit incorrectly
reduced by the separate output-stream budget (P2). The native contract now
requires successful suspended/close-on-exec flag setup before spawning and
independent file and stream budgets. The broker fails closed if setting spawn
flags fails. The ad-hoc-signed physical broker controller-loss regression
passed after this change; a forced `posix_spawnattr_setflags` failure has not
yet been exercised and remains a specific negative-proof gap.

A disposable ARM64 harness compiled the actual staged pre-fix `bootstrap.c`
`apply_limits` function: with file=32 MiB and output=8 MiB, its RLIMIT_FSIZE
readback failed at 8 MiB (exit 22). Compiling the same harness against the
corrected source and ad-hoc signing it returned exit 0, read back a 32 MiB
file limit and wrote an independently verified 12 MiB file. The reproducible
physical test is `test_macos_native_file_budget.py`; it is included in the
ARM64 hosted boundary matrix and skipped in the generic suite unless the
explicit native-control flag is set. This is a measured file-ceiling proof on
macOS 27.0.1, not complete resource or customer acceptance.

### P2 acquisition bundle aggregate byte limit — 2026-10-04

The active native project runtime preparation scenario requires bounded,
authenticated input before project code executes. For acquisition bundles,
the producer and consumer now use the same inclusive 1 GiB cap on the sum of
all regular files: extracted source, retained source archive, wheelhouse,
lock, descriptor and completion marker. The producer rejects excess bytes
before publication and on offline verification; the consumer checks the same
sum before authenticating the bundle. The test substitutes a small limit to
exercise the boundary without allocating a GiB, and confirms exact-limit
acceptance and one-byte-over rejection.

RED: before production edits, `.venv/bin/python -m pytest -o addopts= -p
no:cacheprovider tests/unit/test_macos_project_acquisition.py::test_bundle_rejects_combined_files_above_consumer_limit
-q` exited 1: one failed, `DID NOT RAISE ValueError`. The producer accepted a
bundle whose individually bounded parts exceeded the consumer's aggregate cap.

GREEN: `.venv/bin/python -m pytest -o addopts= -p no:cacheprovider
tests/unit/test_macos_project_acquisition.py
tests/unit/specfact_code_review/run/test_native_project_runtime.py -q
--disable-warnings` exited 0: 32 passed (12 suppressed pytest warnings).
Ruff check and format checks passed for the two source and two test files;
BasedPyright 1.39.10 reported zero errors and warnings. `openspec validate
code-review-native-platform-execution --strict` passed before the test edit.

The scoped SpecFact review reported zero findings but exited 1 with
`assurance_status=UNKNOWN`: every required analyzer returned
`unsupported_controller_platform` for `linux-x86_64-cp314`. That result is
not a passing review gate. No signing, version, manifest or publication step
was performed for this bounded reviewer fix.

### P1 broker spawn-flag failure proof — 2026-10-04

The broker now checks `posix_spawnattr_setflags` before attempting a worker
spawn. A physical ARM64 fault-injection test compiles ad-hoc signed,
disposable brokers from the current source. Its reconstructed RED control
removes exactly that return check and records `FS`: flag setup failed (`F`),
then the broker attempted a spawn (`S`). The spawn is intercepted and denied
in both variants, so the test cannot accidentally admit a worker. The GREEN
broker records only `F`, exits without a reply or surviving process group,
and never attempts a spawn. The test verifies code signatures and fails if
the guarded call site changes. It runs in the hosted ARM64 boundary workflow,
and generic pytest skips it unless native control is explicitly enabled.

This proves the failed-flag call path, not complete startup or customer
acceptance. The physical WAIT test returned broker detail 105 under the tool
sandbox; a disposable diagnostic build traced this to bootstrap
`PT_TRACE_ME` returning `EPERM`. Rerunning the three native proofs serially
with the tool sandbox disabled passed: `3 passed in 2.83s`. No repository
code or system protection was changed to accommodate the tool sandbox.

### Combined repository gates — 2026-10-04

After the independent-review fixes and physical regressions were staged,
`hatch run smart-test -q --tb=short` and `hatch run test -q --tb=short`
each passed `4433 passed, 69 skipped` outside the tool sandbox (286.64s and
288.38s). The first sandboxed smart run reported 22 failures; focused reruns
of the affected Semgrep, inventory and runner cases passed in isolation, and
the complete native-host rerun passed. The sandboxed failures are not being
counted as production defects or as acceptance evidence.

`hatch run format`, `type-check`, `lint`, `yaml-lint`,
`check-bundle-imports`, `contract-test` (28 passed), strict OpenSpec
validation, public-key manifest verification (7 manifests), and staged diff
checks passed. The manual SpecFact Code Review and the normal pre-commit
Block 2 review gate each returned `UNKNOWN`/exit 1 with zero findings because
the local Python 3.14 controller was unsupported for all ten analyzers. The
manual run said `unsupported_controller_platform`; the staged hook gave the
more specific `native_capsule_python_abi_unsupported:darwin-arm64-cp314`
diagnostic. The report's legacy `linux-x86_64-cp314` label did not mean Linux
ran on this host. The pre-commit signature, format, YAML, bundle and lint
stages passed; no hook was bypassed. This blocks committing this patch under
the current local gate. A review-capable admitted runtime and the separate
unforgeable pytest outcome channel remain required.

### Native controller Python 3.14 selection — 2026-10-04

The approved native analyzer closures cover CPython 3.11–3.13, but the CLI
may itself run under Python 3.14. The prior selector tied the analyzer ABI to
the CLI process and rejected the Mac before checking any native artifact.
The new scenario selects the pinned CPython 3.12 analyzer closure for a
Python 3.14 controller; it does not claim that CPython 3.14 project syntax or
extensions work in that closure. Incompatible project code remains incomplete.

RED: focused backend selection test expected `darwin-arm64-cp312` for a
Darwin ARM64 Python 3.14 controller and failed because selection returned
`unsupported`. GREEN: backend and native runner tests passed `56 passed` after
the selector change. This removes one false platform rejection; an admitted
artifact and a protected pytest result are still needed for an actual PASS.

### Native incomplete identity and registry loader — 2026-10-04

The first current-source physical local review on the ARM64 Mac selected the
CPython 3.12 native candidate. Five independent analyzers ran, while project
preparation returned `project_native_acquisition_entry_missing`; the
project-acquisition catalog contains no entries. The review exited 1 and did
not claim complete native evidence. Its four blocking clean-code findings were
all in the registry loader. The loader was split into smaller validation and
streaming functions without changing its authentication decisions. Focused
backend tests passed (29), Ruff and focused type checking of that file passed,
and the largest remaining function complexity is 17.

The incomplete-report scenario was added before its test. RED: the test saw
`linux-x86_64` as the platform for a selected Darwin backend. GREEN: the
incomplete report now retains `darwin-arm64-cp312`, passes Darwin platform
context to admission, marks every analyzer unrun, and uses `unavailable`
versions rather than historical Linux pins. The focused native runner/backend
set passed (57). This fixes report identity only; it does not supply the
missing project acquisition or authoritative pytest result.

### Dependency-free native project layer — 2026-10-04

The specification now permits a source-bound empty site-packages layer only
for static pip projects with no selected dependencies, requirements,
constraints, extras or dynamic dependency metadata. RED: a focused test failed
at the empty remote acquisition catalog. GREEN: 25 native project-runtime tests
passed, including negative declared/dynamic dependency cases. A physical ARM64
Mac run of a small dependency-free project returned PASS with a verified
`darwin-arm64-cp312` local layer; eight analyzers ran, while conditional
Semgrep bugs and explicitly disabled pytest were not applicable. This smoke
does not establish ten-analyzer or four-manager acceptance. Dependent projects
still return `project_native_acquisition_entry_missing`, and native pytest
still fails closed pending its result-authority decision.

### Native pytest opt-out bypass — 2026-10-04

The owner chose protected pytest evidence as a requirement for every Darwin
ARM64 review, including reviews that request `no_tests`. The old native
dispatch treated that flag as `NOT_APPLICABLE`; a report assembled from
otherwise passing members could therefore report PASS without running pytest.
The same outcome was possible for a stub-only or empty selection.

RED: three focused tests failed: two report paths returned PASS instead of
UNKNOWN, and native `no_tests` dispatch returned `NOT_APPLICABLE` instead of
the existing receipt-boundary diagnostic. GREEN: all three passed after
native dispatch stopped honoring the legacy opt-out and report assembly
converted native skipped pytest evidence to UNKNOWN. Linux opt-out behavior
is unchanged. The native runner and physical receipt-forgery characterization
files passed together: **35 passed**, including the Linux compatibility
control and preservation of a more specific native pytest error. Focused Ruff checks and formatting,
strict OpenSpec validation, and diff whitespace checks passed. This closes a
bypass only; the forged atexit receipt proof still prevents admission of
native pytest itself.

A review-agent pass found that the first opt-out fix still called the native
member dispatcher, which would silently run tests after a future removal of
the prelaunch guard. A tightened test failed before code change (member
execution was reached). The native `no_tests` path now returns UNKNOWN before
member execution; the complete focused set remained 35 passed. This keeps an
explicit test opt-out from unexpectedly running project code while preventing
it from yielding PASS.

The focused type-check initially reported four errors in the integration
patch: a nullable Linux Bubblewrap identity in `runner.py` and three optional
report-evidence iterations at the start of `test_runner_native.py`. A new
scenario and failing test proved the missing Linux identity reached sandbox
preparation. The Linux dispatcher now returns UNKNOWN before setup, and the
tests explicitly establish report evidence before iterating. Focused type
checking now passes with zero errors or warnings. The full module review gate
remains UNKNOWN from the independently missing project-acquisition catalog and
protected pytest result, so these checks do not authorize publication.
The repository-wide `hatch run type-check` gate also passed with zero errors,
warnings or notes after these corrections.

The Code Review 0.51.0 manifest checksum was refreshed from the current
filesystem payload without a private key. Verification with the public
module key and version-bump check passed for all seven manifests. The Code
Review manifest remains unsigned locally; signing belongs to the protected
CI/CD follow-up and is not represented as complete here.

### Separate receiver is not a protected pytest outcome — 2026-10-04

A physical ARM64 macOS process probe placed the receipt solely in a separate
parent process and passed a private Unix socket descriptor to a pytest worker.
The project test reached a failing assertion; pytest printed its `F` result.
Its exit handler enumerated inherited descriptors, sent `PASS` on the socket
and called `os._exit(0)`. The parent observed worker exit 0 and received
`PASS` despite the failed assertion. This proves that process-separated
storage alone is insufficient when untrusted test code can impersonate the
worker-to-parent channel. The probe used the local Python environment, not
the capsule broker, so it is a feasibility rejection rather than release
acceptance. At the time of this probe, the native pytest prelaunch guard
remained in force.

### Project-origin native pytest contract — 2026-10-04

The owner accepted project-origin pytest evidence for local macOS reviews
after the physical separate-receiver probe. The forged-result fixture remains
as a characterization of this trust limit; it is not a passing security test.
The specification now requires explicit `project-origin-v1` provenance and
UNKNOWN protected range evidence pending a separate consumer compatibility
change. It retains managed worker isolation and the native `--no-tests`
incomplete outcome.

RED: three focused runner tests failed before production edits: the native
prelaunch guard prevented snapshot and managed-tool entry, and the report
lacked project-origin provenance. A protected-range assertion was also added
before code change. GREEN: the runner and forged-result characterization set
passed **35/35** after the guard was removed and report provenance/range
rejection added. A follow-up failing test preserved the original project
preparation diagnostic when a protected range was already UNKNOWN; the final
focused native runner/worker set passed **101/101**. Strict OpenSpec
validation, focused Ruff, repository type checking and all 28 contract tests
passed. The manifest checksum was refreshed without a private key;
public-key verification passed for all seven module manifests. No module was
signed locally.

An unrelated checkout (`specfact-cli`) was discovered from the current source
as a uv project with identity
`sha256:9a6d2b8c0b0e37e560e218afca9a17286ea56aafa37f5d6fd287ca66ca314e0d`.
It is not dependency-free, and the packaged project catalog returned
`project_native_acquisition_entry_missing`. This confirms that the current
candidate does not yet prepare arbitrary dependent repositories. A broader
runner test attempt was stopped after 18 failures and 99 passes; its first
failures reported `suppression_catalog_semgrep_policy_mismatch` in legacy
synthetic Linux fixtures on this Darwin host. That suite is not counted as
green. No current native artifact or real-project end-to-end PASS was obtained.

The broader runner failures revealed an independent diagnostic-masking bug:
when every analyzer was already UNKNOWN, failed suppression activation for
unavailable native versions replaced the root cause with a Semgrep policy
mismatch. A specification scenario and focused test were added first; the
test failed with the masking diagnostic. The report now preserves complete
already-UNKNOWN evidence without promoting its status or adding a suppression
identity. The focused native set passed **102/102**, and the formerly failing
cached/worktree subset passed **39/39**. This is not a complete repository
suite result.

## Project-driven cold preparation — 2026-10-04 (Europe/Berlin)

Specification: PROJECT_DRIVEN_PREPARATION_CONTRACT.md, current proposal/design,
VM acceptance scenarios and change-order correction. #460 was updated and read
back with project-driven preparation, shared caller configuration and VM policy;
#488 remains the optional follow-up blocked by #460.

Red: structured CLI ambiguity tests failed JSON decoding and lacked candidate
extras. The unfamiliar-project regression demonstrated the publisher catalog
prerequisite. Real pip wheel-layout coverage demonstrated the custom extraction
gap. Independent review identified omitted root installation, exponential group
expansion, incorrect nested constraint mode, unbound snapshots and compact
include syntax. Follow-up red tests reproduced cached build-package leakage,
missing default backend, malformed hook responses, work before manager rejection
and missing source-root projection. Further red tests reproduced 20 inventory
scans for 20 wheel members and an AttributeError on malformed failure JSON.

Code: pinned pip 26.2.1 binary-wheel resolution in acquisition plan 23, offline
pip installation in plan 24, confined disposable PEP 517 hooks in plan 25 and
fresh sealed wheel metadata inspection in plan 26. Acquisition receives bounded
declarations and the local root wheel; hooks receive neither network nor
credentials. Backend imports exclude preloaded analyzer distributions. Local
identities bind source/configuration, manager, native ABI and capsule identity;
atomic artifacts retain local_build provenance. Imports use validated
source-root byte bindings, with a single inventory index and cumulative matching
budget. Malformed worker receipts preserve incomplete evidence. Unsupported
managers are rejected before hooks/acquisition; no manager substitution.

Green: discovery/CLI suite 249 passed; final focused preparation/hook/tool suite
69 passed; execution-plan suite included 9 explicitly skipped maintainer-only
physical fixtures. The broader five-file focused checkpoint was 91 passed,
9 skipped. Backend/assembly compatibility checkpoint 50 passed. Strict OpenSpec
validation passed before the final bounded matching refinement; rerun required
for finalization. Formatting, type checking, lint, YAML and import-boundary gates
passed at their recorded checkpoints; final repository gates remain required.

Physical proof: macOS 27.0.1 (26A434), ARM64, native CPython 3.11.15. An unfamiliar
requirements-only project prepared idna/urllib3 without a catalog and reused its
verified cache offline. PyPA sampleproject at commit
621e4974ca25ce531773def586ba3ed8e736b3fc prepared its actual setuptools root and
dependencies through the broker, then reused the cache offline. All ten analyzers
executed (`ran`); genuine lint/type/coverage findings produced FAIL, with no
missing analyzer diagnostic. Checkout remained clean. The native signatures
were build-time ad-hoc; candidate admission was private maintainer validation,
not publisher-authenticated customer installation. Production eligibility false.

The exact review-agent skill was used by one medium-effort, read-only independent
agent, reused for two follow-ups. All original five and the following six
findings were corrected. The last two controller regressions passed their
red/green cycle. No local CodeRabbit upload, signing key, automatic merge or
publication was used. Hatch/uv/Poetry, live managed launch, complete boundary,
independent installation, Linux VM and supported macOS/ABI release acceptance
remain outstanding; this checkpoint does not claim shipment readiness.

## Core compatibility fixes — 2026-10-05, Europe/Berlin

Contracts preceded each behavioral regression. RED/GREEN in this checkpoint:

- Managed sibling imports and reordered -I: five failing regressions before
  implementation; the combined managed-child/hook suite passed 66 cases.
- Ignored foreign PYTHONPATH in isolated launches: three failures before
  implementation, then 43 managed/child cases passed. The real native
  build-hook test, including these startup forms and lifecycle operations,
  passed in 14.07 seconds.
- Poetry explicit group selection retained main: one failure, then 77
  adapter/controller/shared-manager tests passed.
- Installed uv source-root byte matching: one failure, then 107 neighboring
  cases passed; the automatic-discovery native extension project ran all
  ten analyzers with PASS without configured pytest source paths.
- Canonical snapshot roots for internal directory links: one failure, then
  60 builder/snapshot cases passed; unchanged Requests reached analyzers.
- Whole-file BasedPyright diagnostics and local policy projection: two RED
  regressions. Whole-file parsing is implemented; local doctest/coverage
  policy compatibility remains pending explicit user approval after
  automatic approval review rejected that production revision twice.
  Existing protected policy and native protected-range rejection passed.
- Native version selection and acquisition failure normalization: five
  failing cases before implementation; 72 interpreter/native-runner/shared
  builder cases passed. A subsequent 63-case interpreter/native-runner/
  BasedPyright suite also passed. Native patch values use the separately
  recorded 3.11.16, 3.12.14 and 3.13.14 candidates, not Linux versions.
- Contract input separation on pytest projection failure: two RED cases;
  37 snapshot cases passed after implementation (the pending policy case
  was excluded from this explicitly scoped checkpoint, not treated as green).

The independent review-agent verified closure of the earlier import/isolation
findings and reported the two version/reporting defects addressed above. Its
review covered acquisition/cache/execution, runner/report and the complete
managed-uv builder; concurrently added native uv child support is outside that
pass. Final integrated independent review remains required.

All raw native output, project receipt details and execution paths remain
private. No local module key signing, merge or publication occurred.

## Frozen post-refactor acceptance — 2026-10-05 (Europe/Berlin)

Final private candidate `sha256:736b9ce2f6d5dac1eb556c1cab3ae52b5c7cb98a672ac1cd258587f84af108b5`
repeats the unchanged pip/Requests, uv/Flask, Poetry and Hatch slices: every
manager prepares cold, verifies offline reuse and executes all ten analyzers
with pytest PASS. Genuine project findings retain FAIL. Automatic uv discovery
with the compatible ARM64 extension repeats overall PASS. All caller checkouts
remain clean. The source inventory was unchanged across the final runs.

Post-refactor format/type/lint, YAML, bundle imports, seven manifest checksum/
version/public-key verifications, both strict OpenSpec validations and 28
contract tests pass. The complete frozen smart-test suite passes **4,904 tests**,
73 explicit skips, five warnings. The full-test wrapper passed the same full
suite before this refactor; both wrappers invoke the same complete pytest tree.
The final affected Linux emulation regression repeats **279 passed** with
network disabled, a read-only checkout and unchanged container security.
Independent review-agent closure reports **No findings** for the three frozen
refactored modules, including both ordering-preservation adjustments.

PROJECT_DRIVEN_NATIVE_CHECKPOINT.json contains only allowlisted summary fields.
Raw logs and project receipts remain private. These results do not establish
authenticated artifact acquisition, independent installation, the complete
boundary or the macOS 14/15/26 × CPython 3.11–3.13 release matrix. Module 0.51.0
is an unsigned development candidate; publisher signatures remain CI/CD-only.
Normal native CLI/self-review still requires an authenticated capsule catalog
entry or CI-signed explicit local artifact. The empty catalog is not filled with
a synthetic identity, and no host fallback, relaxed test or hook bypass is used.

## Bounded OCI allocation and unchanged offline gate — 2026-10-05 (Europe/Berlin)

The normal commit hook first rejected the Windows follow-up because its planning
requirements had no evidence sidecar. The added schema-v2 mapping covers all three
requirements and four scenarios at planned maturity; it does not claim a Windows
implementation. The exact staged gate passes both selected change sources.

A subsequent ordinary-user Linux guest exposed a real shared extraction defect:
`GzipFile.read(max_bytes + 1)` requested 4,294,967,297 bytes for the signed 4 GiB
ceiling even when the actual layer was smaller. Specification and nine integrity
regressions preceded the fix. RED: one failed, eight passed. GREEN: all nine new
and 112 existing toolchain cases pass. Reads are now at most 1 MiB and still probe
one byte beyond the exact limit. Compressed/uncompressed digests, duplicate-path,
whiteout and file-count checks remain before filesystem application. The complete
decompressed layer remains in memory; this is not a constant-memory claim.
Independent review-agent review reports No findings and confirms gzip EOF, CRC,
truncation and concatenated-member handling.

Fresh final private candidate
`sha256:b7b89843a5bd03136c1708271225bf25ee973b8893fbc0d8ad5463e2800590ad`
repeats all ten analyzers, cold preparation, offline reuse and pytest PASS for
pip/Requests, uv/Flask, Poetry and Hatch. Their genuine findings retain FAIL;
the clean automatic-uv/native-extension fixture retains PASS. The complete frozen
repository suite passes 4,913 tests, 73 explicit skips and five warnings.
Focused types/lint, module checksum/public-key verification, YAML and strict
native OpenSpec validation pass after this fix.

The commit-gate retry uses the same 4 GiB full x86-64 Linux guest and unchanged
hooks, sandbox, timeouts and worker limits. Both the outer container and guest
are offline, with authenticated public inputs preloaded read-only. This guest
uses CPU emulation and supplements acceptance; it cannot establish matching-CPU
release lifecycle/resource acceptance. No local publisher signing, host fallback,
security override, merge or publication is used. Actual normal-hook completion
remains pending at this checkpoint.

## Independent native coverage correction — 2026-10-05 (Europe/Berlin)

The reused medium-effort review-agent completed the remaining admission/cache,
backend/execution, four-manager preparation, managed-uv and protected-pytest
integration review. It found one P2: the native complete coverage adapter mixed
physical file paths with logical snapshot test roots and selectors, retaining
selected tests/helpers as production coverage inputs.

The specification and eight focused regressions preceded production changes.
RED: seven failed, one passed. GREEN: 70 native worker/customer-pytest/coordinate
cases pass. The shared complete gate accepts an explicit snapshot root, preserving
its Linux default. The scoped native adapter first validates sealed logical roots,
then uses the existing traversal-rejecting path binder below the admitted physical
snapshot. Root-wide and tests-directory policies exclude only intended tests and
helpers; missing production coverage remains UNKNOWN and coverage below the sealed
95% fixture threshold remains a blocking error. Escaping roots fail before pytest
or coverage execution. No provenance, observer reconciliation or permission changes.
The independent reviewer confirmed closure and reported No findings for the fix;
nine read-only probes also preserved Linux/default filtering and escape rejection.

Final corrected candidate
`sha256:36787480dc13c581ac950affd678cf3513767df706b8c955e3bf255033de606a`
repeats all five native project slices with all ten analyzers, pytest PASS, cold
preparation and verified offline reuse; genuine upstream findings retain FAIL and
the clean automatic-uv/native-extension project retains PASS. The complete frozen
suite passes **4,921 tests**, 73 explicit skips and five warnings. Required format,
types and lint pass, with zero type errors/warnings. Only the development manifest
checksum was refreshed; no publisher key was used.

The actual unchanged normal commit hooks in the offline full x86-64 Linux guest
passed signatures/checksums, format, YAML, imports, lint, command/documentation
checks and staged requirements. The allocation crash did not recur. The review
subprocess reached its unchanged 300-second deadline while assembling the fresh
verified capsule; no complete review report or commit was produced. Assembly is
per-invocation, so warming downloaded blobs cannot remove this cost. A generated-
bytes hash/decompression probe provided no evidence that CPU-model tuning would
solve it. No partial cache is accepted, no timeout/worker limit is increased, and
no hook is skipped. A matching x86-64 Linux runner is needed to retry this gate
without treating CPU emulation as release acceptance. PR #489 remains at its
previous remote head; these implementation changes are still staged locally.

Complete-boundary, release-matrix and customer-installation flags remain false.
All raw diagnostics, partial guest caches and receipts remain private. No merge,
publish, local publisher signing or issue closure occurred.

Final supplementary Linux CPython 3.12.3 regression on the existing read-only,
network-disabled amd64 userspace image passes **191 affected tests**, including
the new coverage and allocation negatives. This runs above an ARM64 Docker
kernel and remains supplementary, not native Linux sandbox/release acceptance.
Final contract suite passes 28 cases. Both strict OpenSpec validations, all seven
manifest/public-key checks and the two-source staged planned-evidence gate pass.
The four upstream caller checkouts remain clean. All corrected implementation
files are staged; the remote head remains `81ea5eba07eab82b86cf718530a8bc27c1b1f5c6`.

## Approved hosted capsule gate — 2026-10-05 (Europe/Berlin)

The maintainer explicitly approved deferring **only** the unavailable local
capsule review to mandatory GitHub Linux CI. The customer workflow now binds
a detached review worktree to the event's exact candidate head and base, stages
the candidate delta and invokes the unchanged pre-commit helper under the
ordinary CPython 3.12 customer installation. Its 300-second timeout, changed-line
enforcement and sandbox/integrity behavior remain unchanged. A nonzero exit
fails the customer prerequisite; this is candidate evidence, not public release
or protected macOS acceptance. GitHub credentials and PYTHONPATH are removed
before review. The existing restricted AppArmor prerequisite is unchanged.

Specification and evidence mapping preceded two RED failures for the missing
hosted blocking check. GREEN: **73** recipe, customer gate and pre-commit parity
tests pass, including real Git-index reconstruction, exact file contents and
nonzero exit propagation. The primary checkout remains clean and unchanged.
The earlier frozen complete implementation suite (4,921 passed, 73 skipped)
remains its recorded evidence; these two new workflow regressions are additional.

Automatic approval review rejected a proposed `SKIP=modules-block2` commit
because it would skip the combined hook. That action did not execute. The safer
implementation leaves every hook enabled and exposes an explicit capsule-only
`SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux` option inside the original review
function. It requires a local ARM64 Darwin feature worktree with the blocking
hosted recipe present; CI, other platforms and invalid values fail closed.
It reports DEFERRED, never PASS. All other original hook functions execute
normally. Hosted current-head completion remains required before merge.

The narrow hook contract precedes four RED failures. Its tests execute the
original complete Block 2 recipe against a real fixture worktree, proving all
non-capsule components remain active and CI/platform/invalid flag restrictions
are enforced. No SKIP variable, hook configuration override or production
sandbox/resource change is used for the maintainer commit.

GREEN for the narrow hook integration: **77** combined recipe/customer/parity
cases pass. The accepted local deferral retains command overview/contract,
core documentation, docs, prompt, staged requirements and contract execution
inside the original Block 2 pipeline. CI, Linux and invalid values reject it.
The normal commit will use this capsule-only option with every hook enabled.

## Hosted gate review corrections — 2026-10-05 (Europe/Berlin)

The reused independent review-agent confirmed two concrete findings: the hosted
helper could populate the mandatory cold-customer cache, and unrelated bundle
changes could qualify for local deferral without scheduling capsule CI. Three
RED failures preceded the fixes. GREEN: 78 hosted-recipe/customer/parity cases
pass. The helper now receives its own commit-review cache under a separate exact
launcher AppArmor rule; the original cold cache remains empty. Local deferral
requires a final staged delta versus fetched origin/dev in Code Review or the
customer workflow, which are actual capsule trigger paths. Missing baseline or
non-triggering deltas fail. Every normal commit-hook component remains active.

PR implementation head `049828fd5556f91041781d9cbe38eee83154878a` was pushed.
CI alone signed its module in `9c7920cc324c7578964b1e88656265f80a6e2a2b`;
all seven public-key signature/checksum verifications pass after preserving the
ignored local native build outside the signed source payload. Required bot-head
workflows were approved through GitHub. The first hosted deferred helper returned
UNKNOWN and correctly failed, despite zero findings; no finding filter, timeout
or assurance override was applied. Its rerun prints only bounded diagnostic
reason codes; raw reports/logs/receipts remain private. Current-head CI and actual
review completion remain required and are not claimed here.

Independent closure caught the divergent-dev variant of the trigger check.
Three additional RED failures proved that direct base-tip comparisons include
changes made only on dev. Both hosted staging and local eligibility now use the
merge-base with their bound base. The real-Git fixtures cover dev changing an
unrelated Python file and dev changing only Code Review while the feature
changes another bundle; neither adds a candidate capsule delta. Enforcement,
timeouts, signature verification and cold cache checks remain unchanged.

GREEN after merge-base correction: **81** combined hosted-recipe/customer/parity cases pass.

## Authenticated reviewer and staged subject separation — 2026-10-05

The actual hosted reason was `candidate_payload_unavailable`: resetting the
reviewer/subject checkout moved the imported source away from GITHUB_SHA. The
existing authenticated candidate guard correctly rejected it. Five RED failures
preceded the fix. GREEN: **82** hosted-recipe/customer/pre-commit cases pass.
The helper takes an explicit absolute subject root for report, working directory
and cached diff, but imports module/control sources only from its original
REPO_ROOT. CI invokes that original helper in the unchanged event-authenticated
checkout while the subject uses the disposable staged worktree. GitHub identity
variables, tracked-payload verification, timeout and authoritative UNKNOWN exits
remain unchanged. The unchanged native controller-loss proof also passes on the
physical ARM64 macOS 27 machine; macOS 14 still fails pre-trace startup and is
not accepted. No fallback, signature bypass or release acceptance is claimed.

## Controller imports and bounded startup diagnostics — 2026-10-05

The reused independent review-agent found two additional subject/control paths.
Three RED regressions preceded the fixes: a real interpreter loaded a subject
CLI package from its current directory; inherited relative PYTHONPATH could
restore that path; and missing-runtime bootstrap selected the subject checkout.
The helper now uses Python safe-path mode, only reviewer bundle import paths and
reviewer-anchored dependency bootstrap. No GitHub identity check is relaxed.

Exact-head Linux execution advanced beyond candidate authentication and correctly
rejected missing project preparation. This repository declares multiple Hatch
environments. Five RED cases preceded explicit caller selection of its declared
Hatch default environment through project-config; discovery remains unchanged.
GREEN: 108 hosted recipe, customer assurance, helper and startup codec cases.

macOS 14 still fails before the initial trace handshake; it is not accepted. A
bounded fixed-bootstrap phase/errno record now identifies that failure without
logging worker output or satisfying readiness, tracing or executable admission.
The codec failed before implementation and passes afterward; the original
controller-loss, file-budget and spawn-flag tests pass on the physical ARM64 Mac.
The original five-second bounds, required 100 repetitions and resource/profile
limits remain unchanged. Hosted diagnostics are required to establish the cause.

Module payload checksums are refreshed without publisher keys. Only CI/CD signs
the follow-up. Complete-boundary, independent installation and production flags
remain false until their mandatory suites pass.

Independent closure confirms both controller findings are fixed and identifies
no additional defect in the native startup diagnostic diff. It caught a caller
format mismatch: project-config consumes TOML, whereas the first hosted fixture
used JSON. Four RED recipe failures preceded TOML emission. The real recipe
now invokes the actual discovery parser against this repository and asserts
Hatch/default selection, retaining nonzero gate propagation. CodeRabbit skipped
the requested review because 202 changed files exceed its 150-file allowance;
this is recorded as missing review coverage, not a completed review.

The macOS 14 exact-head diagnostic identifies phase 70 with errno 0: sandbox
initialization, rather than tracing or resource setup, rejected the launch.
No policy was removed. A new RED codec case precedes bounded compiler-line
diagnostics over the same private channel. Numeric line records are disjoint
from READY and cannot grant ownership or executable admission. Original native
cleanup/resource tests pass on the physical Mac; hosted macOS 14 remains pending.

A real native startup failure injection now lowers only the disposable controller's
hard descriptor limit to 64 while preserving the production worker request of
1024. The kernel rejects bootstrap resource setup, the target PID marker never
appears, bounded phase/errno identify the rejection, and broker/controller exit
within five seconds. Both original controller-loss and injected failure tests
pass locally; the same additional proof runs on every hosted native matrix
runner. Independent read-only closure finds no diagnostic defect.

## Equivalent older-kernel protection and scoped preparation — 2026-10-05

Hosted macOS 14 identifies sealed profile line 23: its compiler rejects the newer
exception-port hook. The fix does not drop that protection: all systems deny
task/thread exception-port set/swap kernel RPCs, retaining the newer hook wherever
it exists. A failing native probe preceded implementation. Valid requests all
succeed outside confinement and all four fail inside the signed direct worker
on the physical Mac. The ordinary controller-loss and hard-limit-failure cases
also pass, including five-second cleanup. The historical control acceptance
fixture uses the same unconditional RPC denial; its required cases/repetitions
are unchanged. Hosted macOS 14 proof remains required and is not claimed here.

Linux exact-head review progressed through authenticated source and explicit
Hatch selection, but cold setup plus analysis exceeded the unchanged 300-second
helper bound. New runtime prepare --scope index captures the same base/index
snapshots and independently binds both confined environments. A real Git RED
case preceded implementation; GREEN validates both identities, staged VCS tree,
cleanup and unchanged checkout/index. Hosted preparation has a separate 1800s
bound with private output/cache; review retains 300s and the mandatory customer
cold cache remains empty. No timeout, finding or missing-evidence override is
used. Default project preparation behavior and protected-review authority remain
unchanged.

Independent review caught the no-target preparation case. A real Git workflow-only
index failed before correction; preparation now returns explicit NOT_APPLICABLE
with no acquisition or runtime descriptors. It neither bypasses the subsequent
helper nor the mandatory customer suites. GREEN: 121 helper, recipe, customer,
public runtime and diagnostic cases; 281 historical control/receipt regressions
pass with seven explicitly opt-in physical cases skipped. Physical signed native
startup/resource/spawn cases run separately.

A refreshed private ARM64 CPython 3.11 capsule runs all ten analyzers successfully
on the clean uv/native-extension project with cold preparation and verified
offline reuse under the new RPC restrictions. The all-four-manager real corpus
is being repeated; its result will be recorded after completion. This is local
candidate evidence, not authenticated customer installation or release acceptance.

Final native corpus repeats all five projects against one unchanged private
artifact: `sha256:09172a6ece415d84e4e0fa8d7658ac6f5bdf45537956f55481be80334fb5e5f4`. Requests/pip, Flask/uv, Poetry and Hatch
each prepare cold, verify offline reuse and execute all ten analyzers with pytest
PASS. Genuine upstream findings retain FAIL; automatic uv/native-extension review
returns overall PASS. All five caller checkouts remain clean. The checkpoint is
updated with only allowlisted summary fields; raw reports stay private.

Five physical signed native regressions pass, including the real failed-startup
injection, valid positive exception-port controls and four kernel-denied RPCs.
Independent closure reports no remaining findings in the runtime preparation,
controller, workflow, policy and probe deltas. Every normal hook passed, including
28 contracts; only the owner-approved local capsule step is explicitly DEFERRED
to mandatory Linux CI. CI signs publisher metadata exclusively.

The current signed macOS 14 job passes the release broker startup, resource, spawn
and exception-port proofs and proceeds to unchanged 100-repetition startup/control
suites. That progress is not complete matrix or production acceptance. Exact-head
Linux provisioning/review and actual review coverage remain required. CodeRabbit
has skipped this PR because its file allowance is exceeded; skipped status is
not accepted as completed review.

### Hosted failure corrections — 5 October 2026

- Final full repository suite before the following two narrow corrections: **4,939 passed, 75 explicit native/maintainer skips, five warnings**, 310.71 seconds. No failing tests were suppressed.
- Signed CI head c5aa6225 passed actual broker WAIT/controller-loss, failed-bootstrap, task/thread exception-denial, spawn-flag and file-budget checks on ARM64 macOS 14/15/26. The existing 100-repetition historical control suite correctly failed at exec-exception-task; no release matrix pass is claimed. Physical reproduction: both task/thread cases RED. Independent endpoints remained unchanged but the target returned 40 because its swap probe accepted KERN_NO_ACCESS while syscall-mig returned **KERN_DENIED (53)**, explicitly defined as security-policy denial by the SDK. Accepting that precise denial retains all endpoint snapshots, positive controls and exit checks. GREEN: four real signed admission cases passed in 5.15 seconds, including identity swap rejection.
- Hosted Linux index preparation correctly rejected the repository's two BasedPyright primaries. Pinned upstream 1.39.10 documents JSON precedence over TOML: https://docs.basedpyright.com/v1.39.10/configuration/config-files/ (accessed 5 October 2026). Corrected the selection semantics without editing the reviewed repository or weakening sealed graph, path, projection or suppression checks. RED: two precedence cases failed, two invalid/unsafe JSON no-fallback cases passed. GREEN: all 178 scope/runtime/hosted recipe cases passed in 18.29 seconds. Invalid or unsafe selected JSON cannot fall back to TOML.
- Current-head hosted Linux execution, full 100-repetition native matrix and external review remain required. CodeRabbit's 202-file versus 150-file skip is **not** completed review; no filtered-out security/test surfaces or repeated requests substitute for review.

### Native full-suite and default discovery review fixes — 5 October 2026

- GitHub findings 4184431584 and 4184431589 exposed a selector-truthiness bug and absent default contract arguments. Expanded real-policy binding regressions: RED **10 failed, two passed**; default no-tests inventory RED one failure. A successful empty full pytest selection now still binds policy, whereas selection errors remain UNKNOWN. Default contract discovery inventories actual matching test files; explicit contract-inputs-v2 empty inventory retains all production CrossHair inputs rather than excluding dot/the entire tree. Configured test-root behavior is retained.
- Actual rebuilt native full review with no declared testpaths then produced RED **nine analyzers ran; pytest UNKNOWN**, reporting no collected selectors. Added only native project-origin full discovery to the complete execution evaluator; its protected default still rejects empty selectors. Full discovery requires nonempty observer outcomes reconciled with JUnit/process status, valid relative test paths, unchanged blocking coverage thresholds and no project-omitted initializer exemption. Unit regressions cover success, no tests, conflicting receipts, low coverage, and unchanged protected rejection.
- Actual GREEN on physical ARM64 macOS 27.0.1 / CPython 3.11.16: **all ten analyzers ran; overall PASS** for the autodetected dependency-bearing uv/native-extension fixture under full scope with pytest default discovery. Cold preparation and verified offline reuse passed. Private ad-hoc artifact identity **sha256:35184afc9af798d603a5745c5c8d6ead75cc195ff16f565a539061f89c4ba989**. The allowlisted checkpoint records this separate full proof; prior five-manager corpus identities remain historical, not falsely rebound.
- Signed head 5aef3f66 completed all required control lifecycle cases at **100 repetitions each** on hosted macOS 14/15/26, but aggregate receipt verification rejected actual exception status53 because its old whitelist only allowed0/8. RED two receipt cases; accept exact53 with unchanged endpoint, swap, clear, traced exit and tampering assertions. This is a parser mismatch, not reduced lifecycle proof; final exact-head matrix rerun remains required.
- GitHub finding4184245702: RED native-critical runtime path failed workflow filter test; broadened the native workflow trigger to the entire run integration package. Cases/repetitions/OS matrix are unchanged.
- Full repository regression after the prior policy fix: **4,943 passed, 75 explicit skips, five warnings**, 299.59 seconds. Current native-discovery changes additionally run the complete affected runner/worker/adapter/receipt test surfaces and normal repository hooks.
- Hosted Linux still rejects the large staged review at its unchanged 300-second limit. GitHub finding4184245681 correctly distinguishes candidate identity from trusted review authority: event-bound candidate execution is not independent published/base review. This finding remains unresolved while a compatible immutable trusted reviewer path is evaluated; no candidate result is promoted to protected authority and no timeout is increased.

- Reused medium review-agent found and verified two additional P2 defects: production doctest nodes were incorrectly removed from coverage and 64 default-discovery test files exceeded the 128-argument worker limit. Both were fixed and independently re-reviewed with **No findings**. Doctest-bearing production sources retain TEST_COVERAGE_LOW; sealed native v2 inventories use two fixed launch arguments, bounded JSON bytes/path counts/path lengths and no host path escapes. Existing v1 behavior and every original launch/resource bound remain unchanged. The initial doctest assertion was tightened to require the production-source finding rather than accepting an unrelated test-file error. Five strict outcome/coverage cases pass; 64-file transport and path-escape regressions pass.
- Full affected runtime/runner/adapter/receipt surfaces: **826 passed**, 82.36 seconds. Strict type checking: zero errors/warnings. Independent trusted-reviewer P1 remains open; it is not resolved by labeling candidate control code authenticated.

- Final corrected private native artifact **sha256:78b83dd0175b1a2c87714aa8c299eb1a2673d7f9342f04a91d81371d2d16ad48** repeated full/default-discovery acceptance with cold preparation, offline reuse, **all ten analyzers ran and overall PASS**. This supersedes the earlier subset fixture identity only for this full proof; all publication/complete-boundary/independent-installation flags stay false.

- The same final private artifact also executed a genuine **66-test-file default-discovery full review** with cold preparation/offline reuse, **all ten analyzers ran and overall PASS**. The controller transported a sealed inventory through two arguments; no argument/resource limit was increased. Raw receipts remain private.


## Independent signed reviewer isolation — 2026-10-05

GitHub finding 4184245681 remains open pending hosted validation of this correction.
The candidate customer job is still required, but a second required job now runs
on a fresh Ubuntu 24.04 VM with its own HOME, venv, cache and immutable staged
subject. It installs published core 0.55.4 and signed Code Review 0.50.1 anonymously
and never executes candidate-controlled host scripts. Installed command loading
occurs before entering the subject; isolated Python and a clean execution
environment exclude candidate module roots, unsigned overrides and credentials.
The published discovery/runtime APIs prepare both exact immutable index snapshots
inside the existing 1,800-second provisioning bound. Review retains all ten
members, changed enforcement, bug-hunt activation and the unchanged 300-second
analysis bound. Required incomplete evidence and every nonzero exit still block.

RED: the missing separate job failed the independent-review regression. An
intermediate same-job design was rejected by independent review because earlier
candidate host scripts could modify its venv. RED: a real malicious candidate
`venv.py` executed before isolated bootstrap. GREEN: the fresh job changes to its
private directory before isolated venv/pip creation; that malicious module no
longer executes. Recipe fixtures cover hostile imports, both bound snapshot
preparations, successful review, exits 2/7 and incomplete preparation that never
runs review. All 17 affected recipe cases passed; affected pre-commit/workflow
contracts total 54 cases. Formatting, strict typing (zero errors/warnings) and YAML
validation passed. No candidate-owned result is promoted to independent authority.

A separate temporary installation of the actual published core/module completed
anonymous installation, loaded the generated entry point and displayed the real
review command help. Its installed-payload authentication returned PASS. Its
actual BasedPyright policy resolver returned UNKNOWN with
`basedpyright_config_ambiguous` for this repository. Therefore a separately
trusted compatibility baseline remains necessary for a green independent review;
this correction does not waive or patch the published gate. Linux analyzer
execution is reserved for hosted CI. Raw receipts/install logs remain private.

Exact head 45ee4cfe9dbf2299c9406bab6e6d0d261f4c00f1 passed the complete
configured native-boundary workflow on ARM64 macOS 14, 15 and 26 in run
37321105249, including 20 control lifecycle cases at 100 repetitions each and
28 protocol cases, startup repetitions and signed production-broker protection
checks. This is boundary-subset proof, not the full analyzer/ABI/customer-release
matrix. Complete-boundary, production and independent customer-installation flags
remain false. The candidate Linux 3.13 customer/corpus job also passed; 3.12 still
hit the existing staged-helper limit.

Independent read-only review-agent closure: No findings, high confidence for
the bounded fresh-job/bootstrap correction. The local deferral guard also
requires the independent job: removing that job was RED (deferral incorrectly
succeeded), then GREEN after retaining every original guard and adding this
requirement. This remains a deferral, never PASS, and cannot run in CI.

Final affected workflow/pre-commit verification: **55 passed**, 5.09 seconds;
strict OpenSpec validation passed. Both Linux candidate customer/corpus jobs for
CPython 3.11 and 3.13 completed successfully at exact head 45ee4cfe; CPython 3.12
remained blocked in the added staged helper, so dependent quality prerequisites
correctly failed rather than becoming green.

A final independent guard review found that working-tree checks could conceal a
staged deletion of the independent job. RED reproduced removal in the index plus
restoration only in the working tree. Both hosted gate markers now come from the
exact indexed workflow; missing indexed contents fail closed. No other local
deferral rule or repository gate is relaxed.

Hosted head aeca3f47's new isolated job installed the trusted reviewer and reached
its preparation entry point, then failed closed. Raw exception logs remained
private, so no specific hosted reason is assumed. A failing regression now
requires an allowlisted public incomplete-preparation summary. Only an explicit enum of known controller codes is published; arbitrary text,
paths and newlines become `unstructured_reason`. Raw
reports and logs remain private, and diagnostic publication never changes exit
handling or acceptance.

The actual installed signed reviewer was also queried against a disposable exact
Git index at head aeca3f47, soft-reset to its merge-base. Its pure discovery
returned **UNKNOWN / policy_parse_failure**, consistent with its separately
observed BasedPyright ambiguity. No Linux analyzer or project code was run on
macOS for this probe. Final diagnostic/deferral contracts: **57 passed**.

## PR minor-wheel and controller-installation corrections — 2026-10-05

Findings 4184894581 and 4185082326: specification added before tests. Focused
RED: 10 failed, 112 passed in 0.55 seconds; undeclared cryptography and all nine
exact-minor pure-wheel platform combinations failed. Existing negative admission
cases stayed passing. After declaring the controller dependency and accepting
only matching minor-specific pure tags, focused GREEN: 181 passed in 2.46
seconds, including native manager, analyzer-view, capsule authentication and
manifest tests. Foreign architecture, future minimum OS/Python, noncanonical
minor and native ABI claims remain rejected. Payload verification is unchanged.

Exact head 41ef7efb's fresh hosted independent signed-review job reported
INCOMPLETE / trusted_index_preparation / policy_parse_failure. The installed
published reviewer still blocks approval; this is independent fail-closed
evidence, not candidate self-review. Raw logs stayed private.

New findings 4185481982 and 4185481999: the complete-snapshot/test-only contract
preceded regression tests. RED confirmed generated/environment entries in a
complete snapshot. After correcting sealed config fixture paths, the test-only
regression reached a reconciled TEST_OUTCOME_NOT_PASS and failed native worker
path normalization at the fallback snapshot anchor. The correction keeps
production coverage inputs unchanged and anchors empty-source outcomes at the
first selected file. The worker's selected-path admission is unchanged.

Affected runner/worker GREEN after checksum refresh: **467 passed in 79.84
seconds**. An independent review-agent found that the initial directory-name
filter also omitted regular fixtures named `venv`. A strengthened fixture was
RED (1 failed, 416 deselected), then GREEN after excluding only directories:
**5 passed, 462 deselected in 0.55 seconds** across affected complete snapshot
and TDD gate cases. Regular fixture bytes and an internal regular-file alias
are retained. Review-agent closure: **No findings** for both corrections.
Controller dependency/minor-wheel closure independently returned **No findings**.

Security finding 4185494833 remains open: scheduling and fresh installations do
not authenticate the candidate-defined workflow. The protected dev baseline
lacks the independent job. A separately reviewed protected workflow revision
and compatible signed controller baseline are required for protected approval.
Neither candidate checks nor local deferral imply that approval.

Actual supplemental physical ARM64 validation used the refreshed ad-hoc native
candidate `sha256:5846f6095dbcaaf12ea67a44ba614d972536dbe77cc41826d5a15207aa5cd2d6`,
macOS 27.0.1 / build 26A434, CPython 3.11.16. A configured test-only project
retained a local environment while declaring `testpaths = tests`. All ten
analyzers ran; nine returned PASS, pytest returned FAIL with
TEST_OUTCOME_NOT_PASS, and the complete review returned FAIL. The selected
failing test remained in the inventory. No publisher keys were used. Raw logs
and reports remain private. This supplements, not replaces, release acceptance.

The earlier unconfigured source-only probe with a test-looking file inside its
local environment returned UNKNOWN / uncollected_test_candidate during static
inventory planning. This is not claimed as default-root success. The configured
probe above verifies the corrected worker/snapshot behavior; complete default
discovery and independent installation gates remain required. All production,
complete-boundary and customer-installation admission flags remain false.

Final scoped typing: 0 errors, 0 warnings, 0 notes. Ruff and strict OpenSpec
validation passed. Normal commit hooks passed, including repository lint and
contracts; only the expressly approved local capsule review was deferred to
GitHub Linux. Module manifest is checksum-refreshed and remains unsigned until
the protected CI/CD follow-up supplies its signature.


## Delivery corrections — 2026-10-06 (Europe/Berlin)

Specification scenarios and NATIVE_ARTIFACT_BUILD_CONTRACT.md preceded new tests.
Source edits followed the observed RED results. Commands below ran in the
isolated finish-460 worktree using controller CPython 3.14.7 / pytest 9.1.1.
Fixture-only test keys never authenticate release artifacts; no publisher key
was accessed. Raw transcripts are private under /private/tmp/specfact460-*.

| Correction | Focused RED command | Observed RED | Full focused GREEN |
| --- | --- | --- | --- |
| Literal distinct UNKNOWN causes in ordinary output | `hatch run pytest -q tests/unit/specfact_code_review/run/test_commands.py -k 'unknown_runtime_diagnostics or unknown_diagnostic'` | 3 failed, 1 passed | Same file: 83 passed |
| Keyless deterministic native assembly | `hatch run pytest -q tests/unit/test_build_macos_native_capsule.py -k unsigned` | 1 failed, 1 passed | Same file: 60 passed |
| Generated controller cache cannot affect module composition | `hatch run pytest -q tests/unit/specfact_code_review/run/test_toolchain.py -k controller_bytecode` | 4 failed | Same file: 116 passed |

The command implementation deduplicates only UNKNOWN analyzer diagnostics and
renders them with Rich markup/highlighting disabled. Existing JSON output
remains unchanged. The unsigned builder never calls a signer, omits manifest.sig,
rejects stale sidecars and retains native-signature checks; signed builder
archive/manifest bytes remain identical. The toolchain exclusion exactly matches
module signing: __pycache__ entries and .pyc/.pyo files. Four new cases verify copied
payload exclusion and unchanged identities. Existing
`test_builtin_analyzer_missing_or_drifted_payload_is_unknown` and
`test_builtin_copy_rejects_payload_drift_after_verification`, included in the
116-test toolchain run, separately verify source/content/mode tamper rejection.

`hatch run contract-test`: 28 passed. `hatch run smart-test`: 4998 passed,
75 skipped, 95 subtests. `hatch run test -n 4` after the bytecode correction:
5002 passed, 75 skipped, 95 subtests, five warnings in 111.19 seconds.
Explicit native proof skips are not passing native acceptance.

Mandatory review command:
`hatch run specfact code review run --enforcement changed --bug-hunt --json --out .specfact/code-review.json`.
Report timestamp 2026-10-05T22:11:36.527467Z; FAIL / UNKNOWN / ci_exit_code=1,
all ten required members identify the missing darwin-arm64-cp312 catalog artifact.
The outer process returned zero and is not proof of gate success. No findings
were returned, but unavailable required evidence still blocks the gate.
One requested bounded review agent found no actionable security/defect issues
in the implementation and incremental bytecode fix; this does not replace the
required capsule review or current-head GitHub reviews.

Full artifact/candidate identities, accepted fixture limits, rejected loader
configuration and remaining release obligations are in
DELIVERY_CHECKPOINT_2026-10-06.md and its machine-readable sidecar. Do not archive
this change or infer production eligibility from the unit/checkpoint results.


Final checkpoint validation: format PASS; type check zero errors/warnings;
lint PASS (Pylint 10/10); YAML/import boundary PASS; unsigned-development
manifest integrity/version gate PASS for all seven modules using the paired
core's public verification key; publish pre-check PASS with unchanged declared
core compatibility (core 0.55.4 exercised); OpenSpec strict validation PASS.
No publisher key or main-release required-signature claim is involved.

After the initial missing-reference failure, only fixed hash-authenticated
Semgrep inputs were restored into ignored worktree storage. The existing
versioned adapter comparison then passed 14/14 cases for cp311, cp312 and cp313,
with reference efbae0e733db2ea821702d36f9dfdd377194a22f11335f4208d4a233a76075f8
and semantic adapter 471977480df00f50a7f3e624802db9d964f2afad0a9f6c01707e803ab51be45e.
This is candidate compatibility evidence; producer/consumer/lock/signed policy
admission and final-artifact Linux/native acceptance remain required.

Staged requirements evidence gate: PASS at planned maturity; implementation
evidence not-yet-available and delivery status proposal-only. The initial branch
diff selected no committed changes, so its no-impact result was not counted.
The staged invocation includes both output paths and the workflow-declared
project/requirements module import paths.

Final independent review identified one P3 evidence-attribution defect: the
ledger attributed source mutation to the four new bytecode cases. Corrected the
claim to cite the existing source-tamper tests that actually ran; no code change
or additional acceptance claim was needed.

The same independent agent read back the attribution correction and confirmed
P3 closed, with no remaining concrete inconsistency in those statements.

## Approved local capsule review deferral — 2026-10-06 (Europe/Berlin)

The human explicitly approved the pending request to defer only the local
Darwin ARM64 feature-worktree capsule review to blocking current-head GitHub
Linux CI, enabling commit/push and a draft PR toward dev. Use
SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux only for local hooks. Every other
quality gate still runs. This records DEFERRED, never PASS; both candidate
customer acceptance and independent signed review remain required before merge.
The approval grants no merge, signing-key access, publication, boundary admission
or production eligibility. The existing UNKNOWN report is retained.

The approved complete local hook pipeline passed after selecting the existing
paired core checkout via SPECFACT_CLI_REPO. It ran format, YAML, imports, lint,
command overview/contract, core documentation accountability, module validation
and 28 contract tests; only capsule review reported DEFERRED. No budget or
required analyzer enforcement changed. Initial missing paired-checkout-path
configuration was corrected without editing the core checkout.

## Hosted independent reviewer pin correction — 2026-10-06 (Europe/Berlin)

PR #498 was opened at 30ace59e after rebase onto origin/dev
74d3fd4dd6f9b171f18857abcc8f659c80d686e9 (documentation/governance changes only).
CI subsequently signed the unchanged 0.51.1 module payload at
687b7d7396b50b2bb1454376688fae532db62c84. Public-key required-signature verification
passed for all seven modules; no publisher key was used locally. Only its
signature field changed. The signed head's existing validation runs were approved
after GitHub paused the bot-authored update. Old-head results cannot replace
current-head acceptance.

Hosted independent review failed during installation: its literal 0.50.1 pin
is not advertised by main's single-version registry; signed published 0.51.0
installation succeeded in the separate customer job. An OpenSpec scenario and
regression against the actual registry/tarball preceded workflow modification.
RED: test_independent_reviewer_pin_is_installable_signed_published_baseline
failed (0.50.1 versus 0.51.0),60 deselected. Update only the pinned published
reviewer to 0.51.0, retaining core 0.55.4, main marketplace, env-i isolation,
independent VM and all enforcement/budgets. GREEN: customer gate plus
pr-orchestrator signing suites, 73 passed in 0.63 seconds. The test verifies literal
released pins, declared core compatibility, actual archive checksum, signed
module metadata and absence of candidate roots/unsigned overrides. Hosted
current-head installation and review remain required.

CodeRabbit skipped automatic draft review; its green status does not count as
review completion. The trusted installed CLI authenticated, but automatic
approval review rejected its external diff transmission as outside the bounded
review-agent authorization. No review ran, no external diff was sent, and no
retry/workaround was attempted. Continue the same authorized bounded agent
review and record external review as unavailable, rather than clean.

The same independent agent found P2 stale expected pins in two existing
deferred-review security tests. A dedicated RED reproduced 2failures/18 passes;
update only their expected literal version to 0.51.0. Existing candidate-host
poisoning, isolated bootstrap and override rejection assertions remain intact.
Complete affected customer/deferred-security/orchestrator suite: 93 passed in
6.76 seconds. The concurrently already-collected full suite retained the old
literals and reported 2failures/5001 passes; repeat on corrected sources is
required rather than treating the earlier 5002-test pass as current.

The same independent agent confirmed P2 closed after reading both corrected
expectations; no remaining finding in this bounded correction. Fresh full-suite
GREEN: 5003 passed, 75 skipped, five warnings, 95 subtests in 90.87 seconds. Final
format/type/lint and YAML/OpenSpec validation pass. The smart run had collected
old expectations and retained the same 2 failures; repeat on corrected inputs
uses four workers without changing selection, tests, budgets or enforcement.


## Hosted candidate review diagnostics and selection — 2026-10-06 (Europe/Berlin)

Current signed head 687b7d73's cp312 deferred review failed with 160 findings
(errors 6, warnings 138, info 16). Required Semgrep-clean execution was incomplete,
Semgrep-bugs was not activated, and targeted pytest reported ambiguous source/test
mapping. Raw reports stayed private; counts and bounded reason codes do not prove
findings are resolved. No budget or enforcement waiver is permitted.

The existing helper omitted bug-hunt; portable partial test mapping rejected
multiple matching filenames even when the caller explicitly supplied a matching
test. Specification preceded regressions. RED: 3 failed, 106 deselected for
bug-hunt plus both input orderings. Implementation forwards --bug-hunt and resolves
only explicitly supplied matching candidates. Unrelated explicit tests do not
resolve ambiguity; other explicit tests and multiple matching tests are retained.
Full discovery and required coverage are unchanged. GREEN: 209 affected tests.

A separate spec/test RED showed hosted diagnostics exposed no public finding
locations. Emit at most 200 tracked relative paths, positive integer lines and
declared severities, retaining the failure exit. Messages, raw findings, private
absolute/untracked paths, booleans and invalid severities stay private. The actual
workflow code is executed by its regression; final affected suite result follows.

Parallel smart-test on the corrected pin inputs had 2 failures / 5001 passes in
existing changed-evidence tests (not stale version assertions): missing projected
pre-enforcement evidence and unexpected required UNKNOWN. This is not a pass.
The default serial smart-test command passed all 5003 tests, 75 skips, five warnings
and 95 subtests in 244.88 seconds on the pin correction. The additional selection/
diagnostic tests were not collected by that already-started run; current-source
smart-test and full-suite validation remain required.

Hosted macOS14 at 687b7d73 passed startup and control fixtures. macOS15 passed all
six startup races at 100 repetitions, then control failed at request-authenticate
in cancel after 73 successful repetitions per repeated group. Its exception was
not allowlisted, so public type was unknown; this is incomplete evidence, not a
passing boundary or a reason to increase timing budgets. macOS26 was still running
at inspection. These fixed fixtures do not accept the final capsules or ABIs.


Follow-up selection/diagnostic affected suite GREEN: 210 tests passed in 5.84
seconds. The same independent agent reviewed the complete uncommitted diff
against 687b7d73 and found no introduced defect. Native diagnostic extension
separately reproduced four failing standard exception-class cases before adding
only those fixed names to the existing allowlist. No runtime deadline, cleanup,
repetition or security policy changed. Actual macOS15 connection failure is still
unresolved pending its detailed sanitized next-run class.

The explicit-manifest checksum command rejected same-version signing against
HEAD as designed. Used existing changed-only mode against origin/dev (0.51.0)
for the unpublished 0.51.1 payload, retaining version-bump enforcement; no same-
version bypass or local publisher key was used. CI must sign the updated payload
again before required-signature release verification can pass.


Current-source mandatory smart-test GREEN: 5011 passed, 75 explicit skips,
five warnings, 95 subtests in 254.79 seconds. Default serial execution retains
complete selection. Native receipt suite: 216 passed in 1.61 seconds. Final
format/type/lint (zero errors/warnings, Pylint 10/10), YAML and bundle imports
passed. Complete local hook pipeline passed staged planned-maturity mapping and
28 contracts / 5058 deselected; only the explicitly approved capsule review was
DEFERRED. The same independent agent also reviewed the four-class diagnostic
extension and entire interacting diff: no introduced finding, current hosted
and signed native release acceptance still pending.

Hosted macOS26 completed successfully at 687b7d73 alongside macOS14; macOS15
remains failed. These are fixed-boundary fixtures with false production flags,
not the final-artifact nine-cell OS/ABI acceptance. No native publication,
protective-policy waiver, budget expansion or issue completion occurred.


Completed Linux current-checkpoint evidence at 687b7d73: cp311 and cp313
customer jobs succeeded, including cold/warm fixture/module checks and all five
pinned upstream corpus entries (Flask/pip, Requests/uv, Hatch, detached Hatch and
Poetry). Downloaded GitHub artifact IDs 11380162044 and 11379471574; each
corpus-summary status is PASS and all five acceptance.json entries are candidate
PASS. This supports the reproduced bytecode composition correction on Linux;
it is neither follow-up-head acceptance nor native acceptance. cp312 stopped at
its failed deferred review, and independent review stopped at unavailable-pin
installation. Do not claim a complete green Linux matrix.

The first bare signature verifier command failed because optional signed modules
needed a public key and its default HEAD~1 baseline already held unpublished
0.51.1. Corrected configuration uses --version-check-base origin/dev and the
paired public module verification key; all seven filesystem payload/version
checks passed, with 0.51.1 greater than dev's 0.51.0. No missing-key allowance,
metadata-only check or version bypass was used. Updated code-review payload has
a development checksum only and awaits CI signing. The nonpublishing module
publish pre-check and OpenSpec strict validation also passed.


Final current-source mandatory full-suite GREEN: 5011 passed, 75 explicit native/
platform skips, five warnings, 95 subtests in 260.40 seconds. Together with the
5011-test serial smart pass, this completes local follow-up unit selection.
Skips and local capsule deferral remain incomplete acceptance, not passes.


## 2026-10-06 socket listener readiness and hosted failure diagnostics

Signed checkpoint 18e77026f480268c58ea72186b682e715104339c has all seven
public-key filesystem signatures verified against origin/dev. Current hosted
Linux cp311/cp313 customer jobs and all three minimum-core jobs passed; cp312
failed required review with four incomplete analyzers. Fresh independent signed
0.51.0 installation passed, but its review exited 1 with its private report
withheld. Current fixed-boundary macOS14/15 passed; macOS26 failed at
request-authenticate with ConnectionRefusedError (38 complete lifecycle rounds,
39 successes for the earlier cases). Runs 37387817080 and 37387816637 are
candidate fixture evidence, not signed native archive acceptance.

Spec preceded new readiness tests. RED4 in specfact460-connect-red.log and RED1
Client-routing test in specfact460-client-route-red.log preceded changes to
control_socket.py / Client. The helper retries only initial ConnectionRefusedError,
rechecks private directory/socket metadata, closes each failed descriptor and
uses the original seven-second connection deadline. Authentication runs once;
other errors remain terminal. No fixture/job retry or expanded metadata,
analysis, cleanup or repetition budget. Existing agent found stale remaining
budget after metadata work; RED2 in specfact460-metadata-budget-red.log confirmed
it. Recompute immediately before blocking connect fixed the finding. Current
native unit GREEN: 304 passed, 5 explicit native-run skips (1.97 seconds).

Two attempted full physical macOS27 runs did not establish lifecycle acceptance.
The first failed the foreign-peer assertion; an isolated owning protocol check
observed foreign-client EOFError and passed. The instrumented second full run
stopped when the exception-port positive target received SIGKILL. Both failures
are retained privately; neither is a boundary or repetition pass. This host is
outside the required macOS14/15/26 matrix. No protection was disabled and no
unchanged third attempt was made.

Hosted diagnostic spec/test RED2 preceded inline workflow changes. A further
synthetic regex-safe PRIVATE_TOKEN RED1 established that arbitrary diagnostic
ids/tokens cannot be public. Both projectors now use finite analyzer/code/tool/
category/rule allowlists, tracked relative public locations, integer positive
lines and a 200-row cap. A tool error may expose only a fixed timeout class.
Independent projection runs trusted inline code in its fresh env-i environment;
no candidate script selects or executes the installed reviewer. Raw messages,
absolute/untracked paths and reports remain private; original failure exits are
preserved. Workflow/customer tests GREEN84 (5.68 seconds before the final
finite-token correction; final rerun recorded below).

Local existing-adapter reproduction identifies the hosted complexity errors:
build_native_capsule CC34, length121 and parameters10; _git_identity CC18;
builder test CC17; published-pin test CC17; independent-isolation tests CC25/
CC20 and local deferral test parameters8. This is diagnostic evidence, not a
passing capsule review; clean-code remediation remains required. Local
basedpyright adapter reports no errors at these locations. No analysis budget
or enforcement waiver was introduced.

Final finite-token workflow/customer rerun GREEN84 in 5.42 seconds. The same
requested bounded review agent verified the deadline finding closed and found
no further introduced issue in socket/inline workflow changes. Required serial
smart GREEN5025/75skips/5warnings/95subtests in 244.80 seconds; full GREEN5025
with identical skip/warning/subtest counts in 248.53 seconds. Format, types/lint
(zero errors/warnings, Pylint10/10), YAML, imports and OpenSpec strict passed.
All seven strict public-key filesystem signatures/version checks against
origin/dev passed at 18e77026; no signed module payload changed in this follow-up.
Hosted review/native acceptance remains required; local capsule review uses
only the human-approved DEFERRED mechanism, never PASS.


## 2026-10-06 bounded builder/workflow clean-code remediation

Existing adapter diagnosis at pushed dc8eb069 found nine error findings. The
maintainer builder's orchestration CC increased from origin/dev's CC28 to CC34,
and its length from113 to121 lines; workflow tests introduced CC17/CC25/CC20 and
an eight-parameter fixture. Before-refactor findings are retained privately in
specfact460-complexity-red.jsonl. This is maintainability refactoring under the
existing spec; no behavior/schema/limit is changed and no new behavioral test is
used to mirror implementation.

The builder now delegates bounded validation, file records, archive planning and
document emission through immutable internal input/payload structures. Its
existing ten named Python arguments and CLI remain compatible. A fresh controlled
unsigned fixture matches pre-refactor archive, manifest and summary bytes exactly:
archive8fc6c287bb1c81acb705482d5ec7a1356b86e4563e516962e82d2b36f06b1112,
manifestc10f8fff9d9fb9e3158050e765695155c61fae402c6db5ccbb3d997d27a4d93a,
summary36f6bcba01602736224ba2b49d7ec58258aac69db707a51b1f43f26006c05558.
These are synthetic fixture identities, never release artifact identities.

Workflow tests now separate trusted fixture setup, job isolation, reviewer scope/
budgets, all five forbidden host routes, installed argument checks and rejected
preparation. The same eight deferral cases and every prior assertion are retained.
Signed registry metadata/checksum and deterministic builder consumer checks are
separate complete tests. No enforcement, required analyzer, budget or host-control
check is removed. Focused GREEN183; direct builder types and standard format/
type/lint (zero errors/warnings, Pylint10), YAML and imports passed. The same bounded
agent inspected the entire interacting refactor and reports no findings.

Origin/dev extraction proves the two remaining builder errors (GitCC18 and the
public ten-argument facade), and listed warning sites in existing builder/customer/
Git tests, predate this request. The facade declaration is unchanged at line695;
compatibility is retained instead of silently changing maintainer inputs. New
phase functions and refactored workflow tests have no complexity/length/parameter
finding. This is not a waiver or PASS for hosted review: all required current-head
capsule evidence still must execute, and raw legacy findings remain evidence under
the unchanged changed-line policy. The OpenSpec change and #460 remain incomplete.


Final refactor gates at ea93ce54: serial SMART **5035 passed, 75 skipped,
five warnings, 95 subtests** in248.93s; full **5035 passed** with the same
skip/warning/subtest counts in258.71s. Logs specfact460-refactor-smart/full.log.
OpenSpec strict and all seven strict public-key filesystem signatures/version
checks against origin/dev passed. Normal hooks and28 contracts passed; local
capsule review remains the approved DEFERRED gate.

Fresh hosted boundary run37391623966 at dc8eb069 passed macOS14.8.9,15.7.9
and26.6.2 on ARM64: each startup receipt completed six races at100 repetitions
and each control receipt completed20 races at100 repetitions, retaining the
original independent cleanup bound. These are fixed broker fixtures, not the
final capsule/ABI matrix or physical-Mac acceptance; production flags stay false.
Current orchestrator37391624311 has all three minimum-core checks passed; cp312
deferred review still fails with semgrep-clean/contracts/semgrep-bugs/targeted-
pytest-coverage incomplete. Its200-location public cap hid later tool errors.
Independent signed0.51.0 installation/preparation succeeded but review exited1
with no report projection; exact cause remains unknown. cp311/cp313 customer
jobs remain in progress when this checkpoint is recorded. No budget is raised.

## 2026-10-06 bounded incomplete-execution diagnostic correction

Specification preceded15 meaningful failing regressions (30 passed) in
specfact460-diagnostics-priority-red.log. The projectors preserve the200 public
location cap and finite identity allowlists, but prioritize execution failures
so later required analyzers cannot disappear behind ordinary findings. Known
Semgrep structured/process/empty-output and CrossHair unrecognized-output
messages map only to fixed classes; private text stays private. Missing reports
produce a fixed INCOMPLETE status. The independently installed review wrapper
catches TimeoutExpired as exit124 under the unchanged300s budget; only that
fixed class is public, and the original failure is retained. No candidate host
helper, report upload, analyzer omission or budget relaxation is introduced.


## 2026-10-06 explicit Darwin-only Z3 derivative and final checkpoint gates

The direct finish-460 instruction authorizes reconciliation of Z3 provenance.
The parent amendment preserves the existing metadata-only specfact.1 artifact
and requires explicit selection of a distinct specfact.2 Darwin projection,
authenticated release/source/native/license linkage and exact foreign omissions.
Spec preceded9 projection failures /28 passes, and then5 lock-policy failures /
9 passes, in specfact460-z3-projection-red.log and specfact460-z3-lock-red.log.
GREEN51 in0.27s; meaningful rejection cases cover absent release, altered/missing/
extra DLLs, altered source/license and output-before-authentication.

Two actual upstream-wheel/release preparations produce the same wheel and
provenance. Specfact.2 wheel82436032 bytes, SHA256
03eb2624d4d19d06020e9a6c5823cf8ac4f6b3fcb0a73e25ef2514d1129982bd.
The new wheel retains29 original non-metadata members, omits only the ten exact
reviewed DLL identities, and carries the authenticated MIT text in dist-info
licenses with correct License-File metadata/RECORD. No MIT claim covers omitted
DLLs. Real historical specfact.1 reproduces unchanged hash
af669755eabd97268a4141983a391cb4a832116d5a2c3cf04a4c53c7650ce72c.
All other candidate closure pins stay unchanged. Fresh scratch clones of all
three native environments completed normal full hash-locked uv sync offline,
pip check and actual Z3 import/solve; no no-deps/resolver bypass or old-worktree
mutation. GitHub API rechecked immutable upstream commit0b6cdcdb signature as
valid on2026-10-06. Existing authenticated license/provenance inputs stay frozen.

The actual confined library-loading experiment with the new full lock closure
passed10/10 analyzers,20/20 clean/defective cases and14/14 versioned Semgrep
parity cases for each of cp311/cp312/cp313 on physical macOS27.0.1 ARM64.
Native scratch roots sf-analyzers-311-e6pgdipc,312-1y9gjbeh,313-g76mptve retain
private receipts. These are candidate fixture results, not final archives, the
supported-OS/ABI matrix, upstream manager corpus or independently installed
customer acceptance. All production/dependency/complete-boundary flags stay false.

The same bounded independent agent found no introduced defect in diagnostics
or Z3 projection/lock/provenance handling. Diagnostic GREEN107 in6.70s.
Mandatory serial SMART **5060 passed,75 skipped,five warnings,95 subtests**
in257.55s and full **5060 passed** with identical counts in259.53s. Regular
format/types/lint (zero errors/warnings,Pylint10),YAML,imports and strict OpenSpec
passed. Logs specfact460-projection-smart/full/lint.log. Earlier published
reviewer failures remain failures; exact-head hosted review still blocks merge.

Completed dc8eb069 Linux artifacts11382485918(cp311) and11381794925(cp313)
verify all five external entries PASS (flask,hatch,hatch-detached,poetry,requests)
across the four managers, in addition to customer fixtures. cp312 and independent
installed review failed; downstream quality stopped at its required customer
prerequisite, never at local lint. All three minimum-core checks passed.

This continuation consumed native fixture and full-suite runs and additional
multi-GB scratch copies, with no paid service or publisher key used locally.
Rollback removes the unpublished source/lock projection while preserving the
historical derivative and all immutable evidence; never promote the rejected
empty-entitlement archives. Final supported artifacts/catalog/publication and
physical full-boundary proof remain open.


## 2026-10-06 incomplete native runtime corrections

The direct instruction to implement incomplete runtime logic authorizes these
bounded corrections. Specs preceded production edits. Managed uv preparation
re-signed a verified maintained executable, changing its hash from
3b1a6d08d941bdb0934ab72804748ae5ddd2aeb35940ee93c7a8a44b67cef151
to ae866acd9cf22058c3278513b5fd7f3392b4aa69b49c9159033d8e2b1f1d3bcd
without replacing its receipt. Six meaningful RED regressions preceded the
signature-preservation and post-inventory/assembly provenance checks; focused
GREEN46 includes accepted assembly and rejection before output. Private logs:
specfact460-managed-uv-red/green.log. All three complete CPython candidate inputs
now include verified maintained uv and Git, unlike the earlier analyzer-only
fixture roots. No publisher signing key or host-manager inference is used.

Actual default changed enforcement failed before native analysis on changecost:
worktree identity entered the ignored .changecost/verify-py311 environment while
project preparation excluded it. Five meaningful REDs (one existing negative
control passed) preceded shared pyvenv.cfg exclusion. Tracked/selected environment
inputs and excluded/external aliases remain rejected. The surrounding suite
caught an overbroad parent check for ordinary packages named venv; it was narrowed
to actual environments, retaining the existing reachable-input mutation check.
All32 worktree enforcement tests passed. Logs environment-identity-red/focused.

Native adapter execution alone did not retain pytest observations in its report.
Seven meaningful REDs preceded bounded ordinary-artifact capture before evaluator
cleanup and projection only after completed replay. Project-origin-v1 remains
explicit and native protected-range evidence remains ineligible. GREEN136 covers
worker, native runner and assembly contracts. SMART subsequently caught the new
projection test inheriting controller PYTHONPATH; its fixture now clears only the
worker's existing unsafe environment list, without changing production admission.
The earlier SMART failure (5079 passed,75 skipped) is preserved, never counted as
PASS. No full suite ran after that failed prerequisite. Logs runtime-followup-smart
and native-pytest-red/runtime-followup-focused.

The pinned Requests repository reproduced project_native_runtime_symlink at the
valid internal tests/certs/valid/ca -> ../expired/ca directory alias. Two meaningful
RED cases (no indirection-free projection and copied-source substitution) preceded
private materialization; the first cycle fixture checked the wrong existing error
and is not counted as meaningful RED. A genuine sibling-directory cycle now rejects.
A subsequent meaningful RED detected removal of an ordinary package named venv;
projection now uses the exact preparation exclusion predicate. It preserves empty
directories and never changes the original checkout. Native dependency runtime
inventories still reject all aliases. Final focused GREEN122 in0.93s covers these
corrections and existing preparation/capture contracts. Logs native-source-alias-red,
native-source-alias-projection-red and runtime-final-focused.

Physical candidate scope is ARM64 macOS27.0.1 (26A434), not the supported matrix.
The observed native fixture lease binds real ad-hoc hardened binaries but is not
authenticated by a publisher manifest. Current worker runtime digest
fbc5bc0d59556de4d6d6aa1af153c3456f7da581cba66e01efdfdf1788b8da35,
11126 regular files, cp313. Module CLI uses the real command/report implementation
with only that fixture acquisition seam. No unsigned-module override is used.
Changelog/source changes after that assembly are controller-side corrections;
this is bounded runtime evidence, not final release-byte acceptance.

Changecost uv cold preparation completed in25.747s; offline identity reuse passed.
Full source CLI review with default changed enforcement completed in149.112s:
all10 members reported ran, no reported UNKNOWN or tool errors. Subsequent
diagnostic inspection found Pylint F0002 internal crashes misclassified as style;
this initial completion-checker PASS is insufficient and is not runtime acceptance.
Actual pytest observer retained842 collected selectors,315 call records and325
coverage files, exit1, project-origin-v1. The existing external acceptance report
checker passed its completion contract; it does not reinterpret failed tests as
PASS or provide protected authority. Initial CLI harness mistakes (calling a
callback directly, stale source-manifest rejection and wrong module entrypoint)
are not attributed to native runtime execution and do not count as acceptance.

Requests commit dae7ef63b4df6eded86637f251fc4e3a06c3b479 used real pip preparation,
no project catalog entry, no host hooks/tests, cold13.317s and offline reuse PASS.
Its selected production/test CLI run completed in32.813s: all10 analyzers ran,
no UNKNOWN;24 collected/called tests,139 coverage files and pytest exit0. BasedPyright
findings remain FAIL. Its Pylint collections.abc import failure was subsequently
traced to missing frozen-module filesystem source, not accepted as a project
defect. Safe summaries are private tmp
specfact460-{changecost,requests}-current-cli.summary.json; detailed reports remain
private. Complete manager/ABI/final-byte/customer acceptance is still required.

Exact-head63e6e83 hosted status: macOS14/15/26 fixed boundary jobs all PASS,
6 startup and20 control races per OS, each100 repetitions. Linux cp311/cp313 all
five corpus entries PASS; cp312 deferred review FAIL with structured Semgrep errors,
CrossHair timeout and pytest tool error. Independent signed0.51.0 review reaches
the unchanged300s timeout. All minimum-core jobs PASS; downstream quality stops
at its prerequisite. These failures remain blocking; no budget, roster, policy,
cleanup bound or installed reviewer is waived or altered. Current-head signing
and CI must repeat after this source change. Native catalog remains empty and
publication/production/complete-boundary flags remain false.


### Remaining source-copy and Pylint runtime logic — 6 October 2026

The bounded reviewer identified executable-mode loss and failure cleaning owned
0555 source-copy directories. Both reproduced (2 RED,5 passed) before fixes;
GREEN7 preserves executable regular/alias files, non-executable data, unchanged
customer directory modes and full owned temporary cleanup. No links are followed
when granting cleanup permission in the discarded private copy.

Inspection of actual candidate report findings invalidated the earlier assertion
of complete changecost Pylint execution: F0002 internal crashes had been mapped
to style, and both projects exposed collections.abc lookup errors. Direct real
CPython/Astroid execution reproduced AstroidBuildingError for relocated
lib/python3.13/_collections_abc.py, which was absent because only the ZIP held
source. Three ABI source-projection tests and six fatal-diagnostic mapping tests
failed meaningfully before implementation (RED9,26 passed,1 skipped). The builder
now retains the exact captured bounded source bytes at relocated paths as well
as the ZIP; no host input or third-party package fallback is admitted. Pylint
F diagnostics remain tool_error even outside selected files, preserving ordinary
findings and required incomplete-evidence semantics. Focused GREEN42,1 explicit
maintainer skip. Private logs native-stdlib-pylint-red/green.log.

The rebuilt real cp313 runtime digest is
23efb3a4b24ee668b508c032ea4164f57b4df3bd1e52df55917f4c0052d90d8e,
11758 regular files. Direct actual Astroid resolution now passes collections.abc,
dataclasses, typing, inspect and abc. Production approval and manifest
authentication remain false. The same bounded reviewer returned No findings,
42 tests passed and1 explicit maintainer skip; installed-customer acceptance
remains unverified.

Before the final fixes, SMART passed5085 tests,75 skips and95 subtests; the
subsequent full gate observed the two then-unfixed source-mode/cleanup tests
failing (5085 passed,75 skipped). That historical failure is retained and does
not count as a final PASS. Both failures have focused passing evidence; final
required gates and real project commands are run against the corrected source.


The independent corpus completion checker also reproduced three false accepts
for tool errors or fatal Pylint diagnostics disguised as style/architecture;
RED3 preceded rejection and GREEN50 includes genuine-finding positive controls.
The bounded reviewer found no defects in this correction. Earlier reports are
not retroactively accepted. Real cp311/cp312 assemblies with corrected source
projection contain11860/11811 files with candidate-only digests
a2a2e1b04adf45936c5ca702f9b430e70f88628c9cea14c4d0a876ade14a51d2
and f23914f258f995bcf31d141ac6599c9e8574030e55f1edea85671714a9bc2204.
All three actual isolated -I -S -B interpreters resolve the five stdlib inference
modules. A standalone diagnostic initially omitted -B and generated bytecode in
the private cp313 candidate; unchanged launch ownership checks rejected it. Only
that diagnostic bytecode was removed, source/native bytes preserved, then the
explicit no-bytecode probes and real project commands were checked again.

Corrected physical cp313 changecost preparation25.222s, offline reuse PASS; full
CLI review143.633s. All10 members execute with no fatal Pylint or tool-error
findings, no UNKNOWN; actual pytest842 collected,315 calls,325 coverage files,
exit1. Corrected Requests preparation15.085s, offline PASS; review36.591s,
all10 members execute, no internal/import-resolution errors;24 tests,139 coverage
files, pytest exit0. The stricter independent completion checker accepts both
completed reports; actual project findings/test failures remain FAIL. Both
reports bind cp313 runtime23efb3a4...90d8e and project-origin-v1 observations.
This is candidate module-command evidence on unsupported supplementary macOS27,
not final archive, installed-customer, complete-boundary or publisher proof.


### Actual four-manager follow-up — 6 October 2026

Pinned upstream Hatch d5f7bfe813dd4d81520def23b43f5d46aad1899c prepared in67.217s
and reused offline, but pytest could not import hatch. Its built root wheel's
generated version file discarded otherwise matching src roots; only backend/src
remained. RED1,1 existing installed positive control preceded generated-wheel-only
module handling; represented sources with changed sizes/bytes still reject, and
matching ambiguous copies retain rejection. No name-only root inference is added.
Bounded pytest-only diagnostic retained the actual ModuleNotFoundError and missing
artifact rejection, rather than repeating the failed full acceptance unchanged.

Pinned Flask d73fa1cdcbd8b1465c151db8924ba58b1dd14e35 completed real native uv
preparation7.117s, offline reuse and all ten analyzers35.686s;19 actual test calls,
161 coverage files, pytest exit0, strict complete-report checker PASS. Pinned
Poetry be56ff07db06e9b82574648433ca228e4cac549b prepared53.298s, offline PASS;
its59.372s review ran7 successful tests with856 coverage files but the report lost
collection selectors because distributed plugins emitted only21 setup/call/teardown
events. This was correctly rejected as incomplete acceptance. RED3 preceded
retention of nodeids from actually observed test phases; empty observers remain
empty and requested unobserved selectors are never supplied. GREEN89 surrounds
Hatch runtime preparation and native pytest observations.

The rebuilt cp313 candidate includes those worker changes, digest
bc2a0a3bb089652b7b93964d5611c784acde99bca3395c53605965ce08327473,
11758 regular files, manifest_authenticated=false and production_approved=false.
Actual Hatch and Poetry commands are rechecked under unchanged budgets; final
archive and installed-customer matrix remain pending.

Before these two new corrections, final v3 SMART and full gates each passed5099
tests,75 skips,95 subtests with5 existing warnings. These passes cover the earlier
source, stdlib and fatal-diagnostic fixes; they do not cover the subsequently
added Hatch/Poetry code. Final v4 mandatory gates are run on that corrected source.


### Generated imports, bounded matching and real manager completion — 6 October 2026

The bounded review found generated wheel Python modules could become unreachable
when a source root shadows the installed regular package. RED stage and collision
regressions preceded an immutable source-overlay in the prepared runtime, projected
only into the owned private project snapshot. Existing originals cannot be
replaced, only Python files enter the overlay, and source/ambiguity binding remains.
A second actual Hatch failure was ModuleNotFoundError:hatch.venv: an ordinary
source package named venv was statically excluded. Meaningful capture RED preceded
removal of that name-only exclusion; real pyvenv.cfg environments remain excluded.
Focused GREEN 131 covered surrounding snapshot, preparation and worker behavior.

The review also reproduced comparison-budget exhaustion for unrelated package
names and an uncharged quadratic shared-tail scan. The meaningful shared-tail RED
uses 3,000 packages named customer_i/common/__init__.py and counted over 9 million
candidate path reads. Full suffix indexing bounds construction and exact matching
within the unchanged 100,000 cap; GREEN 115 covers strict bytes, ambiguity, generated
imports, collision and ordinary environments. Measured Radon CC25 in the introduced
combined helper required extraction; the final orchestration is CC11, extracted
helpers CC2–6. The same reviewer found no defects in either correction or extraction.
Logs source-tail-budget-red/green.log and source-helper-green.log remain private.

A complete real four-manager candidate CLI pass binds runtime
a12c8c15eddc27cc987a6f0b7d0910206d359fc98bf26270d880f5692c2c4f4d,
11758 files. Every project completed ten members, no UNKNOWN, no tool_error or fatal
Pylint findings, strict completion-check PASS and offline cache reuse PASS:

| Actual pinned project / manager | Cold preparation (seconds) | Review (seconds) | Observed tests / coverage files | Pytest exit |
| --- | ---: | ---: | ---: | ---: |
| Requests / pip | 14.604 | 36.713 | 24 / 139 | 0 |
| Hatch / Hatch | 64.651 | 38.551 | 5 / 479 | 0 |
| Flask / uv | 6.736 | 34.297 | 19 / 161 | 0 |
| Poetry / Poetry | 51.677 | 55.285 | 7 / 856 | 0 |

The source revisions are those recorded above and in the unchanged pinned corpus.
Requests reports a genuine BasedPyright finding and FAIL; the others report
PASS_WITH_ADVISORY. Reports retain project-origin-v1. This candidate precedes the
final helper/index extraction, which has focused regression proof; these are not
final-source archive identities. The fixture lease is manifest_authenticated=false,
production_approved=false, on supplementary macOS27.0.1. No native catalog, supported
OS/ABI acceptance or ordinary installed-customer success follows from these passes.

Before the latest overlay/index corrections, v4 SMART passed5104 tests,75 skips,
95 subtests. The subsequent full gate passed5103 and failed one changed-line
identity test while tracked source was being changed concurrently. The guard
correctly returned UNKNOWN; it was not weakened. A stable focused rerun passed
both affected changed-enforcement tests. Final gates are run only after all
tracked code/spec/manifest edits stop; the historical full failure is not PASS.


Final v6 SMART found one stale fixture, with 5,108 tests, 75 skips and 95 subtests
passing. The original capture test derived ordinary data filenames from the live
excluded-directory set, then unconditionally linked data/venv. Correct removal
of name-only venv exclusion left that target absent. The fixture now explicitly
creates venv as ordinary project data; exact capture inventory and both alias
content assertions remain. Runtime dangling-alias rejection is unchanged. This
failed gate is retained; focused proof and stable SMART/full reruns follow.


With the corrected ordinary-data fixture, v7 SMART passed 5,109 tests,
75 explicit skips and 95 subtests. Additional measured clean-code comparison
found new environment ancestry raised identity orchestration CC9 to CC13.
Extraction restores it to CC10 (predicate CC4). Optional pytest observation
projection now belongs to the existing response constructor (CC8), restoring
worker main to its prior CC13; no new legacy warning is introduced. UV
verification and analyzer provenance projection are extracted at their natural
boundaries: input CC38 and preparation CC29 remain at their prior values,
assembly CC41 is below its prior CC42, and new helpers are CC3–7.
Focused post-extraction GREEN: 116 tests, 3.12 seconds. This preserves actual
observation authority, provenance rejection and assembler outputs; final stable
gates follow these extractions. An initial focused command named a nonexistent
test module and collected nothing; it is not passing evidence. The corrected
command uses test_assemble_macos_native_capsule.py.


### Stable final runtime checkpoint gates — 6 October 2026, Europe/Berlin

Final v8 format, type (zero errors/warnings), lint (10.00/10), YAML,
import-boundary, filesystem manifest integrity/version, OpenSpec strict,
requirements planned mapping, publish pre-check and 28 contract tests pass.
Final SMART and full suites each pass 5,109 tests, 75 explicit skips and
95 subtests, with five existing fork deprecation warnings. Neither suite ran
while tracked source changed. Native proof skips are not acceptance passes.
The unchanged module compatibility range includes the actually exercised core
0.55.4. The unpublished module remains 0.51.1; local checksum refresh is unsigned,
with all publisher key variables removed. Fresh CI signature and hosted exact-head
review remain required. One bounded agent's final extraction review found no
defects; it did not independently rerun final suites or authenticate customer
installation. Local authoritative capsule review is the existing human-approved
DEFERRED gate, never PASS. No merge, publication or native admission occurred.

Private logs: /private/tmp/specfact460-final-v8-{format,type,lint,yaml,imports,
signature,openspec,requirements,contract,smart,full}.log. Real candidate manager
reports and complete archive/installed-customer release limitations above remain
separate from repository gate results.


### Signed runtime follow-up and bounded hosted diagnostics — 6 October 2026, Europe/Berlin

Runtime source commit ca1cf81f6915661c41bc781107a4b7907e9923c2 was committed
through the normal hook pipeline and pushed to draft PR #498. Its CI signing
follow-up 4ec4e942ae43e7705163dba573b384785fd6653e changes only the module
signature; all seven filesystem payloads pass public-key signature verification.
No publisher private key was used locally. The approved Darwin capsule review
remained DEFERRED, never PASS.

Exact-head orchestrator run 37447095674 failed. Linux customer cp311 and cp313
passed cold/warm/alternate/targeted fixtures and their external-corpus artifacts
contain status PASS with no failures. The cp312 blocking candidate review failed
with structured Semgrep errors, Pylint timeout, incomplete CrossHair timeout and
a pytest tool_error. Independent installed signed review timed out with exit124
at the unchanged 300-second budget. No raw analysis report was uploaded; these
finite diagnostics do not identify the underlying causes yet. All three minimum
core jobs pass. Quality jobs remain failed by their prerequisites. Native run
37447095490 passes fixed startup/control/lifecycle fixtures on macOS14/15/26;
these are not final archives or the required OS/ABI acceptance matrix. Five
bot-authored test runs were approved for execution, without PR approval, merge,
promotion or signing-authority changes.

New case460-15-20 first failed four genuine assertions for absent recognized
Semgrep tags, while eight privacy controls passed. Both trusted inline projectors
now expose at most three fixed public error-variant tags from bounded details;
unknown names, variant payloads, source excerpts and raw messages stay private.
Structured outer errors precede nested Timeout text. A first implementation
failed two such precedence assertions before correction. Actual local CPython
3.14.7 and 3.12.14 both parsed the 1,500-level bounded nesting control, so that
control is not failing-first evidence. Explicit decoder-fault injection then
failed two tests with a private RecursionError traceback; bounded fallback now
catches it and retains the generic public cause. Existing exits, 300-second
review deadline and 200-location cap are unchanged, and the independently
installed review does not execute candidate helper scripts.

Native candidate Semgrep1.175.0 scanned all41 changed Python files with exit0,
no structured errors and six introduced naming matches in tests. Six test names
were corrected without changing assertions; the same diagnostic now has zero
introduced naming matches. This native version differs from the released Linux
tool and does not resolve its structured errors or establish hosted acceptance.
Focused follow-up GREEN is229 tests in8.55seconds. The existing bounded review
agent reports No findings for the workflow/test diff; it did not rerun tests.
Whitespace observations were corrected. Final local gates are recorded after
all tracked edits stop. Protected native release workflow, final nine-cell
archive acceptance, signed catalogs and independent native customer installation
remain incomplete. No archive, publication or #460 closure is authorized by
these partial results.

Private diagnostic logs: specfact460-structured-semgrep-public-red.log,
specfact460-structured-semgrep-decoder-red.log and
specfact460-semgrep-diagnostic-final-green.log under /private/tmp. Historical
failed gates remain retained rather than relabeled as successful.

The first follow-up signature command omitted --version-check-base and compared
against HEAD~1, the CI signature-only commit parent. Cryptographic checks passed
all seven modules, but that default version comparison failed at unchanged0.51.1.
The corrected command uses origin/dev, matching the normal hook policy. This
invocation failure does not justify a second version bump or signature rewrite.


The preserved Semgrep1.144.0 parser failure now has a concrete reproduction.
The official PyPI ARM64 wheel is39,953,709bytes, SHA256
a10b5076d50cdf5ebbec720580679d69a1172485d52f9fbf24b11af5e3676d0f
(metadata https://pypi.org/pypi/semgrep/1.144.0/json, accessed2026-10-06).
It was hash-verified and only its engine extracted into a private diagnostic
folder; installed analyzer packages, locks and compatibility policies were
unchanged. With metrics disabled, a private HOME and the unchanged90-second
budget, the same41-source scan exits0 but reports Syntax error at the pre-existing
keyword-only lambda at test_commands.py:721. The runtime correctly treats this
structured error as incomplete despite exit0. Semgrep1.175.0 has no such error.
Private equivalent-source controls show parentheses still fail, while positional
lambda syntax parses but loses the keyword-only contract and was not adopted.

After specifying case460-15-21, five local callbacks were replaced with nested
named keyword-only functions. Every return value and test assertion is retained.
The same Semgrep1.144.0 command now exits0 with errors[] and28 real findings;
146 command/projector tests pass in7.40seconds. This is a real older-parser
compatibility fix, not an error-filter waiver. Linux reproduction remains to be
confirmed by exact-head hosted review; Pylint/CrossHair/pytest failures and the
independent deadline remain unresolved. The earlier SMART follow-up passed
5,127tests,75skips,95subtests and five existing warnings in264.75seconds before
this additional callback syntax correction. Final stable gates follow below.

The first private-copy comparison command used a nonexistent local config path
and yielded non-JSON output; the corrected command used the original verified
rule paths. That failed diagnostic is not passing parser evidence.

The first new case mapping used a scenario title slug, while the current native
Requirements import exposes requirement-level scenario identities. The existing
gate rejected unknown-source-scenario. The sidecar now uses the established
parent requirement identity, as every existing case does; the concrete scenario
and parser proof remain explicit. No validator or acceptance rule was changed.


Final parser-compatible follow-up gates: SMART5,127passed/75skips/95subtests
in264.63seconds; full5,127passed/75skips/95subtests in267.70seconds. Both
retain five existing fork warnings and ran with tracked files stable. Format,
type (zero errors/warnings), lint10.00/10, YAML, imports, strict filesystem
signatures/version against origin/dev, OpenSpec strict, corrected planned
Requirements mapping and28contracts pass. The bounded callback review reports
No findings and confirms all five keyword-only signatures, closures and
assertions remain unchanged. Hosted exact-head review remains required; local
capsule review is only the previously approved DEFERRED gate. Final logs are
/private/tmp/specfact460-parser-final-{type,lint,yaml,openspec,smart,full}.log,
corrected Requirements output and the followup-signature-dev/contract/imports
logs. No native production flag, published support or completion is asserted.


### Current-source native workflow and timeout progress — 2026-10-06

The rebuilt e71e74c7 module-source candidate has identity
 df8a9ee20f4a7828068b19d90979ee5ebb8af0bc8fc7c68bea46af2c50aa32ee,
11,758 files, on supplementary physical macOS27.0.1/ARM64/cp313. All ten
members complete without UNKNOWN/tool-error/fatal rows for the pinned
Requests/pip, Hatch, Flask/uv and Poetry projects. Actual observed pytest
calls/coverage files are24/139,5/479,19/161,7/856; pytest exits0 in all four.
Cold preparation/review seconds are13.373/32.044,62.919/40.267,
6.563/32.746 and51.721/52.163 respectively. Prepared offline reuse and the
strict completion checker pass; source checkouts remain clean. Actual reported
findings are retained, including Requests' BasedPyright FAIL. The native lease
is an observed candidate fixture: manifest_authenticated=false and
production_approved=false. This is current-source runtime proof for the
preceding committed implementation, not final archive or installed-customer
admission. Private summaries remain under specfact460-native-upstream-5v0slcd6
and specfact460-final-logic-cp313.summary.json in /private/tmp.

Fresh exact-head e71e74c7 hosted run37453978812 has passed Linux3.13 candidate
customer/corpus acceptance and all three minimum-core checks. Linux3.12's
staged review and the independently installed signed baseline hit the
unchanged300-second analysis deadline. The candidate helper originally returns
1 after TimeoutExpired, causing the public projector to say review_report_missing.
This is a concrete diagnostic bug, not proof of which analyzer timed out.

After specifying case460-15-22, the initial test edit targeted the wrong local
variable; its1PASS is preserved as first-not-red, not failing evidence. Correcting
the actual exit_code assertion to124 produces1FAIL/22deselected before changing
production. The single return correction yields86PASS in6.88seconds across
helper and trusted projector suites. Exit124 remains blocking and does not
synthesize a report. Logs: specfact460-hook-timeout-distinct-{red,green}.log.

Reuse is preferred over new observer infrastructure: the ordinary CLI already
provides ReviewOptions.progress_callback, but capsule snapshot dispatch never
calls it. Case460-15-23 specifies fixed public progress and bounded timeout
projection. The real snapshot orchestration test fails before any dispatch
because the callback is absent; two real TimeoutExpired paths also fail because
the helper discards str/bytes partial stderr. Meaningful RED is3FAIL/4PASS;
unknown/payload-bearing lines, oversized tails and missing stderr already pass
negative privacy controls. Production now calls the existing callback before
member checks and projects only the last exact known analyzer from at most
65,536 stderr bytes/characters. It labels an analysis timeout, never execution
success or authority. No callback is emitted for pre-existing unavailable
member evidence. The unchanged300-second deadline and exit124 are retained.

GREEN is447 helper/runner tests in37.50seconds. An initial combined invocation
named a nonexistent workflow test path and ran zero tests; this is not passing
verification. Corrected projector and final repository gates follow separately.
Private logs: specfact460-capsule-progress-{red,green}.log. The authenticated
independent baseline is unchanged and its deadline remains undiagnosed. These
changes improve candidate diagnosis; they do not resolve analysis performance,
complete protected native delivery, waive review budgets or authorize release.

The completed e71e74c7 run also passes Linux3.11 candidate acceptance; cp312
and independent timeouts keep the orchestrator and dependent quality jobs
failed. No successful overall review is inferred. The bounded review agent
reports No findings for the new timeout/callback/projection diff. Trusted
workflow projector plus helper tests pass92 cases in6.92seconds. Type has zero
errors/warnings, lint10.00/10, YAML/imports/OpenSpec strict and28contracts pass.
The first integrity refresh used explicit manifests with --base-ref alone;
that mode compares HEAD and correctly rejected unchanged unpublished0.51.1.
The corrected --changed-only selection compares origin/dev, retains the required
0.51.0→0.51.1 bump and refreshes only the altered Code Review payload checksum.
Its signature is deliberately absent pending CI-only signing. Other six
signatures verify with the paired public key; the initial verification omitted
that key and is retained as a command failure, not cryptographic proof. The
first Requirements invocation omitted its declared PYTHONPATH and failed import;
the corrected command follows the existing CI recipe. No gate is weakened.
Final SMART/full gates run with tracked files unchanged and follow below.

The corrected planned Requirements gate passes (implementation evidence remains
not-yet-available). SMART passes5,134tests/75skips/95subtests with five existing
fork warnings in264.77seconds. Tracked files were stable during that run.

Full GREEN is5,134passed/75skips/95subtests with five existing warnings in
268.33seconds, again with stable tracked files. Existing native acceptance skips
are not passes. The already verified Semgrep1.144.0 engine parses all41 changed
Python files without structured errors; its25 raw legacy rows contain zero
matches on added lines against HEAD or origin/dev. This is a bounded syntax/
clean-rule diagnostic, not a replacement for the required ten-analyzer review.
The first direct engine invocation omitted the existing parity recipe's
--experimental switch, attempted its absent pysemgrep fallback and produced
no JSON. It is retained as an invocation failure; the corrected explicit native
frontend produces exit0/errors[]. Private outputs remain in the existing
semgrep-1.144-diagnostic folder. Mandatory local capsule review remains the
human-approved DEFERRED gate, never PASS. The changed0.51.1 checksum requires
fresh CI-only signing. Final logs are specfact460-progress-{type,lint,yaml,
imports,integrity-verify-corrected,contracts,openspec,smart,full}.log and corrected
Requirements output under /private/tmp. No publisher key was used locally.

## Managed uv fixed-frame build launch correction — 2026-10-06 Europe/Berlin

The exact unsigned5a0c443b cp311 archive round-trip reached actual pinned Hatch
preparation, but the upstream installer failed with
`project_native_managed_process_incomplete:request exceeds bounds`. A private
read-only broker-output observer reproduced the failure through the unchanged
confined hook; no installed reviewer or execution grant was modified.

After specifying case460-15-24, the new native regression compiled the real Rust
bridge and reproduced the same frame failure: **1FAIL/13deselected**,
`/private/tmp/specfact460-uv-frame-red.log`. The production change uses existing
CoreFoundation serialization to emit binary property lists, preserving every
argument/environment field. The actual native broker parser accepts the compact
payload with spaces/Unicode roots. XML exceeds4096bytes while the final binary
frame fits; individually oversized strings and oversized final binary payloads
still fail before channel use. Frame/count/output/resource limits are unchanged.

The initial native parser suite passes14tests; the parser, managed-uv builder
integrity and analyzer provenance suites pass28tests in1.30s. Logs:
`/private/tmp/specfact460-uv-frame-green.log` and
`/private/tmp/specfact460-uv-frame-provenance-green.log`. The reviewed bridge pin
was updated to actual changed source bytes. A newly built executable and real
Hatch command acceptance are pending, so old executable receipts and5a archives
are preserved as historical candidates, not presented as corrected artifacts.

Exact5a LinuxCI run37458400647 isFAIL: cp311/cp313 customer/corpus and all three
minimum-core jobs pass; cp312 candidate review completes but Pylint/CrossHair
reach their unchanged deadlines and targeted pytest has unusable evidence. The
independently installed signed baseline reaches the outer300-second deadline.
Quality jobs fail at prerequisites. Fixed boundary run37458400298 passes on
macOS14/15/26; it does not test final Python archives. No release flag, catalog,
publication or issue-completion claim follows from these observations.

The offline locked upstream build completed through the existing reviewed builder.
Full maintained-input validation and actual native inspection pass for the new
uv executable SHA256
`2469006ee4df6dc43658d0739c18f6fb57ea01d655e2ba0221adc7665bc0a5f8`;
it retains ad-hoc hardened signing under `ai.nold.specfact.managed-uv`.
The changed bridge SHA256 is
`22171d8ccb60b004d94039c762c1ad986dcf87034b44d5615440401e70b75198`.
The historical executable receipt is rejected because its bridge source differs.
No publisher key or local manifest signature is used.

Three fresh brokers were compiled against the actual Python/direct-tool/uv/Git
designated requirements, then three unsigned capsules were assembled and streamed
through the existing extractor. Exact archive SHA256 identities:

| ABI | Archive SHA256 |
| --- | --- |
| cp311 | `1a95b270374991047c44d88df5fc7174c6c96a8a2acd409b1e27fea7297fa3d7` |
| cp312 | `618c80b1219d3307cd9d030f255a7fd682e748f3bc9412bb698a6fe3bb5ae2da` |
| cp313 | `0129ccf5fa0d251f0abd8f1bff894d1e161350b5375e6a18b9ef5b7888c419a2` |

Every extraction verifies exact bytes, inventory and36actual native signatures.
Manifest authentication is deliberately not performed. The source evidence binds
5a0c443b plus working-tree diff SHA256
`7c0d7a19b379b58d2fc9bfe49372fba11b7764b4a210d05b5b4ed3adb68664dc`;
post-build evidence prose does not replace those captured inputs. The initial
extractor helper launch lacked the module source path and failed to import; only
the corrected explicit-PYTHONPATH launch establishes extraction success.

Actual cp311 Hatch preparation/review now completes all ten analyzers, five tests
and480coverage files with offline reuse; the prior hook failure is resolved.
Cp311 Flask/uv and Poetry also complete. Requests/pip completes all ten members
for each ABI, with24observed tests and139coverage files; its real BasedPyright
finding and FAIL exit are retained. These private-cache, explicit fixture-lease
checks on physical macOS27.0.1 are candidate evidence, not normal installed
customer authentication or the required macOS14/15/26 final-artifact matrix.
Remaining ABI manager results will be recorded separately when completed.

Final stable-patch SMART passes5,135tests/75skips/95subtests/five existingwarnings
in275.82s; full passes the same counts in296.47s. Format/type/lint/YAML/imports,
28contract tests, strict OpenSpec, planned requirements, all7payload/version
integrity checks and bounded independent review pass. The changed0.51.1 module
has checksum-only metadata pending CI signing; existing6signatures verify.
The review agent reports No findings. The known Linux review failures, protected
native release path, signed catalogs and independent installed native acceptance
remain blocking; no release/publication/completion flag changes.

The corrected exact-archive manager probes complete **12/12**: Requests/pip,
Hatch, Flask/uv and Poetry on cp311/cp312/cp313. Every case completes all ten
analyzers and prepared offline reuse, with actual project-origin tests/coverage
observed; no required UNKNOWN or tool failure is hidden. Requests keeps its
existing BasedPyright FAIL; the other slices report PASS_WITH_ADVISORY. These are
explicit unsigned fixture-lease probes on the supplementary macOS27 host.

| ABI | Manager/project | Cold preparation(s) | Review(s) | Observed calls | Coverage files |
| --- | --- | ---: | ---: | ---: | ---: |
| cp311 | hatch/hatch | 61.438 | 41.53 | 5 | 480 |
| cp311 | pip/requests | 13.585 | 33.185 | 24 | 139 |
| cp311 | poetry/poetry | 52.479 | 57.387 | 7 | 877 |
| cp311 | uv/flask | 6.55 | 33.731 | 19 | 161 |
| cp312 | hatch/hatch | 64.563 | 38.762 | 5 | 480 |
| cp312 | pip/requests | 15.72 | 39.005 | 24 | 139 |
| cp312 | poetry/poetry | 49.825 | 52.927 | 7 | 857 |
| cp312 | uv/flask | 6.822 | 33.378 | 19 | 161 |
| cp313 | hatch/hatch | 63.701 | 38.147 | 5 | 479 |
| cp313 | pip/requests | 14.815 | 39.145 | 24 | 139 |
| cp313 | poetry/poetry | 54.571 | 54.389 | 7 | 856 |
| cp313 | uv/flask | 6.985 | 35.953 | 19 | 161 |

Private fixed-field aggregate: `/private/tmp/specfact460-uv-frame-complete-matrix-evidence.json`.
Original failed5a cp311 Hatch evidence and all old candidate archives remain
preserved. These12project runs do not replace clean/defective full boundary
acceptance, macOS14/15/26 matrix, anonymous signed acquisition or independent
installed-customer proof.

The corrected exact cp313 archive also completes the physical `changecost`
full-scope candidate CLI in143.146s after24.574s cold preparation, with verified
prepared offline reuse. All ten analyzers run with no requiredUNKNOWN. Actual
project-origin pytest observations retain842collected nodes,315call records,
325coverage files and process exit1. Overall review remainsFAIL; project findings
and the actual nonpassing test outcome are preserved. This candidate fixture
lease does not authenticate the manifest or exercise normal installed native
acquisition. Private summary:
`/private/tmp/specfact460-uv-frame-changecost-cli.summary.json`.


## Z3 test review cleanup and signed-runtime CI — 6 October 2026 (Europe/Berlin)

Normal hooks committed the managed uv runtime correction as
`964ceda0c1f57515eedeece64e9869dca1c82b41`; CI-only module signing followed as
`88f91ca9f27092385a5c02159adf2c44ae5759e6`. The worktree fast-forwarded cleanly
and required public-key/payload/version verification passes all seven modules.
No local publisher key or archive authentication was used.

The prior cp312 hosted public locations contain two introduced Z3 test warnings:
CC13 at line339 and kiss.nesting.warning at line378. The existing full-result
Radon adapter reproduces both in `/private/tmp/specfact460-z3-review-red.json`.
Splitting receipt verification from identity assertions and separating license
mutation from four flat payload mutations retains every provenance, false
admission, RECORD, digest and reject-before-output assertion. The same adapter
returns no findings for the changed test section in
`/private/tmp/specfact460-z3-review-green.json`; all38Z3 tests pass. The bounded
existing review agent reports No findings and confirms preserved assertions,
with no product, authentication, budget or authority changes. This inspection
of capped public locations is not complete hosted review assurance.

Final format/type/lint pass, including no type diagnostics and Pylint10.00/10.
SMART and full each pass5,136tests,75explicit skips,95subtests and five existing
warnings, taking266.30s and267.11s respectively. These repeat gates are justified
by the confirmed review findings and changed test structure. Native candidate
payloads are unchanged by the test-only follow-up; their12/12manager/ABI and
physical changecost observations above remain candidate evidence.

Exact signed-runtime orchestrator37468195895 fails: independent installed
review job112285254663 reaches the unchanged300-second analysis_timeout, and
cp312 staged review job112285254779 also reaches that outer deadline. Its last
fixed public analyzer marker is targeted-pytest-coverage; this does not establish
the underlying cause. Private logs are retained at
`/private/tmp/specfact460-88f91ca9-{independent,cp312}.private.sanitized.log`.
The prior5a per-analyzer Pylint/CrossHair/pytest failures remain historical
evidence, not substituted for this current timeout outcome. No failed job was
manually rerun and no budget changed.

At88f91ca9, all three minimum-core jobs, required signatures, requirements,
docs and macOS14/15/26 fixed boundary fixtures pass; Linux3.13 customer
job112285254767 passes. Linux3.11 is still running at this checkpoint.
The boundary workflow37468195615 tests fixed startup/control fixtures, not
accepted final archives. The test-only follow-up requires its own exact-head
CI; neither local DEFERRED review nor these partial results authorize merging.

Keep PR498 draft and #460 open. Protected native build/accept/sign/stage,
authenticated catalog entries, final nine-cell archive acceptance and ordinary
independent signed installation remain incomplete. No merge, publication,
production admission, issue close or OpenSpec archive occurs.


## Owner-approved native delivery implementation — 6 October 2026 (Europe/Berlin)

The owner requested implementation of the three remaining release/loader/customer
items and expressly accepted normal first-run trust warnings without an Apple
Developer account. No merge or publication was authorized. Specs/design/proposal/
requirements were synchronized before new behavior; strict OpenSpec validation
passed. The linked issue remained OPEN/Todo with complete public metadata. Work
remains in the attached codex worktree and draft PR498.

New release tooling/workflows have 49 focused passing tests. Failing-before logs
in `/private/tmp/specfact460-release-*-red.log` retain archive/profile validation,
protected source/key boundaries, incomplete/mismatched matrix rejection, unsigned
or substituted upload rejection, duplicate JSON and boolean-type rejection,
exclusive staging against an empty-output race, missing/weak environment rules,
actual extension-phase schema, required private copy modes, and read-only trust
observation regressions. Ephemeral unit keys cannot establish publisher authority.
The orchestration wrapper reuses existing tested builders; its additional input
validation tests are not represented as a failing-first new runtime experiment.

A bounded independent reviewer identified the missing clean-CI Node staging
parent, insufficient final-byte lifecycle binding, and a five-second clock that
started after waiting for controller exit. All were corrected. The fake-clock
six-second disappearance case demonstrably failed before the deadline correction
and passes after it. The reviewer confirmed the deadline fix with three passing
boundary tests and no further finding in that bounded correction scope.

The new cp312 build entry point assembled real native archive bytes, identical to
the previous manifest/archive digests in NATIVE_RELEASE.md. All three actual ABI
archives pass strict archive and narrow loader validation. The new acceptance
CLI exercised actual consumer authentication with an explicitly ephemeral fixture
key, real archive extraction/codesign, cold/offline cache verification, actual
Flask preparation and all ten module-command analyzers. The cp312 v4 report
records 20 collected/20 called tests, 162 coverage files and a passed real
MarkupSafe extension test. An initial extension checker mistakenly used an
outcome string rather than the actual boolean passed field; its RED regression
and successful v4 rerun retain that failure honestly.

The post-correction delivered cp312 component proof at
`/private/tmp/specfact460-release-delivered-boundary-cp312-v3/delivered-boundary.json`
passes 100 actual repetitions each of controller loss, bootstrap failure and
exception-port denial. Source/provenance SHA-256 values bind the exact delivered
broker/bootstrap/verifier/self-test/policy bytes. The harness neither compiles nor
patches nor re-signs those components. Cleanup observation time is included in
the unchanged five-second deadline. This physical Mac is 27.0.1/26A434; local
receipts explicitly cannot replace macOS14/15/26 hosted proof or ordinary signed
customer installation.

Direct local AST/AI-bloat/ordinary Radon adapters report zero findings after
introduced complexity warnings were resolved. An attempted direct sealed
full-result Radon pass cannot reconcile upstream CLI omission of constant-only
modules; it is incomplete local authority, not PASS. The unchanged required
capsule review remains DEFERRED to exact-head GitHub Linux under prior owner
approval. No hosted timeout budget or required analyzer gate was weakened.
Explicit script typing reports zero errors/warnings, Actionlint validates both
actual workflows, and the CI preparation shell passes bash syntax validation.
Final repository gate outcomes and the exact commit/CI state follow below.

No native protected environment or signing key was configured, no candidate blob
was uploaded, no authenticated production catalog entry was installed and no
normal customer PASS is claimed. Existing official module assets are unchanged;
all seven existing signatures continue to verify against the public root. The
implemented normal-customer gate forbids developer overrides/credentials and
records actual quarantine attributes without changing them. Visual first-run
dialog observation remains unavailable in unattended CLI evidence. #460 remains
open, the PR remains draft, and OpenSpec archive is pending actual acceptance.

Final implementation gates: full 5,185 passed/75 skipped/95 subtests/five existing
warnings in311.06s; SMART the same counts in311.27s; contracts28 passed. Format,
default lint/type (Pylint10.00/10), explicit new-script typing, YAML/imports,
Actionlint, bash syntax and all seven required module signatures pass. Strict
OpenSpec validation passes. Requirements gate passes at planned maturity and
correctly retains implementation evidence not-yet-available for complete release
acceptance. Logs: `/private/tmp/specfact460-release-{full,smart,contract,lint}-final.log`;
new-script diagnostics: `/private/tmp/specfact460-release-script-type-final.log`;
requirements: `/private/tmp/specfact460-release-requirements.{json,md}`.

No final acceptance checkmark, production flag, issue closure, automatic merge,
publication or OpenSpec archive is inferred from these repository gate results.


## PR Actions timeout diagnosis and fixture correction — 6 October 2026 (Europe/Berlin)

At eeedb18c, orchestrator37530542945 fails cp312 staged job112498571408 and
independent signed job112498571534 at the existing300-second outer deadline.
The candidate's final fixed public marker is targeted-pytest-coverage. Private
sanitized job logs are retained at
`/private/tmp/specfact460-eeedb18c-{cp312,independent}.private.log`.
These markers do not alone establish the precise hosted bottleneck. Module
signatures, requirements, docs, minimum-core and all three fixed native boundary
jobs pass; the new native tools build is still running at this observation.

Read-only planning selects35test files/1,597tests for the61changed Python files.
The unchanged selected suite passes locally in54.39s, with five synthetic
changed-enforcement tests taking5.23–5.89s each. Their analyzer execution is
mocked, but they nevertheless bind the entire real caller's checkout repeatedly
through `_worktree_analysis_identity`. The baseline and index controls in an
installed review can make this redundant work more expensive; that hosted
contribution remains a hypothesis until fresh CI completion.

The portable-review specification now requires these synthetic contracts to use
bounded isolated subjects while preserving real identity/security tests. A
fail-on-real-Git-inventory fixture guard first produces five failures in
`/private/tmp/specfact460-enforcement-fixture-red.log`. Supplying actual tiny
standalone source files and an isolated working directory then passes all29
matching tests in3.25s. The same35-file selected inventory, with no tests removed,
passes1,597tests/one pre-existing maintainer skip in27.63s after the correction.
The relevant source-identity, mutation, cached-index, real capsule and customer
checks are unchanged. No300-second deadline, inner analyzer timeout, blocking
exit124, authenticated reviewer or review subject is replaced or weakened.

The new fixture initially lacked its separate src parent; that setup error was
corrected before passing evidence. Timing logs are
`/private/tmp/specfact460-review-selected-duration{,-green}.log`. Typing/lint and
strict OpenSpec pass. Direct local clean-code adapters find no introduced fixture
finding; this is not hosted capsule-review authority. Final gates and fresh-head
CI results follow; do not infer green PR status from the local speed improvement.

Fixture-correction gates: full5,185 passed/75 explicit skips/95subtests/five
existing warnings in278.76s; SMART the same in277.36s; contracts28 passed.
The touched advisory-readback test's size guidance was subsequently resolved by
grouping identical report/model checks; all13previous asserted values remain.
All29focused enforcement tests pass after that grouping, and direct changed-line
AST/AI-bloat/Radon adapters return zero findings. Format, default typing/lint and
strict OpenSpec pass. Required300-second hosted review is still pending fresh
source; these local tests are not a substituted capsule review PASS.


## Bounded hosted timeout profiling — 6 October 2026 (Europe/Berlin)

At609b72f8, fresh orchestrator37534332122 again fails candidate cp312
job112511410095 and independent signed job112511409991 with analysis_timeout.
The candidate marker remains targeted-pytest-coverage. Both3.11/3.13 customer
jobs pass; all three quality jobs fail at the required customer prerequisite,
before lint/tests. All macOS14/15/26 fixed boundary jobs pass. The preceding
native tools job112498499046 actually completed successfully in30m13s; its
following build jobs were superseded by the609b72f8 push. Current native tools
job112511470796 is still running at this observation. These facts replace the
earlier pending observations; the local fixture timing improvement did not
resolve the hosted timeout, and no hosted review PASS is claimed.

After two failed hosted attempts, the next evidence step is a separate,
non-authoritative candidate-only profiling replay. The original required review
continues to fail with its unchanged300-second outer analysis budget. Only
following that failure, a separately installed/hash-pinned py-spy0.4.2 wheel
samples the same staged subject and helper command as the ordinary runner user.
GNU timeout stops the diagnostic at280seconds with a5second final kill bound.
Authenticated reviewer code, sandbox permissions, test selection and independent
signed reviewer are unchanged. No root profiling, ptrace policy change or raw
profile upload is used. Raw stdout/stderr/stacks remain runner-private; a stdlib
data-only helper emits at most20 known tracked public source/functions with
inclusive sample counts, not elapsed seconds. Malformed indexes, oversized
profiles, ambiguous suffixes and linked sources fail closed or are omitted.
DIAGNOSTIC_ONLY/DIAGNOSTIC_UNAVAILABLE cannot authorize merge or publication.

Specification/evidence mapping preceded tests. Initial import RED is retained
in `/private/tmp/specfact460-profile-summary-red.log`; the absent workflow
step gives a separate RED in `/private/tmp/specfact460-profile-workflow-red.log`.
The new helper and recipe pass86focused tests (including the existing real
staged-tree/failure-propagation tests), explicit script typing with zero
diagnostics, Actionlint and direct AST/AI-bloat/ordinary Radon with zero findings.
Logs are `/private/tmp/specfact460-profile-green.log` and
`/private/tmp/specfact460-profile-clean-code.json`. Strict OpenSpec and planned
requirements evidence gates pass; planned maturity is not release acceptance.
The local candidate runbook now explicitly supplies required SOURCE_SHA.
Final mandatory gates and the next hosted diagnostic result follow.


## Hosted native input corrections — 7 October 2026 (Europe/Berlin)

Native run37534331581 tools completed successfully, then all three archive builds
failed before execution. Completed private logs are retained at
`/private/tmp/specfact460-native-{112521945682,112521945756,112521945818}.private.log`.
cp312/cp313 reject `Git input must be immutable with one executable image`;
cp311 first rejects `installed distribution does not match ABI lock`.

The download action resets artifact files to0644/directories0755. Restoring only
the two executable bits left provenance/license inputs writable. Preparation now
removes all write bits from both managed-tool trees and restores only the two
fixed declared executable images. The unchanged Git validator checks exact
inventory, immutable modes, executable exclusivity, provenance and bytes.

CPython3.11 venv bootstrap additionally seeds setuptools, which none of the
reviewed ABI locks admits. Fresh actual cp311 reproduction produces bootstrap
setuptools79.0.1; the exact fresh-venv uninstall command leaves only bootstrap
pip. The cp311 preparation recipe now removes only setuptools before the
unchanged hash-pinned installation. It does not add that ambient dependency to
the lock or relax installed-distribution/RECORD admission. Reproduction/removal
uses `/private/tmp/specfact460-native-bootstrap-reproduction` and
`/private/tmp/specfact460-native-bootstrap-removal.log`.

The specification precedes two RED regressions retained at
`/private/tmp/specfact460-native-transport-red.log`. Executing the actual hosted
restore recipe against transported-style inputs now passes immutable admission
with identical bytes; an extra executable remains rejected. Together with
native release, profiling and existing staged/independent CI tests,137tests pass
in7.77s (`/private/tmp/specfact460-native-transport-green.log`). Explicit typing,
Actionlint for both workflows, shell syntax and direct AST/AI-bloat/ordinary
Radon pass with zero findings. Source receipt, signing controls, reviewed pins,
analysis deadlines and Linux prerequisite failures remain unchanged.

Primary references, accessed7October2026:
- https://github.com/actions/download-artifact#maintaining-file-permissions
- https://docs.python.org/3.12/library/venv.html (setuptools ceases to be a venv core dependency in3.12)
- https://github.com/benfred/py-spy/tree/v0.4.2 (external child/subprocess profiling; raw memory-derived stacks remain private)

Final pre-push full/SMART results and fresh hosted observations follow. Existing
review failures and unexecuted nine-cell acceptance remain outstanding.


Pre-push gates: SMART5,207 passed/75 skips/95subtests/five existing warnings
in249.56s, then full5,208 passed/75 skips/95subtests/five existing warnings
in255.37s. SMART collected before the final private-input CLI guard was added;
full collected before the two hosted native recipe regressions were added.
The final137focused tests cover those additions and all release/diagnostic
recipes; the final subset rerun also passes after import formatting. Final
lint/typing, signatures(all7), contracts(28), YAML/import boundaries, Actionlint,
shell syntax, strict OpenSpec and planned requirements pass. No test or analyzer
is removed. The owner-approved local review remains DEFERRED to blocking
exact-head Linux CI, never PASS; raw profiling is not acceptance evidence.


## Hosted profile readback refinement — 7 October 2026 (Europe/Berlin)

At56ff60b9, independent job112524988404 again times out; candidate
job112524988393 times out at targeted-pytest-coverage. Its separate bounded
profiling step completes successfully, yielding54,117 sampled thread stacks.
The private job logs are `/private/tmp/specfact460-56ff60b9-{cp312,independent}.private.log`;
only the static-symbol public summary is retained at
`/private/tmp/specfact460-56ff60b9-profile.public.json`. Top20 inclusive entries
are predominantly controller/wait ancestors. The capsule request has2,183
inclusive samples, but this alone does not identify the expensive leaf call or
establish elapsed attribution. This is real sandbox-worker evidence, not review
acceptance; the raw profile is intentionally not uploaded or recoverable.

The next bounded diagnostic refines readback, retaining at most20 inclusive
entries plus20 deepest-public entries. Each validated stack preserves order;
inclusive counts still deduplicate repeats, while the deepest admitted public
frame receives one leaf sample. Private library/command/process labels never
enter output. Specification precedes RED assertions for the missing field and
ancestor/leaf distinction (`/private/tmp/specfact460-profile-leaf-red.log`).
The refinement passes138release/CI/diagnostic tests, zero explicit typing
warnings, zero direct clean-code findings, formatting/lint and strict OpenSpec.
The existing required300-second gates and shorter280+5second diagnostic remain
unchanged. Logs are `/private/tmp/specfact460-profile-leaf-green.log` and
`/private/tmp/specfact460-profile-leaf-clean-code.json`.

Supplementary local timing with coverage and the declared Rust prerequisite
runs the expanded36-file selected inventory:1,622tests pass/one maintainer skip
in28.66s (29.17s wall time). The command retains exit1 from the native global
coverage threshold; this isolated selected suite is explicitly diagnostic-only,
not a review PASS. The first diagnostic omitted the local Rust path and failed
its mandatory macOS parser regression, corrected by the declared prerequisite.
Both logs stay at `/private/tmp/specfact460-selected-coverage{,-green}.private.log`.
Local Python3.14 timing cannot establish hosted Python3.12/sandbox equivalence.
The exact hosted bottleneck remains unknown until useful leaf evidence arrives.


## Hosted ownership-I/O correction — 7 October 2026 (Europe/Berlin)

At c65b8a5e, independent job112532774667 and candidate job112532774779
again fail the unchanged review deadline. Candidate replay yields53,055 sampled
thread stacks. Its deepest-public entries include `_record_row`954 samples,
`_execute_crosshair`1,192, and the controller subprocess waits. These counts
span processes/threads, can overlap, and are not seconds or a causal attribution
to CrossHair. Public summary: `/private/tmp/specfact460-c65b8a5e-profile.public.json`.
Raw runner stacks remain private and are not acceptance authority.

Concrete inspection finds installed ownership scanning before invalid request
decoding and even when there are no Python attribution inputs. The specification
precedes guarded regression tests: seven malformed/nonobject/invalid-selector
requests must reject without RECORD I/O or target launch; empty/non-Python inputs
must return the identical empty bridge without distribution inspection. RED
logs are `/private/tmp/specfact460-pytest-request-io-red.log` and
`/private/tmp/specfact460-empty-attribution-io-red.log`. Both guards fail on the
previous implementation. The first correction also exposes the existing stale
observation regression: preparation failures must clear the owned observation
before preparing a command, not only before launch. Both malformed preparation
and valid-request startup failure now retain that assertion.

The corrected focused suite passes183tests in7.06s; explicit typing reports
zero errors/warnings and direct AST/AI-bloat/ordinary Radon reports no findings.
Logs: `/private/tmp/specfact460-pytest-request-io-{green,lint}.log` and
`/private/tmp/specfact460-pytest-request-io-clean-code.json`. Valid nonempty
requests retain full ownership, byte identity and target coverage checks. No
analyzer, deadline or independent-review authority changes. Hosted contribution
to the timeout remains a hypothesis until both fresh reviewers pass.

The pending module version0.51.1 remains above target dev0.51.0; checksum
refresh uses `--changed-only --base-ref origin/dev --allow-unsigned` with local
private-key variables unset. This removes the stale signature and passes the
feature-branch checksum/version gate for all seven modules. It is not signed
release acceptance: existing same-repo PR CI must sign the fresh payload before
strict public-key verification and a subsequent exact-head review run. No
registry or publisher promotion occurs. Full/SMART final results follow.


The initial full and SMART runs each expose27old synthetic fixtures passing
`{}` into the now-validated request, yielding5,194passes/75skips and failures
before their intended coverage/non-pass assertions. Their original logs remain
`/private/tmp/specfact460-pytest-request-io-{full,smart}.log`; these are failures,
not passing evidence. The evidence fixtures now supply `selectors:["."]` and
the discovery fixture its actual `test_case.py` selector. Every observation,
coverage, malformed-root and non-pass assertion is preserved. Final reruns use
separate `-v2-` logs below.


The corrected combined focused suite passes244tests in16.35s. The long native
usage-error evidence test is then split into a subprocess setup helper and the
original assertions, preserving actual exit4/configuration diagnostics and
retained target execution. Its61fixture/discovery tests pass after extraction;
direct AST/AI-bloat/ordinary Radon for all six modified Python files reports
zero findings (`/private/tmp/specfact460-pytest-request-io-v2-clean-code.json`).
Full/SMART reruns collect the same5,296tests before this fixture-only extraction;
the separate rerun covers its final bytes.

Native run37540557846 now passes managed tools and all three exact ABI archive
builds, establishing correction of the previous immutable-Git/setuptools input
failures. Nine exact-byte execution cells are running, not yet accepted.


Further inspection identifies fixture-owned observations whose mocked target
launch still scans the real installed runtime metadata. Autouse distribution
guards fail38of61evidence/discovery cases on the prior fixture setup
(`/private/tmp/specfact460-synthetic-ownership-red.log`), proving the extra I/O.
Synthetic playback now supplies an explicit empty ownership bridge, matching
its preexisting installation-free local context; every coverage/non-pass
assertion and actual native subprocess discovery remains. The guards remain
active so future fixtures cannot silently read the capsule's installed RECORDs.
Dedicated installed-coverage/portable-worker/target-coverage tests retain real
planner and attribution checks. This concrete fixture leak fits the hosted
RECORD samples but its elapsed contribution still requires hosted confirmation.


Before final fixture ownership isolation, full and SMART each pass5,221tests,
75explicit skips,95subtests and five existing warnings in265.53s/264.69s.
Final guarded fixture/ownership suite passes244tests in15.13s, lint/typing
passes and direct clean-code findings are empty. Final full/SMART with permanent
guards are running at `/private/tmp/specfact460-synthetic-ownership-{full,smart}.log`.


Final guarded full and SMART each pass5,221tests,75explicit skips,95subtests
and five existing warnings in259.05s/259.11s. Their `synthetic-ownership` logs
are final-source evidence; final lint/typing, direct clean-code, feature checksum
and version gate,28contracts, docs/YAML/import boundaries, staged requirements
and strict OpenSpec pass. Normal implementation hooks ran with the owner-approved
local ARM64 capsule review DEFERRED to unchanged blocking Linux CI, never PASS.
The earlier specification amendment failed its newly required evidence mapping;
460-19-1 adds that mapping and the next normal hook passes.

Pre-push native baseline has tools plus all three archive builds PASS. Its nine
execution cells have not completed. The fresh payload requires new source-bound
CI signing and review; pushing necessarily supersedes this older concurrency
group. No partial cell or diagnostic replay is counted as release acceptance.


CI signs the fresh0.51.1runtime payload at6ba108b1d24daab47f38238e28863db1530c814b
following implementatione96d73ccd52821a630bc624d948eb2a06401f434. Fast-forward
readback verifies all seven modules with `--require-signature`, current filesystem
payloads, version-bump comparison against origin/dev and the publisher public
key; no local private key is read. The only signing diff is the manifest
signature. Bot-head workflows report `action_required`; this substantive
readback-evidence commit triggers ordinary exact-signed-payload PR checks.
Required Linux reviews and native nine-cell acceptance remain pending; no
workflow approval or publisher environment policy is bypassed.


## Hosted native proof teardown race — 7 October 2026 (Europe/Berlin)

Signed-head97359e22macOS15boundary job112547218993 fails solely in the
exception-self-test finally block: identity observation sees the owned broker,
but the broker exits before SIGKILL, producing ProcessLookupError. Actual
exception-port denial and five-second worker cleanup assertions precede teardown.
Private log: `/private/tmp/specfact460-97359e22-boundary15.private.log`. This
failure is retained, not relabeled PASS. Specification and regression guards
precede cleanup changes; `/private/tmp/specfact460-broker-cleanup-race-red.log`
has three failing missing-contract tests before implementation.

Cleanup now tolerates only process-not-found after an exact identity match.
Tests also require permission errors to propagate and absent/reused identities
never to receive a signal. The proof harness is separated into protocol setup,
positive/failure controls, held-worker assertions and measured controller loss;
all original wire values, assertions and five-second deadline remain. Partial
process identities stay captured by the outer finally before assertions.
The delivered component path remains byte-for-byte copy-only and100repetitions
per lifecycle/exception case; its acceptance assertions do not change.

Initial focused boundary/receipt tests pass222/three explicit native skips.
Actual local native proofs plus delivered-boundary unit tests pass9tests after
refactoring (`/private/tmp/specfact460-broker-cleanup-race-native-typed.log`);
local macOS27.0.1 is supplementary, not the supported hosted matrix. Direct
clean-code passes after resolving legacy proof-function complexity and length;
normal lint additionally requires stdlib suppress and bound loop captures.
Earlier intermediate parse/type/lint failures remain in `broker-cleanup-race`
logs and do not establish passing evidence. Final full/SMART and lint follow.
No module payload, signature, runtime boundary or reviewer budget changes.


Final cleanup-correction full and SMART pass5,224tests/75explicit skips/
95subtests/five existing warnings in259.59s/258.80s. Final native/unit subset
passes9tests in3.66s, including retention of a prior proof failure through an
already-exited cleanup. Normal hooks pass final lint/typing, staged requirements,
28contracts, docs/YAML/imports, and the unchanged seven strict module signatures.
Direct full-file AST/AI-bloat/ordinary Radon has zero findings after phase helpers
and compact unchanged request encoding. Full runs collect before the final
stdlib-suppress/bound-capture spelling and original-failure assertion; the
final native subset verifies those final bytes.

At97359e22the independent reviewer job112547359085 still reports
analysis_timeout. Candidate job112547359287also fails required review and its
bounded diagnostic replay is running. This proves the ownership fixes alone
are insufficient, despite the concrete guarded I/O defects. Read-only current
selector inspection chooses40test files, with Hatch/default and unchanged
`-ra -v --import-mode=importlib`; no whole `tests` operand is selected. The
manual Hatch-script expansion hypothesis does not apply to the capsule engine,
which consumes exported extra-args and selected paths. No tests are dropped
and no project configuration or budget is changed to hide the failure.


## Final hosted leaf readback and bounded test policy — 7 October 2026 (Europe/Berlin)

The completed97359e22candidate replay yields54,619thread samples. RECORD
scanning is no longer a top20leaf, CrossHair has126leaf samples (previous1,192),
and portable pytest has1,194, discovery subprocess observation358 and target
bootstrap573. Counts span threads/processes, overlap and are not elapsed
seconds. Public summary: `/private/tmp/specfact460-97359e22-profile.public.json`;
required review remains failed. Both Python3.11/3.13 customer cells and all
minimum-core cells pass; all quality cells fail the customer prerequisite.
Fixed macOS14/26boundary cells pass; macOS15has the retained teardown race.

Actual reviewer-plugin execution of the exact40-file current selector inventory
with two workers first fails the existing missing-native-alias-API fixture:
it consumes the active reviewer plugin instead of its fake native API.
`/private/tmp/specfact460-selected-parallel.private.log` retains1failure/
1,751passes/four skips, not a PASS. Fixture-owned helper context now forces that
unit observation's intended fake API without disabling real measurement hooks;
its original records/root/threshold/origin-unavailable assertions remain.
The same40files then pass1,752tests/four skips in19.86s (20.21s wall) with actual
reviewer coverage and two workers, no restarts; log is
`/private/tmp/specfact460-selected-parallel-v2.private.log`. LocalPython3.14
timing is diagnostic only and cannot establish hosted equivalence.

Repository pytest policy explicitly declares two workers and zero restarts
using already-declared pytest-xdist3.8.0. Generic capsule policy, selectors,
coverage, native proof CLI and deadlines/repetitions stay unchanged. Worker
loss remains an error; `-n0` allows serial local debugging. Primary flag reference:
https://pytest-xdist.readthedocs.io/en/stable/distribution.html (accessed7October2026
Europe/Berlin). The specification and retained hosted deadline/active-plugin
failures precede the fixture/policy corrections; no failing review is waived.

Final two-worker full and SMART each pass5,224tests/75explicit skips/95subtests/
five existing warnings in158.47s/152.36s. Logs:
`/private/tmp/specfact460-parallel-policy-{full,smart}.log`. The same40-file
reviewer-plugin suite also passes1,752tests/four skips serially in46.06s
(46.83s wall); two workers pass in19.86s. These runs have different concurrent
local loads and are not a controlled hosted speed ratio. Actual local native
proofs with two workers pass9tests in5.63s. Final lint/typing and direct clean-code
for both affected test modules pass without findings; normal implementation
hooks pass, including staged requirements,28contracts, docs/YAML/imports and
checksum/version verification. Owner-approved local capsule review remains
DEFERRED to blocking Linux, never PASS. Module payloads are unchanged after
CI signing; all seven public-key signatures remain valid. Fresh exact-head
Linux and supported native acceptance remain required before merge.

An intermediate evidence append accidentally overwrote this file with TOML;
pre-push diff inspection caught it. This correction restores the entire previous
Git history verbatim and appends only this section, retaining all prior failures
and acceptance limits. No overwritten evidence is pushed or treated as authority.


## Minimal core smoke isolation — 7 October 2026 (Europe/Berlin)

At61a859ccthe three minimum-core cells fail before their smoke assertion with
pytest usage exit4: the deliberately lean pinned environment lacks xdist and
cannot parse repository-default worker flags. Completed Python3.12job
112556888034log is `/private/tmp/specfact460-61a859cc-mincore312.private.log`.
This is a test-harness plugin dependency error, not evidence of capsule/core
incompatibility. It is retained as a failure.

The specification precedes a plugins-disabled invocation with the old options;
it reproduces the same exit4 (`/private/tmp/specfact460-mincore-plugin-independence-red.log`).
The isolated single-test smoke now explicitly retains its original serial
`-ra -v --import-mode=importlib` reporting/import configuration, with the same
exact test selector and assertions. Immutable tag, commit/tree checks, existing
minimal dependency list and signed-capsule smoke remain. The repository reviewer
continues honoring its declared two-worker policy; no analyzer/test/deadline is
removed or loosened.

A plugins-disabled invocation with the corrected options passes12existing
workflow cases in0.02s; the combined customer/deferred-review/workflow suite
passes137tests in4.21s. Logs are
`/private/tmp/specfact460-mincore-plugin-independence-{green,focused}.log`.
Actionlint, strict OpenSpec and diff whitespace pass. This limited recipe fix
requires fresh three-ABI minimum-core CI; existing full/SMART source evidence
is unchanged. Current Linux reviewer jobs are still running at61a859cc.


## Hosted review root-cause projection — 7 October 2026 (Europe/Berlin)

Corrected diagnosis at61a859cc: the candidate required review completes and
reports Pylint timeout plus incomplete targeted-pytest evidence, followed by
bounded code findings. It is not an overall analysis_timeout. Its diagnostic
replay also completes before the280-second cutoff. The independent installed
reviewer still reports actual300-second analysis_timeout. Earlier commentary
mistakenly treated both as overall timeout; no pass or exception is inferred.

Spec precedes ten RED fixed-pytest-prefix assertions and two RED timeout-stage
assertions. The public projections now emit only finite anchored pytest codes
or fixed file-missing/permission-denied classes; raw details stay private.
The independent timeout reads at most65,536bytes from its private log tail,
projects only the last exact allowlisted analyzer marker, and retains exit124.
Unknown/spoofed codes, payloads, unknown markers and out-of-tail markers stay
private. No analyzer, signed reviewer, source selection or budget is changed.
RED logs: `/private/tmp/specfact460-pytest-diagnostic-red.log` and
`/private/tmp/specfact460-independent-progress-red.log`. Focused real inline
workflow execution, profile and orchestrator tests pass120cases in4.31s in
`/private/tmp/specfact460-pytest-diagnostic-green.log`. Actionlint and touched
Ruff checks pass. Native boundary jobs on macOS14,15and26 all pass including
100repetitions; all three native ABI archive build jobs pass. Nine delivered
archive execution jobs remain running. These diagnostics require fresh CI and
cannot replace the failed required review or final acceptance.


## Pylint parallel benchmark rejected — 7 October 2026 (Europe/Berlin)

Diagnostic native-configuration Pylint4.0.7 on the same68Python files completes
with one process in17.76s and two in12.36s. Both retain actual finding exit30
and848raw findings. All823non-R0801findings match exactly; six duplicate message
bodies differ in ordering among25R0801rows, already excluded by unchanged
reviewer filtering. These local runs do not prove sealed execution. Reports:
`/private/tmp/specfact460-pylint-native-workers{1,2}.private.json`.

The existing parallel runtime-root fixture passes10cases in3.18s, but explicitly
substitutes the native interpreter launcher. The delivered worker profile denies
process-fork and requires broker-managed process launches. Pylint's standard
ProcessPoolExecutor is not broker-managed, so declaring two workers cannot be
accepted from this fixture or benchmark. The proposed local config/spec/sidecar
changes were withdrawn before commit or push. No worker grant, timeout or checker
is changed. The real hosted Pylint timeout remains unresolved.

Initial projected-policy diagnostic attempts reject the executable init hook
or fail usage for `--errors-only=no`; they are not acceptance evidence. The
successful bench uses native repository configuration. Primary process-pool
reference: https://pylint.pycqa.org/en/stable/user_guide/usage/run.html (accessed
7October2026 Europe/Berlin). Diagnostic-only full suite passes5,245tests/75skips/
95subtests/five existing warnings in143.57s in
`/private/tmp/specfact460-diagnostic-final-full.log`. SMART was started while
the temporary worker config was present; it is supplementary only and cannot
establish final-tree acceptance.


## Introduced clean-review corrections — 7 October 2026 (Europe/Berlin)

At61a859ccsix bounded reported locations directly intersect added Python lines:
CC16in the large managed-uv frame test, four print-in-src warnings in CLI entry
points, and the generic naming regex in the empty-attribution test. The report
is capped at200rows; this is not a complete finding inventory. The source delta
and direct pinned analyzer reproduction precede correction and remain RED.

The Semgrep1.144.0 ARM64 wheel's previously hash-verified native binary reproduces
all five warnings. It requires the `osemgrep` argv0 frontend and `--experimental`;
an initial semgrep-core-mode invocation rejects that option and produces no
JSON. No successful scan is inferred from that invocation. Corrected frontend
reports are `/private/tmp/specfact460-clean-locations-{red,green}.private.json`;
the same files now have zero errors and findings with unchanged clean rules.

CLI outputs are machine wire records (JSON, artifact path or fixed public status),
so explicit serialized stdout writes retain exactly the same newline, value and
failure exit without introducing logging prefixes or exposing private exception
text. The empty-attribution test name now describes distribution RECORD scans.
The actual uv large-frame test separates compilation/setup from frame assertions;
all XML payload sizes,30large values, child return codes and native parser checks
remain. A fixed replacement inventory also simplifies the forbidden-request
fixture while retaining all original parameter IDs/expected failures. Initial
refactor retained theCC16large-frame function; the corrected split has zero
Radon findings for the whole UV fixture file. Actual native parser and selected
CLI/ownership tests pass146cases in2.19s in
`/private/tmp/specfact460-clean-locations-final-green.log`. An initial invocation
named a nonexistent release test file and collected zero; it is not GREEN.

Touched AST and AI-bloat return no findings; typing reports zero errors/warnings.
An initial direct AI-bloat call used a nonexistent function name; the corrected
`run_ai_bloat` invocation returns no findings. Ruff import order corrections
precede final verification. Two delivered archive CI cells at61a859ccpass on
macOS14/Python3.12and3.13, including real extensions/all analyzers/offline reuse.
The other seven supported cells and both required Linux reviews remain separate
acceptance. Final full/SMART and hooks follow below before push.


The complete pinned clean/bloat/bug scan of all68changed Python files exposes
five further added-line rows beyond the hosted200-row cap: three broker proof
prints, one cleanup-test name and the timeout test's directexec. All are retained
in `/private/tmp/specfact460-clean-full-semgrep.private.json`. Broker stdout
now retains exact records/newlines plus explicit flushes. The timeout fixture
executes the saved trusted wrapper as a named module using runpy, preserving
both300-second invocation and exit124 assertions. The PID test name is specific.
The corrected whole scan retains29legacy raw rows and has zero added-line
findings or parse errors; it does not replace the required analyzer composition.
`/private/tmp/specfact460-clean-full-semgrep-final.private.json` is private.

Follow-up projector/broker/boundary tests pass90cases with three explicit native
skips. An explicit physical broker/boundary invocation separately passes all9
cases in3.97s (`/private/tmp/specfact460-clean-proof-native-green.log`). The prior
full run144.65s overlaps adaptive source changes, so it is supplementary only.
Stable final full and SMART each pass5,245tests/75explicit skips/95subtests/five
existing warnings in159.24s/157.67s, with source/config unchanged throughout.
Logs: `/private/tmp/specfact460-clean-final-stable-{full,smart}.log`.
Five delivered archive CI cells at61a859ccnow pass: macOS14/cp312/cp313,
macOS15/cp313, and macOS26/cp312/cp313. Four cells remain running; no final matrix
or public installation pass is inferred. Final hooks and exact-head CI are still
required, and the Pylint timeout remains unresolved.


## Focused hosted fixture logic — 7 October 2026 (Europe/Berlin)

The broadened direct pass retains six AI-bloat loc-vs-complexity informational
rows in the deferred-review fixture module (not the previous five-file subset).
Spec precedes the direct RED inventory in
`/private/tmp/specfact460-fixture-bloat-red.log`. Fixed script payloads are now
named constants; isolated fixture modules use named templates with explicit
literal replacements. The exact formerly rendered module bytes match for
three success/failure/private-reason inputs. File materialization and Git branch
transitions are separate fixture responsibilities. Shared tracked-report setup
removes duplicated construction while preserving real inline projector execution.
Command trace assertions remain intact in a dedicated assertion helper.

An initial extraction accidentally attached the existing eight-case parameter
decorator to that helper:112tests pass but the scenario test errors because its
fixture is missing. This is retained in
`/private/tmp/specfact460-fixture-bloat-green.log`, not called GREEN. Restoring
the decorator to the scenario retains all120focused cases, passing in4.34s in
`/private/tmp/specfact460-fixture-bloat-final-green.log`. Typing has zero errors/
warnings. Touched AST and AI-bloat, and full fixture Radon, return zero findings.
The unchanged three pinned Semgrep rule packs scan all68changed Python files:
zero parse errors,29legacy raw rows and zero added-line matches in
`/private/tmp/specfact460-fixture-final-semgrep.private.json`. No rule, severity,
private-output guard, installed-reviewer boundary, test or budget is weakened.
Final stable full/SMART and hooks follow before push; supported native matrix
and exact-head hosted review remain independently required.


Final stable full and SMART each pass5,245tests/75explicit skips/95subtests/
five existing warnings in157.65s/158.25s, with tracked source/config stable:
`/private/tmp/specfact460-fixture-final-{full,smart}.log`. No test case was lost
in fixture extraction. Required Linux review remains deferred locally and must
complete on the pushed exact head; native source bytes and signed module payload
are unchanged by these fixture-only corrections. Normal hooks follow before push.


## Supported native candidate matrix GREEN — 7 October 2026, 02:38 Europe/Berlin

Workflow37548070020for PR head61a859ccade53adb33fc828fded777d933d8ad14
completesSUCCESS: toolchain, all three ABI archives and all nine delivered
execution cells. Source receipts bind the actual PR merge checkout
b37c9d31aca09474ad4d979f5c5a4a553e661430, whose parents are target dev
74d3fd4dd6f9b171f18857abcc8f659c80d686e9and that PR head. This is actual
candidate merge-tree execution, not protected-main publication authority or a
new-head pass. Three separate fixed-boundary supported jobs also pass.

Downloaded9small acceptance receipts in
`/private/tmp/specfact460-native61-receipts` have the exact3×3matrix, arm64,
the same source merge SHA and all eight checks true: all ten analyzers, cold
extraction, loader profile, native boundary, offline reuse, project coverage,
project extensions and project tests. Archive/manifest SHA pairs match across
all three OS cells for each ABI:

- cp311:c75ced8232b441cf20ae8aae437d00a59dd05f7408e178aa209f43bcf5c04492 /
  2f5ecf17409c141cd1262991417b11b9c43a9dc98be5c92d0655f56626d8419f
- cp312:b264b37119bfaa796d9f9fb4e145c6a67829348c7dd8102b7b2829e98d1be6e3 /
  d904de0e748583eac975cf6605cfae6470f65007b433aa50e3a5fb361d70a96b
- cp313:122a727c5585ca6d0c617e35c3ce67cd62ae80f292347dabeeeb7e9622273358 /
  64d8a2f6fe5141be656225814620711f9d655d07e371eb056853211d907e770a

Observed OS14.8.9/23J631,15.7.9/24G830and26.6.2/25G83. No production publisher
key or ordinary signed native installation is inferred. Protected environments,
signing/catalog promotion and independent ordinary installation remain pending.
The subsequent CI/fixture-only correction head still requires its own Linux
review, minimum-core and native checks. The baseline native success is retained
before pushing, avoiding cancellation of this completed evidence.


### 2026-10-07 02:55 Europe/Berlin — retain bounded test diagnostics (460-15-33)

Fresh fc97b0c9 orchestrator 37553154584 confirms all three minimum-core jobs PASS. Candidate cp312 job112573196699 still reports Pylint timeout and incomplete pytest without an allowlisted prefix; independent job112573196520 still reaches the unchanged300-second analysis deadline without a known progress marker. Private candidate replay yields48028 overlapping thread samples and completes in approximately241seconds; these counts are not analyzer elapsed times or acceptance. No speculative runtime or process-policy change is made.

Spec precedes four RED cases proving testing rows were omitted after219ordinary findings in both inline projectors, then six RED cases proving three existing collection/root error prefixes were withheld. Both inline projectors now order tool errors, testing, then ordinary rows within the same200-location cap and admit fixed TEST_OUTCOME_NOT_PASS / TEST_COVERAGE_POLICY_FAILED identifiers plus those three existing prefixes. Messages, test parameters and traces remain private. Required review outcomes, deadline and reviewer identity are unchanged. An initial combined test command named a nonexistent minimum-core test file and collected no tests; it is not GREEN evidence. Correct focused command and final checks follow below.

Fresh fc97 Docs Review112573148858 also exits4 before tests because requirements-docs-ci.txt has pytest but no xdist. Case460-15-34 spec precedes a failing workflow contract and a direct reproduction of its exact original five-file suite with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 (exit4). The docs-only command now sets the same original serial addopts as the minimum-core smoke; the original five files and PIPESTATUS remain. This changes neither review analyzer inventory nor repository parallel policy.

Local verification: original five-file lean docs suite PASS59tests in2.20s with plugin autoload disabled; combined diagnostic/profile/paired-core workflow suite PASS121tests in8.13s. Format, type-check (0errors/warnings), lint, Actionlint, strict OpenSpec, YAML/registry validation, import boundaries, all7strict public-key module signatures and existing contract suite (28PASS in2.89s) pass. Command overview,118command contract and documentation accountability checks pass. Direct AST/AI-bloat diagnostics return no findings for either modified test file; an initial bare Python import lacked the module path and produced no result, corrected explicit local import succeeds. These are bounded checks, not required hosted review acceptance. Full/SMART results and commit-hook record follow.

Final full/SMART: each PASS5256tests,75skips,95subtests,5existing warnings in145.56s/145.54s respectively. Both corrected docs/prompt validators PASS; pinned Semgrep1.144.0 clean/bloat/bug checks on both changed test files have zero findings/errors. Actual full nine-cell native matrix at prior61a859cc merge-tree and currentfc97 boundary jobs remain separate evidence, not exact-next-head acceptance. Required candidate/independent Linux reviews remain FAIL atfc97; no green report is asserted. Local ARM64 review deferral retains the previously explicit maintainer approval and must pass hosted exact-head review before merge.


### 2026-10-07 — ordinary bootstrap fixture identity (460-15-35)

At a1906e5a, hosted Docs Review37555113148 is SUCCESS, confirming the lean serial invocation fix in actual CI. Further source diagnosis shows target_bootstrap sets sys.executable to PROJECT/bin/python and _validate_python_arguments deliberately rejects -I/-E/-S. The hosted recipe fixture had aliased its fake ordinary CI venv Python to that caller. Spec precedes a meaningful regression substituting a rejecting managed caller: original fixture exits78 (RED). Creating a real fixture-owned venv, as the existing independent reviewer fixture already does, executes the unchanged isolated bootstrap and exact staged-tree assertions (GREEN122focused tests in8.73s). No runtime launcher, permissions, test selection or deadline is changed, and no host fallback is introduced into actual capsule execution. The signed module payload is unaffected. This fixture defect is confirmed independently; current public hosted pytest diagnosis is incomplete and this is not claimed as its sole cause.

Final fixture verification: full/SMART each PASS5257tests,75skips,95subtests,5existing warnings in145.82s/145.76s. Format, type/lint, strict OpenSpec, diff checks and direct AST/AI-bloat pass; pinned Semgrep1.144.0 clean/bloat/bug scans return zero findings/errors for the modified fixture. Module assets and manifests are unchanged. Existing hooks retain the approved local ARM64 DEFERRED review route; required exact-head Linux review remains outstanding.


## 2026-10-07 — 460-15-36: precise private-safe test diagnostics

Latest completed PR head `60c39ebe7689c1146ac22416744eab4c1b0570c5`: orchestrator run `37556736050` remains failed. Candidate cp312 job `112585116557` reports incomplete Pylint (30-second timeout) and pytest, with nonpassing observations in six public test files. Independent signed reviewer job `112585116410` retains its required 300-second timeout. Quality cp312 job `112592429767` has `SIGNATURE_RESULT=success` and `CAPSULE_RESULT=failure`, and stops at the prerequisite; this is not a demonstrated separate lint/test defect. Docs, all three minimum-core cells, requirements and strict signatures pass. These facts do not constitute review acceptance.

Specification preceded tests. The original projector fails six outcome/phase/xfail/function regressions (`/private/tmp/specfact460-outcomes-red.log`: 6 failed,8 passed), ten coverage-prefix assertions (`/private/tmp/specfact460-coverage-prefix-red.log`:10 failed,22 passed), and six exception-class assertions (`/private/tmp/specfact460-test-class-red.log`:6 failed,2 passed). Both inline projections now emit only finite outcome/phase/xfail, source-validated public test function, fixed exception classes and existing managed option-rejection codes from the matching controller phase record. No raw node ID, parameter, source excerpt, traceback or exception payload is printed. Message/detail/source size bounds and subject-relative non-symlink source checks apply; candidate Python is parsed, never imported. Existing200-location cap, reviewer identity, test inventory, exits and all deadlines remain. This change diagnoses existing failures; it does not claim to fix or waive them.

Final focused suite:150 passed. Initial new fixture introduced AI-bloat LOC/complexity and parameter-count warnings; compact fixture construction and a grouped case parameter remove both, preserving every assertion. Direct AST,AI-bloat and Radon now return no findings. Pinned Semgrep1.144.0 clean-code/bloat/bug scan has zero findings/errors.

The first broad local run failed because this invocation omitted the existing Rust compiler directory from PATH; it had5280 passes and75 skips. The failure was the explicit Rust prerequisite assertion, not a parser acceptance failure. Restoring `/private/tmp/specfact-rust-toolchain/bin` yields SMART5281 passes/75 skips/95 subtests (146.19s) and full5289 passes/75 skips/95 subtests (147.56s). Subsequent final-fixture verification is recorded below; these diagnostic runs are not hosted capsule PASS. Incorrect focused filename selection produced no tests and exit5 and is retained in its private log, never counted as proof. A transient inline indentation error produced84 failing regressions before correction; the entire affected file then passed109 cases.

Native run `37556735497` independently passes all nine OS/ABI cells. All nine tiny receipts were downloaded to `/private/tmp/specfact460-native60-receipts`; every declared check is true (all_ten_analyzers,cold_extraction,loader_profile,native_boundary,offline_reuse,project_coverage,project_extensions,project_tests). Actual receipt source is PR merge tree `de303d500be615e73fb4015817c7fe29f18b9379`, verified GitHub parents `74d3fd4dd6f9b171f18857abcc8f659c80d686e9` and the60c39ebe PR head. Each ABI's archive/manifest identities match across OS14.8.9/23J631,15.7.9/24G830 and26.6.2/25G83. This confirms native staged execution; secret-bearing signing/publishing stays skipped and public installed catalog acceptance remains pending. Apple membership is not required for the accepted ad-hoc stage.

Stable final fixture snapshot: SMART5289 passed/75 skipped/95 subtests,144.16s; full5289 passed/75 skipped/95 subtests,145.69s; five existing fork deprecation warnings in each. Final150focused cases pass11.91s. Formatting,typing (zero errors/warnings),lint,YAML/import boundaries, all7 strict module signatures (filesystem payload/version-bump against origin/dev),28 contracts,actionlint,strict OpenSpec validation and diff whitespace pass. Final pinned Semgrep clean/bloat/bugs has zero findings/errors and direct AST/AI-bloat/Radon have zero findings. No signed module payload changes. Local capsule review retains the previously approved explicit GitHub-Linux deferral, DEFERRED rather than PASS; the exact-head hosted review remains mandatory.

A test-context decision is pending: the unchanged Linux capsule inventory includes actual macOS/CoreFoundation proofs and ordinary-host bootstrap fixtures. The proposed separation would retain every assertion in required host/macOS jobs while selecting supported tests for capsule execution. No test-selection change, skip exception, deadline extension or acceptance waiver is implemented by this diagnostic patch. The rule in docs/agent-rules/15-intent-and-scope.md requires an explicit decision before that acceptance-contract change.


## 2026-10-07 — 460-15-37: immutable phase records and parameter parsing

Bounded review of immutable eef315067113f00f912406869906e7c8dccda25b found two diagnostic correctness defects: index/range controller observations are nested under head/base, and parameter text containing `::` was parsed as source function scope. Specification preceded twelve failing regressions (`/private/tmp/specfact460-review-corrections-red.log`). Both inline projectors now inspect bounded head/direct/base records, prefer a matching head record, and remove parameter sections before parsing the source function. Corrected focused suite passes156tests in10.99s. Existing privacy restrictions, 200-row cap, required exits and deadlines remain. Read-only review of both corrections returns no findings and twelve targeted passes.

Stable pre-runtime-fix verification: SMART5295passed/75skipped/95subtests in145.38s; full5295passed/75skipped/95subtests in146.11s, five existing fork deprecation warnings each. Format/type/lint and direct AST/AI-bloat/Radon pass. These observations precede the separate runtime and timeout-fixture fixes below and are not exact-head hosted acceptance.

## 2026-10-07 — 460-15-38/39: recursive archive limit and owned timeout fixture

Latest completed eef3150 candidate job112645749322 identifies two ordinary failed-call assertions: test_acquisition_archive_bounds_global_headers_even_without_file_members and test_main_timeout_fails_hook. It also reports ordinary-host bootstrap fixture launch errors, eighteen macOS/maintainer test skips, Pylint timeout30s and incomplete pytest; independent job112645749216 retains analysis_timeout300s. No test selection or acceptance changes are implemented while the requested test-context decision is pending.

Python3.12.13 isolated regression environment `/private/tmp/specfact460-cp312-regressions` reproduces the original archive assertion (1failed, `/private/tmp/specfact460-cp312-existing-archive-red.log`). Specification then precedes a portable regression using valid nonempty global PAX headers and observing physical member processing on Python3.14 as well as the original frombuf assertion. Both Python versions decode five physical headers against the unchanged four-header bound. A positive test requires exact-boundary archives to preserve two original payloads. The timeout fixture gains a report ownership guard before any filesystem write; its original real checkout fails that guard. RED on both Python3.12 and3.14:2failed,1passed (`/private/tmp/specfact460-archive-timeout-red{312,314}.log`).

The runtime now rejects extension metadata at the exhausted physical header boundary before tarfile can recursively decode another header. Regular members at the exact boundary remain accepted. The timeout fixture uses its own temporary repository and preserves the cwd, timeout300, exit124, diagnostic and selected-file assertions. No deadline, count/byte limit, authentication rule or test assertion is weakened. Verification and signed payload readback follow below.


Final stable source verification for460-15-37/38/39: full5296passed/75skipped/95subtests in162.66s; SMART5296passed/75skipped/95subtests in163.44s, five existing fork deprecation warnings each. Both complete earlier broad runs also pass, but precede the final equivalent bound-expression simplification and are not substituted for these stable runs. Focused Python3.14 suite passes226tests; supported Python3.12 full affected runtime/hook suites pass93tests (final4.26s). Bounded read-only review finds no defects and independently passes the three new regressions on Python3.14. All assertions, 30/300-second analysis limits and test selection remain unchanged.

Format,type (zero errors/warnings),lint,YAML/registry,import boundaries,28contracts,Actionlint,strict OpenSpec,staged planned-maturity requirements gate,docs/prompt command validation,command overview/contract and documentation accountability pass. Direct AST has zero findings; AI-bloat/Radon match the prior HEAD's eight/thirty-four existing findings with no additions or removals. An initial expanded conditional introduced an additional complexity level; the equivalent reserved-header limit removes that regression before final checks. Pinned Semgrep1.144.0 has zero errors and no changed-line findings (six pre-existing whole-file findings). These bounded checks are not all-analyzer hosted PASS.

Only the changed module manifest's checksum is refreshed locally with private signing variables removed; module0.51.1 remains newer than dev0.51.0. Filesystem payload/version-bump verification passes all seven manifests at the feature branch's checksum-only policy. CI-only auto-sign and strict authenticated payload readback remain required; no local signing key is accessed. Normal commit hooks retain the existing explicitly approved Darwin feature-worktree capsule review DEFERRED to required GitHub Linux, not PASS. Public exact-head results are still required. Old eef3150 customer cp311/cp313 jobs finishSUCCESS; their deferred review is intentionally cp312-only, and they do not erase its strict review failure.


### CI-only signature readback for460-15-38

Source correction17178d775c35dfa492ae840ab92f0d508bfd6e7d is pushed with normal hooks passing (contract hook28passed in3.90s; approved local review DEFERRED). Signature workflow37578820476 completesSUCCESS and appends CI signing commitdc895be5443cc750d839a318801da643578353d6. Verified diff adds only the signature to the changed module manifest; source bytes, checksum and version are unchanged. After fast-forward readback, public-key verification with --require-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev passes all seven module manifests (`/private/tmp/specfact460-archive-signed-readback.log`). Changed0.51.1 payload checksum issha256:eb7ee671a8ec8ecd1c6a416a76444ce307de0070ffdbbcab915fc742e0406952. No local private key is read or used, and no publication is performed.

This evidence-only follow-up preserves that exact signed runtime payload while normal current-head workflows exercise it. Full native matrix and both mandatory Linux reviews remain independent acceptance gates. The explicit test-context question remains unanswered; no selection or skip-policy change is implied by the ordinary archive/fixture fixes.


## 2026-10-07 — 460-15-40/41: reviewed observer identities and wheel license paths

The explicitly requested CodeRabbit CLI review of 2aea48da reports four minor findings: two stale workflow-status records, malformed observer node identities, and the Darwin derivative License-File path. Each is independently validated before editing. The single bounded read-only review agent confirms the schema and licensing defects; it does not demonstrate a false PASS or confinement bypass. Missing recognized-phase nodeid previously raises an untyped KeyError; non-string values are coerced for collected identities but remain malformed in records.

Specification precedes tests for missing/null/boolean/integer/list/object node identities, exact parameterized valid strings, metadata license resolution and matching provenance. RED: 8 failed / 47 passed in 0.66 s (`/private/tmp/specfact460-autofix-observer-license-red.log`). The worker now rejects malformed identities with WorkerContractError before projection; valid identities are unchanged without coercion. The metadata/provenance value is LICENSE.txt relative to dist-info/licenses; the physical authenticated license member stays unchanged. GREEN: 55 passed in 0.45 s. Bounded read-only review returns no introduced defects, with rebuilt wheel hashes still pending at that review snapshot.

Authenticated source wheel SHA-256 399a38a85d784105e5df5a05c04a581481bfdb80af7424779cf76fa843b4e66c and ARM64 release ZIP SHA-256 81d29e934fd863079a74af35eecaeaef8047e0e12414d33ca322b358d68383db reproduce two identical corrected specfact.2 wheels: SHA-256 81d7e08869fc34877ad9b1315de5bb5398792bc8858f44e45c38a974f310f7e7. Exact-hash tests are updated before all three ABI locks: the old locks fail the new assertions, then receive the authenticated new digest. Historical specfact.1 reproduces unchanged SHA-256 af669755eabd97268a4141983a391cb4a832116d5a2c3cf04a4c53c7650ce72c. Retained native/source bytes, exact reviewed omissions, license bytes, versions and other closure pins remain unchanged. Previous native matrix acceptance does not cover the corrected final bytes. No publication or dependency admission is implied.

PyPA primary specification, accessed 2026-10-07: [installed licenses subdirectory](https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-licenses-subdirectory) and [wheel licenses directory](https://packaging.python.org/en/latest/specifications/binary-distribution-format/#the-dist-info-licenses-directory). The workflow exists; live GitHub environment metadata still lists only github-pages. Delivery notes now distinguish implemented workflow from pending protected native release environment and authority.

Exact 2aea48da hosted candidate 3.12 still reports Pylint 30-second timeout, 19 ordinary-host fixture failures and 18 native/maintainer skips; independent review remains incomplete at 300 seconds. cp311/cp313 candidate jobs, signature/docs/requirements/CodeQL and all three macOS boundary jobs pass. Some final native matrix cells remain running at this observation. The test-context decision remains pending; this autofix changes no test selection, deadlines, confinement or acceptance requirements.


Final stable verification: focused 60 passed on Python 3.14 (1.15 s) and supported Python 3.12 (0.76 s); SMART 5304 passed / 75 skipped / 95 subtests in 159.65 s; full 5304 passed / 75 skipped / 95 subtests in 154.38 s, five existing fork deprecation warnings each. Skips remain explicit unexecuted native/maintainer acceptance, never PASS. Fresh isolated Python 3.12 installation of the corrected authenticated wheel passes pip check, exact metadata/license bytes and native Z3 solve. Separate licensing assertions remove a new test complexity regression without removing any assertion. Format, typing (zero errors/warnings), lint, YAML/import boundaries, 28 contracts, strict OpenSpec, planned-maturity staged requirements and documentation checks pass. Direct AST has zero findings; AI-bloat/Radon match three/thirteen baseline findings with no additions. Pinned Semgrep 1.144.0 reports zero errors, one pre-existing whole-file finding and no changed-line findings.

The single bounded read-only reviewer independently verifies both rebuilt wheel digests and metadata-to-authenticated-member resolution; final patch review has no findings. The final CodeRabbit CLI rerun is not executed: automatic approval review rejects private uncommitted diff egress pending destination-specific approval. This does not erase the preceding completed four-minor-finding CLI review or claim a fresh clean CodeRabbit review. GitHub's posted annotation separately consolidates the two workflow-status records and is resolved only after the verified fix is pushed.

Native run 37579074968 completes SUCCESS on 2026-10-07. Nine downloaded tiny receipts each require all eight declared checks true and bind source merge tree 01f408026f931eff6acb74bfc375cc7a36e20d36, whose verified parents are dev 74d3fd4dd6f9b171f18857abcc8f659c80d686e9 and PR head 2aea48da32d056d09cf9f5cde238e72d2e8af831. Each ABI's archive/manifest identity is unchanged across ARM64 macOS 14.8.9/23J631, 15.7.9/24G830 and 26.6.2/25G83. Signing/publishing is skipped. This completed matrix validates the preceding bytes, not this corrected wheel or observer runtime. Fresh final-byte acceptance remains required.

Only changed unpublished module 0.51.1's filesystem checksum is refreshed locally: sha256:d688d26265448c66e9bfeca02fe6ac5932c1d3670d642e7f0b32d78d1989d1e7. Private signing variables are removed; no local private key is accessed. Feature checksum/version verification passes all seven manifests with the public key; CI-only signature and strict readback remain required. Normal commit hooks retain the earlier explicitly approved local Darwin capsule review DEFERRED to mandatory GitHub Linux, never PASS. Quality job 112662781273 fails only at its capsule/signature prerequisite and skips downstream steps; no local quality defect is inferred from that inherited failure.


### CI-only signing readback for 460-15-40

Source fix 14c738cf43ff43b19a6cff9a8a9391eeb705bd8b passes normal commit hooks (28 contracts in 4.01 s; approved local capsule review DEFERRED). Signature workflow 37585303049 completes SUCCESS and appends f177e906f688a72915689d84634b885131d569d1. The verified diff adds only the manifest signature; source bytes, module version and checksum d688d26265448c66e9bfeca02fe6ac5932c1d3670d642e7f0b32d78d1989d1e7 remain unchanged. Fast-forward readback plus public-key --require-signature --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev verifies all seven manifests (`/private/tmp/specfact460-autofix-signed-readback.log`). No local private key or publication is used.

The consolidated CodeRabbit GitHub annotation PRRT_kwDORVEFbs6pygT8 is resolved after pushing the verified two-record documentation correction; summary comment6032841628 records the fixes and limits. The other two defects originate from the completed CLI review, with no corresponding GitHub thread invented. This substantive evidence follow-up preserves the exact verified source/signature bytes and starts normal current-head acceptance. Current Linux fixture-context/deadline failures remain open pending the recorded test-context decision; no stale or skipped review is described as green.


## Approved required proof contexts — 2026-10-07 (Europe/Berlin)

The maintainer's “yes approved” authorizes separating host/macOS proofs from
confined portable discovery while retaining every assertion. It also authorizes
the bounded CodeRabbit destination review: the committed 2aea48da→082e8b6d CLI
review completed with zero findings over15files. Current paginated GitHub thread
readback reports zero unresolved current annotations.

Specification and failing regressions preceded entrypoint changes: initial three
context checks FAIL3 in0.16s; native-job, package-marker ambiguity, exclusive ABI
preparation and host invocation regressions each separately FAIL before their
fixes. Separate host execution is required: pytest parent-directory plus explicit
child-file discovery omitted all19hostcases; --keep-duplicates repeated them.
Full and SMART now invoke the proof separately before the portable suite, returning the host failure without running the portable suite; after host success,
the portable exit status is returned. No pytest discovery or installed-controller policy is
weakened. Empty namespace package markers are removed after the installed0.51.0
selection probe reproduces their ambiguity. Each native ABI preparation has its
own fresh cwd, retaining exclusive Node output ownership and existing input hashes.

The four obsolete baseline modules are byte-identical to origin/dev; canonical
host wrappers ignore only those versions. All81 original top-level test/helper
ASTs are retained, normalizing only nine cross-module public helper identifiers.
One copied test selector is renamed from copies_data to copies_runtime_bytes to
satisfy the introduced whole-file naming check; its entire body is unchanged.
The read-only reviewer independently confirms assertion preservation and that all
nine newly added Python files select four portable files under installed0.51.0,
with no proof or obsolete baseline fixture selected. Proof-only selection remains
an error. Required macOS jobs explicitly execute parser/broker proofs on all three
OS labels and all three minimal CPython ABI inputs; hosted execution remains due.

Focused final context/portable/host tests PASS154 in13.03s before the selector-only
rename. Full host entrypoint executes19hostcases separately, then5275portable cases
PASS /71declared skips /95subtests in139.57s, with5existing fork warnings. SMART
executes the same19hostcases and5275portable cases in157.19s. Native parser PASS14
in1.41s with real SDK/Rust; all three real broker CLI proofs exit0. Format, typing
(0errors/0warnings), lint, YAML, imports,28contracts, strict OpenSpec and actionlint
PASS. AST, AI-bloat and Radon return0findings for all introduced context modules.
Pinned Semgrep1.144.0 reports0errors; two remaining tools print findings are on
unchanged baseline lines. Strict public-key filesystem/version signatures PASS7;
this change alters no signed module payload.

Fresh historical final-wheel acceptance is now verified from native run
37585571068: all9cells and all8checks percellPASS. Receipts bind merge65cafbd5e0a2a008b3aba0835a8fd38cb0f83e2d, whose parents are dev74d3fd4dd6f9b171f18857abcc8f659c80d686e9 and PR082e8b6dae8d0b333315d8927d4770a92fda1853.
Per-ABI archive/manifest hashes are identical across macOS14/15/26. This proves the
corrected wheel/runtime bytes in staging; it is neither protected publication nor
ordinary signed customer installation. Fresh context-head CI is still required.

The existing authenticated0.51.0 controller additionally reproduces ambiguous
selection for the changed run/commands.py with two baseline test_commands.py
stems. Candidate explicit-match correction is absent from that immutable published
reviewer. Previously observed Pylint30s and independent300s deadlines remain
required. No published reviewer modification, skip-to-PASS conversion, deadline
increase, automatic merge/publication/issue closure/OpenSpec archive is performed.


### Exact-head context diagnosis and bounded native follow-up — 2026-10-07

Head14aff915: required native parser/broker steps pass on macOS14/15/26; the
new minimal CPython proof in tools job112978610168 fails with EOFError during
WAIT. All original assertions remain required. The exact SHA-256-pinned
CPython3.11.16 input independently passes6/6cases locally on the physical ARM64
host; that is not macOS14 evidence. No new sysctl/profile grant is inferred.
A fixed-field failure projection is specified and tested: initial helper import
FAIL before implementation; malformed scalar identities FAIL before type guards.
Raw8KiBfixture-log tails/paths/authority stay private; public output contains only
declared ABI, fixed case/phase and existing four boolean wait-state fields. The
original error is retained privately and the required proof still fails. The
hosted cause remains unknown pending fresh diagnosis. The20focused portable
context/Python-source tests pass before the annotation-only type correction.

CodeRabbit completes context-only14aff915 review with one minor evidence wording
finding: host failure prevents portable execution; after host success the portable
status is returned. Documentation is corrected, with entrypoints unchanged.
The maintainer separately approves preparing a small authenticated reviewer-update
PR covering explicit test selection and a tested Pylint optimization. This does
not authorize automatic merge/publication or modification of installed reviewers.
Existing #498 stays separate from the reviewer bootstrap worktree on updated dev.


## Bounded native WAIT result diagnostic — 7 October 2026 (Europe/Berlin)

Head 8eeae6d4's hosted macOS14 minimal CPython3.11 clean case fails at
request-wait after output_closed, wait_accepted, wait_pending and worker_reaped
are all true. Exact authenticated PBS3.11 bytes pass locally6/6; the cause remains
unknown. Encoding and serialized-response size are distinct rejection paths,
so no permission, output/frame, deadline or cleanup gate is changed.

Specification precedes a meaningful RED for missing last_worker_result, then
finite per-worker entered/queued/output_encoding/response_size/queue_capacity/
session_deadline observations. Status projection permits only worker_exited,
worker_signalled and entry_marker_present booleans. It binds to this client's
recorded failing WAIT and rejects foreign identities, malformed/unknown stages
and non-boolean fields. No raw bytes, exception payload, PID, handle, authority or
path becomes public; every rejection still terminates at the original gate.

Focused25tests pass. The actual native broker compiles and all6minimal CPython
cases pass using the exact authenticated3.11 input. A bounded read-only reviewer
finds no defect; tests do not yet exercise every C rejection path. Full host entry
passes19cases followed by5278portable cases/71declared skips/95subtests in156.85s
before equivalent helper/test extraction; final focused coverage verifies those
extractions. AST/AI-bloat/Radon return0on changed small helpers. Pinned Semgrep
has0errors and only the pre-existing fixture print finding on unchanged code.
Typing/lint pass with0errors/warnings and10.00/10. Fresh hosted diagnostic and
exact-head capsule review remain required; this is not acceptance or publication.


The fffa6856 hosted tools job113006304974 (run37683804287) now proves the
macOS14 clean3.11 failure is output_encoding, with worker_exited=true,
worker_signalled=false and entry_marker_present=false. This identifies broker
rejection of pre-entry startup output, not the underlying startup error. Retain
that distinction; do not infer a new sandbox permission or weaken encoding.

A subsequent spec/RED→GREEN adds five fixed startup classes only: profile
initialization, Python initialization, Python path configuration, loader and
unclassified, based on literal fixture error prefixes.26focused cases and the
actual6native cases pass; invalid/future values cannot disclose raw payloads.
Typing/lint (0errors/warnings,10.00/10) and direct AST/AI-bloat/Radon pass. The
existing single read-only reviewer finds no defect and confirms unchanged gates.
Final full and SMART each pass19required host cases followed by5280portable
cases,71declared skips,95subtests and5existing warnings (142.44s /143.06s). Fresh hosted failure
classification remains required; these labels are clues, not startup acceptance.


## Python profile compatibility correction — 2026-10-07 (Europe/Berlin)

Exact0381b7fac571784476d0ffff6d7dd033d38264c1 tools job113013929699
(run37686023721) fails before CPython entry. Fixed public projection reports
output_class=profile_initialization,stage=output_encoding,worker_exited=true,
worker_signalled=false,entry_marker_present=false. Raw output remains private.
This proves sandbox initialization failed, not its underlying compiler cause.

Source inspection identifies a definite compatibility inconsistency: both Python
fixture profiles name mach-task-exception-port-set unconditionally, while the
already-measured broker retains all four unconditional exception-port RPC denials
and guards the newer operation with defined?. Reuse that exact existing policy
in both Python builders. This adds no allow, changes no budgets and retains the
newer-operation denial wherever defined; protected native execution remains required.

Specification preceded two focused regressions. Both fail against their missing
canonical broker policy(0.81s), then pass after the shared policy correction; the
combined candidate/context suite passes25cases(0.70s). The private exact minimal
PBS3.11 fixture subsequently passes all6cases, with the unchanged cleanup and
denial assertions. The bounded agent verifies canonical denial-policy equality
and unchanged grants/budgets, with no findings. Local/newer-kernel proof does
not establish macOS14 remediation; fresh required hosted execution follows.
Private evidence logs: /private/tmp/specfact460-exception-profile-{red2,green}.log
and /private/tmp/specfact460-exception-profile-native.private.log.

Final correction verification: format, typing0errors/0warnings,lint10.00/10,
manifests/imports,strictOpenSpec,stagedplannedrequirements,28contracts and all
seven strict public-key signatures pass. AST/AI-bloat return0findings; Radon
and pinnedSemgrep return0changed-line findings (unchanged existing observations
are retained, not suppressed). Full:19hostcases then5282portable cases/71declared
skips/95subtests/5existingwarnings(149.21s). SMART:same counts(141.63s).
The signed module payload/checksum is unchanged. Normal hooks reuse only the
approved local Darwin capsule-review deferral; exact-head hosted Linux remains
mandatory. Hosted macOS14 profile compilation/remediation remains pending.

## 9 October 2026: #498 upstream integration and same-stem mapping

User authorized resolving #498 conflicts, readying the PR and fixing review findings before release. Current dev bb57584c includes the signed/published 0.51.2 patch; resumed native payload version is 0.51.3. The merge preserves native diagnostics/proofs alongside dev bootstrap and immutable reporting fixes.

Specification was extended before tests. Four parameterized changed-scope cases (two changed production files with one shared stem, two discovered matching tests, one explicitly selected test; both orders and either selected test) genuinely failed because no ambiguity error was raised. A distinct-stem control passed. RED: `/private/tmp/specfact498-same-stem-red.log` (4 failed, 1 passed).

The minimal fix counts distinct changed source paths per stem, retains the established single-source explicit mapping, and rejects partial explicit coverage of a multi-source matching-test group. Explicitly selecting all matching tests or full native discovery resolves it without guessing directory correspondence. The imported dev fixture uses the current `selectors` field and bounded native invalid-request diagnostic; response initialization still waits for successful observations. Affected worker, bounded diagnostic and host proof checks: 324 passed, `/private/tmp/specfact498-merged-targeted-green.log`. Full/SMART and normal hook results are recorded after completion below.

Release configuration was checked through GitHub metadata, without reading secret values. Both native environments now require djm81, prevent self-review, restrict protected branches and disable admin bypass. The dedicated signing environment currently has no secret names listed. Owner provisioning remains required; a signing-capable workflow cannot manufacture or retrieve an existing GitHub secret value. A different authorized actor must initiate deployment for djm81 to approve under the existing independent-approval rule. No signing/publication was dispatched and no publisher private key was used locally.

Full integration RED additionally exposed 12 stale upstream assumptions (native invalid-request handling and selector schema, subprocess xdist controls, published reviewer pin, immutable host proof invocation). `/private/tmp/specfact498-full-test.log` records 12 failed, 5475 passed. Corrections preserve complete request/ownership assertions, compare JSON object fields semantically, retain original serial reporting/import options, and use actually published signed 0.51.2 in the independent reviewer. No customer analysis inputs, deadlines, contracts or no-write controls were relaxed. The intermediate full run loaded the old key-order assertion before its correction and still failed that assertion; it is not passing evidence. The corrected setup module passed all 11 cases in `/private/tmp/specfact498-setup-final-green.log`.

The authenticated CodeRabbit CLI actually completed the resolved integration review with zero findings over 49 text files (two binary registry archives excluded). Subsequent test-context/published-pin corrections require current-head GitHub producer completion; this earlier CLI result is not an exact final-head clean assertion.

Final full gate: 27 mandatory host proofs and 5487 portable cases passed (71 declared skips, 95 subtests, five existing fork warnings; portable duration 154.26 seconds), `/private/tmp/specfact498-full-verified.log`. Final SMART gate independently passed the same mandatory host proofs and 5487 portable cases (137.35 seconds), `/private/tmp/specfact498-smart-verified.log`. Final typing reports zero errors/warnings; Ruff passes, Pylint 10.00/10, manifest and bundle boundary checks pass, seven module checksums/version policy pass with the new native payload awaiting normal CI signature, and selected strict OpenSpec validation passes. Contract gate: 28 passed. No private publisher key was accessed. Current-head hosted acceptance/review and installed release proof remain outstanding.

Normal merge commit hooks all passed on implementation commit 9fde4785c15e42763430cf8bf0c95d9a51839a08, including 28 contract cases, with only the previously approved local capsule review DEFERRED to exact-head hosted Linux. Existing CI added signature-only child 3d936d5eebcb9e9481d78e0106b7855ca14c0597: exactly one manifest signature insertion, unchanged module payload/checksum/version 0.51.3. After a clean fast-forward, all seven strict signatures, payload checksums and upstream version checks pass against the existing public root. No repeated runtime tests are required for that signature-only child or this reporting checkpoint.

Credential configuration clarification: GitHub lists existing repository-scoped `SPECFACT_MODULE_PRIVATE_SIGN_KEY`, its passphrase and public-key metadata; the native signing environment still lists no secrets. Public-key comparison confirms the native signer and verified module publisher share the same trust root. A new key is not required: the owner can provision the existing securely held key/passphrase under the dedicated native environment secret names. GitHub cannot return existing secret values for an agent to copy, and no private key is read or used locally. GHCR upload uses the workflow's built-in GITHUB_TOKEN with packages:write; no new registry credential is required.

## 9 October 2026: customer release identity P1 and owner secret provisioning

New current review thread PRRT_kwDORVEFbs6qv5R_ correctly identifies release drift: native installed customer acceptance checked out mutable main and omitted RELEASE_TAG. The specification was extended first. A new workflow regression genuinely failed on `ref: main`; a real Git repository test independently proved the existing identity validator rejects newer-main/tag mismatch and accepts the released commit or manual untagged commit. RED: `/private/tmp/specfact498-release-identity-red.log` (1 failed, 1 passed).

The minimal workflow correction checks out the immutable event SHA, fetches tags for identity verification, and forwards RELEASE_TAG to both existing installation selection/verification calls. No registry override, signing key, private output or customer assertion is added. The module payload/version/checksum/signature remain unchanged at 0.51.3. The new workflow path and regression coverage require fresh hosted checks and review.

The owner supplied both `SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY` and `SPECFACT_NATIVE_CAPSULE_PRIVATE_SIGN_KEY_PASSPHRASE` to the signing environment (metadata updated 10:58:29 / 10:58:52 UTC). Both environment policies pass the tracked validator again. Only names and metadata were read; no secret value was retrieved. Value/decryption/public-root compatibility must be validated by the protected main signer after exact nine-cell acceptance and independent approval, not by a local probe or feature-branch dispatch.

P1 GREEN: all 115 release/customer cases pass, `/private/tmp/specfact498-release-identity-green-final.log`. Final Full and SMART each pass 27 mandatory host proofs plus 5489 portable cases, 71 declared skips and 95 subtests (161.46 / 159.35 seconds), `/private/tmp/specfact498-release-p1-full.log` and `/private/tmp/specfact498-release-p1-smart.log`. Final typing/Ruff/Pylint, manifest and strict OpenSpec gates pass. The authenticated CLI review actually completed with zero findings across all six staged text files; a separate bounded read-only audit found no remaining release-binding defect. These are code/review results, not installed production acceptance.

Hosted independent job 113787136598 on reporting head 99e91783 emitted the trusted `analysis_timeout` classification and exited 124. Its finite follow-up projector had no report and emitted missing_report/unclassified; that does not override the verified timeout. This is the explicitly owner-approved timeout exception and remains INCOMPLETE, never PASS. Public fixed diagnostics only were inspected; no private report or key was retrieved. New-head hosted review/customer/native checks remain required after the workflow correction.


## PR #498 source identity and fatal attribution follow-up — 9 October 2026

Both current annotations were independently validated within the approved native delivery scope. Spec scenarios were added before tests and implementation. Root remained sole writer with one bounded read-only audit agent.

- Pylint RED: six later-file absolute/relative fatal cases failed because the first selected path replaced the actual path; six existing selected/global fallback cases passed. `/private/tmp/specfact498-fatal-red.log`. The fix retains admitted source paths/lines and preserves unselected fatal fallback, tool-error and nonfatal selection semantics.
- Native installation RED: seven source identity/workflow regressions failed and two existing release identity controls passed. Real fixture archives/indexes remain internally valid while source version, integrity/resources or manifest availability diverge. `/private/tmp/specfact498-install-red.log`. Native selection and verification now explicitly require complete source/archive manifest equality; the Linux registry-only published candidate default is unchanged.
- Focused GREEN: 152 tests, including matching signed-install receipt controls, version-output binding and original customer controls. `/private/tmp/specfact498-new-findings-green.log`. An actual checkout0.51.3 versus registry0.51.2 invocation rejects before installation/version output as expected (`/private/tmp/specfact498-unpublished-rejection.log`), demonstrating publication is still required rather than claiming installed acceptance.
- Format, typing (zero errors/warnings), Ruff/Pylint10.00/10, seven manifest checks, bundle imports and strict OpenSpec pass. The bounded read-only audit found no defects.
- Exact e3e hosted independent job113792360434 emits `analysis_timeout` and exit124. This is independently verified and remains INCOMPLETE under the existing user-approved timeout exception, never PASS. No private report was retrieved.
- Native environment metadata confirms both owner-provisioned key/passphrase secret names and independent djm81 protection; values remain exclusively for approved protected-main CI. GHCR uses the existing built-in token.

Full and SMART each pass 27 required host proofs plus 5505 portable cases, with the same 71 declared skips, 95 subtests and five existing warnings (139.73/145.02 seconds portable respectively). Logs: `/private/tmp/specfact498-new-full.log` and `/private/tmp/specfact498-new-smart.log`. The authenticated bounded CLI review completed with zero findings across 11 files; the read-only audit also found no defects. Initial automatic approval rejected the upload under a private-repository assumption; fresh GitHub PUBLIC/isPrivate=false metadata and the no-credential-material diff check supported approval of the same direct command before remote analysis began. No completed/started review was retried. Later evidence append only records those results. Refreshed payload checksum is `sha256:3c7d9a6e7f5ef5c76987eb569f7722434747cc535866372fb46cfc5953255f21`; stale signature was removed without accessing a private key. All seven checksum/upstream-version gates pass, and normal commit hooks are enforced with only the already approved local Darwin review deferral; the changed module requires fresh normal CI signing before strict signature acceptance. Current-head GitHub checks remain required. Version0.51.3 remains above freshly verified published dev0.51.2 and is unpublished; no additional patch bump or manual registry artifact is required for this bounded correction.


## PR #498 bounded failure projection — 9 October 2026

CodeRabbit thread `PRRT_kwDORVEFbs6qwc6m` independently reproduces unbounded/unhandled public report parsing and failure exit substitution. Spec preceded tests/code: fourteen genuine RED cases cover both public projectors with malformed/non-object/valid oversized/deep/unreadable private reports plus shell crash propagation at exit17/124. A read-only audit identified the secondary candidate diagnostic invocation in the same failed-review branch; two further RED cases demonstrate its process exit3 replacing review17/124. Logs: `/private/tmp/specfact498-projector-red.log`, `/private/tmp/specfact498-secondary-projector-red.log`.

Both public readers now use the existing32MiB+1 private diagnostic bound, require JSON objects and emit fixed `review_report_unreadable` INCOMPLETE only on parse/read/shape/size failure. All three diagnostic invocations in failed-review branches are nonfatal so the original required nonzero reviewer exit remains authoritative. Existing private parsing, fixed public locations/function identity, 200-location cap, deadlines, analyzer invocation, retained test assertions and timeout/incomplete semantics remain unchanged. Heredoc extractors accept guarded syntax; source assertions are preserved.

Focused GREEN235 includes every current public/private projector assertion and the27 mandatory ordinary-host proofs. `/private/tmp/specfact498-projector-green-final.log`. The first broader run detected one existing inline heredoc extractor tied to unguarded syntax; it is fixed via the existing shared helper and no diagnostic assertion was removed. An accidental targeted invocation of the excluded historical `tests/unit/test_capsule_deferred_review_ci.py` produced six stale-baseline/fixture failures; the required current `tests/host/proof_capsule_deferred_review_ci.py` is the maintained proof and all27 assertions pass. The initial in-flight full run retained the already collected old extractor and therefore reports one failure/5518passes; final full/SMART are being rerun after the actual fixture correction, not waived.

Normal CI signature-only child `7572e239` was inspected and fast-forwarded: it inserts only the signature for unchanged0.51.3 payload checksum `sha256:3c7d9a6e7f5ef5c76987eb569f7722434747cc535866372fb46cfc5953255f21`. All seven strict public-key signatures/checksums/version gates pass. This workflow/test/spec-only follow-up changes no module bytes/version/signature and requires no additional bump or local private key. Native protected-main secret correctness, actual registry publication and installed customer acceptance remain separate pending delivery gates.


The first new six-file CodeRabbit review completed with one Minor privacy finding, not a clean review: a later projector loop crash could print stderr despite the exit guard. Independent validation confirmed this against the existing private-log requirement. Six genuine RED assertions then show public tracebacks or missing fixed projection-failure diagnostics (`/private/tmp/specfact498-projector-privacy-red.log`). All three diagnostic commands now redirect stderr to owner-controlled private logs outside upload-artifact paths and emit only fixed INCOMPLETE `review_projection_failed`; a final nonfatal guard also preserves the original review exit if diagnostic output itself fails. The235-case focused scope passes with empty public stderr, actual private crash evidence and original exit17/124 retained (`/private/tmp/specfact498-projector-private-green.log`). The preceding final full run passed27host/5521portable, but the latest privacy correction receives a fresh final full/SMART check. Neither a started/completed review nor an unchanged failed gate is retried without changed source/evidence.


Final private-diagnostic verification: Full and SMART each pass27requiredhostproofs and5521portable cases (71declaredskips,95subtests,5existingwarnings), with portable durations154.99/155.21seconds. Logs: `/private/tmp/specfact498-projector-private-full.log`, `/private/tmp/specfact498-projector-private-smart.log`. Final focused235 passes. Format/typing/Ruff/Pylint10.00/10, YAML/manifests, bundle imports and strict OpenSpec pass. The final six-file authenticated CLI review completed with zero findings after the privacy correction; the bounded read-only audit also found no remaining defects. This evidence-only append records completed results. Normal commit hooks remain mandatory with only the existing approved local Darwin review deferral, and exact-head hosted review/checks remain pending. Signed0.51.3 module bytes/checksum and CI7572e239signature are unchanged by the workflow-only correction; all7strict signatures previously verified for these exact bytes remain valid.


## PR #498 native workflow input coverage — 9 October 2026

Codex P2 thread `PRRT_kwDORVEFbs6qxFxr` is independently valid: the PR filter omitted real Node/Z3/runtime/parity helpers, acceptance helpers, broker proof/corpus fixtures and pytest/bootstrap inputs consumed by the native jobs. The scenario was specified first, then29 source-backed trigger/negative-control cases produced14 genuine RED failures and15 passes (`/private/tmp/specfact498-path-filter-red.log`). Narrow native/macos script patterns and explicit shared inputs now schedule the existing secret-free build and nine-cell execution jobs; unrelated documentation, module packages and unit tests remain filtered. No matrix, deadline, signing/publication approval or signed module byte changes. Focused native release GREEN:91 cases (`/private/tmp/specfact498-path-green.log`).

Exact prior head3c1d36e1 candidate3.12 job113806025990 and independent job113806025834 both emit fixed public `analysis_timeout` and exit124 (`/private/tmp/specfact498-job113806025990.log`, `/private/tmp/specfact498-job113806025834.log`). These newly inspected failures are INCOMPLETE under the approved timeout exception, never PASS. No private reports or signing secrets were accessed.

The first new five-file CLI review completed with zero findings. The separate read-only audit identified inaccurate single-star slash semantics in the test helper. Six direct controls produced1 genuine RED/34passes before correcting the literal/star matcher to full-path regex with segment stars and recursive stars; this follows [GitHub filter semantics](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#filter-pattern-cheat-sheet), accessed9October2026. `/private/tmp/specfact498-path-glob-red.log`. Earlier full5550passes reflects the pre-correction tests and is historical; final focused and whole-suite evidence follow the actual matcher correction.

Final native input correction evidence: focused97pass (`/private/tmp/specfact498-path-green-final.log`); Full/SMART each27requiredhostproofs plus5556portable cases with71declaredskips,95subtests and5existingwarnings (210.22/177.69seconds). Logs: `/private/tmp/specfact498-path-full-final.log`, `/private/tmp/specfact498-path-smart-final.log`. Final five-file authenticated CLI review completed with zero findings after the actual slash matcher correction; final read-only audit found no defects. Format, zero-error/warning typing, Ruff/Pylint10.00/10, YAML/manifests, bundle imports and strict OpenSpec pass. All7strict public-key signatures/checksums/upstream-version gates pass (`/private/tmp/specfact498-path-signatures-final.log`); signed0.51.3 module bytes remain unchanged. The three prior-head quality jobs113815349590/668/683 fail at customer-matrix prerequisite validation before any quality tools/tests, downstream of the independently verified timeout jobs. Normal hooks remain required with only the already approved Darwin reviewer deferral. New-head hosted checks and actual installed acceptance remain outstanding.


## PR #498 uv generated-module inference — 9 October 2026

Codex P2 `PRRT_kwDORVEFbs6qx3t6` independently identifies a missing overlay destination in uv preparation. The existing byte-bound inference helper rejects generated project files without an overlay; dropping implicit roots can select installed copies instead of reviewed source. Spec first extended the existing generated-wheel scenario to actual uv-installed files. Four genuine REDs plus20passing controls cover locked/unlocked preparation, generated.py/.pyi, byte mismatch, ambiguous matches and explicit-root preservation (`/private/tmp/specfact498-uv-red-controls.log`).

The minimal correction passes the existing private source-overlay destination, matching pip/Hatch/Poetry. It retains exact source byte binding, unrelated dependency exclusion, explicit-root short-circuiting, unchanged customer checkout and existing lock handling. No new importer, deadline change or staging bypass. Affected preparation/source/worker GREEN:129cases (`/private/tmp/specfact498-uv-green.log`). Public hierarchy metadata remains complete; issue460 is OPEN/Todo and cache refresh is unchanged. Source/spec/full/SMART/review and normal-hook final evidence follow.

Exact prior1ce3c039 customer candidate3.12 job113819547817 and independent job113819547758 both emit `analysis_timeout` with exit124. Public finite diagnostics only inspected; these are approved INCOMPLETE exceptions, never PASS (`/private/tmp/specfact498-job113819547817.log`, `/private/tmp/specfact498-job113819547758.log`). Signed module bytes changed by the source correction. Unpublished0.51.3 remains above dev published0.51.2; checksum refreshed via normal checksum-only tooling with all private key/passphrase environment variables removed. Stale signature removed; normal CI signing is required before strict signature acceptance. Registry artifacts are left to normal publication.

The first new six-file CLI review completed with one Major finding, not a clean review: installed files sharing a namespace were selected by package prefix. The independent read-only audit confirmed the same defect. Twenty genuine RED cases cover regular/shared namespace dependencies with resource-relative imports, missing/malformed/ambiguous records and altered hashes (`/private/tmp/specfact498-uv-ownership-red.log`). Four further REDs prove a partial RECORD omitting a generated module must not leave inferred roots without a reachable generated file (`/private/tmp/specfact498-uv-unrecorded-red.log`).

Native uv overlay selection now reuses the established installation RECORD row parser and hash verifier, admits unique owners associated with exact byte-matched source/root sets, and excludes unrelated distributions even when package names overlap. Parsing retains the existing bounded tree, limits each RECORD to4MiB and total rows to100000. `.pyi` is admitted only through an explicit parser option; the portable coverage default remains `.py`. Missing matched ownership or unrecorded project-namespace files reject inference before writes; malformed/ambiguous/changed ownership produces the fixed `project_native_source_ownership_invalid` error. Original source, resources, lock and explicit-root controls remain unchanged. Final focused210pass, including portable coverage defaults (`/private/tmp/specfact498-uv-green-final.log`). Earlier5580 Full/SMART and the one-Major review are historical before this actual correction; fresh final gates/review are required. Final refreshed checksum is `sha256:0e7bb7b55de786b53cc8072e45e66628c682429c80e0a47fe7f2398067c94b85`, with no stale signature or private key access; normal CI signing pending.

The second seven-file CLI review completed with two Major findings, both independently valid and fixed after8genuine REDs (`/private/tmp/specfact498-uv-package-script-red.log`): legitimate outside-site Python launcher RECORD entries caused inference errors, and other packages owned by the same distribution were not package-bound. [PyPA installed RECORD specification](https://packaging.python.org/en/latest/specifications/recording-installed-packages/), accessed9October2026, explicitly permits relative/absolute installed paths outside site-packages. Native ownership now excludes those entries lexically without reading outside files, retains strict in-site parsing/hash checks, and requires both distribution ownership and a matched package prefix. Prefix lookups retain the100000bound. Final focused218pass and final lint/type-check pass (`/private/tmp/specfact498-uv-green-final2.log`, `/private/tmp/specfact498-uv-lint-final2.log`). Prior210focused/5604Full/SMART and the two-Major review are historical before these actual corrections; fresh final gates/review follow.

The third seven-file CLI review completed with zero findings, then a separate bounded source audit found one additional ancestor-initializer case. Two genuine REDs/two controls demonstrate that a same-owner generated parent initializer can select the installed package over edited staged namespace source (`/private/tmp/specfact498-uv-ancestor-red.log`). Exact same-owner required ancestor .py/.pyi initializer bindings now accompany matched package prefixes; the binding index remains bounded at100000. A real isolated Python import observes the edited staged module and its source path; the customer checkout stays unchanged. Final focused222pass (`/private/tmp/specfact498-uv-green-final3.log`), final lint10.00/10 and final read-only audit have no findings. Prior5612Full/SMART and the earlier zero-finding review are historical before this actual last correction; fresh final gates/review follow.


Final uv correction verification: Full and SMART each pass 27 required host proofs and 5616 portable cases (71 declared skips, 95 subtests, five existing warnings), with portable durations 151.79/145.32 seconds. Logs: `/private/tmp/specfact498-uv-full-final3.log`, `/private/tmp/specfact498-uv-smart-final3.log`. Focused 222 passes; final seven-file authenticated CLI review completed with zero findings after the actual ancestor-initializer correction, and the final independent read-only audit found no defects. Format, zero-error/warning typing, Ruff/Pylint 10.00/10, YAML/manifests, bundle imports and strict OpenSpec pass. This evidence-only append records completed results. Final runtime checksum is `sha256:80ee9803c285d4cfc15a0710d4a1408d7671a2271193aee9b174e4eeb2b2d7ac`; all seven checksum/upstream-version gates pass for unpublished 0.51.3 above published dev 0.51.2. Stale signature is removed; normal CI signing and fresh strict verification remain required for these changed bytes. No private signing key/passphrase or registry artifact was accessed. Normal hooks remain mandatory with only the approved local Darwin reviewer deferral; current-head hosted checks and actual installed acceptance remain separate delivery gates.


## PR #498 failure-projector import isolation — 9 October 2026

Codex P1 thread `PRRT_kwDORVEFbs6q1uKd` is independently valid: after entering the staged candidate tree, the candidate failure projector launched stdin Python without isolation. The spec was extended first; workflow-derived launch tests then demonstrate eight genuine REDs and eight passing independent-review controls for checkout/PYTHONPATH ast.py/json.py imports and original exit17/124 (`/private/tmp/specfact498-isolation-red-controls.log`). The initial16failure run contained eight real import-execution REDs plus eight fixture failures because the independent invocation explicitly selects its private report path; the fixture now writes that unchanged path, not a replacement invocation. All real import failures execute a harmless fixed marker within the test temporary directory.

The minimal correction adds `-I` to the one candidate primary projector invocation, matching every other diagnostic heredoc. No program/report/env/guard/stderr/exit, deadline, analyzer input or capsule behavior changed. [Python3.12 isolated-mode documentation](https://docs.python.org/3.12/using/cmdline.html#cmdoption-I), accessed9October2026, confirms exclusion of the current directory/user site and Python environment paths. A bounded read-only audit confirms all other diagnostic heredocs already isolate Python; existing body-only extractor tests did not retain launch flags, so the new test executes the actual workflow invocation. Final focused/full/SMART/review/hooks evidence follows. Signed0.51.3 module bytes/checksum80ee9803 and CIeba12595signature remain unchanged; no new version/signature or private key access is needed for this workflow/test/spec correction.


Final projector-isolation verification: focused251passes; Full/SMART each27requiredhostproofs plus5632portable cases,71declaredskips,95subtests and5existingwarnings. Logs: `/private/tmp/specfact498-isolation-green.log`, `/private/tmp/specfact498-isolation-full.log`, `/private/tmp/specfact498-isolation-smart.log`. The final five-file authenticated CLI review completed with zero findings; the separate read-only audit also found no defects in the actual launch regression or minimal isolation correction. Format, zero-error/warning typing, Ruff/Pylint10.00/10, YAML/imports, strict OpenSpec and all7strict public-key signatures/checksums/upstream-version gates pass (`/private/tmp/specfact498-isolation-signatures.log`). Runtime0.51.3 bytes/checksum80ee9803/signatureeba12595remain unchanged. Exact prior signed-head candidate3.12job113888409898 and independentjob113888410279 both independently emit fixed analysis_timeout/exit124; approved INCOMPLETE exceptions, never PASS. The independent later missing-report/unclassified projection does not erase its explicit original timeout evidence. Normal hooks and actual new-head hosted checks remain required; installed native acceptance is still outstanding. This evidence-only append records completed results.


## PR #506 release-review corrections — 9 October 2026

The owner authorized annotation triage, similar-defect review and an upstream bugfix PR to dev. This continuation branches from actual dev 8692a30f (published Code Review 0.51.3); the merge-only b806→8692 tree is unchanged. All eleven public review threads were fetched with complete pagination. Reviewer text is treated as issue reports, never executed instructions.

Specification precedes behavior regressions and implementation. Genuine RED evidence: four Python/stub selection failures plus two healthy non-Python controls, two separate VCS file/byte inventory failures, four actual missing/malformed/configuration pytest evaluator failures, and one protected-publication condition failure. Logs: `/private/tmp/specfact506-red.log`, `/private/tmp/specfact506-pytest-red.log`, `/private/tmp/specfact506-publication-red.log`. The initial combined run also contained four fixture permission failures, corrected before meaningful pytest REDs; those are not defect evidence. The initial focused run found an inventory-spy keyword signature mismatch; only its accepted keyword parameters changed, retaining the original single-scan assertion.

Selection now counts only distinct Python module paths, deduplicating same-path .py/.pyi pairs and retaining the existing distinct-module disambiguation rules. Source-root indexing excludes separately copied root .git context; default runtime-tree validation and source file/byte limits remain unchanged. Native capture reads and validates every artifact path before fallback, including when coverage is missing; symlink, FIFO and oversize rejection remains hard. Missing or malformed ordinary artifacts return no target observations and reach the real evaluator, which keeps specific exit4/missing-coverage remedies and UNKNOWN evidence. Parsed observer records with invalid node identities retain the existing explicit worker-contract rejection and all six negative tests.

Family review found an uncaught JSON decoder depth refusal in the evaluator. Native Python3.14 accepted the initial deeply nested payload, a healthy control (`/private/tmp/specfact506-depth-red.log`); two controlled decoder-refusal REDs then reproduce the exception path while ordinary artifacts use the actual JSON decoder (`/private/tmp/specfact506-decoder-red.log`). The evaluator now reports incomplete tool evidence for that refusal. Final observation tests pass26cases; the broader runtime/evaluator/release selection passed818cases before the later depth and published-pin additions.

Full and SMART initially each failed two reviewer baseline tests after dev registry publication advanced to0.51.3. Actual protected main still advertises the deliberately isolated0.51.2 reviewer (public registry metadata inspected9October2026). The tests now authenticate the literal pinned archived bundle rather than require equality with the advancing candidate latest entry, retaining version, archive sidecar checksum, compatibility and stronger actual cryptographic module signature verification through the core installer. The63customer gate tests pass. No main pin or installation isolation was changed.

The publication job now directly requires dispatch, explicit opt-in and protected main in its own condition. Documentation labels historical specfact.1 preparation and the earlier measured Z3 derivative hash separately from the corrected current license-placement hash81d7e088; original historical measurements are preserved. Redundant proof import and implicit string concatenation annotations receive small cleanups without removing assertions.

The authenticated sixteen-file CodeRabbit CLI review completed with one Minor report, not zero findings: “Treat malformed observer identities as incomplete evidence.” Independent validation declines it because the existing specification explicitly requires worker-contract rejection for missing/non-string node identifiers; six negative cases and the exact valid-identity control remain passing. That review preceded the final pinned-archive test correction and traceability append; those subsequent diffs were inspected locally, with no additional qualifying defect. No remote review was retried after starting. Public automatic exact-head review remains independently required.

Four hosted annotation reports are independently invalid: starred helper tuple contains all four required values; cleanup in finally deliberately runs under pytest.raises to preserve the original failure; both private fixture variables are imported and used by actual projection tests. YAML BaseLoader reports do not establish arbitrary object construction and literal JSON/request fixtures are intentional tests. These findings must be documented before resolution; real fixes remain unresolved on release506 until actual dev integration.

Final Full and SMART each pass27requiredhostproofs and5650portable cases (71declaredskips,95subtests,5existingwarnings), portable durations166.98/167.07seconds. Logs: `/private/tmp/specfact506-full-final.log`, `/private/tmp/specfact506-smart-final.log`. Final format, zero-error/warning typing, Ruff/Pylint10.00/10, YAML/imports, strict OpenSpec, read-only publish precheck and28contract tests pass. Original intentional negative tests, contracts, source assertions, no-write/isolation and deadlines remain. Publish precheck confirms unchanged core compatibility >=0.55.1,<1.0.0; no core API change requires a newer minimum.

Prepare unpublished patch0.51.4 above published dev0.51.3, refreshed checksum sha256:904cb08790f03151c5593088b45c639ecea3c0d8929526e6ab03f5ff3ec1444e. Six unchanged existing signatures verify with the public key and all seven checksum/version gates pass; the changed bundle is deliberately unsigned pending normal CI signing. No private key/passphrase access or manual registry artifact was used. Normal commit hooks remain required with the previously owner-approved Darwin capsule-review deferral only; DEFERRED is never PASS.

Exact release8692candidate job113947180533 and independentjob113947180656 both emit analysis_timeout and exit124 in actual executed log lines, independently inspected. These remain the approved INCOMPLETE timeout exceptions, never PASS, and do not classify any new-head failure. Release CodeQL analyses are successful; current source fixes, hosted checks, normal CI signing and actual native installed acceptance remain separate gates. Keep460/OpenSpec open. Release version claims stay0.51.3 until bugfix integration and CI registry publication actually reach the release head.


## PR #507 available-observer validation order — 9 October 2026

Hosted exact signed-head CodeRabbit thread `PRRT_kwDORVEFbs6q5WB-` is independently valid and differs from the earlier suggestion to soften malformed-node rejection. In source2f7951f3/CI signature-only child0b4b2c32, missing coverage/JUnit or malformed coverage could return None before validating an available observer's node identity. The existing explicit hard-rejection contract must survive ordinary incomplete-evidence fallback.

Specification preceded the test expansion. Eighteen genuine REDs cover missing/null/boolean/integer/list/object identities with absent coverage, absent JUnit and malformed coverage. Eight original/healthy controls pass (`/private/tmp/specfact507-identity-order-red.log`). The minimal correction retains all three bounded path/type/size reads before parsing, validates available parseable observer records and their unchanged string identities first, then handles missing or malformed ordinary coverage/JUnit. Two positive controls prove valid identities with missing artifacts still produce no invented observations. Final focused native worker/observations/portable-evidence131passes; final format/lint/type checks pass (`/private/tmp/specfact507-identity-order-green.log`, `/private/tmp/specfact507-lint.log`). No original identity or unsafe-artifact assertion is removed.

Patch0.51.4 remains unpublished above dev0.51.3. Its refreshed checksum is sha256:432c265a47379207af87935a0a688aa8f2553146432b3626b8aaaa5112e8e803; stale904c signature is removed pending normal CI signing. All seven strict signatures verified earlier0b4b2c32 for904c only; they do not cover this432c correction. No private signing material or registry artifact is accessed locally. Fresh Full/SMART/normal-hook and hosted outcomes follow; release506 fixed threads remain open until actual upstream dev integration.

Final ordering-correction verification: Full and SMART each pass27hostproofs plus5670portable cases (71declaredskips,95subtests,5existingwarnings), portable duration171.81seconds each; distinct logs retain independent host durations4.58/4.37seconds. Logs `/private/tmp/specfact507-identity-order-full.log` and `/private/tmp/specfact507-identity-order-smart.log`. Focused131pass; format, zero-error/warning typing, Ruff/Pylint10.00/10, YAML/imports, strict OpenSpec and all7checksum/version gates pass. A complete read-only inspection of the correction diff and adjacent artifact/evaluator call paths found no additional qualifying defect. Normal hooks and fresh CI signature/exact-head hosted review remain required; historical0b4strict-signature proof is not current432cpayload proof.


## PR #507 ordinary missing-parent handling — 9 October 2026

Codex thread `PRRT_kwDORVEFbs6q5kCK` reports strict parent resolution outside the artifact fallback. The helper gap is independently real: two REDs cover ordinary missing-parent fallback and typed dangling-symlink hard rejection (`/private/tmp/specfact507-parent-red.log`). Three controls pass, including an actual adapter/evaluator directory-removal control that already produces UNKNOWN. Therefore the report's claimed worker exit76 is not independently reproduced and is not asserted as observed evidence.

Specification precedes tests and correction. Artifact parent canonical equality now resolves existing links even if ordinary directories are missing; actual bounded no-follow open then supplies the caught absence. Existing/dangling symlink parents still change canonical paths and reject before bytes are read. Non-directory parents retain hard rejection. All three artifact reads precede parsing, every bound and node-identity ordering assertion remains. Final focused136passes with format, zero-error/warning typing and Ruff/Pylint10.00/10 (`/private/tmp/specfact507-parent-green.log`, `/private/tmp/specfact507-parent-lint.log`). A read-only inspection of the actual correction and adjacent calls finds no further qualifying defect.

Unpublished0.51.4 remains above publisheddev0.51.3. New checksum sha256:71b06f03f2b7428db415e9733c758cc3a4371ca0d3838fa709a27a99d5995d5b; old432csignature removed for changed bytes. Historical CIchildacd6ba47 strictly verifies432c only, not this71b0 payload. Fresh normal CI signing and current-head hosted evidence remain required. No private signing material or manufactured registry artifact is accessed.

Final missing-parent verification: Full/SMART each pass27hostproofs plus5675portable cases (71declaredskips,95subtests,5existingwarnings), portable durations163.75/164.73seconds. Distinct logs `/private/tmp/specfact507-parent-full.log` and `/private/tmp/specfact507-parent-smart.log` confirm completion. Focused136pass, format/zero-error-warning typing/Ruff-Pylint10.00/10, YAML/manifests/imports/strict OpenSpec and all7checksum/version gates pass. The new source checksum71b06f03 requires a fresh normal CI signature; previous432c/904c signatures and historical review statuses are not transferred. Normal hooks and final exact-head hosted evidence remain required; no native installed/publication acceptance is inferred.


## Release #506 follow-up: complete PID writes and attached Python probes (2026-10-09)

Owner merged #507 and normal registry CI published 0.51.4 in #508 at dev593656f6. All original release review threads are integrated. Follow-up uses branch `bugfix/release-506-ci-evidence` in the existing user-required worktree path; one writer remains. No signed runtime asset changes or registry manufacturing are part of these proof corrections.

Exact historical release job113960008132 failed because self_test.c creates its PID marker before writing; the proof observes existence and parses an empty file. The original deadline and actual broker/worker lifecycle assertions remain. Deterministic empty and partial-marker publication regressions, original-deadline incomplete controls and non-positive/invalid complete PID tests cover the boundary.

Exact upstream candidate3.12job113970759752 reported four ancestor-initializer `CalledProcessError` failures. The proof's `-I` argument is independently rejected by the real managed target-bootstrap validator as `project_python_option_unsupported:-I`; it disables required attachment. Four real import cases now additionally exercise that actual validator before the existing real child import. `-P` excludes implicit working-directory imports while allowing the managed launcher to retain attachment. Every original value/file, initializer, source immutability and no-original-write assertion is retained.

RED: focused command for controller cases and generated ancestor initializer: **10 failed, 5 passed**, before proof implementations changed. Six race/identity boundary REDs and four actual managed-argument REDs; the original four host imports and malformed complete PID control passed.

GREEN: complete focused broker-cleanup and native-project-runtime files: **140 passed**. Full/SMART and normal gates remain to be recorded after actual execution. These proofs do not establish native installed acceptance or erase additional hosted quality findings. The original complete report was not retained in public artifacts; 200 finite public locations and 374 summary findings remain independent triage inputs, not a timeout waiver.


Final follow-up local gates: focused140, Full and SMART each **27 host proofs + 5,686 portable tests**, 71 declared skips, 95 subtests and five existing warnings. Full162.33s / SMART160.64s. Format, typing (zero errors/warnings), Ruff/Pylint10.00/10, YAML/imports, strict OpenSpec and all seven strict public-key signatures pass. The latter authenticate unchanged published0.51.4 payload71b06f03; no version/signature bump is needed for proof/spec-only files.

Separate read-only review of all six follow-up files found no qualifying defect. This is a local audit, not a hosted review or actual Linux/native customer acceptance. Original hosted quality reports are not waived: comparison of 193 projected non-pytest location rows finds 22 error rows and 83 warning rows in units with exactly unchanged AST on main; changed units also contain genuine complexity increases. Complete original Pylint/other finding messages were not retained in public artifacts. An attempted local projected-policy Pylint triage could not execute because `resolve_pylint_policy` returns UNKNOWN/pylint_extension_unsupported for the repository's declared extension. No plugin/analysis input was removed and no alternate analyzer result is claimed equivalent to CI. Source-derived metric comparisons remain triage only; fresh applicable exact-head hosted outcomes are required.


Commit gate additionally exposed an actual scheduling gap: proof-only deltas did not schedule the blocking Linux customer review and therefore correctly could not use local Darwin deferral. Canonical host Git-index and workflow filter cases reproduce **six REDs / ten controls** against the original hook/orchestrator. Historical ignored unit test copies are unchanged. New tests reside in the existing required host proof and its shared fixtures, plus ordinary portable workflow-context tests. An initial attempt used the historical ignored copy and exposed stale pre-existing assumptions; those are not claimed as product defects or passing evidence. Canonical RED evidence is `specfact506-ci-wiring-canonical-red-final.log`.

Fix schedules native proofs, Code Review unit proofs, their host/shared wiring fixtures and the deferral hook for the same mandatory customer job. Deferral additionally requires matching scheduling rules from the staged/indexed orchestrator; missing trigger and unrelated tests still reject. No CI deferral, continue-on-error, analyzer input, timeout or enforcement flag changed. Original prompt-check assertions remain for all original cases; new proof-only cases explicitly assert that unrelated prompt checking does not run.

Final focused canonical contexts: **184 pass**. Earlier Full/SMART27+5686 evidence predates this scheduling correction; final complete runs below must establish its actual state before commit.


Final expanded correction: **Full and SMART each32hostproofs+5,689portable tests**, 71 declared skips, 95 subtests and five existing warnings;155.50s /152.67s. Final focused184, zero-error/warning typing, Ruff/Pylint10.00/10, format, YAML/imports, shell syntax, strict OpenSpec and all seven strict signatures pass. Complete eleven-file read-only diff review found no qualifying defect. Normal commit hooks and hosted exact-head outcomes remain separate; local capsule review alone uses the existing owner-approved Darwin deferral, never PASS. Signed module payload0.51.4/71b06f03 is unchanged and already published in #508.


### #509 result transport, effective review scheduling and alert #11

- Scope remains the native capsule/release correction; sole writer remains the existing user-designated worktree on `bugfix/release-506-ci-evidence`. #507 merged and #508 normally published 0.51.4 before this runtime correction. Prepare unpublished 0.51.5; do not promote release version claims before actual integration/publication.
- Spec first: whole UTF-8 completed response including findings/observations/envelope/newline retains the existing 16 MiB controller limit. Oversize becomes fixed bounded UNKNOWN/error, never truncated PASS; artifact safety and normalized finding identity remain first. Four genuine REDs (combined independently admissible files, multibyte collected/finding bytes and newline boundary) precede implementation; exact-boundary and unsafe finding controls remain. Initial invalid finding-fixture schema failures were corrected before genuine REDs and are not product evidence.
- Indexed scheduling: eight orchestrator REDs (self-trigger, missing/disabled/nonblocking job, wrong filter/target, decoy rule and disconnected output) precede parsed effective scheduling checks. Two explicit YAML false-condition REDs and six reusable-review job/step/condition REDs precede subsequent shared boundary corrections. No CI deferral, altered analyzer input/deadline or softened failure enforcement. New source/test validators remain in mandatory customer triggers. A fixed mutation inventory and shared scope/filter helpers keep new function complexity at 10 or below (existing historical test complexity unchanged).
- Security alert11 is CodeQL `cpp/very-likely-overrunning-write`, critical, on main209b4ed8. All THREE sinks were inspected (bootstrap, Git helper and managed worker `.inc`). Supported host SDK27.0 has PATH_MAX1024, so the alleged 4096-byte macOS overflow is not observed. Three actual-source sink REDs under an explicitly injected larger-libc allocation contract precede the allocated canonical-path helper; not claimed as an observed macOS exploit. All allocated paths free on match/rejection, while protocol length, canonical equality, private-root and directory constraints remain. Seven real-libc canonical/alias/relative/dot/missing/overlong/null controls and all three injected sinks pass. Strict-C11 Linux visibility was caught by independent review and corrected with `_XOPEN_SOURCE=700`; hosted Linux remains required. Independent security candidate review found no remaining actionable scoped defect.
- Actual production ARM64 build.sh compiles bootstrap, broker, verifier and self-test with normal flags and verifies all four local ad-hoc signatures. The Python proof identity is deliberately unadmitted; this is local build evidence, not protected signing, publication, native execution matrix or installed acceptance.
- Earlier 147dd7ea PID/managed import/wiring corrections remain intact; original tests and all limits/assertions are retained. Historical CP312 additional quality findings remain unwaived without complete rule evidence; current hosted results must establish the new head independently. No remote review retry or extra review command was sent.

- One further effective-filter RED reproduces `predicate-quantifier: every` preventing all mutually exclusive capsule rules from scheduling; validator now requires the original some/default matching semantics. No path inventory is reduced.

- Completed local gates for the final source: focused183; Full portable5706 and SMART52host+5706portable, 71declared skips/95subtests/5existing warnings; final host52 also runs in focused verification (Full's earlier51host span preceded the one extra quantifier case). Format/type/lint/YAML/import/strict OpenSpec/shell/checksum/version pass. Prepared0.51.5 checksum1ca9ddb1 is currently unsigned; six existing signatures verify and normal CI must supply the seventh. Normal commit hooks and exact-head hosted results are still required; no false PASS is recorded for deferred local capsule review.


### #509 additional indexed deferral annotations — 10 October 2026 (Europe/Berlin)

Five additional current Codex/CodeRabbit threads independently reproduce real gaps: missing/excluding PR events, mixed unrelated staged reviewable paths, literal on versus boolean YAML keys, excluded Linux CP312 execution and replaced/short-circuited review commands. Specification precedes eighteen genuine REDs in the canonical host proof; two additional duplicate/ambiguous mapping-key REDs precede parser hardening. Logs: `/private/tmp/specfact509-final-trigger-red.log` and `/private/tmp/specfact509-yaml-identity-red.log`. All original tests and blocking review assertions remain.

The hook checks the complete indexed candidate surface against the actual dev merge-base. Literal PR events must cover both release targets and the candidate; ambiguous/duplicate YAML mappings fail closed. Reusable review execution must equal the parsed already-integrated dev contract, including Linux runner, effective matrix, commands, supporting steps, environment, inputs and deadlines. Formatting/comments may differ; unrelated nonreviewed generated docs still pass. A new positive-control fixture initially attempted to recreate an existing docs directory; corrected idempotent fixture setup is not a product defect or RED claim. New implementation/helper function complexity remains at ten or below; historical test complexity is unchanged.

Embedded ast-grep jsonify/command-injection reports are independently invalid: JSON is file/wire serialization with no HTTP response context; compiler, child, workflow-shell and git-show calls use fixed argv or tracked recipes with owned temporary inputs and no incoming request source. Framework serialization changes or removal of intentional tests would violate the existing contract. This disposition does not waive actual CI test, crash or unclassified quality failures.

Runtime 0.51.5 checksum1ca9ddb1 and normal CI signature-only child3a07c3d2 are unchanged by this workflow/test/spec follow-up; no new version or signature is required. Fresh gates and actual push/review outcomes follow below.

A separate read-only audit found falsey malformed PR configurations interpreted as defaults. Four actual indexed shell REDs precede explicit null-only defaulting; false, zero, empty sequence and empty string all reject. Log `/private/tmp/specfact509-falsey-pr-red.log`. Total current follow-up genuine REDs:24.

Exact signed3a07 candidate job114044157782 emits ten FileNotFoundError canonical C test failures and additional quality (132 findings,20errors,100warnings,12info); it is NOT a timeout. All ten reproduce with cc absent from PATH (`specfact509-no-compiler-red.log`), and each actual exception names cc. The sealed toolchain declares no compiler; native compile tests belong in the already explicit host/native contexts. Four required-context REDs precede moving the proof unchanged to tests/native/proof_native_canonical_path.py and mandatory Full/SMART, all three macOS boundaries and a separate Linux compiler job (`specfact509-compiler-context-red.log`). No assertion or test is skipped and no compiler/tool/input/deadline is added to the sealed capsule. This establishes the prerequisite mismatch without asserting an unprojected hosted filename.

Exact signed3a07 independent job114044157825 actually emits analysis_timeout and exit124 in run37996276718; approved INCOMPLETE for that job only. Candidate114044157782 and its20errors remain unwaived. Quality114051143394 fails its customer prerequisite before tools/tests; no PASS. Other quality jobs require their own evidence. Earlier current follow-up Full78host+5706portable passed before the context routing; fresh final routing gates follow.

Complete finite signed3a07 candidate projection retains all132public finding locations (`specfact509-signed-candidate-public-findings.json`), including ten actual test failures plus nine non-pytest errors. Independent AST comparison against dev593656f6 identifies all nine non-pytest error functions as unchanged (`specfact509-signed-quality-triage.json`): seven complexity rows, one nesting row and one Pylint style row. This is provenance/triage only, not an authoritative PASS or owner waiver. Pylint row lacks public rule/message. Earlier sparse374/200 evidence is not substituted for this current finite report.

Compiler-context focused104pass; all ten moved native proof bytes exactly match their previous file (SHA256641c64645192a97634c4f154ddec073fe9b1dc92240fd4734e00a1ea726162d8). The exact isolated compiler recipe passes10 locally with cacheprovider disabled; this avoids /dev configuration-root cache writes and does not supply hosted Linux proof. Final lint/type10.00/10 and zero errors/warnings, YAML/import/strict OpenSpec/shell and all7strict signatures pass. Earlier concurrent follow-up SMART started before the proof routing was complete and failed a superseded command-context expectation; it is not PASS. Stable final Full/SMART follow for the final required contexts.

Final context Full also identified six retained SMART assertions expecting the old single host proof as the final argument. The assertion now requires the exact two-proof suffix while preserving every host/portable failure code, call count, extra-argument and baseline exclusion check. The failed run is retained in specfact509-context-full.log; fresh final gates follow. No runtime failure or dropped assertion is hidden by this fixture update.

Final stable follow-up verification: focused128pass; Full and SMART each88requiredhost/native proofs plus5700portable cases,71declaredskips/95subtests/5existingwarnings. Portable durations156.86s/155.54s, host11.12s/11.96s. Logs specfact509-final2-focused/full/smart.log. Final format/type0errors-warnings/Ruff-Pylint10.00/10, YAML/imports/strict OpenSpec/shell and all7strict signatures against actualdev0.51.4 pass. Actual staged candidate scheduling validates successfully against its full indexed surface and dev merge-base contract. Complete fourteen-file read-only review finds no additional qualifying defect. New implementation/helper complexity remains at10orbelow; existing historical test complexity unchanged. Normal hooks and new-head hosted outcomes are separate and follow. Runtime0.51.5 checksum1ca9ddb1 and CI3a07 signature remain unchanged.


### #509 detector execution findings — 10 October 2026 (Europe/Berlin)

Exact6c625398 completed Codex/CodeRabbit reviews introduce independently valid P1 detector-runner and Major conditional-prerequisite findings (PRRT_kwDORVEFbs6q9-4J/PRRT_kwDORVEFbs6q9_l3). Specification precedes nine actual indexed shell REDs for missing/unavailable runner, conditional/missing dependency, empty matrix, disabled checkout, wrong checkout ref and overridden filter base/ref. Two further REDs cover removal of the integrated registry trigger and duplicate embedded filter keys; original formatting control passes. Logs specfact509-detector-red.log and specfact509-detector-filter-red.log.

The parsed detector job must match integrated dev execution after only its separately validated capsule inventory is normalized; baseline trigger rules remain a subset. Every runner/dependency/strategy/checkout/filter option/output/step stays bound. Shared SafeLoader-based mapping construction rejects duplicates in outer workflows and embedded filters, preserves literal GitHub on identity and supports equivalent comments/formatting. Original negative tests, scope, enforcement, inputs, deadlines and failure semantics remain. This workflow/test/spec correction leaves signed0.51.5 runtime bytes/checksum1ca9ddb1 and normal CI3a07 signature unchanged. Full/SMART and normal hooks follow; no external review retry or explicit review command is sent.

Final detector correction: focused130pass; Full and SMART each100requiredhost/native plus5700portable,71declaredskips/95subtests/5existingwarnings, portable156.29s/154.04s and host13.89s/13.81s. Format/type0errors-warnings/Ruff-Pylint10.00/10, YAML/imports/strict OpenSpec and all7strict signatures against actualdev pass. Complete five-file read-only diff/consumer audit finds no additional qualifying defect; implementation complexity at10orbelow and new test helpers at6orbelow. Metadata refresh passes24issues. Normal hooks and actual new-head hosted results remain separate.

Exact prior6c625398 candidate114056489686 in run38000291648 reports134finitepubliclocations (10errors/112warnings/12info), including pytest tool_error with analyzer_reported_incomplete_execution and the nine earlier quality error locations. No actual test-case failure is projected; absence is not proof of successful execution. The precise pytest and Pylint messages remain unavailable, and all these failures remain unwaived. Exact6c independent114056489541 actually emits analysis_timeout/exit124; approved INCOMPLETE only for that job, never PASS and never transferred to the new head. Logs specfact509-job-114056489686.log / specfact509-job-114056489541.log and finite rows specfact509-source6c-candidate-findings.json are retained. CodeRabbit completed3a07→6c across14files with the new detector finding; that completed review is historical for this follow-up. All ten canonical security proofs passed in exact6c Linux job114056449461. No remote review retry or explicit review/resume command was issued.


### #509 authoritative quality follow-up — 10 October 2026 (Europe/Berlin)

The temporary monitor state/logs were unavailable at this heartbeat. Reconstruction uses committed evidence, existing consolidated summary6086625697 and fresh fully paginated public metadata, not invented prior results. Heads remain release593656f6/upstream19522c98;9upstreamthreads allresolved,13release/onlybudgetthread open. CodeRabbit public summary6089610356 explicitly covers6c625398→19522c98 across5files, coveredCommitId19522c98/kindreviewed; completed with no actionable threads. Generic incoming-request/command findings remain invalid for fixed git argv/internal path/dev merge-base and tracked owned fixture recipes. All9native execute cells,3builds/boundaries/tools/Linuxcanonicalproof/CP311/CP313/Docs/requirements/CodeQL/signatures pass for19522c98; these are candidate proofs, never installed acceptance.

Exact19522c98 candidate114061317015/run38001643608 reports135finitepubliclocations (10errors/113warnings/12info), including pytest tool_error/analyzer_reported_incomplete_execution and9qualityerrors. This is not a timeout. Exact independent114061316827 actually emits analysis_timeout/exit124; approved INCOMPLETE for that job only, never PASS. Quality114069168015/114069167948/114069168066 independently stop at failed customer prerequisite before tools/tests, never PASS. Original pytest diagnostic remains unavailable/unwaived.

Specification precedes two real production Radon policy REDs: native worker CC48/25/23/22/18 plus nesting.error and ownership proofs CC22/18. Logs specfact509-quality-red.log. Direct parser plus identical production mapping reproduces the same8baseline blockers in specfact509-quality-pure-baseline-red.json. Regression stays pure Python (no new child process inside sealed tests). Minimal decomposition preserves every original bound, validation order, failure message, member/argv/option allowlist, replay identity and ownership assertion. Two imperfect helper extractions introduced8then4NameError test failures and were corrected; these are implementation mistakes, not claimed product REDs. Final focused252passes, including complete result/observer identity tests.

Local Pylint independently identifies exact reported line708 E0602 for the local Session self-return annotation; supported Python3.11+typing.Self corrects it without behavior or assertion changes. Refreshed unpublished0.51.5checksum151ef8856caa2e745a011911510461a0ac022fc4562170ca452eaaf7bece4a26 is checksum-only pending normal CI signing. All private-key inputs are explicitly removed during checksum refresh. All7checksum/devversion gates pass; only6existingstrictsignatures cover unchanged bundles until CI supplies the seventh for these actual bytes. Historical3a07 signature covers1ca9only, never this correction. Full/SMART/normal hooks and new-head hosted outcomes follow separately. Remaining full-surface warnings and unclassified pytest evidence are not waived.

Final quality correction gates: focused252, Full/SMART each100requiredhost/native+5702portable,71declaredskips/95subtests/5existingwarnings, portable153.80s/151.20s and host13.29s/13.38s. Format/type0errors-warnings/Ruff-Pylint10.00/10, YAML/imports/strict OpenSpec/checksum/devversion pass. Exact local Pylint reports no error/fatal after Self correction. Independent bounded old/new audit166admission/replay comparisons identical; complete seven-file read-only diff/consumer audit finds no additional qualifying defect. Remaining historical warnings and unclassifiedpytest are unwaived, not asserted fixed. Normal hooks and normal CI signature/current-head hosted outcomes follow separately.


## 2026-10-10: bind reusable reviewer caller before local deferral (#509)

Scope: independently validate Codex thread PRRT_kwDORVEFbs6rHUcv. GitHub's supported caller-job keywords exclude continue-on-error/runs-on/steps/env/timeout-minutes, even when false or empty. The existing checks admitted those fields and ignored changed supported scheduling fields. Pinning the complete parsed caller to integrated dev reuses the existing detector/reviewer contract approach; no deadline or analyzer input changes.

- Spec first: added the integrated reusable-review caller scenario and case460-21-15.
- Genuine RED: nine indexed end-to-end hook cases accepted unsupported false continue-on-error, runs-on, empty steps/env, timeout-minutes, unknown input, empty permissions/matrix and cancelling concurrency. All nine failed their required rejection assertion; three formatting/generated-doc controls passed (1.97s). Log: /private/tmp/specfact509-caller-red.log.
- Implementation: compare the full parsed customer-capsules caller against the same dev merge-base before validating the integrated reusable execution. Comments/formatting remain equivalent; existing enforcement, dependencies and failure propagation are unchanged.
- Focused GREEN: all115current host/proof-context cases pass (18.46s). An initial ad-hoc command accidentally included immutable baseline tests/unit/test_capsule_deferred_review_ci.py and produced six obsolete fixture/version failures; these are a test-selection mistake, not product RED evidence. Required Full/SMART already retain the explicit current host context and exclude the immutable baseline. No baseline assertions were edited.
- Separate complete read-only review-agent audit of the four-file diff and validator/hook/fixture consumers: no additional qualifying introduced defect. Full/SMART, normal hooks and strict signatures are recorded below only after actual completion.
- Timeout clarification from actual source: overall candidate hook and independent CI reviewer each allow300seconds; portable pytest child allows1200seconds, local targeted path defaults120seconds, sandbox analyzer launch defaults300seconds. Exact signed45aa independent114300235642 emitted analysis_timeout/exit124; candidate114300235667 instead returned134finite findings (1pytesttool_error/121warnings/12info) and analyzer_reported_incomplete_execution/exit1. Missing precise pytest diagnostic remains unwaived. These distinct outcomes are not interchangeable; no budget is changed.

Final caller correction verification: focused115pass; Full/SMART each109requiredhost/native plus5702portable,71declaredskips/95subtests/5existingwarnings. Full host14.92s/portable177.20s; SMART host15.38s/portable172.47s. Format/type0errors-warnings/Ruff-Pylint10.00/10, YAML/import/strictOpenSpec and all7strictpublic-key signatures/checksums/dev-version gates pass. Complete five-file read-only audit finds no additional qualifying introduced defect. Normal hooks and actual pushed-head thread resolution are recorded only after completion; new-head hosted results remain separately required.


## 2026-10-10: preserve required quality-consumer propagation (#509)

Independently validated Codex P1 PRRT_kwDORVEFbs6rHePN. The required quality jobs consume customer-capsules and explicitly reject failed/skipped review, but indexed deferral did not bind those consumers. Fresh source/baseline comparison confirms complete parsed orchestration already matches after existing validated trigger normalization.

Spec first: added the required-quality-consumer scenario and case460-21-16. Eleven genuine indexed hook REDs reproduce detached customer dependency, absent/replaced/skipped prerequisite, disabled/nonblocking/empty-matrix quality and changed workflow environment/defaults/permissions/concurrency; three equivalent-formatting/generated-doc controls pass (2.38s). Log:/private/tmp/specfact509-consumer-red.log.

Minimal implementation compares the complete parsed orchestrator after normalizing only the already validated PR event and capsule trigger inventory. Every job, prerequisite, workflow setting, non-PR trigger, analyzer input/deadline and original proof assertion stays bound. Complete four-file read-only diff/consumer audit finds no additional qualifying introduced defect; TDD append is independently reviewed as evidence only. Focused126pass(17.93s), lint/type0errors-warnings/Pylint10.00/10, YAML/imports/strictOpenSpec and all7strictpublic-key signatures pass. Runtime35185/checksum151e/signature45aa remain unchanged; no new version/signature is required. Full/SMART/hooks and exact-head resolution follow only after actual completion.

Final consumer verification: full: 120 passed in 19.10s ; 5702 passed, 71 skipped, 5 warnings, 95 subtests passed in 173.20s (0:02:53)  | smart: 120 passed in 18.33s ; 5702 passed, 71 skipped, 5 warnings, 95 subtests passed in 177.60s (0:02:57) . Focused126pass. All format/type/lint/YAML/import/spec and7strictsignature gates pass. Complete final five-file read-only audit finds no additional qualifying introduced defect; no deadline, policy, assertion, analyzer input or signed runtime byte changes. Local capsule review is DEFERRED to mandatory exact-head Linux CI, never PASS. Normal hooks and exact pushed-head thread resolution are recorded separately only after actual completion.


## 2026-10-10 owner-approved review budget, measured pytest evidence and warning correction

The owner explicitly requested resuming CodeRabbit, identifying pytest evidence failure, correcting genuine findings/warnings and enlarging an inadequate 300-second review budget. Resumed once via issuecomment6101892198. Public CodeRabbit summary6089610356 now records coveredCommitId9235a400f6f8480c06941acff54caf3a3e51862d/kind reviewed. New thread PRRT_kwDORVEFbs6rHlVW repeats complete workflow/caller/orchestration requirements already present in the preceding three spec scenarios and implemented indexed equality checks; independently invalid as a missing-requirement report. No reviewer prompt was executed and no second review/resume command was sent.

Spec first: added finite 1800-second whole-review budget and measured script coverage, warning-remediation preservation, and public return-contract scenarios. Four genuine indexed/behavior REDs reproduce candidate300, independent300, rejection of approved1800, and incorrect acceptance of stale300; two unsupported0/3600 controls already reject. Budget fixture mistakes (candidate-only spec accidentally included in baseline, and replacing the preparation bound as well as review bound) were corrected before recording product REDs. Log:/private/tmp/specfact509-budget-red.log. Only the exact independent wrapper expression changes from300 to1800 in the integrated deferral baseline. All other complete parsed execution, inputs, child budgets and prerequisites remain bound. Eight existing full-suite expectations still naming300 were updated to1800 without changing their original exit124, exit propagation or private-output assertions; these expected-policy mismatches are not new product defects.

Actual real-child pytest/coverage reproduction: configured sources src/packages/tools exclude scripts/check_capsule_deferral.py even when that script executes; native production coverage evaluation reports the sole tool_error, UNKNOWN, analyzer_reported_incomplete_execution. Adding scripts and executing it produces PASS; leaving it unexecuted produces real TEST_COVERAGE_LOW0%, retaining authoritative failure. Logs:/private/tmp/specfact509-pytest-source-policy-repro.py and .log. Historical hosted jobs expose only the generic tool_error; their private original diagnostic remains unavailable. This is an independently reproduced causal coverage defect matching the public error location, not a claim to have recovered private historical messages. Repository source configuration now includes scripts. Portable proofs execute the actual parser/validator against fixed git-show inputs; host/indexed subprocess proofs remain mandatory and separate. Measured actual checker line-and-branch coverage is99.05660377358491% (149/150lines,61/62branches), above the unchanged80% repository threshold. Log:/private/tmp/specfact509-validator-coverage.json. The coverage-policy regression uses an isolated real coverage child so it does not disrupt the review collector; an earlier nested collector attempt was a fixture mistake, not product RED evidence.

Production-policy REDs independently reproduce six remaining Radon warnings in native roots/observation/main and retained UV/canonical proofs, and seven public missing-contract warnings. Logs:/private/tmp/specfact509-warning-red.log and /private/tmp/specfact509-contract-red.log. Runtime decomposition extracts unchanged artifact admission into native_worker_evidence; malformed observer identities still reject before missing-evidence fallback, all three paths validate first, original size/type/no-follow/parent constraints remain. Root permission predicates and dispatch preserve original order, diagnostics, replay and exit identities. Postconditions express existing CompletedProcess/None/int/exit-set guarantees without narrowing inputs. Generated UV fixture cases retain the full48-case Cartesian product. AST assertion audit (normalizing only explicit encoding keywords) retains all135 original runtime,36 observation,52 context and29 host assertions. Complete new helper production complexity mapping has zero findings. Original compiler/security, ownership/RECORD/source-precedence, no-write/isolation and whole-result16MiB limits remain.

Implementation mistakes (Ruff removing an intended public compatibility alias, one initially missed one-line run decorator, and a transient filter indentation during inventory editing) were corrected and are not product RED claims. Explicit UTF8, unused callback argument names and check=False retain original fixture payloads and assertions. Complete read-only review-agent diff/consumer audit found no additional qualifying introduced defect; native preparation copies the entire authenticated package including the new helper. New source has641 focused passes (27.55s) plus29 hook tests (1.29s). Final Full has124 required host/native proofs (17.56s) and5736 portable passes (161.51s),71 declared skips/95 subtests/5 existing warnings. Final type0errors/warnings, format/lint10.00/10, YAML/imports/strict OpenSpec and shell/diff checks pass. SMART and normal hooks are recorded only after completion. Local capsule review remains owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS. Remaining full-surface warnings and historical generic evidence failures are not waived; new exact-head hosted validation is required.

Runtime0.51.5 remains unpublished above published dev0.51.4. Checksum sha256:f98c1a05f4c86ac1d386202bcb4c8eab410a45cf9f9773f4cac0ef2cf0da8f38 covers these corrected filesystem bytes; the old45aa signature covers only prior151e and was removed. All seven checksum/upstream-version gates pass without signature requirement. Normal CI must sign this payload; no private key was accessed or registry artifact manufactured. Actual source/signed heads and strict verification are recorded after their completion. Keep release0.51.4 claims, #506 budget thread and #460/OpenSpec open until actual integration/publication/installed acceptance.


Additional full-surface pure policy audit reproduced a pre-existing blocking seven-level tampering-fixture nesting finding now entering the touched worker-test review surface. A meaningful production KISS RED (/private/tmp/specfact509-tamper-nesting-red.log) precedes mutation-table extraction; all seven original tampering cases, replay steps and UNKNOWN/exit/diagnostic assertions remain. Complete worker proofs53pass(0.53s), including the new no-blocking-nesting regression. Earlier Full124+5736 and SMART124+5736 results predate this last fixture-only correction and are not presented as final-source completion; final repeated gates follow. Private imported helper and autouse-fixture YAGNI reports are independently invalid: exact worker import/calls and pytest autouse registration show real use, not dead code. Other remaining KISS/Pylint/architecture warnings remain unwaived for independent triage and exact-head hosted validation.


Final correction gates after the last tampering-fixture edit: Full124requiredhost/native(20.25s)+5737portable(173.68s); SMART124requiredhost/native(19.35s)+5737portable(161.30s). Each retains71declaredskips/95subtests/5existingwarnings. All66 original worker-test assertions and the exact seven-case tampering matrix are retained. Final lint10.00/10/type0errors-warnings/YAML/imports/strictOpenSpec/shell/diff gates pass. Actual indexed validator admits the complete593656f6merge-base candidate33paths/29reviewpaths with only the owner-approved review-budget expression adaptation and validated trigger inventory. Normal hooks/CI signing/exact-head hosted review remain separately required; no current CI-green claim.


## Sequential independent-job budget correction — 10 October 2026

CodeRabbit completed exact 9235a400→8780e472 coverage and reported PRRT_kwDORVEFbs6rH1xX: two sequential phases each permit 1,800 seconds inside a 2,700-second job. This is a real scheduling contradiction, independently confirmed from the tracked workflow. Under the owner's explicit authorization to enlarge inadequate hard limits, the proposal/spec select the minimal job adjustment to 75 minutes: two 30-minute phase caps plus 15 minutes for setup and diagnostics. Splitting preparation would add isolated-state transfer/trust/cleanup infrastructure; that expansion is unnecessary. Both phase caps, the customer 90-minute job, commands, prerequisites, environment, analyzer/test deadlines, isolation and incomplete/error propagation remain unchanged. This evidence does not claim an observed hosted job cancellation at the worst-case timing.

Spec precedes regressions and implementation. Three maximum-legal-phase scenarios and real portable/indexed admission tests produce seven genuine failures and four rejection controls on the old implementation (1.50 seconds): legal 75-minute candidates reject, obsolete 45-minute candidates admit, and both legal phases cannot complete in 45 minutes. Log: `/private/tmp/specfact509-job-budget-red-final.log`. An initial host fixture omitted its required OpenSpec evidence and produced two unrelated extra failures; that fixture error was corrected before the authoritative RED run and is not product-defect evidence. Only then did the workflow and exact dev-contract adaptation change. Candidate 45/60/90 job bounds still reject. Focused scheduling proofs all pass: 173 in 18.82 seconds. Log: `/private/tmp/specfact509-job-budget-focused.log`.

Full verification passes 128 required host/native proofs in 18.47 seconds and 5,744 portable tests in 160.82 seconds, with the existing 71 declared skips, 95 subtests and five warnings. Log: `/private/tmp/specfact509-job-budget-full.log`. Format, type (zero errors/warnings), lint (10.00/10), YAML/manifests, imports, strict OpenSpec and diff checks pass. All seven actual public-key signatures/checksums/version gates pass against origin/dev; signed runtime f98 bytes and 0.51.5 remain unchanged. The first ad-hoc strict-signature invocation omitted the public-key and correct version baseline, so it failed configuration; the corrected public-key/dev-baseline invocation passes. That invocation mistake is not a product/signature defect. Log: `/private/tmp/specfact509-job-budget-signatures-correct.log`.

A separate complete read-only diff/consumer audit reports no qualifying introduced defect. All original host assertions (30) and portable context assertions (59) remain. P1 packaging report PRRT_kwDORVEFbs6rHy10 is independently invalid: native preparation copies the full authenticated regular-file package, and assembly copies every file in the verified candidate inventory. The helper is mapped into isolated site-packages and included in trusted-worker-v1; TRUSTED_RUNTIME_MODULES binds minimum entrypoints rather than limiting copied dependencies. This assessment was documented on the existing consolidated summary before resolution. Generic JSON/command reports concern fixed argv/internal file fixtures; the /tmp/substituted string deliberately exercises identity rejection, not filesystem allocation. No original negative assertion is removed.

Historical original private pytest messages remain unavailable; prior failures and remaining full-surface warnings are unwaived until actual hosted confirmation. Local capsule review remains owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS. New source requires current-head hosted reviews/checks; installed native publication/customer acceptance and main CodeQL alert closure remain separate. #460/OpenSpec stays open.

Final SMART for the scheduling correction also passes 128 required host/native proofs and 5,744 portable tests in 155.51 seconds; existing skips/subtests/warnings are retained. Log: `/private/tmp/specfact509-job-budget-smart.log`. A newly completed exact8780 CP312 candidate reports genuine shell-fixture FileNotFoundError cases, a CrossHair unrecognized-output warning and further scoped findings. That new failure is not a timeout and is not waived; its finite public rows are saved at `/private/tmp/specfact509-job-114314205246-public-rows.json` for the next bounded root-cause correction.


## Required controller shell proofs and scoped helper exports — 10 October 2026

Finite executed evidence on exact signed8780 candidate114314205246/run38086339528 reports244findings:36errors/189warnings/19info, with200public locations. Thirty-one actual FileNotFoundError cases identify four Bash-launch proof functions (9preparation,4primary diagnostic crash,2secondary crash,16import-isolation). This is exit1, not an executed timeout; a literal timeout diagnostic in printed workflow code is not timeout evidence. Exact5fe candidate114317681032/run38087704322 independently projects the same31failures and scoped findings; no historical classification is transferred. Original private CrossHair/coverage diagnostics remain unavailable. Logs:/private/tmp/specfact509-job-114314205246.log and /private/tmp/specfact509-job-114317681032.log.

Spec precedes six genuine production/context REDs plus one control:/private/tmp/specfact509-shell-context-red.log. The required Bash controller proofs were wrongly entering the sealed portable analyzer, which has no Bash executable. A bounded modeled absence plugin independently reproduces all31failures in1.47seconds; it intercepts only Bash and delegates every other process launch. This modeled reproduction is labeled separately from actual hosted execution. All31cases move to explicit required host/native execution, with original decorators and all154assertion ASTs preserved across the unit/host split. Full and SMART require the third host proof and still propagate host failure before portable execution; Linux and all three macOS boundaries execute it. The exact isolated Linux recipe compiles/runs all10canonical security proofs plus31shell cases:41pass in3.00seconds. Portable Python projection remains in discovery; the complete remaining unit proof under modeled Bash absence passes193tests in9.14seconds. No capsule shell, skipped case, softened assertion or changed analyzer input/deadline is introduced.

The import-isolation fixture's exact production Radon CC16 blocking finding reproduces before setup/assertion extraction; unchanged policy then reports no finding. All poison identities and original review exit/private-output assertions remain. Exact scoped Basedpyright reproduces two reportUnusedFunction errors for the helper definitions genuinely imported/called by native_worker. Explicit exports name the same existing symbols and identities; the exact scoped analyzer then reports zero errors/warnings/information. Logs:/private/tmp/specfact509-helper-export-red.json and -green.json. Export declaration changes runtime bytes, so0.51.5 remains unpublished and gets a new draft checksum; normal CI must provide the signature. Old8780/f98 does not authenticate the new5d56payload. No private key is read.

Initial Full verification catches six old SMART assertions still expecting only two host paths, plus a real coverage probe environment leak. The SMART expectations now name all three mandatory paths, retaining every original call-count, argument, exclusion and failure-propagation assertion. They are expected-policy updates, not product RED claims. Coverage(data_file=None) still creates the inherited COVERAGE_FILE parent directory before constructing its in-memory store; inherited /opt/specfact causes actual PermissionError. A spec-first owned non-directory blocker reproduces the same mechanism deterministically (one genuine RED, one passing control):/private/tmp/specfact509-coverage-env-red.log. The real child now ignores only the inherited data-file destination and local config, still measures actual script execution and complete lines, and leaves production collector configuration/80percent policy unchanged. Final focused117pass in4.68seconds.

Transient Ruff formatting/RET504 errors and an initial local CrossHair diagnostic launcher missing its package import path were corrected invocation/implementation mistakes, not product REDs. Bounded local host CrossHair on Python3.14 independently reports a constructor Signature ValueError; this host failure does not establish the cause of sealed CP312 unrecognized stdout and is not a waiver. CrossHair incomplete evidence, two precise pytest coverage diagnostics and remaining full-surface warnings stay unwaived. Local capsule review stays owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS.

Final Full passes159required host/native proofs in19.51seconds plus5720portable tests in159.93seconds, retaining71declaredskips/95subtests/5existingwarnings. Final format/type0errors-warnings/lint10.00of10/YAML/import/spec/draft-checksum/dev-version gates pass. The first draft refresh was rejected by automatic approval review; documented checksum-only dev-worktree preparation (docs/reference/module-security.md:50-55), explicit owner authorization and existing normal-CI-only signing flow supplied concrete evidence for approval of the same action. No bypass or private-key access occurred. Draft verification is not seven strict signature proof. SMART, normal hooks, actual pushed head and normal CI signature/strict verification are recorded separately after completion.

Final SMART also passes159requiredhost/native(19.51seconds)+5720portable(158.55seconds), with71declaredskips/95subtests/5existingwarnings. Log:/private/tmp/specfact509-shell-smart-final.log. Complete final read-only diff/consumer audit, including the coverage child environment and three-path SMART expectation, reports no qualifying introduced defect. Runtime draft checksum issha256:5d5663174cfc69d828c8f45b8e4c75bb721e6c4df7402b9add7033c20d79f1b1; normal CI signature and current-head hosted validation remain required.


## 11 October 2026: current coverage attribution, actual child state and warning family

Actual signed headc65a41e6 completed CodeRabbit coverage5fe8a04c→c65a41e6 (review5480956753, coveredCommitIdc65a41e6): no new inline threads, one body nitpick about the inherited coverage destination. All14upstream threads remain resolved; release budget thread stays integration-dependent. Exact current candidate114322386176/run38089177839 exits1 with217findings (2errors/195warnings/20info),200finite location rows and no projected individual test-case failure. The31actual Bash failures and earlier type/complexity blockers are absent from this head. Exact independent114322386210 exits1 with oversized_report, observed bounded header, contracts errors on base/head and targeted-pytest error on base. Neither job has independently verified executed analysis_timeout/exit124; oversized/incomplete evidence remains unwaived. An initial ad-hoc parser mistakenly recognized the workflow's printed timeout_status assignment as executed JSON; this was corrected before any public classification or waiver. The strict parser rejects printed ANSI-cyan source and accepts only timestamp followed directly by a JSON object. This parser invocation mistake is not a product RED. Original private historical messages remain unavailable.

The actual current portable-pytest-v2 producer has three testing-error rules; TEST_OUTCOME_NOT_PASS and TEST_COVERAGE_POLICY_FAILED are fixed public enum values, while TEST_COVERAGE_LOW is omitted. Thus the two current testing/error rows with no rule independently identify LOW; this is not the earlier tool_error classification. A bounded real line-and-branch measurement of184existing relevant tests reproduces native_worker77.95percent and SMART41.46percent under unchanged80percent policy. The unchanged production evaluator emits exactly two TEST_COVERAGE_LOW errors at the reported source files:1. This measurement is a local diagnostic, not the unavailable exact hosted percentages. Evidence:/private/tmp/specfact509-c65-production-low-coverage-findings.json.

Spec precedes a genuine inherited-state RED (positive case fails, absent-state control passes):/private/tmp/specfact509-inherited-probe-red.log. The old test removed COVERAGE_FILE before child launch. The corrected real child receives and verifies the exact owned unusable destination, then discards only its own override before constructing its in-memory collector. Actual script execution/complete measured lines and parent collector/policy remain. Meaningful new portable tests cover SMART bootstrap rejection/no later execution, exact run/force argument/exit forwarding, check/status output/no test launch, invalid-command exit2, real managed Semgrep adapter dispatch with explicitly synthetic exact replay receipts and owned policies, policy-grant rejection, and contract-inventory schema/root/symlink boundaries. No host executable or fabricated coverage enters these tests.

The expanded real measurement exposes four fixture assertions whose read_coverage_config inherited the controlled parent COVERAGE_FILE. These are actual local fixture REDs, not recovered historical private failures:/private/tmp/specfact509-coverage-correction-measured.log. Isolating only each fixture's config-reader environment retains every original sealed-data-file/plugin/escaped-expression assertion. Final351selected tests pass5.47seconds under actual coverage. Native worker measures85.0394percent and SMART95.1220percent combined line-and-branch coverage; the unchanged production evaluator emits zero findings:/private/tmp/specfact509-coverage-final-production-findings.json. Repository aggregate coverage of this deliberately focused subset is below80 and coverage-json exits2 as expected; no global production gate is waived. Final strengthened probe/dispatch focused163pass3.11seconds.

Actual unchanged Pylint configuration independently matches21redundant local imports and their shadowing/local-import diagnostics; spec-first family RED records42duplicate/shadowing reports plus the matching local-import warnings:/private/tmp/specfact509-import-family-red.json. Remove only already-bound standard-library reimports, retain external fixture identities through explicit names, and wrap six literals without changing their payloads. Remaining standard-library imports move to module top. Module-length RED then reports1287/1000lines:/private/tmp/specfact509-projection-module-red.json. Fifteen observation tests move into the existing tests/unit/specfact_code_review/** portable review surface. All42original function/decorator ASTs initially match across the split; all154original projection assertion ASTs remain identical through final corrections. One duplicate setup warning exposed by the split reuses the existing byte-identical tracked-report helper. This extraction warning and seven initial static type errors in newly written replay assertions are corrected implementation mistakes, not product RED claims. The entire pre-commit controller AST is unchanged. Three final projection modules have zero findings under the full unchanged production Pylint configuration:/private/tmp/specfact509-projection-module-green-final.json. Split collection224passes11.05seconds; no case/decorator/assertion is skipped or softened.

A separate read-only complete diff/new-module/consumer review finds no qualifying introduced defect:/private/tmp/specfact509-coverage-readonly-audit.md. Nine current Semgrep naming/architecture rows are independently invalid for descriptive test-name substrings and required native JSON/checker rejection/SMART interface output; protocol output and negative assertions stay. Other genuine full-surface KISS/Pylint warnings, sealed CrossHair unrecognized output and independent oversized/base incomplete evidence stay unwaived. Local capsule review remains owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS.

The correction changes only controller formatting, tests and spec/evidence. Runtime0.51.5bytes/checksum5d5663174cfc69d828c8f45b8e4c75bb721e6c4df7402b9add7033c20d79f1b1 and normal CIc65signature remain unchanged; all seven strict public-key signatures/checksums/dev-version gates pass against actual dev593656f6. No new signature or version is needed while0.51.5is unpublished. Native installed acceptance, protected main approvals/publication and alert11main closure remain separate; #460/OpenSpec stays open.


Final layout verification: Full and SMART each pass159required host/native proofs plus5744portable tests, with the existing71declared skips/95subtests/five warnings. Final Full portable148.82seconds; SMART148.71seconds. Full before the split also passed159+5744in169.93seconds and is historical for the final layout. Final format/type0errors-warnings/lint10.00of10/manifests/imports/strict OpenSpec/shell and all7strict public-key signatures/checksums/dev-version gates pass. Final immutable gates:/private/tmp/specfact509-coverage-full-final-layout.log,/private/tmp/specfact509-coverage-smart-final.log,/private/tmp/specfact509-coverage-lint-final.log,/private/tmp/specfact509-coverage-signatures-final.log. Fresh complete pagination still requires actual release integration before resolving its budget thread; current-head hosted checks/review are required after push.


## 11 October 2026 (Europe/Berlin): exact 9bbd dispatch-proof complexity correction

Exact candidate job114330590198/run38092135794 returns156 finite public locations (one error,132 warnings,23 info) and executed gate exit1. Strict timestamp/direct-JSON parsing excludes printed workflow source. The sole projected error is Radon CC16 at the actual Semgrep dispatch proof; no pytest finding is projected on this head. This removes the prior two coverage error locations from the projected current report, not an invented private percentage or complete-evidence waiver. CrossHair unrecognized output and five public counterexample locations remain unwaived; original private messages are unavailable. Native boundaries on macOS14/15/26 and the Linux canonical allocation proofs pass. Other current jobs are pending; no timeout classification is transferred.

Spec precedes expanding the existing pure production-policy regression to inspect its own test module. This yields one meaningful RED, precisely the reported Semgrep proof CC16, before any proof refactor:/private/tmp/specfact509-hb2257-complexity-red.log. Two bounded assertion helpers organize the exact managed argv/policy and private environment/budget groups. Every original assertion AST (88 total) and original test name/decorator is identical; actual replay, exact request binding, no host spawn, module restoration, private permissions and empty output remain. No runtime byte, analyzer input/deadline, production threshold, version or signature changes. Focused71 pass after implementation:/private/tmp/specfact509-hb2257-complexity-green.log. Type0errors/warnings, lint10.00/10, manifests/imports/strict OpenSpec and all7strict signatures pass; final Full/SMART and normal hook outcomes are recorded only after completion. Required public metadata is current: #460Todo with parent163, closed blocker459, labels and SpecFact CLI project; hierarchy cache refreshed.

Final Full passes159requiredhost/native+5744portable; portable149.01seconds,71existingdeclaredskips/95subtests/fiveexistingwarnings:/private/tmp/specfact509-hb2257-full.log. An initial SMART invocation mistakenly appended unsupported --force (the wrapper forwards arguments to pytest), so pytest rejected arguments with exit4 before portable collection. This is an invocation mistake, never product RED or a waived gate. The valid unchanged hatch run smart-test command is running; its actual outcome is recorded only after completion.

Valid SMART passes159requiredhost/native+5744portable, portable148.38seconds, with the same71declaredskips/95subtests/fiveexistingwarnings:/private/tmp/specfact509-hb2257-smart-final.log. Full portable149.01seconds. Contracts28pass3.90seconds; type0errors/warnings, lint10.00/10, format/YAML/import/strict OpenSpec and all7strict public-key signatures/checksums/dev-version gates pass. Complete separate read-only spec/test/consumer audit finds no qualifying introduced defect:/private/tmp/specfact509-hb2257-readonly-audit.md. No external review is retried; local capsule review remains owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS.

Read-only follow-up triage uses actual repository Pylint configuration on the new finite public warning locations:87of93public locations have exact local path/line matches; this is independent triage, not a sealed-quality waiver. Reports:/private/tmp/specfact509-hb2257-pylint-match-triage.json and /private/tmp/specfact509-hb2257-next-warning-families.json. The three imported broker cleanup test functions are demonstrably collected and pass in Full; their static unused reports do not justify removing the exports/tests. Other scoped line-length/module-length/import/KISS/contracts warnings remain unwaived and require correction or independent disposition. Existing signaturec65continues to authenticate unchanged runtime5d56; no version/signature refresh is needed for this test/spec-only correction. Current-head hosted review and non-exempt CI completion remain outstanding after push.


## 11 October 2026 (Europe/Berlin): preserve cleanup proof exports while clearing warning family

Scope is the authorized #509 native capsule warning triage. The exact current-source candidate job 114335991200/run 38093979743 executes and exits 1 with 154 public locations: zero errors, 132 warnings and 22 info. The previously fixed CC16 and pytest error locations are absent, which does not establish complete analyzer execution. CrossHair unrecognized output/incomplete contracts and five counterexample locations remain unwaived because private original messages are unavailable. Independent job 114335991211 executes an oversized_report diagnostic with incomplete contracts base/head and targeted pytest base; no verified executed timeout/exit 124 is attributed to either job. Each quality job 114340914183/114340914200/114340914262 fails at the customer prerequisite before tools/tests.

The export scenario was added before formal failing unchanged-policy evidence. Actual production Pylint over tests/unit/test_native_broker_cleanup.py and tests/unit/specfact_code_review/run/test_native_worker.py reproduces eight scoped findings: three redundant self aliases, three unused imported proofs and two long lines. An explicit zero-scoped-findings assertion fails with those exact eight rows. This is a quality-policy RED, not a claimed runtime failure. The minimal correction declares the same three imported proofs in __all__, removes only their self aliases, and formats the existing autouse fixture signature while retaining its existing type-checker annotation. No production runtime, signed manifest, workflow, deadline or assertion changes.

After correction, the same Pylint configuration has zero scoped export/line findings; other warnings remain unwaived. All 93 original assertion ASTs and every function name, argument and decorator match before/after. Collection trees contain the same 81 cases, including all three imported cleanup proofs, and all 81 execute successfully. Full passes 159 required host/native proofs plus 5,744 portable tests, portable time 154.06 seconds. SMART passes the same 159 plus 5,744, portable time 148.56 seconds. Both retain 71 declared skips, 95 passing subtests and five existing warnings. Required format, type, lint, YAML, imports, strict OpenSpec, 28 contracts and all seven strict public-key signatures/checksums/dev-version checks pass. Separate complete read-only diff/consumer review finds no qualifying introduced defect.

The local capsule stage remains owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS. Normal commit hooks are required without bypass. Runtime 7fec3580/checksum sha256:5d5663174cfc69d828c8f45b8e4c75bb721e6c4df7402b9add7033c20d79f1b1 retains the inspected normal CI c65a41e6 signature. Unpublished 0.51.5 is unchanged. CodeRabbit paused success is not current-head completion; no extra resume or review command was sent. All no-write, identity/ownership/source, complete-result and incomplete-evidence guarantees and original proof cases remain.

Logs: /private/tmp/specfact509-hb2329-export-quality-red.json, -pylint-green.json, -collection-before.log, -collection-after.log, -collection-identity-proof.json, -focused.log, -full.log, -smart.log, -format.log, -type.log, -lint.log, -yaml.log, -imports.log, -spec.log, -signatures.log, -contracts.log and -readonly-audit.md. Finite hosted logs: /private/tmp/specfact509-job-114335991200.log and /private/tmp/specfact509-job-114335991211.log. Preliminary system-Python missing-dependency, guarded edit-anchor and initial collection-parser mistakes were corrected before final evidence; none is asserted as a product RED. Automatic approval-review timeouts were retried once where permitted; they do not classify the patch as unsafe or waive any gate.


## 11 October 2026 (Europe/Berlin): complete complexity serialization and retained proof helpers

Scope is the authorized #509 native capsule warning family. Exact 201a candidate job 114344537444/run 38096884788 exits 1 with 146 finite public locations: zero errors, 124 warnings and 22 info. The previous eight-warning family is absent. No pytest error location is projected, which does not prove complete analyzer execution. CrossHair unrecognized output, incomplete contracts and five counterexample locations remain unwaived because private original messages are unavailable. Same-head independent job 114344537381 exits 1 with an executed oversized_report, incomplete contracts on base/head and targeted pytest on base; 200 side-unlabeled locations are retained. Neither job has verified executed analysis_timeout/exit 124. Logs: /private/tmp/specfact509-job-114344537444.log and /private/tmp/specfact509-job-114344537381.log.

The specification scenario precedes extending the existing production Radon regression to the failure-propagation and native snapshot proof modules. Initial top-level-only serialization yields a genuine CC13 quality RED but misses the nested callback. Production uses complete CLI serialization including closures; radon.cli.tools.cc_to_dict reproduces both actual CC13 and CC15 warnings before implementation. Log: /private/tmp/specfact509-hb0016-complete-complexity-red.log. Two bounded assertion helpers execute at the original successful paths. Exact failing counts/verdict/exit/report guidance, native argv/discovery/config roots and UNKNOWN fallback remain. All 257 original assertion ASTs and 77 original test definitions/arguments/decorators are identical; the two affected modules retain the same 94 collected cases. The complete production-policy regression becomes GREEN; focused 165 pass. No threshold, runtime byte, workflow, manifest, deadline, assertion or case changes.

An initial helper insertion briefly split a parametrization decorator stack; it was caught and corrected before test execution and is not a product RED claim. Radon was already required by the Hatch environment and authenticated capsule inventory; module-level imports avoid new local-import warnings. The regression now traverses actual nested closures instead of a top-level approximation.

Full passes 159 required host/native proofs in 20.53 seconds and 5,744 portable tests in 151.17 seconds. SMART passes the same 159 host/native in 19.44 seconds and 5,744 portable in 154.67 seconds. Both retain 71 declared skips, 95 passing subtests and five existing warnings. Logs: /private/tmp/specfact509-hb0016-full.log and -smart.log. Required format, type (zero errors/warnings), lint (10.00/10), YAML, imports, strict OpenSpec, 28 contracts and all seven strict public-key signatures/checksums/dev-version gates pass. The separate complete root-owned read-only diff/consumer audit finds no qualifying introduced defect; no delegation or external review retry.

Local capsule review stays owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS. Normal hooks remain required without bypass. Runtime 7fec3580/checksum sha256:5d5663174cfc69d828c8f45b8e4c75bb721e6c4df7402b9add7033c20d79f1b1 retains inspected normal CI c65a41e6 authentication; unpublished 0.51.5 needs no new version/signature for this test/spec-only correction. No extra CodeRabbit resume/review command was sent. Current incomplete evidence and remaining genuine scoped warnings remain unwaived; historical checks do not establish later-head or installed acceptance.

Evidence prefix: /private/tmp/specfact509-hb0016- (complete-complexity-red, complexity-green, assertion-identity, collection-proof, focused, full, smart, format, type, lint, yaml, imports, spec, signatures, contracts, readonly-audit).


## 11 October 2026 (Europe/Berlin): cached-diff parser warning with exact admission parity

Exact f2f9 candidate job 114349543401/run 38098561101 exits 1 with 141 finite public locations: zero errors, 120 warnings and 21 info. Previous CC13/CC15 proof warnings are absent. CrossHair still reports unrecognized output/incomplete contracts and five counterexample locations whose private original messages are unavailable; those and other genuine warnings remain UNWAIVED. No executed analysis_timeout/exit 124 is verified. Current independent job 114349543342 was still running when this correction started; no earlier oversized classification transfers to it. Log: /private/tmp/specfact509-job-114349543401.log.

The scenario precedes extending the complete production Radon regression to scripts/pre_commit_code_review.py. One genuine CC14 quality RED and ten passing admission controls precede implementation: /private/tmp/specfact509-hb0046-parser-red.log. A bounded helper retains the exact regex, integer conversions and default count, returns None on unavailable malformed hunks, and iterates an empty range for zero count. Existing header ordering, quoted destinations, deleted files, resets, accumulated identities and every admission branch remain. A return-type postcondition covers the helper. No analysis input/deadline, workflow, no-write, verdict, staged source binding or incomplete-evidence rule changes. Focused 125 pass after extraction.

All 131 original module assertion ASTs and 42 original test definitions/arguments/decorators remain; ten new admission controls are added. A bounded pure old/new parser comparison gives identical outputs for 41,371 combinations (0..4 lines from 14 header/hunk/content tokens). Actual pytest separately executes the decorated implementation paths. This supports unchanged semantics and is not an exhaustive input proof.

Full passes 159 required host/native proofs in 20.41 seconds plus 5,754 portable in 152.38 seconds. SMART passes 159 host/native in 18.36 seconds plus 5,754 portable in 152.72 seconds. Both retain 71 declared skips, 95 passing subtests and five existing warnings. Required format, type (zero errors/warnings), lint (10.00/10), YAML, imports, strict OpenSpec, 28 contracts and seven strict public-key signatures/checksums/version gates against actual origin/dev 593656f6 pass. An initial strict invocation omitted the public-key argument and failed for all seven; the corrected command supplies only tracked scripts/native_release/module-signing-public.pem and explicit --version-check-base origin/dev. This is an invocation mistake, not a product RED or waiver; no private key access.

Root-owned separate complete read-only diff/consumer audit finds no qualifying introduced defect, with no delegation or external review retry. Normal hooks remain required. The local capsule stage stays owner-approved DEFERRED to mandatory exact-head Linux CI, never PASS. Runtime bundle 7fec3580/checksum sha256:5d5663174cfc69d828c8f45b8e4c75bb721e6c4df7402b9add7033c20d79f1b1 retains inspected normal CI c65a41e6 authentication. Only the pre-commit script, tests and spec/evidence change; unpublished 0.51.5 needs no new version/signature. Paused CodeRabbit success still covers historical 9bbd, never current-head completion. No extra resume/review command was sent. Hosted/installed acceptance and remaining genuine warnings/incomplete evidence stay outstanding.

Evidence prefix: /private/tmp/specfact509-hb0046- (hierarchy, spec-before, parser-red, parser-green, parser-parity, identity, format, type, lint, yaml, imports, spec, strict-signatures-dev, contracts, full, smart, readonly-audit).
