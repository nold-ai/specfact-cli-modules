# TDD Evidence

## Planning checkpoint — 2026-08-13

No behavior changed and no tests ran for this OpenSpec-only planning commit. Core PRs #665–#671 are future adjudicated benchmark cases, not evidence that this change is implemented.

## Dependency amendment — 2026-08-19

The approved exact-core target changed from the unavailable planned 0.56.0 identity to existing immutable lightweight tag `v0.55.1`, full commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276`, full tree `47984be5434d7ae65ed6908bf525a32053290337`, and strict `===0.55.1`. Live tag lookup and local commit/tree inspection established those identities. No test or source evidence is claimed by this planning amendment.

## Core-interface and capsule-composition amendment — 2026-08-21

Fresh core refs established `origin/dev@e3a20f20df440dff49f8c6d1f73375451bea1d8c`, `origin/main@b1e517e60e669eaba15a18ecfa83ef5a9df65276`, and immutable `v0.55.1` tree `47984be5434d7ae65ed6908bf525a32053290337`. A path-limited byte comparison of `module_discovery.py`, `module_installer.py`, and `module_package.py` found no difference between `origin/dev` and `v0.55.1`. The tag already contains `DiscoveredModule`, canonical user/marketplace roots, `.specfact-registry-id`, `.specfact-install-verified-checksum`, package-integrity parsing, bundled-key lookup, and `verify_module_artifact`. The earlier contract incorrectly assumed those records arrived as one aggregate loader DTO; no such later unpublished interface exists.

The approved amendment replaces that assumption with derived `core-v0.55.1-installed-module-handoff-v1`, separates workflow-attested `verified-candidate-module-payload-v1` from released official provenance, and distinguishes the immutable OCI base-root identity from generated `sealed-bootstrap-v2` plus `capsule-composite-identity-v1`. The earlier task 3.12e/3.12f green evidence proves descriptor-safe copying only and is not reused as evidence for this amended handoff/bootstrap contract. New named tests, collected selectors, checkpoint projection/digest, actual failing evidence, implementation, and passing evidence are required before either task returns to green.

## Implementation readiness — 2026-08-19

### GitHub governance observation

- Observation: `2026-08-19T22:20:58+02:00` (`2026-08-19T20:20:58Z`).
- Hierarchy cache: `.specfact/backlog/github_hierarchy_cache.md`; state `generated_at=2026-08-19T20:10:14Z`, fingerprint `25ab587f47f83db25875a1b67cbc5094cd6a375dc4c3212bec8992e232240748`; the mandated refresh reported the unchanged 24-issue hierarchy, followed by live issue readback.
- Implementation issue: [nold-ai/specfact-cli-modules#416](https://github.com/nold-ai/specfact-cli-modules/issues/416), `OPEN`, User Story, parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162).
- Project: `SpecFact CLI`, status `Todo`; assignee `djm81`; labels `change-proposal`, `codebase`, `enhancement`, `openspec`.
- Native dependencies: `blockedBy=[]`; `blocking=[]`. The accepted planning PR #413 and synchronization PR #415 are complete. No core adoption issue exists yet by design; it is downstream of the signed module handoff. Requirements R07/R08 are independent.
- Metadata decision: `READY`.

### Immutable repository and benchmark refs

- Synchronized modules base: `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b`; implementation worktree HEAD is the same commit before readiness edits.
- Core: `origin/dev@e3a20f20df440dff49f8c6d1f73375451bea1d8c`; `origin/main@b1e517e60e669eaba15a18ecfa83ef5a9df65276`; immutable lightweight tag `v0.55.1` resolves to that main commit and tree `47984be5434d7ae65ed6908bf525a32053290337`.
- Core benchmark PR head identities: #665 `e3a20f20df440dff49f8c6d1f73375451bea1d8c`; #666 `1677f0c3beb32de49d82aa4dcf1bf4fcf06f07f0`; #667 `96aab447e00de4a09c19ed3a36632b9a46f7c222`; #668 `34c22d271e3653cfa7099ed7132d786c49437b21`; #669 `d17e6ba847599a1366436a3d3e993ba819cb0de7`; #670 `338f853ac2fde8299c11a5adb9c33ab883dead42`; #671 `21a97781ac3b467c2f69adc3344916d978d4328d`.
- Merged core reset PR #674 is `e3a20f20df440dff49f8c6d1f73375451bea1d8c` from reviewed head `51d3120170cd8e08e76881023e511868ce08d5b1`. Its accepted boundary keeps generic review-scope production semantics module-owned and makes the protected workflow consumer a separate downstream core adoption.
- Reviewed core caller paths at `origin/dev`: `.github/workflows/requirements-evidence.yml`, `scripts/pre_commit_code_review.py`, `scripts/pre-commit-quality-checks.sh`, `docs/agent-rules/20-repository-context.md`, and `docs/agent-rules/50-quality-gates-and-review.md`. The workflow currently derives positional PR paths, while the pre-commit helper intentionally remains staged explicit-file scope; these are migration consumers, not evidence that C14 already exists.

### Readiness decision

`READY FOR TEST AUTHORING`. `hatch run openspec validate code-review-14-scope-truth-and-differential-enforcement --strict` passed on 2026-08-19 against synchronized `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b`. No named C14 tests or production sources have been edited or executed for implementation evidence yet. Production edits remain prohibited until every prescribed test is authored, every exact selector is collected, the implementation mapping and `IMPLEMENTATION_CHECKPOINT.json` are frozen, and actual failing evidence is recorded.

## Amended task 3.12e red gate — 2026-08-21

- Checkpoint parent: commit `87f5db8854c2d9c34265f0d1b5a0fd34ee1f55f3`, tree `ee91201bf31e55f53cf06b41a1def7b629c18a43`; checkpoint commit `659c13e`.
- Exact frozen task selector digest: `sha256:dee179d142ba9e535c86141f636b8d7c109857549e675735d6f2fcc9bbaea063`; selector count `8`.
- Command: `.venv/bin/python` loaded task `3.12e` selectors from committed `IMPLEMENTATION_CHECKPOINT.json` and invoked that unchanged list through `python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings`.
- Outcome: `3 failed`, `5 passed` on Python 3.12.13. The exact missing production boundaries were `derive_core_0_55_1_install_handoff`, `verify_candidate_module_payload`, and `compose_post_base_capsule`; no failure was manufactured by changing assertions or selectors.
- Decision: `RED`. Production edit authorization is `GRANTED` only for the amended task 3.12e handoff, candidate-provenance, bootstrap, and composite-capsule behavior. Earlier loader-DTO evidence remains superseded.

Green command: the identical committed task `3.12e` selector list was loaded from `IMPLEMENTATION_CHECKPOINT.json` and invoked unchanged through pytest.

Green outcome: `8 passed`, `0 failed` on Python 3.12.13. `derive_core_0_55_1_install_handoff` consumes the real core object/marker/integrity/key/verifier surfaces; `verify_candidate_module_payload` binds immutable pre-release evidence while granting neither official-install nor `pr_range` authority; and `compose_post_base_capsule` copies the verified payload, generates `sealed-bootstrap-v2`, preserves the immutable base-root identity, and emits `capsule-composite-identity-v1`. After formatting, the identical set remained `8 passed`; repository-wide type/lint reported `0 errors`, `0 warnings`, `0 notes`, Ruff passed, and Pylint scored `10.00/10`. Task decision: `GREEN`.

## Frozen implementation red gate — 2026-08-20

- Committed checkpoint: implementation branch commit `67f1aa0a879931c3098792747b12c8c115750e73`; checkpoint parent commit `dd7490f5a1829dc9fb5b411a33eaa68e97e9c947`, tree `20e6827ae49b62a7524587985cb91df544e20dd3`.
- Verification command: `.venv/bin/python /private/tmp/verify_c14_checkpoint.py`. It verified the committed checkpoint against the frozen parent inputs, the non-empty and pairwise-disjoint 43-item assignment, exact global union, canonical mapping, immutable core identity, and all checkpoint digests.
- Red command: `.venv/bin/python /private/tmp/run_c14_red.py`. The runner loaded the checkpoint's sorted 366 `pytest_args`, invoked that complete selector set without substitution, and rejected collection drift. The per-selector exact argv is therefore bound by the committed selector digest rather than duplicated in this evidence file.
- Checkpoint file digest: `sha256:fb51280c67ea97962fce0af31227335bc00e0128cb4c30706294df3cf09ec7a6`.
- Global selector and observed collection digest: `sha256:7e515d42b9b267eb503bdb98e0d73feae0293e13660ad88f826f055cbd907b68`; collected count `366`.
- Implementation selector-map digest: `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.
- Pytest raw exit code: `1`. Exact outcomes: `365 failed`, `1 passed`; all `43/43` implementation tasks retained at least one independently failing frozen selector.
- Canonical per-selector outcomes digest: `sha256:99e9392aa548da1aaf2a2c5feeb4cf2a2727e1a134bf7171f63d888c7d53be4b`; canonical per-task outcomes digest: `sha256:aaa7c5a1851afdba13e3578e94805933235818341ff5c88b2c526242c6346391`.
- Representative red causes were the deliberately absent `scope`, `differential`, `sandbox`, and `toolchain` modules and the unimplemented schema/profile behavior in existing allowlisted sources. The single passing selector does not invalidate the gate because its mapped task also contains failing selectors and no Section 3 item is green.

Decision: `RED GATE SATISFIED`. Production edits may begin only in the frozen Section 3 order and allowlist, with the checkpoint reverified and each item's identical mapped selector set taken from red to green.

## Section 3 item evidence

### Task 3.1 — request and basic immutable range scope

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:616474d70a4631a71216b163368719310a7d774cb0f11d9cbf59904fa1a0d46f`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_scope.py::test_pr_assurance_rejects_positional_file_downgrade`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_scope_includes_changed_tests_by_default`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_scope_includes_committed_files_on_clean_checkout`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_scope_uses_merge_base_not_head_worktree`

Red outcome from the complete checkpoint run: `4 failed`, `0 passed`; the `specfact_code_review.run.scope` module was deliberately absent. Production edit authorization: `GRANTED` for task 3.1 only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the four frozen task-3.1 selectors above>`.

Green outcome: `4 passed`, `0 failed` on Python 3.12.13. `hatch run format`, `hatch run lint`, the six focused legacy command-discovery compatibility cases, and `git diff --check` also passed. Git discovery now resides in `run/scope.py`; the legacy command surface delegates its local worktree/full discovery there. Task decision: `GREEN`.

### Task 3.2 — claimed context and unique merge-base identity

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:325cbec569a17d2023a7a6b50eb2aa2cd5944c932f1df6c1278bf7fa46b37b71`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_scope.py::test_producer_never_self_asserts_pr_range_from_context_file`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_candidate_rejects_base_ref_mismatching_claimed_target_tip`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_multiple_best_merge_bases_is_unknown`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_without_context_is_preview`

Red outcome from the complete checkpoint run: `4 failed`, `0 passed`; claimed-context parsing/identity validation and canonical merge-base ambiguity evidence were absent. Production edit authorization: `GRANTED` for task 3.2 only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the four frozen task-3.2 selectors above>`.

Green outcome: `4 passed`, `0 failed` on Python 3.12.13. The resolver now freezes bounded regular outside-checkout context bytes, validates claimed provider/repository/event/target/head identity, retains optional project-runtime digests as claimed-only evidence, binds resolved target/head commit/tree identities, enumerates all best merge bases, and hashes the canonical sorted commit/tree candidate set. It emits only `range_candidate` or `range_preview`, never `pr_range`. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.3 — stable complete-index capture

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:863c2fcdd2437f26a1fd5e7f503659df9ddc16295bfb5810a6b3c9e53f678748`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_scope.py::test_index_intent_to_add_survives_captured_tree_omission`
- `tests/unit/specfact_code_review/run/test_scope.py::test_index_rejects_symlinked_governed_input`
- `tests/unit/specfact_code_review/run/test_scope.py::test_index_scope_derives_selection_from_captured_tree_during_concurrent_index_mutation`
- `tests/unit/specfact_code_review/run/test_scope.py::test_index_scope_imports_dependency_from_complete_index_tree`
- `tests/unit/specfact_code_review/run/test_scope.py::test_index_scope_reads_staged_blobs_not_unstaged_worktree`

Red outcome from the complete checkpoint run: `5 failed`, `0 passed`; index scope returned the task-3.1 unsupported-scope UNKNOWN placeholder and had no captured-index tree/materialization evidence. Production edit authorization: `GRANTED` for task 3.3 only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the five frozen task-3.3 selectors above>`.

Green outcome: `5 passed`, `0 failed` on Python 3.12.13. Index resolution now performs a bounded no-follow stable capture of the worktree-specific index plus content-addressed split-index dependencies, switches all subsequent index operations to the captured `GIT_INDEX_FILE`, invokes the deterministic post-capture mutation seam, derives stage/flag metadata and the complete tree from that capture, materializes the complete tree outside the checkout, selects only the captured HEAD-to-tree delta, preserves intent-to-add evidence omitted by `write-tree`, and verifies selected regular inputs by descriptor-relative no-follow reads. `index_tree` and `selection_tree` bind the same immutable tree. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.4 — symmetric detached range snapshots and exact renames

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:e0694f69d44250787482a7bd50c0ff151aef842baf0267edd0ebec05d4cf0118`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_scope.py::test_materialized_governed_input_uses_nofollow_regular_blob_identity`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_analysis_uses_materialized_commit_snapshots`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_mode_change_regular_to_symlink_is_unknown`
- `tests/unit/specfact_code_review/run/test_scope.py::test_range_rejects_symlinked_governed_python_input`

Red outcome from the complete checkpoint run: `4 failed`, `0 passed`; detached snapshots, symmetric tracked-regular manifests, and exact-rename evidence were absent at the checkpoint. Production edit authorization: `GRANTED` for task 3.4 only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the four frozen task-3.4 selectors above>`.

