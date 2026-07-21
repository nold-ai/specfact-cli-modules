# TDD Evidence — requirements-04-upstream-source-readiness

## Failing before implementation

- 2026-07-21 (Europe/Berlin):
  `hatch run test tests/unit/specfact_requirements/test_requirements_runtime.py::test_import_openspec_uses_source_repository_native_validation_policy`
- Result: failed. The wrapper imported one requirement from a source repository
  whose `.specfact/config.yaml` required native OpenSpec validation. The core
  received no source project root, so it resolved policy from the caller's
  working directory and did not reject the missing/invalid native validator.

## Passing after implementation

- 2026-07-21 (Europe/Berlin):
  `hatch run pytest tests/unit/specfact_requirements/test_requirements_runtime.py tests/integration/specfact_requirements/test_command_apps.py -q`
- Result: 23 passed. Coverage includes source-local OpenSpec policy delegation,
  incomplete Spec Kit rejection with zero sidecar writes, unchanged diagnostics,
  source read-only behavior, and accepted-import idempotency.

## Quality evidence

- 2026-07-21 (Europe/Berlin): `hatch run format`, `hatch run type-check`,
  `hatch run lint`, `hatch run yaml-lint`, and `hatch run check-bundle-imports`.
  Result: passed.
- 2026-07-21 (Europe/Berlin): `hatch run contract-test`.
  Result: 28 passed.
- 2026-07-21 (Europe/Berlin): `hatch run smart-test`.
  Result: 886 passed.
- 2026-07-21 (Europe/Berlin): `hatch run python
  scripts/pre_commit_code_review.py
  packages/specfact-requirements/src/specfact_requirements/requirements/runtime.py
  tests/unit/specfact_requirements/test_requirements_runtime.py
  tests/integration/specfact_requirements/test_command_apps.py`.
  Result: passed with zero findings. The report is
  `.specfact/code-review.json` in this worktree.

## Release preparation

- 2026-07-21 (Europe/Berlin):
  `hatch run sign-modules --allow-unsigned --payload-from-filesystem
  packages/specfact-requirements/module-package.yaml`.
- Result: passed. The GitHub PR signing workflow will apply the release
  signature.
- 2026-07-21 (Europe/Berlin):
  `hatch run verify-modules-signature --payload-from-filesystem
  --enforce-version-bump --allow-missing-public-key`.
- Result: passed for the unsigned pre-PR payload checksum. No `0.2.5` registry
  artifacts are committed: GitHub signing/publish automation signs the manifest
  and then rebuilds the tarball, checksum, and registry index from the signed
  manifest bytes. The manifest checksum covers the filesystem payload, while
  the registry checksum covers the generated `.tar.gz` artifact, so their
  values intentionally differ.
- 2026-07-21 (Europe/Berlin):
  `hatch run python scripts/publish_module.py --bundle specfact-requirements
  --registry-index-path registry/index.json`.
- Result: passed against the `dev` registry baseline.

## Post-merge publication

- 2026-07-21 (Europe/Berlin): GitHub Actions `Module Signature Hardening`
  completed successfully for the published 0.2.5 release, and
  `publish-modules` completed successfully from the same `dev` release flow.
- Result: the workflow signed the manifest before packaging, regenerated the
  `.tar.gz` artifact and its registry checksum, and committed the published
  registry metadata. The release is therefore gated by workflow success rather
  than the checksum-only local pre-PR check.
