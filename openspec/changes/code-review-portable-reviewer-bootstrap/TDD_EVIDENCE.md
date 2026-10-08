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


## Pinned CrossHair constructor correction — 2026-10-08 Europe/Berlin

Diagnostic-onlyf0e3fa0d protected run37836889921 job113516135984 verifies both
prepared descriptors, then records contracts analyzer_reported_incomplete_execution
and crosshair_process_error_observed with value_error_observed and
wrong_parameter_order_observed. The installed0.51.0 job113516135892 separately
reaches its unchanged300-second analysis deadline with missing_report and
 timeout_marker_observed. Its timeout remains unclassified and is not claimed
as remediation by a candidate-only patch. Public committed CodeRabbit review
of the diagnostic diff completesreview_completed,0findings.

After the spec/design/mapping, the first fixture run lacks the CrossHair test
dependency (collection error, not RED evidence). Declare the existing analyzer
pin crosshair-tool==0.0.109 in Hatch's development test dependencies and recreate
its dependency state serially before parallel verification. No installed
reviewer or toolchain lock bytes change. Correct an overly strict explicit
signature identity check to upstream signature equality before production.
Final meaningful RED is10failed/4parityPASS(0.20s): actual argument loss,
invalid-order variadics/collision, scoped restoration and unsupported-version
rejection. Implement the existing trusted bootstrap/adapter dispatch pattern.
Clone the upstream intersection using copied globals and a local validated
Signature constructor that stable-orders final parameters; preserve the original
merge assignments/collision precedence. Strip actual implicit receivers before
intersection, preserving inherited, positional-only, static/bound __init__,
bound __new__, explicit signatures/defaults/annotations and variadic parameters.
Patch only core.get_constructor_signature per invocation, restore in finally,
and retain native CLI selection/flags/exit. Exact0.0.109 version guard refuses
unsupported analyzers as incomplete execution rather than claiming clean review.

The initial full/SMART each have one fixture mismatch (5089PASS/75skip/95subtests,
285.10s/283.71s): the earlier no-sampler dispatch proof uses the absent/opt wrapper.
Bind that proof to the actual trusted source without removing any original
attachment/argv/exit assertions and add resolver restoration. It then detects
run_path changing argv[0]; a meaningful focused failure precedes correction.
Forward the original entry program through the trusted adapter globals before
native run_module. Stop superseded test runs; no failing fixture is waived.
Replace the new callback's CC19 branching with explicit expected Parameter
objects retaining all defaults/annotations/kinds, and type annotation/default
values as objects rather than ignoring type errors. Final focused189cases pass
(16.07s), type-check0errors/0warnings and lint10.00/10. Actual installed AST and
AI-bloat have no findings; Radon has no changed findings (two unchanged bootstrap
baseline findings). Pinned Semgrep has0findings/0errors across adapter/bootstrap
and both dispatch test files. Bounded subagent review finds no actionable issues;
production core consumers use the patched lookup, with namedtuple, variadic-only
and unknown-signature parity checked separately.

The final production adapter on exact CPython3.12.13/CrossHair0.0.109 returns
exit1 with an actual structured Path-contract counterexample, empty stderr and
no invalid-order error within existing10-second path/120-second process limits.
No AST source transformation, global Signature mutation, sample profiler,
permission/contract/selection weakening or analysis budget increase is used.
Corrected trusted source refreshes the draft0.51.1checksum to
sha256:e68dde822406b78aea0acb7c94271aef5a4f643e6f103e2ae55a06ecc8693d16
under explicit user approval. Pass None to the checksum helper: no local signing
key is loaded and stale signature is removed. All seven dev-target filesystem
checksum/version checks pass; existing CI signature-only behavior is inspected
separately if it runs. Human merge/promotion and installed/native acceptance are
still outstanding; fresh exact-head sealed review and public committed review
are required before completion.