Green outcome: `4 passed`, `0 failed` on Python 3.12.13. Range resolution now materializes independent merge-base/head trees outside the checkout; records complete source-tree manifest digests and raw add/modify/delete statuses; derives unique identical-blob rename, copy, and ambiguity dispositions with a canonical digest; and applies the same object-type/Git-mode/descriptor-relative no-follow regular-input validation to both sides. Regular-to-symlink and symlinked governed inputs are retained as evidence and return `unsafe_governed_input` UNKNOWN. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5a — authorized target-tip policy bundle

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:cb173f7d7c6eba0482222cdf86142ddf72f4279eb2515d815f23e533006f680b`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_scope.py::test_candidate_policy_change_cannot_self_authorize_pr_range`
- `tests/unit/specfact_code_review/run/test_scope.py::test_policy_only_range_is_unknown_not_not_applicable`
- `tests/unit/specfact_code_review/run/test_scope.py::test_pyproject_nonpolicy_change_can_remain_non_governed`

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; the candidate-versus-target policy manifest and shadow-only candidate-policy decision were absent. Production edit authorization: `GRANTED` for task 3.5a only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the three frozen task-3.5a selectors above>`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. The resolver now materializes a separate read-only authorized target-tip policy bundle bound to source commit/tree and path/blob/content/section identities; records candidate policy path/status/base/head/section evidence plus canonical policy and candidate-change digests; treats policy-only candidate changes as shadow-only UNKNOWN; and leaves unrelated `pyproject.toml` metadata non-governed. Candidate policy never upgrades producer assurance. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5b — sealed Semgrep policy bundle

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:ae74bac4a0287215585bd8e73ffc47b296c9ceb705d88728957a050e0c693653`.

Frozen selector: `tests/unit/specfact_code_review/run/test_scope.py::test_semgrep_ai_bloat_rule_pack_is_governed_and_sealed`.

Red outcome from the complete checkpoint run: `1 failed`, `0 passed`; there was no explicit target-tip/signed-module Semgrep bundle resolver. Production edit authorization: `GRANTED` for task 3.5b only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings tests/unit/specfact_code_review/run/test_scope.py::test_semgrep_ai_bloat_rule_pack_is_governed_and_sealed`.

Green outcome: `1 passed`, `0 failed` on Python 3.12.13. The resolver now selects each clean-code and AI-bloat policy independently from the authorized target root or exact verified-module fallback boundary, reads it through bounded no-follow regular-file capture, materializes one preserved-layout read-only bundle, and binds source kind/path plus content and bundle digests. Missing or unsafe payloads return explicit UNKNOWN evidence. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5c — pinned pytest and Coverage policy location

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:39a2833a3f81ffeec0d21cc6db06413fbe27e157ab4f8f87503b18d7f9a3b508`; frozen selector set: the 16 checkpoint entries for task 3.5c covering the coverage-only range, all five Coverage source cases, bare-pyproject pytest fallback, empty TOML/INI precedence, and all seven pytest source-precedence cases.

Red outcome from the complete checkpoint run: `16 failed`, `0 passed`; pinned logical pytest/Coverage locator APIs and their selected/ignored-source evidence were absent. Production edit authorization: `GRANTED` for task 3.5c only.

Green command: `.venv/bin/python -c '<load task 3.5c selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `16 passed`, `0 failed` on Python 3.12.13. Pytest selection now binds the exact `pytest.toml`, `.pytest.toml`, `pytest.ini`, `.pytest.ini`, table-bearing `pyproject.toml`, `tox.ini`, `setup.cfg`, then bare-pyproject fallback semantics, including zero-byte primaries and ignored lower sources. Coverage binds exact `.coveragerc`, `.coveragerc.toml`, `setup.cfg`, `tox.ini`, `pyproject.toml` precedence. Both expose pinned loader/source-order/section/manifest identities and fail closed on unsafe, parse, shape, or version drift. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5d — Ruff source and extend-closure sealing

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:8fba4933d43d12985479d5526e17da3f2216b81b55cc9546ff4a53ce411632f3`; frozen selector set: the nine checkpoint entries for zero/one `.ruff.toml`, `ruff.toml`, or `pyproject.toml:[tool.ruff]`, multiple-source ambiguity, valid transitive `extend`, and escape/missing/cycle rejection.

Red outcome from the complete checkpoint run: `9 failed`, `0 passed`; no explicit Ruff locator or sealed transitive extend graph existed. Production edit authorization: `GRANTED` for task 3.5d only.

Green command: `.venv/bin/python -c '<load task 3.5d selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `9 passed`, `0 failed` on Python 3.12.13. Ruff policy resolution now recognizes only repository-root `.ruff.toml`, `ruff.toml`, or `pyproject.toml:[tool.ruff]`, emits explicit isolated mode when absent, rejects multiple or malformed sources, recursively seals at most 32 relative regular no-symlink `extend` nodes, rejects escape/missing/cycle cases, preserves layout read-only, and binds complete node/edge/content/materialized closure evidence. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5e — basedpyright primary/reference graph

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:b956447bf0d56880aeff4347d0bbb471a0447aa8a5ec79b4c549357b9ab82c83`; frozen selector: `tests/unit/specfact_code_review/run/test_scope.py::test_basedpyright_referenced_policy_files_are_governed`.

Red outcome from the complete checkpoint run: `1 failed`, `0 passed`; basedpyright primary, `extends`, and `baselineFile` inputs were not resolved or governed. Production edit authorization: `GRANTED` for task 3.5e only.

Green command: `.venv/bin/pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings tests/unit/specfact_code_review/run/test_scope.py::test_basedpyright_referenced_policy_files_are_governed`.

