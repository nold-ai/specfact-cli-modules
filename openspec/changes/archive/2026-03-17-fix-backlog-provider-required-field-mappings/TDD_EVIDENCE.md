## Failing / Gap Confirmation

- Core-repo write-path inspection confirmed that ADO create serializes `payload["provider_fields"]["fields"]` directly into the create patch document, while update flows patch selected fields only.
- Before this change, `backlog add` only forwarded a narrow hardcoded canonical set and had no config-first path for required mapped provider fields discovered by `specfact backlog map-fields`.
- That left enterprise-required mapped ADO fields vulnerable to provider-side HTTP 400 failures unless the command happened to expose the exact canonical field already.

## Passing Evidence

Focused add-command regressions were run in the dedicated worktree using the local `specfact-cli` source and existing site packages on `PYTHONPATH`:

```bash
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli/src:/home/dom/.local/lib/python3.11/site-packages:/usr/lib/python3/dist-packages \
  hatch run pytest tests/unit/specfact_backlog/unit/test_add_command.py \
  tests/unit/specfact_backlog/unit/test_add_command_ado_provider_fields.py \
  tests/unit/specfact_backlog/unit/test_add_command_github_provider_overrides.py -q
```

Result:

- `27 passed in 0.54s`

Additional focused provider-field regressions:

```bash
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli/src:/home/dom/.local/lib/python3.11/site-packages:/usr/lib/python3/dist-packages \
  hatch run pytest tests/unit/specfact_backlog/unit/test_add_command_ado_provider_fields.py -q
```

Result:

- `5 passed in 0.29s`

GitHub provider override regressions:

```bash
PYTHONPATH=/home/dom/git/nold-ai/specfact-cli/src:/home/dom/.local/lib/python3.11/site-packages:/usr/lib/python3/dist-packages \
  hatch run pytest tests/unit/specfact_backlog/unit/test_add_command_github_provider_overrides.py -q
```

Result:

- covered in the combined `27 passed` run above

OpenSpec validation:

```bash
openspec validate fix-backlog-provider-required-field-mappings --strict
```

Result:

- `Change 'fix-backlog-provider-required-field-mappings' is valid`

## Outstanding Environment Issue

Resolved in this worktree by installing the sibling `specfact-cli` checkout into `.venv`, then rerunning the repo gates normally.

## Full Gate Evidence

Completed in the required order:

- `hatch run format`
- `hatch run type-check`
- `hatch run lint`
- `hatch run yaml-lint`
- `hatch run check-bundle-imports`
- `hatch run verify-modules-signature --require-signature --enforce-version-bump`
- `hatch run contract-test`
- `hatch run smart-test`
- `hatch run test`

Final results:

- `type-check`: `0 errors, 0 warnings, 0 notes`
- `contract-test`: `212 passed, 16 skipped`
- `smart-test`: `212 passed, 16 skipped`
- `test`: `212 passed, 16 skipped`
