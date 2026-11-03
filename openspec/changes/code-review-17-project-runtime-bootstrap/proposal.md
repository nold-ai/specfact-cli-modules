# Change: Project-aware runtime and lightweight sidecar bootstrap

## Why

The owner approved replacing capsule execution with trusted local project-aware review on 2026-10-16, Europe/Berlin. Customers need their own Python dependencies, entrypoints, plugins and coding standards without SpecFact dependency pollution.

## What Changes

Extract/adapt project discovery and native manager behavior into the shared Codebase service. Prove one complete detached Hatch existing/cold workflow before expanding pip/pip-tools, uv and Poetry adapters. Keep controller, customer and analyzer dependencies separate.

- Follow the canonical architecture in change 17 and keep one runtime owner and one public review runner.
- Preserve source identity, honest incomplete evidence, signatures and independent security obligations.
- Keep customer standards distinct from supplemental SpecFact findings and future protected/C15 assurance.

## Capabilities

### New Capabilities

- `project-runtime-bootstrap`: project-aware runtime and lightweight sidecar bootstrap.

### Modified Capabilities

Existing review/runtime/sidecar behavior is modified only by the later implementation. The deltas below establish its intended replacement contract. Canonical specs are not promoted by this planning delivery.

## Dependencies

Direct implementation blockers: none.

Parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), within Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162). Optional preflight, architecture and requirement-context work are future consumers, not prerequisites. C15 #417/core #679 and protected core #680 retain their separate ownership and acceptance.

## Impact

The merged 2026-10-20 delivery changed planning artifacts and GitHub alignment only. On 2026-10-23 the owner authorized takeover of #513 and implementation of only the first existing and cold detached Hatch milestone. The ordinary public reviewer cutover, remaining manager adapters, paired core adoption and release acceptance remain later work. Completion of this milestone does not complete or archive change 17.

The confirmed customer outcome is straightforward review of a trusted Python repository without making its developer resolve SpecFact dependency conflicts. Existing project Python, dependencies, native plugins and configuration remain authoritative. SpecFact and analyzer packages stay outside the customer environment. Read-only inspection and actionable ambiguity/preparation failures must not substitute the controller Python or weaken project constraints.

Future implementation affects the owning Codebase/Code Review modules and ordinary core consumers, with semver, signing and exact installed acceptance required. There is no hostile-code sandbox, custom environment broker, mandatory customer coverage floor, mandatory contract decoration, or protected local PR authority.

## Acceptance

Every requirement and scenario in [the delta spec](specs/project-runtime-bootstrap/spec.md) has a planning inspection mapping. Runtime acceptance requires actual failing-first tests, passing execution, source/environment integrity and the applicable installed workflow in follow-up sessions. Strict artifact validation is not runtime verification.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #513
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/513>
- **Last Synced Status**: open
- OpenSpec change: `code-review-17-project-runtime-bootstrap`.
- Status: open / In Progress, verified 2026-10-23. The owner explicitly authorized this chat to take over the first Hatch milestone.
- Assignee: djm81. Project: SpecFact CLI. Issue type: User Story.
- User-confirmed trust: dependency installation, build hooks, imports and configured checks execute locally in trusted customer repositories.
- Rollback: preserve immutable compatible released CLI/module pairs; no old production backend is retained after the cutover.
