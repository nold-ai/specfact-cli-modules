# Capsule Investigation Record

## Evidence boundary

Checked 2026-09-12 (Europe/Berlin). Source baseline: `a6bac86ec529715b9122a7a670ee4886a749d9f6`; module 0.49.77. Investigation ran on macOS and used read-only GitHub/registry requests. No Linux execution, complete layer download, installed-root verification, or customer reproduction was performed. Confidence: high for source/CI observations; medium for the filesystem hypothesis.

## Customer-reported observations

The runtime package was private and became accessible after being made public. Bubblewrap needed permission to register unprivileged namespaces. A Python 3.12 SHA mismatch required adjustments. Directory creation under `/var/opt/specfact/...` then failed, with signed hashes preventing ad hoc capsule edits. The customer's exact release, modified files, failed hash, complete path, and syscall are not available; do not invent them or disclose work-repository details.

## Verified observations

- The current lock selects Linux x86-64 cp311/cp312/cp313. OCI configs report runtime Python 3.11.14/3.12.13/3.13.11.
- An anonymous registry token request and GETs for each locked manifest/config succeeded. All returned manifest bytes matched the expected SHA-256; manifest layer digest/size lists matched the lock. This probe used urllib, not SpecFact's downloader, and therefore does not prove its full customer acquisition path.
- Current CI uses a repository token for ORAS prefetch, copies that cache, and invokes materialization/boot under sudo. Its final smoke directly starts the loader/interpreter and prints a marker. It bypasses complete production descriptor/tracing launch and analyzer execution.
- Production `_bubblewrap_command` binds its root read-only and then emits `--dir` for subsequent mount destinations. `_prepare_capsule_process_roots` creates host-side request/output/temporary/control roots; that alone does not establish their destination directories inside the sealed capsule.
- No literal `/var/opt/specfact` was found in the inspected modules Python/workflow source. The specific customer path remains unresolved.

| ABI | Verified OCI manifest SHA-256 |
|---|---|
| cp311 | `4f9e424f3720ea0807cc0f9f22c0ba28e3c604632ddd719f605c22e878437a72` |
| cp312 | `f00ac813f428b7c2ef3d1ce3400496f67ca2d508064e6efc55af1ba6c4697461` |
| cp313 | `1516be5a113d9176c70fcc4cfac3fe46eaf32d5b66c381b17fbb26a5bcc9fb27` |

## Hypotheses and evidence needed

- **Missing mount destinations:** a read-only parent may prevent Bubblewrap from creating a destination. Capture actual destination, errno and command from the production launch, then verify composition entries.
- **Installed-root determinism:** inherited umask, ownership-sensitive installation or filesystem modes may explain a later checksum mismatch. Compare exact root entries across cp312 runs; current OCI manifest equality cannot rule this out.
- **Host namespace policy:** Ubuntu AppArmor or another host restriction may deny the bundled launcher despite a distro-installed Bubblewrap being allowed. Probe the actual verified descriptor/tracing path and retain host policy diagnostics.

Each hypothesis needs failing-before Linux evidence before a production repair. Do not replace checksums, make sealed runtime code writable, or treat privileged smoke success as proof.

## Sources

All external sources accessed 2026-09-12:

- [Pinned CI workflow](https://github.com/nold-ai/specfact-cli-modules/blob/a6bac86ec529715b9122a7a670ee4886a749d9f6/.github/workflows/pr-orchestrator.yml).
- [Pinned sandbox launcher](https://github.com/nold-ai/specfact-cli-modules/blob/a6bac86ec529715b9122a7a670ee4886a749d9f6/packages/specfact-code-review/src/specfact_code_review/run/sandbox.py).
- [Pinned toolchain implementation](https://github.com/nold-ai/specfact-cli-modules/blob/a6bac86ec529715b9122a7a670ee4886a749d9f6/packages/specfact-code-review/src/specfact_code_review/run/toolchain.py).
- [Pinned toolchain lock](https://github.com/nold-ai/specfact-cli-modules/blob/a6bac86ec529715b9122a7a670ee4886a749d9f6/packages/specfact-code-review/src/specfact_code_review/resources/contracts/pr-range-v1-toolchain-lock.json).
- [Bubblewrap v0.11.0 setup implementation](https://github.com/containers/bubblewrap/blob/v0.11.0/bubblewrap.c): bind mounts and directory operations call `ensure_dir` and fail on creation errors.
- [Ubuntu AppArmor documentation](https://documentation.ubuntu.com/security/security-features/privilege-restriction/apparmor/): unprivileged namespace use can be denied by AppArmor policy.
- [GitHub Container Registry documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry): public container images support anonymous access.
- [Completed payload-layout bug #459](https://github.com/nold-ai/specfact-cli-modules/issues/459) and [release PR #464](https://github.com/nold-ai/specfact-cli-modules/pull/464): distinguish the shipped layout fix from remaining namespace/runtime failures.
