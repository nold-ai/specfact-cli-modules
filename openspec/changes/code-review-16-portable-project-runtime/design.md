# Design: portable project runtime

## Interface and data flow

Keep existing review invocations. Add `specfact code review runtime inspect --json`, `runtime prepare --json`, `run --project-config PATH`, and `run --project-runtime PATH`. Inspect is read-only. Prepare is also invoked automatically for dependency-sensitive analysis.

A package-manager-neutral project plan records manager/environment, Python constraints, dependency and configuration input hashes, selected extras/groups, source roots, pytest policy and declared native libraries. Explicit project configuration wins; verified active context precedes unambiguous repository discovery. Conflicts fail with one actionable diagnostic. Build backend declarations alone do not identify environment managers. Adapters preserve manager semantics and never merge every optional environment.

Prepare in a disposable writable copy using a namespace-isolated builder and a verified capsule interpreter. Separate network dependency acquisition from offline analysis. Do not expose publisher credentials or import project code in the controller. Record manager versions, exact installed distributions, payload and input digests. Cache artifacts outside the source checkout, verify warm reuse, reject symlink/path escape and partially published artifacts. Preserve original manifests, locks and environment files. Native imports report missing shared libraries explicitly.

The v2 descriptor supports local artifacts and binds inputs, platform/ABI and worker identities. It is local build provenance, never an invented publisher attestation. Retain the v1 reader unchanged. Dependency changes across base/head require independent preparations. Dirty/index sources bind their own content, not just HEAD. The host supervisor remains sealed; project dependencies and plugins execute only in disposable target workers. Ordinary package names are allowed in those workers but cannot shadow control entry points. Genuine tool/project constraints conflicts produce UNKNOWN, not changed project pins.

## Pytest and report semantics

Honor configuration precedence, plugin activation, import mode and source roots. Observe actual collection and execution; preserve selected policy and do not suppress controls silently. Unsupported options name the precise reason. Preparation failures retain independent static evidence and produce one root diagnostic referenced by dependent analyzer members. Genuine missing imports after successful preparation remain findings. Local v2 evidence is not eligible for protected pr_range promotion; the existing v1 trust path is unchanged.

## Validation and delivery

Freeze Requests, Hatch, Flask and Poetry commits from the accepted plan. Run real source/test slices under pip/Hatch/uv/Poetry on non-root Ubuntu 24.04 for CPython 3.11/3.12/3.13. Include a labelled reconstruction of #472, cold/offline-warm paths, ordinary GITHUB_ACTIONS, changed lock, corruption, native imports and controlled defects. Required applicable analyzer completion is independent of zero findings. The signed public release repeats the candidate matrix. Keep #472 open pending original customer reproduction.

Run all canonical quality/signature/review/Requirements gates and fix PR findings. Limit corpus jobs to 90 minutes and record actual seconds/bytes. Roll back through reviewed revert and new signed publication; never mutate immutable published payloads. Archive only through openspec after merge and acceptance.

Private VCS context is an explicit object export, not a repository clone. The selected commit, captured index tree, recorded tags and shallow boundary define its object closure. Git plumbing transfers only that closure into fresh metadata; unrelated refs, reflogs, unreachable objects, alternates and source-local configuration are not imported. This preserves SCM version inputs while binding cache reuse to the Git state build hooks can observe.

Target startup installs analyzer-owned import resolution before project paths are processed by site initialization. Verified analyzer origins and namespace search locations must stay under the member installation. This governs ordinary import resolution and detects unexpected preloads; it does not claim that a Python import finder sandboxes arbitrary project code within the same interpreter. Project code remains confined to the isolated target worker, and project-owned graph dependencies retain their selected versions.

### Pylint namespace source-root defaults

The attached worker's validated snapshot import paths (explicit source roots and installed editable hooks) are the authority for Pylint fallback source roots. Pylint's native Run initializes an ordinary PyLinter with these defaults before its own repository configuration and CLI parsing. This avoids independently duplicating config selection, preserves explicit empty values, and keeps the standard picklable analyzer object for parallel execution. Defaults put nested roots before ancestors because Pylint resolves the first matching source root. Installed wheel paths and guessed `src/` paths are not added.

The frozen Poetry corpus declares three independently verified import statement locations. Both cold and warm acceptance reject E0401/E0611 at these exact locations; unrelated findings remain admissible. This guard distinguishes completed execution from demonstrated import-resolution fidelity and will run again for the signed candidate and public release.

### PR #475 configuration and targeted discovery fidelity

The pip adapter uses native pip installable-directory markers (`pyproject.toml` or `setup.py` as regular files); `setup.cfg` remains a configuration input independently of package installation. Pytest targeted selection expands native configured test paths before inspecting matching Python files, preserving repository containment, excluded environments, recursion settings and the no-match repository fallback. Full reviews continue to delegate collection to pytest.

Build diagnostics are a controller resource. Preparation opens a unique private regular log outside builder-writable mounts before execution and passes its descriptor for stdout/stderr capture. Native-manager diagnostics flow through that stream. Failure retention never reopens builder-owned paths; successful logs are closed and removed. The public diagnostic references the private log without embedding repository-controlled output.

The builder artifact crosses the trust boundary only after metadata-only topology validation. Immediately after builder exit, the controller rejects any symlink or special node, including at the artifact root, before opening inventory JSON or enriching native libraries. Final sealing revalidates the enriched tree. This ordering prevents a builder-created native directory alias from redirecting host-side library copies or permission changes.

### Nested Python execution context

The supervisor always enters target workers through the sanitizing `target_command` namespace boundary. The generated project-runtime Python executable is used only inside those workers; its nested entry point reuses the inherited isolation and directly executes trusted native Python startup, preserving application environment additions/removals, cwd and private temporary files. No environment marker selects a less isolated initial launch. A read-only bind of a trusted built-in member file identifies the current dependency domain by file identity, surviving an explicitly empty child environment. Nested Python keeps that already-mounted member graph; it cannot add analyzer mounts. Required runtime startup variables remain controlled, and options that disable required attachment (`-I`, `-E`, `-S`) retain explicit diagnostics. This is a first-entry/nested call-path separation and dependency-domain indicator, not a new authorization framework.

### PR #475 hardlink follow-up

Build-output topology is an execution boundary, independent of the earlier source-symlink scope. Require single-link regular files during pre-enrichment validation and payload sealing/reuse. The driver copies installed distributions into the artifact, so package-manager hardlinks need not survive this boundary. Reject linked entries before reading their content; retain controller failure diagnostics privately. Stream builder stdout through a pipe with bounded reads and a controller-owned binary log; the builder never inherits the regular capture descriptor. Preserve timeout and downstream failure retention, and close the subprocess and capture resources on every exit. Tests reconstruct the filesystem condition using disposable log bytes and do not claim reproduction of the review's Linux `/proc`/bind-mount attack path.

### PR #475 diagnostic and nested import-path follow-up

Keep stable controller error codes and numeric exit status in public preparation diagnostics, alongside the existing private log path. Treat arbitrary exception text and paths as untrusted diagnostic content. Preserve existing log capture and retention without adding diagnostic writes or changing descriptor lifetime. Nested project PYTHONPATH is application configuration: retain it after the trusted startup directory without widening namespace mounts or changing analyzer import ownership.
