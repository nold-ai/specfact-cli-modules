# Change: Expose bounded Linux analyzer failure provenance

## Why

PR [#524](https://github.com/nold-ai/specfact-cli-modules/pull/524) remains blocked at head `59611f358572aaa3c383c2d2fffcf82fb57ff36c`. The Linux reports establish failed pytest evidence and independent contract uncertainty, but the public projection discards information needed to identify the remaining exceptions. It also displays retained findings without lifecycle and blocking fields needed to determine whether they are fixed or active.

The investigation establishes the native skip prerequisites and the diagnostic information loss. It does not establish the separate Linux pytest or CrossHair exception. See [the investigation](INVESTIGATION.md). Repairing an assumed exception or adding capsule dependencies now would exceed the evidence.

## What changes

Prepare one diagnostic-only implementation unit for owner approval:

- Extend the existing candidate and independent CI projections with bounded analyzer side and failure-class observations for readable reports, including ordinary structured reports.
- Preserve existing finding lifecycle and explicit blocking fields in the public projection.
- Classify known native-prerequisite skip details using existing pytest observations. Missing details remain unknown.
- Test the actual workflow projection snippets with Python-only fixtures in a new focused test file. Preserve every existing workflow test and required gate.

The owner approved this diagnostic-only implementation on 2026-10-25, Europe/Berlin. It does not promise green CI. The next decision uses actual exact-head Linux evidence to select a separate, justified repair if one is necessary.

## Capabilities

### New capabilities

- `linux-analyzer-failure-diagnostics`: bounded CI failure provenance with unchanged review authority.

### Modified capabilities

None. Existing report schema, analyzer behavior, differential enforcement, runtime admission, and acceptance requirements remain authoritative.

## Intent and approval boundary

User-confirmed outcome: a Python developer reviews their own trusted repository without SpecFact dependency conflicts or manual environment repair. The first existing/cold detached Hatch milestone belongs to #513 and change 17. This follow-up improves diagnosis of its mandatory Linux review without introducing customer setup steps.

The user requested investigation and a minimal scoped OpenSpec change on 2026-10-25, Europe/Berlin, then explicitly approved implementation, all required gates, and exact-head Linux verification. Actual exception repairs, acceptance ownership changes, or capsule resource admission require a further evidence-based scope decision.

## Dependencies and non-goals

This modules CI follow-up is tracked under the existing authorized #513 takeover and #524, separate from changes 17 through 20 and #518 baseline smoke-identity maintenance. No paired core runtime change is proposed. Fresh public metadata confirms parent #163, Project SpecFact CLI, owner djm81, required labels, no direct blockers, and unchanged downstream #514/#515 relationships. Reuse the dedicated #513 branch/worktree so exact-head verification observes the original failing subject. No additional issue or duplicate implementation branch is needed for this bounded unit.

Excluded: host environment or executable pass-through, new mounts, native capsule support, new dependencies, toolchain pins/locks or assets, timeout increases, test deselection/skips/xfail, changed enforcement or verdicts, reviewer replacement, customer reviewer adoption, other managers/platforms, and unrelated cleanup. Do not merge #524 or archive change 17 on diagnostic evidence.

## Impact and completion

Implementation files are `.github/workflows/capsule-customer-execution.yml` and `tests/unit/test_capsule_analyzer_diagnostics.py`, plus a narrow update to existing exact-output expectations in `tests/unit/test_capsule_review_projection.py` and this change's evidence. The existing tests remain enabled and retain exact assertions. No signed module payload, manifest, registry row, CLI syntax, report schema, or public documentation permalink changes are planned. If that boundary cannot hold, stop for scope review.

Completion requires failing-before and passing-after projection tests, unchanged privacy and authority invariants, all applicable repository gates, independent review, and actual exact-head candidate/independent Linux projections. Underlying review failures remain blocking. Strict OpenSpec validation proves artifact structure only.

Effort is bounded to one projection/test unit and one verification cycle after changed inputs. No measured implementation or monetary estimate is available. If safe diagnostics cannot be obtained within existing report fields, stop with the missing evidence. Rollback reverts the diagnostic unit without altering reviewer decisions.

## Source tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- Related issue: [#513](https://github.com/nold-ai/specfact-cli-modules/issues/513).
- Related PR: [#524](https://github.com/nold-ai/specfact-cli-modules/pull/524).
- Tracking: #513, with the owner's bounded diagnostics approval recorded in its public scope.
- Status: diagnostic-only implementation approved; runtime/admission repairs remain unapproved.
