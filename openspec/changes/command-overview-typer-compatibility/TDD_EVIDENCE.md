# TDD Evidence: command-overview-typer-compatibility

## Failing-before

### 2026-07-26 Europe/Berlin

An isolated environment installed `requirements-docs-ci.txt`, including Typer
0.27.0 and Click 8.4.2. Before the generator change:

```bash
PYTHONPATH=. <docs-review-python> -m pytest \
  tests/unit/docs/test_llms_overview_freshness.py::test_command_overview_records_typer_parameters \
  -q -p no:cacheprovider
```

Result: failed as expected. `_command_options` returned `[]` instead of
`["--format"]` because Typer 0.27 parameters inherit from
`typer._click.core.Parameter`, not Click's public `Option` and `Argument`
classes.

## Passing-after

### 2026-07-26 Europe/Berlin

- The generator now accepts the supported Click and Typer parameter classes and
  normalizes argument display names, keeping the output stable across the
  Hatch and Docs Review runtimes.
- Under the exact Docs Review dependencies, the focused Typer regression passed
  and `scripts/generate-command-overview.py --check` passed.
- `scripts/generate-command-overview.py --write` was run under those same
  dependencies; the three generated artifacts were already the expected bytes.
- The Docs Review test selection passed: 43 tests across docs workflow,
  documentation accountability, pre-commit parity, and overview freshness.
- Local focused checks passed: the overview freshness suite (6 tests),
  `check-command-overview`, `check-command-contract`,
  `scripts/check-docs-commands.py`, and
  `check-core-documentation-accountability`.
- `openspec validate command-overview-typer-compatibility --strict` passed.

## Final quality evidence

### 2026-07-26 Europe/Berlin

- `hatch run format`, `type-check`, `lint`, `yaml-lint`,
  `check-bundle-imports`, `contract-test`, and `smart-test` passed.
- The baseline signature check could not load any local public keys for the
  seven unchanged manifests. The repository-approved
  `--allow-missing-public-key` checksum and version-bump verification passed
  for all seven manifests; this change does not touch signed assets.
- `hatch run specfact code review run --enforcement changed --bug-hunt --json
  --out .specfact/code-review.json` completed with no findings.
- `hatch run test` retains four unrelated Requirements failures because the
  local paired core checkout is `specfact-cli` 0.52.3, whose
  `import_openspec_change` does not accept the `project_root` argument expected
  by the merged Requirements source. The change-specific Docs Review suite
  remains green under the CI dependency set.
