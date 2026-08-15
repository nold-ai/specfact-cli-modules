# Change: Make Code Review Scope and Differential Enforcement Truthful

## Why

`specfact code review run --scope changed` currently means worktree changes from `git diff HEAD`, not the committed pull-request delta. On a clean PR checkout it can select no committed files. Git resolution failure becomes an empty changed-line map, allowing blocking findings to be treated as legacy and producing a green exit.

The report also lacks an honest unknown/not-applicable state, conflates autofix availability with resolution, and determines introduction primarily through changed-line intersection. These are evidence-boundary defects that must be fixed before adding more review rules.

## What Changes

- Define explicit scope sources: `worktree`, `index`, `range`, `full`, or positional files for explicitly labelled non-PR inspection. Keep `changed` only as a deprecated alias for `worktree`.
- Require full base/head refs for range scope, derive the PR delta from the merge base, and reject any positional-file invocation that claims PR-range assurance.
- Materialize index analysis from the complete HEAD-plus-index tree and range analysis from the resolved merge-base/head commit trees in isolated roots, bind them with content manifests, and run every analyzer in a fail-closed OS filesystem sandbox exposing only its active read-only snapshot, exact read-only config/toolchain inputs, and process-private writable output/temp roots. Deny access to caller, opposite-snapshot, context, policy-source, and other-analyzer evidence roots; reject snapshot assurance when the required sandbox capability is unavailable. Also reject mutation-capable options for snapshot scopes and `focus=simplify` for range assurance because its finding filter is intentionally incomplete.
- Emit immutable scope evidence and fail closed as `UNKNOWN` when Git scope cannot be resolved. Treat the closed `governed-policy-paths-v1` analyzer/test/coverage-policy set as governed range impact alongside Python; a candidate policy diff is never NOT_APPLICABLE and remains UNKNOWN until a separately trusted policy-promotion contract exists.
- Reserve producer `assurance_kind=range_candidate` for a complete governed merge-base-to-head Python-and-policy selection with matching claimed context, and effective `pr_range` for a separate protected consumer verification envelope over that immutable report. Changed tests are always included, and path/facet/test/execution-level narrowing options are rejected before analysis. A complete local range without context remains `range_preview`; partial review remains worktree or explicit-files.
- Analyze the resolved merge-base and head source trees with the same pinned analyzer/config identities and classify findings as introduced, fixed, unchanged, or unknown using stable fingerprints; normalize a head file anchor through the resolved one-to-one rename map before comparison, and never use the supplied base-ref tip as the source-code differential baseline. Bind the resolved base-ref tip to an authenticated expected target commit/tree that the consumer independently verifies, freeze that current target-tip policy bundle, and select only contract-named sealed defaults from the signed installed module when an adapter's governed target configuration is absent. Pass the resulting safe per-snapshot config projections explicitly to both source snapshots so candidate head configuration cannot suppress its own findings, relative paths cannot escape into policy/worktree content, consumer repositories do not need to vendor module defaults, and already-promoted target policy cannot be ignored. Candidate policy/config diffs are separately selected and digested as governed impact, but stay shadow-only and cannot authorize themselves. `pr-range-v1` does not attempt Python closure for analyzer extensions: non-empty Pylint `init-hook`, repository/unapproved Pylint `load-plugins`, and Coverage `[run] plugins` outside the signed profile manifest are unsupported UNKNOWN. Any future accepted plugin must be an exact signed-toolchain profile member shared by both sides; the initial Pylint and Coverage plugin manifests are empty. Targeted pytest/coverage receives only explicit sealed target-tip policy projections—or their generated pinned defaults—with candidate auto-discovery and coverage environment overrides disabled. Every pinned-schema Coverage write destination is rewritten into the process-private output root; the read-only snapshot and configuration mounts are never Coverage data/report targets. Pytest policy selection follows the exact pinned pytest 9.0.3 locator across its complete supported source/section set, while the controller emits separate merge-base/head projections that rebase every schema-declared relative path onto the corresponding immutable snapshot and passes both explicit `-c` and `--rootdir`. Coverage selection likewise includes every source recognized by pinned Coverage 7.15.4, including `.coveragerc.toml`, under its recorded precedence. Ruff configuration includes a sealed, manifest-bound target-tip transitive `extend` closure so an extended policy file cannot fall outside governed impact or sandbox inputs. Basedpyright likewise seals its target-tip `extends` graph and `baselineFile` artifact; absence of repository config produces the exact contract-named per-snapshot `basedpyright-default-v1` projection instead of implicit `--project .` discovery.
- Define the closed `pr-range-v1` analyzer profile and report its identity/coverage; incomplete required evidence is `UNKNOWN` when no validated blocker already proves FAIL. The released signed module SHALL provision the exact loader/analyzer versions bound by the profile and implementation checkpoint—never ambient bare or lower-bound resolution—including explicit `pytest==9.0.3` and `coverage==7.15.4` constraints. Portable Python distribution identity binds wheel or canonical `.dist-info/RECORD` payloads and normalized entry points, not environment-specific generated launcher bytes.
- Separate finding severity, lifecycle status, autofix availability, and blocking policy.
- Use `PASS`, `FAIL`, `UNKNOWN`, and `NOT_APPLICABLE` truthfully with closed aggregate precedence: resolved no-impact is NOT_APPLICABLE; otherwise any validated blocker is FAIL; otherwise any required uncertainty is UNKNOWN; otherwise PASS. Mixed FAIL/UNKNOWN retains every unknown member fact while aggregate remains FAIL. Waivers remain a governance overlay.
- Migrate the first-party review ledger to consume and persist schema 1.6 `assurance_status`; UNKNOWN and NOT_APPLICABLE are audit records but never passing streaks or reward events.
- Migrate every canonical merge/PR-quality instruction surface to protected-CI range/base/head/context/full usage; label a complete local range without authenticated event context `range_preview`, and retain worktree/positional commands only for local staged or simplification workflows that do not claim PR assurance.
- Publish a signed schema 1.6 consumer compatibility matrix covering all authoritative statuses, the mixed FAIL/UNKNOWN precedence case, legacy projections, and exit behavior before any core consumer migration.

