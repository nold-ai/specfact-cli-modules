## Context

The `specfact-requirements` bundle already has the authoritative import,
validation, coverage, and gate-finding operations. The missing piece is an
orchestration boundary that turns those existing results into one CI verdict
without changing their runtime semantics.

## Decisions

### Evaluate only changed active OpenSpec sources

The adapter discovers source directories from the branch diff below
`openspec/changes/`, excludes `archive/`, and evaluates each unique active
change directory that still exists in the checked-out revision. A branch with
no changed active source receives `skipped`, rather than a misleading green
requirements verdict.

### Use isolated, disposable bundles

Every selected OpenSpec source is imported into its own temporary project
bundle. This prevents requirements from separate changes from being merged and
keeps the OpenSpec source read-only. The temporary bundle is not a published
artifact; only the normalized evidence report is retained.

### Preserve source results and add a small verdict envelope

The report preserves the module's import diagnostics, validation report,
coverage payload, and gate-finding counts. The adapter adds only stable
orchestration fields: schema version, source path, verdict, reasons, timestamps
where supplied by CI, and aggregate counts. A source fails when any of these
are true:

1. import returns an error diagnostic;
2. zero requirements are imported;
3. validation status is `failed`;
4. `with_test_links` is less than `total_requirements`; or
5. any error-level requirements gate finding is present. Informational findings
   remain in the artifact but do not turn a passed validation report red.

### Declare test links in a sidecar, not in generated native records

Current core native OpenSpec imports do not carry a test-link annotation from
Markdown. A changed OpenSpec source may therefore include an optional sibling
`requirements-evidence.yaml` with a `requirements` mapping keyed by the
imported stable requirement ID. Each entry declares one or more
repository-relative `test_links`. The adapter validates that mapped IDs were
imported and that every target file exists, overlays the links only into its
temporary bundle, and then invokes the existing Requirements validation and
coverage operations. Missing sidecars remain a red traceability result; they
are never silently treated as a green assertion.

### CI always retains failure evidence

The GitHub Actions job runs after the existing paired-core setup, writes the
report to the workspace, appends a concise verdict summary to
`GITHUB_STEP_SUMMARY`, and uploads the report with `if: always()`. The adapter
exits non-zero only after it has written a failed report.

## Risks and mitigations

- **Current OpenSpec sources may lack test links.** The check intentionally
  reports a red, actionable traceability failure; the report identifies the
  source and count rather than hiding it.
- **A changed source may be deleted or archived in the same branch.** Discovery
  excludes archived and absent directories, yielding a deterministic skipped
  result if no active source remains.
- **This is mistaken for execution proof.** Both artifact and CI summary use
  “requirements evidence” wording and state that test execution proof is out
  of scope.
- **A stale sidecar creates false traceability.** The adapter rejects unknown
  requirement IDs and missing target files before validating the temporary
  bundle; executed-test proof remains a separate later phase.
