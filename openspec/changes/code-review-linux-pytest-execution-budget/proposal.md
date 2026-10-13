## Why

A complete configured pytest workload may exceed the legacy Linux capsule launch budget even while tests make progress. Operators need a bounded, explicit execution budget without reducing test selection or weakening incomplete-evidence handling.

## What Changes

- Add an operator-only Linux pytest member launch-budget option with legacy300-second default and maximum600seconds.
- Preserve all other member budgets, selected files, test/coverage policy, sandboxing and signatures.
- Report the requested/effective member budget. Reject invalid budgets before launch and preserve UNKNOWN/nonzero on timeout.

## Impact

Review options, CLI request routing, Linux capsule launch and native report provenance. Darwin keeps its existing broker policy; unsupported nondefault Linux-only overrides fail closed. Publication requires the normal reviewed signed-module path. No downstream private source or evidence is included.
