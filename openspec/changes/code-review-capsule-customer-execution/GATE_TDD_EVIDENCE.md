# Customer gate review corrections

Recorded 2026-09-13, Europe/Berlin, for PR #467 review comment 3997783045.

## Scope and specification

The active `code-review-tool-dependencies` delta already requires fail-closed
production launcher namespace denial and verified warm-cache identity. This
correction makes those requirements executable in the customer workflow.

Before administrator AppArmor setup, each ABI now runs the installed CLI against
an independent fixture with a separate empty `denied-cache`. The driver records
Ubuntu's AppArmor and unprivileged user namespace restriction settings and fails
if the expected restriction baseline is absent. Acceptance requires all ten
analyzer rows to carry capsule composition identities and report an error with
`UNKNOWN`, a `namespace_unavailable:` diagnostic, and CLI exit 1. Generic runtime,
integrity, observation, and analyzer failures cannot satisfy this negative test.
The normal customer gate then uses its own initially empty cache after the scoped
launcher profile is loaded. Neither review command runs with root privileges.

Cold and warm positive reviews additionally compare all analyzer composition
identities. Warm execution remains offline under umask 077. Each actual review
prints a bounded start/completion progress line; complete diagnostics stay in
uploaded report/log artifacts. Namespace policy, command exit, reports, and cache
identities are uploaded separately from positive evidence.

## Failing before production changes

Command:

```sh
hatch run python -m pytest -q tests/unit/test_capsule_customer_gate.py --tb=short
```

Result: **10 failed, 9 passed**. Failures demonstrated missing namespace-denial
validation, missing restriction-baseline validation, absent workflow ordering and
separate negative cache, and absent warm composition identity comparison.
Local transcript: `/private/tmp/capsule-gate-failing-466.log`.

After adding bounded progress expectations, the focused command with
`-k reviews_use_real` failed both selected cases because no start/completion
progress was emitted. Local transcript:
`/private/tmp/capsule-gate-progress-failing-466.log`.

## Passing after production changes

The complete gate unit file passed **22 tests** on macOS with Python 3.14.7.
Tests include rejected generic/missing failures, missing Ubuntu restriction,
unchanged real full-scope CLI arguments, offline/umask settings, and progress.
Local transcript: `/private/tmp/capsule-gate-passing-466.log`.

Targeted Ruff checks and formatting passed. BasedPyright reported **0 errors,
0 warnings, 0 notes** for the driver and its tests. `actionlint` passed the
customer workflow. Every driver function remains at cyclomatic complexity 10 or
below.

## Acceptance limit

These local results verify gate behavior, not Linux capsule success. Hosted
namespace denial and positive analyzer execution still require the actual CI run
on all three ABIs. The extra negative cold pass downloads another runtime per ABI
and uses its own materialization space; its duration must be measured from CI.
Public signed release acceptance remains a separate required gate. The additions
below implement fresh-cache umask and mount probes; their local unit results do
not claim those probes have passed on hosted Linux.

## Fresh umask cache and filesystem probes

The positive loop now adds one clean-fixture review with a different initially
empty `cache-077` root under umask 077. Its OCI bytes and every analyzer capsule
identity must match the umask 022 cold run. It uses anonymous online acquisition,
whereas the existing warm review remains offline. The modules repository is still
reviewed once. AppArmor grants the same narrowly scoped launcher permission to
that second positive cache only; the denied cache remains outside both profiles.
Each review records cache path, umask, offline mode, and cache identities.

The controlled `test_add` calls filesystem assertions that write/read/remove a
probe in HOME, TMPDIR, all declared XDG roots, and the private output mount. It
requires attempted writes beneath runtime Python, analyzers, source snapshot and
configuration to fail specifically with EROFS. Writable sealed paths and
unrelated errors such as EACCES fail the test.

Inspection found that the existing legacy full-review pytest implementation could
report PASS without running a flat customer fixture because its source mapping
was specific to this repository layout. The defective fixture now also contains a
known failing arithmetic assertion. Acceptance requires targeted pytest FAIL and
its reconciled `TEST_OUTCOME_NOT_PASS` finding, so a no-op PASS cannot satisfy the
customer matrix. Runtime inventory repair is handled separately by the main
implementation work.

