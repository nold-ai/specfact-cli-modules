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
- Restore the intended module/core contract: declare the proven minimum core
  and omit a maximum until an actual incompatibility requires one.

**Non-Goals:**

- Add a replacement manual workflow or reusable-workflow framework.
- Change paired-core branch resolution for pull requests or pushes.
- Change analyzer behavior, frozen C14 capsule identities, dependencies, or
  release-job ownership.
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

The `specfact-code-review` manifest will declare `core_compatibility:
">=0.55.1"`. The immutable 0.55.1 checkout remains pinned by tag, commit, and
tree because it proves the lower boundary; it does not define an exact-only
runtime admission policy. The normal quality matrix installs the current paired
core and builds a local marketplace archive from the candidate package, so its
runtime-discovery smoke verifies a compatible version above the minimum.

The signed package manifest is the runtime enforcement source inside the
downloaded archive. The PR signing workflow owns the candidate signature. The
post-merge publisher owns the immutable registry archive, checksum and
signature sidecars, and registry-index promotion; the published 0.49.59 archive
remains immutable.

C14 remains active and its frozen checkpoint binds the original 0.49.59
release evidence, so those bytes are not rewritten. This change explicitly
supersedes C14's exact-only admission policy. If C14 is archived after this
change, its archive review must preserve this minimum-only rule or this
corrective delta must be archived again afterward; exact-only wording may remain
only as historical release evidence.

## Risks / Trade-offs

- [Manual validation entrypoints disappear] -> Use PR/push execution or GitHub's
  rerun controls; design a separate literal-ref-only manual workflow if real
  usage evidence requires one.
- [A future edit restores `workflow_dispatch`] -> Focused tests fail before the
  workflow can merge.
- [Scanner findings have a second root cause] -> Read the new Actions analysis
  after the PR run and extend only if concrete code-flow evidence remains.
- [A future core introduces a breaking change] -> Add an evidence-backed upper
  bound in a new module release before advertising that core as compatible.
- [Publication does not promote the candidate] -> Leave the manifest version
  ahead of the registry without mutating 0.49.59; rerun the canonical publisher
  or revert the metadata release.
- [A later C14 archive reintroduces exact-only policy] -> Treat this change as
  the later normative compatibility authority and verify archive ordering or an
  explicit follow-up supersession before C14 archival.

## Verification

- Strict OpenSpec validation.
- Failing-first and passing focused workflow contract tests.
- `actionlint` and repository YAML validation for the three workflows.
- Required repository quality and review gates.
- GitHub Actions CodeQL analysis on the PR; the private alert state is the final
  external proof and is not reproduced in public artifacts.
- Focused range contracts plus immutable-minimum and current-core runtime jobs.
- Module checksum/version verification and the repository signing workflow.
