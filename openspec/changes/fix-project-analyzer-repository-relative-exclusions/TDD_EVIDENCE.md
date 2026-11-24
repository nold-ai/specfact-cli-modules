## Before the fix

Python 3.11.15, with the Project analyzer loaded from this worktree. The
test calls `CodeAnalyzer.analyze()` on identical source under different paths.

```text
AssertionError: assert 0 == 1
3 failed, 6 passed
```

The failures cover a parent name containing `env`, a repository name
containing `build`, and a production path containing `dist` and `env`.
The ordinary source and the existing directory and test-file exclusions
produce the expected feature counts.

## After the fix

The same nine regression cases and the remaining Project tests pass on
Python 3.11.15. The full Project test directory reports 32 passed. The
production delta is limited to the existing path filter.

On 24 November 2026, the unchanged exclusion fix and regression cases were
checked against the signed Project analyzer migration in #532. All 90 selected
Project tests passed with 81.89% branch-inclusive analyzer coverage. The direct
refresh onto protected dev passed the exclusions tests but measured 40.29%
against the existing 80% gate. This branch follows #530 and #532 so it can
retain the required gate and the existing exclusion behavior.
