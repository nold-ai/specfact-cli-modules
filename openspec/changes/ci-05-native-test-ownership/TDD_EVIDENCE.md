# TDD evidence

20 October 2026 (Europe/Berlin). This is a specification and RED-only checkpoint against HEAD `22306331d8c9fb88440170856ef83ad5d17182a0`. No producer, partition, runtime adapter, physical execution, native build, package installation, Git mutation or native acceptance was performed.

## Ordered evidence

The specification and bounded CHANGE_ORDER entry were written first and `openspec validate ci-05-native-test-ownership --strict` passed before new tests were authored. Original files and full function ASTs were captured before new tests. Genuine pytest collection of the original unit owner produced 34 items at R1 (25 portable + 9 physical) and 727 at R100 (25 portable + 702 physical). Both fixture path environment variables were explicitly unset. Collection did not run physical calls or establish admitted fixtures.

One authoritative corpus at `tests/fixtures/native-execution-proof/corpus.json` records exact original collected case names and function ASTs. Only empty type_params fields absent from Python 3.11 are normalized for cross-ABI comparisons; raw Python 3.12 ASTs remain in the evidence archive. Original function/decorator/guard/parameter logic is not changed. Full tracked baseline covers 2,824 files, plus original index, native C sources and selected source snapshots.

## Actual RED and controls

`tests/unit/native_release/test_physical_proof_ownership.py` produced **5 failed, 3 passed**, zero skipped and zero errors. The final run is `ownership-red-final.xml` with raw stdout/stderr and exact command/environment in `ownership-red-final.run.json` under `/private/tmp/ci521-native-ownership-red`.

Observed failures are: zero definitions in the missing explicit owner against seven frozen definitions; all seven physical functions still selected through the unit owner; unconditional runtime calls only `['delivered_boundary', '_review_candidate']`; REQUIRED_CHECKS lacks native_execution; and the corpus fixture, original unit owner and capsule-proof-context test paths do not schedule native acceptance. These are predicted assertions about actual current source/selector output, not missing imports or setup failures.

Separately, unchanged `test_full_and_smart_host_runs_require_the_retained_host_proof` failed once before new tests on its old single-owner literal. `baseline-host.xml` preserves that preexisting failure; it is not attributed to this checkpoint. Existing portable/PID controls produced **84 passed, 9 deselected**, zero skipped/errors, in `preserved-controls.xml`. New preservation controls verify portable ASTs, actual shared PID alias/frozen bytes, and the unchanged nine-cell/60-minute matrix.

## Commands and environment

All pytest runs used the prepared worktree `.venv/bin/python`, Python 3.12.13, pytest 9.1.1 and xdist 3.8.0, `-p xdist.plugin -o addopts= -n 0 -p no:cacheprovider`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, and `PYTHONDONTWRITEBYTECODE=1`. Installed specfact-cli distribution is 0.55.10; actual imported source paths/hashes are recorded separately from distribution versions. No fake SDK or copied production AST execution was used. `run.py` retains exact argv/environment, raw outputs and JUnit for replay with a fresh run label.

Strict OpenSpec validation, scoped Ruff check/format and git diff whitespace checks passed. Native Requirements import returned all eight actual requirement identities without findings; `_source_mapping_findings` and schema-v2 `evaluate_mapping(required_maturity="planned")` passed. Scenario IDs equal the actual native adapter requirement suffixes. Structural selectors are authored, while fixture/result/cleanup cases are explicitly planned. No runtimeRequirements maturity, whole-change RED maturity or native acceptance is claimed.

## Remaining proof obligations

Five structural RED observations prevent losing tests or merely renaming them without a required acceptance call/check. They do not prove result parsing, real signed inputs, cleanup, artifact retention or the future adapter's behavior. Functional exact-result and process-group cleanup tests remain planned until that owner exists. The three physical refusal controls (missing stall, stock-as-stall, mutated delivered bytes), first 702-case cell and all nine existing cells remain unproved. Full repository quality/review/signature/customer gates remain pending under root authority.

The selected design now states engineering ceilings of 1,200 seconds for pytest, 120 seconds for fixture build, and two five-second terminate/kill cleanup intervals. This implements no timeout and establishes no measured feasibility; existing production deadlines and the 60-minute cell limit remain unchanged.

The final evidence report, source snapshots, actual failure extracts, process-cleanup observation and SHA-256 manifest are in `/private/tmp/ci521-native-ownership-red/REPORT.md`. Root must independently accept RED before any implementation handoff. No archive, commit, push or CI request belongs to this checkpoint.