Final corrected-argv full/SMART each pass19required host proofs plus5090portable
tests,75declared skips,95subtests and five existing warnings(293.13s/291.25s).
Focused189PASS, typing0errors/0warnings, lint10.00/10, manifest schema/import
boundaries,28contracts, actionlint, strict OpenSpec and planned requirements pass.
Final exact pinned CLI still produces the real Path counterexample with empty
stderr; final pinned Semgrep has0findings/0errors. All seven approved draft
filesystem checksum/version checks pass. Protected current-head candidate review,
public committed CodeRabbit review and any signature-only CI child are pending
following the normal-hook commit/push; local capsule review is DEFERRED, never PASS.


## Callable pytest marker registry correction — 2026-10-08 Europe/Berlin

- Current signed2323a0e0 run37840754641 attempt2: CP312 required candidate113529947148 fails with crosshair_timeout_observed and no constructor exception observations; independent113529947167 lacks a report/observes a timeout. Signatures and all three schema compatibility jobs pass. No green or installed acceptance is claimed.
- CP311 artifact11578442358 and CP313 artifact11578244194 each establish Requests cold-auto contracts error/UNKNOWN with TypeError unhashable MarkDecorator at RegisteredContractsParser -> get_contract dictionary lookup. Their other four corpus acceptance records pass. Quality jobs stop at prerequisite customer failures, not demonstrated quality-code failures.
- Spec/design and mapped requirements precede tests. Before production:6genuine RED/16PASS,0.30s in marker-red.log, comprising real marked-class parser failure, both lookup aliases and restoration observations. Hashable registered override/custom-hash exception cases already pass.
- After the scoped declared-unhashable guard:27focused cases pass,0.17s. Real CPython3.12.13/CrossHair0.0.109 CLI on a marked class with an intentional failed postcondition exits1 with counterexample stdout and empty stderr under unchanged2/30-second limits. No classes/methods/contracts are removed. Both imported runtime lookup aliases restore in finally; unsupported-version rejection remains first.
- Actual AST/AI-bloat have0findings; Radon has0changed findings and2existing bootstrap findings. Pinned Semgrep has0findings/0errors. Typing0errors/0warnings, lint10.00/10, formatting/schema/imports,28contracts, strict OpenSpec and planned requirements pass. Initial quality failures (private imported aliases/redundant None branch) are corrected without waivers or removed assertions. Bounded independent review finds no issues.
- Initial full/SMART each pass19host proofs, then fail one assurance case with5097portable PASS/75skips/95subtests/5existingwarnings,293.03s/292.25s. The case passes in isolation, and all419cases in its complete module pass18.43s after edits settle. Source inspection shows its changed-review path captures/rechecks worktree identity; concurrent tracked edits during verification are a plausible cause, not established attribution. Fresh final full/SMART runs use a stable tracked tree.
- Approved draft checksum b33071e748470cf5e634e9ad8c92d479eb90233e81dfcd345d731fe7a85475f3 verifies all7modules against origin/dev with the public key. Stale signature removed; no private key accessed, and the user's CI-signing follow-up policy remains recorded.
- Local unsealed diagnostics are not hosted attribution: CP314 Path checkpoint copying differs from CP312; CP312 changed-source analysis also encounters unsupported Literal construction. A scratch-only finite Literal experiment still reaches the30-second bound, so no such type model, broader tracing change, narrower inputs or deadline change is applied. Required timeout diagnosis remains outstanding.

Final stable-tree full/SMART both PASS:19required host proofs plus5098portable
tests/75declared skips/95subtests/5existing warnings,325.54s/326.55s. Every existing
assurance assertion passes, including the earlier changed-review failure. No
production or test waiver was introduced. The prior concurrent-edit attribution
remains a hypothesis; no additional assurance logic change is warranted.


## Renewed sealed timeout diagnosis — 2026-10-08 Europe/Berlin

The current exact-head required CP312 job reaches the unchanged CrossHair bound
without a constructor exception. Local unsealed type/model experiments do not
attribute the hosted timeout and none are added to production. Reuse the approved
bounded standard-library sampling milestone with an explicit private contracts
boolean. This temporary route is default-off and must be removed before promotion;
raw stacks stay private, finite frame-presence observations are not attribution
or acceptance, and all original failures and deadlines remain blocking.

