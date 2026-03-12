# Allowed Imports Policy

This repository allows `specfact_cli.*` imports only for CORE/SHARED APIs that remain in the core `specfact-cli` package.

## Allowed `specfact_cli.*` Prefixes

- `specfact_cli` (exact only)
- `specfact_cli.adapters.registry`
- `specfact_cli.cli`
- `specfact_cli.common`
- `specfact_cli.contracts.module_interface`
- `specfact_cli.integrations.specmatic`
- `specfact_cli.models`
- `specfact_cli.modes`
- `specfact_cli.modules`
- `specfact_cli.registry.registry`
- `specfact_cli.runtime`
- `specfact_cli.telemetry`
- `specfact_cli.utils` (exact only)
- `specfact_cli.utils.bundle_converters`
- `specfact_cli.utils.bundle_loader`
- `specfact_cli.utils.env_manager`
- `specfact_cli.utils.git`
- `specfact_cli.utils.ide_setup`
- `specfact_cli.utils.optional_deps`
- `specfact_cli.utils.performance`
- `specfact_cli.utils.progress`
- `specfact_cli.utils.sdd_discovery`
- `specfact_cli.utils.structure`
- `specfact_cli.utils.structured_io`
- `specfact_cli.utils.terminal`
- `specfact_cli.validators.contract_validator`
- `specfact_cli.validators.schema`
- `specfact_cli.versioning`

All other `specfact_cli.*` imports are treated as MIGRATE-tier and are forbidden in bundle code.

## Module Group Isolation Rules

Direct lateral imports between unrelated bundle groups are disallowed.

Allowed cross-bundle imports:

- `specfact_codebase` -> `specfact_project` (temporary brownfield import delegation while ownership realigns)
- `specfact_spec` -> `specfact_project`
- `specfact_govern` -> `specfact_project`

All other cross-bundle imports between:

- `specfact_backlog`
- `specfact_codebase`
- `specfact_govern`
- `specfact_project`
- `specfact_spec`

are forbidden unless this policy and the import checker allowlist are updated in the same change.
