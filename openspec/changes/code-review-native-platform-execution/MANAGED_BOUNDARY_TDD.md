# Managed-boundary prerequisite evidence

Date: 2026-10-02 (Europe/Berlin). Base: `37b6000227ba4be353a4f1769e39e92073b1fced`.
Worktree branch: `codex/macos-native-capsule-runtime`.
Scope: approved specification revision and maintainer signing preflight, not a
production backend or signed boundary implementation.

The Developer-ID-first milestone recorded below is historical. The owner-approved
2026-10-02 signing split makes that utility optional; current acceptance is in
FEASIBILITY.md and the new scope-split evidence in TDD_EVIDENCE.md.

## Specification before tests

Updated proposal, design, feasibility, scenarios, tasks, requirement mapping and
change order before authoring preflight tests. The live #460 issue records the
managed-process decision, automatic first-use download and preserved historical
failures. OpenSpec strict validation passed. The staged requirement-evidence gate
passed at **planned** maturity with implementation evidence **not-yet-available**.

## RED and GREEN

- Added 21 focused preflight tests before `preflight.py` existed. Running
  `.venv/bin/python -m pytest tests/unit/test_macos_managed_signing.py -q --no-cov`
  produced 21 setup errors from the missing implementation file.
- Implemented explicit certificate/team/profile validation and bounded read-only
  native command probes. Re-ran those tests with `test_native_node_inputs.py`:
  **26 passed** (21 preflight, 5 previously prepared npm input tests).
- Independent read-only `review-agent` inspected the complete patch present at
  review time, including untracked prerequisite files: **No findings**. It also
  ran the 26 tests and two synthetic CLI JSON/exit-status checks. Subsequent edits
  only recorded the source-review blocker and this validation evidence.
- Actual local preflight without release configuration returned exit 2 and a
  blocked diagnostic. No candidate was compiled or executed by the preflight.
  Mocked success always retains `signed_boundary_verified=false` and
  `production_approved=false`.

## Repository gates

| Gate | Result |
| --- | --- |
| `hatch run format` | Passed |
| `hatch run type-check` | Passed: zero errors/warnings |
| `hatch run lint` | Passed |
| `hatch run yaml-lint` | Passed |
| `hatch run check-bundle-imports` | Passed |
| `hatch run verify-modules-signature --payload-from-filesystem --enforce-version-bump --public-key-file <paired-core>/resources/keys/module-signing-public.pem` | Passed: seven unchanged module manifests |
| `hatch run contract-test` | Passed: 28 selected contracts |
| `hatch run smart-test` | Passed: 3,364 tests, one Linux-only skip |
| `hatch run test -q --no-cov` | Passed: 3,364 tests, one Linux-only skip |
| `openspec validate code-review-native-platform-execution --strict` | Passed |
| Staged requirement-evidence gate, planned maturity | Passed; no runtime proof claimed |
| Actual native Code Review below | Failed; required platform execution remains unsupported |

Actual native command:

```sh
hatch run specfact code review run --scope full --enforcement changed --bug-hunt \
  --json --out .specfact/code-review-managed.json
```

Observed exit 1, overall FAIL, assurance UNKNOWN, with
`unsupported_controller_platform` for all ten analyzers. The unchanged released
runtime reports its existing Linux environment identity; this does not establish
native execution. The JSON remains ignored. Raw command logs remain outside the
repository and are not publication artifacts.

## Not passed

No release-signed boundary suite, supported-OS matrix, managed analyzer/project
execution, first-use runtime download or final signed customer installation was
completed. The source-derived startup gap is detailed in
[MANAGED_BOUNDARY_STATUS.md](MANAGED_BOUNDARY_STATUS.md). Native Code Review is
still a failing gate. No exception, signature bypass, version-only release, PR
claiming implemented support, merge or GHCR publication is justified by these
results. The OpenSpec change stays open.
