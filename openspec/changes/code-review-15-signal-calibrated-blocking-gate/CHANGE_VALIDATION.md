## Recovery review — 2026-09-20

Recovered from uncommitted planning files on `feature/code-review-15-signal-calibrated-blocking-gate`; the source worktree contains only this proposal and its change-order edit. Imported into local `dev` and the R09 planning worktree. No runtime changes were imported. Historical readiness and version identities below are dated context and must be revalidated before implementation. Recovery validation preserves existing staged-review scenarios and classifies previously nonexistent requirement headers as ADDED, avoiding invalid archive replacements. Canonical C14 follow-up reconciliation remains a prerequisite to final C15 specification promotion.

# Change Validation

## Repository reality — 2026-09-20

- Current runner code emits schema 1.6 (`packages/specfact-code-review/src/specfact_code_review/run/runner.py`).
- Modules C14 #416 shipped and is closed; its proposal awaits archival reconciliation.
  Its implementation is not an open prerequisite. Before final C15 specification
  promotion, reconcile C14's mixed completed and unchecked deltas, then use
  `openspec archive code-review-14-scope-truth-and-differential-enforcement`
  for the reconciled shipped change. Do not mark unchecked work complete or promote
  unimplemented deltas merely to archive it; this planning PR does not perform
  that reconciliation.
- Protected core C14 adoption #680 remains distinct and pending; verify its release and the compatible signed module pair before C15 implementation.
- Policy-02 and governance-02 remain prerequisite authorities to revalidate.
- C15 is the schema 1.6 -> 1.7 migration owned by #417 and paired core #679. Requirements policy #481 -> core #740 does not replace this sequence.

## Decision

The OpenSpec artifacts may be reviewed and validated now. Production tests/code,
module version/signature changes, dogfood enforcement, and core adoption remain
blocked until tasks 1.2-1.4 are satisfied.
