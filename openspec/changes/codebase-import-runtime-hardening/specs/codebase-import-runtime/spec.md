## ADDED Requirements

### Requirement: Import runtime SHALL prune hidden and heavyweight trees before discovery
`specfact code import` SHALL apply one deterministic ignore policy before any repository traversal phase counts, discovers, or analyzes candidate files. The default policy SHALL exclude dot-prefixed directories, virtual environments, build outputs, dependency caches, and other heavyweight artifact roots unless the user explicitly targets a path inside them.

#### Scenario: Default traversal skips hidden and heavyweight directories
- **WHEN** the user runs `specfact code import` against a repository root that contains directories such as `.git/`, `.specfact/`, `.venv/`, `venv/`, `node_modules/`, `build/`, `dist/`, or `__pycache__/`
- **THEN** import discovery SHALL prune those directories before recursive traversal
- **AND** those files SHALL NOT contribute to scanned-file counts, analyzer inputs, or relationship extraction inputs

#### Scenario: Repo-local ignore file extends the default policy
- **WHEN** the repository contains `.specfact/.specfactignore` with additional ignore patterns
- **THEN** `specfact code import` SHALL merge those patterns with the default ignore policy for every traversal phase
- **AND** matching files or directories SHALL be pruned before traversal rather than filtered only after discovery

### Requirement: Import runtime SHALL surface large-artifact warnings
The import runtime SHALL warn when repository traversal encounters unusually large ignored artifact trees or unexpectedly high file volumes that are likely to dominate wall-clock time on slow environments.

#### Scenario: Encountering a heavy artifact tree emits a warning
- **WHEN** import discovery encounters an ignored directory whose file count crosses the runtime's heavy-artifact threshold
- **THEN** the command SHALL emit a warning that names the directory or pattern class
- **AND** the warning SHALL explain that the tree was ignored to avoid inflated import duration

#### Scenario: Encountering unusually large candidate file volume emits a warning
- **WHEN** the import runtime discovers a candidate file volume that exceeds its large-repository warning threshold after pruning ignored trees
- **THEN** the command SHALL warn that repository size and environment overhead can materially extend import duration
- **AND** it SHALL avoid promising a fixed-duration expectation such as "about five minutes"

### Requirement: Import progress SHALL use discovered-versus-processed work
Long-running import phases SHALL derive percentage and remaining-time feedback from the amount of real work discovered after ignore pruning, not from optimistic static estimates or totals that include skipped files.

#### Scenario: Analyzer progress total reflects analyzable files only
- **WHEN** the analyzer computes its progress task for a repository import
- **THEN** the total work units SHALL equal the filtered set of analyzable files after ignore pruning
- **AND** progress completion SHALL be able to reach 100 percent without stalling below the total because skipped files were counted

#### Scenario: Remaining time updates from live discovered work
- **WHEN** the command has discovered part of the repository and has processed a subset of that discovered work
- **THEN** the remaining-time display SHALL be derived from processed-versus-discovered work at the current runtime rate
- **AND** any early estimate before full discovery SHALL be labeled as provisional rather than a fixed promise
