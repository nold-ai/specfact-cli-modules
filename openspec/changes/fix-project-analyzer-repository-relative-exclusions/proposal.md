## Why

The companion project analyzer can exclude valid Python sources because it searches absolute paths for fragments such as `env`, `build`, and `dist`. Apply the same directory-component matching as the [core fix](https://github.com/nold-ai/specfact-cli/pull/791).

## What Changes

- Match excluded directory names relative to the selected repository.
- Preserve existing test-file rules, public interfaces, and analyzer behavior outside source selection.
- Verify feature extraction on a nested Python source and the corresponding excluded-directory controls.

## Impact

Only the Project bundle payload changes. Existing dependencies, signing workflows, and release procedures apply.
