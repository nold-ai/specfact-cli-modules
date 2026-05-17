# Code Review AI Bloat Detection

## ADDED Requirements

### Requirement: The code-review runner SHALL emit findings under a new `ai_bloat` principle category

The code-review pipeline SHALL recognise `ai_bloat` as a valid value of the `category` and `principle` fields on `ReviewFinding`. The new category SHALL surface in `.specfact/code-review.json` alongside the existing categories `naming | kiss | yagni | dry | solid | clean_code | architecture` without any schema migration of existing finding consumers. Findings under `ai_bloat` SHALL emit at `advisory` severity only; the runner SHALL never emit `ai_bloat` findings at `warning` or `error` severity in this iteration.

#### Scenario: Review run on a fixture with a manual-loop comprehension emits an ai_bloat finding

- **WHEN** `specfact code review run --json --out .specfact/code-review.json --scope full` runs against a fixture file containing a `for x in xs: out.append(...)` loop whose shape matches the `ai-bloat.manual-loop-comprehension` rule
- **THEN** the resulting JSON SHALL contain at least one finding whose `category` equals `ai_bloat`, `principle` equals `ai_bloat`, `severity` equals `advisory`, and whose rule ID is `ai-bloat.manual-loop-comprehension`
- **AND** the finding SHALL reference the source file path and the starting line of the matched loop

#### Scenario: Review run on the simplified equivalent emits no ai_bloat finding

- **WHEN** the same review command runs against a fixture file containing only the simplified comprehension equivalent
- **THEN** the resulting JSON SHALL NOT contain any finding with `category=ai_bloat` for that file

#### Scenario: Pre-commit hook does not block on ai_bloat findings

- **WHEN** the pre-commit hook at `scripts/pre_commit_code_review.py` runs and the resulting JSON contains `ai_bloat` findings at `advisory` severity but no findings at `error` severity
- **THEN** the hook SHALL exit with status zero
- **AND** the hook SHALL still print a human-readable summary of the `ai_bloat` findings to stderr so the user is aware before committing

### Requirement: A packaged semgrep rule pack SHALL detect pattern-shape AI bloat

The `specfact-code-review` bundle SHALL ship a semgrep rule pack at `resources/semgrep-rules/ai-bloat.yaml` containing detectors for `ai-bloat.manual-loop-comprehension`, `ai-bloat.passthrough-lambda`, `ai-bloat.identity-try-except`, `ai-bloat.none-then-none`, and `ai-bloat.single-call-wrapper`. The semgrep runner SHALL load this pack alongside the existing rule packs and SHALL map each new rule ID to `category=ai_bloat` in `SEMGREP_RULE_CATEGORY`.

#### Scenario: Each pattern-shape rule flags its bloated fixture

- **WHEN** the semgrep runner is invoked on a fixture file containing the bloated form for any of the five pattern-shape rules
- **THEN** the runner SHALL emit a finding for that file with the corresponding rule ID and `category=ai_bloat`

#### Scenario: Each pattern-shape rule ignores its simplified fixture

- **WHEN** the semgrep runner is invoked on a fixture file containing only the simplified equivalent
- **THEN** the runner SHALL NOT emit a finding under any of the five pattern-shape rule IDs for that file

### Requirement: A packaged AST runner SHALL detect semantic AI bloat

The `specfact-code-review` bundle SHALL ship an AST runner at `src/specfact_code_review/tools/ai_bloat_runner.py` implementing detectors for `ai-bloat.unused-optional-param`, `ai-bloat.dead-branch`, `ai-bloat.loc-vs-complexity`, and `ai-bloat.redundant-intermediate`. The runner SHALL be wired into the review orchestration so its findings flow into the same `ReviewFinding` stream as the other tool runners.

#### Scenario: Unused-Optional-param detector flags a parameter that is never tested for None

- **WHEN** the AST runner analyses a function whose signature includes a parameter annotated `Optional[T] = None` and whose body never references the parameter inside an `is None` or `is not None` check
- **THEN** the runner SHALL emit a finding with rule ID `ai-bloat.unused-optional-param` and `category=ai_bloat`