Green outcome: `1 passed`, `0 failed` on Python 3.12.13. Basedpyright policy resolution now accepts exactly one pinned primary (`pyrightconfig.json`, `[tool.pyright]`, or `[tool.basedpyright]`), resolves a bounded relative no-symlink `extends` graph and optional JSON-object `baselineFile` leaves, rejects conflict/escape/cycle/missing/shape/version failures, preserves every referenced payload in a read-only bundle, and binds node/edge/content graph evidence. Absence emits the exact generated-default boundary for later projection. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.5f — pinned Pylint source selection

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:37fc6b99911008aa03463e2fa470a548894cd5ddaa766b154201e9bc23ac9c06`; frozen selector set: the five checkpoint cases for `pylintrc`, `.pylintrc`, `pyproject.toml`, `setup.cfg`, and `tox.ini`.

Red outcome from the complete checkpoint run: `5 failed`, `0 passed`; there was no pinned Pylint source locator/default or explicit selected-source evidence. Production edit authorization: `GRANTED` for task 3.5f only.

Green command: `.venv/bin/python -c '<load task 3.5f selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `5 passed`, `0 failed` on Python 3.12.13. Pylint policy resolution now enumerates the frozen root source set, accepts exactly zero or one regular source, binds the selected payload/loader identity, emits the sealed pinned default when absent, rejects ambiguity/parse/version drift, and exposes the initial total safety projection with closed stdin and extension/plugin rejection for tasks 3.6/3.17. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.6 — per-snapshot configuration projections

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:c2cf791034d0809c4a7fd965d3d7a28c2ac0ef293d6aab0b26c41d809e589537`; frozen selector set: the 20 checkpoint cases covering Ruff force-exclude/per-file/namespace controls, seven Pylint input/no-member controls, and seven basedpyright include/exclude/ignore/baseline/strict/execution-environment controls.

Red outcome from the complete checkpoint run: `20 failed`, `0 passed`; generated per-snapshot projection APIs and total control catalogs were absent. Production edit authorization: `GRANTED` for task 3.6 only.

Green command: `.venv/bin/python -c '<load task 3.6 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `20 passed`, `0 failed` on Python 3.12.13. Ruff projection now materializes a read-only explicit policy with snapshot-root `src`, disabled cache/force-exclude/fix controls, and empty path-scoped suppression/target/namespace maps. Basedpyright projection sorts the exact eligible manifest, clears include/exclude/ignore/strict and every baseline reference, rejects non-empty strict/execution-environment controls, binds the verified project-runtime site-packages location, and launches only through an explicit generated project document. The Pylint projection clears the frozen input/no-member bypass family and seals stdin, confidence, discovery, and result controls. Canonical projection digests and typed generated-projection provenance are exposed. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.7 — snapshot invocation and reserved-import boundary

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:256c40534c573a41095fcbde3ec42cc86b93fcb42e8893093cac60f0d44a154f`.

Frozen selectors:

- `tests/unit/specfact_code_review/run/test_sandbox.py::test_analyzer_subprocesses_use_snapshot_invocation_context`
- `tests/unit/specfact_code_review/run/test_sandbox.py::test_snapshot_cannot_shadow_capsule_reserved_imports[pytest.py]`
- `tests/unit/specfact_code_review/run/test_sandbox.py::test_snapshot_cannot_shadow_capsule_reserved_imports[sitecustomize.py]`
- `tests/unit/specfact_code_review/run/test_sandbox.py::test_snapshot_cannot_shadow_capsule_reserved_imports[specfact_code_review.py]`
- `tests/unit/specfact_code_review/run/test_sandbox.py::test_snapshot_sitecustomize_cannot_run_during_analyzer_startup`

Red outcome from the complete checkpoint run: `5 failed`, `0 passed`; the snapshot invocation context, isolated bootstrap launch, startup-path exclusion, and reserved-import collision preflight module were absent. Production edit authorization: `GRANTED` for task 3.7 only.

Green command: `.venv/bin/python -c '<load task 3.7 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `5 passed`, `0 failed` on Python 3.12.13. The new invocation boundary binds member, snapshot, sealed configuration, capsule, output/temp, project-runtime, network, reserved-prefix, interpreter, and bootstrap inputs into one canonical context digest. Python launch is capsule-interpreter `-I -S` through the sealed bootstrap, with the snapshot excluded from startup `sys.path`; the preflight rejects top-level reserved module, stub, regular-package, namespace-package, and symlink collisions before dispatch. The context accepts the complete signed prefix catalog supplied by the task-3.12 toolchain contract; the test fixture default exercises the three frozen collision vectors. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.8 — Linux Bubblewrap isolation boundary

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:b833efe8d724b1bae8f726676143f608bc425d8259d492bd692667c532da1faa`; frozen selector set: the eight checkpoint entries covering static ELF identity, dynamic-loader rejection, pre-namespace objects, empty capsule root, sealed config mounts, root/capability/network policy, and absence of host-runtime mounts.

Red outcome from the complete checkpoint run: `8 failed`, `0 passed`; the OS-isolation module and Bubblewrap identity/profile validation APIs were absent. Production edit authorization: `GRANTED` for task 3.8 only.

Green command: `.venv/bin/python -c '<load task 3.8 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `8 passed`, `0 failed` on Python 3.12.13. The isolation boundary now accepts only the canonical Linux x86_64 static ELF Bubblewrap descriptor with no interpreter or needed-library records and bound content/descriptor digests; pre-namespace validation admits only the static executable and kernel pseudo-objects. Launch plans use the verified capsule as the empty root, expose no host runtime mounts/capabilities/network, mount every declared policy root read-only, and limit writable mounts to process-private output/temp roots. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.9 — non-adversarial runtime observation boundary

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:dd5a27ee6ad427268f3665500f0195c435e0fe5fe9dd9dd72f806ff3f2005750`; frozen selectors: the three checkpoint entries for cross-root evidence isolation, explicit non-adversarial observation limits, and adversarial runtime policy UNKNOWN.

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; the runtime-observation limitation statement and adversarial-policy disposition API were absent. Production edit authorization: `GRANTED` for task 3.9 only.

Green command: `.venv/bin/python -c '<load task 3.9 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. Each runtime observation now states the initial profile's non-adversarial-candidate limitation and mandatory UNKNOWN fallback. A run in which candidate Python executes while hostile behavior is claimed returns UNKNOWN under the bound `non_adversarial_candidate_runtime` assumption. Mount planning keeps the active member's writable roots separate and exposes no other side's evidence root. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.10 — range/index option widening and mutation rejection

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:95961b94cfa5f33ec3fcaa4433bdeffe05ee7a5588763aacbc0e88a4a7b5d2f9`; frozen selector set: the 15 checkpoint cases for index/range fix, preview-fix, mutation, omitted-enforcement, and all range-narrowing controls.

Red outcome from the complete checkpoint run: `15 failed`, `0 passed`; index/range mutation and narrowing controls were not rejected at the scope boundary and omitted range enforcement was not normalized to full. Production edit authorization: `GRANTED` for task 3.10 only.

Green command: `.venv/bin/python -c '<load task 3.10 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `15 passed`, `0 failed` on Python 3.12.13. Scope normalization now resolves omitted range enforcement to `full`; before any Git materialization, index and range reject fix, preview-fix, and mutation flags, while range additionally rejects positional-file, test exclusion, focus, path-filter, no-tests, severity-level, and non-full enforcement narrowing. Error messages identify the rejected option. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.11 — UNKNOWN and NOT_APPLICABLE evidence boundaries

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:39e087405fdab642d250384738458d23e85d0661d4ac4d294f5fa74f2ed91714`; frozen selector set: the 39 checkpoint entries covering unresolved Git, empty ranges/sides, profile membership/coverage, typed analyzer inputs, required-member error semantics, sealed target policy, complete-suite/test-candidate controls, Coverage policy/outcomes, stub-only applicability, and contracts activation.

Red outcome from the complete checkpoint run: `39 failed`, `0 passed`; the checkpoint run had no closed profile/applicability/evidence-classification APIs and unresolved/empty scope outcomes did not meet the frozen contract. Production edit authorization: `GRANTED` for task 3.11 only.

Green command: `.venv/bin/python -c '<load task 3.11 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `39 passed`, `0 failed` on Python 3.12.13. The runner now exposes the closed required/conditional `pr-range-v1` membership and version identities; aggregates valid FAIL separately from required UNKNOWN while preserving legacy fail-closed projection; binds typed generated inputs and equal eligible/invoked manifests; freezes target-tip policy and test-input roles before candidate execution; rejects candidate policy, collection/report hooks, item/unittest bypasses, missing candidates, custom Coverage exclusions/plugins, and hostile selection controls as UNKNOWN. Empty snapshots/sides are manifest-driven NOT_APPLICABLE, stub-only sides retain static members while excluding coverage/CrossHair, and valid threshold failures remain semantic FAIL with repaired baselines classified fixed. The two scope boundary cases also pass. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12a — canonical finding-location union

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:d5e98fd3df760dd42b7f29c00fbca44cf537cf05b1200e89c3e3a6d937348de1`; frozen selectors: the four checkpoint cases for exact UTF-8 byte spans, whole-line fallback, canonical location-kind coverage, and selector/non-source continuity exclusion.

Red outcome from the complete checkpoint run: `4 failed`, `0 passed`; the typed schema-1.6 location union and canonical source-span conversion module were absent. Production edit authorization: `GRANTED` for task 3.12a only.

Green command: `.venv/bin/python -c '<load task 3.12a selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `4 passed`, `0 failed` on Python 3.12.13. The new differential boundary exposes the canonical `source-span-v1` location with one-based lines, half-open UTF-8 byte columns, raw coordinate-system binding, and exact-versus-whole-physical-line precision. Exact UTF-16 adapter coordinates convert deterministically, and selector/infrastructure identities are rejected from source continuity as non-source UNKNOWN. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12b — signed analyzer toolchain lock projection

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:44841bd4c1ba80b90a575e9010b8e2923c91fe9a9a77cc6a2d43e84c4b90980d`; frozen selector set: the 24 checkpoint entries for canonical lock equality, complete dependency/native/runtime closure, immutable OCI/cache source validation, portable identities, exact installed membership, built-in payload integrity/boot, project/plugin attestation, host dependency exclusion, and package-manifest separation.

Red outcome from the complete checkpoint run: `24 failed`, `0 passed`; the signed toolchain-lock resource and toolchain validation/materialization API were absent, and the package dependency/resource contract did not yet expose the frozen analyzer environment. Production edit authorization: `GRANTED` for task 3.12b only.

Green command: `.venv/bin/python -c '<load task 3.12b selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `24 passed`, `0 failed` on Python 3.12.13. `pr-range-v1-toolchain-lock.json` was generated as the exact compact canonical checkpoint projection: `793458` bytes, SHA-256 `5a6ad4c97100127634272670c09e14eff5fd149daee5d9c63efa5480731c8373`, equal to frozen `toolchain_lock_projection_digest`. The toolchain boundary validates exact pins, cross-environment membership, dependency/native/runtime closure, immutable HTTPS OCI identities, portable storage-independent identities, verified-cache/signed-registry acquisition disposition, signed installed built-in payload shape, project lock/plugin attestation, and candidate dependency drift. Analyzer-only packages were removed from host `pip_dependencies`; `requests` remains the controller HTTP dependency. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12c — immutable OCI acquisition authorization

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:8283b062bcf446af73938386dce55d8e0c0f0a0bcb7c5a24dc9d920664f9344c`; frozen selectors: the three checkpoint redirect-chain downgrade, unauthorized-host, and cross-host credential-forwarding cases.

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; immutable OCI acquisition and per-hop redirect/credential authorization were absent. Production edit authorization: `GRANTED` for task 3.12c only.

Green command: `.venv/bin/python -c '<load task 3.12c selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. OCI acquisition now rejects HTTP downgrade and every redirect host outside the signed allowlist, records unauthorized hops with `credential_sent=false`, and permits only verified-cache or signed-registry digest records. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12d — safe OCI layer extraction boundary

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:16111de4e7f8dcd41bc4330ec4cd926d8d6d447a63bea613abcac88123447dcb`; frozen selector: `tests/unit/specfact_code_review/run/test_toolchain.py::test_runtime_capsule_fresh_cache_miss_installs_only_pinned_wheelhouse`.

Red outcome from the complete checkpoint run: `1 failed`, `0 passed`; fresh-cache capsule materialization and its index-disabled, lock-only install boundary were absent. Production edit authorization: `GRANTED` for task 3.12d only.

Green command: `.venv/bin/python -c '<load task 3.12d selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `1 passed`, `0 failed` on Python 3.12.13. Fresh-cache materialization now returns a storage-root-independent identity, creates a fresh environment root, disables indexes, and reconciles the installed set exactly to the locked plus bootstrap distributions, with no ambient member admitted. `hatch run format`, `hatch run lint`, the exact selector, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12e — verified installed module payload

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:0fb11957cea5b51368dbe39ae35368dcc439035d2138b702eed9f4335ca08179`; frozen selector set: the six checkpoint cases for complete installed-package traversal, approved loader/key/checksum/signature identity, and marketplace metadata without source/archive fields.

Red outcome from the complete checkpoint run: `6 failed`, `0 passed`; verified installed-module payload traversal and identity validation were absent. Production edit authorization: `GRANTED` for task 3.12e only.

Green command: `.venv/bin/python -c '<load task 3.12e selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `6 passed`, `0 failed` on Python 3.12.13. Installed built-in payload validation now requires official marketplace origin plus digest-shaped checksum/key identity and a non-empty signature, traverses the complete expected package as regular non-symlink files, rejects missing/content/link drift, and exposes only marketplace module/version/checksum/signature/key/loader/root identity—no source commit or archive locator. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12f — fresh capsule built-in boot without archive

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:37c8c8048fdadb23850709f4d0f7b14ef36c97c0299c98519a6fba5f9382b21d`; frozen selector: `tests/unit/specfact_code_review/run/test_toolchain.py::test_builtin_payload_boots_after_marketplace_archive_discard`.

Red outcome from the complete checkpoint run: `1 failed`, `0 passed`; capsule built-in installation from the loader-registered payload without retained archive bytes was absent. Production edit authorization: `GRANTED` for task 3.12f only.

Green command: `.venv/bin/python -c '<load task 3.12f selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `1 passed`, `0 failed` on Python 3.12.13. A verified loader-registered installed payload now copies into canonical `/opt/specfact/builtin/specfact_code_review` without consulting or requiring a marketplace archive/cache/locator and reports `archive_required=false`. `hatch run format`, `hatch run lint`, the exact selector, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.12g — attested project-runtime layer

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:d0e2e72bd67a1aa84ce58ff2afbd8777cb28ccb3ef6a241669427e1e6b6c3a34`; frozen selector set: the 13 checkpoint cases for target dependency-input binding, missing/untrusted/candidate/mutable rejection, reserved collisions, identical cross-snapshot identity, closed mount membership, snapshot-before-project import order, and attested pytest-plugin identity.

Red outcome from the complete checkpoint run: `13 failed`, `0 passed`; the project-runtime descriptor/layer validation and mount/import authorization boundary were absent. Production edit authorization: `GRANTED` for task 3.12g only.

Green command: `.venv/bin/python -c '<load task 3.12g selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `13 passed`, `0 failed` on Python 3.12.13. `project-runtime-layer-v1.schema.json` was generated as the exact compact canonical checkpoint document, SHA-256 `07c5ee03c66f90bacc816591b161d23288843a74be27abce12021fe133163fe3`, equal to `project_runtime_contract.digest`. Descriptor validation binds the authorized target and source-lock digest, builder/immutable OCI identity, `/opt/specfact` layer root, distribution/plugin attestations, and rejects missing, mutable, host-backed, candidate-target, observed-unattested, or reserved-collision input. Only the closed import-capable member set may mount it; one identical identity is bound to both snapshots and non-reserved lookup remains snapshot-before-project. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.13 — CrossHair infrastructure failure propagation

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:b1db64340f5a374ec5f5feba2ec5b6b4a53dcd1235f279db98cd00aacc6f3d3d`; frozen selectors: the mandatory CrossHair process-error and timeout propagation cases.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; timeout and documented process-error exits were swallowed instead of producing explicit UNKNOWN analyzer evidence. Production edit authorization: `GRANTED` for task 3.13 only.

Green command: `.venv/bin/python -c '<load task 3.13 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. CrossHair timeout and non-semantic process exits now emit an explicit `CROSSHAIR_INCOMPLETE_EVIDENCE` tool-error record with `execution_state=error` and `evidence_outcome=UNKNOWN`; successful parsed counterexample semantics remain unchanged. The shared finding model now carries optional authoritative execution/evidence fields. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.14a — complete pytest suite and frozen input roles

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:ca1ce3f79d63b55746c57e3e6e44f2473229466d53d67f7f2abb5c698143eaa9`; frozen selectors: complete production-change suite collection plus the four pinned `fnmatch_ex` basename/rooted/recursive match vectors.

Red outcome from the complete checkpoint run: `5 failed`, `0 passed`; complete suite planning and the pinned path-role matcher were absent. Production edit authorization: `GRANTED` for task 3.14a only.

Green command: `.venv/bin/python -c '<load task 3.14a selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `5 passed`, `0 failed` on Python 3.12.13. Suite planning scans every sealed `testpaths` root and accepted `python_files` pattern, collects matching test functions without source-derived narrowing, and reports uncollected changed candidates UNKNOWN. The path-role matcher reproduces pytest's basename behavior for separator-free patterns and whole-path `*/<relative-pattern>` behavior for rooted/recursive patterns. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.14b — pytest hook disposition boundary

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:9ca6edfa00f1c9065a665a3ca04a18e620a117495c3de94272e2dcd88d9bcafe`; frozen selectors: repository deselection through `pytest_collection_modifyitems` and complete execution/report hook catalog coverage.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; hook capability validation and the pinned total hook disposition catalog were absent. Production edit authorization: `GRANTED` for task 3.14b only.

Green command: `.venv/bin/python -c '<load task 3.14b selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. Repository and attested-project collection/report shaping hooks now fail closed as `pytest_plugin_capability_unsupported`; the pinned 9.0.3 hook catalog classifies collection plus setup/call/teardown/protocol/report/status hooks with no unclassified member. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.14c — Coverage private-output projection

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:a200b2a74d68289c25ca0d8fbd6ffcc67d9ff557130e55cb1a86f48999eed602`; frozen selector: `tests/unit/specfact_code_review/run/test_runner.py::test_coverage_projection_redirects_all_writable_paths_to_output_root`.

Red outcome from the complete checkpoint run: `1 failed`, `0 passed`; controller-owned Coverage writable-path projection was absent. Production edit authorization: `GRANTED` for task 3.14c only.

Green command: `.venv/bin/python -c '<load task 3.14c selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `1 passed`, `0 failed` on Python 3.12.13. Coverage projection redirects data, HTML, XML, JSON, and LCOV destinations into the process-private output root and exposes the exact writable manifest; repository plugins and non-empty exclusion/partial registries remain UNKNOWN. `hatch run format`, `hatch run lint`, the exact selector, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.14d — pytest projections, catalogs, observers, and outcome truth

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:bf4a7e0ce783593f94edf6207f7deefcedcf7cc9157e39604ed11deea8ecfbb5`; frozen selector set: the 34 checkpoint cases for path/output projection, option/config/collector catalogs, selection/short-circuit rejection, native controls, complete inventories, import order, observer/JUnit XPASS reconciliation, removed selectors, and PASS/FAIL/UNKNOWN lifecycle outcomes.

Red outcome from the complete checkpoint run: `34 failed`, `0 passed`; the complete pytest projection/catalog/observer/reconciliation surface was absent. Production edit authorization: `GRANTED` for task 3.14d only.

Green command: `.venv/bin/python -c '<load task 3.14d selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `34 passed`, `0 failed` on Python 3.12.13. Pytest projection now binds a snapshot-independent logical-policy digest, rebases sealed read paths per snapshot, rejects escaping inputs, redirects cache/log writes, and exposes complete pinned option/config/collector catalogs. Native and unittest candidate controls fail closed; observer/JUnit reconciliation treats passed-with-`wasxfail` as XPASS/FAIL; removed selectors and deselection/infrastructure errors are UNKNOWN; baseline fail repaired at head is fixed; assertion/skip/xfail/xpass are semantic FAIL; and attested project imports preserve snapshot-first order. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.14e — analyzer input kinds and Coverage manifest completeness

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:82827bc6eecc9b2db5515ebdac3baaef91b7f5a5d5e72f84fb684b3ebbfd9bc4`; frozen selectors: `.pyi` exclusion from runtime Coverage while retained by static members, and required runtime-measurable production-path reconciliation.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; the per-member analyzer input-kind manifest and Coverage required/observed reconciliation APIs were absent. Production edit authorization: `GRANTED` for task 3.14e only.

Green command: `.venv/bin/python -c '<load task 3.14e selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. `runtime-measurable-production-v1` now selects only regular `.py` for targeted Coverage/CrossHair while retaining `.py` and `.pyi` across Ruff, basedpyright, Pylint, and icontract static scan. Required and observed Coverage manifests must match exactly or return `coverage_input_manifest_mismatch` UNKNOWN. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.15 — Ruff governed-input invocation controls

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:a38fd0971533d1db99731dcad978750ebb4adfdafee3955efeaeebbe45b02f69`; frozen selectors: disabled snapshot cache, task-tag/E501 preservation, and fix-only suppression prevention.

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; Ruff snapshot-mode effective controls were not yet exposed or forced by the adapter. Production edit authorization: `GRANTED` for task 3.15 only.

Green command: `.venv/bin/python -c '<load task 3.15 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. The Ruff projection default is pinned to 0.15.12; always emits `--no-cache`/`--no-force-exclude`; exposes an empty cache-write manifest; forces fix/fix-only and overlong-task-comment exemptions off; and retains original task tags as evidence without allowing them to suppress E501. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.16 — Radon sealed full-result controls

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:8892870d73dc29b6ce5e9b5c3b5a4eed1200fb177532c5e48d99463dc10d4cfe`; frozen selectors: candidate Radon config non-authority and sealed full-result option coverage.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; a controller-owned Radon full-result policy API was absent. Production edit authorization: `GRANTED` for task 3.16 only.

Green command: `.venv/bin/python -c '<load task 3.16 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. The pinned `radon-full-result-v1` projection ignores candidate `radon.cfg` narrowing, clears exclude/ignore/output targets, admits the full CC A–F and MI A–C result ranges, uses an empty controller cwd/private home, and sanitizes `RADONCFG`. Version drift returns UNKNOWN. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.17 — Pylint result/input controls

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:daf0b996aa73cb3455b6fcda5833ab12ae814e463a5b879ccf1f0dba9b968a25`; frozen selectors: confidence/errors-only/from-stdin controls and pre-applicability init-hook/load-plugin/extension-package rejection.

Red outcome from the complete checkpoint run: `6 failed`, `0 passed`; Pylint's total control projection and unsafe dynamic-extension disposition were absent. Production edit authorization: `GRANTED` for task 3.17 only.

Green command: `.venv/bin/python -c '<load task 3.17 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings with that unchanged list>'`.

Green outcome: `6 passed`, `0 failed` on Python 3.12.13. Pylint projection forces the complete confidence set, `errors-only=false`, `from-stdin=false`, and closed discovery/input controls; non-empty init hooks, repository plugins, and extension allow-list aliases return explicit UNKNOWN before no-impact derivation. `hatch run format`, `hatch run lint`, the exact selector set, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.18 — basedpyright explicit project projection

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:c7bf0dcc1db82ccaa7c4057ca5c9663e07185f97494681a49edfde5f7366b8a4`; frozen selectors: referenced-policy/baseline governance with disabling, generated no-config default, per-snapshot relative-path rebasing, and escape rejection.