Spec/design and requirement reviewer-bootstrap-12 precede tests. Before source
edits, the expanded regression set produces20RED/6PASS in0.75s:17behavior
assertions plus3missing scoped-helper interfaces. Cases cover strict boolean
validation, contracts-only transport, default request parity, sample lifecycle
including attachment/runtime/SystemExit, CLI/deadline parity,64KiB private-tail
bounds, finite public privacy projection and parent environment restoration.
After implementation,223focused cases pass15.86s, including the mandatory current
hosted-gate proof, unchanged ordinary no-sampler dispatch and timeout assertions.
All25diagnostic cases pass after fixture-only clean-code corrections. No immutable
baseline proof is modified or newly waived. Typing0errors/0warnings, lint10.00/10,
actionlint, strict OpenSpec and planned requirements pass. Pinned Semgrep has
0findings/0errors. Bounded independent and defect-first source reviews find no
issues. Final changed-line scans and stable-tree full/SMART evidence follow.

The separately reported Rosetta home-cache writes are not attribution for the
current required hosted failure: job113529947148 is a GitHub-hosted ubuntu-24.04
x64 runner, with no emulator/container selected in this workflow. Preserve the
no-write assertions; emulated local evidence needs its own native control run.

Final stable diagnostic-tree full/SMART both PASS:19mandatory host proofs plus
5124portable tests,75declared skips,95subtests and five existing warnings,
275.82s/262.33s. Final AST/AI-bloat/Radon have0changed findings; baseline totals
are1/15/52. The extracted fixtures resolve test-length/parameter-count findings
without removing assertions. Final pinned fixture Semgrep also has0findings/0errors.
Format, typing0errors/0warnings, lint10.00/10,7manifest schemas/import boundaries,
28contracts, actionlint, strict OpenSpec and planned requirements pass. Approved
draft checksum e0b9e2fae43684a5cb2066b10fd521b6e9e0e5c9f5568fffdddd0aa8b9c32073
passes all7filesystem checksum/version gates against origin/dev. No private
signing key is accessed. Fresh protected diagnostics and ordinary installed
acceptance remain pending; local capsule review remains explicitly DEFERRED.


## Review follow-up: cache identity and completed-error privacy — 2026-10-08 Europe/Berlin

Public committed CodeRabbit0.9.0 review through5eb41e29 completes with two major
findings. Independently validate the sampled completed-error privacy claim: an
opted-in process error could copy sampler blocks into a finding. Correct it by
removing only five-second faulthandler dump blocks, preserving the original native
error and error/UNKNOWN. The dispatch-mock claim is invalid: the test enters the
real target_crosshair.py adapter, which calls the mocked shared runpy.run_module
for final CLI dispatch. Existing actual argv/lifetime assertions and all25cases
pass; no test or assertion is removed and no exception/waiver is used.

Current connector threadPRRT_kwDORVEFbs6qkNe3 independently demonstrates missing
CrossHair adapter policy in _BUILDER_FILES. Add it to the existing builder digest.
The existing offline cache test holds source/worker/Git identity fixed, proves
unchanged warm reuse and changes only the adapter after caching.

Spec/design and requirements precede tests. Before production:4genuine RED/
28PASS in0.86s, comprising adapter-only stale cache reuse and three sampled error
exits; ordinary completed stderr handling already passes. After correction all
76affected-module/dispatch cases pass0.64s. Actual changed-line AST/AI-bloat/Radon
have0findings. Pinned Semgrep has1unchanged baseline test-name finding at line100
of test_runtime_builder.py, outside the changed policy-invalidation parameter
list; no changed-line finding. Typing0errors/0warnings, lint10.00/10,7schemas/import
boundaries,28contracts, strict OpenSpec and planned requirements pass.

The pre-existing CI workflow adds signature-only child0f8a379e to5eb41e29. Inspect
its one-line manifest signature addition, fast-forward only, and strictly verify
all7signatures/payloads against origin/dev. No private key is accessed. Original
source-identical run37849276401 is cancelled after the child starts; no acceptance
is claimed. Signed-head run37849313316 attempt2 runs after maintainer djm81 rerun;
approval POSTs succeed. Required job113559131690 remains in its review phase.
Fresh protected observations and ordinary installed/native acceptance are pending.

