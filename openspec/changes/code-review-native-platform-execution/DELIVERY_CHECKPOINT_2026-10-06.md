# Native delivery checkpoint — 2026-10-06 (Europe/Berlin)

**Caution: #460 remains incomplete.** Code Review 0.51.0 / core 0.55.4 are
released, but no Darwin ARM64 artifact is admitted in the installed native
catalog. The correction prepares 0.51.1; it adds no command or extra capability.
No publisher private key, module re-signing, GHCR write, merge or publication
occurred locally. Production and complete-boundary eligibility remain false.

Confidence is high for the bounded observations below. Runtime release readiness
is unknown until the remaining final-byte acceptance passes. The physical host is
Darwin ARM64, macOS **27.0.1 (26A434)**; it cannot substitute for macOS 14/15/26.

## Repository and public status

Worktree branch: `codex/finish-460-macos-arm64`, based on updated origin/dev
`b87159c4fbeab3a1282919823035c2109527d385`. Origin/main was
`d13a5c0ca69b21fdbbfdeefdb2435a43b4774c40`. Their file trees agree; main adds only
its release merge commit. The protected primary checkout was not edited.

[#460](https://github.com/nold-ai/specfact-cli-modules/issues/460) was reopened
and its SpecFact CLI project status restored to Todo on 2026-10-05. Parent #163,
required labels, project assignment and dependency directions were read back.
#459 is closed; #460 blocks optional Apple distribution #488 and Windows #495.
Neither follow-up blocks this delivery. Historical evidence is preserved.

## Reproduced native roots and rejected archive bytes

The existing assembler and native component build produced all three complete
roots. The existing builder produced unsigned deterministic USTAR archives with
36 observed ad-hoc hardened Mach-O images per ABI. Native signature, loader,
closure and bounded streaming checks ran. CPython inputs use complete
hash-locked dependency sets; cp312/cp313 were resynchronized in separate inputs
after the older candidate environments were found incomplete.

These **empty-entitlement archives are rejected runtime candidates**, not staged
release artifacts. All three completed **0/20** required analyzer cases because
Pydantic Core extension loading failed under hardened library validation. Their
recorded archive identities must not be promoted or inserted in the catalog.

| ABI | Archive bytes | Archive SHA-256 | Manifest SHA-256 |
| --- | ---: | --- | --- |
| cp311 | 600412672 | `9a908ab3c4c06437a2b45ce630b24369645d67ee2d12f68d2f05b699269aa965` | `0004a62e70e1c39ee6c162e694eeedcda6344d6eef65ff9af7acf3cf5c0af87a` |
| cp312 | 600330240 | `9c562827f4ee97e2c1120e9c7b7f866cbe2b2416272532562f6e88cc32fb2878` | `f95a2a18d3f9f46b00b122e7fd7d0288300fef0b84e980111d9a3ca66c6e09a6` |
| cp313 | 599658496 | `477691de5e29a9ad167ecfca099521d9138a32fc57a785b426231a2f19810f41` | `cb79a3212fe45734464c709c43acb7d780cb4fa6f89d1441d5f84971962d7471` |

Unsigned summaries explicitly report `manifest_authenticated=false` and
`production_eligible=false`. The three archives total about 1.80 GB; fresh
candidate copies, dependency inputs and extracted runtimes require additional
multi-GB disk space. Exact machine-readable counts are retained in
DELIVERY_CHECKPOINT_2026-10-06.json; raw receipts/tool output remain private.

## Existing library-loading experiment

Fresh candidate roots using `cpython-analyzers-library-loading-v1` passed all
**10/10 analyzers and 20/20 clean/defective cases for each ABI**. Each also passed
the existing confined project observer: preparation/execution domains separate,
actual pytest, plugin activation, coverage and ARM64 CFFI extension import.
These are fixed-fixture candidate observations, not final archive-bound release
or upstream four-manager corpus acceptance.

The experiment sets only `com.apple.security.cs.disable-library-validation` on
CPython and Semgrep Core; no production profile was changed. Apple documents that
hardened library validation normally admits Apple/same-Team libraries, while
this entitlement changes library admission and triggers extra Gatekeeper checks.
[Apple entitlement documentation](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.security.cs.disable-library-validation),
accessed 2026-10-06. Static signed-file closure, launch-time image binding, project
extension separation and independent default-protection installation must still
prove the exact proposed initial-distribution configuration. Fixture success
alone does not approve that entitlement or waive any loader/boundary gate.

The historical Hatch reconstruction correctly remained INCOMPLETE for all ABIs:
its fixed adapter lacks hatch.lock, sealed pyodbc/pytest-asyncio and its sealed
adapter executable. The caller-driven production manager implementation remains
the correct route; this older reconstruction is not its acceptance or a reason
to introduce a publisher project catalog. Semgrep reference checking initially
failed because the new worktree lacked ignored, hash-pinned reference inputs;
that attempted failure is preserved rather than counted as parity success.
After restoring only authenticated fixed-reference inputs, the existing
versioned Semgrep adapter comparison passed **14/14 cases for each ABI**.
This resolves that fixture comparison, not global production version-policy
admission; the released Linux version identity remains separate.

## Linux regression observation

Current main public customer run
[37377573666](https://github.com/nold-ai/specfact-cli-modules/actions/runs/37377573666)
failed on cp311/cp312/cp313. Retained cp312 evidence shows cold/warm/alternate
clean reviews executed successfully, expected defects were found, and immutable
OCI blob identities agreed, but warm and alternate capsule composition
identities differed from cold. Source inspection and four RED regressions
reproduced a concrete mechanism: controller-generated cache/bytecode files,
excluded from module signing, entered the copied module manifest and capsule
identity. The correction omits those exact categories and preserves source and
resource tamper checks. **The hosted failure's remediation remains unconfirmed
until current-head Linux CI passes.** Analysis budgets and enforcement are unchanged.

The unchanged fixed C boundary workflow's current-base run
[37376126601](https://github.com/nold-ai/specfact-cli-modules/actions/runs/37376126601)
succeeded on its macOS 14/15/26 runners. That proof uses its fixed native fixtures,
100 repetitions and independent survivor checks; it is not acceptance of these
Python runtime archives or an independent installed customer command.

## Verification and review

Regression order was specification, focused tests, observed RED, implementation,
observed GREEN. TDD_EVIDENCE.md records commands and counts. Controller Python
was 3.14.7; candidate execution used the distinct selected cp311/cp312/cp313
runtimes. All private output was retained outside authenticated module paths.

- Final format, type, lint, YAML, import-boundary, manifest integrity/version,
  publish pre-check and OpenSpec strict validation passed. The changed 0.51.1
  manifest is deliberately unsigned for CI signing; no main-release signature
  gate or actual publication is claimed. Declared core compatibility is unchanged
  because these corrections use existing interfaces and core 0.55.4 was exercised.
- Staged requirements evidence passed at planned maturity, with
  implementation evidence explicitly not-yet-available. This is a mapping gate,
  not executable release acceptance.
- Command diagnostics: RED 3 failures / 1 pass; GREEN 83 tests.
- Keyless assembly: RED 1 failure / 1 pass; GREEN 60 tests.
- Generated bytecode: RED 4 failures; GREEN 116 toolchain tests.
- Contract suite: 28 passed; smart suite: 4998 passed, 75 skipped, 95 subtests.
- Full suite after the bytecode correction: 5002 passed, 75 skipped,
  95 subtests, five warnings, 111.19 seconds. Explicit native/corpus proof skips
  are not acceptance passes.
- One bounded independent agent reviewed the checkpoint and bytecode correction
  using the exact requested review-agent skill; its final pass found one P3
  evidence-attribution defect, corrected by citing the actual existing tamper
  tests. It reported no actionable code security/defect findings. No agent fleet or old-head GitHub review is claimed.
- Mandatory local SpecFact review generated fresh JSON at
  `2026-10-05T22:11:36.527467Z` (2026-10-06 Europe/Berlin). Its authoritative
  verdict is FAIL, assurance UNKNOWN, `ci_exit_code=1`; every analyzer reports
  `native_capsule_artifact_not_admitted:darwin-arm64-cp312`. The outer CLI process
  returned zero; that does not override the report or satisfy the gate.

## Remaining delivery and rollback

The protected native build/accept/sign/stage workflow is still absent. GitHub
public environment metadata read on 2026-10-06 showed only github-pages; a native
release/signing protection environment is not configured. No signing authority
was tested or requested. Final dependency/profile admission and authentic
four-manager upstream corpus remain open, as do the final-byte 14/15/26 x three
ABI matrix, physical changecost/unrelated project, and clean independent signed
module installation with cold anonymous GHCR acquisition and offline reuse.

Catalog entries must bind accepted CI-signed final archive bytes in dedicated
`ghcr.io/nold-ai/specfact-code-review-capsule-darwin-arm64`. Do not manufacture
entries from rejected or experimental roots. Customer installation must use the
ordinary authenticated module route with default protections. No development
link, unsigned override, local artifact override or quarantine bypass can count.

The human approved the repository's narrow local ARM64 deferral on 2026-10-06
to blocking current-head Linux CI, permitting this checkpoint to be committed,
pushed and opened as a draft PR. The local capsule gate is DEFERRED, never PASS.
Merge/promotion remains a separate human decision after complete review and
acceptance. Preserve #460 Open/Todo and this OpenSpec change until authorized
publication and a fresh canonical installation pass.

Risks that could change the outcome: default host protections may reject the
library-loading distribution; native dependencies may fail on older supported
OS builds; genuine manager/corpus incompatibilities may remain. Mitigations are
exact-byte independent installation, the mandatory OS/ABI matrix and original
upstream manager fixtures with the existing confined domains/budgets.
Rollback withdraws affected macOS catalog references in a corrective release,
retains immutable historical artifacts and preserves Linux support. The current
unpublished patch can be reverted as an ordinary source change.


## Draft PR and hosted correction status

Draft [PR #498](https://github.com/nold-ai/specfact-cli-modules/pull/498) targets
`dev`. Its first checkpoint was rebased onto governance-only updated dev
`74d3fd4dd6f9b171f18857abcc8f659c80d686e9`; CI signed its module at
`687b7d7396b50b2bb1454376688fae532db62c84`. Public-key required-signature verification
then passed all seven bundles. The follow-up changes module bytes and therefore
requires a fresh CI signature, preserving unpublished version 0.51.1.

At that signed head, hosted macOS14 and macOS26 passed fixed startup/control
fixtures; macOS15 passed startup and failed control at request-authenticate in
cancel after 73 repetitions. No final capsule bytes or ABI matrix were accepted.
Linux cp311/cp313 completed customer cold/warm fixtures and all five upstream
corpus entries across four managers (candidate PASS). cp312 failed the deferred
candidate review;
the independent signed reviewer failed to install unavailable version 0.50.1.
These statuses cannot substitute for the follow-up head's required CI.

The bounded correction pins independent review to signed published 0.51.0,
activates bug-hunt in the staged helper, honors explicitly matching test paths
when stems collide, and emits bounded tracked public finding locations/fixed
native connection exception classes. Required incomplete evidence, strict
coverage, original 300-second analysis and five-second cleanup bounds, immutable
subject/reviewer separation and all lifecycle counts remain enforced. Detailed
RED/GREEN and current-source gate results are in TDD_EVIDENCE.md.

The same review agent found no introduced defect in the combined correction.
CodeRabbit explicitly skipped the draft. Its CLI did not review: automatic
approval review rejected external diff transmission beyond the authorized
bounded agent. No diff was sent and no workaround or external review request
was made. This is unavailable review evidence, not a completed review.


## Socket readiness follow-up at signed 18e77026

At signed 18e77026, Linux cp311/cp313 customer acceptance and all three minimum-
core checks pass. The cp312 required review and independently installed signed
review fail; independent 0.51.0/core0.55.4 installation itself succeeds. Fixed
native macOS14/15 lifecycle jobs pass, while macOS26 fails request-authenticate
with ConnectionRefusedError. This is current-head fixture evidence only.

The follow-up observes listener readiness within the original seven-second
connect deadline, refreshing the remaining timeout after metadata checks. Only
initial refusal retries; auth, job registration and fixtures do not. RED4+RED1,
and independent-agent deadline RED2, precede the current 304-test native unit
pass (five explicit native skips). Physical macOS27 full attempts stopped in
protocol checks and do not count as 100-repetition acceptance. Hosted review
failure diagnostics now expose only finite public identities/classes and bounded
tracked locations, preserving private reports and original failure exits.

Local analyzer reproduction confirms complexity findings in builder/workflow
functions. Required clean-code remediation and four incomplete analyzer results
remain blockers. Final archives, protected signing/staging, all nine native
OS/ABI cells and fresh default-protection independent installation remain
unproven. #460 stays open; no promotion/publication/archive is authorized.
