# Change Validation

Implementation was authorized on 2026-09-12 after the historical planning checkpoint below. Current status: In Progress; production fixes and candidate CI are under validation. Public signed-release acceptance remains pending. See TDD_EVIDENCE.md for executed regressions and hosted failures.

## Historical planning checkpoint

- Checked: 2026-09-12T23:23:44+02:00 (Europe/Berlin).
- Delivery maturity: planned; implementation evidence: not-yet-available.
- Planning base: `a6bac86ec529715b9122a7a670ee4886a749d9f6`; runtime reference module 0.49.77.
- Issue: [#466](https://github.com/nold-ai/specfact-cli-modules/issues/466), open and Todo.
- Worktree: `codex/bugfix-code-review-capsule-customer-execution`, based on refreshed origin/dev.
- Validation environment: macOS, serially bootstrapped worktree Hatch environment (Python 3.14.7); repository dev-deps selected the existing local core checkout. This environment validates planning only, not the supported Linux customer runtime.

## Verified planning checks

- `openspec validate code-review-capsule-customer-execution --strict`: passed.
- `markdownlint --disable MD013 MD060 -- <changed Markdown files>`: passed. The first run found an issue-reference line interpreted as a heading; wording was corrected and rechecked. Disabled rules match existing planning prose/table formatting.
- `PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --staged --required-maturity planned --output .specfact/reports/capsule-planning-requirements.json --summary .specfact/reports/capsule-planning-requirements.md`: passed; one source passed, zero failed/skipped, observed maturity planned. Seven requirements map to fourteen scenario inspection cases. An initial direct invocation omitted the canonical hook import paths; the corrected invocation above passed.
- `hatch run yaml-lint`: passed for seven manifests and registry.
- `hatch run check-bundle-imports`: passed.
- `hatch run ruff check .` and `hatch run ruff format . --check`: passed; 1255 files already formatted.
- `hatch run python scripts/verify-modules-signature.py --payload-from-filesystem --enforce-version-bump --version-check-base origin/dev --allow-missing-public-key`: passed for all seven manifests under the documented dev-branch policy. No local signing public key was configured; this proves unchanged payload/checksum and version consistency, not a new cryptographic signature verification. No signed payloads, manifests or registry entries changed.
- `scripts/pre_commit_code_review.py <staged paths>`: returned zero and explicitly skipped analyzer review because there are no Python targets. No analyzer PASS or synthetic code-review JSON is claimed.
- `./scripts/pre-commit-quality-checks.sh all`: passed. Formatting left 1255 files unchanged; YAML/import, generated command overview/contract (115 command paths), core documentation accountability, docs commands and planned Requirements evidence passed. The hook classified the delivery as safe planning/documentation and skipped code review/contract execution. Generated command artifacts remained identical to the base.
- `git diff --cached --check`: passed.

## Metadata readback

GitHub readback confirmed type Bug; assignee djm81; labels bug/codebase/openspec/change-proposal; no milestone; native parent #163 under #162; SpecFact CLI project with Todo status; no blocked-by prerequisites; native blocking set contains core #680.

Core #680's native blocked-by set contains the new modules #466 plus existing modules #459 and #431. No pre-existing edge was removed. Related #460 receives no redundant transitive edge. The new issue was checked open/Todo, not In Progress.

## Acceptance boundary

The original planning checkpoint contained proposal/design, investigation, spec deltas, future tasks, planned Requirements evidence and change order only. That checkpoint did not claim Linux reproduction, analyzer PASS, runtime fixes, release publication or completion. All 23 future tasks remain unchecked. The planning PR uses Refs #466, targets dev, and must not close the bug. Future production changes require their own recorded failing/passing evidence, quality review and signed release acceptance.

## Implementation review checkpoint — 2026-09-13 Europe/Berlin

- Normal signed-commit hooks passed payload/version policy, formatting, YAML, import boundaries, typing/lint, changed-line SpecFact code review and 28 contract tests for d14ce7e2. The canonical signing bot then signed the updated manifest.
- Earlier full and smart suites passed 1,829 and 1,830 tests respectively. New runtime-specific selectors passed 141 tests. Fresh broad verification is required after subsequent edits.
- Historical hosted run 34723324162 reached real CLI execution but failed before all analyzers could run. All three revised v2 runtimes were subsequently published with explicit owner approval and their manifests/configs verified anonymously. Run 34723950359 then reached analyzer execution and exposed child startup, private cache, and packaged rule defects. Current fixes remain under candidate validation; no three-ABI PASS or public release acceptance is claimed.
- Review assertions that full scope bypasses capsules and installed payloads permit unsigned execution were checked against production code: commands imports run_capsule_review, and installed_module_identity_from_core requires signature=True, integrity=True and the approved public key. Actual full-scope hosted reports contain all ten capsule rows. Those assertions do not describe the current path.
- Planning-only review comments are superseded by the user's explicit implementation authorization; CHANGE_ORDER now reflects it. Materialization and release scenarios now explicitly cover all three ABIs, two cache roots, and the selected Ubuntu image.

## Combined repair checkpoint — 2026-09-13 Europe/Berlin

The revised gate requires actual pytest execution, including a deliberately failing assertion, before accepting clean-fixture evidence. It probes denied namespaces separately, compares fresh caches under umasks 022/077 and warm offline reuse, and checks private writes plus denied sealed-runtime writes. The repository lane runs an exact-commit, dependency-compatible source/test slice and records blob identities; it does not claim full-repository suite acceptance. See GATE_TDD_EVIDENCE.md, PYTEST_TDD_EVIDENCE.md and REVIEW_EVIDENCE.md for additional red/green evidence.

The reusable customer workflow runs once for relevant PR changes through the PR orchestrator and independently for public registry/release/manual events. Existing required quality checks depend on the customer matrix and explicitly fail when a required capsule result is failed, cancelled, or skipped, including dev-to-main PRs. Unrelated PRs skip the expensive matrix and retain their normal checks. No branch-protection changes or duplicate customer matrices are required.
