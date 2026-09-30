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
