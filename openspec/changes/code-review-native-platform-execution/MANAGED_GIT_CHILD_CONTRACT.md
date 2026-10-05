# Managed Git SCM child contract

The authentic Hatch corpus retains its `hatch-vcs` configuration and
`git describe --dirty --tags --long --match hatch-v*` command. SCM results must
come from the packaged Git image and the sanitized VCS context supplied by the
snapshot owner. No version override, replacement installer, host PATH search,
customer compilation, publisher keys, or controller change is part of this work.

## Child admission

- Internal worker plan 30 selects only the exact capsule `tools/git` path and
  its compiled code requirement. The public controller cannot launch this plan.
- The Python adapter maps bare `git` and discovery of `git` to that image; it
  rejects foreign absolute executables and writable or substituted aliases.
- Queries are restricted to built-in SCM commands: version, describe, rev-parse,
  rev-list, log, status, symbolic-ref, ls-files, cat-file, show-ref, for-each-ref,
  diff, diff-index, and diff-files. Private `--git-dir`/`-C` selectors and the
  read-only `-c log.showSignature=false` selector support setuptools_scm.
- Bootstrap fixes global/system configuration, hooks, fsmonitor, optional locks,
  lazy fetching, pager, protocols, maintenance and signature display. Caller
  Git configuration/environment cannot replace these controls. No PATH is
  supplied. Repository access remains bounded by the parent's filesystem grants.
- Network and fork stay denied in the kernel. External commands, hooks, filters,
  transports, recursive subprocesses and signature programs are unsupported.
  The same traced startup, FD ownership, streams, budgets, deadline, cancellation
  and owner cleanup apply. `describe --dirty` is supported only if physical
  evidence confirms Git's ordinary in-process path under these restrictions.
  For Git, both profile executable parameters name `tools/git`; Python is not
  an additional executable grant. Startup FD 3 is consumed before execution and
  unused managed RPC FDs 5/6 are closed. Caller locale/XDG settings cannot shadow
  fixed bootstrap values through duplicate environment entries.

## Maintainer artifact

