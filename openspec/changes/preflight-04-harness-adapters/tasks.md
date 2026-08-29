# Tasks: preflight-04-harness-adapters

All tasks below are future implementation and external integration work. This planning change completes none of them and creates no plugin, skill, pack, or `TDD_EVIDENCE.md`.

## 1. Dedicated session, worktree, and readiness

- [ ] 1.1 In a dedicated issue-linked session, create `feature/preflight-04-harness-adapters` from current `origin/dev` in a new modules worktree before any implementation edit.
- [ ] 1.2 Refresh hierarchy metadata and verify this issue is `Todo`, correctly parented/labeled/assigned, blocked by core #253, and not concurrently `In Progress`.
- [ ] 1.3 Verify the exact signed #434 module and preflight/implementation-check workflow identities, completed #251/#253 contracts, and current Codex/ECC/hatch3r contribution and packaging rules. For hatch3r, require the selected release to contain and document a supported distribution/extension surface; an upstream contribution qualifies only after it is merged, included in that release, and documented there. Stop hatch3r work otherwise.

## 2. Adapter specs and failing-first tests

- [ ] 2.1 Finalize the shared descriptor and a tested harness/version matrix; remove assumptions contradicted by current upstream primary sources.
- [ ] 2.2 Add failing contract tests for install, invocation mapping, semantic parity, exact-version rejection, registry/core identity mismatch, invalid/untrusted signature rejection, absent verified-installer result, signed workflow-digest binding, unsupported hatch3r distribution rejection, drift, upgrade, and safe uninstall before adapter production edits; exercise every fail-closed identity case across installation, upgrade, invocation, and packaging.
- [ ] 2.3 Capture failing-first results in a newly created `TDD_EVIDENCE.md`.

## 3. Minimal adapter implementation

- [ ] 3.1 Implement the Codex plugin shell using the exact signed #434 module identity, preflight workflow identity/digest, implementation-check workflow identity/digest, and installed CLI.
- [ ] 3.2 Implement the ECC skills-first companion and only the command shims required by the supported matrix.
- [ ] 3.3 Implement hatch3r packaging only through the released and documented supported surface verified in 1.3; an accepted or merged upstream prerequisite alone is insufficient until the selected release contains and documents it. Never write internal inventory data or depend on private package layout.
- [ ] 3.4 Keep all validators, approval decisions, and readiness aggregation in the released SpecFact runtime.

## 4. Verification and upstream coordination

- [ ] 4.1 Run adapter contract/parity fixtures against every declared harness version and capture passing evidence.
- [ ] 4.2 Run modules quality, signature/version, contract, smart-test, test, and SpecFact code-review gates for all touched packaged assets.
- [ ] 4.3 Run `openspec status --change preflight-04-harness-adapters --json` and `openspec validate preflight-04-harness-adapters --strict`.
- [ ] 4.4 In separately authorized upstream sessions, create/link ECC and hatch3r issues/PRs and the Codex distribution record; do not mutate external repositories implicitly.

## 5. Delivery and post-merge cleanup

- [ ] 5.1 Verify install/uninstall rollback and remove any unsupported compatibility claim.
- [ ] 5.2 Open the SpecFact implementation PR to `dev` as the final pre-merge task, linking all approved upstream records and evidence.
- [ ] 5.3 After merge, run `openspec archive preflight-04-harness-adapters`, update ordering/source mirrors, and remove the dedicated worktree and merged branch.
