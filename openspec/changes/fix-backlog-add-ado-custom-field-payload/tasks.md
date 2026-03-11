## 1. Branch and TDD Setup

- [ ] 1.1 Create worktree `../specfact-cli-modules-worktrees/bugfix/fix-backlog-add-ado-custom-field-payload` with branch `bugfix/fix-backlog-add-ado-custom-field-payload` from `origin/dev`
- [ ] 1.2 Bootstrap the worktree environment with `hatch env create`
- [ ] 1.3 Run pre-flight checks with `hatch run smart-test-status` and `hatch run contract-test-status`
- [ ] 1.4 Capture failing regression tests for ADO create payload behavior in `TDD_EVIDENCE.md`
- [ ] 1.5 Confirm the change scope is limited to `backlog-add` ADO create payload assembly and tests

## 2. ADO Create Payload Implementation

- [ ] 2.1 Update `backlog_core/commands/add.py` to resolve mapped ADO create fields from the configured field-mapping file
- [ ] 2.2 Preserve explicit `work_item_type` propagation while adding mapped required custom fields to the create payload
- [ ] 2.3 Keep interactive and non-interactive ADO create flows on the same normalized payload path

## 3. Regression Coverage

- [ ] 3.1 Add unit tests covering non-interactive ADO create payloads with mapped required custom fields
- [ ] 3.2 Add unit tests proving interactive and non-interactive ADO create flows emit equivalent provider payload fields
- [ ] 3.3 Run focused backlog add tests and record passing evidence in `TDD_EVIDENCE.md`

## 4. Validation and Delivery

- [ ] 4.1 Run `openspec validate fix-backlog-add-ado-custom-field-payload --strict`
- [ ] 4.2 Run workflow validation and update `CHANGE_VALIDATION.md` with dependency and consistency analysis
- [ ] 4.3 Open PR to `dev` from `bugfix/fix-backlog-add-ado-custom-field-payload`
