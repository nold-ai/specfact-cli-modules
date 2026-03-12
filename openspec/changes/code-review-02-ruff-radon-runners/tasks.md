# Tasks: code-review Ruff and Radon runners

## 1. Review upstream scope

- [x] 1.1 Review `specfact-cli` change `code-review-02-ruff-radon-runners`
- [x] 1.2 Confirm bundle-side `ReviewFinding` and `ReviewReport` models already exist

## 2. Write tests before implementation

- [x] 2.1 Add `tests/unit/specfact_code_review/tools/test_ruff_runner.py`
  - [x] 2.1.1 Map `S*` rules to `security`
  - [x] 2.1.2 Map `C9*` rules to `clean_code`
  - [x] 2.1.3 Map `E/F/I/W*` rules to `style`
  - [x] 2.1.4 Exclude findings outside the provided file list
  - [x] 2.1.5 Convert parse errors to `tool_error`
  - [x] 2.1.6 Convert missing-tool failures to `tool_error`
  - [x] 2.1.7 Detect fixable findings from Ruff JSON
- [x] 2.2 Add `tests/unit/specfact_code_review/tools/test_radon_runner.py`
  - [x] 2.2.1 Complexity 13 returns `warning`
  - [x] 2.2.2 Complexity 16 returns `error`
  - [x] 2.2.3 Complexity 12 or below returns no finding
  - [x] 2.2.4 Exclude findings outside the provided file list
  - [x] 2.2.5 Convert parse errors to `tool_error`
- [x] 2.3 Run targeted tests and record failing evidence in `TDD_EVIDENCE.md`

## 3. Implement runners

- [x] 3.1 Add `packages/specfact-code-review/src/specfact_code_review/tools/__init__.py`
- [x] 3.2 Implement `ruff_runner.py` with `@require`, `@ensure`, and `@beartype`
- [x] 3.3 Implement `radon_runner.py` with `@require`, `@ensure`, and `@beartype`

## 4. Verify behavior and repository quality

- [x] 4.1 Run targeted runner tests and record passing evidence in `TDD_EVIDENCE.md`
- [x] 4.2 Run `hatch run format`
- [x] 4.3 Run `hatch run type-check`
- [x] 4.4 Run `hatch run lint`
- [x] 4.5 Run `hatch run yaml-lint`
- [x] 4.6 Run `hatch run contract-test`
- [x] 4.7 Run `hatch run smart-test`
- [x] 4.8 Run `hatch run test`

## 5. Documentation

- [x] 5.1 Add `docs/modules/code-review.md` documenting Ruff mappings and Radon thresholds

## 6. Release metadata sync

- [x] 6.1 Publish matching registry artifact metadata for `specfact-code-review`
