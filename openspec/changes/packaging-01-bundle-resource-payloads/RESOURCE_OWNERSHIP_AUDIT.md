# Resource Ownership Audit

Date: 2026-03-25

## Reviewed Core Resource Inventory

### Prompt templates currently in `specfact-cli/resources/prompts`

| Core path | Owning bundle | Notes |
| --- | --- | --- |
| `resources/prompts/specfact.01-import.md` | `specfact-codebase` | Executes `specfact import from-code` from the codebase bundle surface. |
| `resources/prompts/specfact.02-plan.md` | `specfact-project` | Covers `specfact plan *` plan-management flows. |
| `resources/prompts/specfact.03-review.md` | `specfact-project` | Covers `specfact plan review`. This is distinct from the `code review` bundle. |
| `resources/prompts/specfact.04-sdd.md` | `specfact-project` | Executes `specfact plan harden`; naming is historical but command ownership is project-bundle. |
| `resources/prompts/specfact.05-enforce.md` | `specfact-govern` | Covers `specfact enforce sdd`. |
| `resources/prompts/specfact.06-sync.md` | `specfact-project` | Covers `specfact sync bridge`. |
| `resources/prompts/specfact.07-contracts.md` | `specfact-spec` | Covers contract enhancement flows under the spec bundle. |
| `resources/prompts/specfact.compare.md` | `specfact-project` | Covers `specfact plan compare`. |
| `resources/prompts/specfact.validate.md` | `specfact-codebase` | Covers `specfact repro`. |
| `resources/prompts/shared/cli-enforcement.md` | Shared companion resource | Referenced by prompt templates via relative path; export is broken if this file is not shipped/copied with prompts. |

### Historical prompt leftovers observed outside the current source tree

- Installed prompt caches in the sibling `specfact-cli` environment still include backlog prompts such as `specfact.backlog-add.md`, `specfact.backlog-daily.md`, `specfact.backlog-refine.md`, and `specfact.sync-backlog.md`.
- Those files are not present in the current canonical source tree under `specfact-cli/resources/prompts`, so they are treated as historical residue rather than the current migration source of truth for this change.

### Backlog workspace-template seeds still living in `specfact-cli`

Canonical source today:

- `.specfact/templates/backlog/field_mappings/ado_agile.yaml`
- `.specfact/templates/backlog/field_mappings/ado_custom.yaml`
- `.specfact/templates/backlog/field_mappings/ado_default.yaml`
- `.specfact/templates/backlog/field_mappings/ado_kanban.yaml`
- `.specfact/templates/backlog/field_mappings/ado_safe.yaml`
- `.specfact/templates/backlog/field_mappings/ado_scrum.yaml`
- `.specfact/templates/backlog/field_mappings/github_custom.yaml`

Audit result:

- These are backlog-bundle-owned workspace-template seeds.
- Goal 3 requires migrating the full set, not only `ado_*.yaml`, because current copy flows and backlog commands also rely on non-ADO templates such as `github_custom.yaml`.

### Resources reviewed and retained as core-owned

These remain in core unless a later audit proves otherwise:

- `resources/keys/*`
- `resources/mappings/*`
- `resources/schemas/*`
- `resources/templates/github-action.yml.j2`
- `resources/templates/persona/*`
- `resources/templates/policies/*`
- `resources/templates/plan.bundle.yaml.j2`
- `resources/templates/pr-template.md.j2`
- `resources/templates/protocol.yaml.j2`
- `resources/templates/telemetry.yaml.example`
- `.specify/templates/*`
- `src/specfact_cli/templates/*`

### Resources already bundle-local in `specfact-cli-modules`

These are already package-owned and are not migration inputs from the core resource tree:

- `packages/specfact-backlog/src/specfact_backlog/backlog_core/resources/backlog-templates/*`
- `packages/specfact-code-review/src/specfact_code_review/resources/skills/specfact-code-review/SKILL.md`
- `packages/specfact-code-review/src/specfact_code_review/resources/supabase/review_ledger_ddl.sql`

## Review Conclusions

1. `packaging-01` must explicitly cover the prompt inventory above, not just “move prompts to corresponding bundles.”
2. Prompt companion files are part of the prompt payload contract because exported prompts reference them by relative path.
3. Backlog template migration must include the entire workspace seed set used by init/install flows, including `github_custom.yaml`.
4. Docs changes `docs-08` through `docs-12` need to describe bundle-owned prompts/templates and reject stale core-owned path references so no separate docs change is required.