Actual standard-library sample followed by a failed Python process also passes
the completed-error privacy control: sampler headers/frames are removed and the
original TypeError remains. The first standalone harness invocation lacked its
source import path and did not execute; adding explicit PYTHONPATH corrects the
harness. This local control is not sealed acceptance.


### Quoted sample-frame follow-up — 2026-10-09 Europe/Berlin

Bounded review reproduces a legal quoted-filename privacy defect with actual
CPython3.12.13 faulthandler output. Pause the verification process before tracked
edits: partial full run3301PASS/14SKIP170.00s is interrupted; SMART is not completed.
No failure is waived or passing final run claimed. Extend the spec and regressions
before code: quoted cases2RED/plain cases2PASS in0.24s. Correct both sample parsing
patterns to consume the filename through the final frame delimiter, including
embedded quotes, without crossing newlines. All78affected cases pass0.81s.
Actual exact CPython3.12.13 quoted compiled filename plus5-second sampler and
native TypeError passes: private sample token removed, nativeerror retained and
only finite argument_generation emitted. Typing0errors/0warnings, lint10.00/10,
strict OpenSpec and actual changed AST/AI-bloat/Radon pass. Bounded verification
finds the issue resolved with no remaining findings in the correction. Final
stable-tree full/SMART restart after the refreshed draft checksum.

Signed-head independent job113559131656 finishes with missing_report and
 timeout_marker_observed; its authenticated installed0.51.0 remains unchanged.
Required candidate job113559131690 still runs. No installed/native acceptance
or hosted bottleneck attribution is claimed from local controls.

Final corrected cache/privacy full and SMART both PASS:19mandatory host proofs
plus5131portable tests/75declared skips/95subtests/five existing warnings,
258.06s/256.02s. Every ordinary no-sampler, source-ownership and assurance assertion
passes. Approved draft checksum verifies all7modules; no private key is accessed.
Required signed-head job113559131690 finishes with CrossHair timeout and finite
observations installed_coverage_planning, portable_pytest_command,
run_portable_pytest, symbolic_search. Constructor exceptions are absent. These
observations narrow a follow-up setup diagnosis; they are not acceptance or proof
of any decoded input. Independent installed0.51.0 still lacks a report/observes
a timeout; CP311/CP313 external corpus execution is still pending.

## 2026-10-09: preserve errors before unused installed-coverage setup

The signed 0f8a379e CP312 hosted required-review job timed out with finite
observations of portable pytest setup, installed coverage planning and symbolic
search. These observations narrow the path; they do not establish causation or
acceptance. The CP311 and CP313 customer corpora passed. The three quality jobs failed at
the capsule prerequisite check before running quality tools.

Specification and eleven regression/parity cases preceded implementation. The
unchanged code produced eight failures and three passing parity cases
(`/private/tmp/specfact460-setup-order-red.log`). Decoded JSON lists, strings,
null, booleans and integers must retain the exact native assignment TypeError
before unused planning, including when that unused planner would raise OSError.
Valid objects retain serialized command order/bytes and bridge identity. Empty
or non-Python selections retain the exact empty CoverageBridge without metadata
or index work; nonempty outside sources retain the complete ownership path.

After the two setup-order corrections, 106 affected ownership, request and
dispatch tests passed (`/private/tmp/specfact460-setup-order-focused.log`). Exact
pinned CPython 3.12.13 controls and bounded read-only review confirmed native
error and command parity; these controls are not sealed acceptance. No analyzer
inputs, deadlines, flags, baseline errors, contract selection or isolation checks
were reduced. Type checking reported zero errors/warnings, lint 10.00/10,
manifest/import checks passed, all 28 contracts passed, and strict OpenSpec and
planned requirements evidence passed. Two new Semgrep test-name findings were corrected by naming their ownership
checks specifically; no waiver. An initial incomplete full run was stopped
before these name edits and both complete suites restarted on the frozen tree.

