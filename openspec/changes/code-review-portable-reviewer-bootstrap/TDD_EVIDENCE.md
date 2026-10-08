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

## Approved bounded CrossHair diagnosis — 2026-10-08 Europe/Berlin

Owner approved identifying and correcting the demonstrated root cause inside the
existing sealed runtime. Exact5425 CP312 prepares both descriptors, then reports
crosshair_timeout_observed; independent installed0.51.0 reports missing_report
and timeout_marker_observed. Neither result attributes the performance cause.

After specification, six meaningful sampler/privacy tests fail before code
(0.13s); one bounded-tail budget regression already passes. The actual workflow
projector separately fails before code(1.31s). Captured logs:
/private/tmp/specfact460-crosshair-profile-red.log and
/private/tmp/specfact460-crosshair-projector-red.log.
After implementation,129 focused cases pass(7.02s), including actual main wiring
before runtime attachment and preservation of SystemExit1/module args,
normal/error teardown, string/byte stderr, unknown/older token suppression and
30/120-second timeout/2/10-second per-path command parity. Final tail/observations
are bounded and fixed; raw stacks are never published. This is temporary candidate
instrumentation, not installed acceptance or a runtime fix. Remove it after
diagnosis. Full passes19host cases, then5041portable/75skips/95subtests/five existing
warnings(263.80s). SMART passes the same counts(257.33s). Format, zero-error/warning
typing, lint10.00/10, manifests/imports,28contracts, actionlint, planned requirements,
strict OpenSpec and formal filesystem checksum/version verification of7modules
pass. AST/AI-bloat/pinned Semgrep are clean; Radon reports only unchanged legacy
functions. Bounded independent review finds no defect. Actual sealed sampler
operation/overhead and hosted observations remain pending. Normal hooks and public
committed CodeRabbit review follow; local capsule review remains approved DEFERRED.

Candidate checksum refresh uses released origin/dev comparison with both private
key environment variables removed. Code Review remains unpublished0.51.1; CI-only
signature follow-up is required. No authenticated installed bytes are modified.


## Request-first portable pytest setup — 2026-10-08 Europe/Berlin

Exact bb474e44 CP312 job113066295319 prepares both descriptors and times out
in CrossHair; the bounded samples identify run_portable_pytest and symbolic_search.
Independent job113066295210 reports missing_report/timeout_marker_observed without
analyzer attribution. No matching audit denials are observed. These facts do not
yet establish which operation causes the timeout.

After specification, three meaningful regressions fail before implementation:
malformed JSON performs coverage setup; malformed/setup-failed requests import
response helpers before any child observation. The valid-input parity fixture
passes. RED:3failed/1passed/84deselected(0.16s), private log
/private/tmp/specfact460-crosshair-setup-red.log.
The fix decodes JSON before planning installed coverage and loads the two broad
runner response helpers only after observation validation needs them. The public
postcondition, coverage ownership, command arguments, checker selection and all
budgets remain unchanged. Final focused GREEN138passes(1.46s). Additional
valid-response and uncaught ImportError regressions retain existing policy/error
behavior while verifying response imports follow actual child completion.
Sealed timing comparison remains required: setup reduction is verified, its
contribution to the30-second timeout is still a hypothesis.

Final full/SMART each pass19 mandatory host cases followed by5047portable tests,
75declared skips,95subtests and five existing warnings(278.05s/277.17s).
Format, typing0errors/0warnings, lint10.00/10, manifests/imports,28contracts,
planned requirements, strict OpenSpec and seven candidate filesystem checksum/
version validations pass. AST, AI-bloat, Radon and pinned Semgrep report zero
findings for both changed Python files. The existing CI-only signing workflow
will add the candidate signature after push. Normal commit hooks follow with
only local ARM64 capsule review approved DEFERRED to hosted Linux.


## Verified setup correction and sampler removal — 2026-10-08 Europe/Berlin

