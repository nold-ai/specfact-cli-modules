# Quality fixture identity evidence

Recorded 2026-10-16, Europe/Berlin. Branch `codex/ci-fixture-identities`, base `593656f675eaf4954b609aca51aa6504367dc02e`.

## Specification before tests

Created the proposal, design, tasks and `quality-fixture-identities` delta before adding regression tests. The change is bounded to workflow input selection, tests and evidence. No package source, runtime verifier, manifest, registry, dependency declaration or policy was edited.

## Failing before workflow edits

Command `.venv/bin/python -m pytest tests/unit/workflows/test_paired_core_ref_trust.py -o addopts= -q` produced **14 failed, 3 passed in 0.22s**. Local raw output is `/private/tmp/ci518-workflow-red.log`.

The existing full-suite step had no baseline environment override. The reader assertion reported `quality job does not read the paired core smoke lock`; the verifier assertion reported `quality job does not authenticate a separate smoke fixture`. The actual smoke command still passed `${GITHUB_WORKSPACE}` instead of the reviewed fixture path. This result was sent to the parent before editing the workflow.

The parent separately ran the unchanged declared dependency test with paired core 0.55.10. `.audit/ci518-original-core-red.log` records **1 failed in 0.27s**, with `assert '==0.55.4' == '==0.55.10'`. The original paired-core smoke verifier rejected the candidate modules checkout with `RuntimeError: Smoke fixture identity does not match the reviewed commit` and accepted the exact reviewed fixture.

## Passing after workflow repair

The focused workflow suite produced **17 passed in 1.32s** after the first repair. The full workflow test directory produced **52 passed in 1.48s**. Tests execute the workflow's Bash/Python chunks on disposable Git repositories; they reject wrong commit, wrong tree, staged dirt, untracked dirt, malformed JSON, wrong repository, missing identity, wrong identity format and a non-object lock.

Review then identified that candidate formatting could traverse new historical checkouts. The spec was extended before changing the tests. `/private/tmp/ci518-fixture-isolation-red.log` records **2 failed, 15 passed in 1.34s** before moving smoke to runner temporary storage and delaying baseline checkout until after candidate gates. The success case verifies the moved checkout's commit and clean status. After this repair, the full workflow directory passed again with **52 passed in 1.30s** in `/private/tmp/ci518-workflows-green.log`.

`openspec validate ci-03-quality-fixture-identities --strict` passed. Focused Ruff lint passed; Ruff format corrected only the new tests' layout. Final Ruff format check and `git diff --check` passed. Canonical `evaluate_mapping(..., required_maturity="planned")` and `_source_mapping_findings` both returned empty findings for the new sidecar. This validates mapping structure and native source reconciliation without claiming runtime lifecycle promotion.

## Runtime evidence and limits

The parent ran all six real smoke launchers with paired core and immutable modules fixture `046d366c190af7a188d6f48953a96edb65e766db`, tree `c5b44db3477d1c9ea8dae1dceab2af276d265353`. `.audit/ci518-installed-smoke.log` contains successful direct, hatch-source, pip-editable, pipx, uv-run and uvx results. This is local Darwin Python 3.12 evidence, not hosted Linux acceptance.

The unchanged original declared dependency test passed with the exact baseline core 0.55.4, **1 passed in 0.37s**, recorded by the parent in `.audit/ci518-original-core-green.log`. The parent selected it through the unchanged `dev-deps` path.

## Final local gates

The unchanged `SPECFACT_CLI_REPO=/private/tmp/specfact-ci518-core-baseline hatch run test` completed with **5689 passed, 71 skipped, 5 warnings and 95 subtests passed in 192.36s**. Existing platform-specific skip conditions were retained. `hatch run contract-test` passed 28 tests. The required smart-test entrypoint also passed 5689 tests, retaining the same 71 skips and 95 subtests. Paired core 0.55.10 separately passed lint, generated command overview and all 118 generated command path contracts. Format, type-check, lint, manifest validation, bundle import checks and `actionlint` passed. Signature verification passed with the paired core repository's public key after the initial fresh-worktree probe reported its missing key. No module was re-signed or versioned.

Independent read-only review found no code blocker. It identified stale scenario path wording and an omitted fixture-isolation decision in the local trail. Both were corrected. Requirement mappings now bind baseline selection to implementation task 2.1 and smoke preparation to task 2.2.

The required native SpecFact review on Darwin ARM64 Python 3.12 returned `assurance_status=UNKNOWN`, exit 1 and `native_capsule_artifact_not_admitted:darwin-arm64-cp312` for all required analyzers. Zero findings does not mean success. A bounded attempt ran the unchanged review in an existing Linux x86-64 development image with source and Git metadata mounted read-only. It returned `official_installed_module_missing`. A separate preparation installed the official signed reviewer 0.51.2 with no host mounts. Its public-only baseline probe returned `UNKNOWN` with `pre_namespace_host_object:/usr/bin/rosetta-wrapper` and `project_runtime_required`. That probe is not candidate review evidence. The local capsule gate therefore remains incomplete. An unapplied proposal to align the existing maintainer-approved local-to-CI deferral with the orchestrator trigger awaits explicit owner approval. Hosted quality acceptance remains required. No review waiver, dependency relaxation or gate weakening has been applied.

Requirements mappings identify actual selectors; they do not manufacture accepted or verified lifecycle evidence. Archive only after merge.

## Normal staged hook attempt

The unmodified `hatch run pre-commit run` passed signature verification, all four Block 1 stages, generated command overview and contracts, core documentation accountability, docs command validation and staged Requirements evidence. Block 2 then failed the required native capsule review with `assurance_status=UNKNOWN`, exit 1 and zero findings. Its contract stage did not execute because `fail_fast` remains enabled; the separate 28-test contract run above passed. No hook was skipped, no report was relabeled PASS, and the maintenance change remains uncommitted while the explicit local-only deferral decision is pending.

## Approved local deferral regression, 2026-10-18

The maintainer explicitly approved the exact orchestrator eligibility addition on 2026-10-18 (Europe/Berlin), with all checks intact and mandatory hosted review before merge. The proposal, design and spec were extended before tests. Native review remains UNKNOWN; local deferral must report DEFERRED, never PASS.

The first fixture attempt used workflow and Markdown changes only and reached the existing safe-only Block 2 skip. The next added the actual Python-test trigger but still asserted prompt validation for a candidate with no prompt paths. Both probe logs are retained under `.audit`; neither is counted as the decisive reproduction. Package candidates retain their original prompt-validation assertion.

Before the script edit, `.venv/bin/python -m pytest tests/unit/test_capsule_deferred_review_ci.py -k narrow_local_deferral -o addopts= -q` produced **2 failed, 15 passed, 12 deselected in 2.80s**. `.audit/ci518-deferral-red-final.log` records both `orchestrator-only` and `orchestrator-advanced-dev` failing `assert 1 == 0` with `Capsule review deferral requires a candidate change that schedules the blocking capsule workflow.` All existing and new rejection cases passed. The real shell hook executes against disposable Git worktrees and indexes; Hatch tasks are recorded by the established fixture, so this proves hook control flow, not successful native or hosted analyzers.

### Maintained regression target and final local verification

The normal `hatch run test` entrypoint explicitly runs `tests/host/proof_capsule_deferred_review_ci.py` and excludes the legacy unit file above. At parent review, the nine new cases moved to that maintained host proof and its existing shared fixture; the legacy unit file was restored byte-for-byte to HEAD. The fixture now accepts an explicit candidate path and stages a Python prompt-check regression path so every existing Block 2 assertion remains exercised. No legacy assertion or normal test selection changed.

Before restoring the one-line path addition, the final maintained test command `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py -k narrow_local_deferral -o addopts= -q` produced **2 failed, 15 passed, 19 deselected in 3.27s**. `.audit/ci518-deferral-host-red-final.log` records the same two `assert 1 == 0` eligibility rejections. After the exact approved path addition, `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py tests/unit/workflows -o addopts= -q` produced **88 passed in 9.84s**, recorded in `.audit/ci518-deferral-maintained-green.log`. This includes all maintained exact-head and independent-review host proofs, all 17 eligibility cases and the existing workflow regressions.

An exploratory run that explicitly included the normally excluded legacy unit file produced 6 failed and 102 passed. The same six failed against committed HEAD's original unit source, with only its temporary snapshot's REPO_ROOT adjusted to this worktree, producing 6 failed and 14 deselected in 2.15s. Four legacy fixture CLI modules lack the current `app` entrypoint; two fixtures assert the obsolete reviewer version 0.50.1. The raw comparison is `.audit/ci518-deferral-existing-failures.log`. These are not failures of the maintained target, and the legacy source and normal selection remain unchanged.

Strict OpenSpec validation passed. The exact staged requirements hook, with its normal PYTHONPATH and summary destination, passed at `planned` maturity with one source passed and zero failed. Implementation evidence remains `not-yet-available`; no lifecycle promotion is claimed. Earlier manual invocations omitted the hook's import paths and summary argument, and a subsequent mapping run rejected scenario identifiers until they were aligned with the existing canonical requirement-slug convention. Logs remain local. Focused Ruff lint/format, shell syntax and staged whitespace checks pass.

Source snapshot self-review confirms the script diff is exactly the approved one-line path addition. The existing opt-in, CI, platform, architecture, feature-worktree, indexed-review, merge-base guards and DEFERRED warning remain byte-identical. The orchestrator still schedules the existing reusable capsule workflow for this path; its blocking exact-head and independent review jobs are unchanged. No module payload or version is touched. Self-review is not an independent verdict or a native/hosted PASS. The parent owns independent review, normal hooks, signed publication and mandatory exact-head hosted completion before merge. No new full-suite run was needed for this narrow addition; the prior 5689-pass result remains historical evidence.

## Final local review and normal hooks, 2026-10-18

An independent read-only reviewer inspected the final 12-file staged diff and
the actual RED/GREEN logs. No actionable source finding remained. The review
confirmed that the new cases run in the maintained host target and the ignored
legacy unit file remains unchanged.

The complete normal staged hooks passed with the owner-approved local Darwin
deferral and the paired core environment. Signature verification, formatting,
YAML lint, import boundaries, lint, planned Requirements evidence and all 28
contract tests passed. The local capsule review reported `DEFERRED`, explicitly
not PASS. Required exact-head blocking Linux candidate and independent signed
review remain outstanding hosted acceptance before merge.

