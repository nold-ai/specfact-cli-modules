# Bounded observer follow-up evidence

Observed on 14 October 2026 (Europe/Berlin), starting at `55882c25b28cbb52dd179f130eab3dd92a625166`. This records prospective diagnostic behavior, not activation, hosted acceptance or a root-cause verdict. Signed reviewer 0.51.2, analyzer commands, deadlines, gates and actual workflow bodies remain unchanged.

## Contract and source

The approved synthesis selects four optional bounded counts and fixed producer classifications. The source is the extracted signed 0.51.2 `portable_worker.py`, especially `validate_observation`, and the retained-message handling in `contract_runner.py`. The worker's terminal set is call identities union skipped identities. Failed setup alone is not terminal. Global findings carry no authoritative snapshot side.

The source and design evidence is retained under `/private/tmp/specfact-pr506-510-repair/reviewer-0512-source` and `/private/tmp/specfact-pr506-510-repair/diag2/{design-a.md,design-b.md,design-c.md,synthesis.md}`. The approval record is `/private/tmp/specfact-pr506-510-repair/diagnostics-approval.md`.

## Spec, tests, RED, prospective code, GREEN

1. Extended this change's spec and design before adding tests.
2. Added table-driven real observer subprocess tests in the existing projection-test seam. Cases include duplicate and unrelated identities, failed calls, skipped and failed setup, malformed records, complete-input entry bounds, per-string and aggregate character bounds, coverage-map structure, producer token delimiters, retained CrossHair prefixes and side/global provenance. Fixed parameter IDs keep private inputs out of test names.
3. Ran the new tests against the unchanged workflow before generating prospective code. `red-valid.log` records **116 failed, 28 passed**. Representative genuine failure is `assert {} == {'call_identity_count': 1, 'coverage_files_count': 1, 'failed_setup_records_count': 0, 'unexecuted_collected_count': 0}`. Known producer classes and retained-prefix positives also failed because the old observers omitted them.
4. Generated only private `.v2.py` bodies after that RED. Later validation cases extended malformed-record and exact-character-limit coverage. `red-expanded.log` records **130 failed, 28 passed** against the still-unchanged workflow. This expansion is supplemental boundary evidence, not claimed as pre-implementation evidence for all 158 cases.
5. Injected prospective bodies only into private test reads of workflow YAML. `prospective-green-final.log` records **301 passed**, comprising the original 143 tests and 158 added cases. The existing valid-observation expectation gained only three newly available fields. No old assertion was removed. This private test copy is not production workflow activation.
6. Saved the complete activation test delta as `/private/tmp/specfact-pr506-510-repair/diag2/tests-activation.patch` and restored the repository test file byte-for-byte to the starting HEAD. The checker-only ordinary commit therefore need not contain tests that expect inactive behavior. The restored test file passes all 143 original tests in `unchanged-workflow-green.log`.

The first attempt, `red.log` (**123 failed, 21 passed**), included report fixtures missing `analyzer_evidence`; the independent observer correctly rejected those incomplete reports. Those failures are fixture failures, not genuine behavior RED. The fixtures were corrected before the genuine RED run and before prospective implementation. A later restore script initially ran under a Python without PyYAML and made no changes; it was rerun successfully with `.venv/bin/python`. Its incidental repeated RED run provides no new evidence and is not used as a passing baseline claim.

## Exact prospective body identities

Hashes cover exact extracted heredoc bytes without a trailing newline, matching the existing authority convention.

| Program | Previous approved SHA-256 | Prospective SHA-256 |
| --- | --- | --- |
| `PY_CANDIDATE_FAILURE` | `ead9d88db8dfd7e8aeb936135db7c9358cf6fb4dc861efce6a7497078508dfa1` | `cf4a6d94d511a2847beda3e577e2edcdcb4c929ed5c436976afe07c56fa47e10` |
| `PY_REVIEW_FAILURE` | `8052e2ea961ba3109f78ea70f637827cc60f234692842acda0c5d72de61794b9` | `3611f90e4720f1efde80ab96906d8ac48e93cfdccfb7e966ca4dd66fc031a36a` |

