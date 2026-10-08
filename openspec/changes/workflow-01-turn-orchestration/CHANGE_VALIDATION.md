## Planning validation

Date: 2026-09-20 Europe/Berlin. Scope: standalone workflow proposal and issue metadata; runtime implementation is unstarted and all implementation tasks remain unchecked.

This proposal was separated from the combined lean-evidence planning PR at the owner's request. Its branch stacks on the cleaned lean-planning branch, so the PR diff contains harness-owned planning only. R09 issues #740/#481 and their plans retain their separate ownership; no changes to those issues or files are part of this proposal.

The prior combined plan passed strict OpenSpec and scoped documentation validation. Strict OpenSpec 1.13.0 validation, scoped Markdown and whitespace checks passed on the separated branch. The signed #481/v3 compatibility prerequisite is explicit in proposal/design/spec/tasks; runtime acceptance awaits implementation and actual signed releases.

Native metadata is User Story, djm81, enhancement/openspec/change-proposal, SpecFact CLI project 1 / Todo, core #742 parent #372 or modules #483 parent #163. Native direction remains modules #481 -> modules #483 -> core #742 runtime adoption; independent projection is not blocked on signed runtime delivery. Refresh/read back this metadata before implementation.

Normal hooks on the same combined planning artifacts rejected Requirements with unsupported-sidecar-schema. The existing owner-authorized local planning-only Block2 exception is retained for separation commits; it does not change runtime, protected CI or remote policy and is not a passing Requirements/review claim. Other applicable hooks and scoped documentation checks must pass. Workflow receipts remain disposable local progress, separate from Requirements, ReviewReport and governance envelopes.

Separated branch base: `0828bdbc669569e7603ca84522e72452d400b525` on `codex/lean-requirements-evidence`. Proposal scope is limited to this change and the workflow sections of INTEGRATION/CHANGE_ORDER.

## Base refresh — 2026-10-01 Europe/Berlin

PR #482 is merged. The workflow planning branch now incorporates current dev at a6243c0b (including #486), and PR #484 targets dev directly. The merge was conflict-free and retains the workflow-only scope against dev. Runtime prerequisites and unchecked implementation tasks remain unchanged. Historical validation and exceptions above describe the original planning commits; this refresh uses normal hooks.

The normal Requirements hook reproduced unsupported-sidecar-schema for this proposal. This refresh adds a schema-v2 planned-inspection mapping for its nine existing requirements; it changes no runtime acceptance or signed producer prerequisite and uses no hook bypass.

## Risk-first planning creation validation — 2026-10-08

Scope: this existing paired change and its change-order section only. The owner explicitly authorized the supplied risk-first plan. This is documentation/planning work; executable assumption probes, TDD RED/GREEN, runtime adoption and bounded trials are inapplicable to creation and remain future unchecked tasks. No new skill/runtime command is activated. The 2026-10-04 amendment, independent producer authority, effective finding policy, source/index preservation, ownership and exact signed #481/v3 compatibility gates are retained.

### Baseline and prepared artifacts

- Isolated branch: `codex/plan-workflow-risk-first`; Git HEAD at creation validation `74d3fd4d`. Modules starts from refreshed `origin/dev` after merged PR #484. Core starts at draft PR #743's inspected head, with its base `codex/lean-requirements-evidence` at `c8635ed53965c51a1b06f4c2b1cc6a07dcf85f67`; its original branch/base is preserved.
- Proposal/design, existing ADDED capability deltas, unchecked tasks, planned evidence mappings and change ordering were reconciled. No duplicate change/capability, competing stage/command, report/receipt schema, verdict, ledger or automatic collection was introduced. Public artifacts contain adapted guidance and public sources; private research stays local.
- Delivery order: skills/projection -> deterministic verification -> bounded repair -> opt-in PR automation. Two engineer-days is an initial investment checkpoint, not a full-runtime estimate. Trials await a subsequently authorized nontrivial change in each repository.

### Executed checks

