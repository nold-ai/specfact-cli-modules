---
layout: default
title: Requirements bundle overview
nav_order: 2
permalink: /bundles/requirements/overview/
keywords: [requirements, bundle, validation, evidence, coverage]
audience: [solo, team, enterprise]
expertise_level: [beginner, intermediate]
---

# Requirements bundle overview

The **Requirements** bundle (`nold-ai/specfact-requirements`) imports existing
requirement context into SpecFact validation evidence. It normalizes upstream
records, stores them on project bundles as `requirements.inputs`, validates
evidence usefulness by profile, and reports coverage. It does not replace your
planning or product-management system.

## Prerequisites

- SpecFact CLI with core requirements context helpers
- Bundle installed: `specfact module install nold-ai/specfact-requirements`
- A project bundle directory, usually created by the [Project](/bundles/project/overview/) bundle
- Local JSON or YAML requirement records with source attribution

## Command surface

After installation, `specfact requirements --help` lists the runtime command
group.

| Command | Purpose |
|--------|---------|
| `import` | Import local JSON/YAML requirement records into a project bundle |
| `validate` | Validate attached requirement context against a profile |
| `list` | List attached requirement records, optionally with coverage |
| `coverage` | Print coverage counts for downstream evidence links |

## Input shape

Import accepts either a list of records or a mapping with a `requirements` list.
Each record follows the core `RequirementInput` model and must include
`schema_version`, `requirement_id`, `title`, and at least one source reference.

```json
{
  "requirements": [
    {
      "schema_version": "1",
      "requirement_id": "REQ-101",
      "title": "Checkout requires fraud screening",
      "sources": [
        {
          "source_type": "issue",
          "locator": "https://github.com/example/shop/issues/101"
        }
      ],
      "evidence_links": [
        {
          "link_type": "test",
          "target": "tests/test_checkout_fraud.py"
        }
      ]
    }
  ]
}
```

## Quick examples

```bash
specfact requirements import --from-file requirements.json --bundle .specfact/projects/shop --format json
specfact requirements list --bundle .specfact/projects/shop --show-coverage --format json
specfact requirements validate --bundle .specfact/projects/shop --profile enterprise --format json
specfact requirements coverage --bundle .specfact/projects/shop --format json
```

## Storage

The command runtime rehydrates the core `requirements.inputs` extension before
delegating to validation helpers. Because current project bundle serialization
does not persist arbitrary extensions directly, the module also writes
`requirements.inputs.yaml` in the bundle root as the local persistence sidecar.

## Scope boundaries

The bundle is read-first and evidence-focused.

- It imports and normalizes source-attributed requirement context.
- It reports validation findings and coverage gaps.
- It does not expose authoring templates.
- It does not perform bidirectional backlog sync or ceremony automation.

## See also

- [Project bundle overview](/bundles/project/overview/)
- [Backlog adapter patterns](/adapters/backlog-adapter-patterns/)
- [ProjectBundle schema](/reference/projectbundle-schema/)
