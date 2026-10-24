# Evidence status

Proposal prepared and diagnostic-only implementation approved on 2026-10-25, Europe/Berlin. Signed delivery and Linux repair are not established by local test evidence.

The investigation uses PR #524 head `59611f358572aaa3c383c2d2fffcf82fb57ff36c` and base `430e3ccbf9fbd6a6177b033662a76235a8bd6cc8`. Existing milestone evidence remains with change 17 and is not reclassified as evidence for this proposal.

Requirements mappings now contain 126 exact executable selectors across four requirements and ten specification scenarios. Independent mapping review accepted all selectors against actual collection and the repository lifecycle validator before production edits. A diagnostic replay is never a replacement for the original required review decision.

## Proposal verification

- `openspec validate code-review-linux-analyzer-diagnostics --strict --json --no-interactive` passed with no issues using OpenSpec 1.13.2.
- A local reproducible planning audit at `/private/tmp/513-check-diagnostic-proposal.py` checked all four requirements and ten scenarios against ten inspection mappings. It also verified unchanged tracked files and the exact subject HEAD. This is artifact inspection, not executed acceptance.
- `git diff --check` passed. The original governance archive worktree was left untouched. No runtime, workflow, test, dependency, module, registry, index, commit, or push change was made by this investigation.
- Independent read-only grounding review caught and corrected wording that could imply the hosted Pylint rows were proven fixed. Their actual lifecycle remains unresolved.

## Failing-first evidence

Actual workflow projection snippets ran with synthetic private reports and real temporary Git repositories. No Bash or capsule launch occurs in the new fixture tests. The final source-bound RED command was:

```console
.venv/bin/python -m pytest tests/unit/test_capsule_analyzer_diagnostics.py -o addopts= -q -o junit_family=legacy --junitxml=/private/tmp/513-diagnostics-final-red.xml
```

Result: 50 failed, 76 passed, zero skipped, zero errors. Every failure is a missing intended diagnostic field/classification, including `None` versus recorded `base`/`head`, absent lifecycle/strict Boolean fields, and unclassified known pytest producer wrappers. The 76 passing cases are existing privacy, bounds, classification, and authority controls. Do not claim all 126 were RED.

The unchanged workflow SHA-256 was `f048789a790ffa79d33075be48aa3451dac2478c5b816099ee6766fef2384137`. Final RED JUnit SHA-256 was `3366318437d907027f556cceb26370ab08e59e08286e3b640ecdc1134aecfa64`. Mapping digest was `sha256:fa140be021ab83cfb98f7daf1d862b2733a1ec00c680dd723adbdb9b446f1bf0`. The local source manifest, plan, and independent acceptance are under `.audit/513-diagnostics-{red-source,plan,mapping-acceptance}.json`.

Earlier genuine 50-failure runs are retained under `/private/tmp/513-diagnostics-red.*` and `/private/tmp/513-diagnostics-valid-selectors-red.*`. Generated selector IDs were shortened to satisfy the existing validator, and the established `specfact.selector` test property was added before the final run. Neither correction changed test predicates or production behavior. These preliminary runs are not substituted for the final source-bound proof.

Existing exact-output expectations are updated only for newly visible structured-report fields. Every existing scenario/assertion remains enabled. The required gates prevent committing intentionally failing tests, so immutable local source/JUnit records preserve RED-before-production order instead of a failing commit.

## Passing-after evidence

The same 126 exact selectors passed after the inline projection change, with zero skips or errors. Root independently ran:

```console
.venv/bin/python -m pytest tests/unit/test_capsule_analyzer_diagnostics.py -o addopts= -q -o junit_family=legacy --junitxml=/private/tmp/513-diagnostics-final-green.xml
```

Result: 126 passed, one warning, in 7.68 seconds. The warning reports sandbox denial of a pytest cache write, not a skipped or failed case. Workflow SHA-256 was `70d0638343207373c4d4ba5e38b2ae149a34a907e63996c7597b8ead529448cd`. The focused-plus-existing projection suites also passed together: 350 passed, zero skips or failures, one cache-write warning. Three existing unknown-code expectations now require the explicit `unclassified` value; the exact-output helper now expects structured provenance. No existing scenario or assertion was removed.

The local boundary verifier at `/private/tmp/513-verify-diagnostics-boundary.py` passed. Exactly four existing inline Python snippets changed. All other workflow shell commands, review capture/exit handling, job configuration, prerequisites, pins, budgets, artifact paths, and YAML values match the original head. Module/runtime code and signed payloads are unchanged.

The new test module's redundant docstring was removed after independent comment review. Test predicates and selectors did not change. The first combined run exposed six stale legacy unknown-code expectations, which were updated to the approved explicit unclassified output before the passing combined run. Its failed output remains `/private/tmp/513-diagnostics-green.txt` only in earlier tool history because the final combined run reused that path; final and preliminary RED records above remain immutable.

Requirements reconciliation must preserve the honest mixed RED record of 50 regressions and 76 passing controls. Use the existing ledger-supported reconciliation contract, retain both source-bound XML records, and never claim that all 126 tests failed before the change. Local proof cannot grant protected CI authority.

## Local quality and review gates

All ten local gate commands completed with exit 0: format, type-check, lint, YAML lint, bundle imports, strict signatures/version checks, contracts, SMART tests, full tests, and the complete staged pre-commit pipeline. Strict signatures verified all seven unchanged module manifests. Contracts passed 28 tests. SMART and full tests each passed 5,851 tests with 77 existing opt-in skips, five baseline warnings, and 95 passing subtests. The full command also passed all 30 host deferral proofs. No signed payload, dependency, registry row, generated artifact, or runtime source changed.

The capsule component remains explicitly DEFERRED under the previously approved ARM64 Darwin exception. It is not PASS and does not waive the mandatory exact-head Linux matrix or independent signed review. Gate logs/status are under `.audit/513-diagnostics-gate-*`.

CodeRabbit CLI 0.9.1 completed review of all 12 selected files. Its first review raised one minor missing-GREEN-evidence finding; the actual source-bound passing results above resolve it. The final review completed with zero findings. Independent mapping/shape and comment review also completed; no code-quality suppression was added.

The actual Requirements consumer reconciled all 126 passing selectors against mapping digest `sha256:fa140be021ab83cfb98f7daf1d862b2733a1ec00c680dd723adbdb9b446f1bf0`, using the existing explicit mixed-history ledger contract. Its result is `verified`, `passing-after-legacy-tdd-ledger`, with no findings. This describes local fixture evidence only. The ledger preserves the 50-failure/76-control RED record and both XML digests. The final source binding is `.audit/513-diagnostics-tested-source.json`; no protected authority is inferred.

## Hosted verification boundary

The next signed head must run the unchanged required Linux matrix and independent signed reviewer. Record actual job outcomes and bounded class/side/lifecycle observations in the PR delivery record. Runtime, admission, dependency, budget, enforcement, or acceptance repairs require owner approval after those observations. This implementation does not authorize merge or OpenSpec archival.
