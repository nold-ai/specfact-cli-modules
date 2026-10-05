# Tasks: workflow-02-ecosystem-adapters

All tasks are future implementation. This planning PR completes no runtime task and manufactures no RED/GREEN or installed-module evidence. Split implementation tasks into sessions of at most two hours.

## 1. Readiness and specification

- [ ] 1.1 Create a dedicated issue-linked worktree from current origin/dev; refresh cache and verify parent, labels, assignee, project, blockers and no concurrent In Progress owner.
- [ ] 1.2 Verify exact released prerequisites and compatibility; refine only owner-authorized deltas against current code and paired public proposal.
- [ ] 1.3 Finalize optional versioned contracts, source identities, offline behavior and unsupported-input diagnostics in the specs.

## 2. Tests before implementation

- [ ] 2.1 Derive meaningful positive/negative fixtures for thin upstream and ci invocation adapters and all its scenarios.
- [ ] 2.2 Derive meaningful positive/negative fixtures for loss-aware summaries and sarif projection and all its scenarios.
- [ ] 2.3 Derive meaningful positive/negative fixtures for least-privilege portable integration and all its scenarios.
- [ ] 2.4 Run those tests before behavior changes and record actual failing commands, timestamps and causes under the applicable evidence policy; do not reuse planning inspection as execution evidence.

## 3. Bounded implementation

- [ ] 3.1 Implement the smallest contract slice with beartype/icontract on public parsing/validation APIs; preserve existing adapters and original artifacts.
- [ ] 3.2 Integrate only released supported producer interfaces; keep external side effects opt-in and share #483 budgets instead of adding a repair controller.
- [ ] 3.3 Run scenario and compatibility regressions; record passing evidence, limitations and exact identities.

## 4. Documentation and review

- [ ] 4.1 Update owning reference/workflow guides, CLI help and README as needed; preserve frontmatter and navigation.
- [ ] 4.2 Run strict OpenSpec validation, planning/requirements mapping validation, scope-appropriate format/lint/type/contract/tests and independent analysis when code is affected.
- [ ] 4.3 Produce fresh SpecFact review JSON for affected review targets and resolve every finding, including warnings, or document the applicable explicit planning-only exception.

## 5. Release and handoff

- [ ] 5.1 For runtime changes, bump the owning release per semver, update compatibility/changelog and verify signatures and payload identities; this planning-only change bumps nothing.
- [ ] 5.2 Submit the implementation PR to dev and complete normal reviewed integration.
- [ ] 5.3 Publish through the canonical signed release path, exercise the exact installed compatible pair and document rollback before downstream adoption; reconcile issue/project state and paired source tracking, and archive the completed change with openspec archive only after actual delivery.
