## REMOVED Requirements

### Requirement: Manual Runs Use Trusted Paired-Core Refs

**Reason**: Event-only step guards do not isolate a dynamic checkout from the
manual event in GitHub's job-level default-cache security model.

**Migration**: Remove manual dispatch from the mixed-trust workflows. If manual
validation is required later, add a separate literal-ref-only workflow.

## ADDED Requirements

### Requirement: Dynamic Paired-Core Validation Uses Non-Manual Triggers

Modules validation workflows that dynamically resolve and execute paired-core
source SHALL NOT expose an externally triggered manual event with default-
branch cache-write access in the same workflow.

#### Scenario: Pull request retains matching paired-core validation

- **GIVEN** a validation workflow runs for a pull request
- **WHEN** the same-named branch exists in the paired core repository
- **THEN** the workflow may resolve and check out that matching paired-core
  branch
- **AND** the checkout does not persist credentials.

#### Scenario: Protected-branch push retains paired-core validation

- **GIVEN** a supported validation workflow runs for a push to `main` or `dev`
- **WHEN** it resolves paired-core source
- **THEN** it uses the corresponding paired-core branch or the existing
  protected-branch fallback
- **AND** the checkout does not persist credentials.

#### Scenario: Dynamic paired-core workflow is not manually dispatchable

- **GIVEN** a workflow dynamically resolves and executes paired-core source
- **WHEN** its trigger contract is inspected
- **THEN** it does not declare `workflow_dispatch`
- **AND** it contains no unreachable manual paired-core checkout path.

#### Scenario: Future manual validation is isolated

- **GIVEN** a future change requires manual paired-core validation
- **WHEN** that entrypoint is designed
- **THEN** it uses a separate workflow with only literal or immutable trusted
  paired-core identities
- **AND** it does not share a job with dynamic paired-core checkout behavior.