## Capabilities

### Modified Capabilities

- `review-run-command`: Resolve explicit snapshot scopes and perform deterministic base/head differential review.
- `review-finding-model`: Separate lifecycle, remediation availability, differential disposition, and policy.
- `review-cli-contracts`: Prove range selection, unknown handling, differential classifications, and analyzer coverage.

## Impact

- Planning artifacts only. No package source, tests, manifests, registry, version, signatures, prompts, or generated docs change in this commit.
- Later implementation changes the public review CLI and JSON schema additively, with a deprecation path for `--scope changed`.
- CI integrations that claim pull-request assurance must migrate to `--scope range --base-ref <base> --head-ref <head>` and require producer `scope_evidence.assurance_kind=range_candidate` plus a trusted envelope with `effective_assurance_kind=pr_range`; positional files remain valid only as `explicit_files` evidence and cannot satisfy that policy.
- Rollback: retain the legacy alias and dual-write old/new report fields during one compatibility release.

### Report compatibility and release gate

The additive authoritative field SHALL be `assurance_status` in `ReviewReport` schema `1.6`. For one compatibility release, producers SHALL also write the legacy `overall_verdict`, `ci_exit_code`, and `enforcement_mode` fields with this closed projection:

| `assurance_status` | Legacy `overall_verdict` | Non-shadow `ci_exit_code` | Shadow `ci_exit_code` |
|---|---|---:|---:|
| `PASS` | `PASS`, or `PASS_WITH_ADVISORY` when non-blocking findings remain | 0 | 0 |
| `FAIL` | `FAIL` | 1 | 0 |
| `UNKNOWN` | `FAIL` as the conservative legacy projection | 1 | 0 |
| `NOT_APPLICABLE` | `PASS_WITH_ADVISORY`, with an explicit no-governed-impact summary | 0 | 0 |

`enforcement_mode` is copied from the normalized enforcement-policy request, not from scope: `enforce` normalizes to legacy `full`; `full`, `changed`, and `shadow` serialize unchanged. `changed` remains valid for one release only with the deprecated changed/worktree path. Because the current CLI default is `changed`, an omitted enforcement option is resolved with scope awareness: range defaults to strict `full`, while the deprecated changed/worktree path retains `changed`. Explicit range plus `changed` is invalid; a non-shadow range run writes `full`, a shadow range run writes `shadow`, and `range` is never an `enforcement_mode` value. Scope truth remains in `scope_evidence.requested_scope`, `effective_scope`, and `assurance_kind`.

The new field is authoritative; dual-writing MUST NOT rewrite `UNKNOWN` or `NOT_APPLICABLE` to `PASS`. Schema 1.6 first-party consumers, including `code review ledger update`, SHALL read `assurance_status` rather than the legacy projection. The ledger persists UNKNOWN and NOT_APPLICABLE explicitly, retains the complete canonical schema 1.6 report as `report_json` plus `report_digest` in local and Supabase run records, applies zero reward, and leaves both pass and block streak counters unchanged. Reports older than 1.6 retain their prior PASS/PASS_WITH_ADVISORY/FAIL ledger behavior. A schema older than `1.6` may be read only as legacy `PASS` (from `PASS` or `PASS_WITH_ADVISORY`) or `FAIL`; it can never be upgraded by inference to `UNKNOWN` or `NOT_APPLICABLE`. Schema `1.6+` with a missing or invalid `assurance_status` is invalid/unknown and cannot pass.

The first signed C14 module release SHALL set `core_compatibility: '>=0.56.0,<1.0.0'` and is blocked only until compatibility tests prove that core version can load and validate schema `1.6`; actual core PR-CI migration is explicitly downstream of the signed release. The behavior-ready implementation PR regenerates command references and public docs; the canonical post-merge publish workflow alone generates and signs registry/archive/checksum/sidecar artifacts. A separate accepted core adoption change then pins those final signed identities and requires the verified `pr_range` envelope; it never adopts a feature-branch package.

## Explicit Non-Goals

- Add or change individual Ruff, Radon, Semgrep, basedpyright, pylint, contract, or AI-bloat detectors.
- Fuse Requirements verdicts into Code Review.
- Perform LLM review or claim semantic completeness.
- Infer historical pytest dependency closure.
- Implement analyzer-policy promotion or semantic monotonicity comparison; C14 detects the closed candidate policy/config diff and reports UNKNOWN, while a separate accepted trust-epoch/policy-promotion contract is required to authorize it.
- Implement the global governance evidence graph.
- Claim hostile-candidate resistance for pytest, CrossHair, or any analyzer that executes candidate Python. CR14 isolates other evidence roots but does not make candidate-authored runtime output an independent security attestation.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **Origin**: dogfooding analysis of core PRs #665–#671
- **Flagship track**: deterministic code review and AI-bloat defense foundation
- **Planning date**: 2026-08-13

