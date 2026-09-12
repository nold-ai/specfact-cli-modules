# Capsule Customer Execution: TDD Evidence

## First failing checkpoint — 2026-09-12, Europe/Berlin

Accepted scope: owner explicitly requested implementation and a persistent modules dogfooding CI gate after planning PR #467. Baseline a3e2b76a, runtime source unchanged from a6bac86e. Metadata was refreshed and read back before moving #466 from Todo to In Progress for this session. Existing dedicated worktree is cleanly owned by this change.

Command: `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_toolchain.py tests/unit/specfact_code_review/run/test_runner.py tests/unit/specfact_code_review/run/test_sandbox.py -k customer --tb=short`.

Result: **5 failed, 530 deselected**, on macOS Python 3.14.7. No production code had been edited.

- `test_customer_default_materialization_acquires_missing_cache_entries`: observed cache-only flag True instead of False.
- `test_customer_composition_authenticates_empty_mount_anchors`: snapshot anchor absent.
- `test_customer_github_actions_uses_verified_installed_payload[customer/project]`: installed release wrongly routed to candidate provenance.
- `test_customer_github_actions_uses_verified_installed_payload[nold-ai/specfact-cli-modules]`: same error for a public install in the modules repository's own CI.
- `test_customer_configuration_mounts_are_sealed_before_execution`: private configuration staging and sealing absent.

Linux diagnostic: existing cp312 image under Docker with host UID 1000 and default restrictions denied Bubblewrap namespaces. A separate namespace smoke without repository mounts under explicitly relaxed container syscall policy printed its expected marker. These are environment diagnostics, not hosted customer acceptance. A proposed source-mounted networked diagnostic container was rejected by automatic approval review; no such container was launched. Full source/customer evidence will come from hosted CI.

Passing evidence and later failing checkpoints will be appended after actual execution. Neither synthetic checks nor this record establish release acceptance.

## Diagnostic checkpoint — 2026-09-12 Europe/Berlin

Before changing error handling, `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_sandbox.py -k customer_launch_failure --tb=short` failed all three cases (namespace denial, read-only mkdir, generic analyzer failure): the diagnostic classifier was absent. The earlier customer/candidate regressions passed: 6 passed, 529 deselected. These are local regression checks, not Linux acceptance.

## Gate validator checkpoint — 2026-09-12 Europe/Berlin

Before creating the driver, `hatch run python -m pytest -q tests/unit/test_capsule_customer_gate.py --tb=short` failed all four acceptance-validator tests because the driver was absent. Cases reject empty inventory, UNKNOWN, skipped execution, and a defective fixture incorrectly passing.

The complete local capsule regression run finished with 537 passing tests and one failure in a cp314-dependent existing lock-selection test. Python 3.14 is outside the signed matrix; validation will use a supported interpreter before acceptance.

## Python 3.12 umask reproduction — 2026-09-12 Europe/Berlin

An offline, default-security Docker run of the existing public cp312 image, UID 1000, no repository mounts, installed its bundled Ruff wheel under umasks 022 and 077. Python was 3.12.13. Directories changed 0755→0700, ordinary files 0644→0600 and bin/ruff 0755→0711. This proves ambient umask changes mode-bearing filesystem identity; it does not identify the original workplace failure's exact digest stage.

Before repair, `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_toolchain.py -k 'offline_install_executes or customer_root_mismatch' --tb=short` failed 3 cases: subprocess umask was unset in both ambient modes, and mismatch diagnostics omitted the expected digest. The correction fixes the installation policy, not the trusted digest.

The first commit attempt was stopped by the normal review hook: the new driver had complexity findings. Those are being refactored before the next review. Existing broad-file review findings are not Linux customer acceptance evidence.

## Composition determinism checkpoint — 2026-09-12 Europe/Berlin

`hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_toolchain.py -k customer_composition_is --tb=short` failed: identical verified payload and base under umasks 022/077 yielded different final composition digests (`672650ad…` versus `246d1738…`). New generated directories inherited the controller mode. The repair assigns 0755 only to newly generated composition directories, preserves existing base directories and rejects symlink parents.

