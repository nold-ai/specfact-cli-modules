# Native analyzer compatibility inputs

These are maintainer candidate inputs for fixed, repository-authored fixtures.
They do not enable the production Code Review command. Customers will not need
uv, Homebrew, Xcode or any of these preparation steps.

The three CPython 3.11–3.13 Darwin ARM64 locks pin 94 Python distributions with
artifact hashes. BasedPyright and Node are packaged separately through
[the offline Node runbook](../native_node_inputs/README.md). Linux capsule pins
and identities are unchanged. Semgrep 1.175.0 and MCP 1.29.0 are native candidates
matching the paired core security floor; this is not signed policy admission.

## Prepare and install

Use a disposable maintainer directory under ignored `.specfact/`, with no
customer repository or credentials. Supply native ARM64 CPython and uv on the
maintainer machine. The actual compatibility matrix used Python 3.11.16, 3.12.14
and 3.13.14. Absolute paths below are placeholders to replace, not PATH lookups.

1. Package the authenticated Node/BasedPyright archives using the linked runbook.
2. Download the Z3 wheel from `UPSTREAM_URL` in `scripts/native_z3_wheel.py`.
   The offline preparation command verifies its pinned hash, corrects only
   documented metadata and records downstream provenance:

   ```sh
   /absolute/python scripts/native_z3_wheel.py \
     /absolute/inputs/z3_solver-5.1.0.0-py3-none-macosx_13_0_arm64.whl \
     /absolute/new-z3-candidate
   ```

   The output directory must not exist. The downstream distribution is visibly
   named `z3-solver==5.1.0.0+specfact.1`; its native/source/license bytes are
   unchanged. Normal resolution must use this version, not a renamed upstream
   archive or a resolver bypass.
3. Create a native environment and install the matching lock, for example:

   ```sh
   /absolute/uv venv --python /absolute/cpython3.11 /absolute/native-venv
   /absolute/uv pip sync --python /absolute/native-venv/bin/python \
     --require-hashes --only-binary :all: --find-links /absolute/new-z3-candidate \
     scripts/native_analyzer_inputs/darwin-arm64-cp311.txt
   /absolute/uv pip check --python /absolute/native-venv/bin/python
   ```

   Repeat with the cp312/cp313 lock and matching interpreter. Do not use
   `--no-deps`, PyPI BasedPyright or `nodejs-wheel-binaries`.

The reviewed generation command for each Python minor was:

```sh
MACOSX_DEPLOYMENT_TARGET=14.0 /absolute/uv pip compile \
  scripts/native_analyzer_inputs/requirements.in \
  --python-version 3.11 --python-platform aarch64-apple-darwin \
  --only-binary :all: --generate-hashes --no-header --no-annotate \
  --find-links /absolute/new-z3-candidate \
  --output-file scripts/native_analyzer_inputs/darwin-arm64-cp311.txt
```

Lock regeneration can select newer transitive dependencies and requires review;
reproduction of the recorded run uses the committed locks. The minimum OS tag
is a candidate constraint, not macOS 14 acceptance proof.

## Run the ten real adapters

Create an ignored JSON configuration using absolute paths:

```json
{
  "python": "/absolute/native-venv/bin/python",
  "tools": {
    "ruff": "/absolute/native-venv/bin/ruff",
    "radon": "/absolute/native-venv/bin/radon",
    "semgrep": "/absolute/native-venv/bin/semgrep",
    "pylint": "/absolute/native-venv/bin/pylint",
    "crosshair": "/absolute/native-venv/bin/crosshair"
  },
  "node": "/absolute/native-node-runtime/bin/node",
  "basedpyright_js": "/absolute/native-node-runtime/basedpyright/index.js",
  "system_tools": {"uname": "/usr/bin/uname"},
  "ca_bundle": "/absolute/native-venv/lib/python3.11/site-packages/certifi/cacert.pem"
}
```

```sh
/absolute/native-venv/bin/python scripts/native_analyzer_smoke.py \
  --config /absolute/ignored-config.json > /absolute/ignored-receipt.json
```

The harness runs only embedded clean/defective fixtures using the actual module
adapters. It checks findings, tool exits and versions. Missing members and UNKNOWN
results fail; all ten members must pass. Each worker has a private HOME/TMPDIR
and configured-only PATH. Timeout/output observation and ordinary process-group
cleanup protect the maintainer test run; they are not a security boundary or a
broker-death guarantee. Project-controlled inputs are not accepted.

Every receipt states `native_compatibility_only`, `sandbox_verified=false` and
`production_eligible=false`. It cannot be promoted to protected PR evidence.
These fixtures do not cover the four-manager project corpus or exhaustive analyzer
policy behavior. Raw outputs stay ignored; reviewed summary evidence is in
[the active change](../../openspec/changes/code-review-native-platform-execution/NATIVE_COMPATIBILITY_RESULTS.md).

For static Mach-O/load inspection without execution:

```sh
/absolute/python scripts/native_runtime_inventory.py /absolute/native-node-runtime
```

Inventory is bounded to a stable local payload and rejects incompatible or
external loads. It does not prove dynamic loading, minimum OS, signing, sandboxing
or verification-to-launch integrity.
