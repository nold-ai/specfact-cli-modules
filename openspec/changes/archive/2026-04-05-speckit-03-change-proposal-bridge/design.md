## Context

SpecFact's OpenSpec workflow manages change proposals as structured artifact sets (`proposal.md`, `design.md`, `specs/**/*.md`, `tasks.md`) in `openspec/changes/`. Spec-Kit manages features as flat artifact sets (`spec.md`, `plan.md`, `tasks.md`) in `specs/{feature}/` or `.specify/specs/{feature}/`. Both represent the same conceptual unit (a scoped change with requirements, plan, and tasks) but in incompatible formats.

The `SpecKitConverter` in `specfact_project/importers/speckit_converter.py` already converts spec-kit artifacts to SpecFact `PlanBundle` format. This change extends it to produce OpenSpec change artifacts directly, and adds the reverse direction.

Spec-Kit's extension ecosystem now includes backlog integrations (Jira, ADO, Linear, GitHub Projects, Trello) that create issues from specs. When SpecFact's `backlog-sync` also targets the same backlog tools, duplicate issues are created. This change adds issue-mapping detection to prevent that.

## Goals / Non-Goals

**Goals:**
- Convert a spec-kit feature folder into a complete OpenSpec change proposal (all 4 artifacts)
- Convert an OpenSpec change proposal back to spec-kit feature folder format
- Detect spec-kit backlog extension issue mappings and import them into SpecFact's tracking
- Support both solo and team profiles with appropriate sync behavior
- Add a `--mode change-proposal` option to the sync bridge command

**Non-Goals:**
- Replacing spec-kit's own sync/reconcile extensions (we convert artifacts, not compete on drift detection)
- Supporting spec-kit extension invocation from SpecFact (detection only)
- Managing spec-kit's internal state files or caches
- Handling spec-kit extensions that aren't backlog-related (focus on issue sync only)

## Decisions

### D1: Spec-kit feature → OpenSpec change artifact mapping

| Spec-Kit Artifact | OpenSpec Artifact | Mapping Strategy |
|---|---|---|
| `spec.md` (user stories, requirements, success criteria) | `proposal.md` (Why + What Changes) + `specs/{cap}/spec.md` (Given/When/Then) | Split: narrative goes to proposal, requirements reformat to OpenSpec spec scenarios |
| `plan.md` (technical context, dependencies, phases) | `design.md` (Context, Decisions, Risks) | Reformat: phases → decisions, constraints → risks/trade-offs |
| `tasks.md` (checklist items with phase refs) | `tasks.md` (numbered checkbox groups) | Reformat: preserve phase grouping, map to `## N. Group` / `- [ ] N.M Task` format |
| `constitution.md` | Not mapped (project-level, not change-level) | Skip: constitution is project config, not change-scoped |

**Rationale**: Spec-kit's `spec.md` conflates the "why" (narrative) with the "what" (requirements). OpenSpec separates these into `proposal.md` and `specs/`. The split produces better artifacts for each workflow.

### D2: Issue mapping detection via extension catalog metadata

Rather than parsing backlog tool APIs, detect issue mappings from spec-kit extension output files. Spec-Kit backlog extensions (Jira, ADO, etc.) store issue references in the feature's task files or in extension-specific metadata files.

Detection strategy:
1. Check `ToolCapabilities.extension_commands` for backlog extension presence (e.g., `jira`, `azure-devops`, `linear`)
2. Scan feature `tasks.md` for issue reference patterns (e.g., `JIRA-123`, `AB#456`, `LIN-789`)
3. If found, import these as existing issue mappings in SpecFact's backlog tracker
4. During SpecFact backlog sync, skip creation for issues that already have mappings

**Rationale**: This avoids requiring API credentials for each backlog tool. Issue references in task files are the most reliable signal that spec-kit already created the issue.

### D3: Profile-aware sync behavior

| Profile | Spec-Kit Role | SpecFact Role | Sync Behavior |
|---|---|---|---|
| `solo` | Primary authoring tool | Enforcement + validation layer | Spec-Kit → OpenSpec is default direction; export back only on explicit request |
| `startup` / `mid_size` | Shared authoring (some team members use spec-kit, others use OpenSpec) | Shared authoring + enforcement | Bidirectional with conflict detection; warn on divergence |
| `enterprise` | One of many tools | Central governance | Import from spec-kit; governance policies override spec-kit artifacts |

Profile detection uses the `profile-01-config-layering` system when available, falling back to `solo` when no profile is configured.

**Rationale**: Solo devs expect spec-kit to be the source of truth. Teams need reconciliation. Enterprises need governance.

## Risks / Trade-offs

- **[Lossy conversion]** Spec-kit's `spec.md` format contains fields (INVEST criteria, edge cases, scenarios) that don't map 1:1 to OpenSpec's Given/When/Then format → **Mitigation**: Preserve unmapped fields as comments in the generated spec. Add `<!-- Original spec-kit field: ... -->` annotations.
- **[Issue reference parsing fragility]** Regex-based issue reference detection may produce false positives → **Mitigation**: Only parse when a corresponding backlog extension is detected in the catalog. Use known patterns per tool (JIRA: `[A-Z]+-\d+`, ADO: `AB#\d+`, Linear: `[A-Z]+-\d+`).
- **[Profile system dependency]** Profile-aware behavior depends on `profile-01-config-layering` which is pending → **Mitigation**: Fall back to `solo` profile (spec-kit as primary) when profile system is not available. This is a safe default for the most common use case.

## Open Questions

- Should the change proposal bridge preserve spec-kit frontmatter (Feature Branch, Status, Created) as metadata in the OpenSpec proposal? (Proposed: yes, as YAML front-matter block.)
- Should roundtrip conversion (spec-kit → OpenSpec → spec-kit) be lossless? (Proposed: best-effort with annotations for unmappable fields.)