Command: `SPECFACT_CLI_REPO=<paired-core-worktree>
SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux hatch run pre-commit run`.
The actual output is retained locally in `.audit/ci518-approved-normal-hooks.log`.
No runtime/package payload, dependency declaration, version assertion, module
signature, or review workflow was changed. No hosted acceptance is claimed.

## PR 519 indexed scheduling regression, 2026-10-18

Review thread `PRRT_kwDORVEFbs6tuM23`, comment `4308606986`, reported that the local path-only eligibility guard could defer review after staged orchestration disabled the hosted capsule schedule. The source requirement was extended first within the existing all-checks-intact authorization. The maintained fixture then replaced placeholder orchestrator text with actual workflow YAML. No production hook or validator edits preceded the RED run.

The command `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py -k 'broken_indexed_orchestrator or narrow_local_deferral' -o addopts= -q` produced **64 failed, 17 passed, 19 deselected in 15.73s**. Every new rejection case instead returned zero and printed `DEFERRED: only the local capsule review requires mandatory exact-head GitHub Linux CI; this is not a PASS.` The decisive assertion was `assert 0 == 1`. `.audit/ci519-scheduling-red.log` records the run. The 64 cases cover 16 routing mutations, each for an orchestrator and capsule-payload candidate, with and without an unstaged restoration. They include a removed filter entry or output, disabled filter, removed or disabled caller, wrong caller target or needs, nonblocking caller, excluded PR trigger, missing quality dependency, disabled or nonblocking quality job, and removed, disabled, nonblocking or replaced prerequisite. All 17 existing eligibility cases still passed.

The hook now runs `scripts/validate_capsule_ci_schedule.py` before DEFERRED. The validator reads only the indexed orchestrator and compares parsed routing against the documented supported contract. It also parses the nested filter YAML. The existing platform, architecture, CI, opt-in, feature-worktree, indexed reusable-review, merge-base and candidate-path guards remain unchanged. The fixture executes the actual validator while retaining the original Block 2 command-trace assertions. The new rejection cases assert the validator diagnostic as well as the absence of DEFERRED.

The first focused GREEN produced **81 passed, 19 deselected in 17.65s**, recorded in `.audit/ci519-scheduling-green.log`. After final assertion and fixture cleanup, `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py tests/unit/workflows -o addopts= -q` produced **152 passed in 25.04s**, recorded in `.audit/ci519-scheduling-maintained-green.log`. This includes all maintained host proofs and workflow regressions. It proves local hook behavior against real Git indexes; it does not establish native or hosted analyzer success.

Focused Ruff check and format check passed for the validator, maintained host proof and shared fixture. Focused basedpyright returned zero errors, warnings and notes. Shell syntax and staged whitespace checks passed. A direct focused Pylint invocation reported four existing import-placement diagnostics in the host proof and one existing long fixture string. Committed HEAD evaluated through Pylint's `--from-stdin` produced the same diagnostics and exit 16 for each affected baseline file; `.audit/ci519-scheduling-pylint-baseline.log` records that comparison. The newly introduced fixture-local count warning was fixed. No clean Pylint baseline or warning waiver is claimed. Parent normal gates retain authority.

`openspec validate ci-03-quality-fixture-identities --strict` passed. The actual staged adapter command `PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --staged --required-maturity planned --output .audit/ci519-scheduling-requirements.json --summary .audit/ci519-scheduling-requirements.md` passed with one source passed and zero failed. The report retains observed maturity `planned` and implementation evidence `not-yet-available`; no lifecycle promotion is claimed.

The closed routing contract deliberately rejects unsupported routing edits until reviewed. It does not evaluate arbitrary Actions expressions or certify hosted execution. No CI workflow, reusable workflow, package, dependency declaration, manifest, signature or version changed in this correction. Mandatory exact-head Linux candidate and independent signed review remain required before merge. The parent owns independent source review, normal staged hooks, publication and hosted acceptance. This worker made no commit, push or public comment.


## PR 519 inherited workflow defaults regression, 2026-10-18

Independent review found that workflow-level run defaults were outside the indexed routing comparison. A shell default of `bash -c "exit 0" {0}` could suppress the changes job output while the matching job text remained unchanged. The supported contract now explicitly excludes workflow-level defaults. The spec was updated before adding shell and working-directory mutations to the maintained rejection table, with both candidate paths and indexed/unstaged-restoration variants.

Before editing the validator, `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py -k workflow-default -o addopts= -q` produced **8 failed, 100 deselected in 2.48s**. Each case returned zero instead of the required rejection, with `assert 0 == 1`. `.audit/ci519-defaults-red.log` records the actual RED run.

The validator now rejects the presence of the workflow-level `defaults` key before comparing routing jobs. No override evaluator or new function boundary was introduced. After this two-line guard, `.venv/bin/python -m pytest tests/host/proof_capsule_deferred_review_ci.py tests/unit/workflows -o addopts= -q` produced **160 passed in 27.35s**, recorded in `.audit/ci519-defaults-green.log`. The same test selector in the existing Requirements mapping covers the eight additional variants. This proves local hook rejection through real Git indexes, including unstaged restoration, and does not claim hosted or native analyzer PASS.

Focused Ruff check and format check passed for the validator, maintained host proof and shared fixture. Focused basedpyright returned zero errors, warnings and notes. Strict OpenSpec validation passed. Parent review, normal staged hooks, signed publication and exact-head hosted acceptance remain required.

The staged native Requirements adapter also passed with one source passed and zero failed using `PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --staged --required-maturity planned --output .audit/ci519-defaults-requirements.json --summary .audit/ci519-defaults-requirements.md`. Observed maturity remains `planned` and implementation evidence remains `not-yet-available`. Staged whitespace validation passed.


## 2026-10-18 closed byte contract and mandatory host proofs

The reviewed `59b1c048` orchestrator blob independently hashes to
`827e26667ef9951783bfeaffebca5833e1e16a90151676b164b88d303f7ac371` using
`git show 59b1c048:.github/workflows/pr-orchestrator.yml | shasum -a 256`.
The spec was extended before tests, then the existing partial parser was tested
before replacement. The focused RED run recorded **21 failed and 2 passed** in
`.audit/ci519-bytepin-red.log`. Failures comprised sixteen quality-container,
root-env, job-env and runner variants across both candidate paths and restoration
states, four byte/comment changes, and the missing mandatory host schedule.
The two missing-index-file variants already passed and are not claimed as new RED.
Earlier recorded routing/default mutations remain retained.

After replacing the parser with a literal digest over raw indexed bytes, the
maintained host review proof, twelve relocated host identity cases and paired
workflow unit file passed **148 tests** in `.audit/ci519-bytepin-green.log`.
The workflow directory plus new host file passed **53 tests**. After splitting
fixture setup and assertions to preserve the complexity gate, all **12 host
identity cases** passed again. Radon reports maximum complexity 9 in the new host
file and 10 in the shared fixture module. The long fixture string was split into
adjacent literals without changing its generated content.

The standard `hatch run lint` passed (format, types, Ruff and Pylint 10.00/10),
`hatch run type-check` reported zero errors/warnings, and strict OpenSpec validation
passed. An additional explicit Pylint invocation over the maintained host proof
reported its four pre-existing function-local imports; the new unit-local import
was moved to the module boundary. No suppression rule was added. Final focused
Ruff checks pass. Host Bash ownership follows the existing host proof pattern;
no capsule capability, namespace, policy, dependency or workflow changed.
Public hosted records redact private tracebacks, so they alone do not prove the
specific executable responsible for FileNotFoundError. Hosted exact-head review
and full-suite acceptance remain outstanding after this local verification.


The actual staged command `PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --staged --required-maturity planned --output .audit/ci519-bytepin-requirements.json --summary .audit/ci519-bytepin-requirements.md`
passed with one source passed and zero failed. Observed maturity remains `planned`
and implementation evidence `not-yet-available`. Final standard lint passed after
helper extraction, and staged whitespace validation passed. No commit or push was
performed by the delegate; independent review and normal hooks remain parent-owned.


## 2026-10-18 native schedule validator coverage

The existing native coverage policy selected `src`, `packages` and `tools`.
`target_coverage._reviewer_sources` preserves configured coverage sources, while
`runner._portable_coverage_sources` selects the changed schedule script as
production code. Adding seven unit cases alone passed all seven cases but left
the script absent from actual pytest-cov JSON. Feeding that JSON to
`evaluate_portable_pytest_coverage` reproduced the exact error
`Coverage data missing for scripts/validate_capsule_ci_schedule.py`.
This is failing coverage evidence, not a fabricated failing behavior test.

After specifying the coverage requirement, the coverage source list gained only
`scripts.validate_capsule_ci_schedule`. The tests import that qualified module
and exercise the real entrypoint through `runpy`, mocking only the external Git
read. Actual `pytest --cov --cov-report=json:... --cov-fail-under=0` measurement
reported 18 of 18 statements and four of four branches covered, with no excluded
lines. The existing portable adapter returned no findings for that JSON under
its unchanged per-source threshold. The local measurement command disables the
aggregate gate only for this focused seven-case probe; repository thresholds
and exclusions remain unchanged. This does not claim hosted capsule acceptance.

The CLI refusal text and newline are preserved using `sys.stderr.write`.
An actual Semgrep scan identified `print-in-src`; actual Pylint identified
`line-too-long` at 121 characters. Both are resolved without suppressions.
The existing fixture tuples remain the data shape. Natural assertion, baseline
file setup and schedule mutation helpers remove the parameter-count, complexity
and long-function findings without introducing fixture models. Function-local
imports in the host proof moved to module scope; generated bootstrap fixture
imports and their lazy-import behavior remain intact.

Before refactoring, the maintained files passed 148 cases. Afterward, the same
files plus the seven new cases and two split assertion tests passed 157 cases.
All twelve host identity cases remain included. Explicit Pylint, Ruff,
BasedPyright, Radon and AI-bloat checks passed for all six touched Python files.
Semgrep scanned those six files with twelve rules and reported zero findings.
Strict OpenSpec validation passed. Local logs are retained under
`.audit/ci519-coverage-*`; audit files are not staged. Parent independent review,
normal hooks and exact-head hosted acceptance remain outstanding.

