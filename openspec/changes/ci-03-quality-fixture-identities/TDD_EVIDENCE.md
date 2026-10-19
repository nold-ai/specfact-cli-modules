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

The added schedule assertion failed before the Hatch command changed because `proof_capsule_review_projection.py` was absent from its mandatory host stage. The four shell functions, fixture and interpreter helper were first moved with exact AST equality. Subsequent cleanup removed redundant imports, named the registered fixture separately from its argument, exported the shared preparation builder, and extracted existing fixture construction and assertion groups. These changes retain all original assertion ASTs, all 38 test functions, every decorator and all 231 parameter-case identities. Collection now consists of 31 host cases and 200 ordinary unit cases split by private-report and public-diagnostic behavior. The split also removes the actual module-length warning without excluding either file from analysis.

Focused projection execution passed all 231 cases. The combined three mandatory host proofs, both projection unit files and pre-commit parity regression file passed 413 tests. All 200 unit cases passed with PATH containing Git but no Bash. This is a local capability-boundary proof, not a hosted traceback diagnosis or Linux acceptance.

Actual repository analyzer adapters were executed under Python 3.12.13, Pylint 4.0.7 and native `pyproject.toml` configuration. Each of the four resulting fixture files returns zero Pylint findings when checked separately. Radon and AST clean-code adapters return no findings over all four files. The former complexity 24 and 16 functions are now below the warning threshold; no thresholds or exclusions changed. BasedPyright reports zero errors and warnings. Ruff lint/format, strict OpenSpec and native planned Requirements validation pass. Requirements used a disposable private index; the real index was not staged. Observed maturity remains `planned` and implementation evidence `not-yet-available`.

Joint Pylint reports two R0801 data-sequence matches also present before this partition: a literal expected public Radon record versus its independent input fixture, and shared metadata in distinct structured-Semgrep and decoder-depth stimuli. These contain data, not duplicated executable behavior. Deriving expected output from its input would weaken the regression; the independent literals remain. The parity AST warning at line 201 normalizes differing string constants and therefore conflates two regressions: a single added `+++` content line expects lines 10 and 11, whereas forged paired header content across two hunks expects lines 2 and 10. Both distinct stimuli and exact assertions remain unchanged. No suppressions, waivers or analyzer changes were added; these observations are supplied for parent review, not represented as a clean joint analyzer report.

Durable commands, original source, collection lists, move and final AST proofs, raw analyzer reports and local test logs are in `ci518-review-artifacts/ci519-projection-host` in the parent review workspace. Parent independent review, normal hooks and hosted exact-head acceptance remain pending. The independent hosted analysis_timeout remains unresolved. No local result establishes that this fixture partition resolves that timeout.
