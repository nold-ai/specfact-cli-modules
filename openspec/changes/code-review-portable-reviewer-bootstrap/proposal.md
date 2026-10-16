# Repair the authenticated portable reviewer before native promotion

## Remaining capsule scope superseded (2026-10-16)

The owner explicitly replaced the capsule/sandbox approach with trusted local project-aware review. Modules #513-#516 and core #769 now own the replacement sequence. This partially delivered lineage remains in place to preserve shipped fixes, experiments, original task states and evidence. Its remaining capsule preparation, isolation, native publication and installed-capsule acceptance tasks are retired, not completed. Historical unchecked tasks below are not current implementation authority. No runtime code is removed and no unimplemented delta is promoted by this planning delivery.

See [the replacement design](../code-review-17-project-runtime-bootstrap/design.md) and [issue dispositions](../code-review-17-project-runtime-bootstrap/GITHUB_ALIGNMENT.md). Native release/repair PRs #506/#509/#510 and capsule prerequisite #512 are superseded. Reuse customer-observable correctness cases as replacement tests; preserve independent signing/security obligations.

## Why

Published Code Review 0.51.0 rejects explicit changed tests when multiple source
files share a basename, and the full #498 workload reaches the unchanged Pylint
30-second deadline. The candidate corrections cannot modify that immutable
installed reviewer. The owner explicitly approved preparing a separate small
reviewer-update PR on 2026-10-07 for human merge/promotion.

## What Changes

- Honor provided corresponding tests before declaring basename ambiguity; retain
  rejection when explicit correspondence is absent.
- Cache pinned Pylint 4.0.7 similarity hashes only within one invocation, bounded to
  256 object/minimum-line keys, restoring the original function and clearing entries
  on every exit. Retain checkers, pair order, jobs, return codes and deadlines.
- Prepare the signed module patch release from dev, separately from native #498.
- Correct the retired independent-review installation pin to authenticated 0.51.0,
  retaining all host assertions through the already approved context separation.

## Impact

Refs nold-ai/specfact-cli-modules#460; prerequisite for PR #498. No core change,
authenticated installed patch, rule disablement, new CI deadline, automatic merge
or publication. Human-reviewed authenticated promotion and subsequent exact #498
Linux timing remain required. Bootstrap preparation is bounded to the selection
helper, Pylint wrapper, regression tests, the verified installation-pin correction
and its required host/portable proof entry points, plus release/evidence metadata.

The owner explicitly approved bounded sealed CrossHair diagnosis and a verified
root-cause correction on 2026-10-08. Existing selected contracts, checker options,
30/120-second adapter bounds and300-second analysis bound remain unchanged.
Temporary sampling is candidate evidence and must be removed after diagnosis.
