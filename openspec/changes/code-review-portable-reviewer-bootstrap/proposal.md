# Repair the authenticated portable reviewer before native promotion

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

## Impact

Refs nold-ai/specfact-cli-modules#460; prerequisite for PR #498. No core change,
authenticated installed patch, rule disablement, new CI deadline, automatic merge
or publication. Human-reviewed authenticated promotion and subsequent exact #498
Linux timing remain required. Bootstrap preparation is bounded to the selection
helper, Pylint wrapper, regression tests and normal release/evidence metadata.
