## 1. Spec And Test Setup

- [x] 1.1 Add regression tests for the modules pre-commit configuration and helper script so required local gates are asserted in source control.
- [x] 1.2 Capture the pre-implementation failing test run in `openspec/changes/modules-pre-commit-quality-parity/TDD_EVIDENCE.md`.

## 2. Hook Implementation

- [x] 2.1 Add a staged-file aware pre-commit helper script for the modules repo modeled on the core repo behavior.
- [x] 2.2 Update `.pre-commit-config.yaml` to use the new modules quality hook and always-run signature verification hook.

## 3. Validation

- [x] 3.1 Re-run the new tests and capture the passing run in `openspec/changes/modules-pre-commit-quality-parity/TDD_EVIDENCE.md`.
- [x] 3.2 Run `hatch run format`.
- [x] 3.3 Run `hatch run lint`.
- [x] 3.4 Run `hatch run yaml-lint`.
- [x] 3.5 Run `openspec validate modules-pre-commit-quality-parity --strict`.