The staged Requirements evidence gate passed with one source passed and zero
failed after aligning the new mapping with its requirement-level scenario id.
Required and observed maturity remain `planned`; implementation evidence remains
`not-yet-available`. Staged whitespace validation also passed.


## 2026-10-18 structured independent failure diagnostics

The subject is PR 519 at `413f8f1211222eb7d2a15d530d86f8423234adff`.
Run 39167860375 identifies contracts as the only error and UNKNOWN analyzer in
the independent structured report. The actual contract fault remains unknown.
The public artifact contains no failed-review report. The observed diagnostic
gap is that the existing side and class projection ran only for oversized reports.

After the spec update and before production edits,
`.venv/bin/python -m pytest tests/unit/test_capsule_review_projection.py -k 'structured_contract_failure or independent_review_failure_keeps' -o addopts= -q`
returned **9 failed, 6 passed, 216 deselected in 0.65s**. The decisive new assertion
failed with `KeyError: 'error_analyzer_sides'`. Existing structured golden outputs
also rejected the two missing additive fields. Malformed and duplicate-key cases
passed before the correction.

The production diff adds structured reports to the existing diagnostic condition
and reads classes from the already validated `evidence_source`. The complete
projector file then passed **231 tests in 11.57s** using
`.venv/bin/python -m pytest tests/unit/test_capsule_review_projection.py -o addopts= -q`.
The new cases cover error and UNKNOWN-only sides, unrelated tools and categories,
unknown messages, malformed and duplicate JSON, and private token/path/argument
canaries. Existing oversized and diagnostic-bound cases also pass.

Focused Ruff lint and format, strict OpenSpec validation and whitespace checks
pass. The indexed orchestrator SHA-256 remains
`827e26667ef9951783bfeaffebca5833e1e16a90151676b164b88d303f7ac371`.
No classifier, validation, input bound, raw-output handling, review exit, timeout,
required check, runtime or signed payload changed. Requirements mappings remain
planned test mappings and do not claim accepted or verified lifecycle evidence.
The staged native Requirements command passed with one source passed and zero
failed. Required and observed maturity remain `planned`, and implementation
evidence remains `not-yet-available`.

`SPECFACT_CLI_REPO=/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/code-review-local-report-planning SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux hatch run pre-commit run`
completed with exit 0. Signature verification, formatting, YAML validation,
bundle imports, full lint, generated command and documentation checks, staged
Requirements evidence and all 28 contract tests passed. BasedPyright reported
zero errors and warnings; Pylint reported 10.00/10. Only the local capsule review
reported the existing explicit DEFERRED warning. That is not analyzer PASS.
The existing reusable-workflow eligibility path and the indexed orchestrator
byte pin were unchanged. Parent independent review and exact-head hosted
acceptance remain required.

Durable RED and GREEN logs are retained under
`/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/ci518-review-artifacts/ci519-structured-diagnostic/`.


## 2026-10-19 caller-selected immutable local policy

PR review 4308833955 identified that the local hook executed candidate-owned checker code, allowing changed indexed workflow bytes and a matching candidate digest update to authorize deferral. The approved correction preserves the trusted local caller as the approval boundary. The caller explicitly selects a full policy commit SHA and an external absolute host Python executable; this is not owner acceptance, protected-branch policy or hostile-caller isolation. Candidate hook/control changes and exact-head Linux candidate and independent signed review remain independently blocking.

The spec was updated before host regression tests and production edits. With the original hook and a test-only Hatch adapter executing the candidate checker, `.venv/bin/python -m pytest tests/host/proof_quality_fixture_identities.py -k immutable_policy -o addopts= -q` produced **16 failed, 2 passed, 12 deselected in 4.02s**. The candidate-pin case returned zero with `DEFERRED: only the local capsule review requires mandatory exact-head GitHub Linux CI; this is not a PASS.` instead of the required refusal. Candidate canaries, absent selections and Git/Python failure injections also exposed the old invocation. The final replacement fixture uses a parentless replacement commit, avoiding an ancestry cycle that would otherwise stop at the existing merge-base guard rather than test immutable extraction.

The production change adds one private subshell function and replaces the old Hatch checker call. It validates caller inputs, reads the exact commit blob with Git replacements disabled, runs the nonempty extracted checker using `-I -S` from the candidate repository root, and cleans its private temporary directory. The checker itself remains blob `ec30685c4755e4d0f78faf3bc88fe292b022fb79`, SHA-256 `2d8e4b4f5e0200c4293fa1a98c2daa44c6be4e82849bdc2a423b9fce82c7602d`; its orchestrator digest remains unchanged.

All **18 immutable-policy host cases passed** after the fix. The final combined host, pre-commit parity, seven unchanged validator unit cases and preserved diagnostic suite passed **414 tests in 50.15s**. The command selected `tests/host/proof_quality_fixture_identities.py`, `tests/host/proof_capsule_deferred_review_ci.py`, `tests/unit/test_pre_commit_quality_parity.py`, `tests/unit/test_validate_capsule_ci_schedule.py`, and `tests/unit/test_capsule_review_projection.py` with `-o addopts= -q`. Tests use real disposable Git indexes and an external base interpreter, exercise changed indexed bytes despite restored working copies, reject invalid/missing/non-commit/empty policy selections and Git/Python failures, ignore replacement objects and candidate Python imports, and preserve contracts plus temporary cleanup. The test-only Hatch checker adapter is removed after the failing-before run.

Focused Ruff format/lint, Pylint (10.00/10 for the three host/support files), BasedPyright (zero errors/warnings), Bash syntax and strict OpenSpec validation passed. Native staged Requirements validation against a private temporary index passed one source with zero failures, required and observed maturity `planned`, and implementation evidence `not-yet-available`. The earlier branch-diff probe reported no impact and is not counted as mapping evidence. Normal hooks, parent independent review and hosted exact-head acceptance remain to be completed.

Durable RED/GREEN logs and the preserved original eight-file staged patch are retained under `/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/ci518-review-artifacts/ci519-immutable-policy/`. No commit, push, API write or lifecycle promotion is included in this handoff.

The normal hook command completed with exit zero using `SPECFACT_CLI_REPO=/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/code-review-local-report-planning`, `SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux`, `SPECFACT_CODE_REVIEW_POLICY_COMMIT=413f8f1211222eb7d2a15d530d86f8423234adff` and `SPECFACT_CODE_REVIEW_POLICY_PYTHON=/opt/homebrew/bin/python3` with `hatch run pre-commit run`. Signature verification, format, YAML, bundle boundaries, full lint, generated command and documentation checks, staged planned Requirements evidence and **28 contract tests** passed. Only the existing local capsule review reported DEFERRED, never analyzer PASS. Parent independent review and mandatory hosted exact-head acceptance remain outstanding.


## 2026-10-19 external interpreter boundary

Review 4311300796 reproduced a gap in the caller-selected interpreter boundary. Absolute and executable did not imply external. A candidate launcher could exit zero without evaluating the immutable checker and yield DEFERRED despite changed indexed orchestration. Review 4311315724 also identified the inconsistent CHANGE_ORDER exclusion of all policy changes. The scope paragraph now identifies these guards as safeguards for the already approved local deferral, without new policy authority.

The spec preceded tests and production edits. The six added host cases produced **5 failed, 1 passed, 30 deselected in 1.88s** against the old hook. Direct candidate `.venv/bin/python`, an external symlink into it, a parent-directory symlink, and a checkout alias all incorrectly returned DEFERRED. A candidate-local symlink to the external host interpreter was also accepted. The legitimate external host symlink case passed. Executable canaries use exact quoted marker paths.

The minimal shell correction resolves the physical repository and interpreter parent and uses native `realpath` for the target before executing any selected interpreter. Either location inside the candidate repository refuses eligibility; the resolved external target executes with the existing isolated flags. All **36 host cases passed in 6.19s**. The combined host, deferral, parity, validator and diagnostic proof command passed **420 tests in 47.95s** with `-o addopts= -q`, selecting the same five files as the preceding immutable-policy evidence.

Focused Ruff lint and format with `--no-cache`, BasedPyright with zero errors or warnings, Bash syntax, whitespace and strict OpenSpec validation passed. The initial cached Ruff invocation was filesystem-sandbox blocked; the uncached checks completed successfully. Native planned Requirements validation against a disposable private index passed with required and observed maturity `planned`, implementation evidence `not-yet-available`. The real index was not staged. Existing reviewed pins, thresholds, runtime, dependencies, signed payloads and workflows are unchanged. Parent independent review, normal hooks and hosted exact-head acceptance remain outstanding.

Raw RED, focused GREEN, combined GREEN and native Requirements evidence are under `/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/ci518-review-artifacts/ci519-python-boundary/`. This is trusted-local-caller protection. Caller hook edits and hostile concurrent filesystem replacement remain outside that boundary. No commit, push, API write, lifecycle promotion or runtime repair is included.


## Projection host boundary planning (2026-10-19)

Current-head local failure reproduction is `/private/tmp/ci519-no-bash-proof.log`: 31 failed, 200 deselected, each with FileNotFoundError naming Bash. Hosted output only establishes FileNotFoundError, not its private filename. The repair retains mandatory execution in the existing host stage and fixes measured fixture-quality defects. Independent exact-head analysis_timeout remains a separate unresolved gate.

### Projection partition verification (2026-10-19)

This retained pre-publication evidence covers the fixture partition published in signed commit `816c8277e524904c03cfe6c5cbb54a7b73565c43`, whose parent is signed commit `2edcefd5c88a7e5d79b16572d4001fb5efa4032d`. The pending statements below describe that pre-publication checkpoint. Independent review and normal hooks subsequently passed for `816c8277e524904c03cfe6c5cbb54a7b73565c43`; hosted acceptance still requires the current head and is not established by those local results.

