# Individual review warning decisions

These decisions apply to the retained findings at head `66e945f5` and the bounded test-only repair. Producer rules, severity, deadlines and blocking review remain unchanged. Every exception below preserves an existing observable contract; none suppresses a rule or grants acceptance. The original first 200 projection omits exact IDs for some tools; local exact public producers supply the noted rule evidence. Unobserved findings remain open.

| Finding | Decision and evidence |
| --- | --- |
| New observation fixture CC38, nesting17, LOC114 | Fixed by focused variant builders and tables; all 35 payloads and 301 tests preserved. Exact producer now returns no findings. |
| Authority fixture nesting7 | Fixed by one match over the same mutation names/statements; all 16 payloads/outcomes and 190 host proofs preserved. |
| 26 reproduced test Pylint diagnostics | Fixed safe static/duplicate imports, two empty-list comparisons and two redundant locals. Source snapshots and resolved.json retain exact IDs/coordinates. No new diagnostic identities. |
| native_worker.py exact-int checks, C0123 | Retained. Bool is an int subclass; isinstance would widen untrusted reply admission. The exact-int regression controls remain required. |
| check_macos_boundary_ci_receipts.py exact-int counters, C0123 | Retained for the same boundary requirement. Boolean or numeric coercion cannot establish receipt counts. |
| target_crosshair test exact Python Boolean, C0123 | Retained. The test verifies a concrete bool from the compatibility predicate, not an arbitrary truthy/int-subclass value. |
| _WorkflowLoader inherited SafeLoader ancestry, R0901 | Retained. The extra ancestry comes from the existing safe YAML loader, not a new custom hierarchy. Duplicate-key and literal-on parsing controls remain required; switching to an unsafe loader would change admission. |
| test_native_project_inventory transparent subprocess forwarding, W1510 | Retained. The wrapper passes caller options to the original run; forcing check=True or injecting duplicate check alongside **options changes the tested caller behavior. |
| CrossHair core_and_libs and main imports in test execution, C0415 | Retained at original indices 184/189. Fresh-process comparison shows core_and_libs changes proxy registry from 0 to 68; main imports it. Hoisting these imports moves registrations to test collection. The harmless builtinslib-only import was separately proved and lifted. |
| Runtime compatibility-context imports in target_crosshair.py, C0415 | Retained in the compatibility scopes. These are optional submodule accesses when the relevant context enters; module-level CrossHair core imports already exist, so absence of all module-level dependency is not the justification. Compatibility entry order and registration behavior remain unchanged. |
| native_worker.py JSON stdout, print-in-src | Retained. Stdout is the controller transport. The actual public Semgrep producer reproduces this rule at 938; replacing it with logging changes the protocol. |
| check_capsule_deferral.py rejection stderr, print-in-src | Retained. The exact producer reproduces this rule at 299; stderr plus exit 1 is its CLI failure contract. |
| Four target/reporter stream prints in CrossHair test, print-in-src | Retained. Exact producer reproduces four rules at current 548-551. The test deliberately emits target stdout/stderr and reporter stdout/stderr, then proves isolation and preservation of reporter diagnostics. |
| Eight unused private helper warnings from AST producer | Dismissed with concrete callers. native_worker_evidence helpers are imported/called by native_worker; native_project_runtime_fixtures helpers are imported/called by runtime/inventory tests; native_worker autouse fixture is registered by pytest and has unchanged AST from base. Caller paths/coordinates are retained in candidate-warning-triage/report.md. |
| Original public warning index 143 at test_native_worker.py:607 | Unresolved. No exact local finding reproduced at that coordinate; its original rule/message is not exposed. No speculative correction. |
| Undisplayed eighteenth error | Unresolved. First200projection exposes 17 of 18 reported errors. Local approximations do not identify the tail or prove it unchanged. |

Reproduced evidence is under /private/tmp/specfact-pr506-510-repair/candidate-warning-triage/, candidate-warning-cleanup/, candidate-fixture-complexity/ and candidate-authority-complexity/. The exact Semgrep six-rule reproduction is candidate-warning-exceptions/semgrep-correct-bundle.json. The initial wrong bundle-root lookup error is retained separately and is not scan evidence. Final independent review and hosted acceptance still apply.
