# TDD Evidence

## Failing Before

- `hatch run pytest tests/unit/test_check_prompt_commands_script.py -q` — failed as expected before implementation.
  - 7 failures.
  - Missing `scripts/check-prompt-commands.py`.
  - Missing docs-review workflow prompt validation trigger/step.
  - Missing pre-commit prompt validation gate.

## Passing After

- `openspec validate prompt-command-contract-validation --strict` — passed.
- `hatch run pytest tests/unit/test_check_prompt_commands_script.py -q` — 7 passed.
- `hatch run validate-prompt-commands` — passed.
- `hatch run pytest tests/unit/test_check_prompt_commands_script.py tests/unit/test_pre_commit_quality_parity.py tests/unit/test_check_docs_commands_script.py tests/unit/test_validate_repo_manifests_bundle_deps.py tests/unit/test_registry_manifest_bundle_dependencies.py -q` — 30 passed.
- `hatch run yaml-lint` — passed.
- `hatch run format` — passed after applying formatter output.
- `hatch run type-check` — passed.
- `hatch run lint` — passed.
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --version-check-base HEAD` — passed.
- `hatch run contract-test` — 663 passed, 2 warnings.
- `hatch run smart-test` — 663 passed, 2 warnings.
- `hatch run test` — 663 passed, 2 warnings.
- `hatch run specfact code review run --bug-hunt --json --out .specfact/code-review.json --scope changed` — passed with zero findings.

## Resource Signing and Registry Evidence

- `hatch run sign-modules --payload-from-filesystem --changed-only --base-ref HEAD --bump-version patch --allow-unsigned` — refreshed changed bundle manifests and checksum integrity.
- `hatch run sync-registry-from-package --bundle specfact-backlog --bundle specfact-codebase --bundle specfact-govern --bundle specfact-project --bundle specfact-spec` — refreshed registry index and tarball sidecars for changed bundle versions.