Run37703624491 job113073036925 passes deferred candidate commit review and
cold/warm fixtures under unchanged guards. Independent installed0.51.0
job113073036863 reports missing_report/timeout_marker_observed without analyzer
attribution. The combined setup correction is supported by changed-input hosted
evidence; neither operation is separately isolated.
After specification, five production regressions fail before sampler removal
(0.11s; /private/tmp/specfact460-sampler-removal-red.log): normal dispatch must
retain attachment/argv/exit without sampling; byte/string timeout stderr must
remain private with UNKNOWN/error and exact30/120s process +2/10s path bounds.
Temporary sampling, its fixed frame helper/projection and temporary-only tests
are removed. Production regression coverage retains the policy assertions.
The local source probe ends before usable analysis with a signature ValueError
(1.75s); it does not reproduce or establish sealed performance.

Production focused GREEN153passes(6.63s). Full/SMART each pass19required host
cases followed by5043portable tests,75declared skips,95subtests and five existing
warnings(254.89s/255.67s). Format, typing0errors/0warnings, lint10.00/10, manifests,
imports,28contracts, actionlint, planned requirements, strict OpenSpec and seven
filesystem checksum/version checks pass. AST/AI-bloat/pinned Semgrep are clean;
Radon reports only unchanged baseline functions. target_bootstrap and
contract_runner are byte-identical to origin/dev after profiler removal.
Normal hooks follow with approved local capsule-only DEFERRED and mandatory
hosted review. No private signing keys are used; CI signature follow-up required.


## Production hosted result and oversized report header — 2026-10-08 Europe/Berlin

Unprofiled production7bb10941 run37705634781 job113079504408 passes required
candidate commit review under unchanged limits. Independent installed0.51.0
job113079504239 now produces oversized_report, with unavailable assurance/verdict
and unclassified observations. It does not report the earlier missing report or
timeout marker. A request-inventory diagnostic is unnecessary for this observed
phase and is not retained in the change.
Specification precedes seven meaningful oversized-header failures(1.02s),
including the existing oversized fixture and six new root-header cases. After
implementation, an additional oversized Unicode case retains valid header
observations when the prefix ends within a multibyte character. Final65focused
host/projector cases pass(6.69s); AST/AI-bloat/Radon are clean for the real
embedded observer and test file.
The observer retains the existing2MiB+1 sentinel read and parses at most2MiB
of the prefix. Standard-library JSONDecoder consumes complete root fields,
stops before findings, rejects duplicates and malformed/incomplete headers,
and accepts at most64root fields. Only analyzer_evidence and the actual unknown
boolean are retained privately for finite observations. Oversized status and
unavailable verdict/assurance remain unchanged; no partial header is accepted
as a complete report, and private fields/findings/paths are never copied.
Installed bytes, review argv, grants and300/1800s limits are unchanged.
Actual hosted header availability and failure cause remain unverified.

Pinned Semgrep on the extracted embedded observer reports one print-in-src
transport finding at its final JSON emission. Explicit narrow exception: this
existing workflow interface intentionally emits one allowlisted JSON line to
stdout for CI observation; replacing it with ordinary logging would alter the
consumer contract. No arbitrary report data is printed. No other pinned Semgrep
findings or errors are reported; this is not a runtime source-file exception.

Final full/SMART each pass19 mandatory host cases followed by5050portable tests,
75declared skips,95subtests and five existing warnings(271.29s/269.91s).
Format, typing0errors/0warnings, lint10.00/10, manifests/imports,28contracts,
actionlint, planned requirements, strict OpenSpec and seven strict filesystem
signature/checksum/version checks pass. The diagnostic-only change does not
alter signed module payloads; the existing0.51.1 signature remains valid.
Normal hooks follow with approved local capsule-only DEFERRED and mandatory
exact-head hosted review. Public committed CodeRabbit review follows push.


## Complete rows before a large analyzer inventory — 2026-10-08 Europe/Berlin

