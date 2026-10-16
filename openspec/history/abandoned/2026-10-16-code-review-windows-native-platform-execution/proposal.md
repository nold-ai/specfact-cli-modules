# Change: Native Windows x86-64 project-driven Code Review

## Abandoned remaining proposal (2026-10-16)

The owner approved replacing capsules with trusted local project-aware review. Issue #495 is superseded by modules #513-#516 and core #769. This never-delivered capability is retained as non-canonical abandoned history. No implementation, completed archive or specification promotion is claimed. Original task states and planning records below are historical, not remaining implementation authority. The replacement architecture is in `openspec/changes/code-review-17-project-runtime-bootstrap/design.md`.

## Why

Windows developers need the same separation between sealed reviewers and their
actual project setup as Linux and macOS developers. A Linux container or WSL
process does not establish a native Windows execution boundary.

## What Changes

- Extend the shared ProjectPlan discovery, explicit configuration, automatic
  runtime acquisition and on-demand preparation contract to Windows x86-64.
- Prove a Windows boundary for startup ownership, managed children, filesystem,
  network, descriptors, resources and cleanup before selecting production mechanisms.
- Package a verified native Python/analyzer/manager closure with PE dependency
  inventory, atomic local project caches and versioned evidence compatibility.
- Validate all ten analyzers and the complete pip/Hatch/uv/Poetry project corpus
  on matching-architecture Windows VMs or physical systems, under an ordinary
  user with normal protections and through the actual installation route.

## Capabilities

### New Capabilities

- `review-windows-native-execution`: native Windows boundary and artifact-bound acceptance.

### Modified Capabilities

None until this deferred follow-up is approved for implementation.

## Dependencies and Impact

#460 / `code-review-native-platform-execution` blocks this follow-up. This story
does not block Linux x86-64 or macOS ARM64 delivery. Windows ARM64 requires a
separate artifact and acceptance target. Publisher keys remain in CI/CD; no
paid publisher program, Docker, hypervisor or customer SDK is a runtime prerequisite.
Actual download protections still require proof. No automatic merge or publication.

## Source Tracking

<!-- source_repo: nold-ai/specfact-cli-modules -->
- **GitHub Issue**: [#495](https://github.com/nold-ai/specfact-cli-modules/issues/495)
- **Prerequisite**: [#460](https://github.com/nold-ai/specfact-cli-modules/issues/460), [native proposal](../../../changes/code-review-native-platform-execution/proposal.md)
- **Parent Feature**: [#163](https://github.com/nold-ai/specfact-cli-modules/issues/163)
- **Last Synced Status**: open / Todo, deferred, 2026-10-05 Europe/Berlin
