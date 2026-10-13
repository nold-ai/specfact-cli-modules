# Diagnostic verification evidence

Observed on 2026-10-13. This change remains incomplete until its hosted observation and required current-head checks finish.

## Failing and passing controls

The specification and tests preceded the helper. Initial collection failed because the helper did not exist. A subsequent behavioral privacy test exposed exception text escaping redirected file descriptors through a captured Python stream. The helper now redirects both streams and descriptors, and that test passes.

Three isolated mutations were rejected with pytest exit 1: admitting a foreign same-suffix source, launching before identity verification, and allowing the required review failure to continue. The unchanged controls pass. No mutation was applied to the repository source.

The focused new and existing projection suites pass 43 tests on macOS. Three Linux-only lifecycle tests are skipped there, then pass separately in the existing Linux image with network disabled and a read-only supplier checkout. They cover timeout, cancellation and a normally exiting parent whose child starts a separate session. Each proves the descendant is absent from `/proc` afterward. Namespace visibility remains a hosted limitation; no namespace or ptrace restriction was relaxed.

## Prerequisites and limits

An ordinary-user Linux prerequisite check verifies the installed official core 0.55.4 location and existing key, all seven signed reference-209 package archives, and the pinned py-spy 0.4.2 wheel hash and required flags. It executes no subject review. Installed-source digests are observed identities, not authentication of a core wheel. Reviewer symbols must be members of the verified signed payload and retain their recorded file digest.

A synthetic actual sampling probe in the local amd64-emulated container cannot locate a Python process. It returns no profile and cleans up its two owned processes. This is unavailable sampling evidence, not a passed native profiler test or a classified slow stage. The native hosted route remains to be observed. Every public diagnostic reports non-acceptance and explicit unknown member/process joins.

## Scope and publication

The required independent review block is unchanged. The new failure-only step runs after its complete failed step and preserves its inline projection. No raw profile upload is added. Existing module payloads, manifests, registry rows and versions are unchanged. `llms.txt` is a generated command contract and does not change because this workflow helper adds no module command.

Strict OpenSpec validation and focused type/lint checks pass. Independent boundary review closed both lifecycle findings against the frozen source. Hosted native gates remain pending. The approved local ARM64 native-review deferral remains DEFERRED to exact-head Linux CI, never PASS. Rollback removes the optional step and helper.

## Independent review corrections

The first independent review identified two P2 defects: py-spy launch mode ended the wrapper at the 280-second sampling limit, and profiler provisioning did not own descendant cleanup. Both remain recorded in the initial review. The corrected bootstrap starts the unchanged wrapper, then execs py-spy in attach mode as its parent. The helper supervises the target after sampler exit. Provisioning and Git capture now use the same process owner. Five Linux lifecycle tests pass, including continued target execution after sampler exit and cancellation of provisioning with a detached grandchild. No ptrace policy changes are used.

The existing whole-job ban on workspace scripts correctly failed on the approved new helper. Its revised test permits only the exact named post-failure step after the required review, while retaining all other forbidden routes. Negative controls reject an additional helper, a removed failure guard and placement before the review.

The first full and smart runs were incomplete: they included the old workspace-helper assertion and host sandbox failures in process inspection, native tools and Semgrep. Those logs remain retained. Lint, types, YAML, bundle boundaries, 28 contract tests and all seven strict signatures pass. Version enforcement uses the actual PR base, since HEAD~1 is a signing-only commit with the same version. The corrected full suite passes 5,742 tests with 76 conditional skips and 95 passing subtests. The focused closure suite passes 270 tests; its five Linux lifecycle tests also pass in Linux. Staged local hooks pass after configuring the existing paired core checkout and adding the required schema-2 planned evidence mapping. The native capsule hook is explicitly DEFERRED to blocking exact-head Linux CI. The smart suite also passes 5,742 tests with 76 conditional skips and 95 passing subtests. The hosted observation remains pending.


## Current-head provider corrections

The 826948e7 provider reviews identified an unauthenticated workspace-helper launch, a late-adoption cleanup race and missing invalid-data exception projection. Three behavioral tests fail before the cleanup/error corrections: a child survives a falsely successful cleanup, and SyntaxError/AttributeError escape the uniform result. A separate insufficient-budget test observes a subject launch before the admission guard. These failures are retained. The optional step must follow both original projections, authenticate fixed helper bytes before execution and preserve its own full review allowance. Its internal allowance does not guarantee time remaining under the whole-job cap. The tamper fixture now signs a minimal temporary package with an ephemeral test key; production signature verification remains separate.

The first hosted observation at 826948e7 completed with DIAGNOSTIC_PARTIAL: 31,446 samples, 257 owned processes and a 300-second observation. Required review still exited 124 and no report was available. Verified stacks included capsule launch/wait and differential continuity edit-cost functions; missing member/process joins prevent causal attribution or sample-to-time conversion. The consumed attempt is bound to that head, so later heads skip optional sampling.

The corrected inline controller rejects tampered or unavailable downloads before executing any helper (three failing behavioral/order controls precede the fix), then executes only a private copy of authenticated immutable bytes. Both original failure projections precede it. The original whole-job workspace-helper ban is restored unchanged. Five ordinary-host Linux lifecycle cases move to an explicit host-proof file scheduled by both mandatory hatch test and smart-test routes; they are not executed as sealed target programs. Pure privacy, signature, race and budget unit controls remain in ordinary discovery.

A scaled regression extracts the production parent wrapper: with its old300-second value scaled to0.3 seconds, a valid0.22-second leaf after0.12 seconds of prior work loses its report and exits124. The600-second policy scaled to0.6 preserves that report, while an over-budget control still exits124. This proves the deadline ownership mismatch, not hosted sufficiency. The original observation and immutable signed baseline are preserved.
