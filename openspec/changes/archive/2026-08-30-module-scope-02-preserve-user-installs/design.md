## Overview

Keep module precedence unchanged while removing guidance that turns normal shadowing into destructive cleanup. The modules repository only needs to describe the correct contract and protect that wording with focused tests; core owns runtime discovery and doctor output.

## Decisions

- Treat project-over-user shadowing as workspace-local precedence, not evidence of a stale or invalid user installation.
- State that the user copy remains installed and available in repositories without the project-scoped copy.
- Keep explicit user-initiated uninstall behavior unchanged. This change removes routine recommendations; it does not disable the command.
- Test the exact contributor-facing surfaces that caused the defect instead of adding a new runtime abstraction.
- Rename the local test bootstrap test to describe in-memory import eviction accurately. The helper changes `sys.path` and `sys.modules`; it does not delete installed files.

## Risks

- A user may still need to remove a genuinely unwanted duplicate. Mitigation: origin diagnostics remain available through `specfact module list --show-origin`, and explicit uninstall remains documented elsewhere.
- A wording-only regression could reintroduce destructive agent behavior. Mitigation: focused tests reject user-scope uninstall recommendations on these bootstrap surfaces.
- Core output could remain inconsistent with repository guidance. Mitigation: paired bug `nold-ai/specfact-cli#699` carries matching OpenSpec and tests.

## Rollback

Revert the guidance and test changes. No module data, installation state, manifest, registry row, or signature is migrated by this change.