Pin Git 2.54.0, release commit `94f057755b7941b321fd11fec1b2e3ca5313a4e0`,
official archive SHA-256
`f689162364c10de79ef89aa8dbf48731eb057e34edbbd20aca510ce0154681a3`.
The digest is published in the HTTPS-delivered, PGP-signed
[kernel.org checksum manifest](https://www.kernel.org/pub/software/scm/git/sha256sums.asc)
(accessed 2026-10-05). The builder accepts this local archive only, verifies it
before extracting bounded ordinary files into disposable source, and performs
one bounded offline build of the `git` target. No downloads occur in the builder.

Only built-in Git code is installed. Curl/OpenSSL/Expat, language helpers,
third-party package discovery and Unix sockets are disabled. Git's own libraries
are linked internally; remaining dynamic dependencies must be Apple platform
libraries. Record exact compiler/SDK, flags, pin, system dependencies, digests,
GPL license and corresponding upstream source. Ad-hoc hardened signing uses
`ai.nold.specfact.managed-git`; publication and module signing remain separate.
Reproducibility is scoped to the recorded toolchain/SDK, not different macOS SDKs.
The three upstream documentation/GUI symlinks are omitted from extracted build
inputs; their original contents remain in the corresponding source archive.
Standalone Git, sha1dc and reftable license files accompany that archive. The
checksum was checked against the official HTTPS manifest; this bounded proof
does not claim independent OpenPGP verification of the upstream release.

## Verification

Specification precedes failing focused tests, implementation and passing tests.
Physical candidate evidence must distinguish query/parser checks from actual
broker execution and authentic corpus preparation. Full Hatch/Pytest corpus
proof belongs to the parent integration and must not be inferred from fixtures.

### Evidence recorded 2026-10-05

- Initial focused run: 5 failures, 9 passes and 7 missing-builder errors. The
  native parser test also failed before the Git policy header existed. The final
  environment-shadow regression was demonstrated failing before its fix.
- Final focused unit/parser/regression selection: **139 passed, 9 skipped**.
  The skips are the existing opt-in native/stall proofs. Receipt:
  `/private/tmp/specfact-managed-git-focused-proof.xml`.
- Opt-in physical broker test: **1 passed** with
  `SPECFACT_GIT_PROOF_CAPSULE=/private/tmp/specfact-managed-git-proof-capsule`.
  It verifies packaged discovery, the exact upstream version, real clean/dirty
  tag descriptions, commit identity/date, SCM status, owned cancellation,
  transport rejection and independent direct-fork denial. Receipt:
  `/private/tmp/specfact-managed-git-live-proof.xml`.
- Native build succeeded with `-Wall -Wextra -Werror`; all four components passed
  strict code-signature verification. Output:
  `/private/tmp/specfact-managed-git-native-components`.
- Focused BasedPyright: **0 errors, 0 warnings**. Ruff lint and format checks pass.
- Two separate disposable-source builds produced byte-identical signed Git:
  SHA-256 `b74f67c02cc24a7b966082a8d40c1e4900a1d905f08247a8006855b0bdace4fb`;
  CDHash `851a6fd3c30945eab744a399d27349e1ee5b1252`.
  `/private/tmp/specfact-managed-git-reproduction-proof.json` records comparison.
  Apple clang 21.0.0 (`clang-2100.3.34.2`), macOS SDK 27.0, GNU Make 3.81.
  Dynamic closure: Apple CoreServices, libz, libiconv and libSystem only.
- Eight standalone clean/dirty SCM queries also passed using the unchanged
  native profile with acquisition disabled. An initial simplified standalone
  profile missed macOS runtime-library permissions and aborted before queries;
  it was replaced by the existing profile without widening that profile.

The focused selection was:

```text
tests/unit/test_macos_managed_git_child.py
tests/unit/specfact_code_review/run/test_native_managed_git.py
tests/unit/test_build_macos_managed_git.py
tests/unit/test_macos_managed_uv_child.py
tests/unit/specfact_code_review/run/test_native_managed_process.py
tests/unit/specfact_code_review/run/test_native_child_worker.py
tests/unit/specfact_code_review/run/test_native_project_hatch.py
tests/unit/specfact_code_review/run/test_native_execution.py
```

The physical test was
`tests/unit/specfact_code_review/run/test_native_git_live_process.py`.
The only existing test adjustment synchronizes the internal maximum plan and
asserts that public launch admission rejects the Git child plan.

### Parent integration and limits

Use `/private/tmp/specfact-managed-git-reproduced/bin/git` as the capsule
`tools/git` input and pass its sibling `git.requirement` through
`SPECFACT_GIT_REQUIREMENT_FILE` when building native components. This reproduced
candidate includes the final license set, source, digests and provenance.
The private proof capsule is a separate copy; the parent's shared capsule and
authentic Hatch/Pytest repositories were not modified.

Confidence is high for the narrow SCM/build evidence and medium for authentic
corpus compatibility until parent integration passes. A snapshot must contain
the real sanitized object/ref/index context; missing tags or shallow history
cannot be repaired by inventing a version or fetching. Any command needing a
helper process fails under fork denial. Missing/substituted images fail identity
admission; callers cannot opt into host Git or override the fixed configuration.
No full gate, publisher/module signing, staging, commit or controller edit was
performed. Existing policy-blocked tests were not touched. Build work is capped
at four jobs and 600 seconds per invocation; the builder performs no downloads.
Rollback is limited to the Git adapter/internal-plan additions and private
artifact inputs; absent Git requirements default to an impossible code identity.

## Explicit capsule assembly and maintainer preparation

The candidate install helper accepts an explicit `git_artifact_root`. It verifies the
complete immutable artifact inventory, official source pin, ordinary-file
layout, ARM64 Apple-only closure, hardened ad-hoc identity and exact
`git.requirement`/CDHash agreement before copying. Candidate payload uses
`git/bin/git`, `git/licenses/*`, and `git/provenance/*`; assembly maps these to
`tools/git`, `licenses/managed-git/*`, and `provenance/managed-git/*`. Raw
`build.log` is not installed. A complete installation receipt binds every copied
file. Assembly rechecks it against the candidate inventory and observed image;
Git cannot silently substitute for this input or collide with another mapping.

The native component must contain the exact compiled Git requirement and its
observed broker CDHash must match component metadata. Assembly records that
binding in native-component provenance. The capsule packer rechecks the Git
image/requirement/broker binding before creating any archive or manifest output.
These checks bind a candidate produced by the reviewed maintainer workflow;
ad-hoc signatures do not independently authenticate an external publisher.

`build_macos_native_capsule.py prepare-managed-git` is a separate key-free
maintainer route. It accepts either the pinned local source archive (calling the
existing reproducible Git builder) or an already verified Git artifact. It only
installs the verified input. The authoritative analyzer preparation route uses
`SPECFACT_MANAGED_GIT_ARTIFACT` and preserves the original Git signature without
re-signing or rewriting the image. The existing native validator uses
`SPECFACT_GIT_REQUIREMENT_FILE` pointing at `git/provenance/git.requirement` and
then builds the broker requirement from that exact tool; assembly checks the
resulting binding. No network fetch, host Git fallback, manifest/module/publisher
signing or catalog update occurs. Output is fresh, private and candidate-only;
failure removes only work owned by this invocation. Empty catalogs and
`production_eligible=false` remain unchanged.

### Stable install API and input layout

Both arguments must be canonical absolute existing ordinary directories; the
candidate payload must be writable and must not already contain `git/`.

```python
from pathlib import Path
from scripts.build_macos_native_capsule import install_managed_git_input

candidate["managed_git"] = install_managed_git_input(
    Path("/private/tmp/specfact-managed-git-reproduced"),
    candidate["payload"],
)
```

The helper returns the same canonical JSON object saved as
`git/provenance/input.json`. Its `files` entries use paths relative to `git/`
and contain size in bytes and SHA256. Exact installed files are:

```text
git/bin/git
git/licenses/Git-COPYING
git/licenses/sha1dc-LICENSE.txt
git/licenses/reftable-LICENSE
git/provenance/git.requirement
git/provenance/git-2.54.0.tar.xz
git/provenance/input.json
```

`SPECFACT_GIT_REQUIREMENT_FILE` must point to the installed
`git/provenance/git.requirement` when building the native component. Assembly
requires the candidate's `managed_git` object to equal this receipt, observes
the Git and broker signatures, and checks that the exact NUL-terminated Git
requirement is compiled into the broker. This check assumes the reviewed native
component build; a matching string inside an arbitrary ad-hoc signed image is
not independent source or publisher authentication.

The CLI equivalent is `build_macos_native_capsule.py prepare-managed-git
--git-artifact-root <canonical-artifact-root> --payload-root
<canonical-payload-root>`. For a source build, replace the artifact option with
`--source-archive <pinned-local-archive> --git-build-output <fresh-output>`;
`--jobs` is bounded to 1–4. Neither route accepts a signing key. Authoritative
analyzer preparation uses `SPECFACT_MANAGED_GIT_ARTIFACT` with the same helper.
The original Git image is verified without re-signing, and its receipt is
rechecked after preparation. Assembly places the image in `tools/git`, the
licenses in `licenses/managed-git/`, and provenance in `provenance/managed-git/`.

### Integration evidence, 2026-10-05

Installer specification tests initially failed 10 cases before implementation.
The next assembly/packer/preparation RED run had 14 failures, 12 passes and
60 deselections. After implementation, all 26 selected Git integration cases
passed. The final focused command was:

```text
hatch run pytest -q tests/unit/test_assemble_macos_native_capsule.py tests/unit/test_build_macos_native_capsule.py tests/unit/test_macos_python_analyzers_managed_git.py tests/unit/test_build_macos_managed_git.py
```

Result: **93 passed in 0.98 seconds**. Ruff check and format check passed for
the three integration scripts and their three focused test files. Basedpyright
on those same six files reported **0 errors, 0 warnings, 0 notes**.

The reproduced artifact was actually installed and reverified in the separate
private input `/private/tmp/specfact-managed-git-install-integration-proof`.
Its binary retained SHA256
`b74f67c02cc24a7b966082a8d40c1e4900a1d905f08247a8006855b0bdace4fb`
and CDHash `851a6fd3c30945eab744a399d27349e1ee5b1252`. The real broker in
`/private/tmp/specfact-managed-git-native-components` also passed the compiled
requirement and observed broker identity checks. No rebuild or publisher/module
signing occurred in this integration turn; only tests used ephemeral fixture
manifest keys.

The parent's physical Hatch run remains the next proof. This evidence does not
claim full customer artifact compatibility or broader CI coverage. The
implementation is frozen for that integration; no files were staged or
committed, and the shared private capsule, controller, catalogs and
policy-blocked tests were not changed.

## Relative managed Git working directories

Git query admission SHALL use the same canonical, inherited-grant working
directory admitted by the general subprocess adapter. A relative `cwd='.'` or
contained subdirectory SHALL support relative `-C` and `--git-dir` selectors
exactly as an absolute cwd does. This SHALL NOT resolve noncanonical traversal
or symlinks into admission, or broaden repository grants. Host/escaping cwd and
selectors SHALL continue failing before any broker request.

The relative-cwd specification produced **4 failures, 5 passes and 15
deselections** before implementation. Query admission now reconstructs its base
from the general adapter's already validated cwd grant instead of accepting an
unnormalized relative `Path(cwd)`. All 24 focused Git adapter cases pass,
including traversal, symlink and foreign-root rejection. The combined
Hatch/hooks/process/Git scope passes **106 tests**, with clean Ruff/format and
zero typecheck errors/warnings. The initial private Hatch rerun included this fix
but exited after Hatch reported `Installing project`, with hook worker code 2.
The subsequent interpreter-target correction and actual cold/warm Hatch
completion are recorded in `MANAGED_UV_CHILD_CONTRACT.md`; that proof also ran
all nine independent analyzers. Targeted pytest remains incomplete under the
existing unsupported coverage-policy projection. Focused adapter tests alone
do not establish SCM/corpus completion or release acceptance.
