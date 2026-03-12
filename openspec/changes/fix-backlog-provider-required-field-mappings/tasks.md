## 1. Change Setup and Scope

- [x] 1.1 Create worktree `../specfact-cli-modules-worktrees/bugfix/fix-backlog-provider-required-field-mappings` with branch `bugfix/fix-backlog-provider-required-field-mappings` from `origin/dev`
- [x] 1.2 Capture the affected backlog write paths and current mapping/config sources in implementation notes or TDD evidence
- [x] 1.3 Confirm the new change scope covers config-first provider-required field resolution plus explicit override support

## 2. Shared Provider Mapping Resolution

- [x] 2.1 Add shared resolver/helper code that loads persisted `backlog map-fields` config and field-mapping files for backlog write flows
- [x] 2.2 Add explicit command-line provider-field override parsing for backlog write commands
- [x] 2.3 Implement interactive prompting for unresolved required mapped provider fields and non-interactive fail-fast validation

## 3. Command Integration

- [x] 3.1 Update `backlog add` to use the shared provider-required field resolver for ADO and GitHub create payload assembly
- [x] 3.2 Audit backlog writeback commands in `backlog/commands.py` and confirm provider-required field resend is not needed where adapters patch selected fields and preserve untouched provider metadata
- [x] 3.3 Preserve existing canonical CLI flags as higher-priority overrides over resolved config values

## 4. Regression Coverage

- [x] 4.1 Add regression tests for ADO create/write flows with required mapped custom fields resolved from config
- [x] 4.2 Add regression tests for explicit command-line override behavior
- [x] 4.3 Add regression tests proving non-interactive mode fails early and interactive mode prompts for missing mapped required fields
- [x] 4.4 Add GitHub coverage for mapped provider-field handling where persisted `map-fields` metadata is required for write success

## 5. Validation and Delivery

- [x] 5.1 Run `openspec validate fix-backlog-provider-required-field-mappings --strict`
- [x] 5.2 Run targeted tests for the affected backlog command paths and record evidence
- [x] 5.3 Run repo quality gates required for the touched code paths
- [x] 5.4 Open PR to `dev` from `bugfix/fix-backlog-provider-required-field-mappings`