The added schedule assertion failed before the Hatch command changed because `proof_capsule_review_projection.py` was absent from its mandatory host stage. The four shell functions, fixture and interpreter helper were first moved with exact AST equality. Subsequent cleanup removed redundant imports, named the registered fixture separately from its argument, exported the shared preparation builder, and extracted existing fixture construction and assertion groups. These changes retain all original assertion ASTs, all 38 test functions, every decorator and all 231 parameter-case identities. Collection now consists of 31 host cases and 200 ordinary unit cases split by private-report and public-diagnostic behavior. The split also removes the actual module-length warning without excluding either file from analysis.

Focused projection execution passed all 231 cases. The combined three mandatory host proofs, both projection unit files and pre-commit parity regression file passed 413 tests. All 200 unit cases passed with PATH containing Git but no Bash. This is a local capability-boundary proof, not a hosted traceback diagnosis or Linux acceptance.

Actual repository analyzer adapters were executed under Python 3.12.13, Pylint 4.0.7 and native `pyproject.toml` configuration. Each of the four resulting fixture files returns zero Pylint findings when checked separately. Radon and AST clean-code adapters return no findings over all four files. The former complexity 24 and 16 functions are now below the warning threshold; no thresholds or exclusions changed. BasedPyright reports zero errors and warnings. Ruff lint/format, strict OpenSpec and native planned Requirements validation pass. Requirements used a disposable private index; the real index was not staged. Observed maturity remains `planned` and implementation evidence `not-yet-available`.

Joint Pylint reports two R0801 data-sequence matches also present before this partition: a literal expected public Radon record versus its independent input fixture, and shared metadata in distinct structured-Semgrep and decoder-depth stimuli. These contain data, not duplicated executable behavior. Deriving expected output from its input would weaken the regression; the independent literals remain. The parity AST warning at line 201 normalizes differing string constants and therefore conflates two regressions: a single added `+++` content line expects lines 10 and 11, whereas forged paired header content across two hunks expects lines 2 and 10. Both distinct stimuli and exact assertions remain unchanged. No suppressions, waivers or analyzer changes were added; these observations are supplied for parent review, not represented as a clean joint analyzer report.

Durable commands, original source, collection lists, move and final AST proofs, raw analyzer reports and local test logs are in `ci518-review-artifacts/ci519-projection-host` in the parent review workspace. Parent independent review, normal hooks and hosted exact-head acceptance remain pending. The independent hosted analysis_timeout remains unresolved. No local result establishes that this fixture partition resolves that timeout.


### Portable interpreter resolution, initial reproduction (2026-10-19)

Against signed source head `ec93af1d441d66be9299059144ca0f0b7666ee09`, root executed the actual full-hook disposable-Git fixture with the same reviewed index and legitimate external host interpreter. The control returned zero with DEFERRED. Overriding only realpath to return command-unavailable status 127 made the hook return one with its existing path-resolution refusal. This isolates the accidental utility dependency; it is not a native macOS 11/12 run or a new passing capsule review.

Three model sketches and an independent cross-judge selected one private Bash/readlink resolver, with path bytes preserved throughout capture and both original exclusions retained. No source implementation has been written at this checkpoint. The specification precedes the new regression definitions. Actual regression RED, implementation GREEN and publication evidence must be added separately when observed.

Durable root reproduction, candidates, cross-judge primitive evidence and selected contract are in `ci518-review-artifacts/ci519-portable-host-path` in the parent review workspace. Core's 89-test owner decision remains pending; planning PRs #517 and #770 and core source remain unchanged.


The additive host regression segment produced **14 failed, 9 passed, 36 deselected** against unchanged hook blob `954748f6ae4d608109051fd745b9269d4a48ec57`. All 14 failures are intended positive-flow assertions: realpath is genuinely absent from the private whitelist PATH, both Python lookup and Bash command lookup confirm absence, and the hook returns one instead of zero. No fixture setup or collection error is counted as RED. The nine negative controls already refuse on the old fail-closed source; they do not establish correctness of the later replacement resolver.

All 36 original host cases passed before the additive tests were written. AST comparison preserves their functions, decorators, parameters and assertions. Scoped Ruff, formatting, BasedPyright and Pylint pass for the authored test segment. Darwin fixtures select native `/bin/bash` 3.2. The encoded Linux 40-link case has not been executed on this Darwin host; no Linux or native macOS 11/12 acceptance is claimed. Raw RED JUnit/logs, selectors, preservation proof and handoff are retained under `ci519-portable-host-path/red-tests`.

At this checkpoint only tests and change artifacts are authored; production hook source remains unchanged. The test/spec segment must pass normal governance hooks and be signed locally before the resolver implementation is added. Hosted acceptance and implementation GREEN remain pending.

The test/spec checkpoint is signed local commit `f24bd2a1d5133f0cb2b3facef22be36a43a071b2`, tree `498061a91a20a6ea471efde99a7a766c06613bf7`, parent `ec93af1d441d66be9299059144ca0f0b7666ee09`. Signature verification reports Good signature with approved primary key `690E0906488957C08B45D601D90AAF92921066C1`. The checkpoint contains only the additive host tests and six change artifacts. It precedes production edits and remains unpublished until the reviewed fix wave is ready.

Fresh independent review approved the exact seven-file checkpoint and found no comment or correctness issue. Root independently parsed the 23-case RED JUnit and compared every original function AST. The actual staged native Requirements gate passes at planned maturity with one passed source and zero failed sources. Strict OpenSpec and all normal hooks pass, including 28 executed contract cases. The capsule review alone remains explicitly DEFERRED under the approved local exception. Initial manual commands omitted the normal module import path or used the system Python without bootstrap dependencies; the repository import path and initialized worktree environment corrected those invocation errors. No source, dependency or gate change was used to obtain these results.

### Portable interpreter implementation, local proof (2026-10-19)

The source-only writer replaced the accidental realpath CLI dependency with one private Bash/readlink resolver in `scripts/pre-commit-quality-checks.sh`, source blob `6179a99294caf4b9c505286d0492624fb5857ef7`. It preserves the separate physical selected-directory and final-target exclusions before interpreter execution. Successful sentinel captures preserve meaningful newline bytes through parent resolution, symlink traversal and caller capture. Immutable policy extraction, isolated Python flags, temporary cleanup, workflow byte pin, eligibility and hosted gates are unchanged.

The writer's direct pre-edit full-hook repro failed with the expected missing-command and return-code assertion. After the change, all 59 host cases pass, including the 36 original cases and 23 additions. Root independently replayed the original full-hook control and missing-realpath trigger against the changed hook. Both now return zero with DEFERRED and the complete downstream fixture trace; the earlier trigger returned one. This trace verifies routing, not new real contract execution. The initialized native Bash parser passes. ShellCheck has the same four pre-existing findings on baseline and head and no new finding. These are local path-boundary results; hosted capsule UNKNOWN and native older-OS acceptance remain unresolved.

Actual native analyzer adapters then found a CC15 warning in the new positive-test setup despite clean Pylint and AST output. The additive fixture setup is being simplified without removing parameter cases or assertions. Its warning-free result, broader focused proof, final independent review, normal source hooks and publication remain pending at this checkpoint. Raw source reproduction, 59-case JUnit, root replay and baseline-comparison ShellCheck output are retained in `ci519-portable-host-path/implementation`, `root-reproduction-green.json` and `shellcheck.json`.

### Final portable path proof (2026-10-19)

The fixture cleanup replaces branch-heavy path selection with named paths and chain rows. All ten positive parameter identities, their decorators and assertions remain unchanged. All other function bodies are unchanged. Native Radon complexity for that setup is now 8 rather than 15; actual Pylint, Radon and AST adapters return no findings for the authored proof file. Ruff formatting/lint and BasedPyright pass. All 59 hook cases pass after cleanup. Root's direct invocation of the same 23 new cases against immutable pre-fix hook blob `954748f6ae4d608109051fd745b9269d4a48ec57` still produces exactly 14 intended missing-realpath AssertionErrors and nine passing controls. The first direct invocation used a logical `/var` temporary ancestor that consumed an extra native symlink allowance; using the physical temporary root, as native pytest does, corrected that verifier setup without any source or test change.

Root then executed the combined host proofs, projection unit cases, pre-commit parity and immutable-schedule validator regressions. All **443 tests pass**, with zero failures, errors or skips. All normal pre-commit hooks pass for the staged source, test and evidence segment, including canonical lint/types, module signatures/imports, native planned Requirements validation and **28 actual contract cases**. The native Requirements artifact reports one passed source and zero failed sources at planned maturity. The approved local capsule stage remains DEFERRED, never PASS. No threshold, exclusion, capability, timeout, workflow or policy pin changed.

The source and test blobs are respectively `6179a99294caf4b9c505286d0492624fb5857ef7` and `654d277bf18545d198c217fa9301c49214a9a5a4`. Final independent review and signed publication are the remaining local handoff steps. Mandatory exact-head hosted acceptance remains unchecked. The known unclassified contract failure appears on both base and head in current `ec93af1d` hosted independent review; these local path proofs neither classify nor resolve it. Native macOS 11/12 and Linux full-hook execution are not claimed. The complete focused JUnit/log, native adapter output, post-cleanup discrimination receipt, staged Requirements artifact and hook log remain in `ci519-portable-host-path` in the parent review workspace.

Fresh independent final review approved the exact source and test blobs above, final evidence and task reconciliation with no actionable correctness, security or preservation finding. Its distinct native Bash helper probes preserve an exact dot/newline-ending target through 40 hops, refuse at 41 and refuse partial readlink output followed by nonzero status. These are private helper probes, not Linux caller or older-macOS acceptance. The comment audit found no deletion or unsafe suppression; the single new comment explains externally imposed shell newline handling. Every source/test writer and reviewer was explicitly stopped before signing. Task 12.4 records completed local verification and review only; task 12.5 remains unchecked until mandatory exact-head hosted acceptance.


### Checker completion reproduction (2026-10-19)

Against signed published `1f06bd812d324ace3971162bde3ea590f63cfc8e`, root independently executed the full hook with an indexed orchestrator byte mutation and the same caller-reviewed immutable checker. The actual external Python refused with exit one. Selecting the external `/usr/bin/true` instead returned zero and reported DEFERRED while ignoring the Python flags and checker path. This reproduces review `4312619181` within the already required working-Python boundary. It does not establish a protected or hostile-host exploit.

