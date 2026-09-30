# Native XPC boundary experiment — 2026-10-01 Europe/Berlin

## Decision

**CANDIDATE_REJECTED.** App Sandbox plus application-scoped XPC and process-group
cancellation did not contain detached descendants. This is a measured failure of
this candidate, not a general impossibility claim about native macOS.

The checked-in harness is `scripts/macos_execution_boundary/`. Run it with a fresh
output directory and `--diagnose`; see its README. Production selection and
`production_eligible=false` remain unchanged. No GHCR publication occurred.

## Native validation

Physical Mac17,9, macOS 27.0.1 (26A434), ARM64; Apple Command Line Tools/SDK 27.0.
Client, XPC service, fixed C worker and independent libproc observer were compiled
with ARM64, `-Wall -Wextra -Werror`. The service has App Sandbox entitlement and
the worker has sandbox inheritance. The trusted launcher/observer are outside
the worker sandbox. Bundles passed local ad-hoc signature verification; this is
not Developer ID/notarization or customer-distribution acceptance.

The final invocation was:

```sh
python3 scripts/macos_execution_boundary/run.py /private/tmp/specfact-xpc-native-03 --diagnose
```

All 18 cases established successful readiness before observation. Normal completion
and ordinary-child cancellation passed. Every detached lifecycle case failed:

| Creation method | Cancel | Timeout | Client SIGKILL | Service SIGKILL |
| --- | --- | --- | --- | --- |
| fork plus setsid | child survived | child survived | child survived | root and child survived |
| double fork | child survived | child survived | child survived | root and child survived |
| posix_spawn plus setsid | child survived | child survived | child survived | root and child survived |
| vfork/exec plus setsid | child survived | child survived | child survived | root and child survived |

Survival was measured beyond the five-second bound using independent process
birth identity and executable checks, with a host process census. Emergency
cleanup was recorded as failure, not successful containment. Every final case
cleanup audit was empty. Sources/profile/executable digests match the executed
receipt; raw receipts/logs remain under the local temporary output directory.

## Evidence corrections and limits

Independent review found readiness could accept an intermediate process, normal
completion could omit a receipt, and observer failures could look like process
exit. Regression tests now cover these cases. Native success receipts also needed
actual JSON booleans instead of boxed integer values; the final run includes that
correction. Final readiness requires the final child, corroborated session identity
for detachment, and successful fixture events. The observer detects ESRCH separately
from observation failure. These diagnostics are not atomic production ownership.

The candidate failed before the 100-repeat positive-admission threshold. Concurrent
runs, Python/pytest project workloads, full filesystem/network/IPC capability tests,
resource ceilings, complete runtime dependencies and signed distribution remain
unapproved. Repeating a known failing candidate 100 times would not satisfy admission.
No restricted subprocess policy or process-polling substitute was adopted.

Next architectural work requires a different no-admin descendant-ownership
mechanism, supported by evidence, before production integration. This experiment
does not supply that missing mechanism. #460 remains open; do not archive it.
