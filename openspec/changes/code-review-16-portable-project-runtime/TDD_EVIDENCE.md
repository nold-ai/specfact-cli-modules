# TDD evidence

Implementation begins from dev 976460c0541b685f5fae256faef4cec32fe9ba7e on 2026-09-14 (Europe/Berlin). The original customer reproduction is inaccessible. Historical runs and subsequent external execution evidence are recorded below. Record each mapped failing-before run before its production changes and passing-after evidence below.

## Discovery — failing before production changes

`hatch run pytest -q tests/unit/specfact_code_review/run/test_runtime_discovery.py` failed collection with `ModuleNotFoundError: specfact_code_review.run.runtime_discovery` (12 cases planned). No discovery production implementation existed. Output retained in DISCOVERY_RED.txt.

## Discovery passing / artifacts failing

Discovery: 12 passed in 0.10s. Runtime artifact/adapter tests failed collection before production changes: ModuleNotFoundError runtime_artifacts. See ARTIFACTS_RED.txt.

## Artifact passing / builder failing

18 discovery/artifact/adapter tests passed in 0.11s. Builder/source-copy tests fail before implementation with ModuleNotFoundError runtime_builder; see BUILDER_RED.txt. Builder versions verified against PyPI JSON on 2026-09-14: pip 26.2.1, uv 0.12.13, Hatch 1.18.0, Poetry 2.4.3.

## Worker and CLI failing before integration

Worker tests fail collection for missing portable_worker. All three CLI tests fail: missing runtime command, missing handoff options, and rejected project_config/project_runtime kwargs. See WORKER_RED.txt and CLI_RED.txt.

## Snapshot integration failing

Seven CLI/worker tests pass; automatic snapshot attachment fails before production integration with missing portable_snapshot. See SNAPSHOT_RED.txt.

## Immutable pair failing

Independent pair test fails for missing run_project_scope_pair; two other snapshot tests pass. Existing command/runner/sandbox/tool regressions: 511 passed, 14 failed. Failures identify accidental ScopeRequest option forwarding and legacy mocked runtimes entering the newly added preparation boundary. Preserve original legacy assertions and isolate their new dependency boundary.

## Runtime hardening and real external preparation

Additional failing-before artifacts cover pytest configuration precedence and execution/coverage evidence; changed local workspace source; safe internal symlinks; explicit dependency groups; customer Actions source layouts; worker PID/mount isolation; worker identity attachment; native library inventory; credential-free dependency inventory; native Git builder support; analyzer/project dependency conflicts; and dependency-only immutable ranges. Each corresponding `*_RED.txt` was captured before retaining its implementation.

On 2026-09-14, 49 portable-runtime/corpus unit tests passed in 0.31 seconds; the subsequently added worker identity and compatibility scenarios passed separately. Scope plus portable snapshot regressions passed 130 tests in 9.90 seconds. Formatting, typing, lint, manifest/YAML validation, bundle import checks, development checksum/version checks, and strict OpenSpec validation passed before the first full-suite run.

The first complete suite reported 1,972 passed and 22 failed in 75.63 seconds. Five failures were caused by the existing paired core checkout being 0.54.0, below this bundle's already-declared >=0.55.1 requirement. Fifteen Semgrep cases could not load macOS trust anchors. Two failures identified missing command documentation/generated command artifacts. Verification now uses a separate checkout of public core 0.55.4 at d5799705, an explicit certificate bundle, and regenerated documentation; rerun evidence follows.

Real non-root Ubuntu 24.04 x86-64/Python 3.12 preparation succeeded for all four exact pinned upstream repositories: Requests/pip, Hatch/hatch-test, Flask/uv, and Poetry/test. The controller used public core 0.55.4 and the signed 0.49.85 base, with this worktree's development preparation implementation. This is acquisition/bootstrap evidence, not updated signed analyzer or release acceptance. Hatch first exposed missing Git and then its newer glibc requirement; Git now runs with its own private loader/library closure, leaving the supervisor's runtime unchanged.

The dedicated worktree was moved to `/private/tmp/specfact-473-worktree` after automatic approval-service timeouts on edits outside writable roots. Branch identity and all uncommitted changes were preserved; the main dev checkout remains untouched.

