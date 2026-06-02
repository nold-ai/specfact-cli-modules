## MODIFIED Requirements

### Requirement: Tool dependency diagnostics use active environment context

Tool dependency checks SHALL probe the active uv, hatch, pip, or pipx execution context before reporting a tool as unavailable.

#### Scenario: Semgrep available through uv is detected

- **GIVEN** a project where `uv run semgrep --version` succeeds
- **WHEN** a codebase or code-review module checks semgrep availability
- **THEN** semgrep is reported as available
- **AND** the diagnostic does not tell the user to install semgrep with a pip-only command.

#### Scenario: Missing tool hints match active manager

- **GIVEN** a required tool is unavailable
- **WHEN** a module emits an installation hint
- **THEN** the hint matches the active manager context when known
- **AND** the output identifies which manager context was checked.
