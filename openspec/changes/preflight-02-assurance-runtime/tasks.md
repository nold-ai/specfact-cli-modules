# Tasks: preflight-02-assurance-runtime

All tasks below are future implementation work. This planning change completes none of them and creates no `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-02-assurance-runtime` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify issue type, parent, labels, project `Todo`, assignee, blockers, and `In Progress` concurrency state; pause if another implementation session may own it.
- [ ] 1.3 Verify the released core `preflight-01-design-contract-core` interfaces and all upstream input contracts against current repository reality.

## 2. Specification and failing-first evidence

- [ ] 2.1 Finalize CLI, validator registry, scope-role, component, per-input influence/no-impact including sealed-baseline and deterministic permitted-transition bindings, risk-disposition, Requirements-plan reference, verification-stage, persistence, renderer, and canonical workflow deltas without adding checkpoint execution, publication, or external adapters.
- [ ] 2.2 Add tests mapped to every runtime and workflow scenario, including invalid path roles, missing component targets, missing/ambiguous influence dispositions, no-impact dispositions missing exact baseline or predicate identity/version/configuration/closed change class/observable invariants, unsupported or arbitrary semantic transition predicates, uncovered/not-applicable risk rows, planned cases without selectors, planned-to-test-authored selector reconciliation, successor-seal lineage preservation, separate normalized validation-result persistence, explicit approval-write authorization and read-only no-write behavior, complete canonical artifact/source-binding atomicity, protected-history or independent-monotonic rollback anchoring, fresh-checkout transport, canonical-tip advance plus missing/stale/rollback/fork/ambiguity handling and older-ancestor fallback rejection, required shared-source/anchor unavailability as `UNKNOWN` rather than `NOT_APPLICABLE`, stale Requirements plans, unknown fail-closed behavior, approval invalidation, and renderer parity.
- [ ] 2.3 Run targeted tests before production edits, capture failing-first results, and create `TDD_EVIDENCE.md` with the red evidence.

## 3. Minimal unpublished runtime implementation

- [ ] 3.1 Implement the official module boundary and `specfact preflight run <change-id>` orchestration against the released core interfaces.
- [ ] 3.2 Implement the required versioned Python validators and deterministic readiness aggregation, reusing Requirements maturity/selector/plan contracts by identity and preserving the implementation-lineage origin across successor seals.
- [ ] 3.3 Implement human/JSON rendering, optional ignored local working copies, and explicitly authorized atomic persistence of the complete canonical artifact/source-binding set through the policy-authorized protected-history-anchored or independent-monotonic shared approval source.
- [ ] 3.4 Implement the canonical bundled workflow content and slash-command metadata without adding ECC, hatch3r, Codex-plugin, or other external adapter packages.

## 4. Passing evidence and quality gates

- [ ] 4.1 Re-run mapped tests and capture passing evidence after implementation.
- [ ] 4.2 Run required format, type, lint, YAML, bundle-import, contract, smart-test, test, and SpecFact code-review gates; resolve all findings.
- [ ] 4.3 Run module signature verification as a validation check, but do not publish or claim stable signed release in this change.
- [ ] 4.4 Run `openspec status --change preflight-02-assurance-runtime --json` and `openspec validate preflight-02-assurance-runtime --strict`.
- [ ] 4.5 Record only observed commands and results in `TDD_EVIDENCE.md` and implementation docs.

## 5. Delivery and post-merge cleanup

- [ ] 5.1 Prove the implementation remains unpublished and excludes external adapters, checkpoint execution, and final conformance.
- [ ] 5.2 Open the implementation PR to `dev` as the final pre-merge task, linking both repositories and all evidence.
- [ ] 5.3 After merge, run `openspec archive preflight-02-assurance-runtime`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
