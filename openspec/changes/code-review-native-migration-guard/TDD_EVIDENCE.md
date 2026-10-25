# Native migration correction evidence

Observed 2026-10-25, Europe/Berlin. Baseline is signed head `23967ee8dc22545935427cd737b418e5b21198e5`. The owner explicitly requested native Hatch work and an enforced correction against recurring capsule repairs.

## RED before implementation

The spec and exact eleven-selector mapping preceded the authoritative run:

```console
.venv/bin/python -m pytest tests/unit/scripts/test_native_review_scope.py -q -o addopts= -o junit_family=legacy -o cache_dir=/private/tmp/513-native-guard-cache --junitxml=/private/tmp/513-native-guard-final-red.xml
```

Result: 8 failed, 3 passed. The old mandatory boundary command returned `0` and `Import boundary check passed.` when the new rejection cases expected exit `1`. The actual earlier workflow content from `e2b6487679e7ecd06cb8dea7537a473584990f93` was also accepted instead of rejected. The independent native CI workflow was absent. Three preservation controls already passed. No claim is made that all eleven cases were RED. Source/JUnit hashes are in `/private/tmp/513-native-guard-red-binding.json`; the preliminary run is separately retained under `/private/tmp/513-native-guard-red.*`.

## Incremental required-CI proof

After the first checker GREEN, the CI contract was strengthened to require consumption by the existing quality gate rather than an optional isolated job. Before that wiring, its focused check failed with `AssertionError: Required native scope prerequisite is missing` and the actual mismatch `assert 'native-scope' in {...}`. The earlier exploratory failure was a KeyError and is not substituted for this assertion mismatch. Records are `/private/tmp/513-native-guard-ci-dependency-{red,final-red}.txt`.

The required quality matrix now depends on the reusable native scope job and checks its result explicitly. The native scope job itself has no capsule prerequisite and read-only repository permissions. Existing signing and capsule/security prerequisites remain unchanged. Test assertions were strengthened, not weakened; the initial and later test source versions are not represented as identical.

## GREEN and historical rejection

The initial focused suite passed all 11 cases, zero skips. JUnit is `/private/tmp/513-native-guard-final-green.xml`. The existing `scripts/check-bundle-imports.py` entry point also passed and executed the new checker.

The read-only historical command:

```console
.venv/bin/python scripts/check_native_review_scope.py --base-ref 59611f358572aaa3c383c2d2fffcf82fb57ff36c --head-ref e2b6487679e7ecd06cb8dea7537a473584990f93
```

returned exit 1 and rejected the actual capsule workflow and projection-test edits. Its diagnostic directs work to `packages/specfact-codebase/src/specfact_codebase/project_runtime.py` and the established 17 -> 18 -> 19 -> paired core -> 20 order. It reads Git data only and executes no historical subject code. The default command accepts the current native-only change. Existing classified files can remain unchanged or be deleted for retirement; additions and edits fail.

## Review corrections

Independent review reproduced option-shaped Git revisions writing an output file. CodeRabbit also identified policy-only weakening by moving the freeze baseline or removing a classified path. Four focused cases failed before correction with `Native review scope check passed` and exit `0` where exit `1` was required. Records are `/private/tmp/513-native-guard-review-red.{txt,xml}`. Resolve revisions to commit identities before diff and bind reviewed policy bytes by SHA-256. This protects against accidental policy-only bypass, not a hostile candidate rewriting the checker itself.

After those corrections, 15 guard cases and 63 unchanged existing prerequisite cases passed together, 78 passed with zero skips, in `/private/tmp/513-native-guard-review-green.xml`. The first broad SMART run had exposed two existing prerequisite regressions from placing the native variable in the old step. Moving the new native prerequisite into its own step preserved the original signature/customer-capsule behavior without editing frozen tests.

CodeRabbit subsequently found that fingerprint rejection masked three deeper input-validation cases. The test fixture now explicitly approves its mutated test policy for those cases, while the separate weakening cases retain the original fingerprint. It also required the mapped historical case to invoke the actual two-commit comparison, rather than relying on the separately recorded manual comparison and a copied historical file. These are later test refinements, not identical bytes to original RED. The final exact 15-selector run is `/private/tmp/513-native-guard-final-15-green-v3.xml`. The actual-time independent mapping acceptance is `/private/tmp/513-native-guard-final-mapping-acceptance.json`; it is post-implementation test-design evidence, not pre-code approval or protected security authority.

## Native Hatch acceptance

Actual Hatch 1.18.1 and project Python 3.11.15 were verified before the run. With the Python 3.12.13 controller, a fresh external workspace and the existing native acceptance environment inputs, both project-runtime unit and integration modules passed: 56 passed, zero skipped, in 19.41 seconds. The proof executed existing and cold environments and preserved the original fixture identity. Records are `/private/tmp/513-native-ratchet-acceptance.{txt,xml}` and `/private/tmp/513-native-ratchet-proof-20261025-a/receipt.json`.

The other three selectors in change 17's existing 59-selector mapping are unchanged deferral/security guards. They passed separately, 3 passed, zero skipped, in 0.93 seconds; record `/private/tmp/513-native-retained-security.xml`. This is two executions, not a fabricated single 59-case run. No capsule implementation or repair was performed.

## Remaining gates

Final local format, type, lint, YAML, import boundaries, all seven strict module signatures and contracts passed. SMART and full testing each passed 5,866 tests with 77 existing opt-in skips, five baseline warnings and 95 passing subtests. Logs are `.audit/513-native-guard-final-gate-*`. The complete local pipeline passed its executable stages, including Requirements and 28 contract tests; only the approved local capsule review is explicitly DEFERRED, never PASS. Full-suite evidence precedes the final historical-case test refinement; the final 15-selector focused run verifies that test-only refinement without repeating the unchanged runtime suite.

The canonical Requirements reconciliation for the current mapping reports verified with `passing-after-legacy-tdd-ledger`, not a fabricated uniform RED proof. `.audit/513-native-guard-{plan,tdd-ledger,tdd-record,reconciliation,tested-source}.json` binds mixed historical evidence, actual-time independent mapping acceptance, final JUnit and staged-tree source bytes. These are local proof artifacts and grant no protected CI authority.

CodeRabbit CLI 0.9.1 completed full fifteen-file review. Earlier major/minor findings were fixed as described above. The final pass returned two minor findings. The spec now states the fingerprint trust limit explicitly. The proposed staged-file bypass was dismissed after the actual installed `pre_commit.staged_files_only` rejected that repair in a disposable repository and restored the working tree; committed CI also checks the committed tree. Standalone working-tree mode retains that documented limitation. Detailed dispositions and proof are `.audit/513-native-guard-review-dispositions.md` and `.audit/513-native-guard-staged-boundary.txt`. No unresolved actionable local engineering finding is claimed, and this disposition does not turn the separate protected security review into PASS.

The native scope check does not turn existing failures into PASS. The legacy CI transition is specified in `CI_TRANSITION.md`; no old security gate is bypassed by this unit. Independent protected review, exact-head CI and signed delivery remain separate prerequisites. No merge, publication, complete change-17 claim or archive is authorized.
