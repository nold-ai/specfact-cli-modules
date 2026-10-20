# TDD evidence

On 20 October 2026 (Europe/Berlin), specification and strict validation preceded all test edits. At the RED checkpoint, both implementation owners were byte-identical to the pre-activation preservation snapshot.

## Specification before tests

`openspec validate ci-04-native-pid-observation --strict` passed. `test-checkpoint/spec-before-tests.json` binds the exact command, timestamps, interpreter and source/spec hashes. Its raw stdout/stderr prove validation completed before the new test file existed in its current form.

## Actual old-reader RED

From `/Users/dom/.codex/worktrees/ci-fixture-identities/specfact-cli-modules`, the exact interpreter was `.venv/bin/python3.12` (Python 3.12.13). The run was `python3.12 -m pytest tests/unit/native_release/test_boundary.py -n 0 -p no:cacheprovider --junitxml=<evidence-root>/actual-red.junit.xml`. The complete absolute command, source hashes, start/end timestamps and interpreter identity are in `test-checkpoint/actual-red.json`.

Result was **36 failed, 23 passed, 0 setup errors, 0 skips**, exit 1. All three pre-existing tests passed. Both `test_pid_observation_waits_for_publication[controller-empty]` and `[sibling-empty]` failed with `ValueError: invalid literal for int() with base 10: ''`. Their actual-file writer had created the marker and was Event-gated before publishing the actual process PID. Both numeric-prefix cases returned the first digit instead of the actual PID. All writers were released and joined in `finally`; socket peers were closed and joined. No child process was launched by these tests and no marker PID was signaled.

Other intended failures show missing-record sleeps exceeding the fixed deadline (5.009999999999938 controlled seconds), empty-record premature parsing, incomplete-record premature success, permissive record grammar, late acceptance, symlink acceptance and delayed directory/FIFO rejection. Passing cases preserve immediate valid records, already-invalid records and ordinary I/O propagation. These are portable behavioral observations, not physical native acceptance.

Raw stdout, stderr and JUnit are retained under the evidence root. `RED_SUMMARY.json` classifies each failure and pass; `requirements-evidence.yaml` binds every new collected parameter case. Existing pytest defaults collect the portable file without selector or configuration changes. Guarded physical controls were not invoked.

## Preservation and setup distinction

The root checker passes with worktree Python 3.12.13 for 2812 protected tracked paths, ten compatibility inputs, four original boundary functions and the frozen workflow. Its four comparison controls reject known bad inputs. The initial ambient Python 3.14.7 invocation failed only because AST serialization differs from the snapshot's Python 3.12 format. That is setup evidence, not RED. The spec/test author did not modify the checker. Root subsequently added its explicit Python 3.12 guard, as recorded in `root-verification/interpreter-binding-correction.json`. The baseline snapshot remained unchanged.

The workflow remains SHA-256 `c268a001c2741f838207dbb572b1953e4ce11cffebeb07a4793aa49f38b4b5f3`. Native C, signed files, manifests, versions, dependencies, cleanup policy, source readers and historical proof controls remain unchanged. No native build, CI retry, bot/network call, stage, index, commit, push or merge was performed in this phase.

Evidence root is `/Users/dom/git/nold-ai/specfact-cli-worktrees/codex/ci518-review-artifacts/ci519-contract-reason-projection/follow-up-native-pid-observation`. The immutable manifest is `test-checkpoint/artifact-manifest.json` and binds the final portable test, specification snapshots, command records, raw results and verification artifacts.

## Obligations at the RED checkpoint

At that checkpoint, implementation, passing-after evidence, mandatory quality/source/import gates and exact-head hosted/physical acceptance remained unchecked. Independent root verification of RED was required before a fresh source writer could begin. The RED phase provided no native acceptance, runtime release or merge authority.


## Implementation and GREEN on 20 October 2026

Root independently accepted the immutable RED packet before source ownership began. Its manifest remains SHA-256 `64989eda269bd4022271d1b130becfb53339fcc6660d3782b3f4aa2b6220bad6`. The frozen portable test remains SHA-256 `16d581385570e2784b8edf472c549980cfb9bd4c3abe94905e6d94bc9cef6bf8`.

The shared `wait_worker_pid` and private parser now own complete-record observation. The sibling imports the waiter as `_worker_pid`, preserving all three callers. A guarded import check verifies alias identity, unchanged controller protocol bytes and unchanged AST for every other owner function. No physical proof runs during import.

`implementation/final-green.json` records the exact Python 3.12.13 command and timestamps. All 59 frozen cases passed with zero failures, errors or skips. `implementation/final-nearby.json` records 182 passing nearby tests and 12 existing guarded physical skips. Raw stdout, stderr and JUnit accompany both commands. All actual-file writer threads and socket peers were joined by the tests.