Red outcome from the complete checkpoint run: `4 failed`, `0 passed`; the basedpyright runner projection API did not expose the full governed-reference/default/rebase boundary. Production edit authorization: `GRANTED` for task 3.18 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the four unchanged task 3.18 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `4 passed`, `0 failed` on Python 3.12.13. The basedpyright policy now records the exact generated-default or selected-graph identity, retains governed reference/baseline files while removing effective baseline controls, rejects escaping policy paths, rebases directory-scoped eligible inputs into each immutable snapshot, and carries a snapshot-independent logical policy digest. The earlier basedpyright scope regression surface also passed (`8 passed`); `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.19 — Semgrep sealed union and explicit scanned-input evidence

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:48ae8d65f23a76aea94a8b8500f630e0f2fbdcc86d61ce1a70f557219dba46ca`; frozen selectors: nosem-disabled invocation, pass-union reconciliation, rule-target narrowing rejection, scanned/eligible input equality, and signed-module fallback.

Red outcome from the complete checkpoint run: `4 failed`, `1 passed`; signed-module fallback already held, while the invocation, pass reconciliation, rule-pack validation, and scanned-path evidence APIs were absent. Production edit authorization: `GRANTED` for task 3.19 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the five unchanged task 3.19 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `5 passed`, `0 failed` on Python 3.12.13. Each Semgrep pass must independently reconcile its scanned/skipped manifest against the exact eligible inputs, path-targeting rule controls are rejected before launch, the controller appends `--disable-nosem`, and the existing signed-module fallback remains valid. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.20 — suppression catalog and conservative finding multiset

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:262d11f194a607d21dc7d6b1c65a95047b16a36063a34b5403736ad9440e0166`; frozen selectors: all 76 suppression-catalog, occurrence-continuity, finding-multiset, exact-rename, catalog-identity, and signed-resource vectors.

Red outcome from the complete checkpoint run: `76 failed`, `0 passed`; the differential and suppression APIs plus authenticated catalog resource were absent. Production edit authorization: `GRANTED` for task 3.20 only.

Green command: `.venv/bin/python -c '<load task 3.20 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -q --tb=short --disable-warnings --import-mode=importlib with that unchanged list>'`.

Green outcome: `76 passed`, `0 failed` on Python 3.12.13; the full differential test file also passed (`79 passed`). The exact canonical suppression resource SHA-256 is `32346a8a0848bc024b1330c37ab5bdcf12f092460cce904ebbab831f6d276375`, matching the checkpoint and authenticated package-resource entry. Registered comment-token controls, unchanged-control quarantine, conservative rename/fix outcomes, source continuity, multiset surplus, and catalog activation drift now produce the frozen decisions. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.21 — lifecycle/blocking separation

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:bd0db3e3e0a497cae1246ac489758116fd9e05ac2f45fe66c08bbcfce3cb8010`; frozen selectors: fixable-error blocking and scorer preservation.

Red outcome from the complete checkpoint run: `1 failed`, `1 passed`; scoring already retained the error, but `ReviewFinding.is_blocking()` incorrectly treated autofix availability as if the fix had been applied. Production edit authorization: `GRANTED` for task 3.21 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the two unchanged task 3.21 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. The canonical finding model now separates lifecycle `status`, `differential_state`, `autofix_available`, derived `blocking`, and the C14-null `waiver_reference`; an open error remains blocking whether or not an autofix exists. The legacy scorer retains its existing remediation-aware score/verdict projection independently. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.22 — schema 1.6 authoritative assurance derivation

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:d8223398a0a44d0e868e4e6aab972fa0f87b85ae309dea572af0c523ddf2a34a`; frozen selectors: aggregate precedence, fixed-baseline exclusion, suppression-catalog binding, non-misleading UNKNOWN summary, the eight full/shadow legacy projection combinations, and missing-authoritative-status handling.

Red outcome from the complete checkpoint run: `13 failed`, `0 passed`; schema 1.6 report construction, projection, and readback APIs were absent. Production edit authorization: `GRANTED` for task 3.22 only.

Green command: `.venv/bin/python -c '<load task 3.22 selectors from committed IMPLEMENTATION_CHECKPOINT.json; invoke current interpreter -m pytest -ra -v -q --tb=short --disable-warnings --import-mode=importlib with that unchanged list>'`.

Green outcome: `13 passed`, `0 failed` on Python 3.12.13. Schema 1.6 now derives authoritative PASS/FAIL/UNKNOWN/NOT_APPLICABLE after lifecycle classification, gives a validated blocker precedence over concurrent unknown evidence while retaining the unknown flag, excludes fixed baseline evidence from blockers, binds the suppression-catalog identity, and derives the legacy verdict/exit matrix including shadow mode. Missing authoritative schema-1.6 status reads as UNKNOWN. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.23 — schema 1.6 preservation through consumers and enrichment

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:064b614d615ca0b5e4405c2bbdf566a86fb1d4e890f8e677a07dfd5c04affa14`; frozen selectors: pre-commit authoritative UNKNOWN exit, cleanup enrichment preservation, and Requirements evidence attachment preservation.

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; the pre-commit status consumer and Requirements attachment helper were absent, and cleanup refresh downgraded schema 1.6 to 1.3. Production edit authorization: `GRANTED` for task 3.23 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the three unchanged task 3.23 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. Cleanup and Requirements-context enrichment preserve schema 1.6 authoritative status, exit, scope, and analyzer evidence; the pre-commit consumer uses schema 1.6 `assurance_status` before legacy changed-line logic, retaining UNKNOWN as non-zero and NOT_APPLICABLE as zero outside shadow. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.24 — closed schema 1.6 consumer compatibility matrix

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:1857ba9f42cc071e9dafedfc6f999e4abb134cdc0d4c9c69d50041a812b3059e`; frozen selectors: closed matrix validation and suppression-catalog identity mismatch rejection.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; the signed static consumer compatibility matrix resource did not exist. Production edit authorization: `GRANTED` for task 3.24 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the two unchanged task 3.24 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. The closed schema 1.6 matrix exercises PASS/FAIL/UNKNOWN/NOT_APPLICABLE, retains the legacy schema-less ledger fixture, binds checkpoint/resource/package/profile/report/static-envelope suppression-catalog identities, and rejects a mismatched accepted envelope as UNKNOWN. The authenticated matrix SHA-256 is `7146f30b09bab677acb9981cd9d60f814841915b8bb2ba950ca9fbcff6f6438f`; manifest validation and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.25 — ledger authoritative PASS/FAIL transitions

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:e826c63b238af8f9a10a16bc5bf8552a4d8f58c3fba054ca4876ecf2dbd2d1ed`; frozen selectors: authoritative FAIL penalty/block streak and PASS reward/pass streak with report persistence.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; ledger updates still trusted the legacy reward projection and omitted canonical report digest persistence. Production edit authorization: `GRANTED` for task 3.25 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the two unchanged task 3.25 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13. Schema 1.6 PASS/FAIL now use authoritative verdicts, deterministic +5/-5 reward transitions, the corresponding pass/block streaks, and complete canonical `report_json` plus `report_digest`; 11 legacy ledger regressions also passed. UNKNOWN/NOT_APPLICABLE neutral transitions remain deliberately red-owned by the next frozen checkpoint. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN` for the mapped PASS/FAIL checkpoint.

### Task 3.26 — neutral ledger statuses and Supabase persistence compatibility

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:88943daf14f3234d443051b53bd7ba85c3c6d7215e809beafedd86c69d1f521a`; frozen selectors: authoritative UNKNOWN and NOT_APPLICABLE neutral reward/streak persistence.

Red outcome from the complete checkpoint run: `2 failed`, `0 passed`; both neutral statuses still inherited the score-derived +5 reward and legacy non-FAIL streak behavior. Production edit authorization: `GRANTED` for task 3.26 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the two unchanged task 3.26 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `2 passed`, `0 failed` on Python 3.12.13; the full ledger suite also passed (`25 passed`). UNKNOWN and NOT_APPLICABLE persist verbatim as zero-reward neutral audit events without changing either streak or triggering bonuses/penalties. The Supabase DDL now admits both statuses and adds nullable `report_json`/`report_digest` through a backward-compatible migration while preserving legacy rows; local and Supabase run payloads share the canonical report fields. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.27 — canonical complete-range merge guidance

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:d9b72cbcd0997434362af99f32911007bc6be464b34fa2530275857ad4b915e9`; frozen selectors: docs parity, no-execution AI workflow instructions, and installed updater guidance.

Red outcome from the complete checkpoint run: collection stopped with an import error before selector execution because the canonical target-style conflict helper expected by the docs/CLI contract surface was absent; the complete PR-range guidance could not be validated. Production edit authorization: `GRANTED` for task 3.27 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the three unchanged task 3.27 selectors from IMPLEMENTATION_CHECKPOINT.json>`.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13; the complete related docs/updater/CLI regression surface also passed (`37 passed`). All seven canonical guidance surfaces and the no-execution CLI instructions now require range/base/head/event-context/full evidence, identify local output as `range_preview`, reserve promotion for the protected consumer, and keep staged positional review explicitly `explicit_files`. The restored targeting-style validator rejects positional files mixed with `--scope` or `--path`. `hatch run format`, `hatch run lint`, and `git diff --check` passed. Task decision: `GREEN`.

### Task 3.28 — immutable core 0.55.1 compatibility smoke

Pre-edit checkpoint verification: `PASS` on 2026-08-20 with implementation selector-map digest `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.

Frozen selector digest: `sha256:b4d51b8de2f4f25189a38390087fc00766434da0686e3c4a57ec68cfa3dfac78`; frozen selectors: exact core runtime matrix load, immutable tag/commit/tree workflow identity, and PEP 440 local-alias rejection.

Red outcome from the complete checkpoint run: `3 failed`, `0 passed`; the current controller environment still had core 0.54.0, and the PR orchestrator lacked the dedicated exact-core job and local-version rejection vector. Production edit authorization: `GRANTED` for task 3.28 only.

Green command: `.venv/bin/python -m pytest -ra -v --import-mode=importlib -q --tb=short --disable-warnings <the three unchanged task 3.28 selectors from IMPLEMENTATION_CHECKPOINT.json>` after installing local immutable core commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` into the task environment.

Green outcome: `3 passed`, `0 failed` on Python 3.12.13. The workflow now owns a dedicated Python 3.11–3.13 exact-core job, checks `refs/tags/v0.55.1`, commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276`, tree `47984be5434d7ae65ed6908bf525a32053290337`, creates a fresh environment, installs without cache, runs the schema 1.6 matrix selector, and proves `===0.55.1` rejects `0.55.1+vendor` whereas ordinary `==0.55.1` does not. Workflow YAML parsing, `hatch run format`, `hatch run lint`, and `git diff --check` passed; exact core 0.55.1 remained installed. Task decision: `GREEN`.

## Release readiness evidence — 2026-08-21

### Exact core 0.55.1 handoff matrix

Fresh isolated CPython 3.11.15, 3.12.13, and 3.13.14 environments installed the immutable core tag from detached commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337`. Each environment reported core package version `0.55.1` and passed the schema 1.6 end-to-end, installed-handoff derivation, and candidate-payload identity selectors (`3 passed` per interpreter). `===0.55.1` accepted only `0.55.1`; it rejected `0.55.1+vendor`, while ordinary `==0.55.1` admitted that local alias and is therefore not release-authoritative.

The core trust surfaces required by the amended boundary are present in the tag. `module_discovery.py`, `module_installer.py`, and `module_package.py` are byte-identical between immutable v0.55.1 and the freshly fetched current core `origin/dev` observed during readiness validation. C14 derives a module-owned handoff from those existing granular records; it does not depend on an unpublished later core implementation.

### Task 4.2 adjudicated benchmark

Live GitHub bodies and states for core #665–#671 were refreshed on 2026-08-21. The retained #665 release corpus explicitly requires an exact range, unique merge base, changed-test/policy coverage, symmetric evidence, independent verdicts, and UNKNOWN for unresolved facts; #666–#671 remain historical remediation/forensic inputs rather than reusable proof.

