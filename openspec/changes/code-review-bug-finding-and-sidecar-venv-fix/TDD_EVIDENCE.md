# TDD evidence — code-review-bug-finding-and-sidecar-venv-fix

## Timestamp

2026-04-14 (worktree `feature/code-review-bug-finding-and-sidecar-impl`)

## Tests

- `hatch run test` — **566 passed** (after contract-runner fixture updates and new tests for `tool_availability` / `run` package exports).

## Quality gates (touched scope)

- `hatch run format` — clean
- `hatch run type-check` — clean
- `hatch run lint` — clean
- `hatch run yaml-lint` — clean
- `hatch run validate-cli-contracts` — clean
- `hatch run check-bundle-imports` — clean
- `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump` — clean (manifests re-signed with `--allow-unsigned` where no release key; registry `index.json` + `registry/modules` tarballs updated for `specfact-codebase` **0.41.5** and `specfact-code-review` **0.47.0**)

## SpecFact code review

- For KISS/radon changes in the editable module to be exercised, link the dev module before CLI review:
  - `hatch run python scripts/link_dev_module.py specfact-code-review --force`
- Full-repo JSON report: `hatch run specfact code review run --json --out .specfact/code-review.json`
  - After dev link: **0 error-severity** findings; remaining items are **warnings** (historical KISS/complexity across the repo). The pre-commit / quality gate exit policy is **error-severity only**: **warnings do not block**—only **error**-severity findings affect the CI exit code.
- Scoped check on primary touched sources (Typer `run`, `radon_runner`, `run/commands`, FastAPI/Flask extractors): `PASS_WITH_ADVISORY`, **`ci_exit_code` 0**, report at `.specfact/code-review-touch.json`.

## Registry

- `registry/index.json` updated for new module versions and tarball SHA-256 digests; sidecar `.sha256` files written next to published `.tar.gz` artifacts under `registry/modules/`.
