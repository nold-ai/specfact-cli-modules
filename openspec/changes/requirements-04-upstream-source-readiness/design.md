## Context

`openspec-01-intent-trace` established that the Requirements module is a thin
command surface over core-owned OpenSpec and Spec Kit normalizers. Local
end-to-end testing against the official Spec Kit 0.12.15 scaffold found that a
pristine `spec.md` normalizes placeholder Functional Requirements into six
misleading records. OpenSpec has a native strict validator, whereas current
Spec Kit has no equivalent feature-validation command (`specify check` only
checks the tool installation).

The module must not grow a second parser, hashing implementation, or authoring
schema to solve this. Source readiness therefore belongs in the paired core
contract and must be exposed to the module as structured import diagnostics.

## Goals / Non-Goals

**Goals:**

- Ensure only ready native upstream artifacts become persisted requirement
  evidence.
- Make rejected sources deterministic, machine-readable, non-zero, and
  read-only.
- Preserve basic portable imports while allowing strict/enterprise policy to
  require the native OpenSpec validator.
- Keep completed OpenSpec and Spec Kit import mapping, source hashes, and
  idempotency stable.

**Non-Goals:**

- Defining a SpecFact authoring schema for OpenSpec or Spec Kit.
- Writing back validation results or remediation into upstream directories.
- Making the OpenSpec CLI a mandatory dependency for every basic import.
- Treating `specify check` as feature-artifact validation.
- Implementing native readiness parsing or policy evaluation in this module.

## Decisions

### Core returns an atomic readiness result before persistence

The paired core API SHALL return normalized records only when a source is ready;
otherwise it SHALL return zero records and structured diagnostics. The module
shall reuse its existing persistence path only for accepted records.

This prevents partial bundles and keeps the trust decision beside the parser,
normalizer, hash, and gate helpers already owned by core. An alternative of
filtering placeholders in the module is rejected because it duplicates
source-specific parsing and can diverge from the core contract.

### Known incomplete Spec Kit markers are fail-closed

Core SHALL recognise the official native draft markers needed to identify an
unfinished source: unresolved placeholder tokens, `NEEDS CLARIFICATION`, no
substantive Functional Requirement, and absent meaningful acceptance scenarios
when user stories are present. It SHALL return
`incomplete-source-template` or `source-incomplete`, with source locations,
instead of emitting partial records.

Detection SHALL use narrow, documented marker rules rather than a whole-template
hash so valid prose containing ordinary brackets is not rejected. A pinned
official scaffold fixture and a scheduled upstream compatibility check guard
against template drift.

### OpenSpec validation is policy-gated, not an ambient dependency

When the core policy explicitly requires upstream validation, core SHALL invoke
the native OpenSpec CLI with `validate --strict --json` for the selected change.
A failed command yields `source-invalid`; an unavailable validator yields
`upstream-validator-unavailable`. Either result rejects the source atomically.

Basic portable import remains available when policy does not require the CLI;
the existing core parser/schema fail-closed behavior remains in effect. This
avoids different results merely because a developer happens to have `openspec`
on `PATH`. An alternative of always probing any discovered binary is rejected
because it makes imports environment-dependent and falsely conflates tool
presence with an explicit assurance policy.

### Module maps core diagnostics without reinterpretation

The Requirements module SHALL surface the core diagnostic code, severity,
locator, and message unchanged in JSON and text output. It SHALL return a
non-zero command result when core reports an error and SHALL not write the
requirements sidecar for a rejected source.

## Risks / Trade-offs

- [Official Spec Kit templates change] → Pin a current scaffold fixture,
  schedule a compatibility check, and fail only on narrow known markers.
- [A valid project uses bracketed prose] → Do not use generic bracket matching;
  test legitimate bracketed requirements.
- [OpenSpec CLI is absent in portable environments] → Require it only when
  policy explicitly demands upstream validation and return a named diagnostic.
- [Core follow-up is delayed] → Keep this modules change blocked; do not add
  duplicate readiness logic locally.

## Migration Plan

1. Land the paired core readiness contract and its compatibility tests.
2. Raise `specfact-requirements` `core_compatibility` to the released core
   version and delegate the new result unchanged.
3. Add module command tests, docs, signatures, registry publication, and a patch
   release.
4. Roll back by restoring the previous module version; no upstream source files
   or bundle mutation is required for rollback.

## Open Questions

- Which exact core release/version will expose the readiness result and policy
  configuration contract?
- Should strict/enterprise policy require OpenSpec native validation by default,
  or should repository configuration opt in explicitly for those profiles?
