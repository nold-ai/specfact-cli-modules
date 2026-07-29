## Context

The current evaluator is deliberately deterministic: it finds changed active
OpenSpec directories, imports each into a disposable bundle, overlays declared
test links, validates with the enterprise profile, retains a JSON/Markdown
report, then returns a verdict. Its repository script is CI-safe but not a
reusable public surface.

The paired CLI repository needs the same contract without importing internal
script functions or checking out an unpinned modules branch.

## Decisions

### Command owns evaluator semantics

Move evaluator orchestration behind `specfact requirements evidence`. The
existing script becomes a small adapter to preserve CI compatibility while the
CLI command owns argument validation, report schema, verdicts, and exit codes.
No second evaluator implementation is introduced.

### Two explicit selection modes

`--base-ref <git-ref>` selects changed active sources from
`<base-ref>...HEAD` for CI. `--staged` selects change roots from
`git diff --cached` and materializes a temporary snapshot from the Git index.
The modes are mutually exclusive. `--staged` must not read an affected source
from the caller's dirty worktree.

### Preserve reports before non-zero exits

Both modes require `--output` and may accept `--summary`. Every ordinary
failure writes schema-valid reports before returning non-zero. Local callers
receive concise source/reason lines and a stable report path; the paired CLI
hook adds its AI-IDE wording without parsing private implementation details.

### Compatibility and release

The command is a new module surface. Bump the Requirements module version,
update `core_compatibility` only if the command needs a newer core API, rebuild
registry metadata, and satisfy the signed-module release policy. The core
consumer pins the released commit SHA, never a branch name.

## Risks and Mitigations

- **Index snapshot omits linked test files:** materialize the repository index,
  not just the changed source directory, before validating sidecar targets.
- **Source deletion/archive:** retain existing skipped semantics for absent or
  archived active sources.
- **Script/command drift:** retain one evaluator implementation and add parity
  tests for the compatibility wrapper and public command.
- **Agent ambiguity:** expose deterministic JSON reasons and explicitly state
  `execution_proof: not-included`.
