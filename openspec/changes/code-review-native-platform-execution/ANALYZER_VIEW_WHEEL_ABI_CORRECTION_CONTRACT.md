# Analyzer view and wheel ABI correction contract

Scoped #460 correction, 2026-10-05 (Europe/Berlin). This file owns the contract
and TDD evidence for these two corrections; the shared evidence ledger remains
parent-owned.

## Analyzer payload view

The controller calls `build_analyzer_view` for Pylint, CrossHair and pytest with
the verified capsule site and the selected member's dependency graph. The view
SHALL contain only present RECORD members owned by the graph's analyzer-origin
distributions at their exact versions. Project-origin distributions and
unrecorded files SHALL NOT enter the analyzer fallback view.

Candidate preparation (`scripts/macos_managed_boundary/python_analyzers.py`,
`copy_site`) retains the upstream installed RECORD but intentionally omits:

- `.pyc`, `.pyo`, `.dll` and `.exe` files;
- `semgrep/bin/` entries other than `semgrep/bin/semgrep-core` and
  `semgrep/bin/libs/` members;
- `z3/lib/libz3.5.1.dylib`, after verifying identical canonical library bytes.

The view MAY skip absent entries only in those exact categories. The omitted Z3
alias SHALL require the recorded canonical `z3/lib/libz3.dylib` in the selected
view. Every other recorded code, library, metadata or data file SHALL remain
mandatory. Symlink/parent indirection, duplicate ownership, changed bytes,
hard links, destination collisions and file/byte bounds SHALL retain their
existing rejection behavior. An omission SHALL NOT admit unrecorded bytes or
weaken member distribution/dependency identity checks.

RECORD SHALL be read directly rather than relying on `Distribution.files` to
enumerate mandatory entries. The focused controller environment uses CPython
3.14.7, whose `Distribution.files` filters missing paths (including dangling
links); older supported metadata implementations retain those entries. Neither
version-dependent missing-file filtering nor arbitrary missing-file fallback is
an admission rule. Tests SHALL exercise both behaviors without changing payload
selection or invoking a capsule proof.

Scenarios: a retained pip RECORD with missing bytecode stages its present source
and metadata; the other explicit preparation omissions behave identically;
missing source, canonical Z3 libraries, selected Semgrep engine/libraries and
metadata reject before a view is created; unrecorded injection is excluded and
symlinked or multiply owned recorded bytes reject.

## Complete wheel compatibility

Authenticated wheel preparation SHALL validate the complete interpreter/ABI
pair against the selected standard CPython ABI (`cp311`, `cp312`, or `cp313`).
An exact interpreter match SHALL NOT bypass ABI validation. The explicitly
selected interpreter and ABI SHALL determine compatibility, never the
controller's Python build or native ABI.

Platform-independent wheels require a matching interpreter or `py3` and ABI
`none`. macOS ARM64/universal2 wheels require a compatible full CPython pair or
`py3-none`, plus the existing host macOS minimum-version check. Stable `abi3`
wheels permit CPython interpreter tags from Python 3.2 through the selected
minor. Newer interpreter tags, mismatched CPython ABIs, free-threaded/debug ABIs,
`abi3t`, pre-3.2 stable tags and noncanonical tags SHALL reject before output
creation. Valid exact-ABI, ABI-independent and compatible stable-ABI wheels
SHALL continue to prepare successfully.

Scenarios: authenticated `cp313-cp313t` and `cp313-cp312` macOS wheels reject;
future/pre-stable/free-threaded stable tags reject; compatible exact and stable
pairs for each supported ABI preserve the wheel payload bytes.

## Scope and evidence limits

Implementation owns only `native_analyzer_view.py`, `native_project_manager.py`
and their two unit test files. Focused tests, formatting, lint and type checks
are required. No policy, signatures, assembly, shared proof, production catalog,
staging, commits, publication or customer support authority changes are included.
Physical capsule proof and independent final closure remain parent-owned.

