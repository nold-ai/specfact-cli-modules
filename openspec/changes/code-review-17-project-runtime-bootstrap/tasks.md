# Tasks for code-review-17-project-runtime-bootstrap

The full-change checklist remains pending beyond the explicitly bounded checkpoint below. The first Hatch milestone does not complete this change, migrate ordinary consumers or establish installed/release acceptance.

## Readiness and specification

- [ ] Refresh hierarchy metadata and verify current parent, labels, assignee, project, direct blockers and no concurrent In Progress owner.
- [ ] Verify the current modules/core baseline and released prerequisites; review the canonical change-17 design and paired artifacts.
- [ ] Revalidate this change strictly and finalize only owner-authorized scenario/interface refinements before behavior changes.

## Tests before production changes

- [ ] Add meaningful behavior tests for independent customer interpreter selection and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for faithful external sidecar preparation and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for single project execution owner and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for preparation failure and reuse are explicit and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for portable inspection and bootstrap commands and every named positive/negative scenario.
- [ ] Execute the tests against the prior behavior and record genuine failing commands, timestamps and causes in TDD_EVIDENCE.md before production edits.

## Bounded implementation

- [ ] Implement the shared project inspection/preparation/execution boundary in Codebase using adapted discovery and manager knowledge.
- [ ] Prove existing and cold detached Hatch execution with different controller/project Python and actual project check results before broadening adapters.
- [ ] Add faithful pip/pip-tools, locked uv and Poetry preparation; migrate framework sidecar runtime ownership without changing its explicit framework workflow.
- [ ] Run scenario and regression checks after each bounded unit; record actual passing commands, timestamps, results and exact source/environment identities in TDD_EVIDENCE.md.

## Review, release and finalization

- [ ] Run applicable formatting, type, lint, import, contract, test, security and SpecFact review gates; resolve findings including warnings or record an explicitly approved exception.
- [ ] Revalidate OpenSpec and requirement mappings and update affected help/reference/installation documentation.
- [ ] Apply required semver, CHANGELOG.md, compatibility, module payload/signature and canonical publication steps only when runtime assets change.
- [ ] Demonstrate the exact installed user workflow and rollback for the owning scope; keep unavailable cells and required failures nonaccepting.
- [ ] Submit implementation for normal review to dev, reconcile issue/project state and archive only after actual completion using openspec archive.

## Authorized first Hatch checkpoint, 2026-10-23

- [x] Confirm owner takeover, public hierarchy/dependencies and the bounded existing/cold trusted-local use case.
- [x] Preserve the real legacy wrong-interpreter RED before production and retain later genuine constraint/default-discovery RED evidence.
- [x] Implement the Codebase-owned detached Hatch execution capability without changing public review or legacy sidecar consumers.
- [x] Prove existing and cold target Python 3.11.15 from controller 3.12.13, actual imports/entrypoint/native async tests/customer lint/seeded failure, immutable declarations and inventory.
- [x] Reconcile exact mapped executable selectors with genuine independent local technical acceptance and actual JUnit through the canonical Requirements lifecycle using the honest legacy-TDD transition record.
- [x] Complete bounded independent implementation review and resolve its three reproduced corrections. Required SpecFact and CodeRabbit review prerequisites remain separate open gates.
- [ ] Finish all mandatory quality gates and retain any incomplete review prerequisites explicitly.
- [ ] Complete remaining native script/context fidelity, other managers, consumer migrations and full change-17 acceptance before archive.