`body-provenance.json` verifies that the baseline `.old.py` bodies equal actual current workflow extraction. Both prospective bodies contain the same `observation_helpers.v2.py` bytes. Their unchanged surrounding program bytes are copied from those exact prior bodies. The regeneration script, plugin, full activation test copy, hashes and logs are retained in `/private/tmp/specfact-pr506-510-repair/diag2/`.

## Quality checks and limits

Strict OpenSpec validation passes. Activation tests and the changed common helper pass Ruff and basedpyright with zero errors or warnings. The activation test file passes repository formatting. Extracted bodies pass Ruff with only W292 excluded because the authority hashes exclude the final newline. The full extracted independent program still produces two basedpyright errors in unchanged outer `sorted` expressions; `types-baseline-review.log` proves they also exist in the previous approved body. The changed helper has no remaining diagnostics. No full-repository or hosted gate is represented as newly passed by these checks.

The tests stay at the existing trust seam because they execute both actual inline programs through the existing subprocess helper; adding a second production helper or test loader would widen this bounded contract. The matrix uses case names and builds private fixtures inside the test, avoiding huge node IDs. The projection still consumes only the retained report and emits fixed keys, enums and bounded counts.

## Rollout and rollback

Independent review must inspect the prospective bodies and tests. Root then admits their hashes in the approved checker through an ordinary commit, with prior hashes retained. Only afterward may root activate workflow bodies, immutable consumer pins and `tests-activation.patch`. Root must rerun tests against the actual activated workflow plus authority tests and required gates. Private GREEN does not authorize a commit, push, merge, deadline change, reviewer replacement or acceptance bypass.

Rollback restores the previous admitted observer bodies and matching approved pins. The first end-to-end milestone remains one new exact-head hosted observation. These fields may explain incomplete terminal execution or retained coverage attribution messages; they do not establish hosted Pylint causality, physical stdout line origins or valid per-source coverage. Confidence is high in locally tested projection semantics and remains limited for hosted causality until that observation exists.

## Actual activation proof on 14 October 2026

Checker-only commit `56ac770d024e48c1444e09640ca5c92a7a524ed1`, blob `0bfb44b9edfcb196b002b998e2d20ab29866dd2c`, passed ordinary hooks before workflow or consumer-pin activation. Both consumers now use that immutable pair. The authenticated owner wrapper SHA-256 is `423a0770e98674b9f57f9187f6729bb3b4a079e7992bd729e5a82fc2de8b008b`.

The actual activated workflow passes 595 observer, host authority and shell projection checks in `diag2/activated-focus.log`. Global types have zero errors/warnings, global lint scores10/10, workflow YAML and strict OpenSpec pass, staged requirements evidence passes, and all7module filesystem/version/signature checks pass. Full and SMART each subsequently passed304hostproofs and6110supplier tests, with71conditional skips,95subtests and5existingwarnings. Their logs are diag2/full-final.log and diag2/smart-final.log. Separate read-only security verification returned fixed for all3supplied findings, with no hostile-code or hosted-acceptance claim. The failed nonexistent Hatch alias in `diag2/requirements.log` was a command lookup error, not requirement failure; the correct repository adapter passed in `diag2/requirements-staged.json`.

Three independent activation reviewers found no implementation, authority or privacy issue. One new blank-line whitespace nit was corrected; exact observer hashes and whole parsed workflow equality outside their bodies were rechecked afterward. Earlier reviewer A also corrected the baseline/prospective filename in this document. These changes do not alter execution.

The retained authority test log named `authority-final-body-red.log` is actually a successful admission probe and is not RED evidence. The original authority-red run has three genuine admission rejections, plus24cases that halted at fixture setup before mutation. Exact immutable5588 checker comparison later rejects all3final-body combinations in `authority-5588-baseline-final-bodies-red.log`; the new checker passes27admission/mutation cases in `authority-final-body-green.log`. No mutation rejection is inferred from setup failure.

Hosted Linux root cause and exact-head acceptance remain unproven. The signed reviewer, deadlines, all execution and gates are unchanged.
