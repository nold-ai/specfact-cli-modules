## ADDED Requirements

### Requirement: Knowledge bundle registration

The modules repository SHALL provide a signed official bundle named `nold-ai/specfact-knowledge` that exposes memory-related commands and declares truthful bundle dependencies, pip dependencies, and `core_compatibility` for the paired core knowledge contracts.

#### Scenario: Bundle manifest is loaded

- **WHEN** SpecFact reads installed module manifests
- **THEN** the knowledge bundle is discoverable as an official package with memory commands and valid compatibility metadata

### Requirement: Markdown-graph is the default runtime backend

The bundle SHALL implement the paired core `MemoryBackend` protocol using a markdown-graph backend rooted at `.specfact/memory/` and SHALL not require a vector store for correctness.

#### Scenario: A repository initializes the memory runtime

- **WHEN** a user runs the knowledge bundle in a repository with no existing memory layout
- **THEN** the bundle creates the expected `.specfact/memory/` structure and uses the markdown-graph backend as the default runtime

### Requirement: Memory commands manage evidence, learnings, and rules deterministically

The bundle SHALL expose commands that add, search, promote, and inspect memory content using the paired core schemas and deterministic filesystem behavior.

#### Scenario: Evidence is recorded from a review workflow

- **WHEN** a workflow records a new evidence item through the knowledge bundle
- **THEN** the bundle stores it using the paired core schema in the expected memory directory and makes it available to subsequent search/status commands
