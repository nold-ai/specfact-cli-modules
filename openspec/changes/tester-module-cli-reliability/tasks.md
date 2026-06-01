# Tasks: tester-module-cli-reliability

## 1. Readiness and source tracking

- [x] 1.1 Confirm tester bugs are mapped to module ownership and record the decision in `TDD_EVIDENCE.md`.
- [x] 1.2 Confirm GitHub Feature `#305`, User Story `#306`, and paired core story `nold-ai/specfact-cli#594` exist with source links and labels.
- [x] 1.3 Validate the OpenSpec change with `openspec validate tester-module-cli-reliability --strict`.

## 2. Spec-first and failing evidence

- [x] 2.1 Add spec deltas for module CLI error contract, command overview artifacts, docs/prompt command validation, backlog delta, and tool dependency probing.
- [x] 2.2 Add failing tests for project sync bridge help text, code import legacy ordering, backlog auth missing subcommand, backlog delta config/flags, generated command overview freshness, and prompt stale-command detection.
- [x] 2.3 Run targeted tests before production edits and record failing evidence in `TDD_EVIDENCE.md`.

## 3. Module command contract fixes

- [x] 3.1 Fix `project regenerate` to produce typed diagnostics when bundle data is missing or null.
- [x] 3.2 Replace flat `specfact sync bridge` help/docs/prompts with canonical `specfact project sync bridge`.
- [x] 3.3 Make `code import` help and errors unambiguous for supported option ordering and legacy migration guidance.
- [x] 3.4 Make direct module command groups inherit shared help plus missing-subcommand and missing-parameter guidance, including `backlog auth`.
- [x] 3.5 Make `backlog delta status` resolve documented config defaults consistently with `daily` and expose required repo/project inputs.

## 4. Module command overview and validation

- [x] 4.1 Add deterministic module command overview generation for `llms.txt`, Markdown, and JSON artifacts.
- [x] 4.2 Link the module command overview from `README.md`.
- [x] 4.3 Remove legacy flat mount whitelists from docs/prompt validators and add generated-contract freshness validation.
- [x] 4.4 Repair stale module docs, prompts, templates, and guidance strings.

## 5. Runtime tool diagnostics and gates

- [x] 5.1 Adopt active-context semgrep/tool probing for module diagnostics.
- [x] 5.2 Add CI/pre-commit freshness checks for generated module command artifacts.
- [x] 5.3 Coordinate with core package-manager runtime matrix for installed module smoke coverage.

## 6. Passing evidence and quality gates

- [x] 6.1 Re-run targeted tests and record passing evidence in `TDD_EVIDENCE.md`.
- [x] 6.2 Run required quality gates for touched scope: format, type-check, lint, YAML lint, contract-test, smart-test or targeted equivalent.
- [x] 6.3 Run SpecFact code review and resolve findings or document explicit exceptions.