Scoped Ruff formatting and checks passed. BasedPyright reported zero errors, warnings and notes. Strict OpenSpec validation and the immutable preservation checker passed. The implementation phase preserves 2810 tracked paths, four original boundary functions and ten compatibility inputs. The smaller protected-path count excludes the two explicitly owned source files.

The first native source check found a new nesting warning. The waiter now closes its descriptor before interpreting the admitted record, retaining nonblocking regular-file admission and exactly two helpers. The original warning packet remains under `implementation/first-native-quality`.

Repository-context raw contract inspection reports 50 baseline warnings and 51 final warnings. The additional raw warning names the public test helper. The unchanged canonical reviewer already classifies `MISSING_ICONTRACT` under `tests` as known test noise. Its existing project discovery reads `testpaths = ["tests"]`, and its contract routing excludes those test roots from CrossHair. Executing those genuine functions leaves zero governed contract findings before and after. No review rule, policy, test root or configuration was modified. `implementation/configured-contract-reconciliation.json` pins the canonical reviewer and final source.

The raw-only diagnostic initially omitted canonical filtering. A provisional genuine icontract postcondition was approved and tested, then removed after the complete existing policy was verified. Its positive and bad-return mutation controls, installed released-core dependency evidence, stock CrossHair setup failure and successful genuine native-worker run remain under `implementation/superseded-real-contract`. They are superseded diagnostic evidence, not final-source GREEN. Final source remains standard-library-only and preserves standalone invocation. No dependency input changed, and no fake decorator, API hiding or new suppression was introduced.

Final whole-file review preserves the exact identities of existing Radon, AI-bloat, Pylint and Semgrep findings. `implementation/native-final-reconciliation.json` records those mappings and the distinction between raw and governed contracts. This scoped native source result does not claim a globally clean repository. Every final local Python gate used explicit worktree Python 3.12.13. The worktree has installed core 0.55.10, while root separately verified installed released core 0.55.4 during diagnosis. No Hatch command was run in this phase, and no claim equates Hatch with the explicit worktree interpreter.

Root retains full repository hooks, independent review, exact-head hosted acceptance and required physical native acceptance. No native component was built. No workflow, dependency, signed asset, frozen acceptance input, native C, cleanup deadline, repetition count or matrix changed. No stage, commit, push, CI retry, bot request or GitHub mutation occurred in this implementation phase.


## Independent local review

Root rehashed all 343 final implementation artifacts and all 46 immutable RED artifacts, compared the exact 59 case identities and reran the original-function preservation tool. A fresh independent reviewer then rehashed both complete packets, reran all 59 frozen tests and passed five additional real-descriptor controls. Those controls verify closure after success, invalid input, READ FileNotFoundError, READ EIO and FSTAT EIO. Ordinary errors retain their exact identity, acquired descriptors are closed and read failures are not retried as missing opens.

The independent report approves the bounded source with no actionable finding. It confirms the unchanged canonical test policy without a rule or dependency change and retains the public contract docstring. The report is preserved under `independent-final-review/REPORT.md`, SHA-256 `d03cda193fa326a8c4b718396f4b33ec65004257905e4d238fe2ffdea8fbfec0`. The reviewer disclosed and corrected a manifest-schema utility error without repeating successful tests. Root explicitly stopped every writer and reviewer before integration. Normal repository hooks and exact-head hosted and physical acceptance remain separate, pending obligations.


## Native mapping reconciliation and normal local gates

The first normal staged hook exposed seven incorrect requirement-reference keys. A keys-only correction then exposed the native adapter's additional scenario-reference rule. Both failures remain under `final-gates` and `requirement-binding-correction`. Root read the unchanged `_source_mapping_findings` implementation and preflighted the complete correction with native lifecycle and source-import APIs before another hook run.

Only seven requirement identity keys and 56 scenario reference fields changed. Every case ID, selector, assertion, method, intent and observable remains unchanged. Specification and executable source bytes remain exact. The corrected sidecar is SHA-256 `dfe1becbbf40bd4385d76ab4e980d4dc1fce2fea070a242a73f793fb7d35cdfc`. The original sidecar and all original runtime proof packets remain immutable history. This reference correction neither changes acceptance nor creates runtime proof.

A fresh independent metadata review approved the complete original-to-current comparison, confirmed all 56 selectors belong to the frozen 59 passing cases, and inspected the actual adapter rule. Its report is SHA-256 `b9d6a9da9990c0acfa33f4c6d58f70b8dd228c0c222e49429daa49816487caac`. Root explicitly stopped that reviewer before integration.

Normal `hatch run pre-commit run` and strict validation of both active changes passed without source changes. Signature/version checks, formatting, YAML, bundle imports, lint and documentation gates passed. Native staged Requirements reports two sources passed, zero failed or skipped, at planned maturity with implementation evidence not yet available. All 28 contract cases actually executed and passed. The approved local capsule review reports DEFERRED, never PASS, with the same immutable policy, external Python and indexed orchestrator inputs. Exact-head hosted review and physical acceptance remain mandatory and unproved before publication.
