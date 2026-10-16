# Planning delivery validation

Validated on 2026-10-16, Europe/Berlin. This record covers architecture/OpenSpec artifacts and public issue alignment. It is not runtime acceptance, TDD evidence, a release receipt, or a completed implementation claim.

## Structural checks

- `openspec validate <change-id> --strict` passes for new modules changes 17, 18, 19 and 20, and core `code-review-local-report-adoption`.
- Strict validation also passes for touched native-platform, portable-reviewer-bootstrap and C15 modules lineage and the two touched core coordination proposals. The existing core protected/C15 proposals emit informational archive-compatibility warnings. Their historical delta defects were not changed or treated as new local-runtime acceptance.
- The actual Requirements lifecycle/source validator was run on the five explicit new source folders at required maturity `planned`. Its saved result is pass, observed maturity planned, delivery proposal-only, implementation evidence not-yet-available.
- The first run found core inspection scenario identifiers that did not match source requirement identities. That failing result is preserved. After correction, all five sources passed.
- Scenario/mapping inspection verifies 23 requirements, 50 unique inspection cases, valid mapped spec paths and 83 unchecked implementation tasks. No new TDD_EVIDENCE.md exists.
- Relative links in the five new packages resolve. `git diff --check` passes in both worktrees.
- Both diffs are confined to OpenSpec/history and audit artifacts. Production packages, tests, scripts, workflows, registry/manifests, versions/signatures and canonical `openspec/specs/` are unchanged.

## Independent review

An independent read-only artifact reviewer inspected the saved design, source scenarios, mappings and audit trail. No architecture blocker was found. The reviewer requested a roadmap count/date correction and final live metadata evidence. Counts/dates are corrected and the final GitHub readback is saved. The initial timestamp placeholder and initial mapping failure remain transparently corrected in the append-only trail.

The reviewer did not have the full parent transcript. Architecture-panel statements record the actual planning-turn dispatch and judgments; they are not claims of tested runtime capability.

## GitHub verification

[GitHub alignment](GITHUB_ALIGNMENT.md) records actual dispositions. Live before/after readback verifies the five planned stories and exact dependency edges, four Not Planned/Rejected predecessor closures, three unmerged PR closures, retained open #480 and unchanged independent/C15/protected metadata.

## Evidence and reproduction

Working evidence lives under `.audit/` in the modules worktree:

- `code-review-reset.tsv` is the append-only decision record.
- `code-review-reset-requirements-before-correction.json` preserves the initial mapping failure.
- `code-review-reset-requirements.json` is the corrected five-source planned-maturity result.
- `code-review-reset-structure.json` records requirement/scenario/task counts and artifact-only scope checks.
- `code-review-reset-github-before.json` and `code-review-reset-github-after.json` record actual public metadata.
- `code-review-reset-core.patch` preserves the companion core artifact diff for recovery.

The local reproduction helpers are `/private/tmp/specfact_verify_reset_artifacts.py` and `/private/tmp/specfact_code_review_reset.py`. The former reads saved files and checks structure/scope. The latter's `verify` action only reads GitHub and writes a fresh local readback; its other actions mutate GitHub and are not verification commands. Replacement-runtime tests and installed acceptance were not executed or claimed.

## Planning PR checks

The normal staged modules hooks passed with the paired core checkout selected through `SPECFACT_CLI_REPO`. They verified module signatures, formatting, manifests, bundle imports, command/documentation checks and planned Requirements evidence. The hook found no Python review targets and ran 28 existing contract tests successfully. These tests do not prove the proposed replacement runtime.

The normal core hooks passed their applicable planning checks with the clean module fixture at the exact commit and tree pinned by core. They verified version consistency, staged Markdown and planned Requirements evidence. No Python review targets or changed contract inputs were selected. The full-repository YAML command reports unrelated existing errors while returning success; the new core mapping was corrected and checked separately. No gate or signing policy was changed.

## Remaining work

All 83 implementation tasks remain for follow-up sessions. The first implementation unit is #513's existing/cold detached Hatch bootstrap workflow. Public reviewer cutover is #515; exact installed/platform acceptance is #516 after paired core #769. Current runtime/security/review gates remain in force until their explicit replacement implementation lands.

The paired core internal-wiki source mirror and C14/C15 compatibility notes were aligned on 2026-10-16. The native graph rebuild includes core adoption at 0/12 implementation tasks. Strict wiki health reports 59 pre-existing errors, down from 62, with no introduced errors; unrelated source pages were preserved. The full design/scenarios are also preserved publicly on the new stories. Planning branches are prepared for separate pull requests to `dev`. No merge, registry publication, signed module release or runtime support is asserted.
