# TDD Evidence: code-review-07-house-rules-skill

## Failing

Pre-fix behavior established from the reviewed branch state:

- `mirror_skill_to_ide_locations()` wrote the same raw `SKILL.md` payload into every
  IDE path, including `.cursor/rules/house_rules.mdc`
- The generated Cursor rule therefore lacked Cursor metadata such as
  `description` and `alwaysApply`
- The updater also wrote noncanonical mirrors into unsupported locations such as
  `.github/skills/`

Those behaviors are the failures captured by the review findings that triggered this
bugfix.

## Passing

Focused verification:

```bash
hatch run pytest tests/unit/specfact_code_review/rules/test_updater.py -q
```

Result:

- `18 passed in 0.55s`

Type-check verification:

```bash
hatch run type-check
```

Result:

- `0 errors, 0 warnings, 0 notes`

Additional regression fix:

- `tests/unit/specfact_code_review/tools/test_semgrep_runner.py` was failing because
  semgrep `1.144.0` hung in its post-scan version-check path when `--json` output was
  captured by the runner subprocess.

Focused verification:

```bash
hatch run pytest tests/unit/specfact_code_review/tools/test_semgrep_runner.py -q
```

Result:

- `14 passed in 18.33s`

Contract-test verification:

```bash
hatch run contract-test
```

Result:

- `330 passed in 33.14s`
