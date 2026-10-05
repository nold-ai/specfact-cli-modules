# Broker-owned offline uv children

Hatch 1.18.0 SHALL preserve the real upstream corpus and its selected
`installer = 'uv'`. The native preparation adapter SHALL select only
`<verified capsule>/tools/uv`, using Hatch's upstream explicit uv-path setting.
It SHALL supply the private wheelhouse with uv offline/no-index settings and
disable Python downloads and keyring acquisition. It SHALL NOT search host PATH,
substitute another installer, or edit caller/corpus configuration.

The Python subprocess adapter SHALL accept that exact packaged uv identity in
addition to existing Python identities. Unknown uv names, copied images,
symlinks, writable images and host paths SHALL fail before a broker request.
Working directories and environment path grants SHALL remain canonical and
inside the parent's project/output/temporary roots. uv children SHALL carry no
Python import overlays, publisher credentials, executable search path or
caller-supplied managed-channel identity.

Only private worker RPC SHALL select the internal uv child plan. The broker
SHALL transform the validated bounded request into a native startup envelope;
the traced bootstrap SHALL execute its fixed capsule uv image directly. Dynamic
signature admission SHALL require the existing exact uv designated requirement
before execution resumes. The child SHALL inherit the existing filesystem,
resource, deadline, streams, handle ownership, startup and recursive cleanup
protocols. Its sandbox SHALL deny network and process-fork, including when its
parent was an acquisition worker. The reviewed uv bridge SHALL retain inherited
broker pipes for its Python probes and build hooks; unsupported subprocesses
SHALL remain denied.

Focused tests SHALL establish program admission, environment/grant rejection,
Hatch's preserved installer and packaged-image selection, native child request
validation and network-denied dispatch. Native compilation in a separate private
directory SHALL establish build compatibility only. Authentic untouched Hatch
preparation, nested Python/build-hook completion, network/fork denial and
startup/owner-loss/cleanup proof against the resulting exact private capsule
remain required before reporting runtime acceptance.

## Focused evidence — 2026-10-05 (Europe/Berlin)

- Spec first: this contract preceded implementation. The first focused run
  reproduced rejection of the packaged uv child and missing Hatch configuration
  support (4 failing tests). The native parser then reproduced rejection of a
  valid offline uv request (1 failing test). A further failing test established
  case-insensitive credential rejection before that correction.
- Green: `hatch run python -m pytest -q -p no:cacheprovider
  tests/unit/test_macos_managed_uv_child.py
  tests/unit/specfact_code_review/run/test_native_managed_process.py
  tests/unit/specfact_code_review/run/test_native_project_hatch.py
  tests/unit/specfact_code_review/run/test_native_child_worker.py
  tests/unit/specfact_code_review/run/test_native_execution.py`:
  **95 passed, 9 skipped**. The skips are existing opt-in native/stall proof
  cases. The new native parser tests compile and execute the actual
  CoreFoundation request validation and bounded startup serialization; Python
  transport and Hatch-selection tests use fixtures.
- Focused Ruff lint/format checks pass. Focused type checking of
  `native_managed_process.py`, `native_project_hatch.py`, and the new native
  parser test reports **0 errors, 0 warnings**. SIM102 is corrected; stream
  metadata and type-narrowing assertions retain existing stream behavior.
- `native/macos-arm64/build.sh` compiled with its existing `-Wall -Wextra
  -Werror` settings into
  `/private/tmp/specfact-managed-uv-child-build-18c53kk7/components` and verified
  the resulting ad-hoc native signatures. The exact Python and reproducible uv
  designated requirements were read from the existing proof Python image and
  `/private/tmp/specfact-managed-uv-reproducible/bin/uv`.

