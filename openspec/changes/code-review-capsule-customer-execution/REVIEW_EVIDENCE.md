# PR review evidence

Reviewed on 2026-09-13 (Europe/Berlin) against PR #467, including all 20 inline review threads, review bodies and conversation comments available at inspection. This records assessment and local repair evidence; thread resolution requires the repaired commit to be pushed and checked first.

## Review inventory

| Comment | Assessment and disposition |
| --- | --- |
| 3997674620 | Valid. The deterministic-materialization scenario now covers all three ABIs, two cache roots and umasks 022/077. Hosted acceptance remains a separate gate. |
| 3997681552 | Valid. The release requirement and scenario now specify GitHub-hosted Ubuntu 24.04 x86-64. |
| 3997783041 | Valid. The warm run now selects cache-only acquisition; missing entries cannot be downloaded in that iteration. |
| 3997783045 | Valid. Add actual expected namespace-denial execution before administrator setup; retain this thread until its hosted evidence passes. |
| 3997783048 | Valid merge gate. Passing local checkpoints are recorded in TDD evidence; complete supported-ABI hosted evidence remains required. |
| 3997785433 | Stale planning-only premise. The user explicitly authorized implementation and the authoritative change-order entry now records that phase. |
| 3997785435 | The claimed runtime signature gap is absent. `derive_core_0_55_1_install_handoff` rejects missing signatures and calls core verification with `allow_unsigned=False`, `require_integrity=True`, `require_signature=True` and the approved public key. Matching an independently installed release to a candidate checkout manifest would conflate the two lanes. |
| 3997785439 | Contract clarification accepted: require approved-key integrity/signature checks and record installed module identity separately from capsule identity. |
| 3997785443 | Stale planning-only premise. Implementation authorization and execution evidence are retained; release acceptance remains pending. |
| 3997785444 | Valid. Classify complete normalized stderr before limiting the returned diagnostic. |
| 3997785456 | Valid missing status/exit consistency check. Reject missing or contradictory status/exit pairs and preserve this gate's stricter rejection of UNKNOWN or empty execution. |
| 3997796189 | Incorrect current-code premise. `commands.py` imports `run_capsule_review as run_review`; full scope invokes that capsule implementation. Real hosted reports independently demonstrate acquisition/materialization and sandbox launch. |
| 3997803547 | Stale planning-only premise. The proposal describes the explicitly authorized implementation without claiming release acceptance. |
| 3997803550 | Stale planning-only premise. Issue #466 was moved to In Progress by this implementation session; it remains open. |
| 3997803553 | Confirmed and repaired with descriptor-anchored composition operations and three failing-before substitution tests; evidence below. |
| 3997887509 | Confirmed by hosted execution. Add hash-verified PyYAML to all three immutable runtime closures; retain actual runner-import evidence. |
| 3997887511 | Valid. The user approved publishing all three revised v2 runtimes; anonymous retrieval must verify every locked locator before delivery. |
| 3997887512 | Withdrawn and resolved by CodeRabbit after the user confirmed GitHub-only canonical signing (replies 3997910709/3997911505). Strict signed publication remains a release gate; no local signing bypass is introduced. |
| 3997919585 | Valid. Pin public installation to the release/registry version and assert the installed identity; archive-only module-list output is insufficient. |
| 3997919589 | Valid. Attach the selected runtime environment/ABI to propagated capsule failure evidence, independently of the matrix wrapper. |

CodeRabbit's embedded scanner flags for argv-list subprocess calls and `json.dumps` are not shell injection or web-response findings in these paths: commands use no shell and JSON is local evidence/protocol data. New composition helpers include purpose-specific docstrings. Strix reported its trial had ended, so no Strix security review result is claimed.

## Descriptor-anchored composition regression

The new `Composition rejects a substituted destination parent` scenario precedes the tests in `tests/unit/specfact_code_review/run/test_composition_writes.py`.

