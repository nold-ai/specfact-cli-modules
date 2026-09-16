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

## Separate sealed Semgrep diagnostic replay

Native run 35070709935 completed preparation but its unchanged review failed with one Semgrep structured error whose details were discarded by signed 0.50.0. The fallback finding location is not the error location. The new diagnostic replays staged Python inputs through the official sealed capsule and default signed rule packs. It preserves decoded stdout/stderr, return code, identities and hashes in separate artifacts, with diagnostic-only authority and no acceptance. Its fresh HOME/XDG directories and explicit metrics-off argument differ from the adapter's nested temporary home; this is not recovered original stdout.

Specification preceded four real assertion failures in SEMGREP_DIAGNOSTIC_RED.txt. A caller-context regression then recorded one failure/five passing in SEMGREP_CONTEXT_RED.txt; the completed helper rejects inherited Actions context rather than accidentally selecting publisher source. Final focused result: six passed, no skips/errors (0.24s); Ruff and targeted typing passed. Pylint 10.00 before the final context guard, with the same narrow private-controller-API rationale documented in the diagnostic source; final integrated checks follow. Independent read-only review found no helper defect and required sanitized call-site verification. Linux replay remains pending; no underlying Semgrep cause or successful hook result is claimed.

The transport invocation regression (`DIAGNOSTIC_EXIT_RED.txt`: two failing cases and one passing control) proves the separate diagnostic runs only after a genuine hook failure. A diagnostic child exit of zero or nine never replaces the original hook exit of seven; successful hooks do not invoke it. Combined focused coverage passed 37 cases. Trusted-controller diagnostic public functions retain explicit contracts; no project-side dependency is added.

Final diagnostic integration review (`/private/tmp/specfact-478-transport-diagnostic-final-review.json`) is PASS_WITH_ADVISORY with two informational length/readability suggestions and zero warnings/errors. Retain `capture_replay`'s explicit ordered namespace context, exact native argv, raw capture and receipt fields because they expose the isolation/provenance boundary for audit. Retain the real child setup in `test_receipt_binds_actual_outer_identity_and_report`; independent receipt assertions are now factored, correcting its introduced complexity warning. The manual invocation uses the same repository-owned bundle PYTHONPATH that the unchanged hook establishes, enabling CrossHair to import the trusted diagnostic controller. No runtime check or failure is waived.

## Opt-in basedpyright runtime-bound diagnostic (2026-09-16)

`BASEDPYRIGHT_DIAGNOSTIC_RED.txt` records ten failures before the default-off workflow input and diagnostic existed. `BASEDPYRIGHT_ACTIVATION_RED.txt` records a real detached-Hatch regression before replay used genuine `hatch run python` activation. The focused diagnostic/transport/Semgrep set then passed **53 tests in 6.97 seconds**; this includes real manager activation, environment credential exclusion and original hook exit preservation. The diagnostic reconstructs the staged snapshot, requires all four original review identities and an offline verified cache, then calls the unchanged signed nested worker with the actual portable argv. Raw replay streams and status are diagnostic-only, not recovered original output or passing review evidence. Native Linux replay and final exact-tree hook success remain outstanding. No tracing or signed worker changes were made.

Final diagnostic verification after review cleanup: **53 tests passed in 6.86 seconds**. Fresh SpecFact `--bug-hunt` review reports `PASS_WITH_ADVISORY`, score 115, with **zero errors or warnings**. Four informational `ai-bloat.loc-vs-complexity` suggestions concern explicit replay context/receipt construction and native fixture setup (including one pre-existing fixture). Those explicit fields and independent assertions are retained for auditability; no unsafe or duplicated behavior was reported. Public contracts and the flagged parameter-count/test-complexity warnings were corrected. The manually invoked controller review uses explicit workspace imports so CrossHair can import the reviewed helper.
