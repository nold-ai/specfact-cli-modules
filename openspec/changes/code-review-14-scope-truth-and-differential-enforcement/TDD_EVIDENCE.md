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

## Frozen implementation red gate — 2026-08-20

- Committed checkpoint: implementation branch commit `67f1aa0a879931c3098792747b12c8c115750e73`; checkpoint parent commit `dd7490f5a1829dc9fb5b411a33eaa68e97e9c947`, tree `20e6827ae49b62a7524587985cb91df544e20dd3`.
- Verification command: `.venv/bin/python /private/tmp/verify_c14_checkpoint.py`. It verified the committed checkpoint against the frozen parent inputs, the non-empty and pairwise-disjoint 43-item assignment, exact global union, canonical mapping, immutable core identity, and all checkpoint digests.
- Red command: `.venv/bin/python /private/tmp/run_c14_red.py`. The runner loaded the checkpoint's sorted 366 `pytest_args`, invoked that complete selector set without substitution, and rejected collection drift. The per-selector exact argv is therefore bound by the committed selector digest rather than duplicated in this evidence file.
- Checkpoint file digest: `sha256:fb51280c67ea97962fce0af31227335bc00e0128cb4c30706294df3cf09ec7a6`.
- Global selector and observed collection digest: `sha256:7e515d42b9b267eb503bdb98e0d73feae0293e13660ad88f826f055cbd907b68`; collected count `366`.
- Implementation selector-map digest: `sha256:7f9a49abb646f5cc714ff2a1986503c868b4914ab3fbbc9479ec45d9380ee4e5`.
- Pytest raw exit code: `1`. Exact outcomes: `365 failed`, `1 passed`; all `43/43` implementation tasks retained at least one independently failing frozen selector.
- Canonical per-selector outcomes digest: `sha256:99e9392aa548da1aaf2a2c5feeb4cf2a2727e1a134bf7171f63d888c7d53be4b`; canonical per-task outcomes digest: `sha256:aaa7c5a1851afdba13e3578e94805933235818341ff5c88b2c526242c6346391`.
- Representative red causes were the deliberately absent `scope`, `differential`, `sandbox`, and `toolchain` modules and the unimplemented schema/profile behavior in existing allowlisted sources. The single passing selector does not invalidate the gate because its mapped task also contains failing selectors and no Section 3 item is green.

Decision: `RED GATE SATISFIED`. Production edits may begin only in the frozen Section 3 order and allowlist, with the checkpoint reverified and each item's identical mapped selector set taken from red to green.
