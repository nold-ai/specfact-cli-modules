# Change: Native Local Code Review Across macOS Linux and Windows

## Why

SpecFact's primary use is a local-first CLI invoked by developers and agentic AI independently of their OS. C14's immutable execution path is currently Linux x86-64 specific even though several pinned analyzers already ship native macOS and Windows builds. Native ARM64 Linux images alone would not satisfy this product requirement.

## What Changes

- Specify native macOS, Linux, and Windows execution with explicit x64/ARM64 coverage and no Docker, WSL, VM, or emulation dependency.
- Preserve portable review and C15 verdict semantics while separating runtime provisioning and OS-native isolation/observation.
- Require released prerequisite/C15 baseline reassessment and native platform evidence before final implementation design or support claims.

## Capabilities

### New Capabilities

- `review-native-platform-execution`: Requirements and verification obligations for native local platform execution; the installed-payload correction remains a separate prerequisite.

### Modified Capabilities

None in this planning delivery. Future implementation must reconcile these obligations with the then-current review contracts before modifying a public interface.

## Impact

Planning artifacts only. No runtime source, tests, schemas, versions, signatures, registry entries, or supported-platform claims change. Future signed bundle changes require semver/core compatibility and canonical publication. No current CLI/API additions are approved.

## Dependencies

- Parent: modules [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163), under epic #162.
- Direct blockers: layout correction [#459](https://github.com/nold-ai/specfact-cli-modules/issues/459), released checkpoint/conformance [#434](https://github.com/nold-ai/specfact-cli-modules/issues/434), and core C15 adoption [#679](https://github.com/nold-ai/specfact-cli/issues/679).
- Transitive sequence: core #682 -> modules #431 -> core #680 -> core #683 -> modules #432; modules #432 plus core #684 -> modules #434.
- Modules #432 plus existing policy/profile/exception prerequisites -> modules C15 #417 -> core #679. Core #679 retains its existing policy/profile/exception blockers.
- Core means nold-ai/specfact-cli; modules means nold-ai/specfact-cli-modules. Preserve existing edges; do not duplicate transitive blockers.
- Harness adapters #433 are downstream of #434 and are not prerequisites for native execution.

## Acceptance Criteria

- This change has proposal, design, scenario-based spec deltas, ordered future tasks, and planned Requirements evidence.
- GitHub type, assignee, parent, project Todo status, labels, and native dependency relationships match this proposal.
- Strict OpenSpec validation, Markdown checks, staged planned-maturity Requirements validation, and applicable planning review pass.
- The planning PR targets dev, references the issue without closing it, and leaves implementation tasks unchecked.
- Future behavior acceptance is defined in specs/review-native-platform-execution/spec.md; planning acceptance does not establish runtime correctness.

## Non-Goals

No production implementation, runtime tests, release actions, implementation completion, or archive operation in this PR. Existing unrelated changes remain untouched.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: #460
- **Issue URL**: <https://github.com/nold-ai/specfact-cli-modules/issues/460>
- **Last Synced Status**: proposed; Todo; implementation not started
- **Sanitized**: true
