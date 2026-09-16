# Native Linux transport for exact staged review

## Why

Story [#473](https://github.com/nold-ai/specfact-cli-modules/issues/473) requires genuine Linux capsule evidence. On macOS, the Linux-only required test remains incomplete; Apple Silicon Docker introduces a Rosetta executable mapping rejected by the sealed launcher. Transport the unchanged developer hooks to a native Linux runner, binding the result to the exact local staged tree.

## What Changes

Add an explicitly selected workflow-dispatch mode to the existing customer workflow and a bounded patch validation/receipt helper. The normal customer corpus remains unchanged. The transport accepts only the seventeen reviewed PR478 coverage paths and cannot change hooks, workflows, dependencies or trust controls.

## Impact

Developer verification tooling only. No module payload, registry, signature, public CLI, user documentation URL, or release acceptance contract changes. This does not satisfy customer GitHub Actions or protected PR range evidence. Existing signed release and fifteen-combination acceptance remain required.
