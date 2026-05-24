## 1. GitHub readiness and OpenSpec setup

- [x] 1.1 Create OpenSpec change `code-review-13-cleanup-forecast-agent-handoff`.
- [x] 1.2 Create GitHub issue [#297](https://github.com/nold-ai/specfact-cli-modules/issues/297), link it under Feature [#275](https://github.com/nold-ai/specfact-cli-modules/issues/275), and label it with `enhancement`, `codebase`, `openspec`, and `change-proposal`.
- [x] 1.3 Confirm issue project assignment, open/Todo state, parent linkage, blocked-by relationship, source tracking, and absence of implementation concurrency.
- [x] 1.4 Add `openspec/CHANGE_ORDER.md` row as order 06, blocked by [#286](https://github.com/nold-ai/specfact-cli-modules/issues/286).
- [x] 1.5 Validate the OpenSpec change with `openspec validate code-review-13-cleanup-forecast-agent-handoff --strict`.

## 2. Spec-first failing tests

- [x] 2.1 Add model tests for `cleanup_forecast`, `signal_trace`, `preserve_reasons`, and `remediation_packet` compatibility.
- [x] 2.2 Add forecast tests for reviewed LOC, estimated deletion ranges, guidance-kind totals, and AI-bloat index weights.
- [x] 2.3 Add preserve-detection tests for icontract, public API exports, Protocol/ABC members, Typer/Click callbacks, compatibility shims, explicit markers, and mutation load-bearing evidence.
- [x] 2.4 Add CLI tests for `--preview-fixes`, `--with-mutation`, and invalid combinations with non-simplify focus.
- [x] 2.5 Add command-contract and docs parity tests for new flags and report fields.
- [x] 2.6 Record failing-before evidence in `TDD_EVIDENCE.md`.

## 3. Review model and forecast implementation

- [x] 3.1 Extend `ReviewReport` with additive `cleanup_forecast` and schema version derivation.
- [x] 3.2 Extend `ReviewFinding` with additive evidence and handoff fields.
- [x] 3.3 Compute reviewed LOC and forecast metrics from the resolved review file set.
- [x] 3.4 Keep scoring and merge-quality verdict behavior unchanged outside simplify-specific enforcement.

## 4. Preview, preserve, and mutation proof

- [x] 4.1 Implement non-mutating patch forecast support for existing safe-mechanical simplification fixers.
- [x] 4.2 Implement preserve-reason detection before automatic cleanup eligibility is calculated.
- [x] 4.3 Add opt-in mutation proof scaffolding for simplify candidates, treating tool absence or timeout as inconclusive.
- [x] 4.4 Ensure `--fix` still mutates only deterministic safe-mechanical findings and records action evidence.

## 5. AI IDE handoff and docs

- [x] 5.1 Emit remediation packets suitable for Claude, Codex, Cursor, Copilot, or headless agents.
- [x] 5.2 Update `--instructions` and packaged skill guidance to prioritize cleanup forecast and remediation packets.
- [x] 5.3 Update modules docs and AI bloat quickstart for the new JSON-first cleanup workflow.
- [x] 5.4 Coordinate with the paired core docs change before final wording is published.

## 6. Packaging, signatures, and verification

- [x] 6.1 Bump affected module versions when packaged resources change.
- [x] 6.2 Refresh registry metadata and module manifest integrity/signatures.
- [x] 6.3 Re-run targeted tests and record passing evidence in `TDD_EVIDENCE.md`.
- [x] 6.4 Run required gates for touched scope: `hatch run format`, `hatch run type-check`, `hatch run lint`, `hatch run yaml-lint`, `hatch run check-bundle-imports`, `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump`, `hatch run contract-test`, relevant `hatch run smart-test`, relevant `hatch run test`, and `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed`.
