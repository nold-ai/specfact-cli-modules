# Codebase Repro async analysis

Verification on 23 November 2026 used Python 3.12.13 and the exact analyzer
source from the verified core #799 merge `e90a4b57`.

- Before the fix on modules `2155370e`, five Repro cases failed. The
  explicit option was unavailable and legacy configuration still selected
  Semgrep. The unchanged no-request control passed.
- After the fix, all six Repro cases and 13 existing Codebase integration
  and unit cases passed. The suite invokes the actual Codebase command app and
  real core subprocess. It verifies structured results and exit codes,
  migration and missing-scanner diagnostics, and unchanged source.
- Signed external module acceptance remains pending under #516. This
  implements the Codebase Repro milestone of #523. The Project consumers
  and other retirement work remain open.

The first hosted run exposed six inherited host-fixture failures before the
Codebase tests could run. Four existing signed-install layout cases also
failed locally against the paired core's protected release cutoff. The
fixture-only follow-up reuses the reviewed repairs from #524, restores the
exact public-key and released-verifier inputs, and retains the invalid
signature and substituted archive rejection cases. Production workflows,
verification logic, and policies are unchanged.
