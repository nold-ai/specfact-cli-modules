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

## Dependency evidence before admission

Run the offline npm audit from this repository root with an explicit interpreter:

```sh
/absolute/python -B -m scripts.native_analyzer_inputs.candidate_policy \
  /absolute/inputs/basedpyright-1.39.10.tgz > /absolute/private/npm-evidence.json
```

It authenticates the committed archive integrity before bounded parsing, records
actual MIT/third-party license payload hashes and explicit fsevents omission, and
captures the complete released ten-member analyzer version map without importing
production modules. The released Semgrep 1.144.0 identity conflicts with native
1.175.0; the paired core floor requires at least 1.175.0. Matching clean/defective
fixtures does not resolve that policy drift. Parent-owned production policy and
cross-version/Linux evidence must reconcile it; do not downgrade the candidate.

The expanded `scripts/native_semgrep_parity.py` also covers `.semgrep` rule layouts
using the pinned distribution's `--no-rewrite-rule-ids` option on both frontends.
Raw emitted IDs remain exact. Raw invalid-pattern Python/native exit and scanned-target parity still fail on
1.175.0. The owner-authorized versioned adapter below preserves the released
result semantics using independently measured target discovery; raw errors remain.

The authenticated upstream Z3 wheel contains **no license file** despite MIT
METADATA. The sidecar records the missing in-wheel text (`license_payload_complete=false`)
and hashes all 39 unchanged members; the wheel remains byte-identical to the
existing correction. It does not fabricate or insert license text. Final license
admission requires separately authenticated redistribution terms, including the
bundled Windows DLL payloads. Existing source/native preservation and correct
RECORD/metadata are evidence, not dependency admission.

Exact dependency-task contract and measured scope are in
[NATIVE_DEPENDENCY_CONTRACT.md](../../openspec/changes/code-review-native-platform-execution/NATIVE_DEPENDENCY_CONTRACT.md).


## Versioned Semgrep candidate and authenticated Z3 license

The proposed complete version map is frozen in `candidate-version-policy.json`.
It names Semgrep 1.175.0 and adapter
`specfact-semgrep-1.175.0-legacy-result-v1`; it does not change the released 1.144.0
policy. Parent integration must update all production producers, consumers, locks
and signed profiles and validate Linux/portable semantics before admission.

The parity CLI now evaluates the versioned adapter conformance (exit 0 for all
required cases), while its schema-2 receipt preserves raw frontend `passed=false`,
raw 13/14 comparison and every stdout/stderr. `adapter.passed=true` records the
separate 14/14 protocol result. Native `--x-ls` supplies actual selected targets
before rule validation. On the precisely typed rule failure, legacy exit 2 and
`paths.scanned` preserve the reference's selected-target meaning; explicit
`analyzed_targets=[]` states that no scan succeeded. Complete error structures,
including code/message/column/offset, remain compared. Discovery failure,
unknown/mixed errors or changed versions reject adaptation.

`Z3-LICENSE.txt` is the unmodified official tagged license, authenticated with
`z3-license-provenance.json`; both are reviewed repository inputs. Obtain the
exact upstream ARM64 release archive named in that provenance (its digest is
checked offline), then prepare license-bearing candidate artifacts:

```sh
/absolute/python scripts/native_z3_wheel.py \
  /absolute/inputs/z3_solver-5.1.0.0-py3-none-macosx_13_0_arm64.whl \
  /absolute/new-licensed-z3-candidate \
  --release-archive /absolute/inputs/z3-5.1.0-arm64-osx-13.3.zip
```

The schema-3 sidecar verifies tagged source/metadata identity and byte-links 28
native/source/header members to that authenticated release. The output directory
also contains the exact supplemental `Z3-LICENSE.txt`; the corrected wheel is
byte-identical. Final signed redistribution must carry and authenticate that
license file separately: installing the wheel alone does not include it.

The supplemental MIT text covers the verified Z3 Darwin/source payload; it does
not supply Microsoft VC runtime terms or Windows binary-source linkage. Exact
unlinked DLL identities remain named in the reviewed provenance and sidecar.
Neither this evidence nor adapter conformance admits the complete dependency
closure or enables production execution.
