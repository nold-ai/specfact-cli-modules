# Native analyzer compatibility evidence

Recorded 2026-10-02 (Europe/Berlin), baseline
`37b6000227ba4be353a4f1769e39e92073b1fced`. Owner authorized bounded parallel
packaging and compatibility work while the signed boundary remains unresolved.
This checkpoint adds executable preparation/validation tools, not a production
backend. No module version, signature, registry publication or Linux identity changed.

## Actual native execution

Physical host: Darwin ARM64, macOS 27.0.1 build 26A434. No Docker or Rosetta was
used for these runs. Final runs used the complete hash-checked candidate locks;
normal dependency checks passed in each environment.

| Interpreter | Required adapters | Clean/defective results | Harness regressions |
|---|---|---|---|
| CPython 3.11.16 ARM64 | 10/10 | PASS | 17 PASS |
| CPython 3.12.14 ARM64 | 10/10 | PASS | 17 PASS |
| CPython 3.13.14 ARM64 | 10/10 | PASS | 17 PASS |

Adapters: Ruff, Radon, Semgrep clean-code, Semgrep bugs, AI-bloat AST, AST clean
code, BasedPyright, contracts/CrossHair, Pylint and targeted pytest/coverage.
Every adapter used the real module implementation with explicit tool binding and
fixed harmless fixtures. No findings or analyzer outputs were mocked. This is
bounded diagnostic compatibility, not exhaustive policy or full capsule acceptance.

Pinned versions: Ruff 0.15.12, Radon 6.0.1, Semgrep 1.175.0, BasedPyright 1.39.10,
Node 24.16.0, CrossHair 0.0.109, icontract 2.7.1, Pylint 4.0.7, pytest 9.0.3,
pytest-cov 7.1.0, coverage 7.15.4 and downstream Z3 5.1.0.0+specfact.1
(native library reports 5.1.0). Each ABI lock contains 94 pinned Python distributions.
Semgrep/MCP candidate upgrades satisfy the paired core's current security floor;
Linux pins remain unchanged. Native dependency policy admission is still pending.

Final ignored receipts and SHA-256:

- `.specfact/native-compat/final-cp311.json`:
  `dc08b2373b6a8fbc5888d22622f03ce504b7b3c3c81bcb9747e791adf77ac349`
- `.specfact/native-compat/final-cp312.json`:
  `d5cc8b7ced0acdcb26e1925f3338eb832eefdd4efca8bcc9928d54d953c38154`
- `.specfact/native-compat/final-cp313.json`:
  `dc39f6b977626cd34839ac7eda719265e960740c1598bbfb79602a505c20cd52`

All state `sandbox_verified=false` and `production_eligible=false`. The repeatable
[maintainer runbook](../../../scripts/native_analyzer_inputs/README.md) describes
installation and execution. These steps are not customer prerequisites.

## Dependency packaging and integrity

Node's exact archive hash was checked against the upstream checksum list after
successful GPG release-signature verification with an explicit official keyring.
See [input identities and verification](../../../scripts/native_node_inputs/README.md).
Two actual offline Node/BasedPyright builds produced the same 5,421-file manifest,
SHA-256 `55118eac03490f167bf932b1377f41523e9017aca094b402b70ad2820a099e88`.
The npm one-shot payload omits fsevents, PyPI BasedPyright and nodejs-wheel-binaries.

The deterministic Z3 correction produced
`z3_solver-5.1.0.0+specfact.1-py3-none-macosx_14_0_arm64.whl`, SHA-256
`af669755eabd97268a4141983a391cb4a832116d5a2c3cf04a4c53c7650ce72c`.
Two builds were byte-identical. Of 42 members, 39 contents are unchanged; only
METADATA, WHEEL and RECORD change, with the dist-info namespace renamed. Native
code, Python source and licenses retain exact upstream bytes. The sidecar records
all corrections and the upstream digest. Normal installation and dependency checks
passed on all three ABIs. This is visibly downstream provenance, not an assertion
that the upstream wheel was correct.

Static inventory of the actual Node and Z3 payloads passed: ARM64 Mach-O images,
resolved load paths, no Homebrew dependency. Inventory is not proof of every
runtime load or advertised minimum OS. Full interpreter/analyzer closure inventory,
license/security admission and signed payload acceptance remain outstanding.

## Failing-first implementation and independent review

The contracts in NATIVE_NODE_CONTRACT.md and NATIVE_COMPATIBILITY_CONTRACT.md
preceded their tests and implementation. Recorded RED/GREEN steps:

- Node packager: 23 tests failed for missing implementation; implementation passed
  all 23, then three resource/determinism cases expanded the suite to 26 passing.
- Mach-O inventory: initial missing-implementation failures, then 47 passing.
  Independent review found unbounded directory enumeration; a reproducer exceeded
  the configured entry budget before the incremental-scandir fix. All 48 now pass.
- Z3 repack: 13 missing-implementation errors, then 13 passing; actual deterministic
  wheel and unchanged payload independently checked.
- Dependency locks: three missing-lock failures, then all four input-contract tests
  passed, followed by actual hash-checked installs and dependency checks.
- Analyzer harness: missing implementation/initial native dependency failures,
  then all ten adapters passed. Independent review reproduced a surviving ordinary
  descendant after timeout. The fix cleans the process group before reaping its
  leader, retaining PID ownership. kqueue exit observation supports Darwin Python
  versions without waitid; verified zombie-only EPERM is distinguished from live
  cleanup failure. All 17 regression tests pass on each candidate ABI.

