# TDD Evidence

## Planning checkpoint — 2026-08-13

No behavior changed and no tests ran for this OpenSpec-only planning commit. Core PRs #665–#671 are future adjudicated benchmark cases, not evidence that this change is implemented.

## Dependency amendment — 2026-08-19

The approved exact-core target changed from the unavailable planned 0.56.0 identity to existing immutable lightweight tag `v0.55.1`, full commit `b1e517e60e669eaba15a18ecfa83ef5a9df65276`, full tree `47984be5434d7ae65ed6908bf525a32053290337`, and strict `===0.55.1`. Live tag lookup and local commit/tree inspection established those identities. No test or source evidence is claimed by this planning amendment.

## Implementation readiness — 2026-08-19

### GitHub governance observation

- Observation: `2026-08-19T22:20:58+02:00` (`2026-08-19T20:20:58Z`).
- Hierarchy cache: `.specfact/backlog/github_hierarchy_cache.md`; state `generated_at=2026-08-19T20:10:14Z`, fingerprint `25ab587f47f83db25875a1b67cbc5094cd6a375dc4c3212bec8992e232240748`; the mandated refresh reported the unchanged 24-issue hierarchy, followed by live issue readback.
- Implementation issue: [nold-ai/specfact-cli-modules#416](https://github.com/nold-ai/specfact-cli-modules/issues/416), `OPEN`, User Story, parent Feature [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under Epic [#162](https://github.com/nold-ai/specfact-cli-modules/issues/162).
- Project: `SpecFact CLI`, status `Todo`; assignee `djm81`; labels `change-proposal`, `codebase`, `enhancement`, `openspec`.
- Native dependencies: `blockedBy=[]`; `blocking=[]`. The accepted planning PR #413 and synchronization PR #415 are complete. No core adoption issue exists yet by design; it is downstream of the signed module handoff. Requirements R07/R08 are independent.
- Metadata decision: `READY`.

### Immutable repository and benchmark refs

- Synchronized modules base: `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b`; implementation worktree HEAD is the same commit before readiness edits.
- Core: `origin/dev@e3a20f20df440dff49f8c6d1f73375451bea1d8c`; `origin/main@b1e517e60e669eaba15a18ecfa83ef5a9df65276`; immutable lightweight tag `v0.55.1` resolves to that main commit and tree `47984be5434d7ae65ed6908bf525a32053290337`.
- Core benchmark PR head identities: #665 `e3a20f20df440dff49f8c6d1f73375451bea1d8c`; #666 `1677f0c3beb32de49d82aa4dcf1bf4fcf06f07f0`; #667 `96aab447e00de4a09c19ed3a36632b9a46f7c222`; #668 `34c22d271e3653cfa7099ed7132d786c49437b21`; #669 `d17e6ba847599a1366436a3d3e993ba819cb0de7`; #670 `338f853ac2fde8299c11a5adb9c33ab883dead42`; #671 `21a97781ac3b467c2f69adc3344916d978d4328d`.
- Merged core reset PR #674 is `e3a20f20df440dff49f8c6d1f73375451bea1d8c` from reviewed head `51d3120170cd8e08e76881023e511868ce08d5b1`. Its accepted boundary keeps generic review-scope production semantics module-owned and makes the protected workflow consumer a separate downstream core adoption.
- Reviewed core caller paths at `origin/dev`: `.github/workflows/requirements-evidence.yml`, `scripts/pre_commit_code_review.py`, `scripts/pre-commit-quality-checks.sh`, `docs/agent-rules/20-repository-context.md`, and `docs/agent-rules/50-quality-gates-and-review.md`. The workflow currently derives positional PR paths, while the pre-commit helper intentionally remains staged explicit-file scope; these are migration consumers, not evidence that C14 already exists.

### Readiness decision

`READY FOR TEST AUTHORING`. `hatch run openspec validate code-review-14-scope-truth-and-differential-enforcement --strict` passed on 2026-08-19 against synchronized `origin/dev@c3eda08c732267dc3614130f5f36bcd473182d0b`. No named C14 tests or production sources have been edited or executed for implementation evidence yet. Production edits remain prohibited until every prescribed test is authored, every exact selector is collected, the implementation mapping and `IMPLEMENTATION_CHECKPOINT.json` are frozen, and actual failing evidence is recorded.