Run37709238224 job113091006580 passes exact-head candidate commit review,
while installed0.51.0 job113091006648 reports oversized_report with no complete
analyzer header observed. This does not establish an analyzer cause. The
released report places analyzer_evidence before findings, and analyzer rows
can embed complete pytest inventories. A bounded reader requiring the entire
array discards complete earlier rows when a later inventory exceeds its prefix.
After specification, two large-inventory regressions fail; malformed row and
duplicate-root parity cases already pass(2failed/2passed/46deselected,0.91s).
The observer consumes at most10complete JSON analyzer objects, retains earlier
complete objects only when the next object is truncated by the prefix, and
rejects invalid row tokens/delimiters and duplicate root keys. Incomplete object
contents are never projected. Every observation still comes from the original
2MiB prefix; oversized status and unavailable verdict/assurance stay mandatory.
No installed bytes, review argv, grants, acceptance or deadlines change.
Focused69host/projector cases pass(7.09s). Fresh hosted attribution is pending.
The hypothesized large-inventory explanation is not yet confirmed by that run.

Final full/SMART each pass19required host cases followed by5054portable tests,
75declared skips,95subtests and five existing warnings(253.48s/254.72s).
Format, typing0errors/0warnings, lint10.00/10, manifests/imports,28contracts,
actionlint, planned requirements, strict OpenSpec and seven strict signature/
filesystem checksum/version checks pass. AST/AI-bloat/Radon find no issues;
pinned Semgrep retains only the documented structured-stdout exception.
Normal hooks follow with approved local capsule-only DEFERRED; exact-head
hosted execution and public committed CodeRabbit remain required.

Before push, malformed trailing-comma arrays reveal an additional regression at
both one and ten rows; each focused case fails before its rejection correction.
The empty-array branch and final row-limit boundary now reject trailing commas.
The unpublished complete-row commit will be amended through normal hooks after
final verification; no unverified corner-case implementation is pushed.

Final focused71cases pass(7.04s), including both malformed-array regressions
(RED1failure/50deselected,0.81s; RED1failure/51deselected,0.34s).
A final scan explicitly selects the worktree-installed analyzer executables.
The earlier ambient-path Radon check did not establish the embedded reader’s
complexity; the explicit scan found CC13 in analyzer_rows. Factoring one-row
decoding removes it; the real final reader and tests have zero AST/AI-bloat/
Radon findings with the worktree tool path. Final full/SMART reruns follow.


Independent final review identifies valid literal cuts at the byte bound as
a retention defect. After specification,7valid literal cases fail and3malformed
parity cases pass(1.13s): true/false/null, exponent/fraction/negative numbers
and Unicode escape prefixes must preserve earlier complete objects. Only exact
end-of-prefix valid literal fragments are admitted; malformed suffixes remain
rejected. Final81focused host/projector cases pass. No raw literal or row data
is copied publicly; no acceptance/read/analysis budget changes. The correction
is folded into the unpublished complete-row commit before public review.
Previous full/SMART5056-case runs pass(261.28s/259.32s), but precede this literal
fix; final verification of the additional cases follows.

Final literal-aware full/SMART each pass19required host cases followed by5066
portable tests,75declared skips,95subtests and five existing warnings
(263.22s/263.46s). Focused81cases pass(7.24s). Format, typing0errors/0warnings,
lint10.00/10, manifests/imports,28contracts, actionlint, planned requirements
and strict OpenSpec pass. Worktree-installed AST/AI-bloat/Radon have zero
findings for the actual final reader and tests; pinned Semgrep retains only
the documented existing structured-stdout exception. Signed payloads are
unchanged; formal strict signatures/checksum/version validation is repeated
before normal amended commit hooks. Public review and exact-head CI follow.


## Complete private diagnostic report — 2026-10-08 Europe/Berlin