The current proof capsule and real upstream Hatch corpus were not modified.
Existing sibling-import and reordered `-I`/ignored-PYTHONPATH behavior remains
covered and passing. This build has not been integrated into a new authenticated
capsule: actual untouched Hatch default-uv cold/warm preparation, nested
probe/build-hook execution, signature-substitution rejection, uv child network
and fork denials, and owner-loss/startup/recursive-cleanup proof remain pending.
The previously reported Requests/Flask and Python-child live proof does not by
itself establish acceptance of this new uv child plan. No files were staged and
no publisher signing or broad gates were performed for this bounded change.

## Hatch hook wheelhouse identity correction

Hatch hooks SHALL distinguish the disposable source project from the original
broker-admitted input project. Installer settings `UV_FIND_LINKS` and
`PIP_FIND_LINKS` SHALL reference only the original input project's immutable
`wheelhouse/`, while Hatch metadata, SCM queries and build work continue on the
disposable source. No alternate directory, installer fallback, additional grant
or network/fork permission is admitted. The subprocess adapter SHALL continue
rejecting copied or overridden wheelhouse paths before broker launch. Override
diagnostics MAY name the fixed environment field, but SHALL NOT include its
value or reveal private paths. Focused tests SHALL reproduce the original
hook-to-installer mismatch and establish unchanged original wheel bytes/modes,
correct inherited offline settings and continued override rejection.

### Correction evidence, 2026-10-05 (Europe/Berlin)

The new Hatch/input-root tests and fixed-field diagnostic tests first produced
**9 failures, 73 deselections**. `execute_hook` now passes its original input
project separately to Hatch; metadata/build work retains the copied source,
while both installer wheelhouse settings use the original input. No changes
were made to native C, assembly, grants, installer selection or network/fork
restrictions. The original wheel bytes and modes remain unchanged in tests.

After the separately requested Git relative-cwd correction, the final focused
command was:

```text
hatch run pytest -q tests/unit/specfact_code_review/run/test_native_project_hatch.py tests/unit/specfact_code_review/run/test_native_project_hooks.py tests/unit/specfact_code_review/run/test_native_managed_process.py tests/unit/specfact_code_review/run/test_native_managed_git.py
```

Result: **106 passed in 0.33 seconds**. Ruff and format checks passed on the
three owned modules and four focused test files. Basedpyright on those seven
files reported **0 errors, 0 warnings, 0 notes** using a private configuration
extending repository policy with static imports extracted from the existing
pinned Hatch 1.18.0 wheel. No package download, diagnostic suppression or runtime
configuration change was needed for that typecheck.

The authorized private proof refreshed trusted sources, reinstalled existing UV,
retained the already installed Git input, rebuilt the private native component
and assembled the capsule. It used the untouched complete Hatch checkout at
commit `d5f7bfe813dd4d81520def23b43f5d46aad1899c`, environment `hatch-test`, and
canonical files `src/hatch/utils/structures.py` and
`tests/utils/test_structures.py`. Source-only mode was disabled; cold preparation
was attempted before warm reuse and review.

The original UV wheelhouse override rejection was cleared. The next physical
failure is **`project_native_preparation_incomplete:hook:manager worker failed`**
after Hatch reported `Installing project`. A final rerun with both fixes recorded
22 successful native worker exits followed by a hook worker exit code **2**;
its inherited stdout was empty and stderr was **79 bytes**. Unfiltered output
and wait records remain private. No preparation-error receipt explained that
exit. Warm reuse and review were not reached, so authentic Hatch preparation
and full customer artifact compatibility remain unproven. That next worker
failure requires separate diagnosis within its owning scope; it was not hidden
by changing installers, corpus/configuration, confinement or failure policy.
No staging, commit, push or publisher/module signing was performed.

The resulting private capsule identity is
`sha256:36f79fb6d8b5938874a2080f716263179ab472c4c7be7eb86d4154e19e06d2a0`.
Its lease is candidate proof only; `production_eligible=false` remains in force.

## Hatch child failure diagnosis and exit receipts