## Hosted customer-path checkpoint — 2026-09-12 Europe/Berlin

[Actions run 34721199840](https://github.com/nold-ai/specfact-cli-modules/actions/runs/34721199840), candidate commit `187524de5011e0c9f19f1963aa95fc6f0ed809a7`, failed all three Python jobs after anonymous installation, runtime acquisition and non-root final-root verification. Each cold/warm/defective/repository report was UNKNOWN at `candidate_payload_unavailable`: the development module symlink caused candidate Git-root discovery to point at the temporary customer directory. No analyzer execution is claimed. This also means the signed cp312 root digest passed in the actual non-root hosted path after the installation-mode correction.

Before fixing that path, `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_runner.py -k reconstructed_from_verified_git --tb=short` passed the direct path and failed the symlink path with the same Git exit 128. Resolving the loader path before determining its Git root preserves commit/tree/context verification.

## Multithreaded CLI launch checkpoint — 2026-09-13 Europe/Berlin

Reports uploaded by hosted run 34721580237 before replacement by the signing-bot run reached `pre_namespace_observation_requires_single_thread` for all three ABIs. Real CLI background threads prevent the guarded pre-exec tracer from starting; the guard must remain. The mapped `test_customer_threaded_controller_uses_fresh_trace_helper` failed before implementation because the helper was absent. A fresh isolated controller process will inherit only the verified launcher descriptor and run the unchanged guarded tracer.

## Analyzer import closure checkpoint — 2026-09-13 Europe/Berlin

The immutable cp312 interpreter returned no import spec for `beartype`; none of the three signed analyzer component sets contains it, although the real runner imports it at module load. After correcting a missing test import, `test_customer_capsule_locks_the_analyzer_entrypoint_runtime_imports` failed specifically for missing `beartype` on cp311. The proposed dependency is beartype 0.22.9, verified against [PyPI metadata](https://pypi.org/pypi/beartype/0.22.9/json): wheel `beartype-0.22.9-py3-none-any.whl`, 1,333,658 bytes, SHA-256 `d16c9bbc61ea14637596c5f6fbff2ee99cbe3573e46a716401734ef50c3060c2`. New immutable runtime layers and updated signed bindings are required; old OCI assets remain intact.

## Runtime correction verification — 2026-09-13 Europe/Berlin

Two independent offline Linux reference installations per ABI produced identical filesystem manifests. The existing `bin`, `bootstrap`, `lib` and `python` subroots were unchanged. New wheel/analyzer identities and OCI provenance are retained in `runtime-build/reference-receipts.json`; Python 3.13 publication remains pending explicit approval. This is build evidence, not public release acceptance.

`hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_toolchain.py tests/unit/specfact_code_review/run/test_sandbox.py --tb=short`: **141 passed**, including the fresh-process tracer and missing import closure regressions. `SPECFACT_CLI_REPO=/private/tmp/specfact-core-customer-466 hatch run type-check`: **0 errors, 0 warnings**. The isolated core checkout is released 0.55.4; the user's sibling core checkout was not changed.

## Review regressions — 2026-09-13 Europe/Berlin

Before correction, `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_toolchain.py tests/unit/specfact_code_review/run/test_sandbox.py tests/unit/test_capsule_customer_gate.py -k 'customer_offline or customer_long or inconsistent_repository' --tb=short` produced **7 failures**. Missing offline acquisition policy allowed downloads; long stderr lost the namespace stage; five inconsistent or incomplete repository status/exit pairs passed the gate. These are mapped to warm-cache reuse and actionable/failing evidence requirements.

## Complete analyzer import checkpoint — 2026-09-13 Europe/Berlin

Hosted run 34723324162 on cp311 successfully entered the verified Bubblewrap capsule, then failed at runner → differential import with `ModuleNotFoundError: No module named yaml`. All ten member reports retained the actual traceback. The entrypoint import-lock regression was extended and failed before correction; PyYAML must be bound as a real runtime distribution. Its module prefix is `yaml` (not its distribution name `pyyaml`). The complete module import inventory was inspected: other immediate dependencies are already locked; controller-only core imports remain lazy. New PyYAML artifacts will receive new immutable identities; existing development and release artifacts remain unchanged.

PyYAML correction passing checkpoint: all 152 focused toolchain, sandbox and customer-validator tests pass. The real `specfact_code_review.run.runner` import passed in the revised cp312 Linux reference under UID 1000 and `--network none`. Two independent offline reference installs per ABI had identical roots. All three owner-approved v2 OCI manifests/configs were then retrieved anonymously and matched their exact local export SHA-256 identities. Production root/content verification remains unchanged; these are new assets.

OCI mismatch diagnostics: `hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_oci_diagnostics.py --tb=short` failed both cases before repair; the old error omitted expected/actual digest and size. The correction retains the existing failure prefix while adding bounded identity fields, with no payload bytes or credentials.

## Real analyzer launch checkpoint — 2026-09-13 Europe/Berlin

Hosted run 34723950359 reached actual analyzer execution after the complete import correction. Five members returned ran/PASS; Ruff failed trying to create snapshot/.ruff_cache, Radon/Pylint/BasedPyright child console scripts lost the analyzer import root, and Semgrep clean rules were outside the authenticated Python-package copy. These are real error reports, not successful matrix acceptance. The Semgrep payload-copy regression (`test_customer_capsule_payload_contains_all_signed_semgrep_rules`) failed before moving the canonical rules into the copied package.

After the canonical rule move, `test_customer_semgrep_policy_resolves_packaged_module_layout` failed because the controller still searched only the outer module directory. The repair supports the signed src/flat package roots while retaining explicit target policy precedence and stable regular-file verification. Rule bytes are unchanged; their new module paths are covered by canonical payload signing and composition identity.

`test_customer_semgrep_child_uses_sealed_python_startup` failed before Semgrep adopted the shared sealed analyzer launcher. It expected the verified interpreter with `-I -S`, authenticated bootstrap, and direct pysemgrep module; the old console command did not preserve that closure.

Semgrep's first actual offline scan in the cp312 Linux reference failed because OCaml certificate-store discovery attempted missing `uname -s`. Setting `SSL_CERT_FILE` to the already locked certifi bundle made the identical scan succeed (exit 0, one expected scanned file, empty errors); no host tool or certificate bytes were added. `test_customer_sandbox_uses_locked_certificate_store` failed before adding this explicit sandbox environment binding. The probe used UID 1000 and network disabled. OCaml ca-certs supports this explicit trust-store selection; see [OCaml ca-certs source](https://ocaml.org/p/ca-certs/1.0.1/doc/src/ca-certs/ca_certs.ml.html) (checked 2026-09-13).

## Early namespace denial checkpoint — 2026-09-13 Europe/Berlin

Prior hosted quality run 34723950399 failed during the real non-root offline installer with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. This happens before a final composition exists. Two materialization diagnostic regressions failed before repair, as did the late-launch loopback classification test. The correction identifies `stage=offline-install` and the already verified native executable SHA-256, while ordinary pip errors retain a separate diagnostic. It does not claim a completed capsule identity before sealing. Logs: `/private/tmp/capsule-earlynamespace-red-466.log`, `/private/tmp/capsule-loopback-red-466.log`, `/private/tmp/capsule-earlynamespace-green-466.log`.

The first combined full suite found stale documentation-command and moved-resource assertions (now corrected) plus an enforcement fixture coupled to concurrent changes in the shared worktree. The latter now uses a private selected file; production snapshot revalidation remains unchanged. Hosted legacy CLI report-contract tests now explicitly inject their host-runner fixture and reject capsule acquisition, rather than depending on platform-specific development fallback. They provide no customer capsule acceptance.
