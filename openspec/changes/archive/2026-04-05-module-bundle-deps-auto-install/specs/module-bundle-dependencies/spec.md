# module-bundle-dependencies Specification

## Purpose

Define how official module packages declare peer bundle dependencies so SpecFact CLI and the registry expose a consistent install graph for shared command groups (for example `code`).

## ADDED Requirements

### Requirement: Code-review module declares codebase peer dependency

The `nold-ai/specfact-code-review` module SHALL list `nold-ai/specfact-codebase` in `bundle_dependencies` inside `packages/specfact-code-review/module-package.yaml` so that installing code review can resolve the peer bundle required for the full `code` command group.

#### Scenario: Manifest names the codebase bundle

- **WHEN** a maintainer reads `packages/specfact-code-review/module-package.yaml`
- **THEN** the `bundle_dependencies` sequence includes `nold-ai/specfact-codebase`

### Requirement: Registry mirrors manifest bundle dependencies for code-review

The `registry/index.json` entry for `nold-ai/specfact-code-review` SHALL list the same `bundle_dependencies` values as the published `module-package.yaml` for that module version.

#### Scenario: Registry matches manifest after publish

- **WHEN** the code-review module version is published and the registry row is updated
- **THEN** the `bundle_dependencies` array for `nold-ai/specfact-code-review` equals the manifest’s `bundle_dependencies` for that version

### Requirement: Dependency declarations stay acyclic

Official module `bundle_dependencies` SHALL NOT introduce a dependency cycle between official nold-ai bundles.

#### Scenario: Code-review dependency does not create a cycle

- **WHEN** code-review declares a dependency on codebase
- **THEN** no official bundle manifest transitively depends back on `nold-ai/specfact-code-review` in a way that forms a cycle