Installed0.51.0 run37713711290 job113105307584 now establishes contract
error/UNKNOWN with a complete root header; the old2MiB prefix still cannot
reach tool-error findings after a large analyzer inventory. It does not yet
establish a specific contract failure class. Specification precedes three
new failing regressions(3failed/62deselected,0.95s), covering actual CrossHair
classification, another tool with identical text and a report beyond the
private diagnostic cap. A complete standard-library JSON parse replaces
custom prefix parsing. The existing2MiB oversized threshold still makes
assurance/verdict unavailable and findings_present false. Only this private
failure-diagnostic read increases to32MiB; analysis deadlines, failing exit,
grants, authenticated installed bytes and acceptance gates are unchanged.
Duplicate fields/malformed JSON are rejected; at most10analyzer rows and
10000findings are inspected for finite analyzer/side/class observations.
No raw report fields, source paths or failure messages are emitted.

Final focused84cases pass(8.70s). Full/SMART each pass19mandatory host proofs
plus5069portable tests,75declared skips,95subtests and five existing warnings
(256.47s/255.81s). The final test only groups unchanged policy assertions;
focused validation is repeated after simplifying its actual CC13 finding.
Worktree-installed AST/AI-bloat/Radon now have zero findings. Pinned Semgrep
has only the existing documented structured-stdout transport exception and
zero errors. Format, typing0errors/0warnings, lint10.00/10, manifests/imports,
28contracts, actionlint, planned requirements, strict OpenSpec and seven strict
filesystem signature/checksum/version checks pass. Signed assets are unchanged.
Public committed review and fresh hosted exact-head attribution follow push.
Both PRs have zero unresolved current threads at this triage. Their quality
failures occur at signature/customer prerequisites before actual quality stages.


## Incomplete differential evidence and CrossHair exit classification — 2026-10-08 Europe/Berlin

Complete-reader run37716355426 job113113903056 establishes contracts and
targeted-pytest-coverage error/UNKNOWN only in BASE. It emits no CrossHair
failure class. Head warnings can suppress base tool errors because incomplete
differential classification chooses head_findings or base_findings. A bounded
independent source reproduction confirms loss of1/1base errors beside ordinary
head findings and1/2errors when both sides fail. Separately, the actual pinned
CrossHair0.0.109 CLI Path-contract reproduction on CPython3.12.14 exits1 with
a constructor ValueError only on stderr and empty stdout. The runner accepts1
as a normal counterexample exit and reads stdout only, incorrectly returning
zero findings. That false-clean pattern cannot itself explain hosted UNKNOWN.
Do not conflate the local library reproduction with the unclassified hosted
cause; hosted sealed CP312 patch version differs. Upstream0.0.111 still has
the relevant signature intersection code, so a version bump alone is not a
verified fix. No compatibility patch is applied to an installed reviewer.

After specification,4regressions fail(432deselected,0.55s): ordinary/error head
findings must retain base tool errors without resurrecting base ordinary
findings; failure exit1 with empty stdout and either stderr or no diagnostics
must remain error/UNKNOWN. The correction preserves ordinary head selection,
retains all tool errors, keeps unknown differential state and existing failing
report behavior, and rejects exit1 without analysis output as incomplete.
Existing counterexample/side-effect output parsing and all process/path budgets
remain unchanged. Public review ofc0eea11a completesreview_completed,0findings.

Final focused436runner/contract cases pass(16.15s). Full/SMART each pass19required
host proofs plus5073portable tests,75declared skips,95subtests and five existing
warnings(255.84s/253.04s). Format, typing0errors/0warnings, lint10.00/10,
manifest schema/import boundaries,28contracts, actionlint, strict OpenSpec and
planned requirements pass. Worktree-installed AST/AI-bloat/Radon and pinned
Semgrep have zero changed-line findings; existing baseline findings remain
unchanged. Both PRs have zero unresolved current review threads.

