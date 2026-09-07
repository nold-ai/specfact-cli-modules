# Installed payload layout: implementation evidence

- Recorded: 2026-09-07T08:43:25+02:00 (Europe/Berlin).
- Issue: nold-ai/specfact-cli-modules#459.
- Branch: `bugfix/459-installed-payload-layout`.
- Base: `5b521095bf0f294577d27ab08c59a87a9c1cf11c` (current remote dev at intake).
- Initial checkpoint scope: worktree setup, current-spec validation, and regression evidence.
- At the initial checkpoint, production source and release assets were unchanged.
- Implementation and final verification are recorded below; registry publication remains pending.

## Intake and specification

`openspec validate code-review-installed-payload-layout --strict` passed before
adding tests. Existing requirements cover the observed defect; no behavior
contract was amended. GitHub readback confirmed #459 and downstream core #680
are open and Todo. #459 has parent #163, labels, project assignment, no blocked-by
issues, and blocks core #680 and modules #460. Planning PR #461 is merged.
The core #680 issue scope was reviewed as downstream context; this checkpoint
changes no core interfaces or shared workflow semantics.

Hatch was bootstrapped serially. The default Python 3.14 environment and sibling
core 0.54.0 were replaced with Python 3.12.13 and released core wheels.
`smart-test-status` reported ready; `contract-test-status` reported nothing staged.
These helpers automatically reinstall the sibling core, so version-matrix runs
must reinstall the selected released wheel after invoking a bootstrap/status
helper. One collection attempt overlapped that reinstall and is discarded as
environment setup evidence, not a behavior failure.

## Regression fixture

`tests/integration/test_code_review_installed_payload_layout.py` creates an inert
package in pytest's temporary directory and signs it with an ephemeral Ed25519
test key. Only download transport is replaced. Core performs real extraction,
checksum/signature verification, metadata processing, atomic placement, and
install-marker writing. The archive is removed before the handoff. No production
publisher credentials, user-installed modules, or network downloads are used by
the tests. Dependency installation is skipped because the fixture has none.

Both variants require the actual install-relative manifest paths, unchanged
resource bytes and modes, and the existing canonical capsule destination.
The flat control also starts the copied inert fixture in a separate interpreter.
This does not claim real analyzer startup or native sandbox support on macOS.

## Failing-before matrix

Environment: Python 3.12.13, macOS 26.6.2 ARM64, pytest 9.1.1.
For each version, install it serially before executing pytest:

```sh
hatch run python -m pip install specfact-cli==0.55.4
hatch run python -m pytest tests/integration/test_code_review_installed_payload_layout.py -q --no-cov
hatch run python -m pip install specfact-cli==0.55.1
hatch run python -m pytest tests/integration/test_code_review_installed_payload_layout.py -q --no-cov
```

| Core | src case | flat case | Exit |
|---|---|---|---|
| 0.55.4 | FAIL: handoff UNKNOWN, invalid_core_0_55_1_install_handoff | PASS | 1 |
| 0.55.1 | FAIL: handoff UNKNOWN, invalid_core_0_55_1_install_handoff | PASS | 1 |

Both src cases pass real core artifact verification before failing the assertion
that the handoff must be PASS. Source inspection confirms that
`_installed_payload_manifest` only opens the flat `specfact_code_review` root.
The flat controls demonstrate that installation/signing and the fixture itself
are functional on both required core versions.

Existing related regression controls on core 0.55.4:

```sh
hatch run python -m pytest tests/unit/specfact_code_review/run/test_toolchain.py -q --no-cov -k 'builtin or core_handoff'
```

Result: 17 passed, 68 deselected. New-test Ruff lint/format and targeted
basedpyright passed with zero errors or warnings. The environment is restored
to core 0.55.4 after matrix execution.

## Historical checkpoint: remaining work before implementation

At this initial red-test checkpoint, this was not completed implementation or merge
readiness. The src test stops at handoff, so src copying and startup assertions
are not yet reached. Remaining unsafe/changed-root scenarios keep their planned
inspection mappings; this checkpoint does not claim execution coverage for them.

Before completing #459: finish the scoped safety coverage, implement root and
copy-path handling and diagnostics, obtain passing evidence on both core
versions, run real analyzer startup and the recorded Linux range verification,
and classify independent UNKNOWN outcomes separately. Full quality/review,
module version/signature/registry checks, implementation PR, canonical release,
and post-merge archival remain pending. No synthetic review JSON is supplied.

