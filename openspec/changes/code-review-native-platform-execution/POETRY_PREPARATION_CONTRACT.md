# Bounded Poetry preparation — 2026-10-05 (Europe/Berlin)

This disjoint #460 adapter consumes the injected Poetry 2.4.3 dependency site
inside the existing confined, network-denied preparation worker. It never
launches a host manager or uses pip to impersonate Poetry.

The closed `.specfact-poetry.json` request contains exactly `schema`
(`native-poetry-request-v1`), `groups`, and `extras`. Nonempty groups mean
Poetry's `--only main,<groups>` selection, matching the released ProjectPlan
adapter; an empty list uses its nonoptional default groups.
Extras and groups are normalized and validated against the upstream project.
Requests are limited to 1 MiB and 128 unique names per selection.

`poetry.describe` validates an existing regular, fresh `poetry.lock` (at most
16 MiB); absent locks use the metadata resolution phase specified below.
Poetry's installer transaction selects dependencies for the actual worker
interpreter, groups and extras. A capture executor performs no installation.
At most 4096 selected index packages become validated exact requirements;
exact locked Git sources use the separate
[locked source contract](LOCKED_SOURCE_PREPARATION_CONTRACT.md). Other source
dependencies remain actionable incomplete results. Existing locks are never
regenerated. Existing lock format and marker semantics remain Poetry's responsibility.

`poetry.install` repeats selection, creates a private unseeded environment using
Poetry's environment builder and runs its installer. A narrow wheelhouse repository
and local download override preserve upstream wheel choice and archive hash
verification. Only regular bounded wheels in `project/wheelhouse` are candidates.
Custom indexes cannot be flattened safely and remain incomplete. Root package
mode uses the upstream editable builder in the same confined installation worker;
its declared build dependencies and dynamically requested editable dependencies
must be acquired before invocation. The reusable view binds project sources to
the review snapshot rather than a retired private preparation prefix. Plugins requiring
activation remain incomplete. Neither restriction silently changes the project.

Only the resulting site-packages is harvested. The parent must generate a fresh
sealed inventory; manager output never establishes output identity. Provenance
is `local_build`, and production eligibility is false. Native spawn/fork/shell
fallbacks are forbidden. The cp311 Poetry corpus preparation now has the
physical worker evidence below; cross-ABI and full analyzer acceptance remain
separate gates. Unit tests alone cannot establish capsule execution support.

Source inspected: supplied `poetry-2.4.3-py3-none-any.whl`, specifically
`factory.py`, `installation/installer.py`, `installation/chooser.py`,
`installation/executor.py`, and `utils/env/env_manager.py`. Supplied top-level
inputs also include `hatch-1.18.0-py3-none-any.whl`,
`uv-0.12.13-py3-none-macosx_11_0_arm64.whl`, and `hatch-closure/`.

## Focused evidence

All runs used the existing worktree test interpreter, Python 3.14.7 / pytest
9.1.1, and exactly:

```text
.venv/bin/python -m pytest tests/unit/specfact_code_review/run/test_native_project_poetry.py -q --tb=short
```

- Initial RED: exit 2, zero collected, one collection error because the adapter
  did not exist. Initial implementation GREEN: 12 passed in 0.13 seconds.
- Private scheme RED: 3 failed / 12 passed in 0.12 seconds. An intermediate
  editing error produced 4 failed / 11 passed in 0.14 seconds; corrected GREEN:
  15 passed in 0.10 seconds.
- Probe metadata RED: 1 failed / 16 passed in 0.13 seconds (Poetry includes
  non-destination metadata and a list of fallback paths). GREEN: 17 passed
  in 0.10 seconds.
- Harvest test initially had a missing test import: 1 failed / 17 passed in
  0.12 seconds; the test import was corrected without production changes.
- Wheelhouse alias RED: 1 failed / 18 passed in 0.16 seconds (alias accepted).
- Final GREEN: exit 0, **19 passed in 0.12 seconds**. Focused Ruff check passed;
  focused Ruff format check reported **2 files already formatted**.

Selection, source rejection, stale/missing locks, closed requests, lock wheel
hashes, private installation destinations and site-only harvesting are covered.
Lifecycle tests use test doubles for unavailable manager dependencies; they
are orchestration evidence, not authentic Poetry execution receipts.