Failing-before command:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-core-customer-466 hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_composition_writes.py --tb=short
```

Result: **3 failed**. Replacing a checked parent immediately before its write caused an outside directory to receive `policy.json`, `sealed_bootstrap.py`, or mount directories respectively. Full local output: `/private/tmp/capsule-composition-red-466.log`.

The repair keeps every destination directory descriptor open, traverses with `O_NOFOLLOW | O_DIRECTORY`, creates directories with `dir_fd`, writes exclusive regular files, uses `fchmod`, performs descriptor-relative replacements and cleanup, and checks retained directory identities before accepting composition. It preserves existing base modes, deterministic new directory modes, source verification, and sealed bootstrap readback.

Passing-after command:

```sh
SPECFACT_CLI_REPO=/private/tmp/specfact-core-customer-466 hatch run python -m pytest -q tests/unit/specfact_code_review/run/test_composition_writes.py tests/unit/specfact_code_review/run/test_toolchain.py --tb=short
```

Result: **112 passed**, including all three substitutions and existing deterministic composition/source-integrity tests. Output: `/private/tmp/capsule-composition-green-466.log`. Scoped Ruff checks passed; `hatch run type-check` reported **0 errors, 0 warnings, 0 notes**. These local tests ran on macOS with Python 3.14.7 and are regression evidence, not supported Linux runtime acceptance.

The filesystem repair fails closed if a destination path contains a symlink, including substituted parents. Descriptor anchoring prevents following the substituted pathname; it does not claim protection from arbitrary same-user interference with unrelated host files or from a privileged attacker.

## Analyzer child startup and private cache repair

Hosted run `34723950359` reached actual analyzer execution using the cp311 v2 runtime: five members passed; Ruff attempted `.ruff_cache` beneath the read-only snapshot, and Python console-script children lost the analyzer import root (including Pylint's explicit `ModuleNotFoundError`). This is failing production-path evidence, not a synthetic checksum failure.

The `Analyzer child processes retain sealed startup` scenario was added before `tests/unit/specfact_code_review/test_capsule_tool_commands.py`. Its first run produced **7 failures** before the command-construction helper existed. The helper now preserves host compatibility commands, while capsule Python child commands re-enter the sealed interpreter with `-I -S` and authenticated bootstrap. Radon, Pylint, basedpyright and CrossHair use their module entry points. Semgrep uses its supported `pysemgrep` console-script module to avoid a native CLI fallback re-entering an unsealed generated Python wrapper. Ruff receives an explicit cache directory inside `/opt/specfact/tmp/cache`.

Focused child-command plus Ruff/Radon/Pylint/basedpyright/contract-runner regressions: **72 passed**. Logs: `/private/tmp/capsule-child-red-466.log` and `/private/tmp/capsule-child-green-466.log`.

An additional non-root, network-disabled Linux cp312 v2 reference-container check used isolated/no-site startup with the bootstrap's explicit import roots. Radon, Pylint, basedpyright and Semgrep returned their locked versions successfully; CrossHair's `--help` returned 0. Semgrep required the declared private HOME, as provided by the real sandbox. It emitted a dependency SyntaxWarning from glom but completed. These checks establish child startup compatibility; the full hosted analyzer/fixture matrix remains the acceptance authority. Logs: `/private/tmp/capsule-child-linux-466.json` and `/private/tmp/capsule-child-linux-private-466.json`.

## Wheel descriptor validation and lifecycle follow-up

Review comments 3997957672 and 3997957674 identified a stale lifecycle paragraph and unchecked descriptor metadata. The change-order paragraph now records candidate repair/dogfooding in progress and keeps signed module publication and release acceptance pending.

The `Runtime wheel descriptor agrees with authenticated bytes` scenario preceded `tests/unit/test_capsule_refresh_lock.py`. Before the repair, ten altered descriptor fields were silently accepted despite a correct wheel hash: **10 failed, 1 passed**. The builder now parses the filename, METADATA and WHEEL tags, checks name/version agreement, derives actual archive metadata/entry-point digests and file size, and rejects any copied field mismatch before producing a lock component. It also rejects non-basename wheel filenames.

After correction: **11 passed**. All four actual reviewed wheels (beartype plus PyYAML cp311/cp312/cp313) pass the new metadata checks without changing any runtime lock bytes. Scoped Ruff passed. Logs: `/private/tmp/capsule-descriptor-red-466.log` and `/private/tmp/capsule-descriptor-green-466.log`.

Review refresh found four further comments (24 threads total): 3997957672 lifecycle, 3997957674 descriptor validation, 3997957677 deterministic marketplace/main-registry installation, and 3997957678 allowlisted customer subprocess environment. The last two remain covered by the customer-gate follow-up; resolution is recorded only after push and verification.

## Post-push review disposition — 2026-09-13 Europe/Berlin

All 26 threads were inspected. Fixed and stale threads were resolved only after the relevant pushes; namespace denial was resolved after actual three-ABI hosted readback. Comment 3998008724 alleged released core user modules shadow explicit candidate roots; released core 0.55.4 appends explicit roots first and keeps the first module match, so that premise was disproved and resolved with immutable core source links. Comment 3998008726 correctly identified a future publication PR selecting an unavailable candidate registry version. Candidate installation now uses a separate public main registry snapshot with its commit recorded; candidate analyzer source remains the PR checkout and public release validation remains bound to its event checkout. The new regression passes with all 57 gate tests. This thread awaits its fix push; the final quality thread remains pending the complete required matrix.
