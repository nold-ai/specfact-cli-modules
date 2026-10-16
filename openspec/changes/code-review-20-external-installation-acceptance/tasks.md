# Tasks for code-review-20-external-installation-acceptance

All boxes are future implementation. This artifact delivery completes no runtime task and creates no RED/GREEN or installed-support evidence.

## Readiness and specification

- [ ] Refresh hierarchy metadata and verify current parent, labels, assignee, project, direct blockers and no concurrent In Progress owner.
- [ ] Verify the current modules/core baseline and released prerequisites; review the canonical change-17 design and paired artifacts.
- [ ] Revalidate this change strictly and finalize only owner-authorized scenario/interface refinements before behavior changes.

## Tests before production changes

- [ ] Add meaningful behavior tests for external installation survives fresh invocations and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for published compatibility follows installed evidence and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for ci replacement preserves independent gates and every named positive/negative scenario.
- [ ] Add meaningful behavior tests for coordinated release and rollback are explicit and every named positive/negative scenario.
- [ ] Execute the tests against the prior behavior and record genuine failing commands, timestamps and causes in TDD_EVIDENCE.md before production edits.

## Bounded implementation

- [ ] Run actual pipx/uv tool/repeated-uvx installation acceptance with user-scoped module discovery on supported platforms/Pythons.
- [ ] Replace capsule-only customer/build/release CI with local installed acceptance while preserving independent gates.
- [ ] Prepare migration docs and coordinated breaking-major release/signing/compatibility changes after paired core acceptance.
- [ ] Run scenario and regression checks after each bounded unit; record actual passing evidence and exact source/environment identities.

## Review, release and finalization

- [ ] Run applicable formatting, type, lint, import, contract, test, security and SpecFact review gates; resolve findings including warnings or record an explicitly approved exception.
- [ ] Revalidate OpenSpec and requirement mappings and update affected help/reference/installation documentation.
- [ ] Apply required semver, compatibility, module payload/signature and canonical publication steps only when runtime assets change.
- [ ] Demonstrate the exact installed user workflow and rollback for the owning scope; keep unavailable cells and required failures nonaccepting.
- [ ] Submit implementation for normal review to dev, reconcile issue/project state and archive only after actual completion using openspec archive.
