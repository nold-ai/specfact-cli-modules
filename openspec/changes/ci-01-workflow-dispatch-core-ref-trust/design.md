## Context

The affected workflows check out `nold-ai/specfact-cli` and execute or install
that checkout. Same-named feature branches are useful for pull-request parity,
while manual dispatch has a different trust boundary because it is explicitly
operator-triggered and does not need arbitrary paired-branch execution.

## Goals / Non-Goals

**Goals:**

- Keep matching paired-core branch validation for non-manual events.
- Make every manual paired-core checkout resolve to a literal protected branch.
- Express the boundary directly in workflow step conditions and prove it with
  repository tests.

**Non-Goals:**

- Change pull-request permissions, workflow purpose, or validation commands.
- Change C14 behavior, package dependencies, module metadata, publication, or
  dependency scanner findings.
- Generalize the change into a reusable workflow framework.

## Decisions

- Retain the existing resolver only when the event is not
  `workflow_dispatch`.
- Keep the existing dynamic checkout only for non-manual events.
- Add mutually exclusive manual checkout steps with literal `main` and `dev`
  refs. A manual run on `main` pairs with core `main`; every other manual
  modules ref pairs with core `dev`.
- Preserve `persist-credentials: false` on every paired-core checkout.
- Use one focused text-level workflow contract suite so the security invariant
  remains visible without coupling the tests to GitHub's YAML key coercion.

## Risks / Trade-offs

- [Manual feature-branch validation no longer pairs a same-named core branch]
  -> Use a pull request for paired feature-branch integration; manual runs use
  the trusted `dev` core baseline.
- [A future workflow edit removes an event guard] -> Contract tests require the
  resolver, dynamic checkout, and literal manual checkout conditions together.
- [Literal branches diverge from a release candidate] -> This change does not
  add release-candidate inputs; a future explicit immutable-ref design would
  require its own review.

## Migration Plan

1. Add and strictly validate the OpenSpec contract.
2. Add focused tests and record their pre-implementation failure.
3. Apply the same bounded step split to the three workflows.
4. Run focused tests, workflow lint, OpenSpec validation, and repository quality
   gates.
5. Roll back by reverting the workflow and contract-test commit together.
