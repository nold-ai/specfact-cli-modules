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

- [ ] `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` passes (matches PRs targeting **`dev`**)
- [ ] If this PR targets **`main`**, also confirmed: `hatch run verify-modules-signature --require-signature --payload-from-filesystem --enforce-version-bump` (and/or approval triggered **`sign-modules-on-approval`** for same-repo PRs)
- [ ] Changed bundle versions were bumped when module payloads changed
- [ ] Manifests signed when required by your target branch (CI may sign on **approval** for `dev`/`main` same-repo PRs)

## CI and Branch Protection

- [ ] PR orchestrator jobs expected:
  - `verify-module-signatures`
  - `sign-modules-on-approval` (on approval, same-repo PRs to `dev`/`main` only)
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
