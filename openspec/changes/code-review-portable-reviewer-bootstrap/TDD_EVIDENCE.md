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


## Repeated namespace failure: bounded diagnosis — 2026-10-07 (Europe/Berlin)

Fresh8ee966a7 run37688067509 job113021549981 repeats the same verified
launcher a2ebece7de53332b15b956749a0a96b680a4298ebd57675c1e47bea96968f2c0
loopback RTM_NEWADDR denial during offline installation. All10analyzers are
ERROR/UNKNOWN with0findings; no completed analysis exists. Independent job
113021550037 passes corrected installation, then fails opaque preparation.
CP311/13 pass the repository fixtures and reach external-corpus execution.

Bounded source review finds no descriptor/profile-path mismatch or justified
capability-order remedy. Exit0preparation alone is inconclusive because index
NOT_APPLICABLE can return empty runtimes. Add required descriptor-presence
validation and bounded private failure/kernel projections; preserve all grants,
deadlines, original exits and descriptor launch binding. Four preparation, four
private-failure and three initial kernel-projection cases fail before programs
are added. Stale-record and numeric-name regressions cover the agent's two
diagnostic findings; exact prefix continuity and current/baseline capture success
resolve them. Rotation and failed capture also yield unavailable observations.
Final focused suite:19host+45portable/bootstrap cases pass(6.93s). Agent reports
no remaining diagnostic findings. Captured booleans are observations, not verified
launcher attribution, missing-denial proof or acceptance. Raw kernel logs, paths
and exception text remain runner-private. Full and SMART each pass19required host cases followed by5017portable cases,
75declared skips,95subtests and5existing warnings (260.19s/254.54s).
The full runs preceded the test harness-only replacement of exec with real
subprocess execution; the final focused64cases verify those exact programs.
Final typing reports0errors/0warnings; lint10.00/10, formatting, YAML, imports,
actionlint,28contracts and staged planned requirements pass. AST, AI-bloat,
Radon and pinned Semgrep report0findings/0errors in changed Python scope.
The signed runtime checksum is unchanged. Exact-head hosted review remains
required; these local passes do not establish namespace or sealed acceptance.

## Verified core CLI stdout correction — 2026-10-08 (Europe/Berlin)

Diagnostic head df790309 CP312job113035668519 reports both descriptors absent.
Kernel capture/prefix continuity succeed; all matching denial observations are
false. This new run stops before analysis, and cannot attribute the older failure.
Real core0.55.4 cli_main prints version/Started/Finished around JSON. An exact
clean-index invocation is invalid JSON while containing the scope object; direct
registered app invocation returns valid NOT_APPLICABLE JSON without acquisition.
Raw stdout/stderr remain private under /private/tmp/specfact460-index-*.

Specification precedes the decorated-core fixture and outcome cases. Before the
workflow correction:10failed/34passed (6.13s), private CLI-json RED log. After
using trusted app(args=...) with identical scope/config/environment/1800-second
bound:65focused host/portable/bootstrap cases pass (7.15s). Fixed outcomes and
supplied/present flags distinguish invalid JSON from not-applicable scope and
missing descriptor fields/files; no raw text/paths are published. Bounded reviewer
checks app registration/lazy-loading and retained admission/failure exits. Format,
type/lint/actionlint/OpenSpec, AST/AI-bloat/Radon and pinned Semgrep pass, with
zero changed Python findings. Full/SMART each pass19host cases followed by5018portable cases,75declared
skips,95subtests,5existing warnings (256.98s/249.49s). They collect before the
following eight new independent projection cases; final focused execution verifies
those programs separately. Normal hooks and fresh exact-head hosted review follow.

Independent df790309 job113035668532 fails after preparation returns0. Its old
final review command hides raw output and emits no preparation classifier, so
actual review cause is not yet known. The separate failure-only projector keeps
original exit/300-second budget and adds only bounded standard-library observations.
Eight projection regressions fail before adding it(0.53s), and eight identity
schema regressions fail before adding allowlisted analyzer IDs(0.58s). Both direct
and nested error/UNKNOWN, findings-only failure, missing/invalid/oversized reports,
timeout-marker observations and private-token/identity suppression are covered.
The early test CC13 warning is resolved with complete expected-object assertions,
retaining every field. Final focused73cases pass(6.93s), including the new independent projection cases.
Final typing0errors/0warnings, lint10.00/10, format/actionlint/strict OpenSpec,
AST/AI-bloat/Radon and pinned Semgrep0findings/0errors pass. The bounded agent
finds no defect and verifies fixed-ID suppression/nested observations and retained
exit/deadline/isolation. Normal hooks run at commit; exact-head hosted execution
remains required. Signed runtime bytes remain unchanged. Raw logs/reports
remain private; booleans/codes cannot establish attribution or acceptance.

## Remaining contracts failure: fixed observations — 2026-10-08 (Europe/Berlin)

Exact0485eaa5 run37694851883 CP312job113044012871 reports PREPARED with
both descriptors supplied/present. Kernel capture/prefix continuity succeed;
all matching denial observations are false. Contracts then reports incomplete
execution with exit1. Independentjob113044012853 gets past preparation and hits
its300-second wrapper with missing report and observed TimeoutExpired marker;
this does not attribute timeout to any analyzer. Original report is not retained
in uploaded artifacts, so the contract cause is still unknown.

Spec precedes six CrossHair-class regressions:6RED/33deselected(0.34s) before
projection code. Unknown-token privacy then fails6cases(0.47s) before replacing
permissive regex tokens with fixed controller/analyzer allowlists. The candidate
failure projector imports only standard library under-I, bounds raw report reads
to2MiB, emits at most10protocol rows and5deduplicated CrossHair classes with at
most6fixed exception observations. Tool/category filters suppress unrelated
findings. Original exits, all execution/grant/deadline settings and signed payload
are unchanged. Final79focused host/portable/bootstrap cases pass(7.02s); direct
AST/AI-bloat/Radon report0findings, and bounded agent review finds no defect.
Prior full/SMART5018passes predate these six diagnostic-only cases; focused
execution verifies all affected host recipes and exact projector programs. Fresh
hosted results remain required; no underlying runtime remedy is yet justified.

Format, typing0errors/0warnings, lint10.00/10, actionlint, strict OpenSpec and
pinned Semgrep0findings/0errors pass for this correction. Normal hooks run at
commit with the approved capsule-only DEFERRED label; hosted review is required.
