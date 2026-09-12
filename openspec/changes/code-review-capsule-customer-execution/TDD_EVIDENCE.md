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