A `capsule-private-writes-and-sealed-denials-v1` marker is recorded for successful
clean reviews only after the failing-assertion execution witness has passed. It
contains the exact controlled test-source SHA and capsule identity. This marker
is derived from fixture assertions and reconciled pytest evidence; it does not
claim to expose a raw test-created file after private capsule cleanup.

Additional failing-first runs:

- Five focused tests failed for missing fixture probes, proof validation, the
  alternate fresh cache and its launcher profile. Transcript:
  `/private/tmp/capsule-gate-mount-failing-466.log`.
- Two focused tests failed because the defective fixture had no failing pytest
  assertion and a no-op pytest PASS was accepted. Transcript:
  `/private/tmp/capsule-gate-pytest-failing-466.log`.

After implementation, **32 gate tests passed**. Ruff, BasedPyright (zero errors or
warnings) and actionlint passed. Transcript:
`/private/tmp/capsule-gate-mount-passing-466.log`. Generated fixture probes were
also checked with Ruff; the unit test proves an ordinary writable directory is
rejected as a sealed mount and that EACCES cannot masquerade as EROFS. Actual
Linux mount acceptance remains pending the hosted run.

The final matrix has three independent runtime downloads per ABI: denied baseline,
positive cold cache at umask 022, and alternate cold cache at umask 077. Warm,
defective and repository reviews reuse the original positive OCI cache. This
increases network and disk use to approximately three cold passes (about 2.4 GB
compressed across the complete three-ABI matrix, before install dependencies),
while keeping repository analysis single per ABI. Runtime duration is unmeasured.

## Pinned installation and bounded repository dogfooding

PR review 3997919585 identified that an unversioned public install could validate
the wrong release. The workflow now reads the selected checkout's registry entry,
verifies its archive SHA, and installs that exact version with the released core's
`--version` and `--source marketplace` options. It compares the entire installed
manifest to the pinned archive manifest and independently requires both payload
integrity and signature verification with the core's bundled public key. The
receipt records version, publisher, integrity metadata, archive SHA, public-key
SHA and checkout commit. On a release event, the actual release tag must resolve
to the registry checkout commit. No tag naming convention is assumed.

The repository review now uses a sparse checkout of the exact source commit with
`publish_bundle_selection.py` and its unchanged original
`tests/unit/test_publish_bundle_selection.py`. These two repository tests exercise
real publication selection behavior and depend only on the locked `packaging`
runtime dependency. The driver/test-gate pair was considered but rejected because
its tests require a host Git executable inside analysis. The selected pair avoids
that undeclared runtime requirement while still executing all ten analyzers.
The review uses explicit file arguments and records both files' SHA values and
source commit. This is selected repository dogfooding, not full-repository test
acceptance. Original source and tests are compared byte-for-byte with Git objects;
no replacement tests are generated for this lane.

Four focused tests failed before implementing pinned-install checks and the
repository selection contract. Transcript:
`/private/tmp/capsule-gate-install-failing-466.log`.
After implementation, **38 gate tests passed**, including explicit required
signature/integrity arguments and rejecting conflicting positional/scope options.
Ruff, BasedPyright, and actionlint passed. Transcript:
`/private/tmp/capsule-gate-install-passing-466.log`.

A local functional sparse-checkout check at
`8bc9554a6d8512938fcae95295e30eabf0c1889d` retained only the selected original
source/test pair and its two tests passed without the repository conftest or
pyproject. Source SHA:
`996acc9c76e4668fe8af659286ca4696c14a95969d4b2d4289e163f2e43bb3ca`;
test SHA:
`fdb190249dba6d9112aa3670f49a0bb88c0338441ffc14e46a4fb4d586131eaf`.
This is a host-side selection check; Linux capsule execution remains a hosted gate.

## Environment isolation and required PR gate

Review 3997957678 identified that copying the full controller environment could
forward unrelated credentials or SpecFact/Python overrides. Each review now uses
an explicit environment allowlist: private HOME/TMPDIR, fixed locale and PATH,
user-site isolation, isolated Git configuration, and the selected cache/offline
settings. Only the candidate lane adds the exact workflow identity variables and
candidate module root required for authenticated source selection. Public runs
receive no development switches, custom module signing key, Python path/home,
loader injection, runtime timeout override or ambient cloud/Actions credentials.
The CLI executable is the absolute `specfact` beside the active venv Python,
independent of the caller's PATH.

