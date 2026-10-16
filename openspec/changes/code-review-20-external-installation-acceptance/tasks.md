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

- [ ] Run actual pipx/uv tool/repeated-uvx installation acceptance with user-scoped module discovery on supported platforms/Pythons, including provisioned offline execution with networking disabled and the selected tools/cache present locally.
- [ ] Replace capsule-only customer/build/release CI with local installed acceptance while preserving independent gates.
- [ ] Prepare migration docs and coordinated breaking-major release/signing/compatibility changes after paired core acceptance.
- [ ] Run scenario and regression checks after each bounded unit; record actual passing commands, timestamps, results and exact source/environment identities in TDD_EVIDENCE.md.

## Review, release and finalization

- [ ] Run applicable formatting, type, lint, import, contract, test, security and SpecFact review gates; resolve findings including warnings or record an explicitly approved exception.
- [ ] Revalidate OpenSpec and requirement mappings and update affected help/reference/installation documentation.
- [ ] Finalize required semver, CHANGELOG.md, compatibility and signed immutable candidate assets when runtime assets change; rerun affected quality gates and the final full review after final documentation/version edits and substantive repairs before PR publication.
- [ ] Demonstrate the exact installed signed candidate workflow and rollback, and rerun paired core #769 compatibility plus required installed acceptance against those final identities; keep every required failure, timeout or unavailable cell nonaccepting.
- [ ] Submit implementation for normal review to dev, complete required CI/review repairs with fresh evidence and seek owner-authorized integration.
- [ ] Perform canonical stable publication of only the exact signed candidate identities that passed paired core #769 compatibility and required installed acceptance after reviewed integration; withhold publication on any required failure or timeout, then reconcile issue/project state and archive from the repository root only after actual completion using openspec archive.
