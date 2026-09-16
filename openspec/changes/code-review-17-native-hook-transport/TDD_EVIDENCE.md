# Native hook transport evidence

Date: 2026-09-16 (Europe/Berlin). Story473 / PR478. This change transports unchanged developer hooks; it is not customer acceptance or protected PR range evidence.

## RED

Specifications preceded tests. Before production edits, `hatch run python -m pytest tests/unit/test_native_hook_transport.py -q` produced **13 failed** in 1.26s: the transport implementation and opt-in workflow were absent. Actual complete output is retained in `RED.txt`.

## Component GREEN

The same focused suite, expanded to actual child-process exit handling, source mutation, outer identity and report receipts, passes **18 tests**. Native runtime preparation is explicit through `code review runtime prepare --json`; its local build identity and receipt digest are required before unchanged hooks execute.

Strict OpenSpec validation passes. Ruff, repository typing and lint pass. Contract suite: 28 passes; existing lark deprecation warnings remain unrelated. Signature verification uses the paired core public key.

## Remaining acceptance

Final local manual review: `hatch run specfact code review run --enforcement changed --bug-hunt --json --out /private/tmp/specfact-478-transport-review.json scripts/native_hook_transport.py tests/unit/test_native_hook_transport.py` returned PASS with zero findings. Independent review found the mutable core checkout; it is now pinned to reviewed commit `2f9567e28e98b082801b13ff02e863933ce2f0f2`, and re-review found no remaining findings. Requirements planned evidence passes. Full suite: 2,715 passed, one existing Linux `/proc` skip on macOS, two existing lark warnings, 174.45 seconds. Smart suite: the same 2,715 passed, one existing skip and two existing warnings, 166.47 seconds.

The verbatim RED transcript preserves pytest's trailing spaces; no diagnostic content was normalized.

Normal signed commit hooks and the native exact-tree workflow receipt are still required. No dispatch has occurred. The installed coverage delivery remains a separate uncommitted staged snapshot. Local macOS/Docker results do not replace native candidate or public signed release acceptance.

## Native preparation follow-up

The first real native run [35067390728](https://github.com/nold-ai/specfact-cli-modules/actions/runs/35067390728) applied the exact requested staged tree and verified installation of official signed 0.50.0, then correctly failed before hooks: `project_environment_ambiguous:default,hatch-test`. Direct interpreter invocation omitted the genuine Hatch activation used by unchanged hooks. The actual failure log is retained in `NATIVE_PREPARATION_FAILURE.txt`; the workflow artifact retains the complete receipt and raw output.

A new scenario preceded the focused regression, which failed before the fix (actual output `HATCH_RED.txt`). Runtime preparation now uses `hatch run python -m specfact_cli.cli code review runtime prepare --json`; the adapter independently verifies native activation. Raw CLI output remains `runtime.stdout`; exactly one typed descriptor with authority, identity, descriptor path and project metadata becomes `runtime.json`. Twenty-five focused tests pass, including incomplete, wrong-type and ambiguous descriptor rejection.

## Workspace preparation parity

A local clean-environment `hatch run python -m specfact_cli.cli code review runtime inspect --json` lacked the workspace code command when only `SPECFACT_MODULES_REPO` was present (actual output `WORKSPACE_DISCOVERY_FAILURE.txt`). This establishes missing workspace selection; it is not a claim that the in-progress native run loaded a particular old implementation. The unchanged pre-commit helper explicitly augments `SPECFACT_CLI_MODULES_REPO`, `SPECFACT_MODULES_ROOTS` and owned package `src` paths in `PYTHONPATH`. Preparation now mirrors exactly that selection without inheriting host overlays. The spec preceded the failing fixture `WORKSPACE_RED.txt`. The receipt retains the actual runtime workspace paths separately from the installed signed baseline inventory.


## Explicit repository analyzer alignment transport

The second native run35068293754 found a real project/sealed Pylint-isort conflict, retained in the portable-runtime change evidence. This transport permits the explicitly approved repository development pins, their compatibility regression, and the three supporting native/RED artifacts. A byte comparison against the immutable base permits only the two reviewed Pylint/basedpyright replacements in pyproject.toml; any other edit fails before preparation. `PINS_RED.txt` retains the two failing-before cases. Combined transport coverage now passes 28 cases. No external repository files or resolver constraints are changed.

## Final inventory and source preservation

`INVENTORY_RED.txt` records the failing receipt assertion before a fresh `pip freeze --all` from the synchronized hook interpreter was added immediately before hooks. Its output and digest are separate from the initial installation inventory.

A real successful child creating `new_module.py` exposed an unchanged-index gap: the untracked-source regression failed while the tracked-mutation case passed (`UNTRACKED_RED.txt`). The transport now also rejects non-ignored untracked files after hooks; ordinary ignored caches/reports remain permitted.

Final follow-up validation: 29 focused tests passed in 4.50 seconds; typing, Pylint, YAML, strict OpenSpec and planned Requirements passed. Fresh bug-hunt report `/private/tmp/specfact-478-transport-final-review.json` returned PASS_WITH_ADVISORY with one informational `ai-bloat.loc-vs-complexity` finding on `test_receipt_binds_actual_outer_identity_and_report` (40 lines), zero warnings and zero blockers. Review of that suggestion retains the expanded test: its real child setup and independent outer identity, runtime inventory, staged tree and report digest assertions each establish a distinct receipt invariant; collapsing them would obscure failure localization. This is an explicit test readability judgment, not an execution or correctness exemption. Native exact-snapshot acceptance remains required.