The requested review-agent performed separate read-only reviews of Node packaging,
Z3/inventory and analyzer harness/locks. Both actionable P2 findings were fixed
and re-reviewed with no remaining findings. Harness cleanup is deliberately
limited to ordinary controlled descendants; it does not satisfy the production
managed-process lifecycle contract.

## Repository gate checkpoint before final maintainability refactor

| Gate | Result |
|---|---|
| Focused prerequisite/compatibility tests | 134 passed |
| Format, type-check, lint | Passed; zero type errors/warnings |
| YAML manifests and bundle imports | Passed |
| Module signatures and version enforcement | Seven unchanged module manifests verified |
| Contract tests | 28 passed |
| Smart tests | 3,472 passed, one Linux-only skip |
| Full `hatch run test -q --no-cov` | 3,472 passed, one Linux-only skip |
| Strict OpenSpec validation | Passed |
| Staged requirements evidence | Passed at planned maturity; no capsule implementation proof claimed |
| Native public Code Review | FAIL / UNKNOWN: unsupported_controller_platform |

An earlier full-suite run had one report-status fixture failure. Independent
triage found that the unchanged test uses real checkout identity capture: it
passes on clean baseline source but reproduces UNKNOWN when that checkout changes
during analysis. The stable final suite passed without changing production checks
or weakening the assertion. Raw diagnostic logs remain ignored or outside Git.

The final public command was:

```sh
hatch run specfact code review run --enforcement changed --bug-hunt --json \
  --out .specfact/native-compat/final-code-review.json
```

All ten required analyzer entries report `unsupported_controller_platform`; exit
is 1. Compatibility smoke receipts are not substituted for this failing gate.

## Remaining delivery gates

The native public `specfact code review run` backend is not enabled. The signed
broker/bootstrap still lacks proven creation-to-tracing cleanup ownership, as
recorded in MANAGED_BOUNDARY_STATUS.md. No unconfined customer execution fallback
was added. Signed lifecycle proof, managed adapters, all four real-project manager
suites, acquisition/cache integration, final native signatures and authenticated payload manifests,
macOS 14/15/26 and Linux acceptance remain required. The physical macOS 27 result
does not establish support on those other releases.

A completed capability will require the module minor bump, authenticated resource
hashes/signatures, changelog, canonical registry metadata and final-artifact PR
acceptance. Do not archive #460 or claim native support from this checkpoint.

## Standalone-script contract exception

The repository's host review heuristic reports `MISSING_ICONTRACT` for public
functions in `scripts/macos_managed_boundary/preflight.py`,
`scripts/native_analyzer_smoke.py`, `scripts/native_node_package.py`,
`scripts/native_runtime_inventory.py` and `scripts/native_z3_wheel.py`.
This checkpoint records a narrow exception for that rule on those standalone
maintainer entrypoints and helpers only. These are not shipped module APIs.
Acquisition, verification, inventory and preflight intentionally use only the
standard library before any third-party environment is admitted; adding an
unverified icontract dependency to the bootstrap would contradict that boundary.
The smoke controller likewise launches the explicitly configured environment
without requiring the controller interpreter to import its dependencies.

Input identities, path/size bounds, invalid states, return receipts and failure
cleanup are enforced directly and exercised by negative tests. No gate rule,
production module contract or analyzer verdict was weakened; the warnings remain
visible in host review output. This exception does not waive defects or apply to
future production backend APIs, which remain subject to normal contract rules.

Three localized Pylint exceptions in the smoke harness preserve necessary behavior:
its fixture calls the released private pytest observer, catches arbitrary adapter
exceptions to retain independent failed-member evidence, and manages Popen cleanup
explicitly because Popen's context-manager exit waits without a timeout. Each is
explained at its call site and covered by focused regression tests. No global
warning disable or security-policy exception was introduced.


## Maintainer pre-commit follow-up

Normal hooks additionally found complexity/nesting and naming warnings. Refactors
split validation and observation into bounded helpers without changing receipt or
payload semantics. Node tests now total 32 and Z3 tests total 20; the combined
focused suite totals 147. Rebuilt Node manifest and Z3 wheel digests are unchanged.
The final three-ABI native analyzer matrix was repeated successfully after these
refactors; receipt identities above refer to those repeated runs.

Host pre-commit Code Review uses the repository's existing explicit-files review
path. Its successful result must not be confused with the capsule-required public
command, which still reports unsupported_controller_platform. The isolated
maintainer review environment supplies CrossHair and pytest together, avoiding
an ambient CrossHair interpreter that could not import the test fixtures.

Final post-refactor gates on 2026-10-02: full tests **3,485 passed, one Linux-only
skip**; smart tests **3,485 passed, one Linux-only skip**; focused tests **147
passed**. Normal pre-commit hooks passed, including signatures, format, YAML,
imports, lint, planned requirement evidence and 28 contract tests. Host Code
Review returned PASS_WITH_ADVISORY with only the 48 documented MISSING_ICONTRACT
advisories and no changed-line blockers. Independent review-agent re-reviewed
all refactored scripts with no actionable findings. The public capsule-required
native command remains FAIL/UNKNOWN; this is not a release-ready native capsule.

Developer ID and notarization are optional #488 follow-up work following the
2026-10-02 distribution-signing split; their absence is not a current blocker.
