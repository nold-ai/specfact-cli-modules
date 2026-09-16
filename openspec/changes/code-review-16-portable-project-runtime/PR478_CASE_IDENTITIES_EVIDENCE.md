# Case-sensitive snapshot test coverage

Native run [35073276747](https://github.com/nold-ai/specfact-cli-modules/actions/runs/35073276747) recorded two skipped case-collision tests on Linux. These tests previously exercised only case-insensitive filesystems.

The test now asserts the actual filesystem contract on both platforms: reject case aliases when the filesystem conflates them; otherwise materialize both exact Git blob contents, require distinct file identities (and distinct parent directories in the directory case), and verify the complete resulting tree. No runtime implementation or review failure policy changed, and the original rejection assertion remains.

Local validation on 2026-09-16 (Europe/Berlin), macOS / Python 3.14.7:

```text
hatch run python -m pytest tests/unit/specfact_code_review/run/test_runner.py -k materialization_preserves_case_identities -q
2 passed, 406 deselected in 0.41s
hatch run python -m ruff check tests/unit/specfact_code_review/run/test_runner.py
All checks passed!
hatch run python -m ruff format --check tests/unit/specfact_code_review/run/test_runner.py
1 file already formatted
```

Linux capsule execution of the case-sensitive branch remains pending the next native run. This test-only expansion is not evidence of new production behavior or a waiver for skipped required analysis.

Independent review found no functional findings. The new assertions were extracted into a named helper after review identified added test complexity; final Radon complexities are 6 for the test and 7 for its helper. All assertions remain.
