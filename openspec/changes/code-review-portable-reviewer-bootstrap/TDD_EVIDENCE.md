# Reviewer bootstrap evidence — 7 October 2026 (Europe/Berlin)

Owner explicitly approved preparation of a separate reviewer-update PR for human
merge/promotion. It covers the verified explicit-test selection bug and tested
Pylint optimization and the subsequently verified retired CI installation pin. No release is published, installed authenticated
reviewers are unchanged, and #498 exact sealed acceptance remains pending.

## Specification → RED → implementation → GREEN

The active specification and planned requirements mapping preceded code.
Before implementation, all 17 focused selection/cache cases failed (0.61 s)
because explicit source matches remained ambiguous and the cache was absent.
Private local log: /private/tmp/specfact460-bootstrap-red.log.
The first parity comparison exposed identity-only SuccessiveLinesLimits equality;
its test now compares every hash key/file/index/window and start/end bound rather
than requiring independently allocated upstream objects to be identical.

The 17 cases then pass alongside the existing portable-worker and target-launch
regressions: 149 passed (9.28 s). Additional full RuntimeRun coverage passes:
all messages (including real R0801), every statistics field and exit status match
uncached execution. All 18 focused bootstrap cases pass; together with existing portable-worker and
target-launch regressions, the final focused suite passes 150 cases (8.09 s). The cache computes each
of four immutable windows once rather than repeating for each pair; minima,
disabled-line filtering, eviction and RuntimeError/SystemExit teardown remain
covered. This is correctness/operation-count evidence, not sealed timing acceptance.

Format, typing (zero errors/warnings), lint (10.00/10), manifests/import boundaries,
publish precheck, 28 contracts and strict OpenSpec validation pass. Pinned Semgrep
1.144.0 reports zero findings/errors on the three changed Python files. Direct
AST, AI-bloat and Radon checks also report zero findings. The reviewer agent found
no defect in the narrow implementation; it explicitly retained sealed timing as
pending. SMART: 5,009 passed / 75 declared native or maintainer skips / 95 subtests,
5 existing fork warnings (261.97 s). Full: 5,010 passed / 75 declared skips / 95 subtests / 5 existing warnings
(298.76 s). The additional wrapper test accounts for the count difference;
Final SMART: 5,010 passed / 75 declared skips / 95 subtests / 5 existing
warnings (274.60 s). Normal hooks pass with local capsule review explicitly
DEFERRED; staged planned requirements pass without claiming implementation
acceptance. Required exact-head hosted review remains pending.

Code Review is prepared as 0.51.1 from released dev 0.51.0. Checksum refresh removes
both local private-signing environment variables. Explicit repository public-key
filesystem/version verification passes seven manifests; this changed module is
unsigned pending the CI signature-only follow-up. Existing modules are verified,
not waived due to a fresh worktree's missing public-key configuration.

The prior owner-approved ARM64 Darwin feature-worktree exception is reused:
SPECFACT_CODE_REVIEW_DEFER_TO_CI=github-linux defers only local capsule review,
reports DEFERRED, and requires exact-head GitHub Linux acceptance. Every other
normal hook executes. No gate, deadline, analyzer or rule is suppressed.

## Promotion and rollback

Prepare a draft PR for human review. No automatic merge/publication, fabricated
registry archive identity, issue closure or OpenSpec archive. After independently
authorized reviewer promotion, rebase #498 and bump it to 0.51.2 before obtaining
fresh exact-head installed/sealed acceptance. Rollback uses a corrective module
release while immutable historical artifacts and Linux support are retained.


Supplementary actual #498 workload: all75Python files are reviewed with pinned
Pylint4.0.7 and the same project configuration. One fresh uncached process takes
17.303s and the cached process16.369s, with identical870message counts,
statistics and exit30. Non-R0801 diagnostics are exactly equal. Seven R0801
messages vary; a second unchanged uncached process also varies (19.480s), so
cross-process raw duplicate text is not a parity oracle. On the exact same75
LineSet objects, both full duplicate groups and ordered locations compare equal:
two uncached pair passes6.343s versus cached0.771s,75hash misses/11025hits.
The regression wrapper fixture also preserves complete messages/statistics/exit.
These host measurements do not establish sealed Linux30-second acceptance.


Draft PR#499 is created. CI bot commit72310f2fc210aa6c70c4e6faa6f6a0a8db073216
adds only the Code Review manifest signature; its source checksum remains
21f6686ae2f3d25479a866b0e7b371b8826fbd662332a5f7422182f2c3f91fa2. After
inspecting that exact one-line diff, ff-only incorporation and explicit public-key
--require-signature filesystem/version readback pass all seven modules. This
human follow-up starts normal exact-head CI; no signed payload bytes change.

CodeRabbit's public committed review reports a minor suggestion to restrict
explicit tests to the default discovered candidate set. That restriction would
remove legitimate explicit pytest files outside testpaths. Correspondence already
intersects the discovered matches, so a non-candidate cannot waive ambiguity:
(matches & explicit) equals (matches & (explicit & candidates)) because every
match is in candidates. Preserve the old explicit-file semantics; the existing
unrelated-match regression still rejects unresolved ambiguity. No code change
is warranted by that suggestion. The public committed review completed; this suggestion is independently non-actionable.


## Verified independent-installation CI correction

Normal head c3c27ef986061d712c00caf72677f30baf466a7c run37684791456
failed before analysis: the independent installation step requested marketplace
0.50.1, which is absent from the registry. Use signed released0.51.0, retaining
its ordinary-user authenticated installation route and unchanged budgets.
The updated pin assertion and fake CLI first failed:2failed/18passed
(6.77s), private log /private/tmp/specfact460-bootstrap-pin-red.log.
The three SMART exit-propagation regressions then failed against the old single
portable entry point, before implementing required host-first execution; private
log /private/tmp/specfact460-bootstrap-host-entry-red.log.

Reuse the owner-approved context separation rather than editing the immutable
baseline proof file:19 required host cases pass(5.92s), and the nine portable
structural cases plus21 bootstrap cases pass(0.53s). The bounded read-only agent
verified all55 original assertions retained, baseline bytes equal origin/dev,
no new package markers, unchanged runtime corrections, and installed0.51.0
selecting only portable test modules. Both required host and portable failing
exits propagate; no proof is waived. Logs remain private. Final suite and
quality results are recorded below after completion.

Final correction quality gates: format, typing(0errors/0warnings), lint10.00/10,
manifests, import boundaries, strict seven-module signatures, strict OpenSpec,
actionlint,28contracts and30 focused cases pass. Direct AST/AI-bloat/Radon report
zero findings. Pinned Semgrep reports zero changed-line findings; its two
print-in-src observations are byte-identical baseline SMART status/check prints
shifted by11lines, explicitly compared against origin/dev. Full test execution
passes19 required host cases then5002portable cases/75declaredskips/95subtests/
5existingwarnings(260.49s). Final SMART also passes19required host cases then5002portable cases/75declaredskips/95subtests/5existingwarnings(265.77s). Staged planned requirements pass.

The earlier c3c head candidate3.12 receipt fails closed before analysis during
offline installation:namespace_unavailable (loopback RTM_NEWADDR denied). It
contains no completed analyzer evidence, so it cannot establish clean results.
No namespace policy or budget is changed; fresh CI will run on the pin correction.
