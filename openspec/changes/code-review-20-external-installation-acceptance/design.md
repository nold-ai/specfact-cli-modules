# Design for external installation and customer acceptance

## Canonical architecture

[Change 17 design](../code-review-17-project-runtime-bootstrap/design.md) owns the architecture, API sketch, trust decisions, alternatives, acceptance matrix and synthesis. This document records only this change's implementation responsibility. No runtime implementation or supported distribution is established here.

## Responsibility and data flow

Exercise exact signed installed distributions through pipx, uv tool and repeated uvx. Replace capsule-only CI, document the compatibility/trust migration and prepare a coordinated breaking release with rollback.

The acceptance subject is the exact installed compatible CLI/module pair, not a source checkout or candidate self-report. Test pipx and uv tool with user-scoped modules, then test a fresh repeated uvx invocation. Current module installation may assume `sys.executable -m pip`; a disposable tool environment may lack pip or must not be mutated unmanaged. Resolve this with the paired core ordinary-installation contract and supported declared/tool installation mechanisms, without installing anything into customer environments.

After provisioning valid locally verified signed modules, the project environment and selected tools, run each supported installed route with networking disabled and any required local invocation cache present. Do not require fresh registry or package-index access. Missing local prerequisites stay nonaccepting; cold offline bootstrap is not promised. Core #769 supplies compatibility preflight and this change owns release-level offline acceptance.

Exercise existing and cold manager contexts with project/controller Python differences, entrypoints, native extensions/libraries, generated modules, pytest plugins and project-specific standards. Preserve existing environment package inventory and lock/declaration bytes. Attribute ordinary trusted hook outputs separately. Required cell failure or timeout stays nonaccepting. Advertise only passing host/project/analyzer cells, recording capabilities separately from controller support.

Replace capsule-only customer jobs, native builds, publication/signing infrastructure and support docs with required local installed acceptance. Keep independent security, signing, quality and review gates. Modules #511 and core #718/#719 remain independent obligations. Optional preflight, architecture and requirements context do not block this release.

Release Code Review as a breaking major and make truthful Codebase/core compatibility changes. Update docs with existing modules.specfact.io permalinks, native help, tool installation routes, report trust/compatibility and rollback. Use normal canonical publication/signatures. Immutable old releases remain available. A planning PR publishes nothing and cannot satisfy release acceptance.

## Implementation reconciliation and first step

All implementation remains pending. Accepted interface or responsibility deviations must update the canonical design and this delta before handoff. Start by adding scenario-mapped behavior tests and capturing actual failing evidence. Preserve existing applicable governance while implementing the approved replacement.

## Risks and rollback

Wrong interpreter/source, dependency drift and overstated completion are the primary risks. Verify actual executable/source identities, native configuration and failure behavior. Keep an immutable compatible released pair for rollback. No permanent capsule backend remains in the replacement.
