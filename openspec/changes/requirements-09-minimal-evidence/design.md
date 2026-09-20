## Decisions

1. MEB means current observed behavior and relevant validation context. It does not mean complete requirements coverage, absence of defects, or historical TDD compliance.
2. Keep development order: specification -> useful regression tests -> observe the relevant failure where feasible -> implementation -> passing tests. No test-only Git commit or hosted RED run is required. An impractical reproduction needs a brief reason and alternative negative control; setup/import failures do not prove sensitivity to the bug.
3. Reuse normal CI test outputs once per candidate/environment. Bind the receipt to the tested commit/tree, runner/environment identity, selection or command, counts, and artifact references. Keep detailed JUnit/logs in CI artifacts (14 days); retain release integrity records with releases. A PR validation summary normally needs five to ten authored lines, without a line-count gate.
4. A required selected acceptance case must be collected exactly once and pass. Failure/error/skip/missing/duplicate is not proof. Ordinary full-suite skips remain separately visible under existing suite policy. Missing or malformed required output and wrong revision remain non-passing.
5. The trusted orchestration layer verifies candidate identity and required job/result provenance; project-controlled metadata cannot authorize itself. Preserve existing source/module authentication, least privilege, parser/selector bounds, signing, security, contracts, tests, and independent review. Do not run PR code with signing or repository-write credentials.
6. Build one current report and let Code Review consume it as context without verdict fusion. On dev-to-main, validate the actual promotion candidate; do not reconstruct source-PR history or reuse legacy promotion capsules.
7. Scenario associations are optional for ordinary test context. If supplied, validate them exactly. Without them, requirement coverage is not evaluated; do not report complete intent/coverage. Explicit stronger traceability/chronology policy stays opt-in and retains its stricter failure semantics.
8. Existing preflight/seal/checkpoint work is an optional product capability. Its guarantees remain meaningful inside that explicit mode. It is not a prerequisite to ship C14/C15, native execution, generic skills, or lean generated instructions.
9. R09 replaces the unimplemented R07 correction rather than duplicating its workflow. R08 remains abandoned. No new capsule, seal service, checkpoint tag protocol, AST/import closure inference, or proof-specific caching framework.

## Ownership and interfaces

Modules #481 owns current reconciliation, v3 report claims, legacy compatibility, and review-context consumption. Core owns revision selection, safe execution/original job outputs, artifact collection, trusted enforcement and platform integration. The same change ID is paired across repositories; each story owns only its repository's implementation.

Modules add `current` as the default reconciliation stage; explicit legacy `red`/`final` remains supported. V3 separates `current_execution` and `red_green_chronology`; current-only operation reports chronology not evaluated. V2 is read through the explicit legacy path, never inferred from missing v3 fields. No new general profile framework is required for this rollout.

## Delivery boundary

Core #740 owns execution, trusted enforcement and coordinated organization policy. This story owns module contracts, command/help documentation, compatibility and signed publication. A module receipt carries supplied source/environment context without granting it CI authority. Validate the supported existing core interface before release. No new profile framework, service, approval protocol or runtime executor is introduced.