The main dev checkout remains unchanged. Reversal of this checkpoint consists
of discarding its uncommitted test/evidence edits in the dedicated worktree;
there is no published behavior to roll back.

## Defensive contract red tests (2026-09-07)

Before production edits, the eight new layout/copy contract cases in
`tests/unit/specfact_code_review/run/test_toolchain.py` ran on core 0.55.4:
6 failed, 2 passed, 85 deselected (exit 1). The failing cases cover ambiguous
root rejection, missing-root diagnostics, preserving handoff diagnostics,
descriptor-relative source reads, changed directory identity rejection using
injected metadata, and checking regular-file type before reading. Existing
content/mode drift rejection controls passed. These are defensive contract
fixtures, not runtime exploit evidence.

Command: `hatch run python -m pytest tests/unit/specfact_code_review/run/test_toolchain.py -q --no-cov -k 'exactly_one_package_root or reports_missing_root or retains_handoff_failure or descriptor_relative_source or changed_directory_identity or regular_file_before_reading or payload_drift_after_verification'`.

## Implementation and passing evidence (2026-09-07, Europe/Berlin)

The controller resolves exactly one real `specfact_code_review` or
`src/specfact_code_review` root. Manifest paths retain the actual installed
prefix; capsule copying removes that prefix while preserving the existing
`/opt/specfact/builtin/specfact_code_review` destination. Flat canonical payload
projections and report schemas are unchanged. Local directory identities are
excluded from the canonical projection.

Copying traverses source directories using anchored no-follow descriptors,
compares directory identities captured during verification, requires a regular
file before reading, and verifies bytes and mode from the same open source.
Missing, ambiguous, unsafe, or empty roots produce specific layout diagnostics.
Incomplete copying is removed and fails closed. Static invalid-layout controls
and injected metadata/I/O failures exercise these contracts without operational
race reproduction.

The integration suite now also signs and installs the actual current bundle
using the ephemeral fixture key, copies it, and starts the actual AST built-in
in a separate interpreter. It checks a known unused-extension finding. This is
in addition to the inert fixture used for byte/mode assertions.

| Verification | Result |
| --- | --- |
| macOS Python 3.12.13, core 0.55.4: payload unit/integration suite | 102 passed |
| Linux x86_64 Python 3.12.13, core 0.55.4: same payload suite | 102 passed |
| Linux x86_64 Python 3.12.13, core 0.55.1: same payload suite | 102 passed |
| Runner, differential and sandbox regression suite | 529 passed |
| Full `hatch run test -q` | 1806 passed, 81.50 seconds |
| Final full `hatch run smart-test -q` | 1806 passed, 79.53 seconds |
| Contract suite | 28 passed, 1778 deselected |

The full suites emitted two external Lark deprecation warnings (`sre_parse` and
`sre_constants`). An earlier full run detected concurrent worktree drift in an
E2E check; its isolated rerun and both subsequent serial full runs passed. The
failed attempt is retained as an execution issue, not counted as green evidence.

