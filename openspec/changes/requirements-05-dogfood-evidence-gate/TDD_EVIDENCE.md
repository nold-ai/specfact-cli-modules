# TDD Evidence — requirements-05-dogfood-evidence-gate

## Failing before implementation

- 2026-07-25 (Europe/Berlin):
  `hatch run pytest tests/unit/scripts/test_requirements_evidence_gate.py -q`
- Result: failed during collection with `ImportError: cannot import name
  'requirements_evidence_gate' from 'scripts'`. The contract tests require the
  new adapter to produce auditable passed, failed, and skipped verdicts, but no
  adapter module existed.
- 2026-07-25 (Europe/Berlin):
  `hatch run pytest tests/unit/workflows/test_requirements_evidence_workflow.py -q`
- Result: 2 failed with `FileNotFoundError` for
  `.github/workflows/requirements-evidence.yml`. The workflow contract requires
  a paired-core PR check that retains failed JSON evidence and then enforces the
  verdict, but no workflow existed.
- 2026-07-25 (Europe/Berlin):
  `hatch run pytest tests/unit/scripts/test_requirements_evidence_gate.py -q`
- Result: 2 failed because the initial adapter had no
  `requirements-evidence.yaml` overlay or sidecar validation. Native OpenSpec
  imports cannot supply downstream test links directly, so a strict gate would
  otherwise remain permanently red.
- 2026-07-25 (Europe/Berlin):
  `hatch run pytest tests/unit/scripts/test_requirements_evidence_gate.py -q`
- Result: 3 failed after the first sidecar smoke run showed that a core
  `unsupported-profile-field` informational count was treated as blocking. The
  revised contract retains informational counts while only error-level findings
  affect the verdict.

## Passing after implementation

- 2026-07-25 (Europe/Berlin):
  `hatch run pytest tests/unit/scripts/test_requirements_evidence_gate.py tests/unit/workflows/test_requirements_evidence_workflow.py -q`
- Result: 11 passed. This covers passed, failed, and skipped verdicts; source
  discovery; artifact-before-failure ordering; valid and invalid evidence
  sidecars; informational findings; paired-core CI setup; summary publication;
  and always-uploaded failure evidence.
- 2026-07-25 (Europe/Berlin): user-scope SpecFact CLI 0.53.2 direct smoke
  against `requirements-05-dogfood-evidence-gate`.
- Result: passed. The native source imported two requirements, sidecar links
  produced `with_test_links: 2/2`, validation status was `passed`, and the
  retained `unsupported-profile-field` count was informational only. This is
  traceability evidence, not proof of executed tests.

## Quality evidence

- 2026-07-25 (Europe/Berlin): focused test and workflow contract:
  `hatch run pytest tests/unit/scripts/test_requirements_evidence_gate.py
  tests/unit/workflows/test_requirements_evidence_workflow.py -q`.
- Result: 11 passed.
- 2026-07-25 (Europe/Berlin): `hatch run type-check`, changed-file
  `ruff format --check`, `hatch run yaml-lint`, and strict OpenSpec validation.
- Result: passed. The repository-wide lint command is currently blocked by five
  pre-existing, unrelated documentation examples that its formatter would
  rewrite; those files are intentionally excluded from this change.
- 2026-07-25 (Europe/Berlin): `hatch run pytest
  tests/unit/docs/test_docs_review.py -q`, `hatch run contract-test`, and
  `hatch run verify-modules-signature --payload-from-filesystem
  --enforce-version-bump --allow-missing-public-key`.
- Result: passed (20 documentation tests, 28 contract tests, and 7 module
  manifests) before review remediation.
- 2026-07-25 (Europe/Berlin): staged SpecFact code review of the adapter and
  its two focused test files.
- Result: passed with 0 findings.
- 2026-07-25 (Europe/Berlin): `hatch run smart-test` was attempted.
- Result: the suite reaches existing Requirements integration failures because
  the local Hatch environment resolves the sibling core checkout at 0.52.3 on
  Python 3.14. This is not the CI runtime for this workflow, which pins Python
  3.12 and resolves the paired core from `dev`; the compatible user-scope
  0.53.2 smoke above is the local runtime evidence for the adapter.

## Review remediation

- 2026-07-25 (Europe/Berlin): PR #353 review remediation added regression
  tests for repository-contained sidecar links (including symlink escapes),
  enterprise-profile gate counts, and JSON/Markdown evidence persistence when
  discovery raises.
- Failing evidence: the new tests failed before implementation for traversal
  acceptance, profile omission, and uncaught `CalledProcessError`.
- Passing evidence: `hatch run pytest
  tests/unit/scripts/test_requirements_evidence_gate.py
  tests/unit/workflows/test_requirements_evidence_workflow.py -q` reported 14
  passed. A follow-up regression for option-like Git base refs brought the
  focused total to 15 passed; targeted Requirements command-app tests reported 3 passed; and
  `hatch run type-check` reported 0 errors.
- 2026-07-25 (Europe/Berlin): paired-core CI failed its command-overview step
  under Typer 0.27 because the pre-existing Requirements command used
  `click.Context` as a Typer callback parameter. The command now uses
  `typer.Context`, and the Requirements module was bumped from 0.2.5 to 0.2.6
  with the repository's explicit unsigned signing mode. Registry artifact and
  checksum metadata were regenerated; GitHub signing remains the production
  signing authority.
- Post-remediation quality: scoped Ruff format/lint, YAML validation, strict
  OpenSpec validation, bundle import checks, signature/version verification,
  registry-tooling tests (7 passed), and module contract tests (28 passed)
  succeeded.
- The changed-line SpecFact code review was rerun after the remediation and
  completed with 0 findings.