## TDD evidence

The contract above was recorded before adding regression tests or modifying
production code. Failing-before and passing-after facts will be appended here.

Initial focused RED, before production edits: the two test files collected 125
cases, with **25 failed, 100 passed in 0.50 s**. Sixteen ABI rejection cases
incorrectly prepared complete output. Nine view rejection cases incorrectly
accepted missing required members, an unrecorded Z3 replacement or a dangling
bytecode link under CPython 3.14's missing-file filter. The older metadata path
will be reproduced explicitly before production edits.

Supported older metadata behavior RED: the single
`test_retained_pip_bytecode_record_works_with_unfiltered_metadata` case failed in
0.16 s with `native analyzer recorded payload is missing` for the absent pip
bytecode entry, while its source and metadata were present. This run preceded
both production fixes.

The first implementation passed **126 cases in 0.47 s**. A subsequent narrow
boundary check added directory/FIFO rejection for a bytecode-looking RECORD
path, and the hidden `.pyc` filename case to match preparation's exact suffix
test. Before that refinement, the selected tests reported **3 failed, 8 passed,
16 deselected in 0.18 s**. The refinement permits only absent omitted files;
present nonregular objects still reject before destination creation.

Final GREEN command:

```sh
hatch run pytest -q \
  tests/unit/specfact_code_review/run/test_native_analyzer_view.py \
  tests/unit/specfact_code_review/run/test_native_project_manager.py \
  tests/unit/specfact_code_review/run/test_native_tool_worker.py::test_native_domain_uses_project_dependency_and_denies_unrelated_analyzer_fallback \
  --tb=short
```

Result: **130 passed in 0.69 s**, exit 0, on CPython 3.14.7 / pytest 9.1.1.
The two owned test files contribute 129 cases; the remaining existing caller
regression verifies that the staged member view preserves the project dependency,
selects the sealed analyzer entry and rejects unrelated analyzer fallback.
Its file was exercised read-only and was not edited.

Focused quality checks, all on the two production files and two owned test files:

```sh
hatch run ruff check \
  packages/specfact-code-review/src/specfact_code_review/run/native_analyzer_view.py \
  packages/specfact-code-review/src/specfact_code_review/run/native_project_manager.py \
  tests/unit/specfact_code_review/run/test_native_analyzer_view.py \
  tests/unit/specfact_code_review/run/test_native_project_manager.py
hatch run ruff format --check \
  packages/specfact-code-review/src/specfact_code_review/run/native_analyzer_view.py \
  packages/specfact-code-review/src/specfact_code_review/run/native_project_manager.py \
  tests/unit/specfact_code_review/run/test_native_analyzer_view.py \
  tests/unit/specfact_code_review/run/test_native_project_manager.py
hatch run basedpyright \
  packages/specfact-code-review/src/specfact_code_review/run/native_analyzer_view.py \
  packages/specfact-code-review/src/specfact_code_review/run/native_project_manager.py \
  tests/unit/specfact_code_review/run/test_native_analyzer_view.py \
  tests/unit/specfact_code_review/run/test_native_project_manager.py
```

Results: Ruff checks passed; four files already formatted; BasedPyright reported
**0 errors, 0 warnings, 0 notes**. No formatter mutation or type suppression was
needed.

Implementation reads the raw RECORD independently of the host metadata filter
and uses `packaging.tags.cpython_tags` with explicit version, standard ABI and
platform inputs. Native macOS architecture/minimum-version checks and the
platform-independent `none` restriction remain in force. The omission predicate
mirrors only the existing preparation exclusions; a future new exclusion needs
an explicit contract/test update rather than a permissive missing-file rule.

Limits: these are focused unit and caller checks. No physical capsule was
rebuilt/refreshed, no shared proof was executed, and no full quality gate or
independent final review is claimed. Parent integration and Erdos closure remain
required. Shared staged state and unrelated worker edits were preserved; this
task staged no files and used no signing keys.
