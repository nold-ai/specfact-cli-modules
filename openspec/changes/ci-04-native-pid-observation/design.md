# Native PID observation design

## Decision and evidence

The selected design reuses `tests/native/proof_macos_native_broker_wait.py` as the policy owner. Its public `wait_worker_pid(temporary: Path) -> int` hides marker lookup, framing, bounded I/O and the fixed deadline. A private `_parse_pid_record(record: bytes) -> int | None` distinguishes pending from ready. Invalid publication raises `ValueError`; timeout raises `AssertionError`; ordinary `OSError` propagates. These are the root-selected engineering decisions within the owner's delegated maintenance scope, not a new native acceptance policy.

`_hold_worker` calls the helper and preserves its JSON, packed WAIT payload, `WAIT_SENT`, receive and unexpected-completion assertion. `tests/unit/specfact_code_review/run/test_native_execution.py` imports `wait_worker_pid as _worker_pid`, removes the duplicate loop and preserves all three callers. `scripts/native_release/boundary.py` stays unchanged.

The source producer uses `open(... O_CREAT | O_EXCL ...)` followed by a separate `write`, with a 32-byte formatting buffer. Existence therefore does not establish publication completeness. The format permits at most 31 bytes including the final newline. A bounded reader consumes at most 32 bytes to detect oversize.

## Record and deadline contract

Absent marker, empty bytes and newline-free ASCII digits of at most 31 bytes are pending. A ready record is ASCII digits plus exactly one final newline, at most 31 bytes total, with value greater than zero. Signs, whitespace, empty lines, non-ASCII bytes, multiple lines, trailing bytes, complete zero and oversize records fail immediately. No `.strip()` or permissive numeric conversion may widen the grammar.

Set one monotonic deadline five seconds after entry. Retry pending publication with sleeps of at most 10 milliseconds, capped by remaining time. Never renew the deadline. Recheck it after observation before accepting a PID. Every observation opens a fresh descriptor read-only with `O_NOFOLLOW | O_NONBLOCK`, checks `fstat` for a regular file, reads at most 32 bytes and closes in `finally`. Only `FileNotFoundError` from opening is pending. Symlinks, directories and FIFOs fail promptly without blocking; all other ordinary I/O errors propagate unchanged. This bounds observation in a private directory and does not claim atomic snapshots against hostile writers.

## Alternatives

Reusing the existing existence/read loops does not distinguish pending publication. The selected minimal adaptation centralizes one policy and keeps standalone proof invocation working. A separate support module would add import-path obligations without simplifying either consumer. An atomic producer rewrite would change signed native assets and publication protocol without a necessary benefit for this repair. No configurable polling abstraction, callback API, wrapper class or new dependency is justified.

## Verification and preservation

Portable tests call the genuine old `_hold_worker` and sibling `_worker_pid` interfaces. Event-gated threads exclusively create real 0600 marker files, wait until the reader's first pending sleep, then publish the actual process PID and newline. Old readers fail before that seam on the empty record. Partial numeric publication is separately checked. Every writer is released and joined in `finally`.

A real socketpair peer checks the exact WAIT bytes, sends a structured reply and allows the existing unexpected-completion assertion to terminate the controller path. JSON and `WAIT_SENT` remain exact. Controlled clocks are limited to portable deadline tests. No marker PID is signaled. Invalid observation must precede PID output and WAIT. Ordinary pytest discovery already includes the portable owner; selectors and configuration remain unchanged.

The preservation checker binds 2812 protected tracked paths, ten compatibility inputs, the frozen workflow and the original boundary fixture plus three tests. The four historical proof files and `tests/unit/test_macos_native_broker_wait.py` stay unchanged. Imports must not run physical tests. Guarded native execution cases remain skipped unless their explicit required inputs are actually supplied later.

Risks are premature numeric-prefix acceptance (mitigated by newline framing), deadline renewal or late success (one deadline with a final check), and blocked or redirected paths (nonblocking/no-follow open and regular-file admission). Confidence is high in the bounded contract; physical native delivery remains unproven. New producers, hostile writers or additional callers would require a fresh scope decision.


## Implementation reconciliation on 20 October 2026

The two-helper interface, record grammar, deadline and error disposition remain as selected. Descriptor closure precedes pure record parsing. Reading is conditional on regular-file admission, so directories and FIFOs are never read.

Repository-context raw contract warnings increased from 50 to 51 because the new public helper is a test support function. The unchanged canonical reviewer classifies these missing-decorator test warnings as known noise and excludes configured test roots from CrossHair. Genuine policy execution yields zero governed contract findings for both baseline and final source. Root rejected the provisional icontract dependency after this policy was verified. The selected standard-library-only design and standalone invocation remain intact. No test, dependency, review policy or frozen acceptance input was changed.

The final proof retains 59 passing frozen cases and 182 passing nearby cases with 12 guarded physical skips. Existing whole-file warnings remain identified against the baseline. Native worker checks and runtime assertions do not replace physical native acceptance or root's remaining repository gates.