## CI artifact remediation

- 2026-07-25 (Europe/Berlin): Docs Review reported stale command artifacts.
  Investigation showed its test suite used the old pins in
  `requirements-docs-ci.txt` (CLI 0.46.2 and Typer 0.23.1), while the later
  Hatch command-overview check installed the paired core (CLI 0.53.5 and Typer
  0.27.0). The two runtimes produced incompatible generated command metadata.
- Remediation: Docs Review now installs the checked-out paired core editable
  in both the runner environment for its direct Python test suite and Hatch's
  default environment for later command-overview checks, so each uses the same
  paired core revision. The independent tooling pins now match the paired core's
  Click, Typer, and Rich dependency versions; regenerated
  `docs/reference/commands.generated.{json,md}` and `llms.txt` using that
  shared runtime. Direct `--check` and the 25 focused Docs Review tests pass;
  the GitHub rerun remains the final proof.

## Generated command-contract remediation

- 2026-07-25 (Europe/Berlin): with the unified runtime, the generated command
  contract correctly reached `specfact code import` and `specfact code repro`.
  Their bare invocations emit bundle-validation guidance before subcommand
  dispatch, but generated metadata incorrectly classified both as requiring a
  subcommand. The initial regression test failed with
  `requires-subcommand` for each command.
- Remediation: the overview generator now records those runtime-validated
  groups as `executes`; regeneration updates the two metadata records.
  Passing evidence: the regression, focused Docs Review and workflow tests
  reported 28 passed, and `scripts/check-command-contract.py` validated all 91
  generated module command paths.
- The quality matrix then exposed a Typer result-type compatibility issue in
  the backlog test fixture. `click.testing.Result` is the stable public type
  across the Typer 0.23 and 0.27 test runners; the paired-core type check
  reported 0 errors after restoring that import.

## Typer 0.27 full-suite remediation

- 2026-07-25 (Europe/Berlin): the full quality matrix failed 8 tests under
  the paired 0.53.5 / Typer 0.27 runtime. Six Requirements import tests
  failed because Beartype validates the injected Click context against
  `typer.Context`; the remaining two asserted Typer 0.23-specific help and
  error wording.
- Remediation: retained `typer.Context` as Typer's recognised callback type
  while excluding the framework-injected context from Beartype validation;
  command inputs remain covered by Icontract preconditions and postcondition.
  The help and shared-error tests now assert the stable semantic contracts,
  accepting the documented Typer 0.27 rendering.
- Passing evidence: after restoring the paired `specfact-cli 0.53.5`,
  `Typer 0.27.0`, and `Click 8.4.2` runtime, the focused Requirements,
  global CLI, backlog, generator, Docs Review, and workflow suite reported
  39 passed; `scripts/check-command-contract.py` validated all 91 generated
  module command paths; and the repository type check reported 0 errors.
- The final staged changed-line SpecFact review completed with 0 findings.

## Follow-up review remediation

- 2026-07-25 (Europe/Berlin): a new Docs Review workflow assertion first
  failed because the paired core was installed only in the runner interpreter,
  while command-overview checks run through Hatch. The workflow now installs
  the paired core in both environments; focused docs/workflow and CLI error
  contract tests reported 37 passed, with manifest validation and generated
  command checks passing.
- The shared CLI error contract now accepts either the explicit
  `missing subcommand` diagnostic or Typer's concrete
  `COMMAND [ARGS]...` usage form, rather than a generic command-list heading.

## Main-release review remediation

- 2026-07-26 (Europe/Berlin): new P1 regressions first failed because the
  requirements-evidence workflow installed only the paired core CLI, and source
  discovery excluded deleted paths with `--diff-filter=ACMR`. The focused
  workflow and adapter suite reported 2 failures.
- Remediation: the Hatch environment now installs
  `packages/specfact-requirements` before the adapter runs; discovery uses
  `--diff-filter=ACMRD` but still evaluates only active change directories
  present in the checkout. Passing evidence: the focused suite reported 15
  passed, and manifest validation passed.

## Missing-subcommand contract remediation

- 2026-07-26 (Europe/Berlin): the tightened global CLI contract first failed
  because bare `specfact code` displayed help without an explicit missing
  subcommand diagnostic.
- Remediation: the aggregate code command now uses Typer's explicit
  no-subcommand error behavior. The test reads combined CLI output so it
  verifies the error emitted on stderr, and the generated command checker
  accepts both stable explicit diagnostics (`missing subcommand` and
  `missing command`). Passing evidence: the focused global CLI tests passed
  and `check-command-contract` validated all 91 generated command paths.

## Production-stability repair

- 2026-07-26 (Europe/Berlin): PR #360 exposed that the workflow tried to run
  `pip install -e packages/specfact-requirements`, although that module bundle
  directory has no `pyproject.toml` or `setup.py`. Setup stopped before the
  adapter could create its required evidence artifact.
- Failing-before: the expanded workflow contract reported two failures: it
  detected the invalid editable install and the missing `setup-unavailable`
  fallback guarantee.
- Repair: the workflow now uses repository-local `PYTHONPATH` roots for the
  Requirements module and its direct project dependency, and delegates
  setup/adapter fallback artifact creation to the standard-library-only
  `requirements_evidence_fallback.py` helper.
- Passing-after: focused fallback, adapter, and workflow tests reported
  `17 passed`; YAML validation and strict OpenSpec validation passed.
- Runtime proof: invoking the adapter with the workflow's exact source-root
  environment produced a `passed` verdict; invoking the fallback with
  `setup-unavailable` produced a machine-readable failed report and Markdown
  summary. Local artifacts are under `/private/tmp/requirements-evidence-ci.lcreX0/`.