Host gates pin `SPECFACT_CLI_REPO=/private/tmp/specfact-459-core-0.55.4`, an
unchanged checkout of released tag `v0.55.4`, to prevent bootstrap helpers from
silently reinstalling sibling core 0.54.0. Pytest is 9.1.1 and CrossHair is
0.0.109. The Linux runs use the existing verification image in Docker Desktop
with `--platform linux/amd64` on an ARM64 Mac. This is emulated Linux evidence,
not native macOS support or completion of #460.

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-459-core-0.55.4 hatch run test -q
SPECFACT_CLI_REPO=/private/tmp/specfact-459-core-0.55.4 hatch run smart-test -q
SPECFACT_CLI_REPO=/private/tmp/specfact-459-core-0.55.4 hatch run contract-test
```

For each Linux core version, install `specfact-cli==0.55.4` or `==0.55.1`
serially into the isolated container environment and run:

```sh
python -m pytest tests/unit/specfact_code_review/run/test_toolchain.py tests/integration/test_code_review_installed_payload_layout.py -q --no-cov
```

## Official installed artifact and independent range evidence

The unchanged published `specfact-code-review-0.49.76.tar.gz` archive was installed
through core 0.55.4 in the isolated Linux container. Only download transport was
replaced with the existing official archive; core signature and checksum checks
were retained. The corrected controller's official installed-payload lookup
returned PASS with 39 entries and version 0.49.76. Capsule copying also returned
PASS at the canonical destination. Installed official payload bytes were not
modified. This proves the layout correction handles an actual publisher-signed
archive; it does not claim the new 0.49.77 build is already published or signed.

The recorded range uses unchanged core commits
`b897976ed994a708a7ad1984839090b2f858e00c` through
`daf05baa9303ef914f5659eafe940146d311af25`. The fixture is an isolated Git copy.
Initial environment setup encountered copied-repository ownership refusal,
which was corrected only in that container. Direct anonymous GHCR acquisition
returned HTTP 401. Existing OCI runtime blobs were exported from the cached
Docker image for the controller's unchanged digest/size verification; no
credentials or weakened trust checks were used.

The completed range report at 2026-09-07T09:24:01.463709+02:00 resolved the exact
commits and selected `tests/unit/modules/module_registry/test_commands.py` with
scope status PASS. Overall verdict remains FAIL / assurance UNKNOWN because
all required analyzers reported `capsule_materialization_failed`: Bubblewrap
was denied permission to create a namespace during offline analyzer installation.
The run took 95.09 seconds. This is an independent container namespace prerequisite,
not `invalid_core_0_55_1_install_handoff` or a payload-layout failure. The fixture
used normal Docker capabilities; no privileged mode or host namespace changes
were applied. The raw report is retained at
`.specfact/reports/459-linux-range.json`. Protected PR-range assurance and full
analyzer execution still require an appropriately configured Linux runner.

```sh
python -m specfact_cli.cli code review run --scope range --base-ref b897976ed994a708a7ad1984839090b2f858e00c --head-ref daf05baa9303ef914f5659eafe940146d311af25 --enforcement full --bug-hunt --json --out /tmp/459-linux-range.json
```

## Quality gates and bounded advisory exception

Repository format (1248 files), type-check (zero errors/warnings), lint
(Pylint 10/10), YAML validation, bundle import boundaries, strict OpenSpec
validation, contract tests, smart tests, and full tests passed. The staged
Requirements gate passed for one source at required/observed maturity `planned`.
Executable verification mappings were added; lifecycle acceptance/verification
provenance was not fabricated from local test results.

The mandatory manual review used the local source bundles, core 0.55.4, and:

```sh
hatch run specfact code review run --enforcement changed --bug-hunt --json --out .specfact/code-review.json packages/specfact-code-review/src/specfact_code_review/run/toolchain.py tests/unit/specfact_code_review/run/test_toolchain.py tests/integration/test_code_review_installed_payload_layout.py
```

The explicit source environment sets `SPECFACT_CLI_MODULES_REPO`,
`SPECFACT_MODULES_ROOTS`, and `PYTHONPATH` to this worktree's bundle sources.
Final report timestamp: 2026-09-07T09:07:55.275622+02:00;
PASS_WITH_ADVISORY, 73 findings, zero blocking. The same review against exact
base `5b521095bf0f294577d27ab08c59a87a9c1cf11c` at
2026-09-07T09:02:45.471358+02:00 reported 127 findings. Normalizing locations and
numeric counts in messages found no newly introduced advisory. New fixture
shadowing, helper size, import naming, and complexity warnings were fixed.

Explicit bounded exception under `docs/agent-rules/50-quality-gates-and-review.md`:
retain the 73 inherited advisories for this narrowly scoped correction. They
concern existing file size/complexity, public contracts, and whole-file coverage;
refactoring the legacy controller would expand #459 and invalidate its focused
regression comparison. No new clean-code regression or blocking finding is
excepted. This local explicit-files review is not protected PR-range assurance.

## Release boundary and rollback

Canonical changed-only signing tooling bumped Code Review from 0.49.76 to
0.49.77 and refreshed its filesystem payload checksum in dev-PR unsigned mode.
All seven manifests pass signature/version verification for a dev target, and
the bundle publish pre-check passes. Core compatibility remains
`>=0.55.1,<1.0.0`. Cryptographic release signing and registry publication belong
to the canonical release pipeline; registry entries remain unchanged until that
pipeline publishes the new artifact. No publisher credential was used locally.

Rollback before merge is dropping this worktree branch. After merge, revert the
patch and use canonical release tooling for a replacement release; do not edit
installed or published signed payloads. #459 stays open until actual acceptance;
archive only after merge using `openspec archive code-review-installed-payload-layout`.

Documentation Markdown checks passed, with MD025 disabled only for the Jekyll
document because its required frontmatter title and H1 trigger that rule.
OpenSpec Markdown checks retain MD025. Long-line/table-style exceptions follow
the existing documentation format. No runtime source changed after the final
102-test targeted run and 1806-test smart run.
