# sidecar-route-extraction Specification

## Purpose
TBD - created by archiving change code-review-bug-finding-and-sidecar-venv-fix. Update Purpose after archive.
## Requirements
### Requirement: Framework extractors exclude .specfact from scan paths

All sidecar framework extractors (FastAPI, Flask, Django, DRF) SHALL exclude
`.specfact/` directories from Python file discovery. This prevents the sidecar's
own installed venv and workspace artefacts from being scanned as application
source.

#### Scenario: FastAPI extractor ignores .specfact/venv

- **GIVEN** a repo with a `.specfact/venv/` directory containing FastAPI source
- **WHEN** the FastAPI extractor runs route extraction on that repo
- **THEN** no routes are extracted from files under `.specfact/`
- **AND** only routes from application source files are returned

#### Scenario: Flask extractor ignores .specfact/venv

- **GIVEN** a repo with a `.specfact/venv/` directory containing Flask source
- **WHEN** the Flask extractor runs route extraction on that repo
- **THEN** no routes are extracted from files under `.specfact/`

#### Scenario: Django extractor ignores .specfact/venv

- **GIVEN** a repo with a `.specfact/venv/` directory containing Django source
- **WHEN** the Django extractor runs route extraction on that repo
- **THEN** no routes are extracted from files under `.specfact/`

#### Scenario: Other standard exclusions also apply

- **WHEN** any framework extractor scans a repo
- **THEN** files under `.git/`, `__pycache__/`, and `node_modules/` are also excluded
- **AND** legitimate application source outside these directories is not affected

#### Scenario: Route count reflects real application routes only

- **GIVEN** gpt-researcher repo with 19 real FastAPI routes and `.specfact/venv` installed
- **WHEN** sidecar validation runs route extraction
- **THEN** routes extracted is approximately 19, not 25,947

