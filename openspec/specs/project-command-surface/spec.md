# project-command-surface Specification

## Purpose

This spec defines the installed command surface for the `specfact-project`
bundle, including the root `project` group and delegated `plan` commands. It
keeps manifest declarations, docs, and marketplace summaries aligned so routing
tests can prove both command groups remain available.

## Requirements
### Requirement: Project bundle exposes plan command group
The `nold-ai/specfact-project` bundle SHALL declare both `project` and `plan` in its manifest command list so installed bundle routing can delegate `specfact plan ...` calls.

#### Scenario: Manifest includes plan command group
- **WHEN** a consumer inspects `packages/specfact-project/module-package.yaml`
- **THEN** the `commands` list contains both `project` and `plan`
- **AND** docs for module command categories and marketplace bundle summary mention both command groups as part of the project bundle surface.