The normative completion scenario precedes new test definitions and production edits. Raw control and bypass output is in `ci518-review-artifacts/ci519-policy-execution/root-reproduction.json`. New regression RED, design selection and implementation GREEN remain pending. Existing 443 local passes and signed portability proof are unchanged historical evidence. All new work remains in maintenance #519; planning #517/#770 and core #776 source remain unchanged.


### Checker completion test checkpoint (2026-10-19)

The additive host proof has 11 new cases. Against unchanged production hook blob `6179a99294caf4b9c505286d0492624fb5857ef7` at `1f06bd812d324ace3971162bde3ea590f63cfc8e`, the actual final run reports **5 failed, 65 passed, zero errors and skips** across 70 cases. Four failures select either a zero-exit shell executable or `/usr/bin/true`, against reviewed and invalid indexed workflows. The fifth masks a failed checker through a forwarding launcher. Every failure is the incorrect zero hook status with DEFERRED. A launcher that fails after checker success correctly refuses. Five real immutable CLI controls preserve ordinary, SystemExit and direct successful exits, failed exits, exceptions, argv, cwd, isolated flags, Git replacement isolation and stdout/stderr.

All 59 prior case identities and original function ASTs remain unchanged. The test blob is `cd1701d9bd02549ec8642ba873d20533f6f6d756`. Actual native Pylint, Radon and AST adapters return no findings; scoped Ruff, format and canonical BasedPyright pass. Root independently parsed the final raw JUnit and verified the unchanged hook. The first attempt had three fixture setup failures because a synthetic checker commit consumed unrelated staged paths; a checker-only fixture commit corrected setup. Its superseded logs are retained separately and are not the RED checkpoint.

Raw final JUnit, logs, preservation proof, analyzer output and rerunnable test driver are retained in `ci519-policy-execution/red-tests`. These are local hook/index/checker proofs with downstream Hatch fixtures, not new contract execution or hosted acceptance. The signed test-only checkpoint, implementation, GREEN, normal hooks and independent review remain pending. No production source, policy pin, workflow, capsule capability or protected gate changed.


### Checker completion implementation and local proof (2026-10-19)

Signed local test-only checkpoint `7a20f5f322420de860dd9ead7897ea7733211ce2`, tree `d343ad02cd58a1b04303ab11e2ae2f8b2e32ac4c`, precedes all completion-fix production edits. Root verified its approved-key Good GPG signature. Fresh independent review approved the exact seven-file checkpoint, directly parsed the final 70-case RED JUnit and confirmed preservation. Strict OpenSpec, the actual staged native planned Requirements gate and normal signed hooks passed, including 28 actual contract cases. No hook was bypassed; capsule review alone remained DEFERRED under the approved local exception. The checkpoint was kept local while the source fix was prepared.

The source-only change is hook blob `8cef24cb768b16784ead1f5204b20d9901f2a79f`. After unchanged location, immutable-selection and extraction checks, one inline isolated stdlib supervisor runs the extracted checker as an ordinary child CLI. It creates an exclusive completion file in the existing private directory only after child success. The shell requires successful outer execution and completion presence. The existing exit trap cleans both files. An ignored invocation and a launcher masking checker failure cannot create completion through the supervisor. A launcher failing after actual checker success still refuses. This is a working-interpreter and completion check under trusted-host assumptions, not authentication of a malicious host executable. No new policy pin, workflow, capability, timeout, dependency, setting or backend is added.

The same 70 host cases now pass with zero errors or skips. Test blob `cd1701d9bd02549ec8642ba873d20533f6f6d756` is unchanged from the signed failing checkpoint. Root independently replayed four complete hook/index controls. Valid indexed bytes with real Python return zero and DEFERRED. Invalid indexed bytes with Python, and both valid and invalid bytes with `/usr/bin/true`, all return one without DEFERRED or downstream contracts. The original invalid-index `/usr/bin/true` reproduction returned zero and DEFERRED. CLI success, failure, output and cleanup controls remain intact. These fixture traces are orchestration proof, not actual contract test execution.

The broader host, projection, diagnostic, pre-commit parity and immutable-schedule scope reports **454 passed, zero failures, errors or skips**. Native Bash 3.2 syntax passes. Actual ShellCheck comparison has the same four pre-existing findings on the signed baseline and fixed source, with none added. Authored test native Pylint, Radon and AST adapters remain empty and the test source is unchanged. Raw JUnit, commands, full-hook replay and analyzer comparison are in `ci519-policy-execution/implementation`, `focused-green`, `root-full-hook-green.json` and `shellcheck-comparison.json`. Normal source hooks, final independent review and signed publication remain pending at this checkpoint. Hosted exact-head acceptance remains unchecked. This local fix does not classify or resolve the separate hosted UNKNOWN contract evidence on both base and head. Native older-macOS and Linux full-hook acceptance are not claimed.


The actual staged native Requirements gate passes at planned maturity with one source passed and zero failed. Strict OpenSpec and all normal source hooks pass. The existing safe-change rule classifies this shell-hook and Markdown-only segment as metadata, so its unchanged code-review and contract execution stages are SKIPPED. No new contract execution or local capsule PASS is claimed for the source segment. The preceding signed test checkpoint actually executed and passed 28 contracts. The separate full-hook proof above directly executes the new completion boundary and preserves downstream fixture routing. Final independent source review and publication are the remaining local steps; mandatory exact-head hosted acceptance stays unchecked.


Fresh independent final review approved source blob `8cef24cb768b16784ead1f5204b20d9901f2a79f` with the unchanged signed test blob. The reviewer independently parsed the RED, 70-case GREEN and 454-case JUnit, compared original ASTs and 59 identities, checked the four complete hook rows and verified native Bash syntax. Its bounded verdict found no actionable correctness, preservation or evidence issue. The source comment audit reports zero added comments, suppressions or actionable flags. All writers and reviewers were explicitly stopped before signing. Task 13.4 records completed local gates and review only; task 13.5 remains unchecked for mandatory exact-head hosted acceptance.


## Per-snapshot diagnostic association RED checkpoint (2026-10-19)

The selected contract entered proposal, design, tasks and the quality-fixture-identities delta before test edits. Strict OpenSpec validation passes. Tests exercise both actual named workflow failure heredocs through isolated host Python, with no copied production classifier. The dedicated module is `tests/unit/test_capsule_snapshot_diagnostics.py`. It contains 152 parameter cases in five behavioral functions. The original `test_capsule_review_projection.py` and host proof remain byte-identical to HEAD.

At unchanged production workflow SHA-256 `a322d4ede8735bb24787066b5b3bcfd8c6a00bebaf84b3fed843fcf36450c60d`, the full new module reports **124 failed, 28 passed, zero errors and skips**. All 124 failures are the intended absent `snapshot_diagnostic_observations` value, observed as `assert [] == [[...]]`. The eight distinct/swapped, small/large main cases first pass exact legacy-field, unavailable acceptance, report-byte preservation and private-output checks. One actual failure states `Right contains one more item: [{'analyzer': 'contracts', 'side': 'base', 'reason': 'analyzer_process_error'}, {'analyzer': 'contracts', 'side': 'head', 'reason': 'analyzer_output_invalid'}]`. This proves missing public association, not the cause of the hosted contracts failure.

The corpus covers the closed reason vocabulary through both incompleteness routes; exact leading tokens; missing, nonstring and unknown diagnostics; suffix injection; 4096/4097 Unicode code points with ASCII and multibyte suffixes; zero/one/two sides; ten-entry acceptance; duplicate and distinct over-ten-entry refusal; unrelated analyzers; duplicate JSON keys at root, row, side and diagnostic levels; truncation, trailing garbage and reports over 32 MiB. Complete primary large fixtures explicitly assert a byte size above 2 MiB and at most 32 MiB. The legacy independent substring observation for a recognized suffix remains explicitly preserved while its new per-side reason must be unclassified.

All **116 original projection and mandatory host cases pass**, with zero failures, errors or skips. These include original review exits 17 and 124, projector crash handling and import isolation. No host proof edits were needed. Scoped Ruff lint and formatting, Pylint and canonical targeted BasedPyright pass without suppressions. This is the failing-test checkpoint only. Workflow implementation, GREEN, normal source hooks, independent source review and mandatory exact-head hosted acceptance remain pending.

Canonical raw commands, JUnit, stdout/stderr, result hashes and preservation checks live in `/private/tmp/ci519-projection-red/`. The final test SHA-256 is `e73e2a464c7284c52333406c671a97d792b6811452ca46f845f8a14ef88daf2d`. `final-corpus-red.xml` and `.log` are the 152-case RED; `final-preservation.xml` and `.log` are the complete 116-case control run. Their `.command.json` files contain exact rerunnable argv. Earlier primary/corpus runs used the original-module location and broader name selections; they are retained as superseded exploratory evidence, not the canonical count. No tests failed during fixture setup. The final module split preserves original test bytes and avoids the measured module-length warning without suppressing it.

No workflow, controller, gate, runtime capability, timeout, policy pin, manifest, dependency or frozen planning file changed. Nothing was staged, committed, pushed, reviewed through services, or run in CI or Docker. The existing raw untracked `.audit/` was untouched. The next authorized phase is root source review of this test checkpoint before production edits.


### Per-side projection implementation and compatibility proof (2026-10-19 Europe/Berlin)

The two existing failure heredocs now append only the selected finite contracts/side/reason observations. Their original readers, output lines and fields, report bounds, assurance, verdicts, findings, shell exits and isolation stay unchanged. Removing exactly the 74 added workflow lines reproduces every predecessor workflow byte. The helpers are identical. No shared candidate-source import, controller change, capsule capability, deadline or policy extension was introduced.

The initial actual implementation run passed all 152 new cases and 113 of 116 original controls. Three original whole-stream comparisons omitted the deliberately approved extra unclassified envelope for missing or unknown reasons. Those initial 265 passes and three failures remain raw evidence. Root extended only that exact expected stream with explicit finite records; every old row, exact cardinality, key and privacy/exit assertion remains required. No observations were filtered out, no eligibility workaround was added, and no assertion was removed. This is the already specified additive output compatibility, not a gate waiver or a revision of core's frozen 89-case inputs.

