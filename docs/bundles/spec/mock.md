---
layout: default
title: Spec mock
nav_order: 5
permalink: /bundles/spec/mock/
redirect_from:
  - /guides/spec-mock/
keywords: [spec, mock, testing, stub, simulation]
audience: [solo, team, enterprise]
expertise_level: [intermediate, advanced]
---

# Spec mock

`specfact spec mock` starts a Specmatic mock server from a contract file or from the contracts tracked in a bundle.

## Command

- `specfact spec mock`

## Key options

| Option | Purpose |
|--------|---------|
| `--spec <path>` | Start the server from one explicit contract file |
| `--bundle <name>` | Pick the contract from the selected bundle or active plan |
| `--port <number>` | Override the default mock server port (`9000`) |
| `--strict`, `--examples` | Choose strict validation mode or example-driven responses |
| `--no-interactive` | Use the first available bundle contract without prompting |

## Examples

```bash
specfact spec mock --spec api/openapi.yaml
specfact spec mock --spec api/openapi.yaml --port 8080
specfact spec mock --spec api/openapi.yaml --examples
specfact spec mock --bundle legacy-api
specfact spec mock --bundle legacy-api --no-interactive
```

## When to use it

- Frontend development without a running backend
- Contract demos and sandbox environments
- Early integration checks before a service is implemented

## Bundle-owned resources

The mock command reads contracts from the installed bundle or active plan state. That state lives with the bundle and project artifacts, not in legacy core-owned prompt/template paths.

## Related

- [Spec validate and backward compatibility](validate/)
- [Generate Specmatic tests](generate-tests/)