The reported Rosetta HOME writes from another session remain an environment
observation with capsule version and exact commands unavailable. This hosted
job used native ubuntu-24.04 x64; its timeout is not attributed to emulation and
no no-write proof was relaxed. Temporary sampled transport must still be removed
and fresh ordinary sealed acceptance obtained before promotion.

Final frozen-tree full and SMART each pass 19 mandatory host proofs and 5,142
portable tests, 75 declared skips, 95 subtests and five existing warnings
(256.16s/252.27s). Pinned Semgrep reports zero findings/errors across the setup
files. Actual AST/AI-bloat/Radon report zero changed findings. All seven draft
checksums/version checks pass against origin/dev. Logs:
`/private/tmp/specfact460-setup-order-{full,smart}-final2.log`.

## 2026-10-09: final current PR annotation regressions

Validated P2 titles: “Preserve targeted filters across the split test runs” and
“Keep ordinary base findings out of empty-head failures”. Specification preceded
tests: eight failures and nine parity passes on unchanged code
(`/private/tmp/specfact460-final-annotations-red.log`). The actual supported
`hatch run test -k test_target_crosshair` exited 5 after deselecting all 19 host
proofs, before portable execution (`/private/tmp/specfact460-final-hatch-filter-red.log`).
Full/SMART now run the same mandatory host proof unfiltered and preserve user
arguments for the portable run; host and portable failures remain failures.
Empty incomplete HEAD now retains only BASE tool errors, with ordinary BASE
findings absent and both nested UNKNOWN states intact. No errors are waived.

Initial read-only review mistakenly applied the immutable index/range route
to the candidate pre-commit command. Source tracing now establishes that this
candidate uses explicit_files review of one staged index snapshot; its analyzer
states are direct fields. BASE binds only changed-line comparison here. The
independent index/range route retains separate nested states.
The previous run did not upload that report. New finite-side regression cases
precede projection of only existing allowlisted analyzer/base/head incomplete
states; malformed nodes, unknown sides and private text are suppressed. This
is diagnostic attribution, not runtime acceptance or causal frame attribution.
The maintainer's source-identical runtime/documentation merge a5b3771d is retained
by rebasing only the two unpublished local fixes; no force push is required.

After correction, 42 focused regressions pass (1.49s). Actual supported Hatch
filter execution runs all 19 mandatory host proofs and the requested 22
CrossHair tests (1.57s portable). Typing reports zero errors/warnings, lint
10.00/10, all 28 contracts, manifest/import checks, actionlint, strict OpenSpec
and planned requirements pass. All seven draft checksums/version checks verify
against updated origin/dev. Actual AST/AI-bloat/Radon report zero changed
findings; pinned Semgrep reports 12 unchanged baseline findings (10 old test
names and two existing SMART status prints), zero changed findings and zero
errors. Bounded read-only verification reports no findings. No baseline lines
were changed and no failure waiver was introduced.

Final stable full and SMART each pass 19 mandatory host proofs and 5,154
portable tests, 75 declared skips, 95 subtests and five existing warnings
(245.26s/242.56s). The actual SMART targeted-filter command also passes all host
proofs and the requested CrossHair tests. Cumulative actual AST/AI-bloat/Radon
from maintainer head a5b3771d report zero changed findings. Logs:
`/private/tmp/specfact460-final-{full,smart}.log` and
`/private/tmp/specfact460-final-smart-filter-green.log`.

The maintainer merge's CP312 job 113571043433 reports a separate CrossHair
process-error class with no recognized exception observation. It has unchanged
runtime sources and is not attributed to the unpublished fixes. Its cause is
unclassified; fresh completed-frame and nested-side observations remain needed.

## 2026-10-09: preparation-flow annotation

P2 “Capture preparation failures before running the projector” is independently
validated: set-e previously skipped finite diagnosis when prepare failed.
Specification preceded actual Bash-flow tests; three failures and eight parity
passes precede workflow changes (`/private/tmp/specfact460-preparation-flow-red.log`).
Cases fail preparation with valid, invalid and missing reports; all require
INCOMPLETE, original exit 7 and no review execution. Success and projector-only
failures remain separate controls. A fixed successful-command marker is required
for PREPARED, so leftover valid descriptors cannot upgrade failed preparation.
The original 1800-second wrapper, native CLI arguments, environment and all
review deadlines/grants remain intact. No signed module assets changed.