The supplied inputs lack Poetry's complete manager dependency closure (including
Poetry Core, Cleo and installer). No host Poetry was installed or invoked, and
no dependency acquisition was performed. The parent must inject that closure,
wire the two operations and acquire exact locked SHA256 wheels, then exercise
virtualenv's managed probes and macOS xattr behavior in the real confined worker.
Missing lock SHA256 wheel entries, custom sources, plugins, unsupported build toolchains,
unsupported managed probes and split-site schemes remain explicit limitations.
Fresh parent inventory must reject invalid or escaping installed assets.

Confidence: medium for the bounded adapter; actual pinned-manager/physical-worker
execution remains unverified. Local inspection references the supplied upstream
2.4.3 wheel on 2026-10-05 (Europe/Berlin). Rolling back this slice means removing
only the three new owned files before parent wiring. No credentials or external
writes are involved.
No signing, commits, publication or full-repository acceptance is claimed.


## Locked Git corpus follow-up

The initial evidence above is historical. On 2026-10-05 (Europe/Berlin), the
unchanged Poetry corpus at `be56ff07db06e9b82574648433ca228e4cac549b` prepared
successfully using pinned Poetry 2.4.3, groups `main` + `test`, on native ARM64
Python 3.11.16. Exact Git acquisition, separate confined source build, original
Git identity installation and fresh target inventory are described and evidenced
in [the locked source contract](LOCKED_SOURCE_PREPARATION_CONTRACT.md).

`.specfact-poetry-source-wheels` stays separate from the index wheelhouse;
matching name/version filenames do not authorize source/index substitution.
Fresh native inventory and cache loads require `python_full_version` to match
that environment's exact `signed_versions()` resource row. Current known native
versions are 3.11.16, 3.12.14 and 3.13.14; no Linux patch version is inferred.

At the locked-source follow-up, missing-lock resolution was still incomplete.
The subsequent section specifies and proves the separate metadata acquisition
phase that closes the ordinary index dependency path.
Other Git hosts, Git LFS, submodules, symlinks and native source builds remain
explicitly incomplete. No complete analyzer corpus acceptance is claimed here.


## Missing-lock resolution follow-up — specified before implementation

Only an absent lock enables on-demand resolution. Existing regular locks still
must pass Poetry's freshness check; invalid, mismatched or symlink locks fail
without resolution. The original checkout and its manifest/lock remain untouched.

The confined network-denied `poetry.describe` extracts a closed, bounded metadata
request (1 MiB, 4096 dependencies) containing only static dependency/group/extra
metadata and name/version/Python constraints. It excludes build-system,
backend-path, plugins, project files and local manager configuration. Dynamic
project dependencies, custom indexes and unresolved direct sources are incomplete;
they are never replaced by index packages.

A separate sealed acquisition worker receives only that metadata and the pinned
Poetry 2.4.3 manager dependency site. Authentic upstream Solver and Locker resolve
all declared groups/extras and write the preparation lock. PyPI JSON, PEP 658 and
wheel metadata may be read as data. Source archive inspection and every direct
origin resolution entry point are denied before hooks or Git can run. Native
process fallback is forbidden. Solver failures and unavailable safe metadata
return incomplete with a concrete diagnostic.

The controller admits a regular bounded generated lock only after validating its
manager receipt, metadata binding and SHA256. It adds the lock only to the private
snapshot, reruns confined Poetry description/freshness validation, and uses the
existing authentic offline installer. The artifact retains `preparation.lock`
and its digest, labels `generated_preparation_lock=true`, and preserves original
checkout identity. Fresh inventory still binds the exact signed native Python
version. Provenance remains local_build; production eligibility remains false.

Required focused scenarios: absent lock emits metadata without solving in the
hook worker; existing stale locks reject unchanged; closed metadata excludes
hooks/config/sources; resolver denies sdist/direct sources; generated lock receipt
must match; a no-lock preparation resolves, revalidates and installs without
writing a caller lock. One actual minimal no-lock native preparation must prove
the pinned manager, generated lock and fresh installed dependency inventory.


### Missing-lock evidence and handoff

The specified sequence above is implemented in `native_project_poetry.py`, the
Poetry-only path plus new Poetry helpers in `native_project_runtime.py`, and the
closed acquisition dispatch in `native_project_pip.py`. Their three unit test
files changed. `native_project_source.py` and its tests were unchanged in this
follow-up. Parent-owned `_prepare_hatch_on_demand`, `_manager_phase` copy lines,
`_build_project_wheel` copy lines, C/protocol/process workers and other adapters
were not edited. Parent may now integrate its identity-bound snapshot helpers.

