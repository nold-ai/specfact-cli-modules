# Locked source preparation — 2026-10-05 (Europe/Berlin)

The Poetry 2.4.3 describe operation partitions selected transaction operations
into bounded index requirements and locked source declarations. Git declarations
retain package name/version, HTTPS URL, requested reference, exact 40-hex resolved
commit and optional source subdirectory. A mutable branch or tag alone is not
an acquisition authority. No lock or project manifest is rewritten.

A closed data-only request runs in the existing sealed acquisition worker.
Initial supported transport is GitHub HTTPS repositories. Credentials, arbitrary
URLs/redirects, submodules, symbolic links, special files and Git LFS pointers are
rejected. Other HTTPS Git hosts produce an explicit unsupported transport result.
No Git executable, backend, project import or hook executes in this domain.
Authenticated GitHub commit metadata must return the requested exact commit and
root tree. Recursive tree metadata must be complete. The bounded commit archive
is extracted as regular files; each blob hash, executable mode and directory tree
hash must reconstruct that root tree. Unexpected, missing or altered files fail.
The source receipt binds the URL, commit, tree, archive digest and fresh inventory.

The controller revalidates the acquired tree before sending a disposable copy to
its existing confined network-denied build worker. Declared and hook-returned
build requirements are acquired separately as wheels. Resulting pure Python
wheels are inspected in a fresh sealed process and inventoried after hook exit;
manager/hook output cannot establish artifact identity. Only compatible `none-any`
wheels without native executable members are admitted by this initial surface.

A separate immutable `.specfact-poetry-sources.json` binding carries source
identity and the controller-inventoried local wheel digest into Poetry install.
The upstream installer retains its Git Package and lock semantics. A narrow
Executor Git archive override returns only that matching local wheel; Poetry's
normal wheel installer and PEP 610 provenance record the original Git URL,
requested reference and resolved commit. It never clones or invokes Git in the
network-denied installer, and never substitutes a PyPI package for a Git operation.
All selected source declarations must have exactly one matching wheel binding.
Source build provenance remains `local_build`; production eligibility is false.

Missing-lock ordinary project resolution is a separate uncompleted requirement:
it must eventually use authentic Poetry resolution in a disposable project, with
safe index metadata and locked source acquisition separated from hook execution.
Existing stale locks still fail rather than being silently updated.

## Evidence

All focused commands used the existing worktree Python 3.14.7 / pytest 9.1.1:

```text
.venv/bin/python -m pytest tests/unit/specfact_code_review/run/test_native_project_source.py tests/unit/specfact_code_review/run/test_native_project_poetry.py tests/unit/specfact_code_review/run/test_native_project_runtime.py tests/unit/specfact_code_review/run/test_native_project_pip.py -q --tb=short
```

Initial source RED: exit 2, 21 collected / one collection error (source module
missing). Controller lock-binding RED: 1 failed / 39 deselected in 0.17 seconds.
Initial integrated GREEN: 71 passed in 0.31 seconds. Wheel metadata validation
RED: 1 failed / 2 passed / 26 deselected in 0.12 seconds. Exact-version inventory
RED: 5 failed / 40 deselected in 0.20 seconds; after implementing the gate,
four older mocked inventories failed because they lacked required version data.
Updating those fixtures produced 95 passed in 0.60 seconds. Explicit verified CA
RED: 1 failed / 12 deselected in 0.09 seconds. Source/index separation RED:
1 failed / 45 deselected in 0.19 seconds. Both now pass.
Latest integrated GREEN: **100 passed in 0.60 seconds**. Final scoped Ruff
check passed; format check reported **8 files already formatted**. No full
repository gates are claimed.

An independent private candidate copy completed authentic Poetry 2.4.3 corpus
preparation in **43.160 seconds**. Fixture commit:
`be56ff07db06e9b82574648433ca228e4cac549b`. Configured groups: `main` + `test`.
Fresh sealed inventory: `python_full_version=3.11.16`; 60 distributions installed.
Both fixture Git status and lock preservation hash were checked after execution.
The corpus manifest and lock were not altered.

Locked Poetry Core source commit:
`b9663e42c808543377ae523611c4cfad68016f30`; authenticated root Git tree:
`3f58840ee4b56aab57db23973596a7268aaf1ec4`; 618 files verified. Original executable
modes were checked at extraction and cryptographically reconstructed thereafter;
read-only controller transfer intentionally strips filesystem executable bits.
Built wheel: `poetry_core-2.4.1-py3-none-any.whl`, SHA256
`7c35224877642d2f841fbfd9fd3a6d390b54f6f00fc629de3296e4ba804dddc3`.
Its installed `direct_url.json` retains the original HTTPS Git URL,
`requested_revision=HEAD` and the exact locked commit. No PyPI substitution
was made for the Git operation.

Private physical evidence:
`/private/tmp/specfact-poetry-locked-source-proof-jvefkwor/proof-summary.json`,
`authenticated-source.json`, `result.json`, and `artifact/inventory.json`.
The shared `/private/tmp/specfact-project-driven-proof/capsule` and its logs
were only read to create this independent copy. No signing keys were used.

Physical failing-before iterations exposed candidate directory permissions,
confined helper import isolation, unavailable default TLS CA paths, and a
read-only acquired tree copied into hook inputs. Corrections stayed in owned
Python source or this task's private candidate. HTTPS still verifies certificates
and hostnames using sealed bundled CA data; there is no insecure TLS or host Git
fallback. Only disposable input roots become writable before dependency injection.

Confidence: high for this locked cp311 preparation path; other ABIs and full
analyzer acceptance are unverified by this follow-up. Missing-lock resolution,
non-GitHub transports, LFS, submodules, symlinks and native source builds remain
incomplete. Existing exact locks are never regenerated. The parent can consume
the owned Python changes and private proof summary before wider acceptance.
No commit, publication, signing, agents, or full gates were performed.

## Exact native interpreter inventory

Every fresh native site inventory must report `environment.python_full_version`
exactly equal to `signed_versions()[runtime.environment_id]`. Missing signed
native metadata, missing inventory metadata and alternate patch versions are
incomplete preparation, even when the declared ABI matches. Existing inventory
and CI keys remain unchanged. No host interpreter or Linux version row can stand
in for the fresh sealed native worker's `default_environment()` value.
