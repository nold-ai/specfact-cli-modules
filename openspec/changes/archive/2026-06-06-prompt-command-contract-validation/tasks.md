## 1. OpenSpec and Baseline

- [x] 1.1 Create the `prompt-command-contract-validation` OpenSpec change.
- [x] 1.2 Add proposal, design, and spec deltas for prompt validation, packaged resources, and resource integrity.
- [x] 1.3 Validate the change with `openspec validate prompt-command-contract-validation --strict`.

## 2. Tests First

- [x] 2.1 Add unit tests for prompt command extraction from fenced shell blocks, inline backticks, slash examples, comments, placeholders, and line continuations.
- [x] 2.2 Add unit tests for invalid command path and invalid option findings.
- [x] 2.3 Add unit tests that prompt files with executable command guidance must contain CLI reality-check/self-healing guidance.
- [x] 2.4 Run the new tests before implementation and record failing evidence in `TDD_EVIDENCE.md`.

## 3. Validator Implementation

- [x] 3.1 Add `scripts/check-prompt-commands.py` to discover mounted command paths/options and validate `packages/*/resources/prompts/**/*.md`.
- [x] 3.2 Add `hatch run validate-prompt-commands`.
- [x] 3.3 Keep validator output deterministic and line-addressed for pre-commit and CI logs.

## 4. Prompt Resource Repairs

- [x] 4.1 Update bundle prompts to use current mounted command paths and option names.
- [x] 4.2 Add concise CLI reality-check/self-healing guidance to executable bundle prompts and shared companion guidance.
- [x] 4.3 Preserve bundle-owned resource layout and avoid `.github/prompts` changes in this scope.

## 5. Local and CI Gates

- [x] 5.1 Run prompt command validation from `scripts/pre-commit-quality-checks.sh` before safe-change skipping.
- [x] 5.2 Add prompt validation triggers and a logged validation step to `.github/workflows/docs-review.yml`.
- [x] 5.3 Update `openspec/config.yaml` rules to require prompt validation for prompt resource changes.

## 6. Evidence and Finalization

- [x] 6.1 Run `openspec validate prompt-command-contract-validation --strict`.
- [x] 6.2 Run focused pytest coverage for the prompt validator.
- [x] 6.3 Run `hatch run validate-prompt-commands`.
- [x] 6.4 Run relevant quality gates for touched scripts, YAML, prompts, and signed resources.
- [x] 6.5 Record failing-before and passing-after evidence in `TDD_EVIDENCE.md`.
- [x] 6.6 Resolve SpecFact code review findings or document any explicit exception.
