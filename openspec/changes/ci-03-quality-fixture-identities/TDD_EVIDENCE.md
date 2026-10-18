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
