## Context

The affected workflows resolve a same-named branch in `nold-ai/specfact-cli`,
check it out, install or execute it, and then run validation commands. They also
declare `workflow_dispatch`. Runtime `if:` guards route manual runs to literal
`main` or `dev` refs, but GitHub's cache-poisoning analysis associates the
dynamic checkout and its following executable steps with every externally
triggerable default-cache-writing event on the job.

## Goals / Non-Goals

**Goals:**

- Make the trigger boundary statically enforceable by removing manual dispatch
  from workflows that dynamically execute paired-core source.
- Preserve pull-request matching-branch validation and protected-branch push
  validation.
- Keep the change small enough to audit and revert as one unit.

**Non-Goals:**

- Add a replacement manual workflow or reusable-workflow framework.
- Change paired-core branch resolution for pull requests or pushes.
- Change module packages, signatures, versions, dependencies, or release jobs.
- Suppress, dismiss, or rewrite GitHub Security findings.

## Decision

Remove `workflow_dispatch` from each mixed-trust workflow and delete the now
unreachable literal manual checkout steps. Keep the existing non-manual
resolver and dynamic checkout unchanged. The focused contract test will assert
that each affected workflow:

1. retains its expected pull-request or push triggers;
2. contains no `workflow_dispatch` trigger;
3. retains the matching paired-core resolver and credential-free checkout; and
4. contains no dead manual checkout path.

This is preferred over an event-only step condition because the security
analyzer intentionally reasons at the job/trigger boundary. It is preferred
over removing same-named paired-core validation because that integration path
is an existing repository capability.

## Risks / Trade-offs

- [Manual validation entrypoints disappear] -> Use PR/push execution or GitHub's
  rerun controls; design a separate literal-ref-only manual workflow if real
  usage evidence requires one.
- [A future edit restores `workflow_dispatch`] -> Focused tests fail before the
  workflow can merge.
- [Scanner findings have a second root cause] -> Read the new Actions analysis
  after the PR run and extend only if concrete code-flow evidence remains.

## Verification

- Strict OpenSpec validation.
- Failing-first and passing focused workflow contract tests.
- `actionlint` and repository YAML validation for the three workflows.
- Required repository quality and review gates.
- GitHub Actions CodeQL analysis on the PR; the private alert state is the final
  external proof and is not reproduced in public artifacts.