## Review-driven corrections and current delivery boundary

The corrected core/certificate/documentation baseline passed 1,994 tests in 95.74 seconds; smart tests passed the same 1,994 tests and contracts passed 28 tests (1,966 deselected). Subsequent review-driven changes require fresh evidence and do not inherit those passing claims.

The active worktree is now `/private/tmp/specfact-473-implementation`, with writable Git metadata in `/private/tmp/specfact-473-git.git`, the same feature branch and base, and canonical pre-commit hooks installed. Its task-owned development virtualenv symlink is locally excluded from Git. The user checkout remains untouched.

Additional failing-before artifacts record native Python CLI handoff and fail-closed startup, in-repository parent requirements includes, verified active environment selection, exact signed-interpreter patch constraints, and complete external analyzer-roster validation. Grouped adapter/CLI/worker tests were split into corresponding module test files; historical failing transcripts retain their original filenames.

A fresh bug-hunt review exposed an invalid development-only BasedPyright command combining `--venvpath` and `--pythonpath`. That report is not passing analyzer evidence. A real BasedPyright subprocess regression now verifies the corrected `--pythonpath` invocation and dependency imports (9 focused command tests passed). The later full run found 16 failures: foreign Hatch activation, four test observers still reading parameters moved into snapshot settings, and five worktree-identity tests rejecting the task's untracked virtualenv symlink. Discovery now verifies the active environment belongs to the reviewed root; observers inspect the equivalent settings fields; local Git exclusion fixes the task environment without relaxing source identity rules. Runner/discovery verification passed 424 tests in 12.63 seconds after these corrections.

Open acceptance work remains: full updated capsule execution across all twelve Linux corpus combinations, the labelled reconstructed Hatch/native fixture, member-specific dependency closure isolation, interpreter selection across differing base/head constraints, complete preparation/cache failure cases, and published signed installation acceptance. Successful preparation of four cp312 environments does not satisfy these criteria. This change must remain open and any initial PR must remain draft until acceptance and review are complete; #472 additionally requires access to and validation of the original customer reproduction.

Latest local full run on 2026-09-14: `hatch run test` with public core 0.55.4 and the explicit CA bundle passed **2,008 tests in 81.90 seconds**, with two pre-existing lark deprecation warnings. Contract tests passed **28 tests**, with 1,980 deselected. Formatting and typing passed. Formal development verification passed with `--payload-from-filesystem --enforce-version-bump --allow-missing-public-key --version-check-base refs/remotes/origin/dev`, matching the canonical branch-aware hook; this is not a release-signature claim.

Smart-test verification subsequently passed **2,008 tests in 82.95 seconds**. The development virtualenv lacked CrossHair, causing the review tool to discover a globally installed executable using a different interpreter. Installed the capsule-pinned `crosshair-tool==0.0.109` into the task-owned virtualenv; fresh review must be rerun with that environment. Earlier advisory reports containing the CrossHair import error are not complete passing analyzer evidence.

The staged-snapshot pytest failure was isolated to `test_github_candidate_context_failure_never_uses_stale_official_payload`: it depended on the caller checkout containing `.git`. The test now constructs its own publisher-checkout fixture and preserves the original fail-closed assertions. Recorded failing transcripts are normalized only for trailing whitespace; their outcomes and diagnostics are unchanged.


### Follow-up from candidate Linux evidence (2026-09-14)