Command: `hatch run pytest -q` over the eight exact selectors for staged-versus-unstaged index content, positional downgrade rejection, candidate-policy self-authorization rejection, policy-only range UNKNOWN, advanced-base-tip merge-base selection, pure-rename continuity, off-added-line introduced blockers, and head-config false-green prevention.

Outcome: `8 passed`, `0 failed` on Python 3.12.13. Task decision: `GREEN`.

### Task 4.3 release metadata

After the exact-core matrix passed, the permitted feature-branch release metadata was set to module version `0.49.0` and exact `core_compatibility: '===0.55.1'`; the changelog records the additive C14 range/differential/schema 1.6 release. The focused manifest, exact-core workflow, and schema consumer tests passed (`12 passed`, `2 deselected`). Archives, checksums, signatures, sidecars, and `registry/index.json` remain untouched for canonical post-merge generation. Final Linux cache-miss/cache-hit capsule and empty-Bubblewrap authority remains pending protected CI and canonical publication evidence; task 4.3 is not yet complete.

### Final feature-branch gates — 2026-08-21

After clean-code remediation, the candidate module's full local review completed in 39.11 seconds with `138 findings (0 blocking)`. The preceding runs reduced the blocker count from 40 to 14, then 1, then 0 without weakening any detector or accepted C14 behavior. Focused regression validation after the refactor passed `191` tests. The retained non-blocking review diagnostics are explicit pre-merge exceptions: `79` advisory contract-coverage findings across the frozen public C14 model/API surface; structural single-owner file-size/complexity diagnostics required by the closed C14 source allowlist; targeted local coverage warnings whose Linux capsule/cache/Bubblewrap paths are protected-CI owned; and one CrossHair environment error caused by its subprocess lacking `beartype`, while the canonical contract gate itself passed. Adding post-checkpoint decorators, splitting the mandated owner files, or pretending that macOS supplied Linux namespace authority would alter the accepted contract or evidence boundary. These exceptions grant no `pr_range` or Linux authority and remain visible in the JSON evidence.

The final checksum-only dev-PR bridge set `specfact-code-review` `0.49.0` to `sha256:bc205355b32388d968ef30919bd57f30d147f46472c9099e8c19fc8f8b5d5470`; `core_compatibility` is exactly `===0.55.1`, and the registry remains untouched. Filesystem signature/version-bump verification accepted all seven manifests with the local missing-public-key allowance. `git diff --check`, format, type-check (`0` errors), Ruff/Pylint (`10.00/10`), YAML, bundle imports, strict OpenSpec, and contract tests (`28 passed`) all passed. Both `smart-test` and the complete test gate passed all `1344` tests; the only warnings were two third-party `lark` deprecations.

The immutable core compatibility smoke was then repeated against the final candidate bytes under CPython `3.11.15`, `3.12.13`, and `3.13.14`. Each exact-core environment reported package version `0.55.1` and passed the same three schema-1.6/runtime-handoff/candidate-identity selectors (`3 passed` per interpreter). Each environment again proved `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, and ordinary `==0.55.1` is too broad. Protected Linux cache-miss/cache-hit and empty-Bubblewrap evidence remains pending CI, so task 4.3 is not yet adjudicated complete.

The required explicit-range/full self-review then ran from committed head `fa430434204117879aef2560e523255f0164dd95` / tree `1114200666468f6974d29495d69ee77497176e2a` against synchronized `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b` / tree `0b1d0cc80b671c561ddadc3d50f395b1959d0dd7`, using the outside-checkout regular GitHub context file for public issue `#416`. Scope resolution passed with exactly one merge-base candidate (`c3eda08c732267dc3614130f5f36bcd473182d0b`), `assurance_kind=range_candidate`, context digest `sha256:cc3df6f52a62d899e0ee7f150db27c30d3d5ee54939488b04f5d516f96c88594`, and no blocking findings. Schema 1.6 correctly remained authoritative `UNKNOWN` / exit `1` with `snapshot_differential_execution_unavailable`: the module-owned local producer cannot execute or self-promote protected-consumer `pr_range` authority. This is truthful explicit-range evidence, not a PASS claim; protected CI must independently verify and promote the candidate.

### Task 4.3 protected-runtime gate correction

Pre-merge audit found that the original synthetic cache/Bubblewrap unit selectors validated signed descriptors and launch plans but did not perform task 4.3's required live GHCR acquisition or namespace boot. Merge remained blocked. A new allowed workflow-contract selector, `test_pr_orchestrator_runs_real_c14_capsule_smoke`, was authored first and failed `1 failed` because the exact-core job lacked that runtime step. The workflow was then extended, without changing module payload bytes or signed outputs, to run per CPython 3.11–3.13: byte/digest equality between the checkpoint and signed toolchain resource; real signed-registry cache-miss acquisition with HTTPS/final-URL/redirect evidence; complete verified-cache materialization and offline/index-disabled installation; copied-cache network-forbidden materialization below a second storage root; exact installed set, lock identity, final-root manifest/bytes, and interpreter/stdlib/extension/loader/library/bootstrap comparisons; signed static Bubblewrap hash verification; and a real `--unshare-all --unshare-net` empty-root boot using only the capsule loader/libraries/interpreter. The selector then passed (`1 passed`), YAML validation passed, and task 4.3 remains incomplete until the protected Linux matrix returns its evidence.

Protected run `32524928577` at candidate commit `d863e771c06ea5b89790358d001cbb106b42d805` reached the live registry step on all three matrix versions but each job failed before download with `oci_acquisition_failed:401 Client Error: Unauthorized` at the trusted `https://ghcr.io/token` realm. Fresh package metadata showed `specfact-code-review-analyzer-runtime` is private, while the job granted only `contents: read` and supplied no credential. A strengthened workflow-contract test first failed (`1 failed`) on the exact missing fragments: job-scoped `packages: read`, ephemeral GitHub actor/token inputs, and credential plumbing to the two cache-miss calls. The exact selector then passed (`1 passed`) after the workflow granted `packages: read` only to the compatibility job and passed `github.actor:github.token` to the existing client. The client uses those credentials only at the same-host HTTPS token realm, obtains a scoped bearer token, and continues to send no credential on redirects. The complete workflow-contract file passed (`9 passed`); strict OpenSpec, YAML parsing, lint/type checks, `git diff --check`, and a focused full-enforcement SpecFact review of the changed Python test (`0 findings`) passed. Task 4.3 remains incomplete pending a new protected run; a repeated 401 after this correction would establish that the private package still needs repository Actions access in GitHub package settings rather than justify weaker or simulated evidence.

After `nold-ai/specfact-cli-modules` received package Actions read access, protected attempt 2 of run `32525570996` authenticated and resolved the exact checkpoint manifests, then exposed `capsule_materialization_failed:[Errno 26] Text file busy` while launching the extracted `bwrap-static`. The signed descriptor already requires `launch_mode=same-open-descriptor`; production had verified the pathname and then executed the pathname rather than that same descriptor. The new regression `test_offline_install_executes_verified_bubblewrap_from_same_open_descriptor` was authored first and failed (`1 failed`) because `subprocess.run` received neither `/proc/self/fd/<n>` nor `pass_fds`. Production now opens the native executable read-only/no-follow, validates executable regular-file mode, hashes and stability-checks that descriptor, rewinds it, and launches exactly `/proc/self/fd/<n>` with only that descriptor inherited. The focused test passed, followed by the complete toolchain/workflow surface (`59 passed`), format, type/lint (`0` diagnostics; Pylint `10.00/10`), strict OpenSpec, and `git diff --check`. Task 4.3 remains incomplete until protected Linux proves the corrected descriptor-bound launch and subsequent cache/Bubblewrap identities.

Signed-head run `32526962192` proved that `/proc/self/fd/<n>` was used but still returned `ETXTBSY`, exposing the lower-level extraction defect: both OCI layer extraction and cache publication called `tempfile.mkstemp()` while discarding its returned writable descriptor. For an extracted executable, `os.replace()` preserved that still-open writable inode and Linux correctly refused execution. The regression `test_oci_extraction_closes_temporary_creator_descriptor` was authored first and failed (`1 failed`) because `os.fstat()` still succeeded on the captured creator descriptor after extraction. Both sites now write through `os.fdopen()` around the exact creator descriptor so it closes before publication or execution. The two descriptor-focused selectors passed, followed by the complete toolchain/workflow surface (`60 passed`), format, type/lint (`0` diagnostics; Pylint `10.00/10`), strict OpenSpec, and `git diff --check`. Task 4.3 remains pending fresh signed protected-Linux evidence.

### Post-review hardening and refreshed local gates — 2026-08-21

The signed-head review was treated as new input rather than reusing earlier evidence. Sixteen new exact regressions were authored before the corresponding production changes and initially failed `16 failed`, covering invalid source coordinates, missing packaged checkpoint/catalog resources, incomplete invocation manifests, pytest process/JUnit disagreement and non-PASS outcomes, async/class selector discovery, Radon ambient cwd isolation, OCI absolute-symlink containment, explicit public-key handoff authority, payload mutation after handoff, missing ledger assurance status, omitted CLI enforcement, unrecognized CrossHair output, pre-commit authoritative status, and numeric schema ordering. Additional workflow red cases then proved unquoted tree revision/redaction defects, and focused cache/consumer cases proved false-green behavior for schema `1.10` and repeated correspondence work. The implementation fail-closes each boundary; the expanded review-regression surface passed `616 passed` after correction of two test-local placement/assertion mistakes.

The accepted differential evidence requires an exact forbidden-cost value per distinct finding anchor. The implementation now caches the shared forward/suffix matrices per source pair and the forbidden result per anchor, reducing two distinct-anchor classifications from six dynamic-programming builds to four while retaining one exact forbidden solve for each unique anchor. A further approximation or single global forbidden solve would change the accepted signed evidence semantics, so the remaining per-unique-anchor work is an explicit review exception rather than a silent performance claim.

The review also observed that nested fragments in `project-runtime-layer-v1.schema.json` do not independently declare every JSON object type. That signed resource is frozen byte-for-byte by `IMPLEMENTATION_CHECKPOINT.json` as `project_runtime_contract=sha256:07c5ee03c66f90bacc816591b161d23288843a74be27abce12021fe133163fe3`; changing it after the red checkpoint would invalidate the closed task-3.12g contract and task-4.3 equality gate. Production separately verifies mapping/list/member shapes and returns UNKNOWN on malformed descriptors. The resource remains unchanged as an explicit checkpoint-preservation exception; a future schema revision may add redundant structural declarations only through a new checkpoint/version, never by mutating this signed v1 identity.

Fresh final local gates on the hardened payload passed: `hatch run format`; `git diff --check`; type-check with `0 errors, 0 warnings, 0 notes`; Ruff and Pylint with `10.00/10`; YAML validation of seven manifests plus the registry; bundle-import validation; strict C14 OpenSpec validation; `28 passed` contract tests; `1375 passed` smart-test; and `1375 passed` complete tests. The two complete-suite warnings are third-party `lark` deprecations. Full enforcement on the changed Python surface initially found two clean-code complexity blockers; a behavior-preserving helper extraction removed both, after which `143 passed` focused command/runner tests and the type/lint gates remained green and the repeated review reported `387 findings (0 blocking)`. The retained warnings fall within the previously documented frozen-owner/contract-coverage/local-runtime exceptions. Filesystem checksum/version verification against `origin/dev` accepted all seven manifests with the documented local missing-public-key allowance. The signing tool canonically removed the stale bot signature after payload changes and set the unsigned PR checksum to `sha256:b52f8e20c45214352d1f62416f8c6941c5aef0fbce65939ac911ee5c30a2a942`; bot signing must regenerate it after push.

Fresh isolated CPython `3.11.15`, `3.12.13`, and `3.13.14` environments each installed immutable core `0.55.1` from commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337`, loaded the current candidate module, and passed the same three schema/handoff/candidate-identity selectors (`3 passed` per interpreter). Every environment reconfirmed that `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, and ordinary `==0.55.1` admits that local alias. GitHub Actions access was configured at `https://github.com/orgs/nold-ai/packages/container/specfact-code-review-analyzer-runtime/settings`. Task 4.3 remains incomplete until a freshly signed head passes the protected Linux cache-miss/cache-hit and empty-Bubblewrap matrix.

The committed post-review range run bound synchronized base commit `c3eda08c732267dc3614130f5f36bcd473182d0b` / tree `0b1d0cc80b671c561ddadc3d50f395b1959d0dd7` to candidate commit `af558b246e633b9609b5d25579f7a5c429601749` / tree `8dcd49b17addd3a24677fc99611ef46806da3c2d`. It resolved exactly one merge base, emitted `assurance_kind=range_candidate`, context digest `sha256:72ceea4548b1a29ef200d2f2d9c315a2b0bc4bd9d00b2e0cd5c96566526c841b`, and reported `0 findings (0 blocking)`. Schema 1.6 remained truthfully `UNKNOWN` with `snapshot_differential_execution_unavailable`; only the protected consumer may promote it.

The canonical signer then added signature `PUvZ5dbtFe/mVeVobYAAP7DHL/FMNBWO7QKxZMI+1ET1emmQ6/4YKdt+NDO6SPgZbN8/Dlo1KCy9W3MdOGFcCA==` without changing checksum `sha256:b52f8e20c45214352d1f62416f8c6941c5aef0fbce65939ac911ee5c30a2a942`, producing bot commit `4ada53b5c124d0bbebd1334a763bac4f08619830` / tree `2444696cd9af04751e7ab083fadf442474462586`. GitHub marked workflows directly triggered by that bot-authored head `action_required` with no executable jobs. This evidence-only human-authored commit changes no module payload byte and exists to trigger protected CI against the unchanged signed manifest.