After correction, all 99 projection/mandatory host cases pass (8.42s).
Actionlint, strict OpenSpec, planned requirements, format, typing (zero errors
and warnings), lint (10.00/10), manifest/import checks and all 28 contracts
pass. All seven strict signatures/filesystem checksums/version checks remain
valid; no module payload or manifest was modified. Actual AST/AI-bloat and pinned Semgrep report zero findings/errors. Radon
identified CC16 in the new shell-flow test. The just-started full suite was
stopped before edits; replacing computed expectations with six explicit
case outcomes preserves every assertion and strengthens report-outcome checks.
Fresh changed-line review and both complete suites are required.
Bounded read-only final verification reports no findings.

Extracting controlled interpreter/shell setup into fixtures and grouping
explicit expected outcomes retains all six cases and every assertion. Final
99 focused/host cases pass (8.79s), typing is zero errors/warnings, lint10.00/10
and actual AST/AI-bloat/Radon now all report zero changed findings. No warnings
are waived; the original incomplete full run remains retained separately.

Final frozen full and SMART each pass 19 mandatory host proofs and 5,160
portable tests, 75 declared skips, 95 subtests and five existing warnings
(263.57s/262.05s). Logs: `/private/tmp/specfact460-preparation-flow-{full,smart}2.log`.

On 2026-10-09 the user explicitly approved ignoring the known reviewer timeout
while this reviewer update is prepared for dev/main promotion. The independent
job installs published0.51.0 and cannot receive these fixes before promotion.
This is a documented exception for the timeout, not acceptance: its nonzero
exit, missing report and unavailable assurance remain unchanged. Actual process
errors, concrete defects and test failures remain in scope. Current signed371
CP312 reports TypeError with finite class-generation/reconstruction and
portable-pytest frames; that error is unclassified, not covered by the exception.
A bounded CPython3.12.13/CrossHair0.0.109/core0.55.4 control with37aligned
existing tool dependencies analyzes portable_worker alone: exit1 with946bytes
of actual analysis stdout and empty stderr. It does not reproduce the crash
and is not sealed acceptance. Exact batch-selection tracing remains necessary.


## 2026-10-09 Literal defect and sampler retirement

- Public 37186376 candidate batch is 23 Python paths (10 implementation/tool,
  13 tests), with explicit_files selection and one index snapshot. A CPython
  3.12.13 local control with every lock-listed Python distribution reproduces
  `TypeError: typing.Literal['full', 'changed', 'shadow'] is not a module, class,
  method, or function` in argument generation through proxy_for_class /
  get_type_hints. This does not assert the hosted finite TypeError is identical.
- Final pre-code regressions: 19 fail, 24 parity cases pass (2.64s). Real native
  CLI cases require a counterexample for each declared value, including nested
  constructor inputs, equal-but-distinct boolean/integer literals, None/enums,
  unions and a singleton. Initial fixture had one quoted-docstring syntax error;
  it was corrected and red evidence recollected against the original adapter.
- Scoped Literal creation preserves every exact alternative, existing models,
  cached proxies, other registrations and restoration on every exit. Native
  CLI/dispatch controls pass 50 tests (2.71s) on local CPython3.14.7 and all 50
  again on CPython3.12.13 with pinned distributions. The initial cached gen_args
  fixture incorrectly omitted upstream's required NoTracing context; only that
  test was corrected, with no production tracing shortcut.
- The unchanged 23-file CP312 batch moves past the reproduced Literal crash but
  reaches the same 30-second limit. This is timeout/incomplete, not acceptance.
  Per user direction, do not chase known reviewer timeouts or treat them as PASS.
- Sampler-retirement tests: 15 fail / 89 parity pass (3.80s) before removing the
  temporary transport, arming, private-frame parsing and public sample fields.
  Strengthen original ordinary timeout and no-sampler proofs with stale metadata;
  retain original flags/budgets, native errors and all mandatory host proofs.
