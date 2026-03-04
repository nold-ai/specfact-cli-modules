---
name: Bug report
about: Report a bug in specfact-cli-modules (bundles, manifests, signing, CI/docs)
title: "[Bug] <Brief Description>"
labels: bug
assignees: ''

---

## Describe the Bug

A clear and concise description of what the bug is.

## To Reproduce

Steps to reproduce the behavior:

```bash
hatch run <command>
```

Example:

```bash
hatch run verify-modules-signature --require-signature --enforce-version-bump
```

## Expected Behavior

A clear and concise description of what you expected to happen.

## Actual Behavior

What actually happened? Include error messages, stack traces, or unexpected output.

## Environment

- **OS**: [e.g., Linux, macOS, Windows]
- **Python Version**: [e.g., 3.11.5]
- **Repo Branch**: [e.g., `feature/module-migration-05-modules-repo-quality`]
- **Relevant Bundle(s)**: [`specfact-project`, `specfact-backlog`, `specfact-codebase`, `specfact-spec`, `specfact-govern`]

## Validation Output

Include full output from relevant commands:

```markdown
Paste command output here
```

Typical commands:

- `hatch run format`
- `hatch run type-check`
- `hatch run lint`
- `hatch run yaml-lint`
- `hatch run check-bundle-imports`
- `hatch run verify-modules-signature --require-signature --enforce-version-bump`

## Additional Context

Add any other context about the problem here, such as:

- Related issues or PRs
- Whether this blocks release/merge to `dev`/`main`
