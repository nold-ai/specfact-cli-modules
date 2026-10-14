# TDD evidence

2026-10-14 Europe/Berlin. Independent spec was written and `openspec validate code-review-correspondence-candidate-prefilter --strict` passed before tests and source edits.

Original complete literals were captured from commit 5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b, differential.py SHA-256 aa60b0854e31fad55b2c8efa53ffb32c92ab772ffbf8c8e565c2d8b6e45988e9. Capture command, actual Python 3.14.7, dependency versions, source/runner loaded identity, seed 20261014 and inventory are frozen in baseline_provenance.json. Capture completed in 0.1972071659984067 seconds under a 30-second signal alarm. 107 complete public requests/results and seven actual original _classify_range_member projections were saved. Output bytes SHA-256 f82b8eefd0599d9482867c502ac53fc98c1b54196ceea364e4f75c1f0f2e1d9a. Three bound cases lower one constant each; exact production limits are checked directly without large DP.

Before source changes, this command produced the real RED:

```sh
PYTHONPATH=packages/specfact-code-review/src:src /private/tmp/specfact-cli-modules-worktrees/codex/native-pylint-execution-budget/.venv/bin/python -c 'import signal,pytest; signal.alarm(60); raise SystemExit(pytest.main(["tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py", "tests/unit/specfact_code_review/run/test_range_candidate_prefilter.py", "-q", "--override-ini", "addopts="]))'
```

Result: 1 failed, 119 passed in 0.27 seconds. `test_unique_candidates_build_only_four_forbidden_matrices` failed at `assert forbidden == 4`, actual `10`. All original literal and consumer comparisons passed. An earlier command using `--timeout=30` exited 4 because pytest-timeout is absent; that is a tooling failure, not RED. The replacement uses a process alarm and installs nothing.

These are borrowed-interpreter, isolated source-path checks, not installed signed/native acceptance. All full repository, native exact-head, signature/version and independent review gates remain pending under root ownership.

## Passing-after and available checks

The same alarm-bounded command with existing `tests/unit/specfact_code_review/run/test_differential.py` added passed 227 tests in 0.36 seconds after final formatting. The new tests account for 120 and the unchanged existing differential suite for 107. Existing suppression tests ran as part of that file. The work test verifies four forbidden builds and six total builds. This counts synthetic work only; it measures neither historic root cause nor native completion.

With `BIN=/private/tmp/specfact-cli-modules-worktrees/codex/native-pylint-execution-budget/.venv/bin` and `FILES` equal to the changed differential.py and the two new test Python files, the following scoped commands ran through `subprocess.run(..., timeout=60)`:

- `$BIN/ruff check $FILES`: exit 0.
- `$BIN/ruff format --check $FILES`: exit 0, three files formatted.
- `$BIN/basedpyright --venvpath /private/tmp/specfact-cli-modules-worktrees/codex/native-pylint-execution-budget $FILES`: exit 0, zero errors/warnings/notes.
- `PYTHONPATH=packages/specfact-code-review/src:src $BIN/pylint --persistent=no $FILES`: exit 16, two pre-existing production findings remain. C0301 at current line 933 is 163/120 characters; C0302 is 1685/1000 module lines. Original source supplied through `git show 5b451ec066e0ea5cbd8a97ef3b59d915ae54fe5b:packages/specfact-code-review/src/specfact_code_review/run/differential.py` to `$BIN/pylint --persistent=no --from-stdin packages/specfact-code-review/src/specfact_code_review/run/differential.py` also exited 16 with C0301 at original line 911, 163/120, and C0302, 1663/1000. This is not a lint PASS. No new test-file lint findings remain.
- `openspec validate code-review-correspondence-candidate-prefilter --strict`: exit 0 after final artifacts.
- `git diff --check`: exit 0.

Initial scoped Ruff and type runs found test-formatting/type issues, which were corrected before the final commands. The first type invocation also could not find the worktree .venv; explicitly resolving the existing borrowed venv fixed dependency resolution without installation or environment modification. Hatch was not used.

Full repository format/type/lint/yaml/bundle/signature/contracts/smart/full tests, native exact-head review and trusted signing remain root-owned and incomplete here. No existing gate was waived. The original module-package.yaml, runner.py, existing differential tests, all final continuity functions and suppression functions remain unchanged. Independent review is next.

## Importlib collection correction

On 2026-10-14 CodeRabbit identified the new sibling test import as a major collection defect. The earlier GREEN commands used `--override-ini addopts=`, which removed the repository's importlib setting and did not establish normal repository collection readiness. Preserve those historical component results and the independent production work-count RED above.

Before this correction, the normal environment was set to exactly these three source roots, with no test-directory injection:

```sh
PYTHONPATH=/private/tmp/specfact-cli-modules-worktrees/codex/correspondence-prefilter-20/packages/specfact-code-review/src:/private/tmp/specfact-cli-budget-docs/src:/private/tmp/specfact-cli-modules-worktrees/codex/correspondence-prefilter-20/src
SPECFACT_MODULES_REPO=/private/tmp/specfact-cli-modules-worktrees/codex/correspondence-prefilter-20
```

Using the same borrowed Python, `python -m pytest tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py tests/unit/specfact_code_review/run/test_range_candidate_prefilter.py -n 0 -p no:cacheprovider -q` exited 2. It collected seven items and failed collection of the main test module with `ModuleNotFoundError: No module named 'test_range_candidate_prefilter'` at its line 21. This is the import-fix RED, distinct from the earlier production assertion `10 == 4`.

The correction consolidates `range_projection` and its seven tests into `test_correspondence_candidate_prefilter.py`, removes the new baseline-absent sibling test file, and updates the requirement node mapping. It changes no production code, assertions, fixtures or provenance. No generic helper module or test-path configuration is added.

With that exact source-only environment, both commands below ran under 60-second `subprocess.run` timeouts without overriding repository addopts:

```sh
python -m pytest tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py tests/unit/specfact_code_review/run/test_differential.py -p no:cacheprovider -q
python -m pytest tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py tests/unit/specfact_code_review/run/test_differential.py -n 0 -p no:cacheprovider -q
```

Parallel normal configuration created two workers and passed 227 tests in 0.93 seconds. Serial importlib collection collected 227 and passed all in 0.33 seconds. The source-hash capture guard was also executed with `python tests/unit/specfact_code_review/run/test_correspondence_candidate_prefilter.py --capture-original` under a 30-second subprocess timeout. It exited 1 on the expected original-source hash assertion before any writes. Both fixture hashes stayed unchanged: outputs `f82b8eefd0599d9482867c502ac53fc98c1b54196ceea364e4f75c1f0f2e1d9a`, provenance `1c93e0a1b283083f23c5d2aab7d20d75c44cad41f758ddbd3c71d82ac79c7ed9`. Provenance remains the historical capture record, not a rewritten description of this corrected test layout.

Scoped Ruff check, Ruff format check and basedpyright with the borrowed `--venvpath` pass on differential.py and the consolidated test file. Scoped Pylint still exits 16 for the same two production findings recorded above. The changed test file has no Pylint findings. All tools used the same source-only environment and 60-second subprocess limits. Full/native/signature/review acceptance remains pending. The root owns affected-scope independent closure of this correction.