Protected run `32531532061` at human trigger commit `7a0749f4a184b059919fbf3a27134738ba564565` proved package access through the corrected settings surface `https://github.com/orgs/nold-ai/packages/container/specfact-code-review-analyzer-runtime/settings`, immutable core/tag/tree installation, exact-version alias rejection, and the schema 1.6 smoke on CPython 3.11–3.13. All three live capsule jobs then failed at descriptor-bound Bubblewrap launch with the same Ubuntu 24.04 host-policy error: `capsule_materialization_failed:offline analyzer installation failed: bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. The failure occurs while an unprivileged Bubblewrap configures the isolated namespace loopback interface; it is not an OCI authorization, signed-identity, core-compatibility, or schema failure. The remediation preserves `--unshare-all` and adds `--cap-drop ALL` to both the production offline-install and final empty-root boot commands, while only the protected ephemeral-runner smoke Python process is invoked through `sudo --preserve-env=...`; it does not share host networking or disable Ubuntu AppArmor. The strengthened descriptor and workflow selectors were authored first and failed `2 failed` on the absent capability drop/elevated invocation, then passed `2 passed`. A further step-local regression exposed and failed on an initially misplaced elevation before the workflow bound `sudo` to the named live capsule step and restored the ordinary core-alias step; it then passed. The complete toolchain/workflow surface passed `71 passed`. Task 4.3 remains incomplete pending a freshly signed protected Linux matrix proving cache-miss/cache-hit materialization and the empty-root boot under this boundary.

Post-remediation local gates passed on 2026-08-22: format; `git diff --check`; type-check with `0 errors, 0 warnings, 0 notes`; Ruff/Pylint with `10.00/10`; YAML and registry validation; bundle-import validation; strict C14 OpenSpec; `28 passed` contracts; `1375 passed` smart-test; and `1375 passed` complete tests with only the same two third-party `lark` deprecations. The canonical signing utility removed the stale signature and refreshed the unsigned dev-PR checksum to `sha256:1e35b1e0a06a53645815c3f0b1f663b8b1923ae39bf901e72dba1e4b1536ec88`; filesystem checksum/version verification accepted all seven manifests with the repository-approved local missing-public-key allowance. Fresh isolated CPython `3.11.15`, `3.12.13`, and `3.13.14` environments each installed immutable core `0.55.1` from commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337` and passed the three exact schema/handoff/candidate selectors (`3 passed` per interpreter); each reconfirmed that `===0.55.1` accepts only the tested identity, rejects `0.55.1+vendor`, and ordinary `==0.55.1` admits that alias.

The post-remediation explicit range/full review bound synchronized base commit `c3eda08c732267dc3614130f5f36bcd473182d0b` / tree `0b1d0cc80b671c561ddadc3d50f395b1959d0dd7` to candidate implementation commit `64bd07dc2e0ad5fb7e1ca6efecce62c18adf787b` / tree `0601fb30c7c08354b342bfe40b011f2606db75d5`. It resolved exactly one merge base, emitted schema 1.6 `assurance_kind=range_candidate`, context digest `sha256:83a01c2cbb960a03f06f26b4567be6e5b60b1e874b36b27f68d244846a1952d0`, and reported `0 findings (0 blocking)`. Its authoritative result remains `UNKNOWN` / exit `1` with `snapshot_differential_execution_unavailable`, as required because the local producer cannot promote itself to protected `pr_range` authority. The original project-scoped module directory was restored after the current candidate module completed the review.

The canonical signer added signature `z/Ojifmu2yyGDXzsnfYr6MC6+MqO+mMYdqJa17aOMvXqzP+AZUAx47ff/YSbXItJQdW2xZuuc7BiXEH7PVmeCQ==` to unchanged checksum `sha256:1e35b1e0a06a53645815c3f0b1f663b8b1923ae39bf901e72dba1e4b1536ec88`, producing bot commit `124022a91ac26ef453d60dc87ab51e057e48cfac` / tree `b244788bdcf8de163bc018e0972005b160ec656b`. GitHub again marked the bot-authored head workflows `action_required`; the following evidence-only human commit changes no signed payload byte and exists solely to trigger protected CI against this exact signed identity.

