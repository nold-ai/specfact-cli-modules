# Bounded native ARM64 boundary CI

Updated 2026-10-03 (Europe/Berlin). The workflow
[`code-review-macos-boundary.yml`](../../../.github/workflows/code-review-macos-boundary.yml)
extends the existing startup/control fixture proof across three hosted ARM64 OS
images. The first hosted run passed the startup fixtures on all three images
and failed control on all three. Local configuration validation and startup
success do not establish complete hosted boundary acceptance.

## Runner selection and exact platform gate

GitHub's [hosted runner reference](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and [official image label table](https://github.com/actions/runner-images/blob/main/README.md)
list these standard labels as ARM64. Accessed 2026-10-03; avoid floating
`macos-latest`, Intel labels and larger-runner suffixes.

| Workflow label | Required product version | Required OS build | Documented image version | Primary image source |
| --- | --- | --- | --- | --- |
| `macos-14` | `14.8.9` | `23J631` | `20260831.0302.1` | [macOS 14 ARM64 image](https://github.com/actions/runner-images/blob/main/images/macos/macos-14-arm64-Readme.md) |
| `macos-15` | `15.7.9` | `24G830` | `20260907.0337.1` | [macOS 15 ARM64 image](https://github.com/actions/runner-images/blob/main/images/macos/macos-15-arm64-Readme.md) |
| `macos-26` | `26.6.2` | `25G83` | `20260907.0351.1` | [macOS 26 ARM64 image](https://github.com/actions/runner-images/blob/main/images/macos/macos-26-arm64-Readme.md) |

All three image sources accessed 2026-10-03. These labels do not pin a VM image.
Each job asserts the exact product version and build above, cross-checks
`kern.osversion`, requires `RUNNER_ARCH=ARM64`, native Python and `uname` ARM64,
ARM64 hardware support and no translated process. It records the actual image
version and Python patch version. Image rollout drift fails preflight; maintainers
must review fresh official image documentation, revise the exact pins and rerun
the full matrix before expanding fixture evidence.

GitHub's [2026-10-01 retirement notice](https://github.blog/changelog/2026-10-01-github-actions-macos-14-runner-image-retirement/)
(accessed 2026-10-03) retires `macos-14` on **2026-11-02** and schedules brownouts
beginning **2026-10-05**. Reduced availability or a brownout is missing evidence,
never a fixture pass. Keep this row for the requested bounded experiment; resolve
the macOS 14 coverage route before retirement without substituting a newer OS or
claiming macOS 14 acceptance.

## Execution contract and security

The new workflow uses `pull_request` with paths covering itself, the fixture
sources/tests and this OpenSpec change. It can run before merge without requiring
a default-branch `workflow_dispatch` registration. Manual dispatch is also
available once GitHub recognizes the workflow on the default branch. Checkout
uses the event's default PR merge tree, pinned actions and
`persist-credentials: false`. No PR title/body/ref is interpolated into shell
code. Fork approval policies may require a maintainer to approve the ordinary CI
run.

All jobs use ephemeral GitHub-hosted standard runners, `contents: read` and
otherwise no token permissions, secrets, deployment environments, publication,
artifact/log upload actions, caches or Apple credentials. There is no
`pull_request_target`, self-hosted runner, `sudo`, privileged launchd domain or
security override. Untrusted PR code executes only in this ordinary CI context;
this workflow does not promote its receipts to protected release authority.

Only explicit native **Python 3.13** is provisioned for the stdlib helpers.
No Hatch, module/core installation, Semgrep candidate, package bootstrap or
third-party Python dependency is acquired. The preinstalled maintainer
`xcrun clang` and system `codesign` build fixed source snapshots with
`-arch arm64 -Wall -Wextra -Werror` and verify
`--sign - --options runtime` / `--verify --strict` through the existing helpers.
This is maintainer build acceptance, not a requirement for customer compilers.

Preflight requires an ordinary non-root user's real `gui/<uid>` launchd domain.
The first hosted run verified its availability on all three exact builds. Failure or timeout of
`launchctl print gui/<uid>` fails the job before fixture execution. There is no
skip, synthetic login session, privileged bootstrap or alternate domain fallback.
An actual PR job result must establish GUI-domain and native probe availability.

Every job runs these commands in the foreground, **serially**, with no retries:

```sh
python -B scripts/macos_managed_boundary/startup.py --repetitions 100 --out <private-runner-temp>/startup.json
python -B scripts/macos_managed_boundary/control.py --repetitions 100 --out <private-runner-temp>/control.json
```

The wrapper still attempts control after a completed non-timeout startup failure and fails
the combined job if either suite fails. A hard timeout stops the job immediately
to prevent overlap with uncontrolled native fixtures. Each helper has a 720-second outer
execution ceiling; every job has a 30-minute ceiling, a fixed three-row matrix
and at most three concurrent jobs. The execution budget is at most 90
runner-minutes per complete matrix attempt, excluding queue time. Concurrent
matrix jobs use different VMs; startup/control never overlap within one job.
A superseding run cancels the previous run; cancellation provides no acceptance.

The existing helpers retain their five-second survivor/job-removal gates and
native deadline exclusion. The wrapper requires successful exit **and**
`repetition_gate_passed=true`, exact `repetitions=100`, 100 actual passing
records for each of the six startup races and twelve control lifecycle cases,
and all nineteen control protocol checks. It requires the normal-completion and
runtime-trap controls exactly once. It checks both subset flags, the
startup positive and surviving negative controls, native architecture/build,
fixture source snapshot digests, three signed binary digests per suite and
ad-hoc/hardened signing details. It rejects incomplete receipts and requires
`production_approved=false` and `signed_boundary_verified=false`.
Job ceilings do not replace or relax fixture deadlines.

## Sanitized evidence and admission limits

Raw helper stdout/stderr and JSON stay in private runner temporary files and are
deleted by the wrapper after each attempt. Existing helper failure snapshots
stay on the ephemeral VM until teardown. No raw receipt, audit-token identity,
PID/birth record, private capability, authority file, diagnostic path, exception
message or native event/status output is printed or uploaded by this workflow.

The public output is an explicit allowlist: platform/Python/image identity,
suite result or fixed failure category, allowlisted failing case and exception
class, partial successful counts, successful race counts, protocol count,
source/helper/profile and signed-binary SHA-256 values, signing mode, hardened
runtime and the two false production flags. The step summary contains a compact
suite/result/check-digest table. Each check SHA-256 hashes canonical sorted JSON
of that sanitized record (UTF-8, separators `,` and `:`), before adding
`check_sha256`. This digest binds the public summary to the allowlisted checks;
it is not a signature, raw-receipt digest or protected admission seal.

A green matrix establishes only these fixed startup/control fixtures for the
recorded OS/build combinations and PR merge revision. It does not establish
all-ten analyzer parity, sealed analyzer acceptance, arbitrary project or
project-manager execution, runtime installation, customer CLI/GHCR installation,
complete tracing/IPC/loader/resource escape admission or production eligibility.
The current sealed analyzer helper hashes and loader grants reference a locally
prepared environment and are not portable yet; `analyzer.py` is intentionally
outside this workflow. Published platform support remains gated on complete
artifact-bound acceptance and independent physical-Mac installation proof.

## Validation, remaining evidence and rollback

The existing [startup contract](STARTUP_BOUNDARY_CONTRACT.md),
[control contract](CONTROL_BOUNDARY_CONTRACT.md), native fixture tests and
[TDD evidence](TDD_EVIDENCE.md) supply the preceding behavior specification and
fixture proof. This change adds CI configuration and receipt enforcement only;
it does not modify helper behavior or add tests that merely mirror YAML.

Targeted local validation completed 2026-10-03 (Europe/Berlin):

- `actionlint 1.7.12 .github/workflows/code-review-macos-boundary.yml`: passed,
  including runner-label/workflow syntax and available ShellCheck integration.
- YAML parsed with PyYAML 6.0.3; the three ARM64 labels and exact version/build
  values match the primary source table. Both embedded Python scripts compile.
- `markdownlint --disable MD013 MD060 -- openspec/changes/code-review-native-platform-execution/NATIVE_BOUNDARY_CI.md`:
  passed.
- `openspec validate code-review-native-platform-execution --strict`: passed.
- Actual inline receipt functions accepted the existing complete physical-host
  startup/control receipts (six and twelve race groups). Twenty-four altered
  receipts were rejected, including partial counts, missing protocol/positive
  controls, wrong architecture/build/source/signature and true production flags.
  Both private-field injection checks passed. Wrapper success/timeout checks
  preserved sanitization and deleted raw files. These were temporary offline
  checks of actual workflow functions; no new tests or native CI run was created.
- Scoped `scripts/pre_commit_code_review.py`: explicitly skipped because the
  owned scope has no Python file targets. No SpecFact analyzer PASS or
  merge-authority review JSON is claimed.
- Two-file whitespace/content checks: passed. This configuration check did not modify native fixture implementations.

Final repository assurance gates remain for the parent's frozen complete
worktree and must run serially. A run that snapshots concurrently changing
Git-visible files is not final assurance evidence. Broad gates and independent
review are not claimed by this scoped validation.

Required next evidence: the PR run URL, tested merge SHA, all three job results,
recorded OS/build/image/Python identities, GUI preflight result, six-by-100 and
twelve-by-100 counts, nineteen protocol checks and sanitized check digests.
**Complete hosted boundary acceptance: failed on the first run.** Do not mark
the supported-matrix or full native admission task complete from startup proof.

Confidence: High for the documented label architecture; hosted fixture
compatibility remains unverified. Assumptions that can change the result:
runner OS/build deployment, ordinary GUI launchd availability and hosted native
probe/signing behavior. Failures are handled as follows:

- Image drift or macOS 14 retirement: fail; review official image/replacement
  availability and collect fresh exact-platform evidence.
- Missing GUI domain or a confinement/lifecycle survivor: fail; retain the
  existing acceptance gates and investigate the actual hosted result.
- Execution timeout or cancellation: incomplete evidence; rerun the full job
  after resolving the cause, without partial counts or automatic retries.

Rollback is to revert these two CI-only files or disable the workflow after a
reviewed failure. Production flags and signed module assets are unaffected.
These CI checks cannot merge code or publish a capsule. Final repository gates
and actual hosted acceptance are recorded separately.

## Review corrections

A hard helper timeout must stop the job before any second suite starts, because
killing the Python harness can bypass job cleanup and leave native fixtures alive
until VM teardown. Completed non-timeout failures may still allow the next suite;
timeout results cannot. Startup receipts must contain exactly one passing normal
completion and runtime-trap control in addition to every race and negative control.
Regression tests exercise the actual embedded workflow functions, not a duplicate
validator or a YAML shape assertion.

## Hosted failure diagnostics contract (2026-10-03)

The first PR #489 run passed startup on macOS 26 and failed its control helper;
macOS 14 also failed. A generic helper failure is insufficient to triage these
results. On failure, the wrapper must retain only allowlisted case names,
exception classes, fixed operation-phase names and counts of passed cases from a bounded private receipt/log
read. Unknown names and exception messages must never be published. Raw logs,
identities, paths, capabilities and native status/event payloads remain private.
Diagnostic fields cannot change a failed suite to a pass or relax any deadline.

Meaningful tests must exercise the actual workflow functions with injected
private data, incomplete receipts and nonzero helper exits before implementation.

## Initial hosted execution — PR #489

The first run [37079681523](https://github.com/nold-ai/specfact-cli-modules/actions/runs/37079681523)
used merge checkout `66989837e01a407f9742dbcf241de977da278f3d`, combining
head `b0459e322d6d63f1bb5a7833f77a6c82327a5213` with dev
`37b6000227ba4be353a4f1769e39e92073b1fced`. Each ARM64/ordinary-user/GUI
preflight passed; all six startup modes completed 100 times on each build.

| Build | Startup result | Sanitized startup check SHA-256 | Control result |
| --- | --- | --- | --- |
| 23J631 | passed | e89b8f1d5488dd9d300bd53a5270f842a2151f6d18721fc33b0bbe89c91b6b57 | helper_failed |
| 24G830 | passed | dc00b6c6894e007d04f88c23594ce2ce13039330670268685de18ba5c0d8a6dc | helper_failed |
| 25G83 | passed | 5c1e8d9aabe4dca161be830b147ea1b3c1c87b5ce5178a5660ce7b56f6db7929 | helper_failed |

Raw failures were not exported. Their cause is unproven; no later run can turn
this failed run into acceptance. Head `55980530` added bounded diagnostics. Its
merge checkout `2239ddb841678ab07c42d45e104e313f1a030bc1` reproduced a timeout
in the concurrent isolation case on macOS 15 after the first eleven lifecycle
cases; macOS 26 failed during round 18 before completing isolation. Nested
exception propagation can report an outer invocation, so failing-case
attribution was corrected with a failing-first workflow test.

These results verify startup compatibility only. Control, complete boundary,
production integration and customer installation remain gated.

The second run [37080266799](https://github.com/nold-ai/specfact-cli-modules/actions/runs/37080266799)
passed the full macOS 14 startup/control fixture suite at merge `2239ddb841678ab07c42d45e104e313f1a030bc1`.
Control recorded 100 of all twelve lifecycle cases plus nineteen protocol
checks; sanitized check SHA-256:
`aa7129e3edf867c48818090475a6534680fffba8f5ea5dfef1466531a63e83f9`.
macOS 15 and 26 still failed control. This single OS pass does not approve the
full matrix. Next diagnostics select explicitly attributed failure ownership and an allowlisted
operation phase. Nested unwind order alone cannot establish ownership.

Independent review reproduced left-side failures unwinding the right invocation
first. Public attribution must select only a boolean failure_origin=true marker
stamped for the actual active invocation before cleanup. Missing, unknown or
non-boolean ownership never establishes a failing invocation. Request phases
must cover reply validation as well as send/receive errors.

## Diagnostic-only control transition observations — 2026-10-03

The third hosted run at head `314e5b6c` passed 600 startup races on every image,
but control aborted on macOS 14/15 at `bootstrap-socket` and on macOS 26 at
`cancel` / `request-wait`. No C event-loop cause has been established; 300
additional physical-Mac cancellation trials passed. Keep this failed run as
missing matrix acceptance, not a retryable pass.

To distinguish unread waits, reap, output EOF and completion dispatch, the fixed
broker will emit a complete private transition snapshot for each owned worker.
It contains four actual booleans: `wait_accepted`, `wait_pending`,
`worker_reaped`, `output_closed`. The failing controller must select the last
valid snapshot for the worker handle of its failing wait. The public workflow
may copy only those four boolean fields as `last_worker_state`; missing evidence
must remain omitted, never inferred as false. These are last observed diagnostic
states, not a claim of current process presence or cleanup enforcement. The
snapshot cannot contain a public PID, handle, audit token, path, capability,
raw output, status or exception message. Raw snapshots remain private.

Diagnostic instrumentation must preserve requests, signal delivery, tracing,
wait/reap behavior, event-loop scheduling, five-second measurements, competing
deadline exclusion and the 100-repetition requirements. Neither transition
observations nor socket readiness checks grant production eligibility.

The native workflow's pinned actions are updated to official
[checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1)
(`3d3c42e5aac5ba805825da76410c181273ba90b1`) and
[setup-python v7.0.0](https://github.com/actions/setup-python/releases/tag/v7.0.0)
(`5fda3b95a4ea91299a34e894583c3862153e4b97`). The official action manifests
were read at those exact revisions on 2026-10-03; both use Node 24. This resolves
the hosted Node 20 deprecation annotations. Checkout still retains no credentials;
permissions, native Python selection and acceptance gates are unchanged.
