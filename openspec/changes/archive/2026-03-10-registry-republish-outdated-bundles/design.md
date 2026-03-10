## Context

`specfact-cli-modules` publishes registry artifacts from an automated workflow on both `dev` and `main`. Today the workflow resolves bundles from the current diff and then asks `scripts/publish-module.py` whether each bundle's manifest version is greater than the checked-out branch's `registry/index.json`. That is sufficient for simple linear publishes, but it fails when registry state is stale relative to package manifests for reasons outside the current push. In that case, the workflow should still create the existing auto publish PR, but it currently does nothing because the bundle was not in the diff set.

## Goals / Non-Goals

**Goals:**
- Detect bundles whose manifest versions are ahead of the registry version used for publish decisions, even when those bundles were not part of the current push diff.
- Reuse the existing auto publish PR path instead of creating a second publish mechanism.
- Make the comparison source explicit so the workflow can reason about the effective registry state rather than only the current branch checkout.

**Non-Goals:**
- Redesign the entire registry layout or release process.
- Publish bundles without version monotonicity checks.
- Introduce branch-specific registry indexes or multi-registry serving in this change.

## Decisions

### 1. Keep diff-based detection, then union it with registry-outdated detection

The workflow should continue collecting bundles changed in the current push, because that is the cheapest signal for likely publishes. It should then add a second pass that scans bundle manifests versus the target registry baseline and unions any outdated bundles into the publish set.

Alternative considered:
- Replace diff detection entirely with scanning every bundle on every push. Rejected because it is slower and obscures the distinction between directly changed bundles and opportunistic catch-up republishes.

### 2. Centralize version comparison in a reusable script interface

`scripts/publish-module.py` already enforces monotonic version comparison. The workflow should extend or wrap that logic with an explicit registry baseline path/ref input so one implementation decides whether a bundle is outdated.

Alternative considered:
- Duplicate the version comparison inline in the workflow YAML. Rejected because it would drift from the existing publish pre-check script.

### 3. Compare against an explicit target registry baseline

The workflow should compare bundle manifests against a known target registry baseline, with `main` as the default exposed branch unless explicitly overridden. This avoids accidental branch-local decisions when `dev` and `main` differ.

Alternative considered:
- Keep comparing only against the currently checked-out branch. Rejected because that is the source of the stale-registry gap.

## Risks / Trade-offs

- [More bundles may be included in an automated publish PR than were changed in the current push] → Mitigation: surface the resolved publish set clearly in workflow logs and PR body.
- [Fetching or resolving the target baseline branch may fail in unusual repo states] → Mitigation: fail closed with a clear workflow error rather than silently skipping outdated bundles.
- [Developers may be surprised when a push republishes an older untouched bundle whose manifest was already ahead] → Mitigation: document that the workflow maintains registry consistency, not just diff-local publishes.

## Migration Plan

1. Add spec coverage for registry-outdated bundle detection and auto publish PR inclusion.
2. Add failing tests for bundle selection when manifest versions are ahead of the target registry baseline.
3. Extend the publish script/workflow to compute the union of changed bundles and outdated bundles.
4. Re-run workflow-oriented tests and validate the change.

## Open Questions

- Should the target comparison branch remain fixed to `main`, or should it be configurable per workflow invocation for maintenance scenarios?
