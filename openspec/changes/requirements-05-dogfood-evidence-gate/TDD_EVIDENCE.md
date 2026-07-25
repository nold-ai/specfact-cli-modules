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
