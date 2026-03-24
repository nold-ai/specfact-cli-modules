## 1. Scope And Ownership Audit

- [ ] 1.1 Enumerate prompt templates currently stored in specfact-cli core and map each one to the owning official bundle.
- [ ] 1.2 Audit other core `resources/` assets for bundle ownership, starting with backlog field mapping templates.
- [ ] 1.3 Record any assets that remain legitimately core-owned so the migration boundary is explicit.

## 2. Test-First Packaging Coverage

- [ ] 2.1 Add failing tests that assert official bundles package their owned prompt resources at stable bundle resource paths.
- [ ] 2.2 Add failing tests that assert the backlog bundle packages field mapping templates needed by init/install flows.
- [ ] 2.3 Add failing tests for integrity/version-bump enforcement when bundled resources change.
- [ ] 2.4 Record failing evidence in `TDD_EVIDENCE.md`.

## 3. Bundle Resource Migration

- [ ] 3.1 Move prompt templates from core-owned storage into the owning official bundle packages.
- [ ] 3.2 Move backlog field mapping templates and any other audited bundle-owned resources into the owning bundle packages.
- [ ] 3.3 Update manifests, package data, and publish-time expectations so the resources are included in released bundle artifacts.

## 4. Validation

- [ ] 4.1 Re-run packaging and integrity tests and record passing evidence in `TDD_EVIDENCE.md`.
- [ ] 4.2 Update docs or package guidance for bundle-owned resources and publish/version-bump expectations.
- [ ] 4.3 Run `openspec validate packaging-01-bundle-resource-payloads --strict`.
