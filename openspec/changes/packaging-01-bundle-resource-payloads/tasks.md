## 1. Scope And Ownership Audit

- [x] 1.1 Enumerate prompt templates currently stored in specfact-cli core and map each one to the owning official bundle.
- [x] 1.2 Record prompt companion assets required by those prompts, starting with `resources/prompts/shared/cli-enforcement.md`, and map how they will be packaged and exported.
- [x] 1.3 Audit other core `resources/` assets for bundle ownership, starting with the complete backlog field mapping template seed set used by init/install flows.
- [x] 1.4 Record any assets that remain legitimately core-owned so the migration boundary is explicit.
- [x] 1.5 Save the ownership inventory and keep-in-core list in `RESOURCE_OWNERSHIP_AUDIT.md`.

## 2. Test-First Packaging Coverage

- [x] 2.1 Add failing tests that assert official bundles package their owned prompt resources at stable bundle resource paths.
- [x] 2.2 Add failing tests that assert prompt companion assets referenced by exported prompts are packaged and discoverable with those prompts.
- [x] 2.3 Add failing tests that assert the backlog bundle packages all field mapping templates needed by init/install flows, including non-ADO templates.
- [x] 2.4 Add failing tests for integrity/version-bump enforcement when bundled resources change.
- [x] 2.5 Add failing tests or fixtures that exercise the stable resource paths expected by `specfact init ide` and related copy flows.
- [x] 2.6 Record failing evidence in `TDD_EVIDENCE.md`.

## 3. Bundle Resource Migration

- [x] 3.1 Move prompt templates from core-owned storage into the owning official bundle packages.
- [x] 3.2 Move prompt companion assets needed by migrated prompts into the stable bundle prompt layout.
- [x] 3.3 Move backlog field mapping templates and any other audited bundle-owned resources into the owning bundle packages.
- [x] 3.4 Update manifests, package data, and publish-time expectations so the resources are included in released bundle artifacts.

## 4. Validation

- [x] 4.1 Re-run packaging and integrity tests and record passing evidence in `TDD_EVIDENCE.md`.
- [x] 4.2 Verify the packaged layout matches the path contract consumed by specfact-cli change `packaging-02-cross-platform-runtime-and-module-resources`.
- [x] 4.3 Update docs or package guidance for bundle-owned resources and publish/version-bump expectations.
- [x] 4.4 Confirm docs changes `docs-08` through `docs-12` absorb the user-facing documentation fallout from migrated resources so no extra docs change is required.
- [x] 4.5 Run `openspec validate packaging-01-bundle-resource-payloads --strict`.
