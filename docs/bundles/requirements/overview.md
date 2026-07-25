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

- SpecFact CLI `>=0.53.1,<1.0.0`
- Bundle installed: `specfact module install nold-ai/specfact-requirements`
- A project bundle directory, usually created by the [Project](/bundles/project/overview/) bundle
- Local JSON or YAML requirement records with source attribution

## Command surface

After installation, `specfact requirements --help` lists the runtime command
group.

| Command | Purpose |
|--------|---------|
| `import` | Import local records or native OpenSpec/Spec Kit evidence into a project bundle |
| `validate` | Validate attached requirement context against the selected or layered profile |
| `list` | List attached requirement records with optional coverage and core gate counts |
| `coverage` | Print coverage and core gate-finding counts |

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
specfact requirements import --from-openspec openspec/changes/widget-evidence --bundle .specfact/projects/shop --format json
specfact requirements import --from-speckit specs/001-widget-rendering --bundle .specfact/projects/shop --format json
specfact requirements list --bundle .specfact/projects/shop --show-coverage --format json
specfact requirements validate --bundle .specfact/projects/shop --profile enterprise --format json
specfact requirements coverage --bundle .specfact/projects/shop --format json
```

For native imports, a source path is optional. `--from-openspec` discovers a
single conventional change below `openspec/changes/`; `--from-speckit`
discovers a single feature below `specs/`. Multiple or missing candidates are a
clear error so the command never guesses. Pass a path whenever the project has
more than one candidate.

Native imports are read-only and supported only for core's default,
fixture-backed OpenSpec and Spec Kit Markdown profiles. Core readiness
diagnostics are returned unchanged, and any error leaves the requirements
sidecar uncreated or unchanged. Incomplete Spec Kit scaffolds report `incomplete-source-template` or
`source-incomplete`. If the source repository's policy requires native OpenSpec
validation, a failed validator reports `source-invalid`; an unavailable required
validator reports `upstream-validator-unavailable`. Basic OpenSpec imports stay
portable when that policy is not required. The bundle does not infer upstream
tool versions, fall back to another parser, or add upstream metadata.

When `--profile` is omitted, validation uses the effective layered core
configuration. Explicit `--profile` still wins. Core findings such as
`scenario-unverified`, `stale-import`, `source-missing`,
`ambiguous-mapping`, and `unsupported-profile-field` remain machine-readable;
the list and coverage commands include their counts without re-evaluating the
gates.

## CI dogfooding evidence

This repository's `requirements-evidence` pull-request check dogfoods the
native OpenSpec import path. It discovers changed active OpenSpec changes,
imports each one into an isolated temporary project bundle, and writes
`requirements-evidence.json` with one of these verdicts:

- `passed`: source import, validation, test-link coverage, and Requirements
  gate findings are all acceptable.
- `failed`: the artifact lists each deterministic cause, including import
  diagnostics, zero imported requirements, failed validation, incomplete
  test-link coverage, or error-level gate findings. Informational findings stay
  visible in the JSON but do not make the verdict red.
- `skipped`: no active OpenSpec source changed. This is not a claim that
  requirements are met.

GitHub Actions always retains the JSON artifact, including for a red verdict,
and shows a compact summary in the job output. The gate validates requirement
source quality and traceability only. It does **not** prove that linked tests
executed or that product behavior satisfies the requirement; that needs a
future test-result evidence adapter with stable requirement-to-test-result
mapping.

To reproduce the committed-branch check locally:

```bash
hatch run python scripts/requirements_evidence_gate.py \
  --repo-root . \
  --base-ref origin/dev \
  --output artifacts/requirements-evidence/requirements-evidence.json \
  --summary artifacts/requirements-evidence/requirements-evidence.md
```

## Storage

The command runtime rehydrates the core `requirements.inputs` extension before
delegating to validation helpers. Because current project bundle serialization
does not persist arbitrary extensions directly, the module also writes
`reports/requirements/inputs.yaml` in the bundle directory as the local
persistence sidecar.

## Scope boundaries

The bundle is read-first and evidence-focused.

- It imports and normalizes source-attributed requirement context.
- It reports validation findings and coverage gaps.
- It delegates parsing, hashing, compatibility, and gate evaluation to core.
- It does not expose authoring templates.
- It does not perform bidirectional backlog sync or ceremony automation.

## See also

- [Project bundle overview](/bundles/project/overview/)
- [Backlog adapter patterns](/adapters/backlog-adapter-patterns/)
- [ProjectBundle schema](/reference/projectbundle-schema/)
