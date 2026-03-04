# Summary

Describe what changed in `specfact-cli-modules` and why.

Refs:
- specfact-cli issue: #
- related module migration item/change: #

## Scope

- [ ] Bundle source changes under `packages/`
- [ ] Registry/manifest changes (`registry/index.json`, `packages/*/module-package.yaml`)
- [ ] CI/workflow changes (`.github/workflows/*`)
- [ ] Documentation changes (`docs/*`, `README.md`, `AGENTS.md`)
- [ ] Security/signing changes (`scripts/sign-modules.py`, `scripts/verify-modules-signature.py`)

## Bundle Impact

List impacted bundles and version updates:

- `nold-ai/specfact-project`: `old -> new`
- `nold-ai/specfact-backlog`: `old -> new`
- `nold-ai/specfact-codebase`: `old -> new`
- `nold-ai/specfact-spec`: `old -> new`
- `nold-ai/specfact-govern`: `old -> new`

## Validation Evidence

Paste command output snippets or link workflow runs.

### Required local gates

- [ ] `hatch run format`
- [ ] `hatch run type-check`
- [ ] `hatch run lint`
- [ ] `hatch run yaml-lint`
- [ ] `hatch run check-bundle-imports`
- [ ] `hatch run contract-test`
- [ ] `hatch run smart-test` (or `hatch run test`)

### Signature + version integrity (required)

- [ ] `hatch run verify-modules-signature --require-signature --enforce-version-bump`
- [ ] Changed bundle versions were bumped before signing
- [ ] Manifests re-signed after bundle content changes

## CI and Branch Protection

- [ ] PR orchestrator jobs expected:
  - `verify-module-signatures`
  - `quality (3.11)`
  - `quality (3.12)`
  - `quality (3.13)`
- [ ] Branch protection required checks are aligned with the above

## Docs / Pages

- [ ] Bundle/module docs updated in this repo (`docs/`)
- [ ] Pages workflow impact reviewed (`docs-pages.yml`, if changed)
- [ ] Cross-links from `specfact-cli` docs updated (if applicable)

## Checklist

- [ ] Self-review completed
- [ ] No unrelated files or generated artifacts included
- [ ] Backward-compatibility/rollout notes documented (if needed)