The predecessor replay selects all 152 cases in `tests/unit/test_capsule_snapshot_diagnostics.py` plus the five parameter cases in `tests/unit/test_capsule_review_projection.py::test_candidate_incomplete_snapshot_projection_is_finite`. Against exact authenticated workflow SHA-256 a322d4ede8735bb24787066b5b3bcfd8c6a00bebaf84b3fed843fcf36450c60d, those 157 cases produce 127 intended missing-output failures and 30 passing controls, with zero errors/skips. The unchanged new module contributes the same 124 failures and 28 passes as its original RED checkpoint; the existing stream selector contributes three failures and two passes. The broader GREEN run selects the complete new module, all 85 existing unit cases and all 31 mandatory host cases. Against exact implementation SHA-256 61363bf5eafd61455495a1e1a09733035d572c0657fcc1435e4094920a3f24c7, those 268 cases pass with zero failures/errors/skips. The original mandatory 31 host cases still execute, including review exits 17/124 and hostile-import controls. The new 152-case source is unchanged from its RED checkpoint. The only original test edit is the explicit additional-envelope expectation.

Durable raw evidence is under ci518-review-artifacts/ci519-contract-reason-projection in red-checkpoint, implementation and compatibility-proof. Actionlint and strict OpenSpec passed for the source implementation. Remaining normal gates and fresh independent review are recorded separately. Underlying hosted contracts causes remain unknown until a new exact-head run publishes these existing private reason classes. Local Darwin review remains DEFERRED, never PASS. Mandatory hosted acceptance remains unchecked.

The first normal source hook correctly refused the new requirement because its existing sidecar lacked a source mapping. The sidecar now appends five concrete verification functions for the 152 executed cases. Every predecessor mapping is byte-preserved. Required maturity stays planned; neither the adapter nor the local Darwin deferral is presented as hosted review or runtime acceptance. The failed hook report remains retained.


## Native snapshot test ownership correction (2026-10-20 Europe/Berlin)

Actual hosted 8c10 candidate Python 3.12 evidence reports unsupported `-I` runtime attachment for the 152 new snapshot cases, CC17 in their legacy-output test and excessive nesting in the row-case test. This classifies new fixture defects separately from the still-unclassified contracts UNKNOWN on both base and head. No contracts runtime cause is inferred. This test ownership refactor changes no production behavior and uses those retained failures rather than claiming a newly run RED result.

Before editing, native collection records exactly 268 cases, consisting of 152 new snapshot, 31 existing host and 85 existing unit cases. The full 152-case family moves into the already mandatory host proof. Every generated identity is preserved with only its file prefix changed. The original host file is a byte-identical prefix, and the original 85-case unit file, pyproject, both workflows and indexed orchestrator are byte-identical. Two private assertion helpers expand back to the exact original test AST. The other moved fixture/test ASTs are unchanged. All nine explicit row-table inputs reproduce their original serialized JSON objects and expected observations. Native `-I`, empty stderr, four private canary exclusions, unchanged report bytes and exact legacy equality remain required.

The focused actual native run passes all 268 cases with zero failures, errors or skips in 4.95 seconds. New host ownership contains 183 cases and ordinary unit discovery retains 85. Radon measures the repaired legacy-output function at CC9 and row-case test at CC2. Ruff lint and format pass. A preservation verifier first used an unrelated host Python without pytest; that setup failure was corrected by selecting the prepared modules environment. It is not source failure or passing evidence. Raw inventories, baseline bytes, JUnit, commands and rerunnable preservation verifier are retained in `ci519-contract-reason-projection/follow-up-host-migration`. Current-head hosted acceptance, native static review, normal hooks and independent final review remain required. No capsule capability, runtime guard, timeout, bound, verdict, security gate or local deferral is changed.


The first normal hook run passed formatting, canonical types and Pylint, then correctly rejected duplicate Requirements selectors in a redundant new ownership mapping. Ownership is now stated in the existing mandatory-host requirement, and the existing five snapshot mappings point to their new host path. No test or selected case changes. The failed native report is retained; this correction preserves the one-selector ownership rule rather than weakening validation.


After the mapping ownership correction, the unchanged normal hook and strict OpenSpec pass. The hook executes all 28 contract cases successfully and accepts planned native Requirements maturity. Canonical types, Ruff, Pylint and the real Radon, AST clean-code and AI-bloat adapters pass; the three latter adapters report no findings on the host file. Approved local Darwin capsule review is explicitly DEFERRED, never PASS. The immutable caller-selected policy commit, external host Python and full indexed orchestrator digest are unchanged. Independent final review and current-head hosted acceptance remain required.


## Finite fallback fact checkpoint (2026-10-20 Europe/Berlin)

Before workflow edits, both actual isolated programs ran 264 new native cases. They produced 248 predicted missing-envelope or missing-field AssertionErrors and 16 classified-side omission controls, zero errors and zero skips. The workflow remained byte-identical to 8c10, SHA-256 61363bf5eafd61455495a1e1a09733035d572c0657fcc1435e4094920a3f24c7. This is local synthetic-report boundary evidence, not a runtime fault classification or hosted GREEN.

The additive implementation reuses the existing validated observations, promotes exactly the existing20-token vocabulary within each independent inline program and computes only finite facts for unclassified sides. It does not change reason records, report readers, bounds, acceptance, review exits or runtime behavior. The first combined run has 529 passes and three failures, all exact-stream expectations missing the newly appended finite envelope. Only that existing test's expected stream was extended with the exact five-key records. Its original assertions remain intact. The next actual native run passes all 548 cases with zero failures, errors or skips in 9.40 seconds. Every original 268 identity remains retained, with 280 added cases. The real fixture returns all output rows and continues enforcing native isolation, empty stderr, private-canary exclusion and unchanged report bytes.

Producer identity remains unknown and outside this unit. Installed source hashes alone do not prove executed Python bytes; no such identity or protected authority is claimed. Exact legacy-output replay, static parity, normal gates, independent final review and current-head hosted acceptance remain separate verification.


The final compatibility verifier executes 162 complete old/new program comparisons. It removes only the exact validated finite field or envelope and proves all remaining output identical. Four negative controls reject an extra envelope key or non-boolean membership and retain unknown rows/keys for exact comparison. All private canaries remain absent and reports remain byte-identical. Both programs have identical helper ASTs and exactly the original 20-token vocabulary; removing this unit reconstructs the complete predecessor workflow bytes. The final native collection retains every original 268 identity and adds 280 unique cases.

The native static review found one new readability advisory on the expanded exact-stream test. It is retained raw and resolved by naming the two analyzer fixture records directly and colocating the three expected envelopes in one list. No assertion is removed. Inlining those two pure fixture values recovers the original payload AST; deleting only the newly expected envelope recovers the original test AST. Radon, AST clean-code and AI-bloat now report zero findings. The final 548-case run passes without errors or skips in 9.58 seconds. This is a relevant projection selection, not a full repository suite. No new warning waiver is introduced.


Final normal hooks, strict OpenSpec and actionlint pass. Native planned Requirements passes, all 28 contract cases execute successfully, and canonical types, Ruff and Pylint pass. Real native Radon, AST clean-code and AI-bloat report zero findings after the fixture cleanup. Local Darwin capsule review remains explicitly DEFERRED under the unchanged approved immutable policy. Fresh independent review and exact-head hosted acceptance remain required; no actual contracts runtime fault has been classified.


## Installed controller source observation checkpoint (2026-10-20)

Spec authored first at predecessor 29ee5503480fd18d7f6c5cfff08b550ed2ef8104. The independently selected contract requires complete workflow programs and missing-observation assertions. No production implementation is included in this checkpoint. Native synthetic fixtures prove observer wiring only; cached native signature evidence and future hosted source evidence remain distinct. Reproducible commands, raw logs, JUnit, inventory and workflow hashes are retained in follow-up-installed-source-identity/test-checkpoint. RED results will be recorded after tests are authored and executed.

Final native RED used `.venv/bin/python -m pytest -o addopts= -q tests/host/proof_capsule_review_projection.py tests/unit/test_capsule_review_projection.py -k installed_source --tb=short --junitxml=<checkpoint>/red.junit.xml`. It produced 120 expected failures, zero errors and zero skips in 20.82 seconds. There were six missing complete receipts, 66 missing unavailable receipts, 47 missing two-record publications and one missing always-step assertion. Exact messages include `complete source receipt must exist before subject entry` with `None is not None` and `installed source publisher must emit two records` with `0 == 2`.

Before those failures, complete generated reviewer dispatches and real Bash command recipes passed original exit, preload, preparation, cleanup and argument controls. Separate command/publication execution preserved exits 0, 2, 7, 17 and 124, no-impact and failed-preparation routes, original public output and private report bytes. The missing publisher produces no records in the job driver; no future helper import or fabricated baseline observer supplies RED. Predicate and parser expectations beyond the missing boundary still require production GREEN.

Collection retains all 548 original node IDs and adds 120, for 668 total. Every original function/class AST and assignment in the three test/support files remains unchanged. Native Radon, AST clean-code and AI-bloat adapters report zero findings; Ruff and strict OpenSpec validation pass. This is a test/spec checkpoint, with no full-suite run, normal hooks, signing, workflow edit or hosted acceptance claim. Both workflow hashes remain identical to predecessor 29ee. Source-only synthetic verification does not establish native cryptographic admission or actual hosted identity.


### Installed controller source implementation checkpoint (2026-10-20)

The workflow adds only the selected inline observer and a separate always publisher. Removing those two insertions reconstructs signed predecessor `29ee5503480fd18d7f6c5cfff08b550ed2ef8104` byte for byte. The candidate job, original independent steps, original report projectors and indexed orchestrator are unchanged. The observer authenticates installed source with the existing native verifier and checks loaded origins and function identity. It does not identify literal executed bytes, Python caches, child analyzers, candidate source or a historical producer.

The same frozen tests now report **120 focused passes, 668 relevant passes and 14 legacy independent Bash control passes**, with zero failures, errors or skips in each run. The prepared native interpreter is Python 3.12.13. All nine spec and test checkpoint hashes stayed unchanged through implementation. Root independently replayed the raw JUnit counts and hashes before this evidence update. The two metadata edits here record GREEN and completed implementation without changing tests or acceptance.

