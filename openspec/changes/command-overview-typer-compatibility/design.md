## Context

`scripts/generate-command-overview.py` identifies options and arguments with
Click's public classes. Typer 0.27.0 uses implementation classes derived from
its bundled Click compatibility layer, so valid Typer parameters are skipped
in the Docs Review environment.

## Goals / Non-Goals

**Goals:**

- Preserve every option and argument exposed by the pinned Typer runtime.
- Keep existing Click parameter handling and generated-artifact schema stable.
- Prove the behavior with the same Typer version that Docs Review installs.

**Non-Goals:**

- Change module command syntax, registry contents, or package dependencies.
- Support arbitrary unpinned parameter implementations.

## Decisions

- Classify parameters against the supported Click and Typer option/argument
  classes instead of relying only on Click's public inheritance hierarchy.
- Add focused regression tests using Typer command construction and regenerate
  artifacts in an environment built from `requirements-docs-ci.txt`.

## Risks / Trade-offs

- [Typer internals change again] → Pin the tested version in the Docs Review
  dependency file and retain focused parameter-class coverage.
- [Broader type acceptance misclassifies a parameter] → Limit accepted classes
  to the runtime types emitted by Click and Typer.

## Migration Plan

1. Add a failing Typer 0.27 regression test.
2. Implement the narrow classifier update.
3. Regenerate artifacts using the CI dependency set and run Docs Review tests.
4. Roll back by reverting the classifier and generated artifacts together.
