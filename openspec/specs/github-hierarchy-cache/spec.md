# github-hierarchy-cache Specification

## Purpose

This capability standardizes a **repo-local, deterministic GitHub Epic/Feature hierarchy cache** for SpecFact modules and paired `specfact-cli` workflows. It defines how contributors sync hierarchy metadata from GitHub into ignored `.specfact/backlog/` files, how fingerprints detect unchanged trees, and how governance (for example `AGENTS.md` and `docs/agent-rules/`) MUST consult that cache before manual GitHub parent lookups. It builds on the archived OpenSpec change **`governance-03-github-hierarchy-cache`**; shipped behavior and drift against `openspec/**/*.md` remain governed by `openspec/CHANGE_ORDER.md` and the modules release checklist.

## Requirements

### Requirement: Repository hierarchy cache sync

The repository SHALL provide a deterministic sync mechanism that retrieves GitHub Epic and Feature issues for the current repository and writes a local hierarchy cache under ignored `.specfact/backlog/`.

#### Scenario: Generate hierarchy cache from GitHub metadata

- **WHEN** the user runs the hierarchy cache sync script for the repository
- **THEN** the script retrieves GitHub issues whose Type is `Epic` or `Feature`
- **AND** writes a markdown cache under ignored `.specfact/backlog/` with each issue's number, title, URL, short summary, labels, and hierarchy relationships
- **AND** the output ordering is deterministic across repeated runs with unchanged source data

#### Scenario: Fast exit on unchanged hierarchy state

- **WHEN** the script detects that the current Epic and Feature hierarchy fingerprint matches the last synced fingerprint
- **THEN** it exits successfully without regenerating the markdown cache
- **AND** it reports that no hierarchy update was required

### Requirement: Modules governance must use cache-first hierarchy lookup

Repository governance instructions SHALL direct contributors and agents to consult the local hierarchy cache before performing manual GitHub lookups for Epic or Feature parenting.

#### Scenario: Cache-first governance guidance

- **WHEN** a contributor reads `AGENTS.md` for GitHub issue setup guidance
- **THEN** the instructions tell them to consult the local hierarchy cache first
- **AND** the instructions define when the sync script must be rerun to refresh stale hierarchy metadata
- **AND** the instructions state that the cache is local ephemeral state and must not be committed