Poetry's CoreFactory first parses original declarations in the network-denied
worker. A whitelist preserves precisely dependency metadata relevant to Locker's
content hash, including Poetry groups and PEP 735 group includes. The network
worker receives no caller source files, build-system/backend-path, readme,
scripts, plugins or local Poetry configuration. Its sys.path includes only the
sealed manager dependency site and interpreter paths; no project path or analyzer
package site is added and `.pth` files are not executed. Actual upstream Solver
resolves all declared groups, and Locker writes format 2.1. Provider's direct-origin
entry point and HTTPRepository's sdist-inspection entry point fail before a clone
or build. Existing lock validation still occurs in the confined worker.

Focused command (Python 3.14.7 / pytest 9.1.1, worktree test interpreter):

```text
.venv/bin/python -m pytest tests/unit/specfact_code_review/run/test_native_project_poetry.py tests/unit/specfact_code_review/run/test_native_project_runtime.py tests/unit/specfact_code_review/run/test_native_project_pip.py -k 'poetry or resolution' -q --tb=short
```

- RED: exit 1, **16 failed, 23 passed, 64 deselected in 0.31 s**, before
  production changes. Failures covered new metadata functions, no-lock runtime
  orchestration, generated-lock evidence/receipt checks and sealed dispatch.
- First implementation: **1 failed, 38 passed, 64 deselected in 0.25 s**;
  the remaining failure was an undefined artifact variable in the new test.
  Correcting only that test produced GREEN: exit 0,
  **39 passed, 64 deselected in 0.25 s**.
- Initial broader RED also observed two parent Hatch failures during its active
  integration. These were left untouched. Final bounded regression command:

```text
.venv/bin/python -m pytest tests/unit/specfact_code_review/run/test_native_project_poetry.py tests/unit/specfact_code_review/run/test_native_project_runtime.py tests/unit/specfact_code_review/run/test_native_project_pip.py tests/unit/specfact_code_review/run/test_native_project_source.py -k 'not hatch' -q --tb=short
```

Final GREEN: exit 0, **114 passed, 2 deselected in 0.61 s**. Focused Ruff check
reported all checks passed; focused format check reported 6 files formatted.
No full repository gate, analyzer acceptance, commit or signing was performed.

Actual minimal native proof: private root
`/private/tmp/specfact-poetry-no-lock-proof-a3h_l9k5`, candidate copied from this
task's earlier private locked-source proof. Shared candidate and shared logs were
not used. `result.json`, `artifact/inventory.json`, `artifact/preparation.lock`
and the unchanged `caller/pyproject.toml` retain the evidence. The first harness
attempt failed before invoking workers because its config incorrectly wrapped
fields in `[project_runtime]`; correcting the harness to the repository's flat
configuration produced one successful actual preparation.

- COMPLETE in **21.528 s**, manager Poetry **2.4.3**, fresh target inventory
  **darwin-arm64-cp311 / CPython 3.11.16**.
- Main: `idna>=3.10,<4` resolved/installed **idna 3.20**; selected testing
  group: **iniconfig 2.3.0**; selected async extra: **sniffio 1.3.1**.
- Generated lock's upstream comment identifies Poetry 2.4.3; format **2.1**;
  group/extra/optional membership is retained.
- Preparation lock SHA256:
  `9f5727e49b7478de572484033287f02601556aa62fe48567ef548ddd3671858f`.
  Metadata content hash:
  `ed04552fd5f99d2ba4e7be4babea61113b107419879795e99a6bbdbb0fedfce1`.
- Fresh inventory found exactly the three expected distributions. Caller manifest
  bytes were unchanged and caller `poetry.lock` remained absent. Output labels
  generated_preparation_lock true, existing_lock_preserved false, local_build,
  production_eligible false and build_hooks_executed false (package mode disabled).

Limits remain concrete: stale existing locks intentionally reject rather than
refresh; unlocked Git/URL/file/path dependencies need independently authenticated
exact source metadata before resolution and currently return incomplete. A
transitive direct origin is blocked by Provider as well. Releases needing sdist
metadata are incomplete because backend inspection cannot happen in the network
domain; no synthetic dependency metadata or index replacement is supplied.
Dynamic dependency metadata, custom indexes and plugins require separate admission.
The actual no-lock proof is cp311 and package-mode=false; no new cross-ABI or root
editable no-lock physical proof is claimed. Parent retains full corpus/analyzer
integration authority. Rollback is limited to the new no-lock path and tests;
existing fresh-lock and authenticated Git paths remain independently usable.
Confidence: high for the proved minimal native index path; broader no-lock source
and metadata cases are explicitly incomplete.