- Signed branch head `6499136806637c6c2075ea44c857e0b90a8fb301`, PR orchestrator run `34839312884`: existing capsule namespace/cold/warm/controlled-defect fixtures completed as expected on Python 3.11/3.12/3.13. Python 3.12 Requests external acceptance passed; Hatch analysis remained incomplete. Original customer reproduction remains inaccessible and unvalidated.
- The Hatch adapter incorrectly supplied global `-e` to native `env create/find`, which take a positional name. The host command reported `Unknown environment: hatch-test` and the former harness accepted exit 1 without test inventory. These were implementation defects, not evidence of customer compatibility.
- `HATCH_EXECUTION_RED.txt`, `HATCH_NATIVE_EXPORT_RED.txt`, `EXECUTABLE_INVENTORY_RED.txt`, and `OFFLINE_PLUGIN_RED.txt` record failures before fixes. Native exports now select the concrete ABI environment; artifacts retain owned scripts/native executables; host acceptance requires actual JUnit test execution; setup/collection/internal errors remain observable. Local Linux preparation selected `hatch-test.py3.12`; execution exposed missing localhost resolution in pytest-rerunfailures, addressed with private hosts configuration inside the offline namespace.
- `MEMBER_CLOSURE_RED.txt`, `MEMBER_IMPORT_DOMAIN_RED.txt`, `NATIVE_LOADER_RED.txt`, and `NATIVE_WORKER_LAUNCH_RED.txt` precede member-specific sealed import graphs and target native loader/libc isolation. Unit checks do not substitute for Linux acceptance.
- `RECONSTRUCTION_RED.txt` and `CORPUS_CONTINUATION_RED.txt` precede the labelled detached Hatch/src-layout/asyncio/requests/pyodbc fixture and continuation across failed corpus entries. Any failed entry still fails the gate.
- `VCS_VERSION_RED.txt`, `VCS_SNAPSHOT_RED.txt`, and `PYTHON_SELECTION_RED.txt` precede Git version/cache binding and signed target Python selection independent from the controller.
- Follow-up full run: 2011 passes and 15 Semgrep failures when the task's required SSL_CERT_FILE was omitted. Rerun with the established certificate bundle is required; that failed run is not passing evidence.


### Passing follow-up evidence (2026-09-14)

- Local full and smart suites: 2032 passed, two existing lark deprecation warnings, 100.91s and 99.93s respectively. Contract suite: 28 passed. Formatting, typing, lint (10.00/10), YAML, import boundaries, strict OpenSpec, planned Requirements mapping, and development checksum/version verification passed before review refinements.
- Actual local Linux x86-64/non-root/Python 3.12 component runs: pinned Hatch `hatch-test.py3.12` collected/executed all five selected tests, exit 0; labelled detached reconstruction executed its asyncio/requests/pyodbc test, exit 0. Source and artifacts remained in private task storage. These use signed baseline Python with development worker components and are **not signed release acceptance**.
- `HATCH_INSTALLER_DOMAIN_RED.txt` records the pip-backed detached failure before manager-specific environment controls were separated. Upstream Hatch's uv installer was unaffected; the reconstruction was essential to expose pip redirection.
- Fresh SpecFact bug-hunt review identified a preparation complexity regression and long review function; refactoring passed 411 focused tests. Targeted pytest instrumentation subsequently recorded 1058 passes; a fresh review is required after the fixes.


- Instrumenting the actual review subprocess (not a separately invoked test suite) revealed 30 worktree-test failures caused by inherited `SPECFACT_CODE_REVIEW_CHANGED_DIFF=cached`. `NESTED_SCOPE_RED.txt` precedes removal of that controller-only setting from child pytest environments. The controller setting remains intact, and tests may explicitly set their own scope.


- Fresh SpecFact `--bug-hunt` after nested scope isolation: exit 0, no error findings, 43.54s. Lint/type/format recheck passed (10.00/10). Warning-level review work remains before final acceptance, including explicit standard-library bootstrap contract exceptions and snapshot argument grouping. The PR remains a draft and no release acceptance is claimed.


- The first follow-up commit attempt was stopped by canonical hooks. A new VCS fixture inherited the hook's GIT_INDEX_FILE and staged its temporary app.py into the calling index. No commit was created. The fixture-only staged artifact was removed; `HOOK_INDEX_ISOLATION_RED.txt` records regression failures before sanitizing both fixture Git processes and the child pytest environment. Source changes were retained.

## PR #474 feedback and second candidate matrix

The signed candidate `b8f762551430566b9fc2f9a03eb5ca83e2f97ad9` failed all three ABI jobs in run 34845391063. All four upstream cold reviews reached analysis. Pylint could not map its bundled checker files to modules because its sealed dependency closure was exposed only by an import finder. Poetry additionally failed xdist startup because nested Python lost its private coverage destination. The reconstructed Hatch host baseline duplicated the explicitly loaded asyncio plugin under its entry-point alias. These are failures, not completed acceptance.

