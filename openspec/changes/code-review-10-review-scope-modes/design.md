# Design: code-review scope modes for modules repo

## Context

`code-review-08-review-run-integration` gave the modules repo a working
`specfact code review run` command, but its implicit changed-file discovery is
too narrow for stepwise review debt cleanup. The upstream `specfact-cli`
contract now defines two auto-discovery modes, `changed` and `full`, plus
repo-relative path filters that can recursively narrow either mode.

This repository owns the runtime command implementation, test fixtures, cli-val
scenario YAML, and bundle docs. The design therefore focuses on deterministic
file selection inside the bundle rather than on higher-level GitHub or
automation wiring.

## Goals / Non-Goals

**Goals:**
- Keep default no-argument behavior aligned with existing changed-file review
- Add `--scope changed|full` and repeatable `--path` filters at the bundle
  command boundary
- Make subtree filtering recursive so users can review one package or test area
  at a time
- Cover the new behavior with unit, e2e, and cli-val fixtures

**Non-Goals:**
- Changing scoring, verdict mapping, or ledger integration
- Adding globbing or exclusion syntax beyond repo-relative path prefixes
- Reworking the internal runner ordering established in `code-review-08`

## Decisions

### Decision: Resolve scope before filtering by path

The bundle should first compute the candidate file set from the selected scope,
then filter that set by any `--path` prefixes. That keeps the behavior stable
between tests and runtime, and makes it easy to explain to users.

### Decision: Reject positional files mixed with scope controls

Positional files already provide an explicit review target. Mixing them with
`--scope` or `--path` would create ambiguous precedence rules, so the command
should fail fast and tell the user to choose one targeting style.

### Decision: Treat `--path` values as repo-relative recursive path segments

Users asked for folder and subfolder limiting. Prefix-based matching is enough
for that need, but matching must happen on normalized path boundaries rather
than raw strings. That keeps `--path packages/specfact-code-review` scoped to
that package and its descendants instead of accidentally including sibling
paths such as `packages/specfact-code-review-old`, while still avoiding new
pattern syntax in the CLI contract.

### Decision: Explicit path filters may opt matched tests back in

The existing changed-only workflow excludes tests by default unless users pass
`--include-tests`. For scope-mode filtering, explicit `--path tests/...`
selection should count as intentional targeting, so matching test files remain
reviewable even when the global include-tests toggle stays at its default.

## Risks / Trade-offs

- [Risk] Full-review mode may surface far more findings than users expect.
  Mitigation: keep it opt-in and document subtree filtering prominently.
- [Risk] Scope/path selection may vary between unit tests and e2e execution if
  repo root detection is inconsistent.
  Mitigation: centralize target resolution in one helper and exercise it
  through both direct tests and installed-command tests.
- [Risk] cli-val scenarios could lag behind actual command behavior.
  Mitigation: update review-run scenario YAML in the same change as the command
  implementation and validate them together.
