## Why

Primary tester reports show that shipped AI slash prompts can drift from the CLI command surface. Because these prompts are bundle payloads, stale command paths or options can ship to users even when code, docs, and signatures pass.

## What Changes

- Add a prompt command validation gate for bundle-owned prompt resources under `packages/*/resources/prompts`.
- Validate prompt command examples and option references against the mounted Typer/Click command tree discovered from the current repo.
- Update shipped prompt guidance so prompts treat their text as operating guidance and verify CLI reality at execution time instead of acting as the source of truth.
- Wire the validator into Hatch, local pre-commit checks, and Markdown-triggered CI.
- Exclude `.github/prompts` from this change; OpenSpec helper prompts remain a separate governance surface.

## Capabilities

### New Capabilities

- `prompt-command-validation`: Validation of bundle-owned AI prompt command references against current CLI command contracts.

### Modified Capabilities

- `bundle-packaged-resources`: Bundle-owned prompt resources are additionally required to be command-contract validated before release.
- `resource-aware-integrity`: Resource prompt edits remain signed payload changes and must continue to trigger version/signature enforcement.

## Impact

- Affected resources: `packages/*/resources/prompts/**/*.md`.
- Affected validation tooling: `scripts/`, `pyproject.toml`, `scripts/pre-commit-quality-checks.sh`, `.github/workflows/docs-review.yml`, and tests.
- Bundle prompt edits may require module version/signature updates because prompt resources are signed payloads; this change does not alter `registry/index.json` unless release packaging is performed separately.