The source fixes change the signed0.51.1payload. Read-only strict verification
confirms the old manifest checksum no longer matches. Proposed checksum is
sha256:86c8e5942b4cb3d7728b43fd40584295cef9b3202edeb5ebd2ff31404e7716c6.
Automatic approval review rejected checksum-only manifest replacement because
it would remove the existing signature and was classified outside diagnostic
scope. No manifest change or bypass occurs. Source/test/spec work is complete
locally; updating the checksum and obtaining a fresh signature from the existing
CI workflow requires explicit approval before normal commit/push. No private
key is read, no installed reviewer is mutated, and no merge/publication occurs.
Public committed review and exact-head candidate/installed acceptance must run
again after this source correction is signed and pushed. The original hosted
base-snapshot analyzer cause is still unclassified; the new evidence-retention
fix must not be represented as remediation of that as-yet-unknown cause.

## Signed-payload update authorization — 2026-10-08 Europe/Berlin

The user explicitly approves the checksum refresh and states that CI signing
will occur through a follow-up PR after merge to dev. This resolves the preceding
automatic approval-review rejection. Replace the stale signature with the
correct filesystem payload checksum only; never present it as signed acceptance.
Use the existing unsigned-head checksum/version policy for this dev-targeted PR.
No private key is read and no authenticated installed reviewer is modified.
Do not merge or publish automatically. A fresh valid CI signature remains a
release prerequisite. Public committed review and exact-head hosted verification
follow the normal-hook commit and authorized PR push.


## Signed production review and candidate private diagnostic bound — 2026-10-08 Europe/Berlin

The existing PR workflow adds signature-onlye0cc2f54 todf9230a1. All seven
strict signatures/filesystem checksums/version gates pass for the unchanged
86c8e594payload. Public committed review ofdf9230a1 completesreview_completed
with0findings. In run37833646841, job113505891002 now fails the required review
and emits only candidate_report_unavailable: its old2MiB diagnostic cap conceals
large-report tool errors, so no analyzer cause is established from this result.
After specification, the actual large candidate-report classification regression
fails; other-tool privacy and beyond32MiB parity remain passing. Reuse the same
complete32MiB private diagnostic strategy already tested for independent review;
retain candidate_report_unavailable for reports above2MiB and the original
failing exit. Reject duplicate/invalid JSON, inspect at most10analyzer rows and
10000findings, and print only closed failure classes/exception observations.
No installed bytes, payload assets, grants, checker argv or analysis budgets
change. Do not conflate a diagnostic failure with the underlying analyzer cause.

A scratch actual-CLI reproduction on exact pinned CPython3.12.13/CrossHair0.0.109
confirms Path constructor ValueError on stderr with no analysis stdout. A scratch
receiver-before-merge/variadic-order correction produces an actual Path-contract
counterexample within the same10/120s bounds. Named argument preservation also
requires removing each receiver before merging; sorting then final stripping is
unsafe. These are local library facts; no production compatibility shim or
authenticated installed reviewer mutation is made without hosted attribution.

Candidate diagnostic validation:87canonical host/projector cases pass(8.40s).
Full/SMART each pass19required host proofs and5076portable tests,75declared skips,
95subtests and five existing warnings(261.02s/258.22s). Format, type-check
0errors/0warnings, lint10.00/10, manifest schema/import boundaries,28contracts,
actionlint, strict OpenSpec and planned requirements pass. Actual installed
AST/AI-bloat/Radon report zero findings across both projectors and zero changed
test findings. Pinned Semgrep reports only the documented structured JSON stdout
transport exception; no other findings or analysis errors. All seven strict
signature/filesystem checksum/version checks pass: this workflow/test correction
does not change signed module assets. A mistakenly selected immutable baseline
fixture file retains six known stale-recipe failures; canonical mandatory host
proofs execute current assertions and pass, and full/SMART preserve that policy.
No baseline fixture bytes or existing assertion is removed.

Latest installed0.51.0 job113505891187 exits after its existing300-second analysis
deadline with missing_report/timeout_marker_observed. This is fresh installed
failure evidence, not attribution to the local constructor defect. Both PRs
have zero unresolved current threads. Existing signatures are retained and
no merge/publication occurs. A new diagnostic-only committed head must receive
fresh exact-head candidate review and public committed CodeRabbit analysis.
