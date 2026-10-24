# Linux analyzer investigation

Observed 2026-10-25, Europe/Berlin. Subject head `59611f358572aaa3c383c2d2fffcf82fb57ff36c`; base `430e3ccbf9fbd6a6177b033662a76235a8bd6cc8`. This is source inspection plus bounded public CI evidence and labeled host diagnostics. It is not a successful Linux acceptance run.

## Findings and confidence

| Observation | Established cause or limit | Confidence |
| --- | --- | --- |
| Six native Hatch acceptance cases skip at call phase in candidate and independent jobs | The tests require explicit native proof workspace/executable/Python inputs. The sealed analyzer clears the environment and does not supply those inputs. Tests skip before invoking production proof behavior. | High for source flow and matching skip pattern. |
| Pytest tool error points at `scripts/prove_hatch_project_runtime.py:1` | Coverage evaluation uses the first selected source as an error anchor. That location does not prove the script ran or caused the failure. The actual protected exception remains unavailable. | High for anchor behavior; underlying Linux cause unknown. |
| Independent contracts analyzer has error/UNKNOWN | Process/import errors, execution errors, timeouts, and unrecognized output can all produce this result. Structured-report projection omits the available class and side observations. | High for incomplete evidence and projection gap; actual exception unknown. |
| Four Pylint warnings match base-only host emissions | The public projection drops lifecycle and blocking fields. A pure classifier diagnostic marks the four base-only rows fixed/non-blocking. Released index review also uses paired differential classification, so retained base findings are a supported explanation. Actual hosted row lifecycle remains unavailable. | High for lossy projection and index flow; hosted attribution unresolved. |

The confirmed root causes are missing native acceptance prerequisites and loss of diagnostic provenance. I don't know yet which separate exceptions caused Linux pytest and contracts incompleteness. The required next evidence is the actual analyzer side and fixed failure class from the same protected execution. No analyzer repair is justified by the current public anchor or a Darwin import failure.

## Execution boundaries

Linux preparation uses `runtime_builder.py` and `runtime_build_driver.py`. It installs Hatch in preparation tooling, builds the customer environment, and copies customer dependencies/executables into the sealed artifact. It does not promise that the sealed analyzer can invoke native acceptance tooling. Historical traces through `native_project_runtime.py` describe Darwin and cannot establish the Linux launch path.

The sandbox mounts prepared runtime content read-only, clears the environment, and sets a bounded analyzer PATH. Passing host `SPECFACT_HATCH_*` values or executable paths into it would change the boundary. Native acceptance also requires a compatible controller, project Python 3.11.15, and a fresh external workspace. A PREPARED descriptor alone proves none of those acceptance-cell resources.

The independent job installs CLI 0.55.4 and released reviewer 0.51.2, captures the subject without executing its host code, and reviews index scope. Candidate implementation and independent reviewer implementation are distinct. Named pytest command/environment and sandbox functions in the cached released archive match the candidate AST, but this is not whole-runner equivalence or authenticated proof of hosted loaded bytes.

## Diagnostic reproductions and their limits

A controlled Darwin Python 3.12.13/CrossHair 0.0.107 probe exits 2 when the proof script cannot import `specfact_codebase`. Adding the Codebase source root changes that probe to exit 0. Linux uses pinned CrossHair 0.0.109 and injects descriptor-recorded source roots. The host result therefore proves its own ambient import omission, not the protected Linux cause.

The actual host Pylint adapter emits four C0415 warnings on the base file and none on the head file. Feeding those observations and committed source bytes into the pure differential classifier returns PASS with four fixed findings. Candidate and released 0.51.2 retain fixed findings with explicit `blocking=false` in differential report mapping. Direct inspection of the downloaded 0.51.2 archive confirms that index review materializes HEAD and index snapshots and invokes paired differential classification, including its portable project-runtime path. The workflow's soft reset makes HEAD the merge-base while retaining the candidate index bytes. Historical fixed rows are therefore a supported explanation. The actual hosted rows still require lifecycle/side evidence. Do not infer a classifier bug or dismiss active findings from this diagnostic.

The source error projection already defines `incomplete_sides` and `crosshair_failure_observations`, but calls them only for oversized independent reports. The observed independent report is structured. This deterministically explains why the useful class/side discriminators are absent from that public summary. Existing artifact upload paths exclude the private review report and log; the available uploaded artifact cannot supply their hidden exception details.

## Exact-head public evidence

These primary CI sources were read through the Code Review connector on 2026-10-25. Returned log tails were truncated, so absence from those tails is not proof that an analyzer passed.

- [Candidate Python 3.12 job](https://github.com/nold-ai/specfact-cli-modules/actions/runs/40135941692/job/120997951923): failed; both descriptors prepared/present; pytest tool error and six native skips. Namespace audit captured without observed AppArmor/user-namespace denial markers.
- [Independent signed review](https://github.com/nold-ai/specfact-cli-modules/actions/runs/40135941692/job/120997951869): failed; structured report, overall FAIL, assurance UNKNOWN, contracts and targeted-pytest-coverage error/UNKNOWN.
- Other matrix jobs were still reported in progress on the latest read. This investigation makes no overall success claim and does not retry unchanged failed jobs.

## Primary source map

All links pin the subject revision and were inspected on 2026-10-25.

- [Native prerequisite guards](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/tests/integration/test_hatch_project_runtime.py#L26): main case; storage lines 86-97 and absolute-Python cases lines 237-250.
- [Linux preparation](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/runtime_builder.py#L267) and [build driver](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/runtime_build_driver.py#L226).
- [Cleared sandbox environment](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/sandbox.py#L502).
- [Pytest error anchor](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/runner.py#L7190).
- [Contract command/result handling](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/tools/contract_runner.py#L259) and [Linux target source roots](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/target_bootstrap.py#L270).
- [Finding lifecycle mapping](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/packages/specfact-code-review/src/specfact_code_review/run/runner.py#L8079).
- Released 0.51.2 archive members inspected directly: `run/commands.py:1215-1216` dispatches immutable index review; `run/scope.py:2732-2742` materializes HEAD/index snapshots; `run/portable_snapshot.py:332-359` classifies the index pair. These released-source observations are distinct from authenticated hosted execution evidence.
- [Independent reviewer identity and invocation](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/.github/workflows/capsule-customer-execution.yml#L650), [lossy finding projection](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/.github/workflows/capsule-customer-execution.yml#L938), and [oversized-only class/side projection](https://github.com/nold-ai/specfact-cli-modules/blob/59611f358572aaa3c383c2d2fffcf82fb57ff36c/.github/workflows/capsule-customer-execution.yml#L1124).

## Decision

Recommend the [diagnostic-only proposal](proposal.md). Preserve every existing gate and trust boundary. If those observations reveal a runtime admission, dependency, timeout, or acceptance ownership issue, return a separate scope decision before repair. Strict proposal validation cannot establish a working customer reviewer or green Linux CI.
