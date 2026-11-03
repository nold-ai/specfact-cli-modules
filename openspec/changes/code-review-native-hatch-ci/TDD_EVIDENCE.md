# Native Hatch CI evidence

Recorded 2026-10-25, Europe/Berlin, against signed base `6b865787bd3dc6e852529be663452b7e1337e6cd`.

## Scope

The owner requested continued corrected native implementation. This unit adds hosted execution of the existing first-Hatch acceptance. It does not implement native script expansion, another manager, public reviewer cutover or security-test ownership transfer. No capsule implementation or repair is included. Existing independent review, signing and adverse gate results remain effective.

## Spec, tests and actual RED

The spec and sixteen-selector mapping preceded workflow implementation. The actual command was:

```console
.venv/bin/python -m pytest tests/unit/workflows/test_native_hatch_acceptance.py -o 'addopts=-ra -q --import-mode=importlib' -o junit_family=xunit1 --junitxml=/private/tmp/513-native-ci-red.xml
```

All sixteen cases failed. The intended failures were `Mandatory native Hatch acceptance workflow is missing` and `Required native Hatch prerequisite is missing`. This demonstrates absence of the required feature, not sixteen pre-existing bugs in a report parser. There were no collection errors or skipped cases. Source hashes and the RED JUnit digest are in `/private/tmp/513-native-ci-red-binding.json`.

Independent technical mapping review then accepted the sixteen exact selectors before implementation. Actual `evaluate_mapping` passed at test-authored maturity using `/private/tmp/513-native-ci-mapping-acceptance.json`. The canonical RED reconciliation passed at red maturity against staged tree `ac5948ecceb5266e0a738e5a918a24cf1422ace8`; records are `.audit/513-native-ci-{plan,red-reconciliation}.json`. This technical acceptance grants no product-owner or protected security authority.

## Implementation and GREEN

One isolated writer implemented only the reusable native workflow and its required orchestrator prerequisite. The workflow uses exact head checkout, separate controller/project Python installations, pinned native Hatch, the existing controller Hatch environment and the authoritative change-17 selector mapping. Every observed JUnit case must have exactly one mapped selector; missing, extra, duplicate, skipped, failed, erroneous or absent results cannot pass. The existing signature/customer-capsule step is preserved.

All sixteen workflow checks passed. Combined regression testing also passed all 94 cases covering the new workflow plus existing scope and prerequisite tests. `/private/tmp/513-native-ci-green-regression.xml` is this combined run. The fake pytest producer in workflow checks validates acceptance logic only and does not establish actual project execution.

The same inline workflow program was separately executed with actual Hatch 1.18.1, controller Python 3.12.13 and project Python 3.11.15. It selected the existing 59 mapped cases, passed all 59 with zero skips in 19.92 seconds and accepted their exact JUnit properties. Existing/cold workflow receipt is `/private/tmp/513-native-ci-real-_plw8u06/proof/receipt.json`; JUnit is `/private/tmp/513-native-ci-real-_plw8u06/junit.xml`. The invocation log and provenance are `.audit/513-native-ci-real.txt` and `.audit/513-native-ci-real-run.json`. This is actual local native execution, not hosted Linux or protected assurance.

## Archive lifecycle regression

CodeRabbit found that normal archival of change 17 would remove the active mapping path. The spec and mapping were extended to eighteen cases before the lookup correction. The two new cases genuinely failed in `/private/tmp/513-native-ci-archive-red.xml`. Independent pre-fix acceptance is `/private/tmp/513-native-ci-archive-mapping-acceptance.json`, with mapping digest `sha256:1ece19a51a7df27d35f0f47570d071088dc025225d45b470ca733fc0a576424d`.

The workflow now prefers the active mapping and otherwise requires exactly one archived source for the same change identity. No real change folder was moved or archived. All eighteen final checks pass in `/private/tmp/513-native-ci-final-green.xml`; the combined retained-scope/prerequisite regression run passes all 96 cases in `/private/tmp/513-native-ci-archive-green-regression.xml`. Independent narrow implementation review accepted the correction in `/private/tmp/513-native-ci-archive-implementation-review.md`.

The final workflow program also passed all 59 actual native mapped cases with zero skips in 19.66 seconds. Its fresh receipt and JUnit paths are recorded in `.audit/513-native-ci-final-real-run.json`; the execution log is `.audit/513-native-ci-final-real.txt`. An initial outer launch used a Python without PyYAML and stopped before the program ran. The corrected launch used the repository controller Python. This launch error is not a runtime or acceptance failure.

The final eighteen-case reconciliation uses an explicit incremental legacy-TDD ledger. The initial sixteen-case RED/direct reconciliation remains intact; two later RED cases are not relabeled as initial failing evidence. Final bindings are `.audit/513-native-ci-final-{plan,tdd-ledger,tdd-record,reconciliation,tested-source}.json`. These local artifacts establish engineering evidence only.

## Delivery gates

CodeRabbit completed its final ten-file review after the archive fix. Its remaining minor suggestion was to replace the same-repository `./.github/workflows/...` reference with `$/...`. This is a nonblocking style recommendation. [GitHub's reusable-workflow documentation](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows), accessed 2026-10-25, explicitly supports both and states that both select the caller's commit. The existing repository pattern and actionlint-validated `./` reference are retained. No `zizmor` configuration or mandatory gate exists in this checkout. This disposition does not waive a runtime or security finding.

The final local gate cycle passed formatting, types, lint, YAML, actionlint, bundle import boundaries, all seven strict module signatures, contracts, SMART, full tests and the complete pre-commit pipeline. SMART and full each passed 5,884 tests with 77 existing opt-in skips, five baseline warnings and 95 passing subtests. The pipeline passed its Requirements and 28 contract cases. Logs and actual exit codes are `.audit/513-native-ci-final-gate-{name}.txt` and `.audit/513-native-ci-final-gate-status.json`.

Only the approved local Darwin capsule component remains explicitly DEFERRED. No successful native receipt turns an old capsule result into PASS. Signed delivery and exact-head hosted status are recorded in the PR after push; hosted native evidence and independent requirements remain separate from these local results. This evidence file does not claim merge-ready status or authorize archive.

At the prior exact head, the new native scope guard and signatures passed. Linux candidate 3.12 and independent signed review failed; candidate 3.11/3.13 passed. Quality failed at `Required customer capsule matrix did not pass: failure`, before later quality stages, in run `40196995042`. These terminal results are preserved. This unit adds independently required native evidence while leaving the later acceptance/CI replacement to the approved cutover sequence. No old gate is removed, retried or repaired here.
