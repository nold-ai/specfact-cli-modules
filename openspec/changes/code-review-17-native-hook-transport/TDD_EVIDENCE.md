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