Unsupported or failed upstream installer execution SHALL remain incomplete.
The hook entry point SHALL record a bounded project-origin `SystemExit` receipt
instead of silently losing the manager's exit code. Integer codes 0–255 and
`None` (code 0) MAY be recorded; arbitrary string/object exit values SHALL NOT
be published. Even code 0 without a hook result SHALL remain incomplete. These
receipts are untrusted diagnostics and SHALL NOT establish preparation success
or override broker authority. Temporary private argument/stream probes MAY
remove quiet verbosity flags solely for diagnosis; production launch behavior,
installer choice and confinement SHALL remain authoritative.

The bootstrap's fixed `UV_PYTHON` identifies the capsule image; it SHALL NOT
cause Hatch's install to target immutable capsule site-packages. For `uv pip
install`/`sync` in an upstream-selected private `VIRTUAL_ENV`, the adapter SHALL
explicitly select that environment's verified `bin/python` alias on the command
line. Admission SHALL require the existing private Python-prefix checks:
canonical inherited root, ordinary non-system-site pyvenv configuration, and an
alias resolving to the already admitted capsule interpreter. Caller interpreter
selectors SHALL either match that exact alias or fail before broker launch.
No new image, writable root, network grant, installer fallback or native C change
is admitted. Production verbosity flags SHALL remain untouched.

### Actual Hatch completion evidence, 2026-10-05 (Europe/Berlin)

Bounded private child tracing established that `uv venv` exited 0 and Hatch's
`uv pip install -qq --editable ...` exited 2. The original install produced no
child stream output because of `-qq`. A private probe removing only those quiet
flags exposed an attempted installation of `tomli-w==1.2.0` into the immutable
capsule's site-packages, denied with `Operation not permitted`. The bootstrap's
fixed `UV_PYTHON` selected the capsule instead of Hatch's private environment.
No stream-forwarding defect or stdin failure was established.

The hook SystemExit scenarios first failed **4 tests**; interpreter-target and
substitution scenarios then failed **8 tests** before their implementation.
The adapter now adds an explicit verified private `--python` target for UV pip
install/sync and preserves already matching explicit selectors. Missing,
foreign, substituted or system-site aliases remain rejected before broker
launch. Production `-qq` and other verbosity settings are unchanged. The hook
entry point returns incomplete with a bounded project-origin exit receipt when
upstream code calls SystemExit without a result.

Final focused tests:

```text
hatch run pytest -q tests/unit/specfact_code_review/run/test_native_managed_process.py tests/unit/specfact_code_review/run/test_native_project_hooks.py tests/unit/specfact_code_review/run/test_native_project_hatch.py tests/unit/specfact_code_review/run/test_native_managed_git.py
```

Result: **122 passed in 0.36 seconds**. Focused Ruff and formatting passed;
Basedpyright on the three owned modules and four test files reported **0 errors,
0 warnings, 0 notes**, using the same existing pinned Hatch static type inputs.

After removing private instrumentation through the normal trusted-source
refresh, the unchanged complete upstream Hatch fixture actually completed
**cold native preparation and offline warm reuse**, with identical prepared
environment identities. Source-only mode remained false. The resulting exact
private capsule identity is
`sha256:4debdf92faa1f46e6690c07dc74963889fa4f099d2c313efe5d2d8da61bd5151`.
All three owned module bytes in that capsule matched repository sources, and
the capsule contained no private trace instrumentation. Git was retained and
the existing UV artifact was reinstalled; native C and assembly source were not
edited. Raw arguments, diagnostic streams and proof logs remain private.

All nine independent analyzers executed with `execution_state=ran`: Ruff,
Radon, Semgrep clean, AI bloat AST, AST clean code, Basedpyright, Pylint,
contracts and Semgrep bugs. The complete review verdict was **FAIL**, not a
passing review claim. Targeted pytest remained `execution_state=error` with
`native_pytest_policy_projection_failed:coverage_policy_unsupported`. That
existing policy/approval scope was not modified or bypassed. Full pytest and
production customer artifact acceptance remain unproven; catalogs stay empty
and the private candidate remains `production_eligible=false`. No staging,
commit, push or publisher/module signing was performed.
