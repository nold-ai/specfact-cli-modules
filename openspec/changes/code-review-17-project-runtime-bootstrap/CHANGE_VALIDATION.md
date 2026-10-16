# Planning delivery validation

Validated on 2026-10-16, Europe/Berlin. This record covers architecture/OpenSpec artifacts and public issue alignment. It is not runtime acceptance, TDD evidence, a release receipt, or a completed implementation claim.

## Structural checks

- `openspec validate <change-id> --strict` passes for new modules changes 17, 18, 19 and 20, and core `code-review-local-report-adoption`.
- Strict validation also passes for touched native-platform, portable-reviewer-bootstrap and C15 modules lineage and the two touched core coordination proposals. The existing core protected/C15 proposals emit informational archive-compatibility warnings. Their historical delta defects were not changed or treated as new local-runtime acceptance.
- The actual Requirements lifecycle/source validator was run on the five explicit new source folders at required maturity `planned`. Its saved result is pass, observed maturity planned, delivery proposal-only, implementation evidence not-yet-available.
- The first run found core inspection scenario identifiers that did not match source requirement identities. That failing result is preserved. After correction, all five sources passed.
- Scenario/mapping inspection verifies 23 requirements, 55 unique inspection cases, valid mapped spec paths and 89 unchecked implementation tasks. Review follow-ups add C15 compatibility and unsupported same-major scenarios plus explicit future release, installation-test, executable evidence binding and PR-delivery steps, plus provisioned offline acceptance in core and modules. No new TDD_EVIDENCE.md exists.
- Relative links in the five new packages resolve. `git diff --check` passes in both worktrees.
- Both diffs contain planning/history, audit artifacts and one repaired documentation cross-link in `scripts/macos_managed_boundary/README.md`. Runtime source, tests, executable scripts, workflows, registry/manifests, versions/signatures and canonical `openspec/specs/` are unchanged.

## Independent review

An independent read-only artifact reviewer inspected the saved design, source scenarios, mappings and audit trail. No architecture blocker was found. The reviewer requested a roadmap count/date correction and final live metadata evidence. Counts/dates are corrected and the final GitHub readback is saved. The initial timestamp placeholder and initial mapping failure remain transparently corrected in the append-only trail.

The reviewer did not have the full parent transcript. Architecture-panel statements record the actual planning-turn dispatch and judgments; they are not claims of tested runtime capability.

## GitHub verification

[GitHub alignment](GITHUB_ALIGNMENT.md) records actual dispositions. Live before/after readback verifies the five planned stories and exact dependency edges, four Not Planned/Rejected predecessor closures, three unmerged PR closures, retained open #480 and unchanged independent/C15/protected metadata.

## Evidence and reproduction

The committed [validation receipt](../../../.audit/code-review-reset-validation.json) contains the original mapping failure, repeated current planned-maturity results, current structural counts, the before/after public issue disposition snapshots and the planning-review probe results. It projects actual observations without full scenario prose or unrelated GitHub transport fields. Historical snapshots are labeled separately from current inspection. The [decision trail](../../../.audit/code-review-reset.tsv) is append-only.

The paired core artifacts are reviewable in [core PR #770](https://github.com/nold-ai/specfact-cli/pull/770). Uncommitted recovery patches and temporary helper scripts are local scratch state, not published evidence or reproduction prerequisites.

From each repository, validate its named replacement changes with `openspec validate <change-id> --strict`. The ordinary modules evidence adapter can repeat branch inspection with:

```sh
PYTHONPATH=packages/specfact-project/src:packages/specfact-requirements/src hatch run python scripts/requirements_evidence_gate.py --base-ref origin/dev --required-maturity planned --output /tmp/code-review-reset-planned.json
```

Core repeats the equivalent check with `scripts/requirements_evidence_delivery_gate.py --base-ref origin/dev --required-maturity planned --output /tmp/core-review-planned.json --summary /tmp/core-review-planned.md`, through Hatch with `SPECFACT_MODULES_REPO` pointing at a clean checkout of the exact commit/tree in core's `ci/module-fixture.lock.json`. Neither command supplies protected authority. Replacement-runtime tests and installed acceptance were not executed or claimed.

## Planning PR checks

The normal staged modules hooks passed with the paired core checkout selected through `SPECFACT_CLI_REPO`. They verified module signatures, formatting, manifests, bundle imports, command/documentation checks and planned Requirements evidence. The hook found no Python review targets and ran 28 existing contract tests successfully. These tests do not prove the proposed replacement runtime.

The normal core hooks passed their applicable planning checks with the clean module fixture at the exact commit and tree pinned by core. They verified version consistency, staged Markdown and planned Requirements evidence. No Python review targets or changed contract inputs were selected. The full-repository YAML command reports unrelated existing errors while returning success; the new core mapping was corrected and checked separately. No gate or signing policy was changed.

## Remaining work

All 89 implementation tasks remain for follow-up sessions. The first implementation unit is #513's existing/cold detached Hatch bootstrap workflow. Public reviewer cutover is #515; release-level installed/platform acceptance is #516 after paired core #769 supplies consumer-compatibility preflight evidence. Current runtime/security/review gates remain in force until their explicit replacement implementation lands.

The paired core internal-wiki source mirror and C14/C15 compatibility notes were aligned on 2026-10-16. The review follow-up updates core adoption to 0/18 implementation tasks and retains C15 schema 1.7 dispatch until separately authorized retirement. Initial alignment had 59 pre-existing wiki errors, down from 62. The follow-up observes 58 and introduces none; an unrelated coverage improvement occurred independently. The final release-order alignment observes 59 errors both before and after; an independently added source is missing from the wiki index. This alignment introduces none. Unrelated source pages were preserved. The original design/scenarios are also preserved publicly on the new stories; the PR artifacts contain the subsequent review refinements. No merge, registry publication, signed module release or runtime support is asserted.
