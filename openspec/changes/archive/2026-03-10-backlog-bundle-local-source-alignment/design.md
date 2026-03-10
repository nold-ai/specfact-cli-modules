## Context

Combined PR validation in `specfact-cli-modules` can import `specfact_backlog` from an installed user-home bundle copy under `~/.specfact/modules` instead of the checked-out workspace package. The branch code is correct, but larger gate runs become order-dependent and fail against stale bundle code.

## Decision

- Keep test bootstrap responsible for local bundle source precedence in this repo.
- Actively remove user-home module source paths from `sys.path` during pytest bootstrap.
- Purge already-imported bundle modules that resolved from user-home module roots so later imports rebind to local workspace sources.
- Reassert this alignment at session start and before each test to tolerate path mutations from imported core helpers.

## Validation

- Add a regression test for the bootstrap sanitizer.
- Re-run the failing backlog tests first.
- Re-run `hatch run contract-test` and `hatch run smart-test`.
