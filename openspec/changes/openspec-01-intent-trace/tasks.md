# Tasks: OpenSpec and Spec Kit Import Runtime for Requirement Evidence

## TDD / SDD order (enforced)

Spec deltas first, failing tests second, production code third. Record
evidence in `TDD_EVIDENCE.md`.

---

## 1. Branch and dependency guardrails

- [ ] 1.1 Create worktree branch `feature/openspec-01-intent-trace` from `dev`.
- [ ] 1.2 Verify the paired core change (nold-ai/specfact-cli#350) import normalizers and gate helpers are merged, or coordinate parallel implementation with explicit core version pinning.
- [ ] 1.3 Re-run change validation for the rescoped proposal and refresh `CHANGE_VALIDATION.md`.

## 2. Spec-first and test-first preparation

- [ ] 2.1 Finalize the `requirements-module` spec delta and cross-check scenario completeness.
- [ ] 2.2 Add tests: `--from-openspec`/`--from-speckit` import against fixtures, auto-detection success and clear-error cases, gate findings surfaced in `validate` with non-zero exit, and upstream directories untouched after runs.
- [ ] 2.2b Add tests: omitted `--profile` resolves the effective profile from layered configuration instead of a hardcoded `startup` default; explicit `--profile` overrides; core's four supported aliases and `unsupported-profile-field` advisories pass through unchanged.
- [ ] 2.2c Add tests: core `unsupported-source-schema` diagnostics surface unchanged and produce no partial sidecar persistence.
- [ ] 2.3 Run targeted tests, capture failing-first output in `TDD_EVIDENCE.md`.

## 3. Implementation

- [x] 3.1 Extend `packages/specfact-requirements/.../commands.py` import command with `--from-openspec [PATH]` and `--from-speckit [PATH]` options.
- [x] 3.2 Extend `runtime.py` with thin delegation to the new core normalizers via the existing `_load_requirements_module` pattern, including `RequirementsCoreUnavailableError` messaging.
- [x] 3.3 Surface gate findings in `validate` output and gate-relevant counts in `list`/`coverage`.
- [x] 3.3b Change the `validate` command's profile default from hardcoded `startup` to core layered-config resolution when the flag is omitted, and render core required-field advisories unchanged (delegated to the core helper; no config parsing or metadata enrichment in the module).
- [x] 3.3c Surface core `unsupported-source-schema` results without fallback parsing or partial persistence.
- [ ] 3.4 Contract decorators (`@beartype`, `@require`, `@ensure`) on all new public APIs.

## 4. Validation and documentation

- [ ] 4.1 Re-run tests and quality gates until green; record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Update module docs and command overview with import-first examples and gate categories.
- [ ] 4.3 Run `openspec validate openspec-01-intent-trace --strict` and resolve all issues.

## 5. Delivery

- [ ] 5.1 Open PR to `dev` with spec/test/code/docs evidence.
- [ ] 5.2 Sync GitHub issue #168 title/body with the rescoped proposal.
