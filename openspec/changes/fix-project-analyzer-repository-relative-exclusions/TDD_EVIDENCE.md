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
