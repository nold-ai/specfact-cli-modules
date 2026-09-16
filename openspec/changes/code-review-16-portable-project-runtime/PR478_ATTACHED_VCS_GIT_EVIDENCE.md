# PR #478: retain declared Git during sanitized VCS export

The native run `35081982712` exposed `FileNotFoundError: git` in VCS context
inspection: the worker exposes declared Git in its private runtime `bin`, while
VCS inspection intentionally resets PATH to the system default. The canonical
OpenSpec scenarios were added before the regression tests and production edit.

`PR478_ATTACHED_VCS_GIT_RED.txt` records seven failing regression cases and one
passing host-isolation control before the correction. The positive regression
executes actual Git through a fixture launcher while the system-default PATH
contains no Git; it reproduced the original missing-executable failure.
Negative cases require precise rejection of undeclared, differently owned,
changed, missing or symlinked launchers and a copied rather than inherited
worker-context inode. The synthetic mount layout is a host test fixture; it is
not Linux namespace acceptance evidence.

The correction reuses `target_launch.execution_domain()` to verify the existing
read-only startup context. Only in that context can VCS select the fixed
attached `bin/git`, and only when the runtime descriptor declares Git and the
controller-generated inventory digest matches a contained regular launcher.
The complete artifact was already verified before worker entry; this check does
not attempt a new independent whole-artifact attestation. Host lookup still
uses only `os.defpath`. Neither ambient PATH nor environment markers select the
attached executable. All existing Git configuration, hook, replacement-object,
graft, network acquisition and prompting controls remain unchanged.

The positive regression was then parameterized by Git isolation control to
retain individually attributable checks without duplicating the production
configuration literal. Final focused validation on 2026-09-16:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-473-core .venv/bin/python -m pytest \
  tests/unit/specfact_code_review/run/test_runtime_vcs.py \
  tests/unit/specfact_code_review/run/test_snapshot_activation.py -q --tb=short
```

Result: **69 passed in 10.09 seconds**, macOS, Python 3.14.7, pytest 9.1.1.
Focused BasedPyright found zero errors or warnings; Ruff lint/format passed.
Direct Pylint reported only ten unchanged protected-member accesses in earlier
VCS tests, and no production or newly added test findings. New production helper
complexity is eight and three. The subsequent real Linux capsule run remains
required before claiming native acceptance.