- OpenSpec CLI 1.13.2: `openspec validate workflow-01-turn-orchestration --strict --json --no-interactive` passed with no findings.
- `openspec validate --changes --strict --json --no-interactive`: 32/33 passed. The existing unrelated `requirements-03-backlog-sync` failure was reproduced before editing and remained identical afterward; no new all-change failure was introduced.
- Native Requirements evidence on the actual amended index snapshot, `--staged --required-maturity planned`, passed: schema 2, observed maturity `planned`, delivery status `proposal-only`, no source/mapping findings. Index staging was temporary and restored; no commit was made. Inspection cases use the existing native requirement identity convention with individual scenario intent/observable text; no executable selectors or historical proof were fabricated.
- Mapping file SHA-256 at validation: `148cdfcef0decfe8cf1411c854ea26a28aa1a6b11883900c19185bc0868bc51b`. Existing producer-generated evidence is ignored under `.specfact/reports/risk-first/`; it is planning evidence, not signed runtime compatibility acceptance.
- Scoped Markdown lint (repository core configuration), local planning-link integrity and `git diff --check` passed. Two pre-existing extra blank lines in the already touched modules change order were normalized. Every implementation/trial checkbox remains unchecked; all touched public paths are OpenSpec Markdown/YAML.
- Existing modules documentation command validation passed with no findings; `tools/validate_repo_manifests.py` validated seven manifests and the registry without asset edits.
- Existing `tests/unit/docs/test_docs_review.py`: 20 passed with `--no-cov`. One pytest cache-write warning came from sandbox permissions; it does not change the test outcomes or establish runtime/coverage admission.
- Native evidence used the owning modules planning gate with this worktree's Requirements/project sources and the existing local Python environment (Python 3.14.7).

### Tracking, ownership and limits

- [Existing issue #483](https://github.com/nold-ai/specfact-cli-modules/issues/483) synchronized with a dated, idempotent risk-first section, unchecked acceptance criteria, non-goals, verification/rollback and reciprocal public baseline proposal links. At creation completion the amendment was locally prepared/unpublished at those baseline links; subsequent publication is authorized below.
- Live readback: native User Story; native parent Feature #163; assignee `djm81`; organization project SpecFact CLI/1; Status Todo; labels `architecture, change-proposal, enhancement, openspec`. Titles, unrelated body content, milestone/project date fields and both native dependency directions were preserved. Modules QA is absent and was not created. Modules #483 remains blocked by #481 and blocks core #742/#492; core #742 remains blocked by modules #483.
- Both prescribed GitHub hierarchy cache refreshes succeeded. Core's required private wiki mirror/index and generated graph were updated without copying private content into public artifacts. Scoped mirror health has no findings; unrelated full-wiki health failures are recorded locally. Its prior modified graph was backed up, and unrelated source files were preserved.
- Python analyzer/code-review JSON, runtime tests, security/contract execution, signing/version bumps and release acceptance are inapplicable to this Markdown/YAML planning surface; no analyzer/runtime PASS or completed OpenSpec delivery is claimed. The existing modules planning-only analyzer applicability rationale remains in `openspec/AGENTIC_SDLC_VALIDATION.md`. These gates remain mandatory for their applicable implementation slices.
- During creation: no commits, pushes, new issues/PRs, PR retargeting, runtime implementation, trial execution or archival. Current policy remains effective; calibrated warnings and minimal-evidence cutover retain their separate owners.

Rollback: revert/disable new guidance/projection planning while retaining evidence and ordinary checks. Runtime rollout still uses coordinated configuration/module-pin rollback. Risks are added ceremony, narrow probes implying too much and mistaken defect dismissal; mitigate with limited assumptions, explicit proof boundaries and producer/current-input authority. Confidence: high in scoped planning/tracking consistency; medium in defect/overhead improvements. Monetary and causal savings remain unverified.

## Publication follow-up — 2026-10-08

The owner subsequently authorized committing/pushing both amendments, creating review PRs and monitoring CI/review with the CodeRabbit autofix skill. Both publication PRs target dev. Core incorporates only the reconciled workflow artifacts inspected at PR #743 head into refreshed origin/dev; draft PR #743, its branch and codex/lean-requirements-evidence base are preserved. This publication does not implement runtime, complete trial tasks, close either story or archive the changes. Applicable pre-commit checks and signed commit provenance remain required. Remote PR/check/review outcomes are reported separately; no green/review-complete result is inferred from local planning validation.

Publication hooks passed on the actual prepared candidates. Scoped mapping YAML lint passed with parsed-value equality after indentation adjustment. Local GPG signing is unavailable (No secret key); the publication route uses GitHub createCommitOnBranch with expected-head protection, then requires verified signature and exact tree equality with git write-tree before accepting the remote commit. No signing configuration or protected CI policy is changed. Runtime review/contract checks were skipped by their owning hooks for this planning-only scope, not claimed as runtime PASS.
