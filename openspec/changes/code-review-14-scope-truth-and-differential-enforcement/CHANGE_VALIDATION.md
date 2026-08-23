# Change Validation

## Status

`IMPLEMENTED — PROTECTED RELEASE EVIDENCE IN PROGRESS`

The public scope semantics, report truth model, red-test names, implementation boundary, migration, benchmark, and rollback are implemented with tests-first evidence in `TDD_EVIDENCE.md`. Task 4.3 remains incomplete until the protected Linux matrix proves signed-registry cache miss, network-forbidden cache hit, and empty-root Bubblewrap boot on every supported Python version; `pr_range` promotion remains owned by the later protected core consumer in task 4.7.

The approved compatibility dependency is immutable lightweight core tag `v0.55.1`, full commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276`, full tree `47984be5434d7ae65ed6908bf525a32053290337`, and strict specifier `===0.55.1`.

On 2026-08-21, fresh refs established `origin/dev@e3a20f20df440dff49f8c6d1f73375451bea1d8c`; its `module_discovery.py`, `module_installer.py`, and `module_package.py` trust surfaces are byte-identical to `v0.55.1`. The tag already provides `DiscoveredModule`, canonical install roots, registry/install-verification marker files, parsed package integrity, bundled-key lookup, and artifact verification. C14 therefore derives `core-v0.55.1-installed-module-handoff-v1` from those surfaces and does not depend on a later unreleased core interface or a new aggregate loader DTO. Pre-release candidate provenance is separately tagged and cannot satisfy official-install or protected `pr_range` provenance. The immutable OCI base root remains distinct from the signed post-base bootstrap/composite capsule identity.

All active proposal/design/spec/task/requirements/checkpoint/evidence artifacts were amended consistently, the internal scope-truth source and graph were rebuilt, and `hatch run openspec validate code-review-14-scope-truth-and-differential-enforcement --strict` passed on 2026-08-21. The amended 3.12e boundary is ready for new named-test authoring; its prior green evidence is superseded and cannot authorize production edits for the new behavior.

Public implementation issue [#416](https://github.com/nold-ai/specfact-cli-modules/issues/416) exists with verified native hierarchy and project metadata. The accepted contract was revalidated against synchronized `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b`, the immutable core benchmark/caller refs were inspected, and `hatch run openspec validate code-review-14-scope-truth-and-differential-enforcement --strict` passed on 2026-08-19. The change may proceed only in the tests-first/checkpoint order recorded in `tasks.md`.