#### Scenario: LOC-vs-complexity detector flags long but linear functions

- **WHEN** the AST runner analyses a function with line count at or above the configured LOC floor and cyclomatic complexity at or below the configured complexity ceiling
- **THEN** the runner SHALL emit a finding with rule ID `ai-bloat.loc-vs-complexity` and `category=ai_bloat`

#### Scenario: Detectors are silent on idiomatic code

- **WHEN** the AST runner analyses a function whose `Optional` parameters all branch on `None`, whose branches are all reachable, whose LOC-to-complexity ratio is within thresholds, and whose intermediate variables either are read multiple times or carry naming clarity
- **THEN** the runner SHALL NOT emit any `ai_bloat` finding for that function

### Requirement: A dedicated policy pack SHALL register the new rules under `principle: ai_bloat`

The `specfact-code-review` bundle SHALL ship a policy pack at `resources/policy-packs/specfact/ai-bloat-patterns.yaml` with `pack_ref: specfact/ai-bloat-patterns`, `default_mode: advisory`, and one entry per rule ID listed above, each tagged `principle: ai_bloat`. The pack SHALL be parallel to `clean-code-principles.yaml` so adopters can enable or disable the two packs independently.

#### Scenario: Policy pack references only existing rules

- **WHEN** the contract test loads `ai-bloat-patterns.yaml`
- **THEN** every rule ID in the pack SHALL exist either in the semgrep rule pack `resources/semgrep-rules/ai-bloat.yaml` or as a detector emitted by `ai_bloat_runner.py`
- **AND** every rule entry in the pack SHALL specify `principle: ai_bloat`

### Requirement: An IDE slash-command prompt SHALL drive targeted rewrites

The `specfact-project` bundle SHALL ship a prompt resource at `resources/prompts/specfact.08-simplify.md` that drives an LLM-assisted rewrite workflow in the user's IDE. The prompt SHALL: read `.specfact/code-review.json`, filter findings where `category=ai_bloat`, group by file and then by rule ID, present each candidate with a rewrite hint, drive a per-change accept/reject/skip/explain loop, apply accepted edits via the IDE's edit tool, and suggest re-running the review afterwards. The prompt SHALL NOT edit files autonomously and SHALL NOT skip the per-change confirmation step.

#### Scenario: Slash command runs with no ai_bloat findings present

- **WHEN** the user invokes `/specfact.08-simplify` in an IDE session whose `.specfact/code-review.json` contains no findings with `category=ai_bloat`
- **THEN** the prompt SHALL report that there are no ai-bloat candidates and exit without modifying any files

#### Scenario: Slash command walks the user through findings with confirmation

- **WHEN** the user invokes `/specfact.08-simplify` and the JSON contains one or more `ai_bloat` findings
- **THEN** the prompt SHALL present each finding in turn with its source snippet, rule ID, and rewrite hint
- **AND** the prompt SHALL ask the user to accept, reject, skip, or request explanation before applying any edit
- **AND** the prompt SHALL apply only the edits the user accepts

## MODIFIED Requirements

### Requirement: The clean-code policy pack documentation SHALL note the parallel ai-bloat pack

The clean-code policy-pack documentation SHALL note that `ai-bloat-patterns.yaml` is a parallel policy pack with independent enable/disable semantics, an `advisory`-only severity model, and a dedicated `ai_bloat` principle category. The documentation SHALL state that adopting `clean-code-principles.yaml` does not automatically enable `ai-bloat-patterns.yaml` and vice versa.

#### Scenario: Documentation describes the two packs as independent

- **WHEN** a reader consults the clean-code policy-pack documentation
- **THEN** the documentation SHALL state explicitly that `ai-bloat-patterns.yaml` is a separate policy pack
- **AND** SHALL state that its severity model is `advisory`-only
- **AND** SHALL state that its principle category is `ai_bloat`, distinct from the existing six categories