Protected run `32533566806` against signed payload `124022a91ac26ef453d60dc87ab51e057e48cfac` passed signature verification plus immutable core/tag/tree, exact-version alias rejection, and schema 1.6 on all three Python versions. All three capsule jobs then progressed beyond the former loopback denial and failed consistently while the capability-dropped Bubblewrap traversed the root Python process's staging path below runner-owned `$RUNNER_TEMP`: `bwrap: Can't find source path .../rootfs: Permission denied`. Bubblewrap deliberately performs filesystem access without retained DAC-override authority, so the workflow now creates a unique root-owned staging directory with `tempfile.mkdtemp(..., dir="/tmp")` and no longer preserves `RUNNER_TEMP` into the elevated process. The step-local regression was authored first and failed `1 failed` because the workflow still used runner temp, then passed `1 passed`; the complete toolchain/workflow surface passed `71 passed`, followed by format, type/lint (`0` diagnostics; Pylint `10.00/10`), YAML, strict OpenSpec, and `git diff --check`. This changes no signed module payload byte or signature. Task 4.3 remains incomplete pending protected proof from the corrected staging boundary.

Protected run `32533849894` passed the same signature/core/schema gates and proved that root-owned `/tmp` staging clears the traversal failure and completes offline installation. Final verification then reported the exact signed entry count and regular-byte total on every ABI but a different manifest digest (for cp312: expected `20583` entries / `889139510` bytes / `sha256:2335bf98d393cf99b544df7abc35c7651acff55d0b83e1f8b65df2a4db3cb0ba`, observed the same count/bytes with `sha256:b86a739bbf38b1b8c1344cee5711d8804f1364c86c3d1dd726a578d4629261cb`). This isolates the drift to canonical metadata such as modes produced when pip runs as UID 0 rather than payload membership or byte volume. The next boundary therefore keeps only Bubblewrap namespace setup elevated and explicitly runs both offline pip and final capsule boot as the original positive non-root sudo caller UID/GID, after chowning only the empty analyzer target; `--cap-drop ALL` remains mandatory. The explicit API/workflow regressions were authored first and failed `2 failed`, then passed `2 passed`, and a materialization propagation assertion binds the identity through the public call. A further bool/non-positive/non-root validation regression exposed boolean UID acceptance (`1 failed`, `2 passed`) before the API was made fail-closed; all three invalid cases then passed. The complete focused surface passed `75 passed`; format, type/lint (`0` diagnostics; Pylint `10.00/10`), YAML, bundle imports, strict OpenSpec, checksum/version verification, and `28 passed` contracts passed; both smart and complete suites passed `1379 passed` with only the two third-party `lark` deprecations. Fresh isolated immutable-core `0.55.1` matrices again passed `3 passed` plus exact alias rejection on CPython `3.11.15`, `3.12.13`, and `3.13.14`. The canonical signer utility removed the stale signature and set the unsigned checksum to `sha256:86ce07991c14987fa85750c506188075e1c3d78ff591dc7a91f8605a2117e3dd`. Task 4.3 remains incomplete pending freshly signed protected proof.

The refreshed explicit range/full review bound base commit `c3eda08c732267dc3614130f5f36bcd473182d0b` / tree `0b1d0cc80b671c561ddadc3d50f395b1959d0dd7` to implementation commit `f3cac18ddb8e05064fedd99d8694c10b9fbfd45e` / tree `efbb47330f2f1046eb5402d01394d918cb388d36`, resolved exactly one merge base, and emitted schema 1.6 `range_candidate` with context digest `sha256:55066dba1b56878f097ed38ff08098bad6945bb07ce6c909dcd76ca26b99f45d`. It reported `0 findings (0 blocking)` and the required local-only `UNKNOWN` / exit `1` reason `snapshot_differential_execution_unavailable`. The original project-scoped module directory was restored after reviewing the current candidate.

Protected run `32535079040` against unsigned dev-target commit `c90c897a8e0d4718366ce3ab498cd9c9d6a1cb16` passed the dev-branch signature policy, immutable core/tag/tree, exact-version alias rejection, and schema 1.6 on CPython 3.11–3.13. All three offline installs then failed consistently after the child switched to the sudo caller UID/GID: `PermissionError: [Errno 13] Permission denied: '/opt/specfact/analyzers/annotated_types-0.8.0.dist-info'`. A root-created Bubblewrap user namespace does not map that namespace UID/GID back to the same host filesystem identity, so chowning the analyzer target cannot grant the intended write authority. The attempted explicit-child-identity design is rejected by this protected evidence.

The next diagnostic remains fail-closed: the workflow uses the already required `--cap-drop ALL` root child, records only canonical manifest/subroot digests and analyzer mode counts plus three deterministic mode-normalization candidate digests, and then invokes the original strict verifier. Its strengthened workflow selector was authored first and failed `1 failed` because the diagnostic and removal of the invalid child-identity arguments were absent; after the harness-only edit it passed `1 passed`, workflow YAML parsing passed, and `git diff --check` passed. This diagnostic cannot convert a mismatch to PASS and changes no package payload byte. Task 4.3 remains incomplete pending the protected diagnostic output and a tests-first production correction grounded in that output.

Protected diagnostic run `32536174297` against signed checksum `sha256:86ce07991c14987fa85750c506188075e1c3d78ff591dc7a91f8605a2117e3dd` disproved the mode-drift hypothesis on every ABI. Each runtime produced the exact signed `analyzers`, `bin`, `bootstrap`, `lib`, `python`, and `wheelhouse` subroot digest; the analyzer mode inventory was identically `2528` directories at `0755`, `14412` regular files at `0644`, and `173` regular files at `0755`; and the `pip-standard`, `owner-writable`, and `umask-022` candidates were identical to the actual aggregate. Only the redundant aggregate digest differed despite exact membership/bytes and exact constituent subroots. The strengthened aggregate-order diagnostic selector was authored first and failed `1 failed` because no cross-subroot ordering search existed, then passed `1 passed` after adding a bounded six-subroot permutation check that still invokes the original strict verifier. Task 4.3 remains incomplete; no frozen identity has been edited and no verifier condition has been removed.

Protected diagnostic run `32536547169` found no matching concatenation among all `720` permutations of the six exact signed subroot entry blocks on CPython 3.12; the aggregate mismatch is therefore not top-level subroot ordering. The compressed-manifest artifact regression was authored first and failed `1 failed` on the absent artifact path/upload contract, then passed as part of the complete workflow regression file (`10 passed`) after the fail-closed verifier wrote only canonical path/type/mode/size/content-digest metadata for one-day diagnostic upload. Workflow YAML parsing and `git diff --check` passed. No file contents, credentials, or relaxed verifier result are exported.

### Pull-request review remediation — 2026-08-22

The authoritative GitHub review-thread inventory for PR #418 was refreshed from GraphQL rather than inferred from flat comments. Two already-corrected integrity threads were verified by the exact schema-1.6 missing-assurance and installed-payload mutation selectors (`4 passed` including three payload mutations), answered with evidence, and resolved. The next two tests-first batches covered OCI whiteout parent traversal, active conditional-analyzer UNKNOWN aggregation, complete pytest selection/execution controls and shaping hooks, shadow range enforcement, Ruff projection validity, Basedpyright snapshot-root includes, required context trees, blocking-input partitions, case-sensitive Ruff controls, score-derived ledger rewards, canonical worktree scope, context-declared source locks, transitive Ruff policy paths, shared INI/Pylint applicability, duplicate occurrence continuity, captured index evidence, temporary-root cleanup, repository identity propagation, and reversible Git path decoding.

The first exact regression command collected `18` parameterized cases and failed all `18` before production edits, then passed all `18`. The second exact command failed `8` of `8` before production edits, then passed all `8`. Two final decoding/origin regressions passed `2 passed`. The complete affected surface passed `499 passed`; both the complete and smart suites passed `1406 passed` with only the two existing third-party `lark` deprecations; and the contract gate passed `28 passed`. Type-check reported `0 errors, 0 warnings, 0 notes`; format, Ruff, and Pylint passed with Pylint `10.00/10`; manifest and CLI-contract validation passed; strict OpenSpec validation passed; and `git diff --check` passed. The two still-open architectural review findings—immutable range/index analyzer execution and analyzer availability for legacy local scopes—remain unresolved and are not claimed as fixed. Task 4.3 also remains blocked by the separately documented aggregate-manifest contract defect; no frozen lock/checkpoint identity was edited and no aggregate verifier condition was relaxed.

A second authoritative review-body audit found six still-valid behavioral gaps beyond the inline inventory. The exact selected command failed `6 failed` before production edits, proving missing CrossHair launch evidence, indistinguishable core-API failure, payload permission drift, tautological eligible/invoked manifests, undeclared Radon control-root mutation, and URL userinfo retention. After correction, the expanded selected surface passed `14 passed`. The same batch binds the full frozen pytest 9.0.3/pytest-cov option classes and all `52` hook dispositions, makes duplicate pairing independent of analyzer emission order, removes scope roots on exceptional resolution paths, verifies analyzer locks per ABI, pins every action used by the exact-core job to a resolved commit SHA, and replaces two misleading tests with semantic invariants. The payload-manifest projection now includes stable permission mode consistently at core handoff, re-verification, copy, and capsule composition; the legacy package checksum projection remains unchanged for its separately versioned compatibility path.

Final review-batch gates passed on 2026-08-22: complete and smart suites each `1421 passed` with only the same two third-party `lark` deprecations; contracts `28 passed`; type-check `0 errors, 0 warnings, 0 notes`; format, Ruff, and Pylint with Pylint `10.00/10`; seven manifests plus registry validation; three CLI-contract files; bundle-import validation; strict OpenSpec; and `git diff --check`. The canonical signing utility removed the stale bot signature and refreshed the unsigned dev-PR checksum to `sha256:1287b21162af585fa114c7409bb93b39be4f2c127147eb10e5fa6273f01ef6ce`; checksum/version verification against `origin/dev` accepted all seven manifests with the repository-approved local missing-public-key allowance. A new canonical bot signature is required after push.

The signed-commit hook then exposed inherited repository-local Git variables: an isolated Git fixture could target the caller worktree when `GIT_DIR`/`GIT_WORK_TREE` leaked through the hook environment. The observed shared-config mutation was repaired by removing only the exact fixture values and restoring `core.bare=false`; signed commits were not bypassed. Production Git subprocesses and the fixture helper now strip all repository-local Git environment variables while preserving explicit captured-index overrides. The focused scope suite passed `105 passed` including the poisoned-environment regression, the refreshed complete suite passed `1422 passed`, contracts remained `28 passed`, type/lint and strict OpenSpec remained green, and shared config stayed non-bare without the fixture identity. The canonical signing utility then refreshed the final unsigned checksum to `sha256:d44812b627a108ebadab53fb46c946d8bab313226d0f24f0f7b603c4fa0e52dd`; all seven manifests passed checksum/version verification against `origin/dev` with the approved local missing-public-key allowance.

A subsequent authoritative review refresh found one new valid schema-1.6 contradiction: an untrusted serialized report could claim `assurance_status=PASS` while carrying analyzer evidence with `evidence_outcome=UNKNOWN`; deserialization marked `has_unknown_required_evidence` but retained PASS, exit `0`, and ledger reward eligibility. The exact regression `test_schema_1_6_json_pass_with_unknown_analyzer_is_demoted` was authored first and failed `1 failed` because the report remained PASS. The authoritative derivation now demotes PASS or NOT_APPLICABLE to UNKNOWN whenever required analyzer evidence is UNKNOWN, after which the existing projection produces verdict FAIL and exit `1` outside shadow mode. The focused findings/ledger surface passed `85 passed`; type-check and lint passed with Pylint `10.00/10`; the complete suite passed `1423 passed` with only the same two third-party `lark` deprecations; contracts passed `28 passed`; strict OpenSpec validation and `git diff --check` passed. The canonical signing utility removed the stale bot signature and refreshed the unsigned dev-PR checksum to `sha256:f955fe1293b31b3bc5b79bc8ae80ff5c34328774c348b4fd422b8a81e2e651d1`; checksum/version verification against `origin/dev` accepted all seven manifests with the repository-approved local missing-public-key allowance. A fresh canonical bot signature is required after push.

The next authoritative review refresh found two additional valid gaps. A target-tip Basedpyright `extends`/`baselineFile` graph was resolved but its reference paths were not included in the governed range closure, so a reference-only candidate change returned NOT_APPLICABLE. Separately, a serialized schema-1.6 PASS report could omit all or part of the frozen analyzer profile while retaining PASS and ledger reward eligibility. The exact three-case checkpoint failed `3 failed` before production edits: one reference-only range and empty/subset analyzer evidence. The range resolver now unions the complete successfully resolved Basedpyright reference graph with the Ruff closure before governed selection, policy bundling, and candidate-policy evidence. The frozen eight required plus two conditional `pr-range-v1` member tuples now have one shared definition used by report validation and runner aggregation; PASS requires each member exactly once, while missing, extra, or duplicate membership demotes to UNKNOWN before legacy verdict/exit projection. The exact checkpoint then passed `3 passed`; the complete affected findings/scope/runner/ledger surface passed `338 passed`; type-check reported `0 errors, 0 warnings, 0 notes`; format, Ruff, and Pylint passed with Pylint `10.00/10`; the complete suite passed `1426 passed` with only the same two third-party `lark` deprecations; contracts passed `28 passed`; strict OpenSpec validation and `git diff --check` passed. The signed-commit review then identified one new Radon complexity blocker in the authoritative derivation; extracting the closed-profile completeness predicate removed it without changing behavior, and the exact three schema regressions plus type/lint gates remained green. The canonical signing utility removed the stale bot signature and refreshed the unsigned dev-PR checksum to `sha256:cb8ae16b95007be7a09d766dde829174a9494886f846cd37c3c4678f7aa58a06`; checksum/version verification accepted all seven manifests. The two capsule-execution P1 review threads remain valid and unresolved; this batch does not claim that missing execution layer is fixed.

The following automated review batch exposed two further fail-closed gaps. A complete ten-member schema-1.6 evidence array could omit `evidence_outcome` or supply an unrecognized value and still retain aggregate PASS; each immutable index request also left its copied `index` and `sharedindex.*` root under the system temporary directory. The exact three-case regression command failed `3 failed` before production edits: both untrusted-outcome variants remained PASS and the capture root remained present. Report validation now accepts a passing profile only when every exact member carries PASS or NOT_APPLICABLE, marks missing/unrecognized outcomes as unknown evidence, and demotes contradictory PASS to UNKNOWN. Index capture now removes its owned root immediately after the captured tree, metadata, and snapshots have been derived, and also removes the root on capture failure. The exact command then passed `3 passed`; the affected findings/scope/commands/ledger surface passed `263 passed`; type-check reported `0 errors, 0 warnings, 0 notes`; format, Ruff, and Pylint passed with Pylint `10.00/10`; the complete suite passed `1429 passed` with only the same two third-party `lark` deprecations; contracts passed `28 passed`; strict OpenSpec validation and `git diff --check` passed. The full staged pre-commit pipeline against immutable core v0.55.1 passed command/docs/accountability, requirements, bundle, lint, contract, and SpecFact review gates; the review reported `155` retained advisory findings, `0` blocking findings, and `0` introduced differential findings, matching the already documented frozen-owner/contract-coverage/local-runtime exceptions. The approved non-main signing hook removed the stale signature, incremented the module to `0.49.3`, and refreshed the unsigned dev-PR checksum to `sha256:a8dec2e90e2bdd366549077452bc7f82d899e633be39419e9e92686e5d924c54`; all seven manifests passed checksum/version verification. The two capsule-execution P1 threads and the aggregate-manifest protected-runtime blocker remain unresolved and are not weakened by this review remediation.

The next review batch identified two selector-completeness defects. A governed test-shaped path outside configured `testpaths` was incorrectly frozen as `test_support`, and a newly added extant `test_candidate` with empty base and head selector inventories bypassed reconciliation. The two exact regressions were authored first and failed `2 failed`: the role was `test_support` instead of `test_candidate_outside_root`, and the empty new candidate returned PASS instead of UNKNOWN. The classifier now preserves the contract's outside-root candidate role whenever the frozen pytest filename matcher recognizes the path, while in-root nonmatching files remain support. Candidate reconciliation now requires every extant head candidate to contribute at least one selector regardless of whether a baseline selector existed. The unchanged exact command then passed `2 passed`, and the complete runner unit surface passed `147 passed`. Final batch gates against immutable core v0.55.1 passed: complete and smart suites each `1431 passed` with only the same two third-party `lark` deprecations; contracts `28 passed`; type-check `0 errors, 0 warnings, 0 notes`; format, Ruff, and Pylint with Pylint `10.00/10`; seven manifests plus registry validation; three CLI-contract files; bundle-import validation; strict OpenSpec; and `git diff --check`. The architectural capsule-execution threads remain open and are not claimed as fixed by this bounded remediation.

### Capsule execution and differential review remediation — 2026-08-22

The two unresolved P1 threads were revalidated against the signed PR head and found valid: immutable `index`/`range` scopes returned before any analyzer execution, while fresh marketplace installs no longer carried host analyzers for legacy scopes. Four exact architecture regressions were authored first and failed `4 failed` because the command gateway, per-member capsule executor, same-descriptor Bubblewrap launch, and immutable base/head execution APIs did not exist. Production now routes immutable scopes through base and head capsule runs, launches every active profile member in a fresh `--unshare-all`/`--cap-drop ALL` sandbox, validates and executes the Bubblewrap binary from the same open descriptor, and routes legacy scopes through the capsule gateway. A tightly bounded macOS source-checkout compatibility branch remains only for non-immutable developer scopes; marketplace/user installs and every immutable scope fail closed as schema 1.6 UNKNOWN when the Linux capsule cannot run. The exact architecture selectors then passed `4 passed` and the affected command/runner/sandbox/toolchain surface passed `307 passed` at that checkpoint.

Protected pre-release execution does not borrow provenance from an older installed release. Two candidate-source verification selectors first failed `2 failed` because no source-payload verifier existed, then passed `2 passed` after the verifier bound full path/type/mode/content manifest bytes to an explicitly non-official `verified-candidate-module-payload-v1` identity. The protected PR selector reconstructs module bytes from the verified Git commit/tree rather than from a live directory that may contain generated files, binds repository/workflow/run/job/module-package/payload identities, and refuses installed-release fallback whenever GitHub Actions candidate context is invalid. Exact regressions also prove that immutable scopes never enter the developer host-compatibility branch.

The next authoritative GraphQL refresh found two additional valid comments. The protected diagnostic artifact used undefined `matrix.python`, and the first immutable implementation combined only per-analyzer outcomes rather than invoking the accepted finding-level differential classifier. The exact three-case checkpoint failed `3 failed`: two classifier integration APIs were absent and the workflow lacked `matrix.python-version`. The corrected workflow emits ABI-unique artifact names. Each analyzer now passes canonical base/head findings, immutable source bytes, exact rename facts, and added/deleted paths through `finding-multiset-v1`; schema 1.6 evidence includes the differential digest and fixed/introduced/unchanged/unknown counts, introduced or retained blockers remain FAIL, fixed baseline findings are retained as non-blocking lifecycle evidence, and mapping or analyzer/result inconsistencies are UNKNOWN. The unchanged exact command then passed `3 passed`; the complete affected C14/workflow surface passed `324 passed`.

Fresh post-remediation gates passed against immutable core v0.55.1: format; type-check with `0 errors, 0 warnings, 0 notes`; Ruff and Pylint with Pylint `10.00/10`; seven manifests plus registry validation; three CLI-contract files; bundle-import validation; strict OpenSpec; `git diff --check`; and `28 passed` contract tests. Both smart and complete test gates passed all `1445` tests with only the two existing third-party `lark` deprecations. Fresh isolated Python `3.11.15`, `3.12.13`, and `3.13.14` environments each force-reinstalled core `0.55.1` from detached commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337` and passed the same three schema/handoff/candidate-identity selectors (`3 passed` per interpreter). Every environment reconfirmed that `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, and ordinary `==0.55.1` admits that untested alias.

These local results do not claim protected Linux or publication authority. Task 4.3 remains blocked by the separately isolated frozen aggregate-manifest defect: all six signed subroots, exact membership, and exact bytes match, but the redundant aggregate digest does not. No lock/checkpoint/verifier identity has been edited or relaxed. The PR review threads remain open until this implementation is signed, pushed, and reverified on the authoritative head.

The first signed-commit attempt was correctly stopped by the changed-line review gate. It identified capsule-request complexity plus two host-review type-inference errors, while the targeted-test error exposed that the new protected-candidate Git fixture inherited hook-local `GIT_DIR`/`GIT_WORK_TREE` and again flipped the shared repository to bare while overwriting its local signer identity with the fixture identity. The repository state was restored to `core.bare=false` and the real history-backed signer identity. A poisoned-environment regression then failed `1 failed` before both fixture and protected-candidate Git subprocesses adopted the same closed local-environment override set as scope resolution, and passed under the exact signed-hook environment afterward without changing shared state. Helper extraction removed the complexity blocker, explicit evidence/ambiguity types removed both inference errors, and the complete command/runner surface passed `225 passed` with type-check and Ruff clean. The repeated pre-commit review then reported `236` retained advisory findings, `0` errors, and no changed-line blockers; the contract hook passed `28 passed`.

The canonical non-main signer then advanced `specfact-code-review` from `0.49.4` to `0.49.5`, removed the stale bot signature, and set the final unsigned filesystem checksum to `sha256:6c0a3e8c4777278047fddaa490b98db3abf34dff57abefed58adc5fcea12b2ce`. The formal filesystem/version verifier accepted all seven manifests with the repository-approved local missing-public-key allowance. A new canonical bot signature is required after push; no registry archive, sidecar, or signed publication output was hand-edited.

### Signed-head policy/runtime/pytest review remediation — 2026-08-22

After the four preceding architecture/differential threads were answered and resolved, the authoritative GraphQL refresh on signed head `0288a8b73c9455766b9964d6ef8263ada1af8c7f` returned three new P1 findings. All three reproduced against the actual capsule path. The exact selectors `test_capsule_member_passes_explicit_target_policy_to_adapter`, `test_immutable_review_reuses_authenticated_project_runtime_for_both_snapshots`, and `test_immutable_range_reconciles_removed_pytest_selector_before_execution` failed `3 failed` before production edits: adapter argv was absent, both snapshots received no project-runtime root, and analyzer execution began without selector reconciliation.

The sealed member request now carries controller-generated explicit adapter argv; Ruff, Basedpyright, and Pylint consume only those explicit projections, and configured Semgrep passes receive the mounted target-tip bundle rather than snapshot discovery. The immutable runner validates and materializes a supplied `project-runtime-layer-v1`, re-verifies manifest/config/layer and extracted root/distribution identities, binds its identity into capsule composition, and exposes the identical read-only root only to the closed import-capable member set for both snapshots. Before analyzer launch, base/head complete pytest inventories are derived from the shared target-tip policy, changed candidates must remain collectable, and removed selectors fail closed. Module-level `__test__ = False` therefore produces `uncollected_changed_test` UNKNOWN even when a sibling test would otherwise pass.

The unchanged three-selector command then passed `3 passed`. Added integration proofs also passed: generated target-tip policy paths map only to `/opt/specfact/config/*`, and an identity-keyed project-runtime cache is reused only after full root-manifest and exact distribution-set re-verification. The expanded runtime/adapter/workflow surface passed `654 passed`; focused type-check reported `0 errors, 0 warnings, 0 notes`; Ruff passed; and no protected authority, archive, core edit, or frozen aggregate identity is claimed by this remediation. Final full gates and canonical re-signing remain pending.

Fresh final gates then passed: smart and complete suites each `1450 passed` with only the same two third-party `lark` deprecations; contracts `28 passed`; repository-wide format, type-check, Ruff, and Pylint with `0 errors, 0 warnings, 0 notes` and Pylint `10.00/10`; seven manifests plus registry validation; three CLI-contract files; bundle-import validation; strict C14 OpenSpec; and `git diff --check`. Isolated Python `3.11.15`, `3.12.13`, and `3.13.14` environments each loaded immutable core `0.55.1` and the current candidate module, passed the exact schema-1.6/core-handoff/candidate-identity selectors (`3 passed` per interpreter), and reconfirmed that `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, while ordinary `==0.55.1` admits the untested local alias. The canonical non-main checksum/version hook and bot signature remain required after the human commit.

The first staged SpecFact review exposed four clean-code errors and two changed-line blockers in the newly connected orchestration. Helper extraction and an immutable `CapsuleMemberExecutionRequest` removed the complexity and parameter-count regressions without changing behavior; the complete runner/toolchain unit surface remained `231 passed`. The repeated full pre-commit pipeline passed with `201` retained advisory findings, `0` errors, and no changed-line blockers; contracts remained `28 passed`, type/lint remained clean, and the approved non-main signer advanced the module to `0.49.6`, removed the stale signature, and set unsigned checksum `sha256:00ac4f5abad1978e5468465292c179146ec1ab04375d87046843d9bba368eee8`. A fresh canonical bot signature is required after push.

### Complete pytest, sealed policy, runtime-lock, and Git-path review remediation — 2026-08-22

Revalidation before resolving the targeted-pytest thread found that static base/head inventory reconciliation did not reach the actual capsule member: execution still called the legacy source-to-test mapper. The member regression `test_capsule_targeted_pytest_executes_supplied_complete_inventory` failed before the member accepted controller-owned inventory mode. A second controller-level regression, `test_immutable_review_binds_each_complete_pytest_inventory_to_its_snapshot`, then failed with a missing `targeted-pytest-coverage` binding, and `test_run_complete_pytest_inventory_preserves_exact_node_ids` failed because exact node-ID execution did not exist. Production now binds distinct reconciled base/head inventories, marks that mode explicitly in the sealed request so an empty inventory cannot fall back to legacy mapping, validates repository-relative selector paths, executes exact node IDs, and measures the immutable candidate snapshot rather than the analyzer package. The three exact selectors passed.

The next authoritative GraphQL refresh returned three further valid comments. Exact regressions first failed `4 failed`: schema-valid `project-runtime-layer-v1` source-lock records were rejected as unsafe context, local Git discovery lost quoted/non-ASCII and newline-containing Python paths, and pytest/coverage execution omitted sealed target-tip projection argv. The context validator now accepts the canonical sorted record shape (`path`, `blob_sha`, `content_sha256`) consumed by the materializer and projects only its validated paths into governed selection. Local worktree/full discovery uses NUL-delimited Git output with surrogate-safe decoding. Each immutable side now receives generated read-only pytest and Coverage configs through explicit `-c`, `--rootdir`, and `--cov-config`, with target test roots rebased to `/opt/specfact/snapshot`, controller-owned writable paths redirected below the private temporary root, custom Coverage exclusions/plugins rejected, and exact selectors appended after a controller separator. The unchanged exact command then passed all `4` selectors; the combined seven review regressions passed `7 passed`.

The complete code-review subsystem passed `617 passed`. The full repository test gate and smart-test gate each passed `1456 passed` with only the two existing third-party `lark` deprecations; contracts passed `28 passed`. Repository-wide format, Ruff, Basedpyright, and Pylint passed with `0 errors, 0 warnings, 0 notes` and Pylint `10.00/10`. Manifest/registry validation, three CLI-contract files, bundle imports, strict OpenSpec, and `git diff --check` also passed.

The first staged SpecFact review correctly stopped on two new Radon changed-line blockers: complexity `17` in the sealed capsule-request loader and `18` in project-runtime context validation. Extracting path/adapter validation and source-lock-record validation removed both without changing the contract; the complete runner/scope surface then passed `273 passed`. The repeated canonical pre-commit pipeline reported `236` retained warnings/information findings, `0` errors, and no changed-line blockers; contracts remained `28 passed`. The approved non-main signer advanced `specfact-code-review` from `0.49.6` to `0.49.7`, removed the stale bot signature, and set unsigned checksum `sha256:af0a5fbe0e94d426043898e8d440c315fa7a2b60ec8d544d1fd66ef63b0f2f24`. Exact-core CPython 3.11–3.13 smoke and a fresh canonical bot signature remain required after the human commit is pushed.

Fresh isolated Python `3.11.15`, `3.12.13`, and `3.13.14` environments each installed core `0.55.1` from detached commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337`, linked the current candidate module, and passed the exact schema-1.6/core-handoff/candidate-identity selectors (`3 passed` per interpreter). Every environment reconfirmed that `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, and ordinary `==0.55.1` admits the untested local alias. A fresh canonical bot signature remains required after push.

### Signed-head project-runtime import and complete-candidate remediation — 2026-08-22

The next signed-head Codex review returned two new P1 findings. Both reproduced before production edits. `test_post_base_bootstrap_and_composite_identity_bind_copied_payload` failed because the sealed `-I -S` bootstrap inserted only the analyzer and built-in roots, leaving the authenticated `/opt/specfact/project-runtime/site-packages` mount outside `sys.path`. `test_unchanged_test_candidate_without_selector_is_unknown` failed because complete-suite planning checked only changed candidates, allowing an unchanged empty `tests/test_placeholder.py` to pass during a production-only range. The exact red command reported `2 failed`, `0 passed`.

The sealed bootstrap now adds the canonical project-runtime site-packages path after its two capsule-owned roots. That path is populated only when the sandbox controller mounts a fully materialized and reverified project runtime for one of the closed import-capable members; non-importing members still receive no project-runtime mount, and snapshot/project imports remain behind capsule-reserved imports. Complete pytest planning now enumerates every extant policy-matching candidate in each immutable snapshot and returns `uncollected_test_candidate` UNKNOWN when an unchanged candidate contributes no selector, while retaining the more specific `uncollected_changed_test` reason for changed candidates.

The unchanged two-selector command then passed, the adjacent five-selector diagnostic set passed, and the complete Code Review subsystem passed `829 passed`. Fresh repository gates then passed: strict OpenSpec; seven manifests plus `registry/index.json`; three CLI-contract scenario files; bundle imports; formatting and `git diff --check`; type-check with `0 errors, 0 warnings, 0 notes`; Ruff; Pylint `10.00/10`; contracts `28 passed`; and both smart and complete suites at `1457 passed`. The complete suites retained only the two existing third-party `lark` deprecation warnings.

Fresh isolated CPython `3.11.15`, `3.12.13`, and `3.13.14` environments then installed core `0.55.1` from detached commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337`, linked the current candidate module, and passed the exact schema-1.6/core-handoff/candidate-identity selectors (`3 passed` per interpreter). Each environment independently reconfirmed that strict `===0.55.1` accepts `0.55.1`, rejects `0.55.1+vendor`, and ordinary `==0.55.1` admits that untested local alias. No earlier gate evidence is reused for this review batch.

The canonical staged pre-commit pipeline then passed all signature/version, format, bundle, type/lint, requirements-evidence, command/docs, changed-line review, and contract stages. The fresh changed-line report was `PASS_WITH_ADVISORY` with `203` retained findings, `0` errors, and no changed-line blocker; contracts again passed `28 passed`. The repository-approved non-main signer advanced `specfact-code-review` from `0.49.7` to `0.49.8`, removed the stale signature, and set the unsigned filesystem checksum to `sha256:ff8cdf85f23cfcbaf9e19a5f55a95db0f991947be08c6c6cd573847aa3b176d9`. A human commit, fresh exact-range/full report, and canonical bot signature remain required.

### Protected Linux legacy-source compatibility correction — 2026-08-22

Protected run `32550416328` passed exact core tag/commit/tree verification, strict local-version rejection, the schema 1.6 exact-core selector, and module-signature verification. Its complete Python 3.11 quality suite then exposed five legacy explicit-file CLI tests returning UNKNOWN because the Linux source checkout had an empty verified capsule cache. The existing compatibility branch was intentionally limited to unsupported controller platforms, so the same tests had passed locally on macOS and had not exercised this Linux boundary.

The exact regression `test_source_checkout_legacy_scope_explicitly_opts_into_linux_cache_miss_compatibility` was authored first and failed `1 failed`. Production now permits host analyzers only when all of these facts hold simultaneously: the scope is the existing non-immutable legacy gateway, the module is running from this development source checkout, the failure is exactly `oci_acquisition_failed:verified cache entry is missing`, and `SPECFACT_CODE_REVIEW_DEV_HOST_COMPAT=1` is explicitly set. The five legacy CLI tests set that test-only opt-in. A companion regression proves the same Linux cache miss remains schema 1.6 UNKNOWN without the opt-in; the existing marketplace and immutable-scope regressions continue to prove they never use host analyzers. The exact nine-selector legacy/marketplace/immutable set passed, followed by the complete Code Review subsystem at `831 passed`.

The protected capsule job separately confirmed the frozen aggregate-manifest blocker on Python 3.11, 3.12, and 3.13. For CPython 3.12, all six signed subroots matched exactly (`analyzers`, `bin`, `bootstrap`, `lib`, `python`, `wheelhouse`), with `20583` entries and `889139510` regular-file bytes, but the actual aggregate digest `sha256:b86a739bbf38b1b8c1344cee5711d8804f1364c86c3d1dd726a578d4629261cb` differed from frozen expected `sha256:2335bf98d393cf99b544df7abc35c7651acff55d0b83e1f8b65df2a4db3cb0ba`. No signed lock/checkpoint/verifier identity is changed or relaxed; amending that redundant aggregate requires explicit user approval.

Fresh local gates after the compatibility correction passed: strict OpenSpec; seven manifests plus registry; three CLI-contract scenario files; bundle imports; formatting and `git diff --check`; type-check with `0 errors, 0 warnings, 0 notes`; Ruff; Pylint `10.00/10`; contracts `28 passed`; and both smart and complete suites at `1459 passed` with only the same two third-party `lark` deprecations. The exact immutable core v0.55.1 smoke was rerun against the updated candidate bytes on CPython `3.11.15`, `3.12.13`, and `3.13.14`; all three schema/handoff/candidate-identity selectors passed per interpreter, and strict `===0.55.1` versus local-alias rejection was reconfirmed.

The canonical staged pipeline then passed with a fresh changed-line report of `PASS_WITH_ADVISORY`, `92` retained warnings/information findings, `0` errors, and no changed-line blocker; contracts again passed `28 passed`. The approved non-main signer advanced the module from `0.49.8` to `0.49.9`, removed the stale signature, and set unsigned filesystem checksum `sha256:ea72b1305643a02f8ee45bb6a1bb0b22abeb6312425fa3c8ea4b78882136a299`. A signed human commit, fresh exact-range/full reports, protected Linux rerun, and canonical bot signature remain required.

### Review batch — sealed Semgrep activation, inherited unittest selectors, and empty snapshots

Three new PR review findings were treated as fresh tests-first input on 2026-08-22. The exact selectors `test_sealed_target_bugs_policy_activates_semgrep_bugs_without_bug_hunt`, `test_complete_suite_collects_inherited_unittest_selector`, and `test_empty_capsule_snapshot_marks_every_member_not_applicable` were authored before production edits and failed together (`3 failed`). They proved that sealed target policy did not activate `semgrep-bugs` unless the legacy `--bug-hunt` option was also set, same-module inherited `unittest.TestCase` methods were absent from the complete selector inventory, and an empty Python snapshot attempted to construct analyzer requests instead of classifying every closed-profile member as NOT_APPLICABLE.

Production now activates `semgrep-bugs` from the sealed member-policy binding while retaining the legacy option, binds that member only when the authorized `.semgrep/bugs.yaml` exists, derives inherited same-module test methods conservatively without executing candidate code, and returns `empty_snapshot_input` NOT_APPLICABLE evidence for every profile member before analyzer launch when no Python input exists. The three exact selectors passed, followed by the complete Code Review unit subsystem (`834 passed`).

Fresh post-review gates passed: format and `git diff --check`; type-check with `0 errors, 0 warnings, 0 notes`; Ruff and Pylint `10.00/10`; seven manifests plus registry; three CLI-contract scenario files; bundle imports; strict C14 OpenSpec; contracts `28 passed`; and smart plus complete suites at `1462 passed` each with only the two existing third-party `lark` deprecations. Isolated CPython `3.11.15`, `3.12.13`, and `3.13.14` environments each linked the current candidate, loaded immutable core `0.55.1` from commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276` / tree `47984be5434d7ae65ed6908bf525a32053290337`, and passed the three schema/handoff/candidate-identity selectors (`3 passed` per interpreter); strict `===0.55.1` accepted `0.55.1`, rejected `0.55.1+vendor`, and ordinary `==0.55.1` admitted the untested alias. Canonical unsigned PR metadata advanced the changed module to `0.49.10` with filesystem checksum `sha256:1500d98dd54701ea72ca4d1d4cad0be5c57ff2554c2dcb567a07c63e7ef7804b`; all seven filesystem checksum/version checks passed. A fresh canonical bot signature remains required after the human commit is pushed.

The canonical staged pipeline passed when bound to the exact detached core checkout: signature/version, format, YAML, bundle, type/lint, documentation accountability, Requirements evidence, command/docs, changed-line review, and contracts were all green. The fresh changed-line report was `PASS_WITH_ADVISORY` with `91` retained findings, `0` errors, and no changed-line blocker; contracts again passed `28 passed`.
