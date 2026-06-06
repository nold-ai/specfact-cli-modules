# Parking Lot (modules side)

These module-runtime change proposals are paused, not abandoned. They are not
active implementation scope until a concrete validation need or customer signal
justifies bringing them back.

## Why this directory exists

The modules roadmap is now centered on SpecFact as the validation and AI-bloat
defense CLI. Work that mainly expands upstream ceremonies, enterprise platforms,
FinOps, knowledge systems, or security suites stays here unless it directly
strengthens validation evidence for real users.

## Restoration Policy

A modules-side proposal can return to `openspec/changes/` only after:

1. A concrete trigger is documented in an issue or implementation plan.
2. The paired core contract, if any, is active and validated.
3. The proposal is rechecked against current module command topology and shipped
   specs.
4. `openspec validate <change-id> --strict` passes after the move.

## Contents and Un-Park Triggers

| Modules change | Paired core change | GH issue | Un-park trigger |
|---|---|---|---|
| `enterprise-01-module-policy-client` | `enterprise-01-policy-resolution-extension` | [#231](https://github.com/nold-ai/specfact-cli-modules/issues/231) | Core enterprise-01 un-parked and paying enterprise policy pull exists |
| `enterprise-02-module-audit-client` | `enterprise-02-rbac-and-audit-trail` | [#232](https://github.com/nold-ai/specfact-cli-modules/issues/232) | Core enterprise-02 un-parked and audit/RBAC pull exists |
| `finops-01-module-cost-outcome` | `finops-01-telemetry-and-outcomes` | [#223](https://github.com/nold-ai/specfact-cli-modules/issues/223) | Heavy in-product LLM workloads or customer spend-evidence pull |
| `knowledge-01-module-memory-runtime` | `knowledge-01-distillation-engine` | [#224](https://github.com/nold-ai/specfact-cli-modules/issues/224) | Large evidence corpus with proven rule-mining value |
| `knowledge-02-module-writeback` | `knowledge-02-preflight-context-assembly` | [#225](https://github.com/nold-ai/specfact-cli-modules/issues/225) | knowledge-01 ships useful validation rules in practice |
| `review-resiliency-01-module` | `review-resiliency-01-contracts` | [#226](https://github.com/nold-ai/specfact-cli-modules/issues/226) | Code-review users report a real resiliency evidence gap |
| `security-01-module-sast-sca-secret` | `security-01-unified-findings-model` | [#227](https://github.com/nold-ai/specfact-cli-modules/issues/227) | Customer asks for unified security finding output inside validation evidence |
| `security-02-module-license-compliance` | `security-01-unified-findings-model` | [#228](https://github.com/nold-ai/specfact-cli-modules/issues/228) | Customer asks for license findings inside validation evidence |
| `security-03-module-pii-gdpr-eu` | `security-02-eu-gdpr-baseline` | [#229](https://github.com/nold-ai/specfact-cli-modules/issues/229) | Regulated customer asks for GDPR evidence gates |
| `backlog-scrum-02-sprint-planning` | none active | [#160](https://github.com/nold-ai/specfact-cli-modules/issues/160) | Validation evidence requires sprint-planning data, not ceremony expansion |
| `backlog-scrum-03-story-complexity` | none active | [#153](https://github.com/nold-ai/specfact-cli-modules/issues/153) | Validation evidence requires complexity signals from real users |
| `backlog-scrum-04-definition-of-done` | none active | [#152](https://github.com/nold-ai/specfact-cli-modules/issues/152) | Validation evidence requires DoD fields as gate inputs |
| `backlog-kanban-01-flow-metrics` | none active | [#155](https://github.com/nold-ai/specfact-cli-modules/issues/155) | Validation evidence requires flow metrics for a real delivery gate |
| `backlog-safe-01-pi-planning` | none active | [#154](https://github.com/nold-ai/specfact-cli-modules/issues/154) | Paying customer needs PI-planning data as validation input |
| `backlog-safe-02-risk-rollups` | none active | [#156](https://github.com/nold-ai/specfact-cli-modules/issues/156) | Paying customer needs risk rollups as validation input |
| `ceremony-02-requirements-aware-output` | none active | [#159](https://github.com/nold-ai/specfact-cli-modules/issues/159) | Validation evidence needs ceremony output fields from a real workflow |

## Still Active

The following remain active because they support validation evidence, runtime
trust, or optional upstream context adapters:

- `policy-02-packs-and-modes`
- `governance-01-evidence-output`, `governance-02-exception-management`
- `validation-02-full-chain-engine`, `traceability-01-index-and-orphans`
- `requirements-02-module-commands`, `requirements-03-backlog-sync`
- `architecture-01-solution-layer`, `architecture-02-module-well-architected`
- `openspec-01-intent-trace`
- `sync-01-unified-kernel`
- `docs-14-module-release-history`

Completed validation and AI-bloat changes are archived, not parked.