The follow-up introduces a real read-only member package directory, preserves pytest child-domain/coverage settings and native Hatch extra arguments, and records the host baseline's explicit `-p no:asyncio` alias suppression while retaining `-p pytest_asyncio.plugin`. The host command and justification are checked into the corpus manifest. No upstream source or pytest selection is changed.

Local Ubuntu 24.04 x86-64 non-root cp312 component observations (not signed candidate or release acceptance): Hatch 5 tests, Flask 19 tests, Poetry 7 tests with unchanged `-n logical`, and reconstructed Hatch 1 test including pyodbc all executed successfully. Pylint separately completed with exit 0 on the Hatch slice after the member-directory fix. The reconstructed native-manager host baseline now executes successfully. The preceding full local suite passed 2046 tests in 105.67 seconds (two existing lark warnings); later review fixes require a fresh suite.

PR findings have failing-before regressions in `PR_REVIEW_474_ROUND1_RED.txt`, `PR_REVIEW_474_ROUND2_RED.txt`, `SOURCE_LINK_EXCLUSIONS_RED.txt`, and the specific option/evidence transcripts. Transcript machine paths have been replaced with stable placeholders; test assertions and observed outcomes are preserved. Every `*RED.txt` is historical failing-before evidence, not a current acceptance gate. In particular, `NATIVE_RED.txt` does not claim the module remains absent. Native Linux candidate and public-release acceptance remain mandatory and incomplete.

PR follow-up verification: full local suite passed **2066 tests in 101.72 seconds**, with two existing lark warnings. The subsequent focused command/scope/descriptor/source/startup regression set passed **238 tests in 11.36 seconds**; the source-link compatibility subset passed **36 tests**. The second fresh `--bug-hunt` review completed in 43.94 seconds after refactoring the four initially reported blockers. Warning cleanup and external acceptance remain open; development checksum verification does not substitute for release signing.

## Complete signed candidate and subsequent review refinements