Three focused tests failed for missing environment isolation and shared trigger
coverage; three command tests also failed because the executable was PATH-resolved.
Transcripts: `/private/tmp/capsule-gate-env-failing-466.log` and
`/private/tmp/capsule-gate-executable-failing-466.log`.

Read-only GitHub metadata checked on 2026-09-13 showed that dev/main already require
`quality (3.11)`, `quality (3.12)` and `quality (3.13)` but no customer capsule
status. The customer workflow is now reusable and the PR orchestrator invokes its
matrix once when capsule payload, registry, driver/link helper, selected repository
source/tests, or either workflow changes. Direct customer pull-request triggering
was removed to prevent duplicate matrices. Public main-registry, release and
manual triggers remain.

Each existing required quality job depends on the capsule call and uses `always()`
to enter a first prerequisite assertion when code changed. That step explicitly
fails for failed signature prerequisites or any non-success capsule result when
required, including skipped/cancelled. It runs before the dev-to-main optimization.
Ordinary later steps retain their default success condition. Unrelated PRs skip
the costly capsule call and continue normal quality checks. No branch protection
settings were modified.

Eight focused workflow tests failed before the integration. After implementation,
**48 gate tests passed**, including shell execution of success/failure/skipped/
cancelled prerequisite cases. Ruff and BasedPyright passed, and actionlint passed
both workflows. Transcripts:
`/private/tmp/capsule-gate-orchestrator-failing-466.log` and
`/private/tmp/capsule-gate-orchestrator-passing-466.log`.

## Minimum-core compatibility uses the current authenticated lock

The earlier privileged compatibility smoke compared current lock bytes with the
completed C14 checkpoint and prefetched three old literal OCI digests. Revised
immutable artifacts intentionally have new identities. The smoke now depends on
canonical module signature/payload verification, reads each ABI's OCI digest from
the current lock, and requires that lock's SHA to match the current module
manifest's `authenticated_resources` binding. Historical C14 checkpoint files and
old immutable artifacts are unchanged.

The focused regression test failed before this correction and the complete gate
file then passed **49 tests**. Actionlint passed both workflows. Transcripts:
`/private/tmp/capsule-gate-minimum-core-failing-466.log` and
`/private/tmp/capsule-gate-minimum-core-passing-466.log`.

## Cold namespace denial before composition

Actual materialization uses the verified launcher during offline installation, so
a truly cold denied run can fail before a composed capsule identity exists. The
gate now accepts exactly two authenticated stages: the original analyzer-launch
namespace diagnostic with composition identities, or the explicit
`capsule_materialization_failed:namespace_unavailable:stage=offline-install:launcher=sha256:...`
diagnostic emitted after native launcher verification. The early form requires
all ten error/UNKNOWN rows, the current matrix's supported environment ID, and one
identical 64-hex launcher digest across every row. Generic installation errors,
missing digests, mixed launchers and missing/wrong ABIs fail. A separate identity
receipt records the observed stage; no pre-composition capsule identity is invented.

The early acceptance test failed first, while five rejection cases remained
failing closed. After implementation the complete gate file passed **55 tests**;
Ruff, BasedPyright, and actionlint passed. Transcripts:
`/private/tmp/capsule-gate-early-denial-failing-466.log` and
`/private/tmp/capsule-gate-early-denial-passing-466.log`.

## Candidate public baseline is independent of unpublished registry changes

Review 3998008726 identified that a publication PR may update its registry entry
before that version is available publicly. Candidate jobs now check out a separate
published `main` registry snapshot using the pinned checkout action, registry-only
sparse selection, and no persisted credentials. Only installation version lookup
and installed-artifact verification use that snapshot; its exact commit is already
recorded in the installation identity receipt. Actual review and candidate source
selection continue using the candidate checkout.

Public main/release/manual jobs keep their own checkout registry as the expected
artifact and retain release-tag identity checks. The existing scope scenario was
extended before tests to make both lane semantics explicit.

The regression test failed because no separate published registry checkout existed.
After implementation **57 gate tests passed**, Ruff and both workflow actionlint
checks passed, and strict OpenSpec validation passed. Transcripts:
`/private/tmp/capsule-gate-published-baseline-failing-466.log` and
`/private/tmp/capsule-gate-published-baseline-passing-466.log`.