Both complete extracted Python programs pass native Radon, AST clean-code, AI-bloat and local Semgrep checks with no findings or scanner errors. Actionlint, Bash syntax, Python AST parsing and diff whitespace checks pass. An initial local Semgrep finding on publisher output was fixed by buffering both records through one `sys.stdout.write`; its raw evidence is retained. No warning exception or scanner suppression was added. Ordinary observation failure yields only unavailable evidence and does not replace the original operation outcome.

Raw commands, logs, JUnit, preservation proof and verification JSON remain under `ci518-review-artifacts/ci519-contract-reason-projection/follow-up-installed-source-identity/implementation-checkpoint`. Synthetic installed-module factories prove wiring and failure preservation, not cryptographic admission. Actual hosted source identity and the contract failure cause remain unknown. Native verification cost is unmeasured within the unchanged deadlines. Normal hooks, strict OpenSpec, independent implementation review, signed publication and exact-head hosted observation remain pending.


The first normal hook run passed signature, formatting, YAML, import boundaries, Ruff, types and Pylint, then rejected four new Requirements mapping IDs. The adapter expects each verification case scenario_id to use its imported requirement stem. The four prose scenario slugs were corrected to that stem, retaining the requirement text, selectors, intent, observables and test assertions. The failed native report is retained under implementation-checkpoint/metadata-correction. The comment audit also removed one redundant internal fixture docstring. Root proved its executable AST unchanged after removing that docstring. These metadata and prose corrections supersede the affected checkpoint hashes without changing the RED or GREEN behavior evidence. Final native hooks and independent review remain pending.


After the mapping correction, all normal hooks pass, including 28 actual contract tests. Native Requirements passes at planned maturity with implementation evidence not-yet-available. Strict OpenSpec passes. Local capsule review remains explicitly DEFERRED, never PASS. Fresh independent implementation review approves the exact ten-path change and independently replays old workflow equality, inventories, raw RED and GREEN counts, the mapping-only correction and six additional complete-publisher cases. The comment audit has no remaining flags after the one docstring deletion. All writers and reviewers were explicitly stopped before signing. Task 17.4 is complete; signed publication and exact-head hosted observations remain required by 17.5. No hosted source identity or runtime repair is claimed.


### Native source fixture quality RED (2026-10-20)

Published `fff041c3249b48fd3fca079a1db9d6d5a4d4cf65` produces thirteen new Pylint locations in candidate3.12 job118367681730/run39342645526. Actual Pylint4.0.7, the cached published adapter and its genuine target worker reproduce all thirteen in order. Six are C0301, one C0302 at1039/1000 host lines, one W0613 unused environment parameter and five C0415 function-local imports. Parent29ee produces zero for both full files under the identical project config. Missing docstrings are not a finding. Normal local lint did not cover these full fixture files; embedded-program static success did not establish their Pylint result.

The existing quality rules and native-only proof ownership precede this failure. This semantics-preserving refactor uses the genuine thirteen-finding native result as RED, without inventing a new behavioral failure. Root froze all668 unique case IDs, test and assertion ASTs, source snapshots and workflow/orchestrator/configuration hashes before implementation. All three independent designs and the cross-judge select one native-only fixture owner with direct public helpers. Ordinary discovery retains SDK-free shared support; tests and assertions remain at the existing host path. No source, assertion, selection, acceptance or runtime policy weakening is authorized. Raw native head/parent/base evidence, architecture and baseline are retained under `ci518-review-artifacts/ci519-contract-reason-projection/follow-up-native-source-fixtures`. Implementation and GREEN remain pending at this checkpoint.


### Actual installed-source observation and native fixture quality GREEN (2026-10-20)

Signed published head `fff041c3249b48fd3fca079a1db9d6d5a4d4cf65` is independently observed in job118367681676/run39342645526. Its always publisher succeeds and emits exactly two authenticated-source-and-loaded-origins records, one before preparation and one before review. Both runner digest `fa83b61f67e671681be0dd7ee5b3db0cae75b08b278e6835642b1e8bfcdde428` and sandbox digest `34108210bd4de6b37f34143195fb4ddbd6dfc343c0875bd0010d3f4c48294fae` match the cached signed reference verified with native core0.55.4. This rules out source drift in those two observed installed files. It does not attest executed caches, other files, children, the candidate job, a historical producer or protected authority. The independent review still reports oversized_report and contracts/pylint UNKNOWN on both sides. No contracts runtime fault is classified. Raw job, log, native reference verification and source receipt proof are retained under follow-up-installed-source-identity/publication/hosted-fff041.

The selected extraction now passes all three full files through actual Pylint4.0.7 using the cached published adapter and genuine target worker, individually and jointly. Radon, AST clean-code and AI-bloat report zero findings. Ruff, formatting, scoped Basedpyright and diff checks pass. An initial joint extraction result found R0801 for the identical purelib query; its raw evidence is retained. Root approved the bounded shared query after source inspection and updated the selected architecture before dependent edits. The final joint analyzer result is zero without suppression or policy changes.

Exactly668 relevant cases, the120 source-observation subset and14 legacy Bash controls pass with zero failures, errors or skips. All89 original function ASTs,41 test ASTs and202 assertion occurrences remain preserved under only the selected renames, import hoists, three unused-argument removals, literal wrapping and two purelib-query extractions. The38 generated source cases produce the same1102 filesystem entries, modes, symlinks, environments and digests as the frozen baseline. Fresh ordinary imports load neither tests.host nor the genuine SDK model; explicit native import and a deliberate leakage control establish the detector's sensitivity. Workflow, orchestrator and configuration pins are byte-identical. Rerunnable comparison scripts, source snapshots, commands, raw logs and JUnit remain under follow-up-native-source-fixtures/implementation. This is local scoped GREEN. Normal final hooks, independent review, signed publication and current-head hosted acceptance remain pending. The contracts UNKNOWN and existing unrelated parity warning are separate gates.


Final normal hooks pass with28 actual contract cases, native planned Requirements and strict OpenSpec. Darwin capsule review stays DEFERRED under the approved immutable policy. The read-only comment audit identified one redundant new module-summary docstring; root removed exactly that docstring and adjacent blank line and proved executable AST equality. Native full-file analyzers, Ruff, formatting and scoped types pass again on the final source. Fresh independent final review approves all six files without findings, independently replays all668 ordered IDs,38 generated trees, import controls, genuine native analyzers and14 legacy controls, and verifies all140 original packet hashes plus raw668/120/14 JUnit identities. The writer and both reviewers were explicitly stopped. Only this evidence paragraph and task18.4 closure follow that pinned review; source hashes are unchanged. Task18.5 remains pending normal signed publication and mandatory hosted acceptance. No general contracts verdict or unrelated warning waiver is claimed.


### Sparse producer-category spec-first checkpoint (2026-10-20 Europe/Berlin)

The selected contract is authored before new tests at signed local predecessor c5a8c4f2e765fd8b2455424f42c9190cc70cc018. It adds only sparse positive producer-family observations and retains all existing negative facts and acceptance. No workflow implementation is included. The actual hosted prefix remains unknown. Native synthetic complete-program proofs will establish the missing field, not a runtime repair.

The test writer owns only these six change files, the existing host proof and one new pure-data module. Initial workflow digest is 523d5038793383cdaedb763519f90d5955f3f98cff35111e395a7eeceaf63dbe and complete orchestrator digest is 827e26667ef9951783bfeaffebca5833e1e16a90151676b164b88d303f7ac371. Independent expectations, source pins, snapshots and rerunnable evidence are retained in follow-up-portable-conflict-category/test-checkpoint. RED, implementation and GREEN are pending at this spec-first checkpoint.


The final native test checkpoint declares 70 stable input cases and executes both unchanged whole failure programs. All 140 independently declared legacy outputs match before implementation. The data was frozen before these executions and was never derived from their output. Optional controlled log inputs cover both family-only logs without changing the old fixture API or AST. The two shell cases execute the real candidate guard and complete invocation-to-exit tail through native Python 3.12.13.

Focused RED has 142 cases, with 49 predicted missing-field AssertionErrors and 93 passing negative controls. Of the failures, 47 are positive owner cases and two are candidate shell exits 17 and 124. The printed mismatch is `Missing finite producer field` with `assert [] == [[...]]` and the fixed expected category records. There are zero errors or skips. The combined selection has 810 cases, with the same 49 failures and 761 passes. All original 668 ordered IDs and every old assertion remain intact. All 14 maintained legacy Bash controls pass. No syntax, import, environment, timeout or skipped execution supplies RED.

The final host file has 999 naturally formatted lines, exactly 50 more than its predecessor. All 32 old host functions and all original top-level function, class, assignment and loop ASTs across the four test owners remain unchanged. The existing shared support, native source fixture and ordinary test files remain byte-identical. The 202 old assertions remain, with eight new assertions in the existing host file. Pure data imports only stdlib json and contains no classifier, helper function, assertion, loader or production import. Ordinary import probes load neither native test ownership nor SDK models, and the deliberate leakage control fails as expected.

Actual Pylint 4.0.7 through the published adapter and genuine target worker reports zero findings on both affected full files individually and jointly. Native Radon, AST clean-code and AI-bloat also report zero findings. Ruff, formatting, scoped Basedpyright, strict OpenSpec and native planned Requirements pass. The initial W1514 on the new direct log write and import-spacing issue were retained and corrected with explicit UTF-8 and normal import sorting. Final RED and combined results were rerun on that final source. Two Requirements setup failures are retained separately, one missing the existing hook PYTHONPATH and one passing an omitted summary as None to the current typed API. Using the existing hook environment and an explicit summary path resolves setup without repository configuration changes. Planned Requirements still reports implementation evidence not-yet-available.

Raw commands, stdout, stderr, JUnit, exact collected identities, source snapshots, complete scoped patch, preservation pins and rerunnable checks are retained in follow-up-portable-conflict-category/test-checkpoint. Workflow and complete orchestrator bytes retain their initial digests. This checkpoint contains only spec and tests. Task 19.2 is complete; workflow implementation, GREEN, normal signed hooks, independent final review, publication and exact-head hosted acceptance remain pending. No runtime repair, merge authority, warning waiver or hosted producer classification is claimed.


### Sparse producer-category implementation and local GREEN

