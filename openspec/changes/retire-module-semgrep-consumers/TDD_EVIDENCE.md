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

## Native CI after merging the modules baseline

The signed update incorporates modules `dev` at `9f0de196`. The independent
review stops at CrossHair before it runs candidate tests. A separate local run
using the native candidate environment's released core 0.55.4 produced four
failures because that wheel predates the built-in analyzer. The paired-core
workflow regression also failed against the original workflow before the
checkout was added.

The updated workflow resolves the exact same-repository companion commit and
uses it for candidate tests only. It still installs and verifies the separate
signed controller first. The Repro, workflow, and independent-review regression
set passed 52 cases locally. The 42 focused Repro tests passed with branch
coverage of 81.53% for the command and 83.94% for the checker.