- Combined focused proof: 203 pass (11.02s). Full/SMART and final quality evidence
  follow on the frozen production tree before commit/push. Original immutable
  historical deferred-review proof is untouched.


### Fresh P1 positional-prefix annotation

- Independently validate `Preserve valid ordering among positional parameters`
  (PRRT_kwDORVEFbs6qlrru). Two valid positional-only constructor combinations
  fail before code with `non-default argument follows default argument`; 29
  existing cases pass (0.22s). An initial mixed-kind fixture was valid and did
  not demonstrate this defect; it was replaced and red evidence recollected.
- Preserve positional order and real constructed first/second values; clear
  only impossible optional prefixes before a later required positional input.
  Reordering required arguments before optional arguments would change positional
  meaning and was not used. Valid optional defaults and annotations remain.
- Constructor/Literal/native-dispatch controls pass 57 tests (2.39s). Type checks
  have zero errors/warnings; lint10.00/10; actual AST/AI-bloat/Radon have zero
  changed findings; pinned Semgrep has zero findings/errors after a test-name
  correction and DRY consolidation preserving all cases.
- Earlier full attempts were superseded by real typing/clean-code/new-P1 fixes,
  stopped through their task-specific log writers, and are not passing evidence.
  Final frozen Full/SMART results are required below.


### Actual Full/SMART failure and test-state isolation

- Frozen Full and SMART each expose the same real regression: unknown bridge
  input raises ValueError instead of the original required ViolationError after
  parent-process CrossHair test initialization disables icontract checkers.
  Each run has 5,172 passing portable tests, one failure, 75 skips, 95 passing
  subtests and five existing warnings (269.14s/267.57s); neither is green.
- A fresh subprocess running the ten constructor-dispatch cases followed by the
  unchanged unknown-bridge contract test reproduces one failure / ten passes
  before fixture code. The outer regression fails before code (2.19s).
- Snapshot the three upstream-mutated checker functions through pytest's
  monkeypatch fixture and restore them at teardown. No project contract assertion,
  production analyzer initialization or symbolic-analysis policy is changed.
- Constructor/Literal/dispatch/bridge controls now pass82tests (5.96s), including
  the actual test-order subprocess. Actual changed AST/AI-bloat/Radon remain zero;
  required lint/type and pinned Semgrep are rechecked before final Full/SMART.


### Shared bootstrap isolation correction

- The next Full/SMART runs still expose the same bridge failure (5,173 passes,
  one failure,75skips,95subtests,five warnings;273.12s/272.33s). Constructor-only
  fixture restoration misses the earlier production-dispatch bootstrap test.
- Expand the subprocess order to production dispatch, ten constructor cases and
  the original bridge contract assertion. Before shared isolation the outer
  regression fails (1.95s), with the child exposing the same bridge failure.
- Move checker snapshots to an autouse fixture scoped only to the code-review
  run unit-test directory. Both real bootstrap test paths now restore their
  upstream mutations; production source and bridge assertions remain unchanged.
- The expanded controls pass82tests (5.97s); changed-code AST/AI-bloat/Radon remain
  zero. Final shared-isolation Full/SMART below supersede previous failed runs.


### Final shared-isolation verification

- Full and SMART each pass19mandatory host proofs and5,174portable tests,
  75declared skips,95subtests andfive existing warnings (265.40s/264.54s).
  The original unknown-bridge ViolationError assertion passes in both complete
  runs after all preceding code-review tests. No test failure is waived; the five existing warnings retain their prior status.
- Type0errors/0warnings,lint10.00/10,actual changed AST/AI-bloat/Radon0findings,
  pinned Semgrep0findings/0errors,strict OpenSpec/planned requirements/manifests,
  actionlint,CLI-contract/import checks and28contracts pass.
- Changed draft checksum/version and six unaffected signatures verify. The
  changed module remains an approved unsigned draft pending CI signing follow-up;
  no private signing key is read. Production sampler transport is fully removed.
- The known review timeout is separately user-approved as incomplete evidence.
  Current-head hosted process-crash confirmation and public review follow push;
  native installed/public acceptance remains after human reviewer promotion.