The workflow writer was explicitly stopped after freezing its151-file implementation packet. Root independently replayed every packet hash, all eight frozen spec/test pins and raw JUnit identities. Final native Python3.12.13 execution passes142 focused cases,810 combined cases and14 maintained legacy Bash controls, with zero failures, errors or skips. The exact RED identities are preserved. The workflow contains only60 inserted lines, and removing those additions reconstructs the signed c5a8c4f2e765fd8b2455424f42c9190cc70cc018 workflow byte for byte. Existing functions, outputs, exits and protected inputs remain unchanged. Both helper copies have equivalent ASTs. Final workflow SHA-256 is1b211c845336255a37577aef24bb970bc03301596230ddbfb7b7ea2daf360236.

Native analysis is reported against the real complete-program baseline. Both versions retain24 Pylint findings and two pre-existing Radon CC14 findings. The existing single R0801 group expands by27 duplicate lines in each isolated failure program. The selected design intentionally keeps these programs self-contained, without a new runtime import. Every other native finding maps to unchanged original source. New helpers have complexities4and9. AST clean-code and AI-bloat report zero. Actionlint, both complete Bash syntax checks, Ruff, formatting, scoped types, strict OpenSpec and planned Requirements pass. Planned Requirements is not runtime acceptance.

Semgrep exits zero with no engine errors but reports eight baseline print-in-src matches and nine final matches. The one added match is the required standalone candidate JSONL envelope. Root read the actual rule and complete program and disposes this as a contextual false positive. This process communicates through structured stdout, so replacing it with logging or a return would break its contract. No scanner rule, severity, suppression or waiver changed. The R0801 scope and this disposition remain visible to independent final review. Initial extraction setup, five corrected new Pylint warnings and a corrected proof-count assertion remain raw evidence. Only new local names and line wrapping changed after initial GREEN; final frozen tests were rerun unchanged.

The read-only comment audit found no new comments, docstrings or suppressions and proposed no deletions. Root verified its hashes match the final source and explicitly stopped the auditor. Root source review finds no extra abstraction, defensive guard or scope expansion. Durable evidence is follow-up-portable-conflict-category/{test-checkpoint,implementation,root-verification,comment-audit}. Normal hooks and independent final review remain pending at this checkpoint. No runtime repair, hosted family, exact-head acceptance, warning waiver or authority is claimed.


Final normal staged hooks and strict OpenSpec pass. All28 contract cases actually execute and pass, native staged Requirements remains planned, and the local capsule review explicitly remains DEFERRED. Fresh independent final review approves the exact nine-path source with no actionable findings after replaying all269 RED and151 implementation hashes, raw JUnit identities, old ASTs and140 declared legacy outputs. It also executes32 complete-program controls, including Unicode, fullwidth-colon, newline and NUL cases. It independently accepts the isolated-program duplication tradeoff and JSONL print false-positive disposition without granting a waiver. Root verifies the report and supplemental receipt hashes. Both source writers and both reviewers are explicitly stopped. Only this truthful evidence paragraph and task19.4 closure follow the pinned review. Task19.5 remains pending signed publication and exact-head hosted evidence.


## Compatibility predicate proof checkpoint (2026-10-20)

Specification and named requirement mappings were written before tests. Baseline is signed 07d7b735483d9ebcfd25d4fed6f235e4eb88cbdc and workflow SHA-256 1b211c845336255a37577aef24bb970bc03301596230ddbfb7b7ea2daf360236. Root selected Astra with Sol complete graphs and unique common minimum. Native feasibility and intended RED are pending; setup failures never count as RED. No workflow implementation, staging, commit, push, review or hosted acceptance is part of this checkpoint. Raw rerunnable evidence is retained in follow-up-compatibility-predicate-proof/test-checkpoint.


### Frozen compatibility predicate RED and native feasibility

The final default Hatch context executes both new explicit owners under Python 3.12.13: 100 cases, 76 intended AssertionErrors and 24 passing controls, zero errors or skips. Fifteen failures reach the missing current private receipt after successful real preparation, verification and cleanup; one vertical preparation-to-publisher case reaches missing transport; one rejects the unchanged stale prior pair. The remaining 59 failures require the absent finite public proof. All 39 full-object publisher comparisons differ only by the missing compatibility_proof key, with every old output item identical. Constructor, import, setup and syntax errors do not supply RED.

Actual genuine ProjectPlan, PreparedRuntime, prepare_runtime, seal_runtime, load_runtime, complete native compatibility and every member graph execute. All four fixed categories have passing native full-process construction controls. Pinned string inequality, active requirement rejection, equal-string variants, missing targets, satisfied constraints, false markers and accepted prereleases are measured native behavior. Whole-map basedpyright retention and a real missing pinned graph payload prevent corrective claims. Complete-program mutations cover returned root, identity, descriptor path, altered descriptor with valid original disk content, and payload drift with unchanged return. The latter independently records genuine verifier rejection, original exit17 and real worker/scope cleanup before the missing-receipt RED. Source authentication is explicitly synthetic at the installation seam; native verification is never fabricated. External removal mutations against a future observer remain planned for GREEN.

The default integration uses genuine core source0.55.10 and repository reviewer source; installed distribution version and exact source manifests are recorded separately. A supplemental final run selects the whole authenticated cached reviewer0.51.2 source and released core source/distribution0.55.4 with normal imports: 12 cases, two intended missing-proof failures and ten passing native controls, zero errors or skips. Pre-run snapshots bind both runs to final test/helper bytes. The supplemental runner records fa83b61f67e671681be0dd7ee5b3db0cae75b08b278e6835642b1e8bfcdde428. Neither variant reproduces hosted target versions or proves resolver acceptance. Worker acquisition, external build output, installation verification and CLI output remain explicitly synthetic authorities.

The existing trusted protocol context scopes compatibility_proof. Within TRUSTED_ROOT and its fixed report/log paths, missing or invalid receipt is unavailable. Standalone final Python publication without that context preserves the complete legacy object and omits the field; the complete-program control passes. This reconciliation preserves frozen original assertions and uses no new environment API.

All810 original ordered projection cases and14 maintained legacy controls pass. The original210 assertions,999-line host owner, eight immutable file pins and complete orchestrator remain exact. Parsed pyproject settings differ only by the two additive explicit selectors. Ordinary discovery runs in a fresh process with an import tripwire and never imports either new owner or native helper. The native helper remains host-only.

Actual Pylint4.0.7 through authenticated cached adapter and genuine target worker reports zero findings across each affected whole file and jointly. Native Radon, AST clean-code and AI-bloat report zero. Ruff, formatting, scoped Basedpyright and strict OpenSpec pass. Native planned Requirements evaluates the actual changed scope using a private temporary GIT_INDEX_FILE: one source passes with zero skips, implementation not-yet-available. The canonical index before/after hash is identical and the private index is removed. The earlier HEAD comparison returned no-impact/skipped and is retained as SKIP.

Raw chronological setup failures and preliminary runs remain separate. An automatic review rejected one nonexecuted batch; its exact tool command and exact rejection response are retained. Safe corrections retained all genuine native calls, split visible assertion groups and encoded fixed input cases; they did not introduce the rejected hand-built expected-observation helper. Early setup failures whose raw output was not persisted are explicitly listed in the checkpoint report rather than represented as complete receipts.

The packet contains full rerunnable commands, raw stdout/stderr/JUnit, source snapshots, native lifecycle/private program outputs, original-source file manifests, baseline identities/assert inventories and an artifact SHA-256 manifest. Task20.2 is complete at RED/native feasibility only. Workflow implementation, GREEN mutation testing, normal signed hooks, independent review, publication, hosted acceptance and any actual dependency repair remain pending. No production workflow or existing test owner changed, no canonical staging/commit/push/review occurred, and no cached skip or deferred review is reported as PASS.


### Compatibility predicate implementation and independent local review

The workflow implementation is frozen at SHA-256 `c268a001c2741f838207dbb572b1953e4ce11cffebeb07a4793aa49f38b4b5f3`. Root independently rehashed all 4712 implementation artifacts and the 2008 original RED artifacts. The ten spec, test and selector inputs remained unchanged throughout implementation and native PID maintenance. This final evidence update records completed local work without altering the original frozen packets or acceptance assertions.

Actual local verification passed 100 default compatibility cases, all 810 ordered original cases, 14 legacy controls, 12 released-reference cases and six supplemental cases. The supplemental variants retain explicit before-and-after workflow and extracted-program bindings. Fourteen complete-program guard-removal mutants each produced the intended behavioral assertion failure. The default core source integration at 0.55.10 remains distinct from the released core source and distribution at 0.55.4. These fixtures do not reproduce hosted target dependency operands or establish a dependency repair.

Native whole-program findings retain their exact baseline identities. Pylint remains 32, Radon remains two, AST clean-code and AI-bloat remain zero, and Semgrep remains nine with zero engine errors. These counts cover the complete candidate, observer and publisher programs, including the reviewer warnings omitted by an older 24-count scope. Ruff, formatting, scoped types, actionlint and complete shell syntax checks pass. Independent Bash 3.2.57 checks cover all three complete scripts. No analyzer rule, severity, capability, time budget or test selection was relaxed.

A fresh independent source reviewer approved the implementation with no actionable finding and ran four additional complete-publisher controls. Its report SHA-256 is `67f699d1b4fa7801358d3f335a2747b9138c29133f6c721e4a53b7ea266e135f`. Root replayed the raw verification and artifact hashes, then explicitly stopped the writer and both reviewers. Durable packets are `follow-up-compatibility-predicate-proof/{implementation,final-source-review,root-verification}` under the existing ci518 evidence root. Required full hooks, normal signed publication and exact-head hosted acceptance remain pending at this checkpoint. No actual hosted dependency correction or native runtime acceptance is claimed.


Normal staged repository hooks and strict OpenSpec for ci03 and ci04 now pass. All 28 contract cases actually execute and pass. Staged native Requirements passes both sources at planned maturity after a separately reviewed ci04 reference-only correction. The capsule review remains explicitly DEFERRED under the existing owner-approved Darwin exception. The compatibility workflow and frozen executable tests are unchanged. Independent compatibility source review and native PID source and metadata reviews are approved, with all authors and reviewers explicitly stopped. Normal signed publication and exact-head hosted evidence remain pending. This local result does not classify or repair the hosted target dependency conflict.
