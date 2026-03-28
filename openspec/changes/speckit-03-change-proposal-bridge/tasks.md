## 1. Spec-Kit to OpenSpec change proposal conversion

- [x] 1.1 Add `convert_to_change_proposal(feature_path, change_name, output_dir)` method to `SpecKitConverter` in `packages/specfact-project/src/specfact_project/importers/speckit_converter.py`
- [x] 1.2 Implement `spec.md` → `proposal.md` mapping: extract narrative for Why section, extract requirements list for What Changes section, derive capability names
- [x] 1.3 Implement `plan.md` → `design.md` mapping: technical context → Context, phases → Decisions, constraints → Risks/Trade-offs
- [x] 1.4 Implement `spec.md` → `specs/{cap}/spec.md` mapping: reformat user stories and requirements to Given/When/Then scenarios
- [x] 1.5 Implement `tasks.md` → `tasks.md` mapping: convert phase-grouped checklist to numbered checkbox groups
- [x] 1.6 Handle missing artifacts gracefully (no plan.md → minimal design.md with placeholder)
- [x] 1.7 Add unit tests for each mapping step and for the complete conversion flow

## 2. OpenSpec to Spec-Kit feature export

- [x] 2.1 Add `convert_to_speckit_feature(change_dir, output_dir)` method to `SpecKitConverter`
- [x] 2.2 Implement `proposal.md` + `specs/` → `spec.md` mapping: merge narrative and scenarios into user story format
- [x] 2.3 Implement `design.md` → `plan.md` mapping: Context → technical context, Decisions → phases
- [x] 2.4 Implement `tasks.md` → `tasks.md` mapping: checkbox groups → phase-grouped checklist
- [x] 2.5 Add roundtrip test: spec-kit → OpenSpec → spec-kit, verify no data loss for core fields
- [x] 2.6 Add unit tests for export conversion

## 3. Backlog extension issue mapping detection

- [x] 3.1 Create `SpecKitBacklogSync` class in `packages/specfact-project/src/specfact_project/sync_runtime/speckit_backlog_sync.py`
- [x] 3.2 Implement `detect_issue_mappings(feature_path, capabilities)` — scan tasks.md for issue references when matching backlog extension is detected
- [x] 3.3 Add issue reference patterns per tool: Jira (`[A-Z]+-\d+`), ADO (`AB#\d+`), Linear (`[A-Z]+-\d+`), GitHub (`#\d+`)
- [x] 3.4 Return structured issue mapping objects with `tool`, `issue_ref`, `source` fields
- [x] 3.5 Add unit tests for each backlog tool pattern and for the no-extension case

## 4. Integrate duplicate prevention into backlog sync

- [x] 4.1 Update backlog sync flow in `packages/specfact-project/src/specfact_project/sync/commands.py` to call `detect_issue_mappings()` before issue creation
- [x] 4.2 Skip issue creation for tasks with existing spec-kit backlog extension mappings
- [x] 4.3 Log skipped issues and link existing references
- [x] 4.4 Add integration tests for the duplicate prevention flow

## 5. Sync bridge change-proposal mode

- [x] 5.1 Add `--mode change-proposal` option to `specfact sync bridge` command in `sync/commands.py`
- [x] 5.2 Add `--feature` option to specify which spec-kit feature to convert
- [x] 5.3 Add `--all` flag to convert all untracked spec-kit features
- [x] 5.4 Implement feature tracking: detect which spec-kit features already have corresponding OpenSpec changes
- [x] 5.5 Add integration tests for the new command mode

## 6. Profile-aware sync behavior

- [x] 6.1 Add profile detection in sync bridge command (use `profile-01` system when available, fall back to `solo`)
- [x] 6.2 Implement solo profile: spec-kit → OpenSpec as default direction
- [ ] 6.3 Implement team profile: bidirectional with divergence warnings
- [ ] 6.4 Add unit tests for each profile behavior

## 7. Documentation

- [x] 7.1 Update `docs/guides/speckit-comparison.md` with change proposal bridge feature
- [x] 7.2 Update `docs/guides/integrations-overview.md` spec-kit integration section
- [x] 7.3 Add usage examples for the new `--mode change-proposal` command

## 8. Contracts and quality gates

- [x] 8.1 Add `@icontract` and `@beartype` decorators to all new public methods
- [ ] 8.2 Run full quality gate suite
- [x] 8.3 Record TDD evidence in `TDD_EVIDENCE.md`