Signed candidate `790c39eb47b89046f6525cce9f7345f746896706`, Actions run [34850206113](https://github.com/nold-ai/specfact-cli-modules/actions/runs/34850206113), passed the customer capsule jobs on Python 3.11, 3.12 and 3.13. All four pinned upstream repositories and the reconstructed Hatch/native fixture completed applicable analysis with unchanged source. Initial collected/executed test counts were Requests 24, Hatch 5, Flask 19, Poetry 7, and reconstruction 1 per ABI. Real findings remain visible; acceptance does not require zero findings. This is signed candidate evidence, not public release acceptance.

Subsequent local refinements cover pip-tools/pylock inputs, setup.cfg Python constraints, group/extra ambiguity, complete permission-mode source identity, required member dependency closure, private analyzer source copies, index VCS context, pytest collection/internal errors, inventory argument shape, and native ELF architecture. Failing-before transcripts are `PIP_METADATA_SELECTION_RED.txt`, `MEMBER_CLOSURE_RED.txt`, `ANALYSIS_EXCLUSIONS_RED.txt`, and `PR_REVIEW_474_ROUND3_RED.txt`. Local full verification passed **2,085 tests in 102.51 seconds** with two existing lark warnings; targeted PR regressions passed 53 tests. Type checking and lint passed after the corpus additions. These refinements need a new signed candidate matrix.

The initial warm corpus requested offline reuse without independently denying host networking. `OFFLINE_CORPUS_RED.txt` records the stronger harness requirements and a controlled-report naming regression. The corrected harness passes 11 unit tests and uses administrator-provisioned Bubblewrap solely to deny external networking around warm customer commands. A child probe verifies non-root execution, a distinct network namespace and no active non-loopback interfaces. This test harness does not grant capsule or protected PR authority. `CORPUS_TRANSFER_RED.txt` covers host-interface byte counters, explicitly labelled as host-wide measurements.

Windows/macOS automatic worker handoff and platform-native test support remain outside the accepted Linux x86-64 execution scope. Metadata discovery must not be presented as cross-platform execution acceptance. The original customer reproduction remains required before closing #472.

The stronger network wrapper was exercised on the non-root Linux component host: the child ran as UID 1001 in a distinct network namespace with no active non-loopback interface. The strict member closure also prepared the reconstructed Hatch environment and executed its native-extension test successfully (pytest 9.1.1, pytest-cov 7.1.0). This remains component evidence; the updated customer-interface candidate matrix is still required. Requirements evidence passed at the repository-required `planned` maturity; it does not claim implementation-verification maturity. Narrow review exceptions are enumerated in `REVIEW_EXCEPTIONS.md`.

Final local gate pass before the next candidate push: full tests **2,087 passed in 100.79 seconds**; smart tests **2,087 passed in 101.22 seconds**; contracts **28 passed, 2,059 deselected**. Format, type-check, lint, YAML, bundle imports, development signature/version checks, strict OpenSpec, planned Requirements evidence, and canonical publish pre-check passed. Core compatibility remains intentionally `>=0.55.1,<1.0.0`; the signed candidate's minimum-core checks passed on all three ABIs.

Fresh branch-wide SpecFact review with `--enforcement changed --bug-hunt` completed at 2026-09-14 16:33:01 Europe/Berlin in **49.14 seconds**: **zero errors**, 285 warnings and 69 informational findings. Actionable new mechanical/complexity findings were fixed. Boundary-specific exceptions and unchanged baseline findings are documented in `REVIEW_EXCEPTIONS.md`; coverage limits remain explicit and conditional on Linux acceptance. The preceding review's failing stale-observation mock was fixed at its actual imported launch boundary, and the full suite then passed.

The independent offline wrapper additionally needed a private `/dev`: the Linux user namespace could not open the bind-mounted host `/dev/null`, so GitPython failed before runtime discovery. `OFFLINE_DEVICES_RED.txt` records this failure. Adding `--dev /dev` restored `git --version` inside the non-root offline namespace, and all 11 corpus harness tests passed. Complete warm preparation/attachment remains an updated signed-CI acceptance gate; the local command-level correction alone is not that acceptance.

## PR #474 review rounds 4 and 5 (2026-09-14)

`PR_REVIEW_474_ROUND4_RED.txt` records eight failures before honoring pytest's autoload-disable control, binding directory presence/modes, detecting pylock/requirements.in ambiguity, converting malformed INI to a runtime diagnostic, and protecting the offline launcher's ownership and identity. Focused validation passed 74 tests; the then-current full suite passed 2,101 tests in 103.07 seconds. The Linux UID-1001 offline wrapper executed Git successfully; overwriting the root-owned launcher raised PermissionError.

Candidate `6eda1a0c950a09417dd563371799e08b14cef856`, run [34857677581](https://github.com/nold-ai/specfact-cli-modules/actions/runs/34857677581), failed all corpus ABI jobs. The downloaded cp312 reports identify repository-relative paths being passed to `relative_to(absolute_root)` during private source mapping. `RELATIVE_SELECTION_RED.txt` records one failing and nine passing tests before the mapping fix; afterward all ten passed, including rejection of escaping selections. Quality jobs failed their required capsule prerequisite, not a separate lint/type gate. This failure remains historical evidence; a new signed candidate run is required.

`PR_REVIEW_474_ROUND5_RED.txt` records failures before adding the builder's Git exec path and enforcing selected worker dependency versions. Git's HTTP/HTTPS transport helpers now carry their native library closure, and their bytes enter cache identity. This follows Git's [exec-path contract](https://git-scm.com/docs/git) and [remote-helper contract](https://git-scm.com/docs/gitremote-helpers), accessed 2026-09-14. An actual non-root Ubuntu 24.04 x86-64 builder executed `git ls-remote https://github.com/psf/requests.git HEAD`, exit 0, returning the pinned Requests revision `dae7ef63b4df6eded86637f251fc4e3a06c3b479`. This is transport component evidence, not signed release acceptance. The focused builder, transport and dependency-domain suite passed 24 tests.

An intermediate full suite overlapped the addition of new failing-first tests and a source mutation: 3 failed, 2,104 passed. An earlier accidentally unscoped test invocation omitted the established SSL certificate bundle and also failed. Neither is final passing evidence. The subsequent stable full/smart suites and fresh review are recorded below.

Stable round-5 validation: full suite **2,109 passed in 90.20 seconds**, smart suite **2,109 passed in 101.43 seconds**, and contracts **28 passed**. Both large suites retain two existing lark deprecation warnings. Type/lint (10.00/10), format, YAML, import boundaries, strict OpenSpec, planned Requirements evidence, the generated command overview, 118 module command-contract paths, and three CLI contract scenarios passed. A final transport-identity postcondition was then checked by its focused tests.

Final fresh branch-wide SpecFact `--enforcement changed --bug-hunt` review completed on **2026-09-14 at 17:21:15 Europe/Berlin**, in **41.62 seconds**. The initial review caught the corpus root identity's optional value type; the type refinement and two test assertion warnings were corrected. The final focused harness/pytest/transport set passed **26 tests in 0.54 seconds**. The final review has **zero errors**, with existing/boundary warnings covered by `REVIEW_EXCEPTIONS.md`. Development checksum/version verification and the canonical publish pre-check passed; core compatibility was intentionally retained. Updated signed candidate and public-release acceptance remain required.

## PR #474 review round 6 (2026-09-14)

`PR_REVIEW_474_ROUND6_RED.txt` records seven failures before excluding Git history from analyzer source copies, preserving pytest's repository-root default when `testpaths` is absent/empty, and converting Git identity probe failures into actionable runtime diagnostics. The Git source-copy regression uses a real committed repository and asserts that the analyzer mount has no `.git`, while existing build-copy tests still verify sanitized VCS state and uncommitted source modifications. Parameterized tests cover missing/empty pytest roots and failed/timed-out/unavailable Git probes. The focused set subsequently passed **23 tests**. This follow-up still requires a new signed candidate run; earlier component/candidate receipts are not evidence for the updated artifact.

Signed candidate `dcc30b46fd7477200b55b5f07292963d62012be7`, run [34861791235](https://github.com/nold-ai/specfact-cli-modules/actions/runs/34861791235), failed the updated corpus. Downloaded cp311/cp312 receipts identify two causes: the hosted runner's writable `/opt` ancestor was rejected by the offline launcher, and Hatch's pytest exited 4 while importing its legitimate `hatch.venv` package. The latter was reproduced in the real non-root Linux private-source worker: `ModuleNotFoundError: No module named 'hatch.venv'`. The common-name `venv` exclusion had removed `src/hatch/venv` from both build and analyzer copies.

`HOSTED_RUNNER_ANCESTOR_RED.txt` precedes relocating the administrator-provisioned launcher directly under `/specfact-corpus-offline`, with all ownership, ancestor and digest checks retained. Actual Linux UID-1001 execution passed the relocated wrapper's network probe and Git command; replacement remained denied. `SOURCE_VENV_PACKAGE_RED.txt` precedes recognizing actual virtual environments by `pyvenv.cfg`, retaining ordinary `venv` packages and rejecting aliases into custom-named environments. The source/copy/corpus regression set passed **55 tests**. Source and test selection were not patched in the upstream Hatch checkout.

The corrected private Linux Hatch worker executed all five selected tests successfully with unchanged `--dist worksteal`, pytest 9.1.1, coverage 7.16.1 and pytest-cov 7.1.0. Runtime descriptor identity at that component observation was `603ad4ff2fb113e1f56b9ca355dc6c0bbbf3ad83ad308fa82ab5ca6754dd46fa`. This is component evidence, not signed candidate acceptance. Both local full/smart suites then passed **2,119 tests** (87.95s/88.02s).

`ENVIRONMENT_TEST_SELECTION_RED.txt` additionally records three failures before pruning actual environments from repository-root test candidate traversal. Installed dependency tests no longer create false ambiguity for a customer's root-level test file. The focused worker/source set passed **18 tests**. Fresh preliminary SpecFact review found no errors and one new line-length advisory, which was corrected before final verification.

Final round-6 validation: full suite **2,122 passed in 87.74 seconds**, smart suite **2,122 passed in 87.53 seconds**, contracts **28 passed**. Format, type/lint (10.00/10), YAML, bundle imports, development checksum/version verification, strict OpenSpec and planned Requirements evidence passed. Fresh branch-wide SpecFact `--enforcement changed --bug-hunt` completed at **2026-09-14 18:00:01 Europe/Berlin**, in **41.66 seconds**, with **zero errors**. The narrow advisory exceptions remain documented; no current signed-candidate or public-release acceptance is claimed.
